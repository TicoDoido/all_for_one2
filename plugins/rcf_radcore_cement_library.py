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
        "plugin_name": "RCF - Radcore Cement Library VER:1.2/2.1",
        "plugin_description": "Extrai e recria arquivos RCF de jogos da Radical Entertainment",
        "extract_file": "Extrair Arquivo",
        "rebuild_file": "Recriar Arquivo",
        "select_rcf_file": "Selecione o arquivo .rcf",
        "select_txt_file": "Selecione o arquivo .txt",
        "rcf_files": "Arquivos RCF",
        "text_files": "Arquivos de Texto",
        "all_files": "Todos os arquivos",
        "unsupported_file": "Arquivo não suportado!",
        "extraction_completed": "Arquivos extraídos com sucesso para: {path}",
        "recreation_completed": "Novo arquivo RCF criado em: {path}",
        "folder_not_found": "Pasta não encontrada: {folder}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "error_creating_dir": "Erro ao criar diretório: {error}",
        "version_21_le": "Versão é 2.1 MODO LITTLE ENDIAN",
        "version_21_be": "Versão é 2.1 MODO BIG ENDIAN",
        "version_12_le": "Versão é 1.2 MODO LITTLE ENDIAN",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "extracting_to": "Extraindo para: {path}",
        "file_extracted": "Arquivo extraído: {name}",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "RCF - Radcore Cement Library VER:1.2/2.1",
        "plugin_description": "Extracts and recreates RCF files from Radical Entertainment games",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild File",
        "select_rcf_file": "Select .rcf file",
        "select_txt_file": "Select .txt file",
        "rcf_files": "RCF Files",
        "text_files": "Text Files",
        "all_files": "All files",
        "unsupported_file": "Unsupported file!",
        "extraction_completed": "Files successfully extracted to: {path}",
        "recreation_completed": "New RCF file created at: {path}",
        "folder_not_found": "Folder not found: {folder}",
        "file_not_found": "File not found: {file}",
        "error_creating_dir": "Error creating directory: {error}",
        "version_21_le": "Version 2.1 LITTLE ENDIAN MODE",
        "version_21_be": "Version 2.1 BIG ENDIAN MODE",
        "version_12_le": "Version 1.2 LITTLE ENDIAN MODE",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "extracting_to": "Extracting to: {path}",
        "file_extracted": "File extracted: {name}",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "RCF - Radcore Cement Library VER:1.2/2.1",
        "plugin_description": "Extrae y recrea archivos RCF de juegos de Radical Entertainment",
        "extract_file": "Extraer Archivo",
        "rebuild_file": "Recrear Archivo",
        "select_rcf_file": "Seleccionar archivo .rcf",
        "select_txt_file": "Seleccionar archivo .txt",
        "rcf_files": "Archivos RCF",
        "text_files": "Archivos de Texto",
        "all_files": "Todos los archivos",
        "unsupported_file": "¡Archivo no soportado!",
        "extraction_completed": "Archivos extraídos exitosamente a: {path}",
        "recreation_completed": "Nuevo archivo RCF creado en: {path}",
        "folder_not_found": "Carpeta no encontrada: {folder}",
        "file_not_found": "Archivo no encontrado: {file}",
        "error_creating_dir": "Error al crear directorio: {error}",
        "version_21_le": "Versión 2.1 MODO LITTLE ENDIAN",
        "version_21_be": "Versión 2.1 MODO BIG ENDIAN",
        "version_12_le": "Versión 1.2 MODO LITTLE ENDIAN",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "extracting_to": "Extrayendo a: {path}",
        "file_extracted": "Archivo extraído: {name}",
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
# FUNÇÕES PARA CORRIGIR A JANELA (TOPMOST)
# ==============================================================================
def pick_file_topmost(title, file_types):
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    file_path = filedialog.askopenfilename(parent=root, title=title, filetypes=file_types)
    root.destroy()
    return file_path

def pick_folder_topmost(title):
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    folder_path = filedialog.askdirectory(parent=root, title=title)
    root.destroy()
    return folder_path

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def calculate_padding(size, allocation=512):
    if size % allocation == 0:
        return size
    return ((size // allocation) + 1) * allocation

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA USAR LOGGER)
# ==============================================================================
def extract_files(file_path):
    base_directory = os.path.dirname(file_path)
    base_filename = os.path.splitext(os.path.basename(file_path))[0]
    extraction_directory = os.path.join(base_directory, base_filename)

    try:
        os.makedirs(extraction_directory, exist_ok=True)
    except Exception as e:
        logger(t("error_creating_dir", error=str(e)), color=COLOR_LOG_RED)
        return

    logger(t("extracting_to", path=extraction_directory), color=COLOR_LOG_YELLOW)

    with open(file_path, 'rb') as file:
        file.seek(32)
        file_version = file.read(4)

        if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:
            endian_format = '<' if file_version == b'\x02\x01\x00\x01' else '>'
            logger(t("version_21_le") if endian_format == '<' else t("version_21_be"), color=COLOR_LOG_YELLOW)

            file.seek(36)
            pointers_offset = struct.unpack(f'{endian_format}I', file.read(4))[0]
            file.seek(4, os.SEEK_CUR)
            names_offset = struct.unpack(f'{endian_format}I', file.read(4))[0]
            file.seek(4, os.SEEK_CUR)

            file.seek(56)
            total_items = struct.unpack(f'{endian_format}I', file.read(4))[0]

            pointers = []
            file.seek(pointers_offset)
            for _ in range(total_items):
                file.seek(4, os.SEEK_CUR)
                file_offset = struct.unpack(f'{endian_format}I', file.read(4))[0]
                file_size = struct.unpack(f'{endian_format}I', file.read(4))[0]
                pointers.append((file_offset, file_size))

            names = []
            file.seek(names_offset + 8)
            for _ in range(total_items):
                file.seek(12, os.SEEK_CUR)
                name_size = struct.unpack('<I', file.read(4))[0]
                name_bytes = file.read(name_size)
                try:
                    name = name_bytes.decode('utf-8').strip('\x00')
                    names.append(name)
                except UnicodeDecodeError:
                    names.append(f"unknown_{len(names)}")

            for i, (file_offset, file_size) in enumerate(pointers):
                if i >= len(names):
                    break
                file.seek(file_offset)
                data = file.read(file_size)
                file_name = names[i].strip()
                complete_path = os.path.join(extraction_directory, file_name.lstrip("/\\"))
                os.makedirs(os.path.dirname(complete_path), exist_ok=True)
                with open(complete_path, 'wb') as f:
                    f.write(data)
                logger(t("file_extracted", name=file_name), color=COLOR_LOG_GREEN)

            names_list_path = os.path.join(base_directory, f"{base_filename}.txt")
            with open(names_list_path, 'w', encoding='utf-8') as names_list:
                for name in names:
                    names_list.write(name + '\n')

        elif file_version == b'\x01\x02\x00\x01':
            logger(t("version_12_le"), color=COLOR_LOG_YELLOW)

            file.seek(2048)
            total_items = struct.unpack('<I', file.read(4))[0]
            names_offset = struct.unpack('<I', file.read(4))[0]
            file.seek(8, os.SEEK_CUR)

            pointers = []
            for _ in range(total_items):
                file.seek(4, os.SEEK_CUR)
                file_offset = struct.unpack('<I', file.read(4))[0]
                file_size = struct.unpack('<I', file.read(4))[0]
                pointers.append((file_offset, file_size))

            names = []
            file.seek(names_offset + 4)
            for _ in range(total_items):
                file.seek(4, os.SEEK_CUR)
                name_size = struct.unpack('<I', file.read(4))[0]
                name_bytes = file.read(name_size)
                try:
                    name = name_bytes.decode('utf-8').strip('\x00')
                    names.append(name)
                except UnicodeDecodeError:
                    names.append(f"unknown_{len(names)}")

            for i, (file_offset, file_size) in enumerate(pointers):
                if i >= len(names):
                    break
                file.seek(file_offset)
                data = file.read(file_size)
                file_name = names[i].strip()
                complete_path = os.path.join(extraction_directory, file_name.lstrip("/\\"))
                os.makedirs(os.path.dirname(complete_path), exist_ok=True)
                with open(complete_path, 'wb') as f:
                    f.write(data)
                logger(t("file_extracted", name=file_name), color=COLOR_LOG_GREEN)

            names_list_path = os.path.join(base_directory, f"{base_filename}.txt")
            with open(names_list_path, 'w', encoding='utf-8') as names_list:
                for name in names:
                    names_list.write(name + '\n')

        else:
            logger(t("unsupported_file"), color=COLOR_LOG_RED)
            return

    logger(t("extraction_completed", path=extraction_directory), color=COLOR_LOG_GREEN)


def recreate_rcf(original_file_path, txt_names_path):
    base_filename = os.path.splitext(os.path.basename(original_file_path))[0]
    base_directory = os.path.dirname(original_file_path)
    new_rcf_path = os.path.join(base_directory, f"new_{base_filename}.rcf")
    extracted_files_directory = os.path.join(base_directory, base_filename)

    if not os.path.exists(extracted_files_directory):
        logger(t("folder_not_found", folder=extracted_files_directory), color=COLOR_LOG_RED)
        return

    if not os.path.exists(txt_names_path):
        logger(t("file_not_found", file=txt_names_path), color=COLOR_LOG_RED)
        return

    with open(original_file_path, 'rb') as original_file:
        original_file.seek(32)
        file_version = original_file.read(4)

        if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:
            endian_format = '<' if file_version == b'\x02\x01\x00\x01' else '>'
            logger(t("version_21_le") if endian_format == '<' else t("version_21_be"), color=COLOR_LOG_YELLOW)

            original_file.seek(44)
            offset_value = struct.unpack(f'{endian_format}I', original_file.read(4))[0]
            original_file.seek(48)
            size_value = struct.unpack(f'{endian_format}I', original_file.read(4))[0]

            header_size = offset_value + size_value
            adjusted_header_size = calculate_padding(header_size)

            original_file.seek(0)
            header = original_file.read(adjusted_header_size)

        elif file_version == b'\x01\x02\x00\x01':
            logger(t("version_12_le"), color=COLOR_LOG_YELLOW)
            endian_format = '<'

            original_file.seek(2048)
            total_items = struct.unpack('<I', original_file.read(4))[0]
            names_offset = struct.unpack('<I', original_file.read(4))[0]

            original_file.seek(names_offset + 4)

            for _ in range(total_items):
                original_file.seek(4, os.SEEK_CUR)
                name_size = struct.unpack('<I', original_file.read(4))[0]
                original_file.read(name_size)

            header_size = original_file.tell()
            adjusted_header_size = calculate_padding(header_size)

            original_file.seek(0)
            header = original_file.read(adjusted_header_size)

        else:
            logger(t("unsupported_file"), color=COLOR_LOG_RED)
            return

    with open(new_rcf_path, 'w+b') as new_rcf:
        new_rcf.write(header)
        pointers = []
        current_position = adjusted_header_size

        with open(txt_names_path, 'r', encoding='utf-8') as txt_names:
            for line in txt_names:
                file_name = line.lstrip("/\\").strip()
                file_path = os.path.join(extracted_files_directory, file_name)

                if not os.path.exists(file_path):
                    logger(t("file_not_found", file=file_path), color=COLOR_LOG_YELLOW)
                    continue

                with open(file_path, 'rb') as f_file:
                    file_data = f_file.read()

                original_size = len(file_data)
                size_with_padding = calculate_padding(original_size)

                new_rcf.write(file_data)
                new_rcf.write(b'\x00' * (size_with_padding - original_size))

                pointers.append((current_position, original_size))
                current_position += size_with_padding

        new_rcf.seek(32)
        file_version = new_rcf.read(4)

        if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:
            endian_format = '<' if file_version == b'\x02\x01\x00\x01' else '>'
            new_rcf.seek(60)
            for pointer, original_size in pointers:
                new_rcf.seek(4, os.SEEK_CUR)
                new_rcf.write(struct.pack(f'{endian_format}I', pointer))
                new_rcf.write(struct.pack(f'{endian_format}I', original_size))
        else:
            new_rcf.seek(2064)
            for pointer, original_size in pointers:
                new_rcf.seek(4, os.SEEK_CUR)
                new_rcf.write(struct.pack('<I', pointer))
                new_rcf.write(struct.pack('<I', original_size))

    logger(t("recreation_completed", path=new_rcf_path), color=COLOR_LOG_GREEN)

# ==============================================================================
# AÇÕES DOS COMANDOS (SEM THREADING)
# ==============================================================================
def action_extract():
    path = pick_file_topmost(t("select_rcf_file"), [(t("rcf_files"), "*.rcf"), (t("all_files"), "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return
    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
    try:
        extract_files(path)
    except Exception as e:
        logger(t("error") + ": " + str(e), color=COLOR_LOG_RED)

def action_rebuild():
    rcf_path = pick_file_topmost(t("select_rcf_file"), [(t("rcf_files"), "*.rcf")])
    if not rcf_path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    base_filename = os.path.splitext(os.path.basename(rcf_path))[0]
    txt_path = pick_file_topmost(t("select_txt_file"), [(t("text_files"), "*.txt")])
    if not txt_path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(rcf_path)), color=COLOR_LOG_YELLOW)
    try:
        recreate_rcf(rcf_path, txt_path)
    except Exception as e:
        logger(t("error") + ": " + str(e), color=COLOR_LOG_RED)

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