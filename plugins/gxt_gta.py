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
        "plugin_name": "GXT de texto GTA 4",
        "plugin_description": "Extrai e recria textos de arquivos .GXT GTA 4",
        "extract_file": "Extrair Arquivo",
        "rebuild_file": "Recriar Arquivo",
        "select_GXT_file": "Selecione arquivos GXT",
        "select_txt_file": "Selecione arquivos TXT",
        "GXT_files": "Arquivos GXT",
        "txt_files": "Arquivos TXT",
        "all_files": "Todos os arquivos",
        "success": "Sucesso",
        "extraction_success": "Textos extraídos e salvos em: {path}",
        "recreation_success": "Textos reinseridos com sucesso",
        "error": "Erro",
        "extraction_error": "Erro durante extração: {error}",
        "recreation_error": "Erro durante reconstrução: {error}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "invalid_pointer": "Ponteiro inválido: 0x{pointer:X} fora do arquivo",
        "processing_file": "Processando arquivo: {file}",
        "detected_endian": "Endianness detectado: {endian}",
        "invalid_header": "Cabeçalho do arquivo inválido",
        "writing_to": "Escrevendo em: {path}",
        "tab_replacement": "[TAB]",
        "end_marker": "[FIM]",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "GXT Text GTA 4",
        "plugin_description": "Extracts and rebuilds text from .GXT GTA 4",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild File",
        "select_GXT_file": "Select GXT Files",
        "select_txt_file": "Select TXT Files",
        "GXT_files": "GXT Files",
        "txt_files": "TXT Files",
        "all_files": "All Files",
        "success": "Success",
        "extraction_success": "Texts extracted and saved to: {path}",
        "recreation_success": "Texts reinserted successfully",
        "error": "Error",
        "extraction_error": "Error during extraction: {error}",
        "recreation_error": "Error during rebuilding: {error}",
        "file_not_found": "File not found: {file}",
        "invalid_pointer": "Invalid pointer: 0x{pointer:X} outside file",
        "processing_file": "Processing file: {file}",
        "detected_endian": "Detected endianness: {endian}",
        "invalid_header": "Invalid file header",
        "writing_to": "Writing to: {path}",
        "tab_replacement": "[TAB]",
        "end_marker": "[END]",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "GXT de texto GTA 4",
        "plugin_description": "Extrae y recrea textos de archivos .GXT GTA 4",
        "extract_file": "Extraer Archivo",
        "rebuild_file": "Recrear Archivo",
        "select_GXT_file": "Seleccionar archivos GXT",
        "select_txt_file": "Seleccionar archivos TXT",
        "GXT_files": "Archivos GXT",
        "txt_files": "Archivos TXT",
        "all_files": "Todos los archivos",
        "success": "Éxito",
        "extraction_success": "Textos extraídos y guardados en: {path}",
        "recreation_success": "Textos reinsertados con éxito",
        "error": "Error",
        "extraction_error": "Error durante extracción: {error}",
        "recreation_error": "Error durante reconstrucción: {error}",
        "file_not_found": "Archivo no encontrado: {file}",
        "invalid_pointer": "Puntero inválido: 0x{pointer:X} fuera del archivo",
        "processing_file": "Procesando archivo: {file}",
        "detected_endian": "Endianness detectado: {endian}",
        "invalid_header": "Cabecera de archivo inválida",
        "writing_to": "Escribiendo en: {path}",
        "tab_replacement": "[TAB]",
        "end_marker": "[FIN]",
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
# FUNÇÕES PARA CORRIGIR A JANELA (TOPMOST) – SUPORTE A MÚLTIPLOS ARQUIVOS
# ==============================================================================
def pick_files_topmost(title, file_types):
    """Cria uma janela Tk invisível, força ela pro topo e abre diálogo de múltipla seleção."""
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    file_paths = filedialog.askopenfilenames(parent=root, title=title, filetypes=file_types)
    root.destroy()
    return list(file_paths)

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def determine_endianness(file_path):
    """Determine file endianness by checking header"""
    with file_path.open('rb') as file:
        header = file.read(2)
        big_endian = struct.unpack('>H', header)[0] == 4
        little_endian = struct.unpack('<H', header)[0] == 4

        if big_endian:
            logger(t("detected_endian", endian="Big-endian"), color=COLOR_LOG_YELLOW)
            return '>'
        elif little_endian:
            logger(t("detected_endian", endian="Little-endian"), color=COLOR_LOG_YELLOW)
            return '<'
        else:
            raise ValueError(t("invalid_header"))

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA USAR LOGGER)
# ==============================================================================
def extract_GXT_text(file_path, endian):
    """Extract text from GXT file"""
    logger(t("processing_file", file=file_path.name), color=COLOR_LOG_YELLOW)

    with file_path.open('rb') as file:
        file.seek(8)
        value1 = struct.unpack(endian + 'I', file.read(4))[0]
        pointer_count = value1 // 8

        # Read pointers
        pointers = []
        for _ in range(pointer_count):
            pointer = struct.unpack(endian + 'I', file.read(4))[0]
            file.seek(4, os.SEEK_CUR)  # Skip unknown bytes
            absolute_pos = 20 + pointer + value1

            if absolute_pos >= file_path.stat().st_size:
                logger(t("invalid_pointer", pointer=absolute_pos), color=COLOR_LOG_YELLOW)
                continue

            pointers.append(absolute_pos)

        # Prepare marker
        marker_bytes = t("end_marker").encode('ansi')
        tab_repl = t("tab_replacement").encode('ansi')

        # Extract text blocks
        text_blocks = []
        for pos in pointers:
            file.seek(pos)
            text_bytes = bytearray()

            while True:
                byte = file.read(1)
                if byte == b'\x00' or not byte:
                    break
                text_bytes += byte

            # Replace tabs with marker
            text_bytes = text_bytes.replace(b'\x09', tab_repl)

            text_blocks.append(bytes(text_bytes) + marker_bytes)

    # Join blocks with newline between them (cada bloco já tem seu end_marker)
    joined_text = b'\n'.join(text_blocks) + b'\n'

    # Save to TXT file
    output_path = file_path.with_suffix('.txt')
    logger(t("writing_to", path=str(output_path)), color=COLOR_LOG_YELLOW)
    output_path.write_bytes(joined_text)

    return output_path


def rebuild_GXT_from_txt(txt_path, endian):
    """Rebuild GXT file from TXT"""
    GXT_path = txt_path.with_suffix('.GXT')
    if not GXT_path.exists():
        raise FileNotFoundError(t("file_not_found", file=str(GXT_path)))

    logger(t("processing_file", file=txt_path.name), color=COLOR_LOG_YELLOW)

    # Read and parse TXT file
    text_data = txt_path.read_bytes()
    end_marker_b = t("end_marker").encode('ansi')
    split_token = end_marker_b + b'\n'
    text_blocks = text_data.split(split_token)

    # Process text blocks
    processed_blocks = []
    tab_rep_b = t("tab_replacement").encode('ansi')
    for block in text_blocks:
        block = block.replace(tab_rep_b, b'\x09')
        processed_blocks.append(block)

    # Remove trailing empty block(s) robustly (handles \r, \n, \x00)
    while processed_blocks and processed_blocks[-1].strip(b'\r\n\x00') == b'':
        processed_blocks.pop()

    with GXT_path.open('r+b') as file:
        # Read original structure
        file.seek(8)
        value1 = struct.unpack(endian + 'I', file.read(4))[0]
        text_start_pos = 20 + value1

        # Write new text blocks
        block_positions = []
        current_pos = text_start_pos
        for block in processed_blocks:
            file.seek(current_pos)
            file.write(block)
            file.write(b'\x00')
            block_positions.append(current_pos)
            current_pos += len(block) + 1

        tamanho_final = file.tell()
        file.truncate()

        # Update pointers
        file.seek(12)
        for pos in block_positions:
            relative_pos = pos - text_start_pos
            file.write(struct.pack(endian + 'I', relative_pos))
            file.seek(4, os.SEEK_CUR)  # Skip unknown bytes

        file.seek(4, os.SEEK_CUR)
        tamanho_bloco_texto = tamanho_final - text_start_pos

    return True

# ==============================================================================
# AÇÕES DOS COMANDOS (SEM THREADING)
# ==============================================================================
def action_extract():
    paths = pick_files_topmost(t("select_GXT_file"), [(t("GXT_files"), "*.GXT"), (t("all_files"), "*.*")])
    if not paths:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    total = len(paths)
    for idx, filepath in enumerate(paths, 1):
        logger(t("processing", name=os.path.basename(filepath)), color=COLOR_LOG_YELLOW)
        try:
            path = Path(filepath)
            endian = determine_endianness(path)
            output_path = extract_GXT_text(path, endian)
            logger(t("extraction_success", path=str(output_path)), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)

    logger(t("operation_completed"), color=COLOR_LOG_GREEN)

def action_rebuild():
    paths = pick_files_topmost(t("select_txt_file"), [(t("txt_files"), "*.txt"), (t("all_files"), "*.*")])
    if not paths:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    total = len(paths)
    for idx, filepath in enumerate(paths, 1):
        logger(t("processing", name=os.path.basename(filepath)), color=COLOR_LOG_YELLOW)
        try:
            txt_path = Path(filepath)
            GXT_path = txt_path.with_suffix('.GXT')
            endian = determine_endianness(GXT_path)
            rebuild_GXT_from_txt(txt_path, endian)
            logger(t("recreation_success"), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("recreation_error", error=str(e)), color=COLOR_LOG_RED)

    logger(t("operation_completed"), color=COLOR_LOG_GREEN)

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