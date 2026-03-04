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
        "plugin_name": "SWIZZLER para Xbox 360",
        "plugin_description": "Aplica ou retira o Swizzle de Xbox 360.",
        "operation_label": "Operação",
        "format_label": "Formato do DDS",
        "swizzle": "Swizzle",
        "unswizzle": "Unswizzle",
        "select_file": "Selecionar DDS",
        "dds_files": "Arquivos DDS",
        "all_files": "Todos os arquivos",
        "processing": "Processando: {name} ({width}x{height})",
        "success_title": "Sucesso",
        "success_message": "Arquivo salvo em: {path}",
        "error_title": "Erro",
        "error_message": "Falha ao processar o arquivo: {error}",
        "unsupported_format": "Formato não suportado: {fmt}",
        "cancelled": "Seleção cancelada.",
        "operation_completed": "Operação concluída.",
        "processing_file": "Processando: {name}..."
    },
    "en_US": {
        "plugin_name": "Xbox360 Swizzler",
        "plugin_description": "Apply or remove Xbox 360 texture swizzle.",
        "operation_label": "Operation",
        "format_label": "DDS Format",
        "swizzle": "Swizzle",
        "unswizzle": "Unswizzle",
        "select_file": "Select DDS file",
        "dds_files": "DDS files",
        "all_files": "All files",
        "processing": "Processing: {name} ({width}x{height})",
        "success_title": "Success",
        "success_message": "File saved at: {path}",
        "error_title": "Error",
        "error_message": "Failed to process file: {error}",
        "unsupported_format": "Unsupported format: {fmt}",
        "cancelled": "Selection cancelled.",
        "operation_completed": "Operation completed.",
        "processing_file": "Processing: {name}..."
    },
    "es_ES": {
        "plugin_name": "SWIZZLER para Xbox 360",
        "plugin_description": "Aplica o quita el Swizzle de Xbox 360.",
        "operation_label": "Operación",
        "format_label": "Formato DDS",
        "swizzle": "Swizzle",
        "unswizzle": "Unswizzle",
        "select_file": "Seleccionar DDS",
        "dds_files": "Archivos DDS",
        "all_files": "Todos los archivos",
        "processing": "Procesando: {name} ({width}x{height})",
        "success_title": "Éxito",
        "success_message": "Archivo guardado en: {path}",
        "error_title": "Error",
        "error_message": "Error al procesar el archivo: {error}",
        "unsupported_format": "Formato no soportado: {fmt}",
        "cancelled": "Selección cancelada.",
        "operation_completed": "Operación completada.",
        "processing_file": "Procesando: {name}..."
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
# FUNÇÕES DE SWIZZLE (MANTIDAS DO ORIGINAL)
# ==============================================================================

def swap_byte_order_x360(image_data: bytes) -> bytes:
    if len(image_data) % 2 != 0:
        pass

    swapped = bytearray(image_data)
    for i in range(0, len(swapped) & ~1, 2):
        swapped[i], swapped[i+1] = swapped[i+1], swapped[i]
    return bytes(swapped)

def _xg_address_2d_tiled_x(block_offset: int, width_in_blocks: int, texel_byte_pitch: int) -> int:
    aligned_width: int = (width_in_blocks + 31) & ~31
    log_bpp: int = (texel_byte_pitch >> 2) + ((texel_byte_pitch >> 1) >> (texel_byte_pitch >> 2))
    offset_byte: int = block_offset << log_bpp
    offset_tile: int = (((offset_byte & ~0xFFF) >> 3) + ((offset_byte & 0x700) >> 2) + (offset_byte & 0x3F))
    offset_macro: int = offset_tile >> (7 + log_bpp)

    macro_x: int = (offset_macro % (aligned_width >> 5)) << 2
    tile: int = (((offset_tile >> (5 + log_bpp)) & 2) + (offset_byte >> 6)) & 3
    macro: int = (macro_x + tile) << 3
    micro: int = ((((offset_tile >> 1) & ~0xF) + (offset_tile & 0xF)) & ((texel_byte_pitch << 3) - 1)) >> log_bpp

    return macro + micro


def _xg_address_2d_tiled_y(block_offset: int, width_in_blocks: int, texel_byte_pitch: int) -> int:
    aligned_width: int = (width_in_blocks + 31) & ~31
    log_bpp: int = (texel_byte_pitch >> 2) + ((texel_byte_pitch >> 1) >> (texel_byte_pitch >> 2))
    offset_byte: int = block_offset << log_bpp
    offset_tile: int = (((offset_byte & ~0xFFF) >> 3) + ((offset_byte & 0x700) >> 2) + (offset_byte & 0x3F))
    offset_macro: int = offset_tile >> (7 + log_bpp)

    macro_y: int = (offset_macro // (aligned_width >> 5)) << 2
    tile: int = ((offset_tile >> (6 + log_bpp)) & 1) + ((offset_byte & 0x800) >> 10)
    macro: int = (macro_y + tile) << 3
    micro: int = (((offset_tile & ((texel_byte_pitch << 6) - 1 & ~0x1F)) + ((offset_tile & 0xF) << 1)) >> (3 + log_bpp)) & ~1

    return macro + micro + ((offset_tile & 0x10) >> 4)


def _convert_x360_image_data(image_data: bytes, image_width: int, image_height: int, block_pixel_size: int, texel_byte_pitch: int, swizzle_flag: bool) -> bytes:
    width_in_blocks: int = image_width // block_pixel_size
    height_in_blocks: int = image_height // block_pixel_size

    padded_width_in_blocks: int = (width_in_blocks + 31) & ~31
    padded_height_in_blocks: int = (height_in_blocks + 31) & ~31
    total_padded_blocks = padded_width_in_blocks * padded_height_in_blocks

    if not swizzle_flag:
        converted_data: bytearray = bytearray(width_in_blocks * height_in_blocks * texel_byte_pitch)
    else:
        converted_data: bytearray = bytearray(total_padded_blocks * texel_byte_pitch)

    for block_offset in range(total_padded_blocks):
        x = _xg_address_2d_tiled_x(block_offset, padded_width_in_blocks, texel_byte_pitch)
        y = _xg_address_2d_tiled_y(block_offset, padded_width_in_blocks, texel_byte_pitch)

        if x < width_in_blocks and y < height_in_blocks:
            if not swizzle_flag:
                src_byte_offset = block_offset * texel_byte_pitch
                dest_byte_offset = (y * width_in_blocks + x) * texel_byte_pitch
                if src_byte_offset + texel_byte_pitch <= len(image_data):
                    converted_data[dest_byte_offset: dest_byte_offset + texel_byte_pitch] = image_data[src_byte_offset: src_byte_offset + texel_byte_pitch]
            else:
                src_byte_offset = (y * width_in_blocks + x) * texel_byte_pitch
                dest_byte_offset = block_offset * texel_byte_pitch
                if src_byte_offset + texel_byte_pitch <= len(image_data):
                    converted_data[dest_byte_offset: dest_byte_offset + texel_byte_pitch] = image_data[src_byte_offset: src_byte_offset + texel_byte_pitch]

    return bytes(converted_data)


def unswizzle_x360(image_data: bytes, img_width: int, img_height: int, block_pixel_size: int = 4, texel_byte_pitch: int = 8) -> bytes:
    swapped_data: bytes = swap_byte_order_x360(image_data)
    unswizzled_data: bytes = _convert_x360_image_data(swapped_data, img_width, img_height, block_pixel_size, texel_byte_pitch, False)
    return unswizzled_data


def swizzle_x360(image_data: bytes, img_width: int, img_height: int, block_pixel_size: int = 4, texel_byte_pitch: int = 8) -> bytes:
    swapped_data: bytes = swap_byte_order_x360(image_data)
    swizzled_data: bytes = _convert_x360_image_data(swapped_data, img_width, img_height, block_pixel_size, texel_byte_pitch, True)
    return swizzled_data

# ==============================================================================
# AÇÃO PRINCIPAL (SEM THREADING)
# ==============================================================================

def action_process():
    mode = get_option("var_mode")
    fmt = get_option("var_format")

    path = pick_file_topmost(t("select_file"), [(t("dds_files"), "*.dds"), (t("all_files"), "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing_file", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)

    try:
        with open(path, "rb") as f:
            hdr = f.read(128)
            w = int.from_bytes(hdr[16:20], 'little')
            h = int.from_bytes(hdr[12:16], 'little')
            data = f.read()

        logger(t("processing", name=os.path.basename(path), width=w, height=h), color=COLOR_LOG_YELLOW)

        format_map = {
            "DXT1": 8,
            "DXT3": 16,
            "DXT5": 16,
            "RGBA8888": 64
        }

        pitch = format_map.get(fmt)
        if pitch is None:
            raise ValueError(t("unsupported_format", fmt=fmt))

        if mode == t("swizzle"):
            new_data = swizzle_x360(data, w, h, 4, pitch)
        else:
            new_data = unswizzle_x360(data, w, h, 4, pitch)

        with open(path, "wb") as f:
            f.write(hdr + new_data)

        logger(t("success_message", path=path), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("error_message", error=str(e)), color=COLOR_LOG_RED)

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
            {"name": "var_format", "label": t("format_label"),    "values": ["DXT1", "DXT3", "DXT5", "RGBA8888"]}
        ],
        "commands": [
            {"label": t("select_file"), "action": action_process}
        ]
    }