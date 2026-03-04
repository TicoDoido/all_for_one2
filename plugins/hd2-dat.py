import os
import struct
import time
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "Extrator DAT+HD2 (Dark Cloud PS2)",
        "plugin_description": "Extrai arquivos de jogos PS2 que usam pares .hd2 + .dat (Dark Cloud)",
        "extract_command": "Extrair DAT+HD2",
        "select_hd2_file": "Selecione o arquivo .hd2",
        "error_dat_not_found": "Arquivo DAT correspondente não encontrado: {path}",
        "error_hd2_invalid": "Arquivo HD2 inválido (tamanho insuficiente).",
        "log_header_size": "Tamanho do cabeçalho: {size} bytes",
        "log_total_files": "Total de arquivos: {count}",
        "log_extracting": "[{i}] {filename} | Offset: {offset} | Tamanho: {size}",
        "log_extraction_finished": "Extração finalizada!",
        "extraction_success": "Sucesso! Arquivos salvos em: {folder}",
        "unexpected_error": "Erro inesperado: {error}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}..."
    },
    "en_US": {
        "plugin_name": "DAT+HD2 Extractor (Dark Cloud PS2)",
        "plugin_description": "Extracts files from PS2 games using .hd2 + .dat pairs (Dark Cloud)",
        "extract_command": "Extract DAT+HD2",
        "select_hd2_file": "Select .hd2 file",
        "error_dat_not_found": "Corresponding DAT file not found: {path}",
        "error_hd2_invalid": "Invalid HD2 file (insufficient size).",
        "log_header_size": "Header size: {size} bytes",
        "log_total_files": "Total files: {count}",
        "log_extracting": "[{i}] {filename} | Offset: {offset} | Size: {size}",
        "log_extraction_finished": "Extraction finished!",
        "extraction_success": "Success! Files saved to: {folder}",
        "unexpected_error": "Unexpected error: {error}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}..."
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

# Estado interno do plugin
state = {
    "logger": None,
    "lang": "pt_BR",
    "picker": None
}

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(state["lang"], PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# LÓGICA DE EXTRAÇÃO (BACKEND)
# ==============================================================================

def read_null_terminated_string(file, offset):
    current_pos = file.tell()
    file.seek(offset)
    name_bytes = bytearray()
    while True:
        b = file.read(1)
        if not b or b == b"\x00":
            break
        name_bytes += b
    file.seek(current_pos)
    return name_bytes.decode("shift-jis", errors="ignore")

def run_extraction(hd2_path):
    base_dir = os.path.dirname(hd2_path)
    base_name = os.path.splitext(os.path.basename(hd2_path))[0]
    dat_path = os.path.join(base_dir, base_name + ".dat")

    if not os.path.isfile(dat_path):
        state["logger"](t("error_dat_not_found", path=dat_path), color=COLOR_LOG_RED)
        return

    output_folder = os.path.join(base_dir, base_name)
    os.makedirs(output_folder, exist_ok=True)
    
    log_buffer = []  # Buffer para acumular mensagens
    last_update = time.time()

    def flush_logs(force=False):
        nonlocal last_update
        # Só atualiza a UI se houver mensagens e se passou 0.1s ou se for o fim
        if log_buffer and (time.time() - last_update > 0.1 or force):
            state["logger"]("\n".join(log_buffer))
            log_buffer.clear()
            last_update = time.time()

    try:
        with open(hd2_path, "rb") as hd2:
            header_size_bytes = hd2.read(4)
            if len(header_size_bytes) < 4:
                state["logger"](t("error_hd2_invalid"), color=COLOR_LOG_RED)
                return

            header_size = struct.unpack("<I", header_size_bytes)[0]
            state["logger"](t("log_header_size", size=header_size), color=COLOR_LOG_YELLOW)

            hd2.seek(0)
            total_entries = header_size // 32
            state["logger"](t("log_total_files", count=total_entries), color=COLOR_LOG_YELLOW)

            with open(dat_path, "rb") as dat:
                for i in range(total_entries):
                    entry_data = hd2.read(32)
                    if len(entry_data) < 32: break

                    name_offset = struct.unpack("<I", entry_data[0:4])[0]
                    offset = struct.unpack("<I", entry_data[16:20])[0]
                    size = struct.unpack("<I", entry_data[20:24])[0]

                    filename = read_null_terminated_string(hd2, name_offset)
                    # EM VEZ DE CHAMAR O LOGGER DIRETO:
                    msg = t("log_extracting", i=i, filename=filename, offset=offset, size=size)
                    log_buffer.append(msg)
                    
                    # Tenta descarregar o log sem travar a extração
                    if i % 50 == 0: # Checa a cada 50 arquivos para economizar CPU
                        flush_logs()

                    if size > 0:
                        dat.seek(offset)
                        file_data = dat.read(size)
                        out_path = os.path.join(output_folder, filename)
                        os.makedirs(os.path.dirname(out_path), exist_ok=True)
                        with open(out_path, "wb") as f: f.write(file_data)

        log_buffer.append(t("log_extraction_finished"))
        flush_logs(force=True) # Garante que tudo que sobrou apareça
    except Exception as e:
        state["logger"](t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# INTERFACE E EVENTOS (FLET NATIVO)
# ==============================================================================

def on_file_result(e: ft.FilePickerResultEvent):
    if not e.files:
        state["logger"](t("cancelled"), color=COLOR_LOG_YELLOW)
        return
    
    file_path = e.files[0].path
    state["logger"](t("processing", name=os.path.basename(file_path)), color=COLOR_LOG_YELLOW)
    run_extraction(file_path)

def register_plugin(log_func, option_getter, host_language="pt_BR", page: ft.Page = None):
    state["logger"] = log_func
    state["lang"] = host_language

    # Se o Manager passou a página, configuramos o seletor nativo
    if page:
        # Verifica se já existe um picker para este plugin na página para evitar duplicatas
        picker = ft.FilePicker(on_result=on_file_result)
        page.overlay.append(picker)
        page.update()
        state["picker"] = picker

    def trigger_picker():
        if state["picker"]:
            state["picker"].pick_files(
                dialog_title=t("select_hd2_file"),
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["hd2"]
            )
        else:
            state["logger"]("Erro: FilePicker não inicializado.", color=COLOR_LOG_RED)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_command"), "action": trigger_picker},
        ]
    }