import os
import struct
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "VIV - Extrator e Reconstrutor (Medal of Honor - Frontline)",
        "plugin_description": "Extrai e reconstrói arquivos .viv (Medal of Honor - Frontline)",
        "extract_file": "Extrair Arquivo",
        "rebuild_file": "Reconstruir Arquivo",
        "select_viv_file": "Selecione o arquivo .viv",
        "viv_files": "Arquivos VIV",
        "all_files": "Todos os arquivos",
        "extraction_success": "Extração concluída com sucesso! Arquivos extraídos para: {path}",
        "rebuild_success": "Reconstrução concluída no arquivo original: {path}",
        "invalid_magic": "Arquivo inválido: magic não reconhecida (esperado 0xC0 0xFB)",
        "extracted_folder_not_found": "Pasta extraída não encontrada: {folder}",
        "file_not_found": "Arquivo não encontrado: {name}",
        "unexpected_error": "Erro inesperado: {error}",
        "extracting_to": "Extraindo para: {path}",
        "recreating_to": "Reconstruindo: {path}",
        "completed": "Concluído",
        "error": "Erro",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída.",
        "progress_status": "{percent}% - {current}/{total} arquivos"
    },
    "en_US": {
        "plugin_name": "VIV - Extractor and Rebuilder (Medal of Honor - Frontline)",
        "plugin_description": "Extracts and rebuilds .viv files (Medal of Honor - Frontline)",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild File",
        "select_viv_file": "Select .viv file",
        "viv_files": "VIV Files",
        "all_files": "All files",
        "extraction_success": "Extraction completed successfully! Files extracted to: {path}",
        "rebuild_success": "Rebuild completed on original file: {path}",
        "invalid_magic": "Invalid file: magic not recognized (expected 0xC0 0xFB)",
        "extracted_folder_not_found": "Extracted folder not found: {folder}",
        "file_not_found": "File not found: {name}",
        "unexpected_error": "Unexpected error: {error}",
        "extracting_to": "Extracting to: {path}",
        "recreating_to": "Rebuilding: {path}",
        "completed": "Completed",
        "error": "Error",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed.",
        "progress_status": "{percent}% - {current}/{total} files"
    },
    "es_ES": {
        "plugin_name": "VIV - Extractor y Reconstructor (Medal of Honor - Frontline)",
        "plugin_description": "Extrae y reconstruye archivos .viv (Medal of Honor - Frontline)",
        "extract_file": "Extraer Archivo",
        "rebuild_file": "Reconstruir Archivo",
        "select_viv_file": "Seleccionar archivo .viv",
        "viv_files": "Archivos VIV",
        "all_files": "Todos los archivos",
        "extraction_success": "¡Extracción completada con éxito! Archivos extraídos en: {path}",
        "rebuild_success": "Reconstrucción completada en el archivo original: {path}",
        "invalid_magic": "Archivo inválido: magic no reconocida (se esperaba 0xC0 0xFB)",
        "extracted_folder_not_found": "Carpeta extraída no encontrada: {folder}",
        "file_not_found": "Archivo no encontrado: {name}",
        "unexpected_error": "Error inesperado: {error}",
        "extracting_to": "Extrayendo a: {path}",
        "recreating_to": "Reconstruyendo: {path}",
        "completed": "Completado",
        "error": "Error",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "operation_completed": "Operación completada.",
        "progress_status": "{percent}% - {current}/{total} archivos"
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
# FilePickers globais
# ==============================================================================

fp_extract = ft.FilePicker(
    on_result=lambda e: _extract_viv(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)
fp_rebuild = ft.FilePicker(
    on_result=lambda e: _rebuild_viv(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
ALIGNMENT = 64

def align64(value):
    return (value + (ALIGNMENT - 1)) & ~(ALIGNMENT - 1)

def read_u16_be(f):
    return struct.unpack('>H', f.read(2))[0]

def read_3byte_be_int(f):
    return int.from_bytes(f.read(3), 'big')

def write_3byte_be_int(value):
    return value.to_bytes(3, 'big')

def read_cstring(f):
    pieces = []
    while True:
        b = f.read(1)
        if not b or b == b'\x00':
            break
        pieces.append(b)
    return b''.join(pieces)

# ==============================================================================
# FUNÇÕES PRINCIPAIS
# ==============================================================================
def _extract_viv(path: Path):
    """Extrai arquivos do arquivo .viv."""
    logger(t("processing", name=path.name), color=COLOR_LOG_YELLOW)

    with open(path, 'rb') as f:
        magic = f.read(2)
        if magic != b'\xC0\xFB':
            raise ValueError(t("invalid_magic"))

        header_size = read_u16_be(f)
        total_files = read_u16_be(f)

        entries = []
        for _ in range(total_files):
            offset = read_3byte_be_int(f)
            size = read_3byte_be_int(f)
            name = read_cstring(f).decode('utf-8', errors='ignore')
            entries.append({'offset': offset, 'size': size, 'name': name})

        base_dir = path.parent
        base_name = path.stem
        out_dir = base_dir / base_name
        out_dir.mkdir(parents=True, exist_ok=True)

        logger(t("extracting_to", path=str(out_dir)), color=COLOR_LOG_YELLOW)

        for i, e in enumerate(entries):
            f.seek(e['offset'])
            data = f.read(e['size'])

            out_path = out_dir / e['name']
            out_path.parent.mkdir(parents=True, exist_ok=True)

            with open(out_path, 'wb') as out_f:
                out_f.write(data)

            percent = int((i + 1) / total_files * 100)
            logger(t("progress_status", percent=percent, current=i+1, total=total_files), color=COLOR_LOG_YELLOW)

        logger(t("extraction_success", path=str(out_dir)), color=COLOR_LOG_GREEN)
        return out_dir


def _rebuild_viv(original_path: Path):
    """Reconstroi o arquivo .viv a partir da pasta extraída."""
    logger(t("processing", name=original_path.name), color=COLOR_LOG_YELLOW)

    base_dir = original_path.parent
    base_name = original_path.stem
    extracted_folder = base_dir / base_name

    if not extracted_folder.is_dir():
        raise FileNotFoundError(t("extracted_folder_not_found", folder=str(extracted_folder)))

    with open(original_path, 'r+b') as f:
        magic = f.read(2)
        if magic != b'\xC0\xFB':
            raise ValueError(t("invalid_magic"))

        header_size = read_u16_be(f)
        total_files = read_u16_be(f)

        header_start = f.tell()

        entries = []
        for _ in range(total_files):
            entry_pos = f.tell()
            offset = read_3byte_be_int(f)
            size = read_3byte_be_int(f)
            name = read_cstring(f).decode('utf-8', errors='ignore')
            entries.append({"entry_pos": entry_pos, "name": name})

        current_offset = align64(header_size)
        updated_entries = []

        logger(t("recreating_to", path=str(original_path)), color=COLOR_LOG_YELLOW)

        for i, e in enumerate(entries):
            name = e["name"]
            file_path = extracted_folder / name

            if not file_path.is_file():
                raise FileNotFoundError(t("file_not_found", name=name))

            with open(file_path, 'rb') as file_f:
                data = file_f.read()

            size = len(data)

            f.seek(current_offset)
            f.write(data)

            pad_size = align64(size) - size
            if pad_size > 0:
                f.write(b'\x00' * pad_size)

            updated_entries.append({
                "entry_pos": e["entry_pos"],
                "offset": current_offset,
                "size": size
            })

            current_offset = align64(current_offset + size)

            percent = int((i + 1) / total_files * 100)
            logger(t("progress_status", percent=percent, current=i+1, total=total_files), color=COLOR_LOG_YELLOW)

        for e in updated_entries:
            f.seek(e["entry_pos"])
            f.write(write_3byte_be_int(e["offset"]))
            f.write(write_3byte_be_int(e["size"]))

    logger(t("rebuild_success", path=str(original_path)), color=COLOR_LOG_GREEN)


# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================
def action_extract():
    fp_extract.pick_files(
        allowed_extensions=["viv"],
        dialog_title=t("select_viv_file")
    )

def action_rebuild():
    fp_rebuild.pick_files(
        allowed_extensions=["viv"],
        dialog_title=t("select_viv_file")
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
        host_page.overlay.extend([fp_extract, fp_rebuild])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_file"), "action": action_extract},
            {"label": t("rebuild_file"), "action": action_rebuild},
        ]
    }