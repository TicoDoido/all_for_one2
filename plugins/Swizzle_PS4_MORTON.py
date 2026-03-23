# Swizzle code from REVERSE BOX https://github.com/bartlomiejduda/ReverseBox
import os
import struct
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES (mantido igual)
# ==============================================================================
PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "SWIZZLER para PS4",
        "plugin_description": "Aplica ou retira o Swizzle de PS4 (MORTON).",
        "operation_label": "Operação",
        "format_label": "Formato do DDS",
        "swizzle": "swizzle",
        "unswizzle": "unswizzle",
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
        "plugin_name": "SWIZZLER for PS4",
        "plugin_description": "Apply or remove PS4 (MORTON) swizzle.",
        "operation_label": "Operation",
        "format_label": "DDS Format",
        "swizzle": "swizzle",
        "unswizzle": "unswizzle",
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
        "swizzle": "swizzle",
        "unswizzle": "unswizzle",
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

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

logger = None
get_option = None
current_lang = "pt_BR"
host_page = None

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FilePicker global com suporte a múltiplos arquivos
# ==============================================================================
fp = ft.FilePicker(
    on_result=lambda e: _process_selected_files([Path(f.path) for f in e.files]) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW),

)

# ==============================================================================
# FUNÇÕES AUXILIARES (mantidas do original)
# ==============================================================================
def calculate_morton_index_ps4(t: int, input_img_width: int, input_img_height: int) -> int:
    num1 = num2 = 1
    num3 = num4 = 0
    img_width = input_img_width
    img_height = input_img_height
    while img_width > 1 or img_height > 1:
        if img_width > 1:
            num3 += num2 * (t & 1)
            t >>= 1
            num2 <<= 1
            img_width >>= 1
        if img_height > 1:
            num4 += num1 * (t & 1)
            t >>= 1
            num1 <<= 1
            img_height >>= 1
    return num4 * input_img_width + num3

def swizzle_ps4(image_data: bytes, img_width: int, img_height: int,
                block_width: int = 4, block_height: int = 4, block_data_size: int = 16) -> bytes:
    swizzled = bytearray(len(image_data))
    src_idx = 0
    w_blocks = img_width // block_width
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
    w_blocks = img_width // block_width
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

# ==============================================================================
# FUNÇÃO DE PROCESSAMENTO EM MEMÓRIA
# ==============================================================================
def process_data(hdr: bytes, data: bytes, mode: str, fmt: str) -> bytes:
    """
    Processa os dados em memória e retorna os bytes finais (incluindo o cabeçalho).
    """
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

    height = int.from_bytes(hdr[12:16], 'little')
    width = int.from_bytes(hdr[16:20], 'little')

    aligned_w = round_up_multiple(width, 16)
    aligned_h = round_up_multiple(height, 16)
    block_w = aligned_w // 4
    block_h = aligned_h // 4
    orig_block_w = width // 4
    orig_block_h = height // 4

    # Cria buffer com padding (zeros) para processamento
    padded_data = bytearray(block_w * block_h * block_data_size)

    # Copia dados originais linha por linha
    for y in range(orig_block_h):
        src_offset = y * orig_block_w * block_data_size
        dst_offset = y * block_w * block_data_size
        padded_data[dst_offset : dst_offset + (orig_block_w * block_data_size)] = \
            data[src_offset : src_offset + (orig_block_w * block_data_size)]

    if mode == "swizzle":
        processed = swizzle_ps4(padded_data, aligned_w, aligned_h,
                                block_width=4, block_height=4,
                                block_data_size=block_data_size)
        # No swizzle, mantemos o padding (não removemos)
    else:  # unswizzle
        unswizzled = unswizzle_ps4(data, aligned_w, aligned_h,
                                   block_width=4, block_height=4,
                                   block_data_size=block_data_size)
        # Remove o padding após o unswizzle
        processed = bytearray(orig_block_w * orig_block_h * block_data_size)
        for y in range(orig_block_h):
            src_offset = y * block_w * block_data_size
            dst_offset = y * orig_block_w * block_data_size
            processed[dst_offset : dst_offset + (orig_block_w * block_data_size)] = \
                unswizzled[src_offset : src_offset + (orig_block_w * block_data_size)]

    return hdr + processed

# ==============================================================================
# FUNÇÃO AUXILIAR PARA LER ARQUIVO
# ==============================================================================
def read_dds_file(filepath: Path, fmt: str):
    """Retorna (cabeçalho, dados) do arquivo DDS."""
    if fmt == "DXT1":
        header_size = 128
    elif fmt == "DXT5":
        header_size = 128
    elif fmt == "BC7":
        header_size = 148
    elif fmt == "BGRA 8888":
        header_size = 148
    else:
        raise ValueError(t("unsupported_format", fmt=fmt))

    with open(filepath, "rb") as f:
        hdr = f.read(header_size)
        data = f.read()
    return hdr, data

# ==============================================================================
# FUNÇÃO DE PROCESSAMENTO DOS ARQUIVOS SELECIONADOS
# ==============================================================================
def _process_selected_files(file_paths):
    mode = get_option("var_mode")
    fmt = get_option("var_format")
    total = len(file_paths)
    for idx, path in enumerate(file_paths, 1):
        logger(t("processing_file", current=idx, total=total, name=path.name), color=COLOR_LOG_YELLOW)
        try:
            hdr, data = read_dds_file(path, fmt)
            result_bytes = process_data(hdr, data, mode, fmt)
            with open(path, "wb") as out_f:
                out_f.write(result_bytes)
            logger(t("success_message", path=str(path)), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("error_message", error=str(e)), color=COLOR_LOG_RED)
    logger(t("operation_completed"), color=COLOR_LOG_GREEN)

# ==============================================================================
# AÇÃO DO COMANDO (ABRE O FILE PICKER)
# ==============================================================================
def action_process():
    fp.pick_files(
        allowed_extensions=["dds"],
        dialog_title=t("select_file"),
    
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
            {"name": "var_mode", "label": t("operation_label"), "values": ["swizzle", "unswizzle"]},
            {"name": "var_format", "label": t("format_label"), "values": ["DXT1", "DXT5", "BC7", "BGRA 8888"]}
        ],
        "commands": [
            {"label": t("select_file"), "action": action_process}
        ]
    }