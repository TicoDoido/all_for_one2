import os
import struct
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

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

# Cores usadas no All For One
COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

# Variáveis globais injetadas pelo sistema
logger = None
get_option = None
current_lang = "pt_BR"

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FUNÇÕES PARA CORRIGIR A JANELA (TOPMOST)
# ==============================================================================
def pick_file_topmost(title, file_types):
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    file_path = filedialog.askopenfilename(parent=root, title=title, filetypes=file_types)
    root.destroy()
    return file_path

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA USAR LOGGER)
# ==============================================================================

def extract_hog(filepath):
    entradas = []
    with open(filepath, "rb") as f:
        magic = f.read(4)
        if magic != b"\x01\x00\x02\x00":
            raise ValueError(t("invalid_file_magic"))

        header_start = struct.unpack("<I", f.read(4))[0]
        f.seek(8, 1)
        total_files = struct.unpack("<I", f.read(4))[0]
        f.seek(header_start)

        for _ in range(total_files):
            filename_pos = struct.unpack("<I", f.read(4))[0]
            pos = struct.unpack("<I", f.read(4))[0]
            size = struct.unpack("<I", f.read(4))[0]
            f.seek(4, 1)
            entradas.append((filename_pos, pos, size))

        out_dir = os.path.splitext(filepath)[0]
        os.makedirs(out_dir, exist_ok=True)
        logger(t("extracting_to", path=out_dir), color=COLOR_LOG_YELLOW)

        for filename_pos, pos, size in entradas:
            f.seek(filename_pos)
            name_bytes = bytearray()
            while True:
                b = f.read(1)
                if b == b"\x00" or b == b"":
                    break
                name_bytes.extend(b)
            filename = name_bytes.decode("utf-8", errors="ignore")

            f.seek(pos)
            data = f.read(size)

            out_path = os.path.join(out_dir, filename)
            logger(t("extracting", file=out_path), color=COLOR_LOG_YELLOW)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as out_file:
                out_file.write(data)

    logger(t("extraction_completed", count=total_files, path=out_dir), color=COLOR_LOG_GREEN)


def insert_hog(filepath, folder):
    with open(filepath, "r+b") as f:
        f.seek(0)
        magic = f.read(4)
        f.seek(4)
        header_start = struct.unpack("<I", f.read(4))[0]
        f.seek(16)
        total_files = struct.unpack("<I", f.read(4))[0]

        f.seek(header_start + 4)
        insert_position = struct.unpack("<I", f.read(4))[0]
        f.seek(header_start)

        entradas = []
        for _ in range(total_files):
            filename_pos = struct.unpack("<I", f.read(4))[0]
            f.seek(12, 1)
            entradas.append(filename_pos)

        arquivos = []
        for entry in entradas:
            f.seek(entry)
            name_bytes = bytearray()
            while True:
                b = f.read(1)
                if b == b"\x00" or b == b"":
                    break
                name_bytes.extend(b)
            arquivos.append(name_bytes.decode("utf-8", errors="ignore"))

        f.seek(insert_position)
        novos_parametros = []
        for file_to_insert in arquivos:
            file_path = os.path.join(folder, file_to_insert)
            if not os.path.isfile(file_path):
                logger(t("file_not_found", file=file_to_insert), color=COLOR_LOG_YELLOW)
                continue

            with open(file_path, "rb") as infile:
                data = infile.read()
                new_size = len(data)

            new_pos = f.tell()
            f.write(data)

            pad = ((2048 - (new_size % 2048)) % 2048)
            if pad > 0:
                f.write(b"\x00" * pad)

            novos_parametros.append((new_size, new_pos))

        f.truncate()
        f.seek(header_start)
        for new_size, new_pos in novos_parametros:
            f.seek(4, 1)
            f.write(struct.pack("<I", new_pos))
            f.write(struct.pack("<I", new_size))
            f.seek(4, 1)

    logger(t("insertion_completed"), color=COLOR_LOG_GREEN)


# ==============================================================================
# AÇÕES DOS COMANDOS (SEM THREADING)
# ==============================================================================

def action_extract():
    path = pick_file_topmost(t("select_hog_file"), [(t("hog_files"), "*.hog"), (t("all_files"), "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
    try:
        extract_hog(path)
    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)


def action_rebuild():
    path = pick_file_topmost(t("select_hog_file"), [(t("hog_files"), "*.hog"), (t("all_files"), "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    # pasta de extração é o nome do arquivo sem extensão
    pasta = os.path.splitext(path)[0]
    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
    logger(t("recreating_to", path=pasta), color=COLOR_LOG_YELLOW)

    try:
        insert_hog(path, pasta)
    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)


# ==============================================================================
# ENTRY POINT (REGISTRO)
# ==============================================================================
def register_plugin(log_func, option_getter, host_language="pt_BR"):
    global logger, get_option, current_lang
    logger = log_func
    get_option = option_getter
    current_lang = host_language

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_file"), "action": action_extract},
            {"label": t("rebuild_file"), "action": action_rebuild},
        ]
    }