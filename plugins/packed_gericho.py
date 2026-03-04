import os
import struct
import zlib
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "PACKED - Clive Barker's Jericho",
        "plugin_description": "Extrai e reinsere arquivos de containers .packed",
        "extract_container": "Extrair Container",
        "reinsert_files": "Reinserir Arquivos",
        "select_packed_file": "Selecione o arquivo .packed",
        "packed_files": "Arquivos Packed",
        "all_files": "Todos os arquivos",
        "invalid_file": "Arquivo inválido",
        "invalid_packed_file": "Arquivo não é um container .packed válido.",
        "extraction_completed": "Extração concluída! Arquivos salvos em: {path}",
        "reinsertion_completed": "Reinserção concluída com sucesso!",
        "cancelled": "Cancelado",
        "extraction_cancelled": "Extração cancelada pelo usuário",
        "reinsertion_cancelled": "Reinserção cancelada pelo usuário",
        "file_not_found": "Arquivo não encontrado: {file}",
        "dir_not_found": "Diretório não encontrado: {dir}",
        "processing": "Processando: {name}...",
        "extracting_to": "Extraindo para: {path}",
        "file_extracted": "Arquivo extraído: {name}",
        "progress_status": "{percent}% - {current}/{total} arquivos",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "PACKED - Clive Barker's Jericho",
        "plugin_description": "Extracts and reinserts files from .packed containers",
        "extract_container": "Extract Container",
        "reinsert_files": "Reinsert Files",
        "select_packed_file": "Select .packed file",
        "packed_files": "Packed Files",
        "all_files": "All files",
        "invalid_file": "Invalid file",
        "invalid_packed_file": "File is not a valid .packed container.",
        "extraction_completed": "Extraction completed! Files saved to: {path}",
        "reinsertion_completed": "Reinsertion completed successfully!",
        "cancelled": "Cancelled",
        "extraction_cancelled": "Extraction cancelled by user",
        "reinsertion_cancelled": "Reinsertion cancelled by user",
        "file_not_found": "File not found: {file}",
        "dir_not_found": "Directory not found: {dir}",
        "processing": "Processing: {name}...",
        "extracting_to": "Extracting to: {path}",
        "file_extracted": "File extracted: {name}",
        "progress_status": "{percent}% - {current}/{total} files",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "PACKED - Clive Barker's Jericho",
        "plugin_description": "Extrae y reinserta archivos de contenedores .packed",
        "extract_container": "Extraer Contenedor",
        "reinsert_files": "Reinsertar Archivos",
        "select_packed_file": "Seleccionar archivo .packed",
        "packed_files": "Archivos Packed",
        "all_files": "Todos los archivos",
        "invalid_file": "Archivo inválido",
        "invalid_packed_file": "El archivo no es un contenedor .packed válido.",
        "extraction_completed": "¡Extracción completada! Archivos guardados en: {path}",
        "reinsertion_completed": "¡Reinserción completada con éxito!",
        "cancelled": "Cancelado",
        "extraction_cancelled": "Extracción cancelada por el usuario",
        "reinsertion_cancelled": "Reinserción cancelada por el usuario",
        "file_not_found": "Archivo no encontrado: {file}",
        "dir_not_found": "Directorio no encontrado: {dir}",
        "processing": "Procesando: {name}...",
        "extracting_to": "Extrayendo a: {path}",
        "file_extracted": "Archivo extraído: {name}",
        "progress_status": "{percent}% - {current}/{total} archivos",
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

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FUNÇÃO PARA CORRIGIR A JANELA (TOPMOST)
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

def extract_packed_container(container_path):
    base_name = os.path.splitext(os.path.basename(container_path))[0]
    output_dir = os.path.join(os.path.dirname(container_path), base_name)
    os.makedirs(output_dir, exist_ok=True)
    logger(t("extracting_to", path=output_dir), color=COLOR_LOG_YELLOW)

    with open(container_path, 'rb') as f:
        if f.read(4) != b'BFPK':
            raise ValueError(t("invalid_packed_file"))

        version = struct.unpack('<I', f.read(4))[0]
        num_files = struct.unpack('<I', f.read(4))[0]

        for i in range(num_files):
            name_size = struct.unpack('<I', f.read(4))[0]
            name = f.read(name_size).decode('utf-8').replace('/', os.sep)
            decompressed_size = struct.unpack('<I', f.read(4))[0]
            file_offset = struct.unpack('<I', f.read(4))[0]

            current_pos = f.tell()
            f.seek(file_offset)
            compressed_size = struct.unpack('<I', f.read(4))[0]
            compressed_data = f.read(compressed_size)
            f.seek(current_pos)

            output_path = os.path.join(output_dir, name)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            try:
                decompressed_data = zlib.decompress(compressed_data)
            except zlib.error:
                f.seek(file_offset)
                decompressed_data = f.read(compressed_size + 4)

            with open(output_path, 'wb') as out_file:
                out_file.write(decompressed_data)

            percent = int((i + 1) / num_files * 100)
            logger(t("progress_status", percent=percent, current=i+1, total=num_files), color=COLOR_LOG_YELLOW)
            logger(t("file_extracted", name=name), color=COLOR_LOG_GREEN)

    return output_dir

def get_file_list(container_path):
    with open(container_path, 'rb') as f:
        if f.read(4) != b'BFPK':
            raise ValueError(t("invalid_packed_file"))
        f.seek(8)
        num_files = struct.unpack('<I', f.read(4))[0]

        file_list = []
        for _ in range(num_files):
            name_size = struct.unpack('<I', f.read(4))[0]
            name = f.read(name_size).decode('utf-8').replace('/', os.sep)
            f.seek(8, 1)
            file_list.append(name)

        header_end = f.tell()

    return file_list, header_end

def reinsert_files(container_path, input_dir):
    file_list, header_end = get_file_list(container_path)
    total_files = len(file_list)
    temp_path = container_path + ".new"

    with open(container_path, 'rb') as f, open(temp_path, 'w+b') as out:
        out.write(f.read(header_end))
        novos_dados = []

        for i, name in enumerate(file_list):
            input_file = os.path.join(input_dir, name)
            if not os.path.exists(input_file):
                raise FileNotFoundError(t("file_not_found", file=input_file))

            with open(input_file, 'rb') as fin:
                original_data = fin.read()
                compressed_data = zlib.compress(original_data)
                pointer = out.tell()
                out.write(struct.pack('<I', len(compressed_data)))
                out.write(compressed_data)
                novos_dados.append((pointer, len(original_data)))

            percent = int((i + 1) / total_files * 100)
            logger(t("progress_status", percent=percent, current=i+1, total=total_files), color=COLOR_LOG_YELLOW)

        out.seek(12)
        for (pointer, size) in novos_dados:
            name_size = struct.unpack('<I', out.read(4))[0]
            out.seek(name_size, 1)
            out.write(struct.pack('<I', size))
            out.write(struct.pack('<I', pointer))

    os.replace(temp_path, container_path)
    return True

# ==============================================================================
# AÇÕES DOS COMANDOS (SEM THREADING)
# ==============================================================================

def action_extract():
    path = pick_file_topmost(t("select_packed_file"), [(t("packed_files"), "*.packed"), (t("all_files"), "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)

    try:
        # validação rápida para obter número de arquivos (para log de progresso)
        with open(path, 'rb') as f:
            if f.read(4) != b'BFPK':
                raise ValueError(t("invalid_packed_file"))
            f.seek(8)
            num_files = struct.unpack('<I', f.read(4))[0]

        output_dir = extract_packed_container(path)
        logger(t("extraction_completed", path=output_dir), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("invalid_file") + ": " + str(e), color=COLOR_LOG_RED)


def action_reinsert():
    path = pick_file_topmost(t("select_packed_file"), [(t("packed_files"), "*.packed"), (t("all_files"), "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    input_dir = os.path.splitext(path)[0]
    if not os.path.exists(input_dir):
        logger(t("dir_not_found", dir=input_dir), color=COLOR_LOG_RED)
        return

    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)

    try:
        # validação rápida
        file_list, _ = get_file_list(path)
        total_files = len(file_list)

        success = reinsert_files(path, input_dir)
        if success:
            logger(t("reinsertion_completed"), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("invalid_file") + ": " + str(e), color=COLOR_LOG_RED)


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
            {"label": t("extract_container"), "action": action_extract},
            {"label": t("reinsert_files"), "action": action_reinsert},
        ]
    }