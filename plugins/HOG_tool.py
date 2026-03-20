import os
import struct
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "HOG Meet The Robinsons (PS2)",
        "plugin_description": "Extrai e recria arquivos HOG do jogo Meet The Robinsons (PS2)",
        "extract_file": "Extrair .HOG",
        "rebuild_file": "Remontar .HOG",
        "invalid_file_magic": "Arquivo inválido: Magic incorreto (esperado 01 00 02 00).",
        "extracting": "Extraindo: {file}",
        "completed": "Concluído",
        "extraction_completed": "Extração de {count} arquivos concluída em: {path}",
        "insertion_completed": "Remontagem concluída com sucesso.",
        "file_not_found": "Arquivo não encontrado: {file}",
        "unexpected_error": "Ocorreu um erro inesperado: {error}",
        "select_hog_file": "Selecione um arquivo HOG",
        "hog_files": "Arquivos HOG",
        "all_files": "Todos os arquivos",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída.",
        "extracting_to": "Extraindo para: {path}",
        "recreating_to": "Remontando a partir de: {path}"
    },
    "en_US": {
        "plugin_name": "HOG Meet The Robinsons (PS2)",
        "plugin_description": "Extracts and rebuilds HOG files from Meet The Robinsons (PS2)",
        "extract_file": "Extract .HOG",
        "rebuild_file": "Rebuild .HOG",
        "invalid_file_magic": "Invalid file: Incorrect magic (expected 01 00 02 00).",
        "extracting": "Extracting: {file}",
        "completed": "Completed",
        "extraction_completed": "Extraction of {count} files completed in: {path}",
        "insertion_completed": "Rebuild completed successfully.",
        "file_not_found": "File not found: {file}",
        "unexpected_error": "An unexpected error occurred: {error}",
        "select_hog_file": "Select a HOG file",
        "hog_files": "HOG files",
        "all_files": "All files",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed.",
        "extracting_to": "Extracting to: {path}",
        "recreating_to": "Rebuilding from: {path}"
    },
    "es_ES": {
        "plugin_name": "HOG Meet The Robinsons (PS2)",
        "plugin_description": "Extrae y reconstruye archivos HOG del juego Meet The Robinsons (PS2)",
        "extract_file": "Extraer .HOG",
        "rebuild_file": "Reconstruir .HOG",
        "invalid_file_magic": "Archivo inválido: Magic incorrecto (se esperaba 01 00 02 00).",
        "extracting": "Extrayendo: {file}",
        "completed": "Completado",
        "extraction_completed": "Extracción de {count} archivos completada en: {path}",
        "insertion_completed": "Reconstrucción completada con éxito.",
        "file_not_found": "Archivo no encontrado: {file}",
        "unexpected_error": "Ocurrió un error inesperado: {error}",
        "select_hog_file": "Seleccionar un archivo HOG",
        "hog_files": "Archivos HOG",
        "all_files": "Todos los archivos",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "operation_completed": "Operación completada.",
        "extracting_to": "Extrayendo a: {path}",
        "recreating_to": "Reconstruyendo desde: {path}"
    }
}


# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================
COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

logger = None
current_lang = "pt_BR"

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# LÓGICA HOG (BACKEND)
# ==============================================================================

def run_extraction(filepath):
    try:
        path = Path(filepath)
        logger(t("processing", name=path.name), color=COLOR_LOG_YELLOW)
        
        with path.open("rb") as f:
            if f.read(4) != b"\x01\x00\x02\x00":
                raise ValueError(t("invalid_magic"))

            header_start = struct.unpack("<I", f.read(4))[0]
            f.seek(8, 1)
            total_files = struct.unpack("<I", f.read(4))[0]
            f.seek(header_start)

            entries = []
            for _ in range(total_files):
                filename_pos = struct.unpack("<I", f.read(4))[0]
                pos = struct.unpack("<I", f.read(4))[0]
                size = struct.unpack("<I", f.read(4))[0]
                f.seek(4, 1)
                entries.append((filename_pos, pos, size))

            out_dir = path.parent / path.stem
            out_dir.mkdir(exist_ok=True)

            for filename_pos, pos, size in entries:
                f.seek(filename_pos)
                name_bytes = bytearray()
                while (b := f.read(1)) != b"\x00" and b:
                    name_bytes.extend(b)
                filename = name_bytes.decode("utf-8", errors="ignore")

                f.seek(pos)
                data = f.read(size)

                target = out_dir / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

        logger(t("extraction_success", count=total_files, path=out_dir.name), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("error", error=str(e)), color=COLOR_LOG_RED)

def run_rebuild(filepath):
    try:
        path = Path(filepath)
        folder = path.parent / path.stem
        
        if not folder.is_dir():
            logger(t("file_not_found", file=folder.name), color=COLOR_LOG_RED)
            return

        logger(t("processing", name=path.name), color=COLOR_LOG_YELLOW)

        with path.open("r+b") as f:
            f.seek(4)
            header_start = struct.unpack("<I", f.read(4))[0]
            f.seek(16)
            total_files = struct.unpack("<I", f.read(4))[0]

            # Coletar nomes originais para manter a ordem do HOG
            f.seek(header_start)
            entries_info = []
            for _ in range(total_files):
                filename_pos = struct.unpack("<I", f.read(4))[0]
                f.seek(12, 1)
                entries_info.append(filename_pos)

            filenames = []
            for pos in entries_info:
                f.seek(pos)
                name_bytes = bytearray()
                while (b := f.read(1)) != b"\x00" and b:
                    name_bytes.extend(b)
                filenames.append(name_bytes.decode("utf-8", errors="ignore"))

            # Determinar início da escrita de dados (após o primeiro arquivo original)
            f.seek(header_start + 4)
            first_data_pos = struct.unpack("<I", f.read(4))[0]
            f.seek(first_data_pos)

            new_params = []
            for name in filenames:
                src = folder / name
                if not src.is_file():
                    logger(t("file_not_found", file=name), color=COLOR_LOG_YELLOW)
                    continue

                data = src.read_bytes()
                new_size = len(data)
                new_pos = f.tell()
                
                f.write(data)
                
                # Alinhamento PS2 (2048 bytes)
                pad = (2048 - (new_size % 2048)) % 2048
                if pad > 0: f.write(b"\x00" * pad)
                
                new_params.append((new_size, new_pos))

            f.truncate()
            
            # Atualizar Tabela de Cabeçalho
            f.seek(header_start)
            for size, pos in new_params:
                f.seek(4, 1) # pula filename_pos
                f.write(struct.pack("<I", pos))
                f.write(struct.pack("<I", size))
                f.seek(4, 1) # pula padding/unknown

        logger(t("insertion_success"), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# REGISTRO DO PLUGIN (FLET)
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR"):
    global logger, current_lang
    logger = log_func
    current_lang = host_language

    def on_extract_res(e: ft.FilePickerResultEvent):
        if e.files:
            for f in e.files: run_extraction(f.path)
        else: logger(t("cancelled"), color=COLOR_LOG_YELLOW)

    def on_rebuild_res(e: ft.FilePickerResultEvent):
        if e.files:
            for f in e.files: run_rebuild(f.path)
        else: logger(t("cancelled"), color=COLOR_LOG_YELLOW)

    fp_extract = ft.FilePicker(on_result=on_extract_res)
    fp_rebuild = ft.FilePicker(on_result=on_rebuild_res)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "pickers": [fp_extract, fp_rebuild],
        "commands": [
            {
                "label": t("extract_file"), 
                "action": lambda: fp_extract.pick_files(
                    allow_multiple=True, 
                    allowed_extensions=["hog"]
                )
            },
            {
                "label": t("rebuild_file"), 
                "action": lambda: fp_rebuild.pick_files(
                    allow_multiple=True, 
                    allowed_extensions=["hog"]
                )
            },
        ]
    }