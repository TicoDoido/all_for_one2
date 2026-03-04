import os
import re
import struct
from pathlib import Path
from typing import List
import tkinter as tk
from tkinter import filedialog

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "GMD Arquivos de texto MT Framework (RE6)",
        "plugin_description": "Extrai e reinsere textos dos arquivos GMD da MT Framework, testado com Resident Evil 6",
        "extract_texts": "Extrair Textos",
        "insert_texts": "Reinserir Textos",
        "select_gmd_file": "Selecione arquivo GMD",
        "gmd_files": "Arquivos GMD",
        "all_files": "Todos os arquivos",
        "success": "Sucesso",
        "extraction_success": "Textos extraídos e salvos em: {path}",
        "insertion_success": "Textos reinseridos com sucesso no arquivo binário",
        "error": "Erro",
        "extraction_error": "Erro durante extração: {error}",
        "insertion_error": "Erro durante reinserção: {error}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "processing_file": "Processando arquivo: {file}",
        "extracting_texts": "Extraindo {count} textos...",
        "saving_to": "Salvando em: {path}",
        "invalid_utf8": "Texto[{index}] contém bytes UTF-8 inválidos",
        "pointer_update": "Pointer[{index}] atualizado com offset {offset}",
        "skipped_pointer": "Pointer[{index}] ignorado (0xFFFFFFFF)",
        "text_count_mismatch": "Mais textos ({text_count}) que ponteiros válidos ({pointer_count})",
        "text_file_not_found": "Arquivo de texto não encontrado para reinserção",
        "decoding_error": "<ERRO DE DECODIFICAÇÃO>",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "GMD Text Files MT Framework (RE6)",
        "plugin_description": "Extracts and reinserts texts from GMD files in MT Framework, tested with Resident Evil 6",
        "extract_texts": "Extract Texts",
        "insert_texts": "Insert Texts",
        "select_gmd_file": "Select GMD File",
        "gmd_files": "GMD Files",
        "all_files": "All Files",
        "success": "Success",
        "extraction_success": "Texts extracted and saved to: {path}",
        "insertion_success": "Texts successfully reinserted into binary file",
        "error": "Error",
        "extraction_error": "Error during extraction: {error}",
        "insertion_error": "Error during insertion: {error}",
        "file_not_found": "File not found: {file}",
        "processing_file": "Processing file: {file}",
        "extracting_texts": "Extracting {count} texts...",
        "saving_to": "Saving to: {path}",
        "invalid_utf8": "Text[{index}] contains invalid UTF-8 bytes",
        "pointer_update": "Pointer[{index}] updated with offset {offset}",
        "skipped_pointer": "Pointer[{index}] skipped (0xFFFFFFFF)",
        "text_count_mismatch": "More texts ({text_count}) than valid pointers ({pointer_count})",
        "text_file_not_found": "Text file not found for insertion",
        "decoding_error": "<DECODING ERROR>",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "GMD Archivos de texto MT Framework (RE6)",
        "plugin_description": "Extrae y reinserta textos de archivos GMD de MT Framework, probado con Resident Evil 6",
        "extract_texts": "Extraer Textos",
        "insert_texts": "Reinsertar Textos",
        "select_gmd_file": "Seleccionar archivo GMD",
        "gmd_files": "Archivos GMD",
        "all_files": "Todos los archivos",
        "success": "Éxito",
        "extraction_success": "Textos extraídos y guardados en: {path}",
        "insertion_success": "Textos reinsertados exitosamente en el archivo binario",
        "error": "Error",
        "extraction_error": "Error durante extracción: {error}",
        "insertion_error": "Error durante reinserción: {error}",
        "file_not_found": "Archivo no encontrado: {file}",
        "processing_file": "Procesando archivo: {file}",
        "extracting_texts": "Extrayendo {count} textos...",
        "saving_to": "Guardando en: {path}",
        "invalid_utf8": "Texto[{index}] contiene bytes UTF-8 inválidos",
        "pointer_update": "Pointer[{index}] actualizado con offset {offset}",
        "skipped_pointer": "Pointer[{index}] ignorado (0xFFFFFFFF)",
        "text_count_mismatch": "Más textos ({text_count}) que punteros válidos ({pointer_count})",
        "text_file_not_found": "Archivo de texto no encontrado para reinserción",
        "decoding_error": "<ERROR DE DECODIFICACIÓN>",
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

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FUNÇÃO PARA CORRIGIR A JANELA (TOPMOST)
# ==============================================================================
def pick_file_topmost(title, file_types):
    """Cria uma janela Tk invisível, força ela pro topo e abre o diálogo."""
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    file_path = filedialog.askopenfilename(parent=root, title=title, filetypes=file_types)
    root.destroy()
    return file_path

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def read_little_endian_int(file):
    """Read 4-byte little-endian integer from file"""
    return struct.unpack('<I', file.read(4))[0]

def decode_text(text_bytes):
    """Decode text bytes with UTF-8, fallback to error message"""
    try:
        return text_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return t("decoding_error")

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA USAR LOGGER)
# ==============================================================================
def extract_texts_from_gmd(gmd_path):
    """Extract texts from GMD binary file"""
    gmd_path = Path(gmd_path)
    logger(t("processing_file", file=gmd_path.name), color=COLOR_LOG_YELLOW)

    with gmd_path.open('rb') as file:
        file.seek(20)
        pointer_count = read_little_endian_int(file)
        pointer_block_size = pointer_count * 4
        pointer_table_end = pointer_block_size + 28

        # Read valid pointers
        valid_pointers = []
        for _ in range(pointer_count):
            pointer_data = file.read(4)
            if pointer_data != b'\xFF\xFF\xFF\xFF':
                valid_pointers.append(struct.unpack('<I', pointer_data)[0])

        logger(t("extracting_texts", count=len(valid_pointers)), color=COLOR_LOG_YELLOW)
        texts = []

        for i, pointer in enumerate(valid_pointers):
            file.seek(pointer_table_end + pointer)

            # Read null-terminated string
            text_bytes = bytearray()
            while True:
                byte = file.read(1)
                if byte == b'\x00' or not byte:
                    break
                text_bytes += byte

            text = decode_text(text_bytes)
            if text == t("decoding_error"):
                logger(t("invalid_utf8", index=i), color=COLOR_LOG_YELLOW)
            texts.append(text)

    return texts

def save_extracted_texts(texts, gmd_path):
    """Save extracted texts to output file"""
    output_path = Path(gmd_path).with_suffix('.txt')
    logger(t("saving_to", path=str(output_path)), color=COLOR_LOG_YELLOW)

    with output_path.open('w', encoding='utf-8') as f:
        for text in texts:
            processed_text = text.replace("\r\n", "[BR]")
            f.write(f"{processed_text}[END]\n")

    return output_path

def insert_texts_into_gmd(gmd_path):
    """Insert texts from TXT file back into GMD binary"""
    gmd_path = Path(gmd_path)
    txt_path = gmd_path.with_suffix('.txt')

    if not txt_path.exists():
        raise FileNotFoundError(t("text_file_not_found"))

    logger(t("processing_file", file=gmd_path.name), color=COLOR_LOG_YELLOW)

    # Read texts from TXT file
    with txt_path.open('r', encoding='utf-8') as f:
        texts = [t.replace("[BR]", "\r\n") for t in f.read().split("[END]\n") if t]

    with gmd_path.open('r+b') as file:
        # Read pointer information
        file.seek(20)
        pointer_count = read_little_endian_int(file)
        pointer_block_size = pointer_count * 4
        pointer_table_end = pointer_block_size + 28

        # Find all valid pointers (skip 0xFFFFFFFF)
        file.seek(24)
        valid_pointer_positions = []
        for _ in range(pointer_count):
            pos = file.tell()
            if file.read(4) != b'\xFF\xFF\xFF\xFF':
                valid_pointer_positions.append(pos)
            else:
                # Skip invalid pointer (already read 4 bytes)
                pass

        # Write new texts and collect offsets
        file.seek(pointer_table_end)
        text_offsets = []

        for text in texts:
            offset = file.tell() - pointer_table_end
            text_offsets.append(offset)
            file.write(text.encode('utf-8') + b'\x00')

        # Update file size in header
        file_size = file.tell()
        file.seek(pointer_table_end - 4)
        file.write(struct.pack('<I', file_size - pointer_table_end))

        # Update valid pointers with new offsets
        text_index = 0
        for pos in valid_pointer_positions:
            if text_index < len(text_offsets):
                file.seek(pos)
                file.write(struct.pack('<I', text_offsets[text_index]))
                logger(t("pointer_update", index=text_index, offset=text_offsets[text_index]), color=COLOR_LOG_GREEN)
                text_index += 1
            else:
                break

        # Warn if there are more texts than pointers
        if text_index < len(texts):
            warning = t("text_count_mismatch",
                        text_count=len(texts),
                        pointer_count=text_index)
            logger(warning, color=COLOR_LOG_YELLOW)
            return warning

    return True

# ==============================================================================
# AÇÕES DOS COMANDOS (SEM THREADING)
# ==============================================================================
def action_extract():
    path = pick_file_topmost(t("select_gmd_file"), [(t("gmd_files"), "*.gmd"), (t("all_files"), "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
    try:
        texts = extract_texts_from_gmd(path)
        output_path = save_extracted_texts(texts, path)
        logger(t("extraction_success", path=str(output_path)), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)

def action_insert():
    path = pick_file_topmost(t("select_gmd_file"), [(t("gmd_files"), "*.gmd"), (t("all_files"), "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
    try:
        result = insert_texts_into_gmd(path)
        if result is True:
            logger(t("insertion_success"), color=COLOR_LOG_GREEN)
        else:
            logger(result, color=COLOR_LOG_YELLOW)  # warning
    except Exception as e:
        logger(t("insertion_error", error=str(e)), color=COLOR_LOG_RED)

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
            {"label": t("extract_texts"), "action": action_extract},
            {"label": t("insert_texts"), "action": action_insert},
        ]
    }