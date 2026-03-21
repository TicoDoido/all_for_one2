import os
import struct
import json
from pathlib import Path
import flet as ft

# Importa unlzss diretamente (assumindo que o módulo está acessível)
try:
    from plugins.DECOMP_CODE.lzss_codec import unlzss
except ModuleNotFoundError:
    from DECOMP_CODE.lzss_codec import unlzss

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "BIN Corpse Party Extrator",
        "plugin_description": "Extrai arquivos de image.bin (formato PACK do PSP)",
        "extract_file": "Extrair image.bin (PACK)",
        "select_image_file": "Selecione o image.bin (PACK)",
        "image_bin": "image.bin",
        "all_files": "Todos os arquivos",

        "log_detected_magic": "Magic detectado: {magic} no offset {offset}",
        "log_invalid_magic": "Magic inválido (esperado 'PACK') — abortando.",
        "error_invalid_magic": "Arquivo não é um PACK válido",
        "log_read_count": "Total de arquivos: {count}",
        "log_entry_found": "Entrada {i} encontrada em {entry_pos}: name='{name}' offset={offset} size={size}",
        "log_extracting": "Extraindo: {name} (offset={offset}, size={size})",
        "log_lzss_detected": "Arquivo {name} detectado como LZSS — descompactando.",
        "log_saved": "Arquivo salvo em: {path}",
        "log_json_written": "JSON salvo em: {json_path}",
        "log_extracted_folder": "Arquivos extraídos em: {folder}",

        "msg_title_error": "Erro",
        "msg_title_done": "Concluído",
        "err_file_not_found": "Arquivo não encontrado: {path}",
        "err_unexpected": "Erro inesperado: {error}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "BIN Corpse Party Extractor",
        "plugin_description": "Extract files from image.bin (PSP PACK format)",
        "extract_file": "Extract image.bin (PACK)",
        "select_image_file": "Select image.bin (PACK)",
        "image_bin": "image.bin",
        "all_files": "All files",

        "log_detected_magic": "Detected magic: {magic} at offset {offset}",
        "log_invalid_magic": "Invalid magic (expected 'PACK') — aborting.",
        "error_invalid_magic": "File is not a valid PACK",
        "log_read_count": "Total files: {count}",
        "log_entry_found": "Entry {i} at {entry_pos}: name='{name}' offset={offset} size={size}",
        "log_extracting": "Extracting: {name} (offset={offset}, size={size})",
        "log_lzss_detected": "File {name} detected as LZSS — decompressing.",
        "log_saved": "File saved to: {path}",
        "log_json_written": "JSON saved at: {json_path}",
        "log_extracted_folder": "Files extracted to: {folder}",

        "msg_title_error": "Error",
        "msg_title_done": "Done",
        "err_file_not_found": "File not found: {path}",
        "err_unexpected": "Unexpected error: {error}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "BIN Corpse Party Extractor",
        "plugin_description": "Extrae archivos de image.bin (formato PACK PSP)",
        "extract_file": "Extraer image.bin (PACK)",
        "select_image_file": "Seleccionar image.bin (PACK)",
        "image_bin": "image.bin",
        "all_files": "Todos los archivos",

        "log_detected_magic": "Magic detectado: {magic} en offset {offset}",
        "log_invalid_magic": "Magic inválido (se esperaba 'PACK') — abortando.",
        "error_invalid_magic": "El archivo no es un PACK válido",
        "log_read_count": "Total de archivos: {count}",
        "log_entry_found": "Entrada {i} en {entry_pos}: name='{name}' offset={offset} size={size}",
        "log_extracting": "Extrayendo: {name} (offset={offset}, size={size})",
        "log_lzss_detected": "Archivo {name} detectado como LZSS — descomprimiendo.",
        "log_saved": "Archivo guardado en: {path}",
        "log_json_written": "JSON guardado en: {json_path}",
        "log_extracted_folder": "Archivos extraídos en: {folder}",

        "msg_title_error": "Error",
        "msg_title_done": "Completado",
        "err_file_not_found": "Archivo no encontrado: {path}",
        "err_unexpected": "Error inesperado: {error}",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "operation_completed": "Operación completada."
    }
}

# Cores usadas no All For One
COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

# Variáveis globais injetadas pelo sistema
logger = None
get_option = None
current_lang = "pt_BR"
host_page = None

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FilePicker global
# ==============================================================================

fp_extract = ft.FilePicker(
    on_result=lambda e: _extract_pack(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# FUNÇÃO PRINCIPAL DE EXTRAÇÃO (ADAPTADA PARA USAR PATH E LOGGER)
# ==============================================================================
def _extract_pack(filepath: Path):
    try:
        if not filepath.exists():
            logger(t("err_file_not_found", path=str(filepath)), color=COLOR_LOG_RED)
            return

        with open(filepath, "rb") as f:
            magic_offset = f.tell()
            magic = f.read(4)
            magic_str = magic.decode("ascii", errors="ignore")
            logger(t("log_detected_magic", magic=magic_str, offset=magic_offset), color=COLOR_LOG_YELLOW)

            if magic != b"PACK":
                logger(t("log_invalid_magic"), color=COLOR_LOG_RED)
                raise ValueError(t("error_invalid_magic"))

            total_files = struct.unpack("<I", f.read(4))[0]
            _ = f.read(4)  # CRC ignorado
            logger(t("log_read_count", count=total_files), color=COLOR_LOG_YELLOW)

            entries = []
            for i in range(total_files):
                entry_pos = f.tell()
                _ = f.read(8)  # CRC-like
                offset = struct.unpack("<I", f.read(4))[0]
                size = struct.unpack("<I", f.read(4))[0]
                name_bytes = f.read(128)
                name = name_bytes.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
                if not name:
                    name = name_bytes.split(b"\x00", 1)[0].decode("cp1252", errors="ignore")
                if not name:
                    name = f"file_{i:05d}.bin"

                logger(t("log_entry_found", i=i, entry_pos=entry_pos, name=name, offset=offset, size=size), color=COLOR_LOG_YELLOW)

                entries.append({"ENTRY_OFF": entry_pos, "NAME": name, "OFFSET": offset, "SIZE": size})

        # Pasta de saída
        base_dir = filepath.parent
        base_name = filepath.stem
        extracted_dir = base_dir / f"{base_name}_extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)

        logger(t("extracting_to", path=str(extracted_dir)), color=COLOR_LOG_YELLOW)

        with open(filepath, "rb") as f:
            for e in entries:
                f.seek(e["OFFSET"])
                data = f.read(e["SIZE"])
                logger(t("log_extracting", name=e["NAME"], offset=e["OFFSET"], size=e["SIZE"]), color=COLOR_LOG_YELLOW)

                out_path = extracted_dir / e["NAME"]
                out_path.parent.mkdir(parents=True, exist_ok=True)

                # Se for LZSS, tenta descomprimir
                if data.startswith(b"LZSS"):
                    logger(t("log_lzss_detected", name=e["NAME"]), color=COLOR_LOG_YELLOW)
                    try:
                        expected_size = struct.unpack("<I", data[4:8])[0] if len(data) >= 8 else 0
                        decomp = unlzss(data[8:])
                        with open(out_path, "wb") as df:
                            df.write(decomp)
                        logger(t("log_saved", path=str(out_path)), color=COLOR_LOG_GREEN)
                        if expected_size and len(decomp) != expected_size:
                            logger(f"[WARN] tamanho esperado={expected_size}, obtido={len(decomp)}", color=COLOR_LOG_YELLOW)
                        continue  # não salvar raw se já descompactou
                    except Exception as dex:
                        logger(t("err_unexpected", error=str(dex)), color=COLOR_LOG_RED)

                # Salvar raw
                with open(out_path, "wb") as fout:
                    fout.write(data)
                logger(t("log_saved", path=str(out_path)), color=COLOR_LOG_GREEN)

        # JSON com metadados
        json_path = base_dir / f"{base_name}.json"
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(entries, jf, indent=4, ensure_ascii=False)

        logger(t("log_json_written", json_path=str(json_path)), color=COLOR_LOG_GREEN)
        logger(t("log_extracted_folder", folder=str(extracted_dir)), color=COLOR_LOG_GREEN)

        return extracted_dir, json_path

    except Exception as e_all:
        logger(t("err_unexpected", error=str(e_all)), color=COLOR_LOG_RED)
        return None, None

# ==============================================================================
# AÇÃO DO COMANDO (CHAMA O FILEPICKER)
# ==============================================================================
def action_extract():
    fp_extract.pick_files(
        allowed_extensions=["bin"],
        dialog_title=t("select_image_file")
    )

# ==============================================================================
# ENTRY POINT (REGISTRO)
# ==============================================================================
def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, get_option, current_lang, host_page
    logger = log_func
    get_option = option_getter
    current_lang = host_language
    host_page = page

    if host_page:
        host_page.overlay.append(fp_extract)
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_file"), "action": action_extract},
        ]
    }
