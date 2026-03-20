import os
import struct
import json
import flet as ft
from pathlib import Path

# Tenta importar o unlzss conforme a estrutura de pastas do seu projeto
try:
    from plugins.DECOMP_CODE.lzss_codec import unlzss
except ModuleNotFoundError:
    try:
        from DECOMP_CODE.lzss_codec import unlzss
    except ImportError:
        unlzss = None # Fallback caso o arquivo não exista no ambiente

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "BIN Corpse Party Extrator",
        "plugin_description": "Extrai arquivos de image.bin (formato PACK do PSP)",
        "extract_file": "Extrair image.bin (PACK)",
        "select_image_file": "Selecione o image.bin (PACK)",
        "log_detected_magic": "Magic detectado: {magic} no offset {offset}",
        "log_invalid_magic": "Magic inválido (esperado 'PACK') — abortando.",
        "log_read_count": "Total de arquivos: {count}",
        "log_entry_found": "Entrada {i}: {name} | Offset: {offset} | Size: {size}",
        "log_extracting": "Extraindo: {name}...",
        "log_lzss_detected": "Arquivo {name} detectado como LZSS — descompactando.",
        "log_saved": "Salvo: {path}",
        "log_json_written": "JSON de metadados salvo: {json_path}",
        "err_file_not_found": "Arquivo não encontrado: {path}",
        "err_unexpected": "Erro: {error}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
    },
    "en_US": {
        "plugin_name": "BIN Corpse Party Extractor",
        "plugin_description": "Extract files from image.bin (PSP PACK format)",
        "extract_file": "Extract image.bin (PACK)",
        "select_image_file": "Select image.bin (PACK)",
        "log_detected_magic": "Detected magic: {magic} at offset {offset}",
        "log_invalid_magic": "Invalid magic (expected 'PACK') — aborting.",
        "log_read_count": "Total files: {count}",
        "log_entry_found": "Entry {i}: {name} | Offset: {offset} | Size: {size}",
        "log_extracting": "Extracting: {name}...",
        "log_lzss_detected": "File {name} detected as LZSS — decompressing.",
        "log_saved": "Saved: {path}",
        "log_json_written": "Metadata JSON saved: {json_path}",
        "err_file_not_found": "File not found: {path}",
        "err_unexpected": "Error: {error}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

logger = None
current_lang = "pt_BR"
host_page = None

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# LÓGICA DE EXTRAÇÃO
# ==============================================================================

def extract_pack(filepath):
    try:
        if not filepath or not os.path.exists(filepath):
            if logger: logger(t("err_file_not_found", path=filepath), color=COLOR_LOG_RED)
            return

        with open(filepath, "rb") as f:
            magic = f.read(4)
            if magic != b"PACK":
                if logger: logger(t("log_invalid_magic"), color=COLOR_LOG_RED)
                return

            total_files = struct.unpack("<I", f.read(4))[0]
            f.read(4) # Skip CRC
            if logger: logger(t("log_read_count", count=total_files), color=COLOR_LOG_YELLOW)

            entries = []
            for i in range(total_files):
                f.read(8) # CRC entry
                offset = struct.unpack("<I", f.read(4))[0]
                size = struct.unpack("<I", f.read(4))[0]
                name_bytes = f.read(128)
                name = name_bytes.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
                if not name: name = f"file_{i:05d}.bin"
                
                entries.append({"NAME": name, "OFFSET": offset, "SIZE": size})

        # Preparar pastas
        base_path = Path(filepath)
        out_dir = base_path.parent / f"{base_path.stem}_extracted"
        out_dir.mkdir(exist_ok=True)

        with open(filepath, "rb") as f:
            for e in entries:
                if logger: logger(t("log_extracting", name=e["NAME"]), color=COLOR_LOG_YELLOW)
                f.seek(e["OFFSET"])
                data = f.read(e["SIZE"])

                target_file = out_dir / e["NAME"]
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # Lógica LZSS
                if data.startswith(b"LZSS") and unlzss:
                    if logger: logger(t("log_lzss_detected", name=e["NAME"]), color=COLOR_LOG_YELLOW)
                    try:
                        decomp = unlzss(data[8:])
                        target_file.write_bytes(decomp)
                        if logger: logger(t("log_saved", path=e["NAME"]), color=COLOR_LOG_GREEN)
                        continue
                    except:
                        pass # Se falhar, salva o raw abaixo

                target_file.write_bytes(data)
                if logger: logger(t("log_saved", path=e["NAME"]), color=COLOR_LOG_GREEN)

        # Salvar JSON de metadados para futura reconstrução
        json_path = base_path.with_suffix(".json")
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(entries, jf, indent=4, ensure_ascii=False)
        
        if logger: 
            logger(t("log_json_written", json_path=json_path.name), color=COLOR_LOG_GREEN)
            logger(t("operation_completed"), color=COLOR_LOG_GREEN)

    except Exception as e:
        if logger: logger(t("err_unexpected", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# FLET FILE PICKER
# ==============================================================================

fp_pack = ft.FilePicker(
    on_result=lambda e: extract_pack(e.files[0].path) if e.files else None
)

# ==============================================================================
# REGISTRO
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, current_lang, host_page
    logger = log_func
    current_lang = host_language
    host_page = page

    if host_page:
        host_page.overlay.append(fp_pack)
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {
                "label": t("extract_file"), 
                "action": lambda: fp_pack.pick_files(
                    allowed_extensions=["bin"],
                    dialog_title=t("select_image_file")
                )
            },
        ]
    }