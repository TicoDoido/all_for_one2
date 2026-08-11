import os
import struct
import json
import flet as ft

# ==============================================================================
# TRADUÇÕES DO PLUGIN
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "UISB Mindjack",
        "plugin_description": "Escolha múltiplos arquivos .UISB para exportar em .JSON ou arquivos .JSON para converter em .UISB",
        "cmd_pick_uisb": "📦 Selecionar Arquivos .UISB ➔ Exportar JSON",
        "cmd_pick_json": "📦 Selecionar Arquivos .JSON ➔ Converter UISB",
        "log_starting_export": "Iniciando exportação dos arquivos .UISB selecionados...",
        "log_starting_import": "Iniciando conversão dos arquivos .JSON selecionados...",
        "summary": "Processamento concluído: {success} sucesso(s), {fail} falha(s).",
        "cancelled": "Seleção cancelada pelo usuário.",
        "select_uisb_title": "Selecione os arquivos .UISB",
        "select_json_title": "Selecione os arquivos .JSON",
    },
    "en_US": {
        "plugin_name": "UISB Mindjack",
        "plugin_description": "Select multiple .UISB files to export to .JSON or .JSON files to convert to .UISB",
        "cmd_pick_uisb": "📦 Select .UISB Files ➔ Export JSON",
        "cmd_pick_json": "📦 Select .JSON Files ➔ Repack UISB",
        "log_starting_export": "Starting export of selected .UISB files...",
        "log_starting_import": "Starting repack of selected .JSON files...",
        "summary": "Processing finished: {success} succeeded, {fail} failed.",
        "cancelled": "Selection cancelled by user.",
        "select_uisb_title": "Select .UISB files",
        "select_json_title": "Select .JSON files",
    },
    "es_ES": {
        "plugin_name": "UISB Mindjack",
        "plugin_description": "Seleccione varios archivos .UISB para exportar a .JSON o archivos .JSON para convertir a .UISB",
        "cmd_pick_uisb": "📦 Seleccionar Archivos .UISB ➔ Exportar JSON",
        "cmd_pick_json": "📦 Seleccionar Archivos .JSON ➔ Convertir UISB",
        "log_starting_export": "Iniciando exportación de archivos .UISB seleccionados...",
        "log_starting_import": "Iniciando conversión de archivos .JSON seleccionados...",
        "summary": "Procesamiento finalizado: {success} éxito(s), {fail} fallo(s).",
        "cancelled": "Selección cancelada por el usuario.",
        "select_uisb_title": "Seleccione archivos .UISB",
        "select_json_title": "Seleccione archivos .JSON",
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

state = {
    "logger": None,
    "lang": "pt_BR"
}

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(
        state["lang"],
        PLUGIN_TRANSLATIONS["pt_BR"]
    ).get(key, key).format(**kwargs)

def log(msg, color=None):
    if state["logger"]:
        state["logger"](msg, color=color)
    else:
        print(msg)

# ==============================================================================
# LÓGICA DE EXTRAÇÃO E REINSERÇÃO BINÁRIA (.UISB / .JSON)
# ==============================================================================

def parse_uisb(file_path):
    """Extrai os dados e textos de um arquivo binário .UISB"""
    with open(file_path, 'rb') as f:
        data = f.read()
    
    magic, hash_val, file_size = struct.unpack('>III', data[0:12])
    name = data[12:44].decode('ascii', errors='ignore').rstrip('\x00')
    flag = struct.unpack('>I', data[44:48])[0]
    count = struct.unpack('>I', data[48:52])[0]
    audio_start, audio_end = struct.unpack('>ff', data[52:60])
    
    entries = []
    offset = 60
    for i in range(count):
        start_time, end_time, char_count = struct.unpack('>ffI', data[offset:offset+12])
        text_bytes = data[offset+12 : offset+12 + char_count*2]
        raw_text = text_bytes.decode('utf-16be', errors='ignore')
        clean_text = raw_text.rstrip('\x00')
        
        entries.append({
            "id": i + 1,
            "start_time": round(start_time, 3),
            "end_time": round(end_time, 3),
            "text": clean_text
        })
        offset += 12 + char_count * 2
        
    result = {
        "header": {
            "magic": magic,
            "hash_val": hash_val,
            "name": name,
            "flag": flag,
            "audio_start": round(audio_start, 3),
            "audio_end": round(audio_end, 3)
        },
        "entries": entries
    }
    return result

def repack_uisb_data(header_info, entries, output_uisb_path):
    """Reinsere os textos de volta no binário .UISB ajustando bytes UTF-16 BE e alinhamento"""
    magic = header_info["magic"]
    hash_val = header_info["hash_val"]
    name = header_info["name"]
    flag = header_info["flag"]
    audio_start = header_info["audio_start"]
    audio_end = header_info["audio_end"]
    
    body = bytearray()
    
    for e in entries:
        txt = e["text"]
        text_utf16be = txt.encode('utf-16be')
        
        # Garante a terminação nula em UTF-16 (\x00\x00)
        if not text_utf16be.endswith(b'\x00\x00'):
            text_utf16be += b'\x00\x00'
            
        # Assegura alinhamento em múltiplos de 4 bytes
        if len(text_utf16be) % 4 != 0:
            text_utf16be += b'\x00\x00'
            
        char_count = len(text_utf16be) // 2
        
        body.extend(struct.pack('>ffI', float(e["start_time"]), float(e["end_time"]), char_count))
        body.extend(text_utf16be)
        
    total_size = 60 + len(body)
    
    name_bytes = name.encode('ascii').ljust(32, b'\x00')
    header_bytes = struct.pack('>III', magic, hash_val, total_size) + name_bytes + struct.pack('>IIff', flag, len(entries), float(audio_start), float(audio_end))
    
    final_data = header_bytes + body
    
    with open(output_uisb_path, 'wb') as f:
        f.write(final_data)
        
    return len(final_data)

def repack_uisb(json_path, output_uisb_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return repack_uisb_data(data["header"], data["entries"], output_uisb_path)

# ==============================================================================
# REGISTRO DO PLUGIN NO ALL FOR ONE
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    state["logger"] = log_func
    state["lang"] = host_language

    def on_uisb_picked(e: ft.FilePickerResultEvent):
        if not e.files:
            log(t("cancelled"), color=COLOR_LOG_YELLOW)
            return

        success = 0
        fail = 0

        log(t("log_starting_export"), color=COLOR_LOG_YELLOW)
        for f in e.files:
            try:
                target_dir = os.path.dirname(f.path)
                out_path = os.path.join(target_dir, os.path.splitext(os.path.basename(f.path))[0] + ".json")

                data = parse_uisb(f.path)
                with open(out_path, 'w', encoding='utf-8') as out_f:
                    json.dump(data, out_f, ensure_ascii=False, indent=2)

                log(f"  [OK] {os.path.basename(f.path)} ➔ {os.path.basename(out_path)}", color=COLOR_LOG_GREEN)
                success += 1
            except Exception as ex:
                log(f"  [ERRO] {os.path.basename(f.path)}: {ex}", color=COLOR_LOG_RED)
                fail += 1

        log(t("summary", success=success, fail=fail), color=COLOR_LOG_GREEN if fail == 0 else COLOR_LOG_YELLOW)

    def on_json_picked(e: ft.FilePickerResultEvent):
        if not e.files:
            log(t("cancelled"), color=COLOR_LOG_YELLOW)
            return

        success = 0
        fail = 0

        log(t("log_starting_import"), color=COLOR_LOG_YELLOW)
        for f in e.files:
            try:
                target_dir = os.path.dirname(f.path)
                out_path = os.path.join(target_dir, os.path.splitext(os.path.basename(f.path))[0] + ".UISB")

                size = repack_uisb(f.path, out_path)
                log(f"  [OK] {os.path.basename(f.path)} ➔ {os.path.basename(out_path)} ({size} bytes)", color=COLOR_LOG_GREEN)
                success += 1
            except Exception as ex:
                log(f"  [ERRO] {os.path.basename(f.path)}: {ex}", color=COLOR_LOG_RED)
                fail += 1

        log(t("summary", success=success, fail=fail), color=COLOR_LOG_GREEN if fail == 0 else COLOR_LOG_YELLOW)

    picker_uisb = ft.FilePicker(on_result=on_uisb_picked)
    picker_json = ft.FilePicker(on_result=on_json_picked)

    if page:
        page.overlay.append(picker_uisb)
        page.overlay.append(picker_json)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "pickers": [picker_uisb, picker_json],
        "commands": [
            {
                "label": t("cmd_pick_uisb"),
                "action": lambda: picker_uisb.pick_files(
                    dialog_title=t("select_uisb_title"),
                    allow_multiple=True,
                    allowed_extensions=["uisb"]
                )
            },
            {
                "label": t("cmd_pick_json"),
                "action": lambda: picker_json.pick_files(
                    dialog_title=t("select_json_title"),
                    allow_multiple=True,
                    allowed_extensions=["json"]
                )
            }
        ]
    }
