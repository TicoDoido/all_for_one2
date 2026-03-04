# Swizzle code from REVERSE BOX https://github.com/bartlomiejduda/ReverseBox
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
        "plugin_name": "SWIZZLER para PS4",
        "plugin_description": "Aplica ou retira o Swizzle de PS4 (MORTON).",
        "operation_label": "Operação",
        "format_label": "Formato do DDS",
        "swizzle": "Swizzle",
        "unswizzle": "Unswizzle",
        "select_file": "Selecionar DDS",
        "dds_files": "Arquivos DDS",
        "all_files": "Todos os arquivos",
        "success_title": "Sucesso",
        "success_message": "Arquivo salvo em: {path}",
        "error_title": "Erro",
        "error_message": "{error}",
        "unsupported_format": "Formato não suportado: {fmt}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída.",
        "processing_file": "Processando arquivo {current}/{total}: {name}"
    },
    "en_US": {
        "plugin_name": "PS4 Swizzler",
        "plugin_description": "Apply or remove PS4 Morton swizzle.",
        "operation_label": "Operation",
        "format_label": "DDS Format",
        "swizzle": "Swizzle",
        "unswizzle": "Unswizzle",
        "select_file": "Select DDS file",
        "dds_files": "DDS files",
        "all_files": "All files",
        "success_title": "Success",
        "success_message": "File saved at: {path}",
        "error_title": "Error",
        "error_message": "{error}",
        "unsupported_format": "Unsupported format: {fmt}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed.",
        "processing_file": "Processing file {current}/{total}: {name}"
    },
    "es_ES": {
        "plugin_name": "SWIZZLER para PS4",
        "plugin_description": "Aplica o quita el Swizzle de PS4 (MORTON).",
        "operation_label": "Operación",
        "format_label": "Formato DDS",
        "swizzle": "Swizzle",
        "unswizzle": "Unswizzle",
        "select_file": "Seleccionar DDS",
        "dds_files": "Archivos DDS",
        "all_files": "Todos los archivos",
        "success_title": "Éxito",
        "success_message": "Archivo guardado en: {path}",
        "error_title": "Error",
        "error_message": "{error}",
        "unsupported_format": "Formato no soportado: {fmt}",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "operation_completed": "Operación completada.",
        "processing_file": "Procesando archivo {current}/{total}: {name}"
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
# FUNÇÃO PARA CORRIGIR A JANELA (TOPMOST) – SUPORTE A MÚLTIPLOS ARQUIVOS
# ==============================================================================
def pick_files_topmost(title, file_types):
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    file_paths = filedialog.askopenfilenames(parent=root, title=title, filetypes=file_types)
    root.destroy()
    return list(file_paths)

# ==============================================================================
# FUNÇÕES AUXILIARES (MANTIDAS DO ORIGINAL)
# ==============================================================================
def calculate_morton_index_ps4(t: int, input_img_width: int, input_img_height: int) -> int:
    num1 = num2 = 1
    num3 = num4 = 0
    img_width = input_img_width
    img_height = input_img_height
    while img_width > 1 or img_height > 1:
        if img_width > 1:
            num3 += num2 * (t & 1)
            t   >>= 1
            num2 <<= 1
            img_width >>= 1
        if img_height > 1:
            num4 += num1 * (t & 1)
            t   >>= 1
            num1 <<= 1
            img_height >>= 1
    return num4 * input_img_width + num3

def swizzle_ps4(image_data: bytes, img_width: int, img_height: int,
                block_width: int = 4, block_height: int = 4, block_data_size: int = 16) -> bytes:
    swizzled = bytearray(len(image_data))
    src_idx = 0
    w_blocks = img_width  // block_width
    h_blocks = img_height // block_height

    for y in range((h_blocks + 7) // 8):
        for x in range((w_blocks + 7) // 8):
            for t in range(64):
                morton = calculate_morton_index_ps4(t, 8, 8)
                dy = morton // 8
                dx = morton % 8
                if (x*8 + dx) < w_blocks and (y*8 + dy) < h_blocks:
                    dst = block_data_size * ((y*8 + dy) * w_blocks + (x*8 + dx))
                    swizzled[src_idx:src_idx+block_data_size] = image_data[dst:dst+block_data_size]
                    src_idx += block_data_size
    return swizzled

def unswizzle_ps4(image_data: bytes, img_width: int, img_height: int,
                  block_width: int = 4, block_height: int = 4, block_data_size: int = 16) -> bytes:
    unswizzled = bytearray(len(image_data))
    src_idx = 0
    w_blocks = img_width  // block_width
    h_blocks = img_height // block_height

    for y in range((h_blocks + 7) // 8):
        for x in range((w_blocks + 7) // 8):
            for t in range(64):
                morton = calculate_morton_index_ps4(t, 8, 8)
                dy = morton // 8
                dx = morton % 8
                if (x*8 + dx) < w_blocks and (y*8 + dy) < h_blocks:
                    dst = block_data_size * ((y*8 + dy) * w_blocks + (x*8 + dx))
                    unswizzled[dst:dst+block_data_size] = image_data[src_idx:src_idx+block_data_size]
                    src_idx += block_data_size
    return unswizzled

def round_up_multiple(value: int, multiple: int) -> int:
    return ((value + multiple - 1) // multiple) * multiple

def process_file(input_path: str, output_path: str, mode: str, fmt: str):
    # Define tamanhos por formato
    if fmt == "DXT1":
        block_data_size, header = 8, 128
    elif fmt == "DXT5":
        block_data_size, header = 16, 128
    elif fmt == "BC7":
        block_data_size, header = 16, 148
    elif fmt == "BGRA 8888":
        block_data_size, header = 16, 148
    else:
        raise ValueError(t("unsupported_format", fmt=fmt))

    with open(input_path, "rb") as f:
        hdr = f.read(header)
        height = int.from_bytes(hdr[12:16], 'little')
        width  = int.from_bytes(hdr[16:20], 'little')
        data   = f.read()

    aligned_w = round_up_multiple(width,  32)
    aligned_h = round_up_multiple(height, 32)
    block_w = aligned_w // 4
    block_h = aligned_h // 4

    orig_block_w = width  // 4
    orig_block_h = height // 4

    # Cria buffer com padding (zeros)
    padded_data = bytearray(block_w * block_h * block_data_size)

    # Copia dados originais linha por linha
    for y in range(orig_block_h):
        src_offset = y * orig_block_w * block_data_size
        dst_offset = y * block_w * block_data_size
        padded_data[dst_offset : dst_offset + (orig_block_w * block_data_size)] = \
            data[src_offset : src_offset + (orig_block_w * block_data_size)]

    if mode == t("swizzle"):
        out = swizzle_ps4(padded_data, aligned_w, aligned_h,
                          block_width=4, block_height=4,
                          block_data_size=block_data_size)
    else:  # unswizzle
        unswizzled = unswizzle_ps4(data, aligned_w, aligned_h,
                                   block_width=4, block_height=4,
                                   block_data_size=block_data_size)
        # Remove o padding após o unswizzle
        out = bytearray(orig_block_w * orig_block_h * block_data_size)
        for y in range(orig_block_h):
            src_offset = y * block_w * block_data_size
            dst_offset = y * orig_block_w * block_data_size
            out[dst_offset : dst_offset + (orig_block_w * block_data_size)] = \
                unswizzled[src_offset : src_offset + (orig_block_w * block_data_size)]

    with open(output_path, "wb") as out_f:
        out_f.write(hdr)
        out_f.write(out)

# ==============================================================================
# AÇÃO PRINCIPAL (SEM THREADING)
# ==============================================================================
def action_process():
    mode = get_option("var_mode")
    fmt  = get_option("var_format")
    paths = pick_files_topmost(t("select_file"), [(t("dds_files"), "*.dds"), (t("all_files"), "*.*")])
    if not paths:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    total = len(paths)
    for idx, filepath in enumerate(paths, 1):
        logger(t("processing_file", current=idx, total=total, name=os.path.basename(filepath)), color=COLOR_LOG_YELLOW)
        try:
            # process in-place (mesmo arquivo)
            process_file(filepath, filepath, mode, fmt)
            logger(t("success_message", path=filepath), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("error_message", error=str(e)), color=COLOR_LOG_RED)

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
        "options": [
            {"name": "var_mode",   "label": t("operation_label"), "values": [t("swizzle"), t("unswizzle")]},
            {"name": "var_format", "label": t("format_label"),    "values": ["DXT1", "DXT5", "BC7", "BGRA 8888"]}
        ],
        "commands": [
            {"label": t("select_file"), "action": action_process}
        ]
    }