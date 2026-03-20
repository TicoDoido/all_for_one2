import os
import struct
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "DAT/HED/DB Eternal Poison (PS2)",
        "plugin_description": "Extrai e reempacota arquivos de containers DAT/HED e textos .DB",
        "extract_file": "Extrair .DAT/.HED",
        "rebuild_file": "Reempacotar .DAT/.HED",
        "extract_db": "Extrair textos .DB",
        "insert_db": "Inserir textos .DB",
        "select_hed_file": "Selecione o arquivo .HED",
        "select_db_file": "Selecione o arquivo .DB",
        "msg_done_extract": "Arquivos extraídos em: {folder}",
        "msg_done_repack": "Repack concluído: {dat}",
        "msg_done_extract_db": "Textos extraídos em: {txt}",
        "msg_done_insert_db": "DB atualizado com sucesso!",
        "log_read_entry": "Entrada {i}: {name} (Offset: {offset})",
        "log_skipped": "Entrada {i} ignorada (vazia/fim)",
        "warn_missing": "[AVISO] Arquivo ausente: {name}",
        "err_unexpected": "Erro: {error}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}..."
    },
    "en_US": {
        "plugin_name": "DAT/HED/DB Eternal Poison (PS2)",
        "plugin_description": "Extracts and repacks DAT/HED and .DB text files",
        "extract_file": "Extract .DAT/.HED",
        "rebuild_file": "Repack .DAT/.HED",
        "extract_db": "Extract .DB texts",
        "insert_db": "Insert .DB texts",
        "select_hed_file": "Select .HED file",
        "select_db_file": "Select .DB file",
        "msg_done_extract": "Files extracted to: {folder}",
        "msg_done_repack": "Repack finished: {dat}",
        "msg_done_extract_db": "Texts extracted to: {txt}",
        "msg_done_insert_db": "DB updated successfully!",
        "log_read_entry": "Entry {i}: {name} (Offset: {offset})",
        "log_skipped": "Entry {i} skipped",
        "warn_missing": "[WARN] Missing file: {name}",
        "err_unexpected": "Error: {error}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}..."
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

logger = None
current_lang = "pt_BR"

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# LÓGICA DE NEGÓCIO (MANTIDA)
# ==============================================================================

def pad_to_boundary_size(n, boundary):
    return (boundary - (n % boundary)) % boundary

def read_hed_entries(hed_path):
    entries = []
    with open(hed_path, "rb") as f:
        f.seek(88) # Pulo padrão do Eternal Poison
        i = 0
        while True:
            pos = f.tell()
            data = f.read(44)
            if not data or len(data) < 44: break
            
            offset, size = struct.unpack("<II", data[:8])
            raw_name = data[8:40]
            name = raw_name.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
            file_id = data[40:44]

            if name == "--DirEnd--" or file_id == b"\x00\x00\x00\x00":
                i += 1
                continue

            entries.append({"NAME": name, "OFFSET": offset, "SIZE": size, "HED_POS": pos})
            logger(t("log_read_entry", i=i, name=name, offset=offset))
            i += 1
    return entries

# ==============================================================================
# FUNÇÕES DE EXECUÇÃO
# ==============================================================================

def run_extract_ep(hed_path):
    try:
        dat_path = os.path.splitext(hed_path)[0] + ".dat"
        entries = read_hed_entries(hed_path)
        out_dir = os.path.splitext(hed_path)[0]
        os.makedirs(out_dir, exist_ok=True)

        with open(dat_path, "rb") as df:
            for e in entries:
                df.seek(e["OFFSET"])
                data = df.read(e["SIZE"])
                out_path = os.path.join(out_dir, e["NAME"])
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "wb") as outf:
                    outf.write(data)
        
        logger(t("msg_done_extract", folder=out_dir), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("err_unexpected", error=str(e)), color=COLOR_LOG_RED)

def run_repack_ep(hed_path):
    try:
        entries = read_hed_entries(hed_path)
        extracted_folder = os.path.splitext(hed_path)[0]
        dat_path = os.path.splitext(hed_path)[0] + ".dat"

        with open(dat_path, "wb") as dat_out, open(hed_path, "rb+") as hed_io:
            current_offset = 0
            for e in entries:
                in_path = os.path.join(extracted_folder, e["NAME"])
                if not os.path.exists(in_path):
                    logger(t("warn_missing", name=e["NAME"]), color=COLOR_LOG_RED)
                    continue

                with open(in_path, "rb") as inf:
                    data = inf.read()

                dat_out.seek(current_offset)
                dat_out.write(data)
                
                # Padding de 0x4000 (Setor PS2)
                pad = pad_to_boundary_size(len(data), 0x4000)
                if pad: dat_out.write(b"\x00" * pad)

                hed_io.seek(e["HED_POS"])
                hed_io.write(struct.pack("<II", current_offset, len(data)))
                current_offset = dat_out.tell()

        logger(t("msg_done_repack", dat=dat_path), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("err_unexpected", error=str(e)), color=COLOR_LOG_RED)

def run_extract_db(db_path):
    try:
        out_txt = os.path.splitext(db_path)[0] + ".txt"
        texts = []
        with open(db_path, "rb") as f:
            total_texts = f.read(1)[0]
            for i in range(total_texts):
                id_bytes = f.read(4)
                size = f.read(1)[0]
                text = f.read(size).rstrip(b"\x00").decode("ansi", errors="ignore").replace("\n", "[BR]")
                texts.append(f"{id_bytes.hex().upper()}:{text}")
        
        with open(out_txt, "w", encoding="ansi") as out_f:
            out_f.write("\n".join(texts))
        logger(t("msg_done_extract_db", txt=out_txt), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("err_unexpected", error=str(e)), color=COLOR_LOG_RED)

def run_insert_db(db_path):
    try:
        txt_path = os.path.splitext(db_path)[0] + ".txt"
        lines = []
        with open(txt_path, "r", encoding="ansi") as f:
            for line in f:
                if ":" in line:
                    id_hex, text = line.strip().split(":", 1)
                    text_bytes = text.replace("[BR]", "\n").encode("ansi") + b"\x00"
                    lines.append((id_hex, text_bytes))

        with open(db_path, "wb") as f:
            f.write(bytes([len(lines)]))
            for id_hex, data in lines:
                f.write(bytes.fromhex(id_hex))
                f.write(bytes([len(data)]))
                f.write(data)
        logger(t("msg_done_insert_db"), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("err_unexpected", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# REGISTRO DO PLUGIN
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR"):
    global logger, current_lang
    logger = log_func
    current_lang = host_language

    # File Pickers
    fp_extract = ft.FilePicker(on_result=lambda e: run_extract_ep(e.files[0].path) if e.files else None)
    fp_rebuild = ft.FilePicker(on_result=lambda e: run_rebuild_ep(e.files[0].path) if e.files else None)
    fp_db_ext = ft.FilePicker(on_result=lambda e: run_extract_db(e.files[0].path) if e.files else None)
    fp_db_ins = ft.FilePicker(on_result=lambda e: run_insert_db(e.files[0].path) if e.files else None)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "pickers": [fp_extract, fp_rebuild, fp_db_ext, fp_db_ins],
        "commands": [
            {"label": t("extract_file"), "action": lambda: fp_extract.pick_files(allowed_extensions=["hed"])},
            {"label": t("rebuild_file"), "action": lambda: fp_rebuild.pick_files(allowed_extensions=["hed"])},
            {"label": t("extract_db"), "action": lambda: fp_db_ext.pick_files(allowed_extensions=["db"])},
            {"label": t("insert_db"), "action": lambda: fp_db_ins.pick_files(allowed_extensions=["db"])}
        ]
    }