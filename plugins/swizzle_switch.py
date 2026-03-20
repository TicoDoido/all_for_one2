# Swizzle code for Nintendo Switch (adapted from REVERSE BOX plugin)
import os
import struct
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "SWIZZLER para Nintendo Switch",
        "plugin_description": "Aplica ou retira o Swizzle de texturas do Nintendo Switch.",
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
        "plugin_name": "Nintendo Switch Swizzler",
        "plugin_description": "Apply or remove Switch texture swizzle.",
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
        "plugin_name": "SWIZZLER para Nintendo Switch",
        "plugin_description": "Aplica o quita el Swizzle de Nintendo Switch.",
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
host_page = None

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FilePicker global
# ==============================================================================

fp = ft.FilePicker(
    on_result=lambda e: _process_file(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# FUNÇÕES DE SWIZZLE (mantidas do original)
# ==============================================================================

def _convert_switch(input_image_data: bytes, img_width: int, img_height: int,
                    bytes_per_block: int = 4, block_height: int = 8,
                    width_pad: int = 8, height_pad: int = 8, swizzle_flag: bool = False):
    converted_data = bytearray(len(input_image_data))
    if img_width % width_pad or img_height % height_pad:
        width_show = img_width
        height_show = img_height
        img_width = width_real = ((img_width + width_pad - 1) // width_pad) * width_pad
        img_height = height_real = ((img_height + height_pad - 1) // height_pad) * height_pad
    else:
        width_show = width_real = img_width
        height_show = height_real = img_height

    image_width_in_gobs = img_width * bytes_per_block // 64

    for Y in range(img_height):
        for X in range(img_width):
            Z = Y * img_width + X
            gob_address = (Y // (8 * block_height)) * 512 * block_height * image_width_in_gobs + \
                          (X * bytes_per_block // 64) * 512 * block_height + \
                          (Y % (8 * block_height) // 8) * 512
            Xb = X * bytes_per_block
            address = gob_address + ((Xb % 64) // 32) * 256 + ((Y % 8) // 2) * 64 + \
                      ((Xb % 32) // 16) * 32 + (Y % 2) * 16 + (Xb % 16)

            if not swizzle_flag:
                converted_data[Z * bytes_per_block:(Z + 1) * bytes_per_block] = \
                    input_image_data[address:address + bytes_per_block]
            else:
                converted_data[address:address + bytes_per_block] = \
                    input_image_data[Z * bytes_per_block:(Z + 1) * bytes_per_block]

    # Crop (caso tenha padding)
    if width_show != width_real or height_show != height_real:
        crop = bytearray(width_show * height_show * bytes_per_block)
        for Y in range(height_show):
            offset_in = Y * width_real * bytes_per_block
            offset_out = Y * width_show * bytes_per_block
            if not swizzle_flag:
                crop[offset_out:offset_out + width_show * bytes_per_block] = \
                    converted_data[offset_in:offset_in + width_show * bytes_per_block]
            else:
                crop[offset_in:offset_in + width_show * bytes_per_block] = \
                    converted_data[offset_out:offset_out + width_show * bytes_per_block]
        converted_data = crop

    return converted_data

def unswizzle_switch(input_image_data: bytes, img_width: int, img_height: int,
                     bytes_per_block: int = 4, block_height: int = 8,
                     width_pad: int = 8, height_pad: int = 8) -> bytes:
    return _convert_switch(input_image_data, img_width, img_height, bytes_per_block, block_height, width_pad, height_pad, False)

def swizzle_switch(input_image_data: bytes, img_width: int, img_height: int,
                   bytes_per_block: int = 4, block_height: int = 8,
                   width_pad: int = 8, height_pad: int = 8) -> bytes:
    return _convert_switch(input_image_data, img_width, img_height, bytes_per_block, block_height, width_pad, height_pad, True)

# ==============================================================================
# FUNÇÃO DE PROCESSAMENTO DE UM ÚNICO ARQUIVO
# ==============================================================================

def _process_file(path: Path):
    mode = get_option("var_mode")
    fmt = get_option("var_format")

    logger(t("processing_file", name=path.name), color=COLOR_LOG_YELLOW)

    try:
        with open(path, "rb") as f:
            # O cabeçalho DDS varia conforme o formato
            if fmt == "RGBA8888":
                hdr = f.read(148)
            else:
                hdr = f.read(128)
            w = int.from_bytes(hdr[16:20], 'little')
            h = int.from_bytes(hdr[12:16], 'little')
            data = f.read()

        logger(t("processing", name=path.name, width=w, height=h), color=COLOR_LOG_YELLOW)

        format_map = {
            "DXT1": 8,
            "DXT3": 16,
            "DXT5": 16,
            "RGBA8888": 4,
            "BC7": 8
        }

        bpp = format_map.get(fmt)
        if bpp is None:
            raise ValueError(t("unsupported_format", fmt=fmt))

        if mode == "Swizzle":
            new_data = swizzle_switch(data, w, h, bpp)
        else:
            new_data = unswizzle_switch(data, w, h, bpp)

        with open(path, "wb") as f:
            f.write(hdr + new_data)

        logger(t("success_message", path=str(path)), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("error_message", error=str(e)), color=COLOR_LOG_RED)


# ==============================================================================
# AÇÃO DO COMANDO (CHAMA O FILEPICKER)
# ==============================================================================

def action_process():
    fp.pick_files(
        allowed_extensions=["dds"],
        dialog_title=t("select_file")
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
        host_page.overlay.append(fp)
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "options": [
            {"name": "var_mode",   "label": t("operation_label"), "values": ["Swizzle", "Unswizzle"]},
            {"name": "var_format", "label": t("format_label"),    "values": ["DXT1", "DXT3", "DXT5", "RGBA8888", "BC7"]}
        ],
        "commands": [
            {"label": t("select_file"), "action": action_process}
        ]
    }