import os
import json
import re
import struct
from pathlib import Path
from typing import List, Optional, Tuple
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "FILES/TEX/P3TEX... (Eternal Sonata PS3)",
        "plugin_description": "Extrai e recria textos de arquivos do jogo Eternal Sonata",
        "extract_file": "Extrair Arquivo(.FILES)",
        "import_files": "Reimportar Arquivos(.FILES)",
        "extract_ntx": "Extrair NTX3 -> DDS",
        "import_dds": "Importar DDS -> NTX3",
        "select_files_file": "Selecione arquivo .FILES",
        "select_import_dir": "Selecione pasta com arquivos para reimportar",
        "select_ntx_files": "Escolha o(s) arquivo(s) binário(s)",
        "select_ntx_file": "Escolha o arquivo NTX3 original para receber os DDS",
        "select_dds_files": "Selecione os arquivos .dds a importar",
        "files_files": "Arquivos FILES",
        "all_files": "Todos os arquivos",
        "log_magic_invalid": "Magic FILE não encontrado no início do arquivo.",
        "success": "Sucesso",
        "extraction_success": "Arquivos extraídos com sucesso!",
        "import_success": "Arquivos reimportados com sucesso!",
        "error": "Erro",
        "extraction_error": "Erro durante extração: {error}",
        "import_error": "Erro durante reimportação: {error}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "processing_file": "Processando arquivo: {file}",
        "extracting_to": "Extraindo para: {path}",
        "invalid_structure": "Estrutura do arquivo inválida",
        "file_extracted": "Arquivo extraído: {filename} -> {output_path}",
        "file_reimported": "Arquivo reimportado: {filename} -> offset {offset} size {size}",
        "file_not_in_header": "Arquivo não encontrado no header, pulando: {filename}",
        "reading_header": "Lendo header do container...",
        "found_num_files": "Número de entradas no header: {num}",
        "starting_insert_at": "Iniciando inserção em offset alinhado: {offset}",
        "skipping_nonfiles": "Pulando: {name} (não é arquivo)",
        "msg_title_error": "Erro",
        "msg_title_done": "Concluído",
        "msg_no_offsets": "Nenhum offset NTX3 encontrado no arquivo.",
        "msg_invalid_magic": "Magic inválido: {magic} (esperado {file_magic} ou 'NTX3').",
        "msg_offsets_found": "Offsets encontrados: {n}",
        "msg_extracted_count": "Texturas extraídas: {n} (pasta: {out})",
        "msg_import_success": "Importação concluída. Arquivos gravados com sucesso: {n}",
        "msg_import_fail": "Falha durante importação: {err}",
        "warn_offset_negative": "[WARN] offset negativo {off} — pulando",
        "warn_offset_beyond_file": "[WARN] offset {off} está além do tamanho do arquivo ({file_size}) — pulando",
        "warn_cant_read_header_size": "[WARN] offset {off}: não foi possível ler header_size — pulando",
        "warn_invalid_header_size": "[WARN] offset {off}: header_size inválido ({header_size}) — pulando",
        "warn_pixel_format": "[WARN] Pixel Format Não implementado {b} em: {off}",
        "warn_cant_read_wh": "[WARN] offset {off}: não foi possível ler width/height — pulando",
        "warn_invalid_dimensions": "[WARN] offset {off}: dimensão inválida ({width}x{height}) — pulando",
        "warn_data_exceeds_file": "[WARN] offset {off}: dados esperados ({data_size} bytes) excedem arquivo ({available} disponíveis). Tentando ler parcial.",
        "warn_no_data_read": "[WARN] offset {off}: nenhum dado lido — pulando",
        "info_ok_written": "[OK] {path} ({width}x{height}) fmt={fmt} read={read}/{expected} bytes",
        "error_processing_offset": "[ERROR] ao processar offset {off}: {err}",
        "warn_index_mismatch": "Arquivo {name}: índice {idx} não corresponde a nenhum offset (offsets: {count}). Pulando.",
        "warn_cant_read_block": "Não foi possível ler informações do bloco NTX3 em 0x{off:08X}. Pulando {name}",
        "warn_unknown_pixel_byte": "Offset 0x{off:08X}: pixel format byte desconhecido {pixel}. Pulando {name}",
        "error_read_dds": "Falha lendo {name}: {err}",
        "warn_dds_small": "{name}: DDS parece pequeno (<128 bytes). Pulando.",
        "warn_size_mismatch": "{name}: tamanho de imagem DDS ({have}) não corresponde a {width}x{height} (esperado {expect}).",
        "error_convert": "Falha convertendo ARGB->RGBA em {name}: {err}",
        "warn_cant_determine_expected": "cannot determine expected data size for offset 0x{off:08X}. Pulando {name}",
        "warn_final_img_too_big": "{name}: dados a escrever ({have}) maiores que espaço original ({expected}) em 0x{off:08X}. Pulando.",
        "info_padding": "{name}: dados menores; serão preenchidos com {pad} zeros.",
        "info_written": "[OK] Gravado {name} em 0x{off:08X} (tamanho {expected}).",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída.",
        "missing_files_abort": "Arquivos faltando para reimportação: {files}",
        "no_auto_dds": "Nenhum arquivo DDS automático encontrado. Abortando importação.",
        "extracting_ntx": "Extraindo texturas de {name}..."
    },
    "en_US": {
        "plugin_name": "FILES|TEX|P3TEX... (Eternal Sonata PS3)",
        "plugin_description": "Extracts and rebuilds text files from Eternal Sonata game",
        "extract_file": "Extract File(.FILES)",
        "import_files": "Reimport Files(.FILES)",
        "extract_ntx": "Extract NTX3 -> DDS",
        "import_dds": "Import DDS -> NTX3",
        "select_files_file": "Select .FILES file",
        "select_import_dir": "Select folder with files to reimport",
        "select_ntx_files": "Choose binary file(s)",
        "select_ntx_file": "Choose the NTX3 original file to receive DDSs",
        "select_dds_files": "Select .dds files to import",
        "files_files": "FILES Files",
        "all_files": "All files",
        "log_magic_invalid": "FILE magic not found at file start.",
        "success": "Success",
        "extraction_success": "Files extracted successfully!",
        "import_success": "Files reimported successfully!",
        "error": "Error",
        "extraction_error": "Error during extraction: {error}",
        "import_error": "Error during reimport: {error}",
        "file_not_found": "File not found: {file}",
        "processing_file": "Processing file: {file}",
        "extracting_to": "Extracting to: {path}",
        "invalid_structure": "Invalid file structure",
        "file_extracted": "File extracted: {filename} -> {output_path}",
        "file_reimported": "File reimported: {filename} -> offset {offset} size {size}",
        "file_not_in_header": "File not found in header, skipping: {filename}",
        "reading_header": "Reading container header...",
        "found_num_files": "Number of header entries: {num}",
        "starting_insert_at": "Starting insertion at aligned offset: {offset}",
        "skipping_nonfiles": "Skipping: {name} (not a file)",
        "msg_title_error": "Error",
        "msg_title_done": "Done",
        "msg_no_offsets": "No NTX3 offsets found in the file.",
        "msg_invalid_magic": "Invalid magic: {magic} (expected {file_magic} or 'NTX3').",
        "msg_offsets_found": "Offsets found: {n}",
        "msg_extracted_count": "Textures extracted: {n} (folder: {out})",
        "msg_import_success": "Import finished. Files written successfully: {n}",
        "msg_import_fail": "Import failed: {err}",
        "warn_offset_negative": "[WARN] offset negative {off} — skipping",
        "warn_offset_beyond_file": "[WARN] offset {off} is beyond file size ({file_size}) — skipping",
        "warn_cant_read_header_size": "[WARN] offset {off}: cannot read header_size — skipping",
        "warn_invalid_header_size": "[WARN] offset {off}: invalid header_size ({header_size}) — skipping",
        "warn_pixel_format": "[WARN] Pixel Format not implemented {b} at: {off}",
        "warn_cant_read_wh": "[WARN] offset {off}: cannot read width/height — skipping",
        "warn_invalid_dimensions": "[WARN] offset {off}: invalid dimensions ({width}x{height}) — skipping",
        "warn_data_exceeds_file": "[WARN] offset {off}: expected data ({data_size} bytes) exceeds file ({available} available). Trying partial read.",
        "warn_no_data_read": "[WARN] offset {off}: no data read — skipping",
        "info_ok_written": "[OK] {path} ({width}x{height}) fmt={fmt} read={read}/{expected} bytes",
        "error_processing_offset": "[ERROR] processing offset {off}: {err}",
        "warn_index_mismatch": "File {name}: index {idx} does not match any offset (offsets: {count}). Skipping.",
        "warn_cant_read_block": "Cannot read NTX3 block info at 0x{off:08X}. Skipping {name}",
        "warn_unknown_pixel_byte": "Offset 0x{off:08X}: unknown pixel format byte {pixel}. Skipping {name}",
        "error_read_dds": "Failed reading {name}: {err}",
        "warn_dds_small": "{name}: DDS seems small (<128 bytes). Skipping.",
        "warn_size_mismatch": "{name}: DDS image size ({have}) does not match {width}x{height} (expected {expect}).",
        "error_convert": "Failed converting ARGB->RGBA in {name}: {err}",
        "warn_cant_determine_expected": "cannot determine expected data size for offset 0x{off:08X}. Skipping {name}",
        "warn_final_img_too_big": "{name}: data to write ({have}) larger than original space ({expected}) at 0x{off:08X}. Skipping.",
        "info_padding": "{name}: data smaller than original; will be padded with {pad} zeros.",
        "info_written": "[OK] Written {name} at 0x{off:08X} (size {expected}).",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed.",
        "missing_files_abort": "Missing files for reimport: {files}",
        "no_auto_dds": "No automatic DDS files found. Aborting import.",
        "extracting_ntx": "Extracting textures from {name}..."
    },
    "es_ES": {
        "plugin_name": "FILES|TEX|P3TEX... (Eternal Sonata PS3)",
        "plugin_description": "Extrae y recrea archivos de texto del juego Eternal Sonata",
        "extract_file": "Extraer Archivo(.FILES)",
        "import_files": "Reimportar Archivos(.FILES)",
        "extract_ntx": "Extraer NTX3 -> DDS",
        "import_dds": "Importar DDS -> NTX3",
        "select_files_file": "Seleccionar archivo .FILES",
        "select_import_dir": "Seleccionar carpeta con archivos para reimportar",
        "select_ntx_files": "Elija archivo(s) binario(s)",
        "select_ntx_file": "Elija el archivo NTX3 original para recibir los DDS",
        "select_dds_files": "Seleccione los archivos .dds a importar",
        "files_files": "Archivos FILES",
        "all_files": "Todos los archivos",
        "log_magic_invalid": "Magic FILE no encontrada al inicio del archivo.",
        "success": "Éxito",
        "extraction_success": "¡Archivos extraídos con éxito!",
        "import_success": "¡Archivos reimportados con éxito!",
        "error": "Error",
        "extraction_error": "Error durante extracción: {error}",
        "import_error": "Error durante reimportación: {error}",
        "file_not_found": "Archivo no encontrado: {file}",
        "processing_file": "Procesando archivo: {file}",
        "extracting_to": "Extrayendo a: {path}",
        "invalid_structure": "Estructura de archivo inválida",
        "file_extracted": "Archivo extraído: {filename} -> {output_path}",
        "file_reimported": "Archivo reimportado: {filename} -> offset {offset} size {size}",
        "file_not_in_header": "Archivo no encontrado en el header, saltando: {filename}",
        "reading_header": "Leyendo header del contenedor...",
        "found_num_files": "Número de entradas en el header: {num}",
        "starting_insert_at": "Iniciando inserción en offset alineado: {offset}",
        "skipping_nonfiles": "Saltando: {name} (no es archivo)",
        "msg_title_error": "Error",
        "msg_title_done": "Listo",
        "msg_no_offsets": "No se encontraron offsets NTX3 en el archivo.",
        "msg_invalid_magic": "Magic inválido: {magic} (se esperaba {file_magic} o 'NTX3').",
        "msg_offsets_found": "Offsets encontrados: {n}",
        "msg_extracted_count": "Texturas extraídas: {n} (carpeta: {out})",
        "msg_import_success": "Importación finalizada. Archivos escritos con éxito: {n}",
        "msg_import_fail": "Fallo durante la importación: {err}",
        "warn_offset_negative": "[WARN] offset negativo {off} — omitiendo",
        "warn_offset_beyond_file": "[WARN] offset {off} está más allá del tamaño del archivo ({file_size}) — omitiendo",
        "warn_cant_read_header_size": "[WARN] offset {off}: no se pudo leer header_size — omitiendo",
        "warn_invalid_header_size": "[WARN] offset {off}: header_size inválido ({header_size}) — omitiendo",
        "warn_pixel_format": "[WARN] Pixel Format no implementado {b} en: {off}",
        "warn_cant_read_wh": "[WARN] offset {off}: no se pudo leer width/height — omitiendo",
        "warn_invalid_dimensions": "[WARN] offset {off}: dimensión inválida ({width}x{height}) — omitiendo",
        "warn_data_exceeds_file": "[WARN] offset {off}: datos esperados ({data_size} bytes) exceden archivo ({available} disponibles). Intentando lectura parcial.",
        "warn_no_data_read": "[WARN] offset {off}: no se leyeron datos — omitiendo",
        "info_ok_written": "[OK] {path} ({width}x{height}) fmt={fmt} read={read}/{expected} bytes",
        "error_processing_offset": "[ERROR] al procesar offset {off}: {err}",
        "warn_index_mismatch": "Archivo {name}: índice {idx} no corresponde a ningún offset (offsets: {count}). Omite.",
        "warn_cant_read_block": "No se pudo leer información del bloque NTX3 en 0x{off:08X}. Omite {name}",
        "warn_unknown_pixel_byte": "Offset 0x{off:08X}: byte de formato de píxel desconocido {pixel}. Omite {name}",
        "error_read_dds": "Fallo leyendo {name}: {err}",
        "warn_dds_small": "{name}: DDS parece pequeño (<128 bytes). Omite.",
        "warn_size_mismatch": "{name}: tamaño de imagen DDS ({have}) no coincide con {width}x{height} (esperado {expect}).",
        "error_convert": "Fallo al convertir ARGB->RGBA en {name}: {err}",
        "warn_cant_determine_expected": "cannot determine expected data size for offset 0x{off:08X}. Omite {name}",
        "warn_final_img_too_big": "{name}: datos a escribir ({have}) mayores que el espacio original ({expected}) en 0x{off:08X}. Omite.",
        "info_padding": "{name}: datos menores; serán rellenados con {pad} ceros.",
        "info_written": "[OK] Grabado {name} en 0x{off:08X} (tamaño {expected}).",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "operation_completed": "Operación completada.",
        "missing_files_abort": "Archivos faltantes para reimportación: {files}",
        "no_auto_dds": "No se encontraron archivos DDS automáticos. Abortando importación.",
        "extracting_ntx": "Extrayendo texturas de {name}..."
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
# FilePickers globais
# ==============================================================================

fp_extract = ft.FilePicker(
    on_result=lambda e: _extract_files(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)
fp_reimport = ft.FilePicker(
    on_result=lambda e: _reimport_files(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)
fp_ntx_extract = ft.FilePicker(
    on_result=lambda e: _extract_ntx([Path(f.path) for f in e.files]) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW),

)
fp_ntx_import = ft.FilePicker(
    on_result=lambda e: _import_dds(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# FUNÇÕES AUXILIARES (mantidas intactas)
# ==============================================================================

def align_up(x: int, alignment: int) -> int:
    return ((x + alignment - 1) // alignment) * alignment

# Constantes do formato
FILE_MAGIC = bytes.fromhex("03 33 90 10")
NTX_MAGIC = b"NTX3"

DDS_MAGIC = b"DDS "
DDS_HEADER_SIZE = 124
DDSD_CAPS = 0x1
DDSD_HEIGHT = 0x2
DDSD_WIDTH = 0x4
DDSD_PITCH = 0x8
DDSD_PIXELFORMAT = 0x1000
DDSD_LINEARSIZE = 0x80000
DDSCAPS_TEXTURE = 0x1000
DDPF_FOURCC = 0x4
DDPF_RGB = 0x40
DDPF_ALPHAPIXELS = 0x1

def rgba_to_argb(data: bytes) -> bytes:
    out = bytearray(len(data))
    for i in range(0, len(data), 4):
        r = data[i]
        g = data[i + 1]
        b = data[i + 2]
        a = data[i + 3]
        out[i]     = a
        out[i + 1] = r
        out[i + 2] = g
        out[i + 3] = b
    return bytes(out)

def argb_to_rgba(data: bytes) -> bytes:
    out = bytearray(len(data))
    for i in range(0, len(data), 4):
        a = data[i]
        r = data[i + 1]
        g = data[i + 2]
        b = data[i + 3]
        out[i]     = r
        out[i + 1] = g
        out[i + 2] = b
        out[i + 3] = a
    return bytes(out)

def build_dds_header(width: int, height: int, fmt: str = "DXT5") -> bytes:
    if fmt not in ("DXT5", "DXT1", "RGBA"):
        raise ValueError("fmt must be 'DXT5', 'DXT1' or 'RGBA'")
    if fmt in ("DXT5", "DXT1"):
        flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE
    else:
        flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_PITCH
    header = bytearray()
    header += DDS_MAGIC
    header += struct.pack("<I", DDS_HEADER_SIZE)
    header += struct.pack("<I", flags)
    header += struct.pack("<I", height)
    header += struct.pack("<I", width)
    if fmt == "DXT5":
        blocks_w = max(1, (width + 3) // 4)
        blocks_h = max(1, (height + 3) // 4)
        linear_size = blocks_w * blocks_h * 16
        header += struct.pack("<I", linear_size)
    elif fmt == "DXT1":
        blocks_w = max(1, (width + 3) // 4)
        blocks_h = max(1, (height + 3) // 4)
        linear_size = blocks_w * blocks_h * 8
        header += struct.pack("<I", linear_size)
    else:
        header += struct.pack("<I", width * 4)
    header += struct.pack("<I", 0)
    header += struct.pack("<I", 0)
    for _ in range(11):
        header += struct.pack("<I", 0)
    header += struct.pack("<I", 32)
    if fmt in ("DXT5", "DXT1"):
        header += struct.pack("<I", DDPF_FOURCC)
        header += (b"DXT5" if fmt == "DXT5" else b"DXT1")
        header += struct.pack("<I", 0)
        header += struct.pack("<I", 0)
        header += struct.pack("<I", 0)
        header += struct.pack("<I", 0)
        header += struct.pack("<I", 0)
    else:
        header += struct.pack("<I", DDPF_RGB | DDPF_ALPHAPIXELS)
        header += struct.pack("<4s", b"\x00\x00\x00\x00")
        header += struct.pack("<I", 32)
        header += struct.pack("<I", 0x00FF0000)
        header += struct.pack("<I", 0x0000FF00)
        header += struct.pack("<I", 0x000000FF)
        header += struct.pack("<I", 0xFF000000)
    header += struct.pack("<I", DDSCAPS_TEXTURE)
    header += struct.pack("<I", 0)
    header += struct.pack("<I", 0)
    header += struct.pack("<I", 0)
    header += struct.pack("<I", 0)
    if len(header) != 128:
        raise RuntimeError(f"DDS header inesperado: {len(header)} bytes (esperado 128)")
    return bytes(header)

def collect_offsets_from_file(f) -> List[int]:
    offsets: List[int] = []
    try:
        f.seek(8)
    except Exception:
        return offsets
    while True:
        marker_bytes = f.read(4)
        if len(marker_bytes) < 4:
            break
        marker = int.from_bytes(marker_bytes, byteorder="little", signed=False)
        if marker == 1:
            off_bytes = f.read(4)
            if len(off_bytes) < 4:
                break
            offset = int.from_bytes(off_bytes, byteorder="big", signed=False)
            offsets.append(offset)
            continue
        else:
            break
    return offsets

def find_ntx_offsets_by_scanning(path: Path) -> List[int]:
    offsets: List[int] = []
    data = path.read_bytes()
    start = 0
    while True:
        idx = data.find(NTX_MAGIC, start)
        if idx == -1:
            break
        offsets.append(idx)
        start = idx + 1
    offsets = sorted(set(offsets))
    return offsets

def extract_textures(path: Path, offsets: List[int]) -> List[Path]:
    out_files: List[Path] = []
    base = path.stem
    out_dir = path.parent
    with path.open("rb") as f:
        counter = 1
        for off in offsets:
            try:
                if off < 0:
                    logger(t("warn_offset_negative", off=off), color=COLOR_LOG_YELLOW)
                    continue
                f.seek(0, 2)
                file_size = f.tell()
                if off + 16 > file_size:
                    logger(t("warn_offset_beyond_file", off=off, file_size=file_size), color=COLOR_LOG_YELLOW)
                    continue
                f.seek(off)
                magic = f.read(4)
                if magic != NTX_MAGIC:
                    logger(t("warn_pixel_format", b=magic.hex(), off=off), color=COLOR_LOG_YELLOW)
                    continue
                f.seek(off + 16)
                header_size_b = f.read(4)
                if len(header_size_b) < 4:
                    logger(t("warn_cant_read_header_size", off=off), color=COLOR_LOG_YELLOW)
                    continue
                header_size = int.from_bytes(header_size_b, byteorder="big", signed=False)
                if header_size <= 0:
                    logger(t("warn_invalid_header_size", off=off, header_size=header_size), color=COLOR_LOG_YELLOW)
                    continue

                f.seek(off + 24)
                b = f.read(1)
                if b == b'\x86' or b == b'\xA6':
                    fmt = "DXT1"
                elif b == b'\x88' or b == b'\xA8':
                    fmt = "DXT5"
                elif b == b'\xA5':
                    fmt = "RGBA"
                else:
                    logger(t("warn_pixel_format", b=b.hex(), off=off), color=COLOR_LOG_YELLOW)
                    fmt = "DXT5"

                f.seek(off + 32)
                wh = f.read(4)
                if len(wh) < 4:
                    logger(t("warn_cant_read_wh", off=off), color=COLOR_LOG_YELLOW)
                    continue
                width = int.from_bytes(wh[0:2], byteorder="big", signed=False)
                height = int.from_bytes(wh[2:4], byteorder="big", signed=False)
                if width == 0 or height == 0:
                    logger(t("warn_invalid_dimensions", off=off, width=width, height=height), color=COLOR_LOG_YELLOW)
                    continue

                blocks_w = max(1, (width + 3) // 4)
                blocks_h = max(1, (height + 3) // 4)
                dxt1_size = blocks_w * blocks_h * 8
                dxt5_size = blocks_w * blocks_h * 16
                rgba_size = width * height * 4

                if fmt == "RGBA":
                    data_size = rgba_size
                elif fmt == "DXT1":
                    data_size = dxt1_size
                else:
                    data_size = dxt5_size

                data_offset = off + header_size

                if data_offset + data_size > file_size:
                    available = max(0, file_size - data_offset)
                    logger(t("warn_data_exceeds_file", off=off, data_size=data_size, available=available), color=COLOR_LOG_YELLOW)
                    f.seek(data_offset)
                    img_data = f.read(data_size)
                    if not img_data:
                        logger(t("warn_no_data_read", off=off), color=COLOR_LOG_YELLOW)
                        continue
                else:
                    f.seek(data_offset)
                    img_data = f.read(data_size)

                dds_fmt_for_header = fmt if fmt in ("DXT5", "DXT1") else "RGBA"
                dds_hdr = build_dds_header(width, height, dds_fmt_for_header)

                if dds_fmt_for_header == "RGBA":
                    img_data = rgba_to_argb(img_data)

                filename = f"{base}_{counter:04d}.dds"
                out_path = out_dir / filename
                with out_path.open("wb") as out_f:
                    out_f.write(dds_hdr)
                    out_f.write(img_data)

                logger(t("info_ok_written", path=out_path, width=width, height=height, fmt=fmt, read=len(img_data), expected=data_size), color=COLOR_LOG_GREEN)
                out_files.append(out_path)
                counter += 1
            except Exception as e:
                logger(t("error_processing_offset", off=off, err=str(e)), color=COLOR_LOG_RED)
                continue
    return out_files

def read_ntx3_block_info(f, off: int) -> Optional[Tuple[int,int,int,bytes,int]]:
    try:
        f.seek(0, 2)
        file_size = f.tell()
        if off + 40 > file_size:
            return None
        f.seek(off)
        magic = f.read(4)
        if magic != NTX_MAGIC:
            return None
        f.seek(off + 16)
        header_size_b = f.read(4)
        if len(header_size_b) < 4:
            return None
        header_size = int.from_bytes(header_size_b, byteorder="big", signed=False)
        f.seek(off + 24)
        pixel_byte = f.read(1)
        f.seek(off + 32)
        wh = f.read(4)
        if len(wh) < 4:
            return None
        width = int.from_bytes(wh[0:2], byteorder="big", signed=False)
        height = int.from_bytes(wh[2:4], byteorder="big", signed=False)
        if width == 0 or height == 0:
            return None
        blocks_w = max(1, (width + 3) // 4)
        blocks_h = max(1, (height + 3) // 4)
        dxt1_size = blocks_w * blocks_h * 8
        dxt5_size = blocks_w * blocks_h * 16
        rgba_size = width * height * 4
        if pixel_byte == b'\xA5':
            expected = rgba_size
        elif pixel_byte in (b'\x86', b'\xA6'):
            expected = dxt1_size
        elif pixel_byte in (b'\x88', b'\xA8'):
            expected = dxt5_size
        else:
            expected = 0
        return (header_size, width, height, pixel_byte, expected)
    except Exception:
        return None

def parse_dds_header(header: bytes) -> Tuple[str, int]:
    if len(header) < 128:
        raise ValueError("Header DDS muito pequeno")
    if b"DXT1" in header:
        return ("DXT1", 128)
    if b"DXT5" in header:
        return ("DXT5", 128)
    m1 = struct.pack("<I", 0x00FF0000)
    m2 = struct.pack("<I", 0x0000FF00)
    m3 = struct.pack("<I", 0x000000FF)
    m4 = struct.pack("<I", 0xFF000000)
    if m1 in header and m2 in header and m3 in header and m4 in header:
        return ("ARGB", 128)
    return ("ARGB", 128)

def import_dds_back_to_ntx3(ntx_path: Path, dds_paths: List[Path]) -> int:
    success_count = 0
    with ntx_path.open("rb") as f:
        start4 = f.read(4)
        f.seek(0)
        if start4 == FILE_MAGIC:
            offsets = collect_offsets_from_file(f)
        else:
            whole = f.read()
            if whole.startswith(NTX_MAGIC) or NTX_MAGIC in whole:
                offsets = find_ntx_offsets_by_scanning(ntx_path)
            else:
                raise RuntimeError(t("msg_invalid_magic", magic=start4.hex(), file_magic=FILE_MAGIC.hex()))
    if not offsets:
        raise RuntimeError(t("msg_no_offsets"))

    regex_idx = re.compile(r"_(\d{1,4})\.dds$", re.IGNORECASE)
    mapped: List[Tuple[int, Path]] = []
    for p in dds_paths:
        m = regex_idx.search(p.name)
        if m:
            idx = int(m.group(1))
            mapped.append((idx, p))
        else:
            mapped.append((0, p))
    has_indices = any(idx > 0 for idx, _ in mapped)
    if has_indices:
        mapped = [pair for pair in mapped if pair[0] > 0]
        mapped.sort(key=lambda x: x[0])
    else:
        dds_paths_sorted = sorted([p for _, p in mapped], key=lambda p: p.name)
        mapped = [(i+1, p) for i, p in enumerate(dds_paths_sorted)]

    with ntx_path.open("r+b") as f:
        for idx, dds_path in mapped:
            if idx - 1 < 0 or idx - 1 >= len(offsets):
                logger(t("warn_index_mismatch", name=dds_path.name, idx=idx, count=len(offsets)), color=COLOR_LOG_YELLOW)
                continue
            off = offsets[idx - 1]
            block_info = read_ntx3_block_info(f, off)
            if block_info is None:
                logger(t("warn_cant_read_block", off=off, name=dds_path.name), color=COLOR_LOG_YELLOW)
                continue
            header_size, width, height, pixel_byte, expected_size = block_info
            if pixel_byte == b'\xA5':
                orig_fmt = "RGBA"
            elif pixel_byte in (b'\x86', b'\xA6'):
                orig_fmt = "DXT1"
            elif pixel_byte in (b'\x88', b'\xA8'):
                orig_fmt = "DXT5"
            else:
                logger(t("warn_unknown_pixel_byte", off=off, pixel=pixel_byte.hex(), name=dds_path.name), color=COLOR_LOG_YELLOW)
                continue

            try:
                with dds_path.open("rb") as df:
                    dds_all = df.read()
            except Exception as e:
                logger(t("error_read_dds", name=dds_path.name, err=str(e)), color=COLOR_LOG_RED)
                continue
            if len(dds_all) < 128:
                logger(t("warn_dds_small", name=dds_path.name), color=COLOR_LOG_YELLOW)
                continue
            dds_header = dds_all[:128]
            dds_fmt, dds_data_offset = parse_dds_header(dds_header)
            dds_img = dds_all[dds_data_offset:]

            if dds_fmt in ("DXT1", "DXT5"):
                dds_type = dds_fmt
            else:
                dds_type = "RGBA"

            if orig_fmt != dds_type:
                logger(t("warn_final_img_too_big", name=dds_path.name, have=len(dds_img), expected=expected_size, off=off), color=COLOR_LOG_YELLOW)
                logger(t("warn_size_mismatch", name=dds_path.name, have=len(dds_img), width=width, expect=width*height*4), color=COLOR_LOG_YELLOW)
                continue

            if dds_type == "RGBA":
                if len(dds_img) != width * height * 4:
                    logger(t("warn_size_mismatch", name=dds_path.name, have=len(dds_img), width=width, expect=width*height*4), color=COLOR_LOG_YELLOW)
                try:
                    final_img = argb_to_rgba(dds_img)
                except Exception as e:
                    logger(t("error_convert", name=dds_path.name, err=str(e)), color=COLOR_LOG_RED)
                    continue
            else:
                final_img = dds_img

            if expected_size == 0:
                logger(t("warn_cant_determine_expected", off=off, name=dds_path.name), color=COLOR_LOG_YELLOW)
                continue

            if len(final_img) > expected_size:
                logger(t("warn_final_img_too_big", name=dds_path.name, have=len(final_img), expected=expected_size, off=off), color=COLOR_LOG_YELLOW)
                continue
            if len(final_img) < expected_size:
                pad_len = expected_size - len(final_img)
                final_img = final_img + (b"\x00" * pad_len)
                logger(t("info_padding", name=dds_path.name, pad=pad_len), color=COLOR_LOG_YELLOW)

            data_offset = off + header_size
            try:
                f.seek(data_offset)
                f.write(final_img[:expected_size])
                f.flush()
                logger(t("info_written", name=dds_path.name, off=off, expected=expected_size), color=COLOR_LOG_GREEN)
                success_count += 1
            except Exception as e:
                logger(t("error_processing_offset", off=off, err=str(e)), color=COLOR_LOG_RED)
                continue

    return success_count

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA RECEBER CAMINHOS)
# ==============================================================================

def _extract_files(container_path: Path):
    try:
        output_dir = container_path.with_name(container_path.stem)
        output_dir.mkdir(exist_ok=True)

        logger(t("extracting_to", path=str(output_dir)), color=COLOR_LOG_YELLOW)

        with container_path.open('rb') as container:
            magic = container.read(4)
            if magic != b'FILE':
                logger(t("log_magic_invalid"), color=COLOR_LOG_RED)
                raise ValueError(t("log_magic_invalid"))

            container.seek(8)
            num_files = struct.unpack('>I', container.read(4))[0]

            if num_files == 0 or num_files > 10000:
                raise ValueError(t("invalid_structure"))

            header_offset = 16
            entry_size = 48

            for i in range(num_files):
                container.seek(header_offset + i * entry_size)
                filename = container.read(32).decode('utf-8').rstrip('\x00')
                file_start = struct.unpack('>I', container.read(4))[0]
                file_size = struct.unpack('>I', container.read(4))[0]

                logger(t("processing_file", file=filename), color=COLOR_LOG_YELLOW)

                container.seek(file_start)
                file_data = container.read(file_size)

                output_path = output_dir / filename
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(file_data)

                logger(t("file_extracted", filename=filename, output_path=str(output_path)), color=COLOR_LOG_GREEN)

        logger(t("extraction_success"), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)


def _reimport_files(container_path: Path):
    try:
        import_dir = container_path.with_name(container_path.stem)

        logger(t("reading_header"), color=COLOR_LOG_YELLOW)

        with container_path.open('rb') as orig:
            orig.seek(0)
            magic = orig.read(4)
            if magic != b'FILE':
                logger(t("log_magic_invalid"), color=COLOR_LOG_RED)
                raise ValueError(t("log_magic_invalid"))

            orig.seek(8)
            num_files = struct.unpack('>I', orig.read(4))[0]
            logger(t("found_num_files", num=num_files), color=COLOR_LOG_YELLOW)
            if num_files == 0 or num_files > 10000:
                raise ValueError(t("invalid_structure"))

            entries_start = 16
            entry_size = 48
            header_entries = []

            for i in range(num_files):
                entry_offset = entries_start + i * entry_size
                orig.seek(entry_offset)
                raw_name = orig.read(32)
                filename = raw_name.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
                header_entries.append({
                    "filename": filename,
                    "entry_offset": entry_offset
                })

            header_end = entries_start + num_files * entry_size

        # Verificar arquivos faltantes
        missing = []
        for e in header_entries:
            src = import_dir / e['filename']
            if not src.exists() or not src.is_file():
                missing.append(e['filename'])

        if missing:
            for m in missing:
                logger(t("file_not_in_header", filename=m), color=COLOR_LOG_YELLOW)
            logger(t("missing_files_abort", files=", ".join(missing)), color=COLOR_LOG_RED)
            return

        with container_path.open('r+b') as container:
            insert_ptr = align_up(header_end, 2048)
            logger(t("starting_insert_at", offset=insert_ptr), color=COLOR_LOG_YELLOW)

            if insert_ptr > header_end:
                container.seek(header_end)
                to_write = insert_ptr - header_end
                chunk = 65536
                while to_write > 0:
                    write_now = min(chunk, to_write)
                    container.write(b'\x00' * write_now)
                    to_write -= write_now

            for e in header_entries:
                fname = e['filename']
                src_path = import_dir / fname
                data = src_path.read_bytes()
                file_len = len(data)

                insert_ptr = align_up(insert_ptr, 2048)

                container.seek(insert_ptr)
                container.write(data)

                end_after_write = insert_ptr + file_len
                next_aligned = align_up(end_after_write, 2048)
                padding = next_aligned - end_after_write
                if padding > 0:
                    container.write(b'\x00' * padding)

                container.seek(e['entry_offset'] + 32)
                container.write(struct.pack('>I', insert_ptr))
                container.write(struct.pack('>I', file_len))

                logger(t("file_reimported", filename=fname, offset=insert_ptr, size=file_len), color=COLOR_LOG_GREEN)

                insert_ptr = next_aligned

            container.truncate()
            total_size = container.tell()
            container.seek(4)
            container.write(struct.pack('>I', total_size))

        logger(t("import_success"), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("import_error", error=str(e)), color=COLOR_LOG_RED)


def _extract_ntx(file_paths: List[Path]):
    for path in file_paths:
        logger(t("extracting_ntx", name=path.name), color=COLOR_LOG_YELLOW)
        try:
            with path.open("rb") as f:
                start = f.read(4)
                f.seek(0)
                if start == FILE_MAGIC:
                    offsets = collect_offsets_from_file(f)
                else:
                    whole = f.read()
                    if whole.startswith(NTX_MAGIC) or NTX_MAGIC in whole:
                        offsets = find_ntx_offsets_by_scanning(path)
                    else:
                        logger(t("msg_invalid_magic", magic=start.hex(), file_magic=FILE_MAGIC.hex()), color=COLOR_LOG_RED)
                        continue
        except Exception as e:
            logger(t("error_processing_offset", off=0, err=str(e)), color=COLOR_LOG_RED)
            continue

        logger(t("msg_offsets_found", n=len(offsets)), color=COLOR_LOG_YELLOW)

        if not offsets:
            logger(t("msg_no_offsets"), color=COLOR_LOG_YELLOW)
            continue

        out_files = extract_textures(path, offsets)
        logger(t("msg_extracted_count", n=len(out_files), out=str(path.parent)), color=COLOR_LOG_GREEN)

    logger(t("operation_completed"), color=COLOR_LOG_GREEN)


def _import_dds(ntx_path: Path):
    base = ntx_path.stem
    dirp = ntx_path.parent
    pattern = f"{base}_*.dds"
    found = sorted(dirp.glob(pattern), key=lambda p: p.name)

    if not found:
        logger(t("no_auto_dds"), color=COLOR_LOG_RED)
        return

    try:
        written = import_dds_back_to_ntx3(ntx_path, found)
        logger(t("msg_import_success", n=written), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("msg_import_fail", err=str(e)), color=COLOR_LOG_RED)

    logger(t("operation_completed"), color=COLOR_LOG_GREEN)


# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================

def action_extract_file():
    fp_extract.pick_files(
        allowed_extensions=["files"],
        dialog_title=t("select_files_file")
    )

def action_import_files():
    fp_reimport.pick_files(
        allowed_extensions=["files"],
        dialog_title=t("select_files_file")
    )

def action_extract_ntx():
    fp_ntx_extract.pick_files(
        allowed_extensions=["tex", "p3tex"],
        dialog_title=t("select_ntx_files"),
    )

def action_import_dds():
    fp_ntx_import.pick_files(
        allowed_extensions=["tex", "p3tex"],
        dialog_title=t("select_ntx_file")
    )

BMD_MAGIC = b"BMD "
BMD_TXT_VERSION = 2
BMD_RECORD_SIZE_TEXT16 = 16
BMD_RECORD_SIZE_TEXT12 = 12

BMD_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "FILES/TEX/P3TEX/BMD (Eternal Sonata PS3)",
        "plugin_description": "Extrai e recria FILES, texturas NTX3 e textos BMD de Eternal Sonata.",
        "extract_bmd": "Extrair BMD -> TXT",
        "import_bmd": "Recompilar BMD <- TXT",
        "select_bmd_files": "Selecione arquivo(s) .BMD",
        "bmd_extracting": "Extraindo textos BMD: {name}",
        "bmd_detected": "Formato BMD detectado: {variant}",
        "bmd_extracted": "[OK] BMD extraído: {src} -> {dst} ({blocks} blocos / {entries} textos / {encoding})",
        "bmd_rebuilding": "Recompilando BMD: {name}",
        "bmd_rebuilt": "[OK] BMD recompilado: {name} ({size} bytes)",
        "bmd_backup": "Backup original: {path}",
        "bmd_not_text": "BMD {variant} não usa tabela de texto deste plugin. Recursos detectados: {details}",
        "bmd_error": "[ERRO] BMD {name}: {error}",
        "bmd_done": "Operação BMD concluída.",
        "cancelled": "Seleção cancelada.",
    },
    "en_US": {
        "plugin_name": "FILES/TEX/P3TEX/BMD (Eternal Sonata PS3)",
        "plugin_description": "Extracts and rebuilds FILES, NTX3 textures and BMD text from Eternal Sonata.",
        "extract_bmd": "Extract BMD -> TXT",
        "import_bmd": "Rebuild BMD <- TXT",
        "select_bmd_files": "Select .BMD file(s)",
        "bmd_extracting": "Extracting BMD text: {name}",
        "bmd_detected": "Detected BMD format: {variant}",
        "bmd_extracted": "[OK] BMD extracted: {src} -> {dst} ({blocks} blocks / {entries} texts / {encoding})",
        "bmd_rebuilding": "Rebuilding BMD: {name}",
        "bmd_rebuilt": "[OK] BMD rebuilt: {name} ({size} bytes)",
        "bmd_backup": "Original backup: {path}",
        "bmd_not_text": "BMD {variant} does not use this plugin's text table. Detected resources: {details}",
        "bmd_error": "[ERROR] BMD {name}: {error}",
        "bmd_done": "BMD operation completed.",
        "cancelled": "Selection cancelled.",
    },
    "es_ES": {
        "plugin_name": "FILES/TEX/P3TEX/BMD (Eternal Sonata PS3)",
        "plugin_description": "Extrae y recompila FILES, texturas NTX3 y textos BMD de Eternal Sonata.",
        "extract_bmd": "Extraer BMD -> TXT",
        "import_bmd": "Recompilar BMD <- TXT",
        "select_bmd_files": "Seleccione archivo(s) .BMD",
        "bmd_extracting": "Extrayendo textos BMD: {name}",
        "bmd_detected": "Formato BMD detectado: {variant}",
        "bmd_extracted": "[OK] BMD extraído: {src} -> {dst} ({blocks} bloques / {entries} textos / {encoding})",
        "bmd_rebuilding": "Recompilando BMD: {name}",
        "bmd_rebuilt": "[OK] BMD recompilado: {name} ({size} bytes)",
        "bmd_backup": "Copia original: {path}",
        "bmd_not_text": "BMD {variant} no usa la tabla de texto de este plugin. Recursos detectados: {details}",
        "bmd_error": "[ERROR] BMD {name}: {error}",
        "bmd_done": "Operación BMD completada.",
        "cancelled": "Selección cancelada.",
    },
}


def bt(key, **kwargs):
    text = BMD_TRANSLATIONS.get(
        current_lang, BMD_TRANSLATIONS["pt_BR"]
    ).get(key, key)
    return text.format(**kwargs) if kwargs else text


def _log(message, color=COLOR_LOG_GREEN):
    if logger:
        logger(message, color=color)
    else:
        print(message)


def _bmd_u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"Leitura u32 fora do arquivo em 0x{offset:X}.")
    return struct.unpack_from(">I", data, offset)[0]


def _parse_bmd_block_header(data: bytes):
    if len(data) < 12 or data[:4] != BMD_MAGIC:
        raise ValueError("Magic BMD inválido (esperado 'BMD ').")

    declared_size = _bmd_u32(data, 4)
    if declared_size != len(data):
        raise ValueError(
            f"Tamanho BMD inválido: header=0x{declared_size:X}, arquivo=0x{len(data):X}."
        )

    block_offsets = []
    pos = 8
    while pos + 4 <= len(data):
        off = _bmd_u32(data, pos)
        pos += 4
        if off == 0:
            break
        if off >= len(data):
            raise ValueError(f"Offset de bloco fora do arquivo: 0x{off:X}.")
        block_offsets.append(off)
    else:
        raise ValueError("Tabela de blocos BMD sem terminador 00000000.")

    if not block_offsets:
        raise ValueError("BMD sem tabela de blocos.")
    if block_offsets != sorted(block_offsets) or len(set(block_offsets)) != len(block_offsets):
        raise ValueError("Offsets de blocos BMD não são crescentes/únicos.")
    if block_offsets[0] < pos:
        raise ValueError("Primeiro bloco BMD invade o cabeçalho.")

    return block_offsets, data[pos:block_offsets[0]]


def _try_parse_bmd_text16(data: bytes):
    try:
        block_offsets, header_extra = _parse_bmd_block_header(data)
    except Exception:
        return None

    blocks = []
    for block_index, block_start in enumerate(block_offsets):
        block_end = (
            block_offsets[block_index + 1]
            if block_index + 1 < len(block_offsets)
            else len(data)
        )
        if block_start + 16 > block_end:
            return None

        first_ptr = _bmd_u32(data, block_start + 12)
        delta = first_ptr - block_start
        if first_ptr <= block_start or first_ptr >= block_end:
            return None
        if delta < 4 or (delta - 4) % 16:
            return None

        record_count = (delta - 4) // 16
        table_end = block_start + record_count * 16
        if record_count <= 0 or data[table_end:table_end + 4] != b"\x00" * 4:
            return None

        records = []
        text_intervals = []
        for record_index in range(record_count):
            rec_pos = block_start + record_index * 16
            ptr = _bmd_u32(data, rec_pos + 12)
            if not (table_end + 4 <= ptr < block_end):
                return None
            zero = data.find(b"\x00", ptr, block_end)
            if zero < 0:
                return None
            raw = data[ptr:zero]
            records.append(
                {
                    "meta": data[rec_pos:rec_pos + 12],
                    "value": ptr,
                    "is_text": True,
                    "ptr": ptr,
                    "raw": raw,
                    "end": zero + 1,
                }
            )
            text_intervals.append((ptr, zero + 1, record_index))

        blocks.append(
            {
                "old_start": block_start,
                "old_end": block_end,
                "table_end": table_end,
                "record_size": 16,
                "records": records,
                "texts": sorted(text_intervals),
                "terminator": data[table_end:table_end + 4],
            }
        )

    return {
        "variant": "TEXT16",
        "header_extra": header_extra,
        "blocks": blocks,
    }


def _try_parse_bmd_text12(data: bytes):
    try:
        block_offsets, header_extra = _parse_bmd_block_header(data)
    except Exception:
        return None

    blocks = []
    for block_index, block_start in enumerate(block_offsets):
        block_end = (
            block_offsets[block_index + 1]
            if block_index + 1 < len(block_offsets)
            else len(data)
        )

        record_count = None
        max_records = (block_end - block_start) // 12
        for candidate in range(1, max_records + 1):
            table_end = block_start + candidate * 12
            if data[table_end:table_end + 4] != b"\x00" * 4:
                continue
            if all(
                _bmd_u32(data, block_start + i * 12) == 0xFFFFD8F0
                for i in range(candidate)
            ):
                record_count = candidate
                break

        if record_count is None:
            return None

        table_end = block_start + record_count * 12
        records = []
        text_intervals = []

        for record_index in range(record_count):
            rec_pos = block_start + record_index * 12
            first, rec_type, value = struct.unpack_from(">III", data, rec_pos)
            if first != 0xFFFFD8F0:
                return None

            rec = {
                "meta": data[rec_pos:rec_pos + 8],
                "type": rec_type,
                "value": value,
                "is_text": False,
            }

            if value and table_end + 4 <= value < block_end:
                zero = data.find(b"\x00", value, block_end)
                if zero >= 0:
                    raw = data[value:zero]
                    if raw.startswith(b"<d"):
                        try:
                            raw.decode("cp932", errors="strict")
                            rec.update(
                                {
                                    "is_text": True,
                                    "ptr": value,
                                    "raw": raw,
                                    "end": zero + 1,
                                }
                            )
                            text_intervals.append((value, zero + 1, record_index))
                        except UnicodeDecodeError:
                            pass

            records.append(rec)

        blocks.append(
            {
                "old_start": block_start,
                "old_end": block_end,
                "table_end": table_end,
                "record_size": 12,
                "records": records,
                "texts": sorted(text_intervals),
                "terminator": data[table_end:table_end + 4],
            }
        )

    if not any(block["texts"] for block in blocks):
        return None

    return {
        "variant": "TEXT12",
        "header_extra": header_extra,
        "blocks": blocks,
    }


def _try_detect_bmd_pack(data: bytes):
    if len(data) < 12 or data[:4] != BMD_MAGIC:
        return None
    if _bmd_u32(data, 4) != len(data):
        return None

    count = _bmd_u32(data, 8)
    if count <= 0 or count > 100000:
        return None

    candidates = []
    for table_start in range(0x0C, 0x44, 4):
        table_end = table_start + count * 4
        if table_end > len(data):
            continue

        pointers = [_bmd_u32(data, table_start + i * 4) for i in range(count)]
        nonzero = [p for p in pointers if p]
        if not nonzero:
            continue
        if nonzero != sorted(nonzero) or len(nonzero) != len(set(nonzero)):
            continue
        if nonzero[0] < table_end or nonzero[-1] >= len(data):
            continue

        sample = nonzero[: min(100, len(nonzero))]
        printable = 0
        for ptr in sample:
            tag = data[ptr:ptr + 4]
            if tag == b"\x89PNG" or (
                len(tag) == 4 and all(0x20 <= b < 0x7F for b in tag)
            ):
                printable += 1

        if printable < max(1, int(len(sample) * 0.8)):
            continue

        gap = nonzero[0] - table_end
        candidates.append((printable, -gap, table_start, pointers))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    _, _, table_start, pointers = candidates[0]
    tags = []
    for ptr in pointers:
        if not ptr:
            continue
        tag = data[ptr:ptr + 4]
        if tag == b"\x89PNG":
            name = "PNG"
        else:
            name = tag.decode("ascii", errors="replace")
        tags.append(name)

    tag_counts = {}
    for tag in tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if tags and all(tag == "NOBJ" for tag in tags):
        variant = "PACK_NOBJ"
    else:
        variant = "PACK_RESOURCE"

    details = ", ".join(
        f"{tag}:{count}" for tag, count in
        sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
    )

    return {
        "variant": variant,
        "count": count,
        "table_start": table_start,
        "pointers": pointers,
        "details": details or "desconhecido",
    }


def _detect_bmd_structure(data: bytes):
    parsed = _try_parse_bmd_text16(data)
    if parsed:
        return parsed

    parsed = _try_parse_bmd_text12(data)
    if parsed:
        return parsed

    packed = _try_detect_bmd_pack(data)
    if packed:
        return packed

    raise ValueError("Variante BMD ainda não reconhecida.")


def _detect_bmd_encoding(structure) -> str:
    raw_texts = [
        rec["raw"]
        for block in structure["blocks"]
        for rec in block["records"]
        if rec.get("is_text")
    ]

    for encoding in ("cp932", "utf-8", "cp1252"):
        try:
            for raw in raw_texts:
                raw.decode(encoding, errors="strict")
            return encoding
        except UnicodeDecodeError:
            continue

    return "cp932"


def _decode_bmd_text(raw: bytes, encoding: str) -> str:
    try:
        return raw.decode(encoding, errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Texto BMD não pôde ser decodificado como {encoding}: {exc}."
        ) from exc


def _extract_bmd_to_txt(bmd_path: Path):
    data = bmd_path.read_bytes()
    structure = _detect_bmd_structure(data)

    if structure["variant"].startswith("PACK_"):
        raise ValueError(
            bt(
                "bmd_not_text",
                variant=structure["variant"],
                details=structure.get("details", "desconhecido"),
            )
        )

    source_encoding = _detect_bmd_encoding(structure)
    txt_path = bmd_path.with_suffix(bmd_path.suffix + ".txt")

    lines = [
        f"# Eternal Sonata BMD TXT v{BMD_TXT_VERSION}",
        f"# source_file={bmd_path.name}",
        f"# bmd_variant={structure['variant']}",
        f"# source_encoding={source_encoding}",
        f"# output_encoding={source_encoding}",
        "# Edite somente o texto depois da TAB. O texto é uma string JSON UTF-8.",
        "# Os IDs mantêm bloco e índice do registro original.",
    ]

    entry_count = 0
    for block_index, block in enumerate(structure["blocks"]):
        for record_index, record in enumerate(block["records"]):
            if not record.get("is_text"):
                continue
            text = _decode_bmd_text(record["raw"], source_encoding)
            payload = json.dumps(text, ensure_ascii=False)
            lines.append(f"B{block_index:03d}:E{record_index:03d}\t{payload}")
            entry_count += 1

    txt_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    return (
        txt_path,
        len(structure["blocks"]),
        entry_count,
        source_encoding,
        structure["variant"],
    )


def _read_bmd_txt(txt_path: Path):
    source_encoding = None
    output_encoding = None
    variant = None
    entries = {}

    with txt_path.open("r", encoding="utf-8-sig", newline=None) as f:
        for line_no, raw_line in enumerate(f, 1):
            line = raw_line.rstrip("\r\n")
            if not line:
                continue

            if line.startswith("#"):
                if line.startswith("# source_encoding="):
                    source_encoding = line.split("=", 1)[1].strip()
                elif line.startswith("# output_encoding="):
                    output_encoding = line.split("=", 1)[1].strip()
                elif line.startswith("# bmd_variant="):
                    variant = line.split("=", 1)[1].strip()
                continue

            if "\t" not in line:
                raise ValueError(
                    f"{txt_path.name}, linha {line_no}: esperado ID<TAB>texto JSON."
                )

            key, payload = line.split("\t", 1)
            match = re.fullmatch(
                r"B(\d+):E(\d+)",
                key.strip(),
                flags=re.IGNORECASE,
            )
            if not match:
                raise ValueError(
                    f"{txt_path.name}, linha {line_no}: ID inválido '{key}'."
                )

            entry_key = (int(match.group(1)), int(match.group(2)))
            if entry_key in entries:
                raise ValueError(
                    f"{txt_path.name}, linha {line_no}: ID duplicado {key}."
                )

            try:
                text = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{txt_path.name}, linha {line_no}: texto JSON inválido: {exc.msg}."
                ) from exc

            if not isinstance(text, str):
                raise ValueError(
                    f"{txt_path.name}, linha {line_no}: o valor precisa ser uma string JSON."
                )

            entries[entry_key] = text

    if not source_encoding:
        source_encoding = "cp932"
    if not output_encoding:
        output_encoding = source_encoding

    try:
        "".encode(source_encoding)
        "".encode(output_encoding)
    except LookupError as exc:
        raise ValueError(f"Encoding BMD desconhecido: {exc}.") from exc

    return source_encoding, output_encoding, variant, entries


def _encode_bmd_entry(
    block_index,
    record_index,
    record,
    translated,
    source_encoding,
    output_encoding,
):
    original_text = _decode_bmd_text(record["raw"], source_encoding)

    if (
        translated == original_text
        and output_encoding.lower() == source_encoding.lower()
    ):
        encoded = record["raw"]
    else:
        try:
            encoded = translated.encode(output_encoding, errors="strict")
        except UnicodeEncodeError as exc:
            bad = translated[exc.start:exc.end]
            raise ValueError(
                f"B{block_index:03d}:E{record_index:03d}: "
                f"'{bad}' não pode ser codificado em {output_encoding}. "
                "Altere '# output_encoding=' no TXT se necessário."
            ) from exc

    if b"\x00" in encoded:
        raise ValueError(
            f"B{block_index:03d}:E{record_index:03d}: texto contém byte NUL."
        )

    return encoded


def _rebuild_bmd_bytes(
    original_data: bytes,
    source_encoding: str,
    output_encoding: str,
    entries,
    expected_variant=None,
):
    structure = _detect_bmd_structure(original_data)
    if structure["variant"].startswith("PACK_"):
        raise ValueError(
            bt(
                "bmd_not_text",
                variant=structure["variant"],
                details=structure.get("details", "desconhecido"),
            )
        )

    if expected_variant and expected_variant != structure["variant"]:
        raise ValueError(
            f"O TXT é {expected_variant}, mas o BMD original é {structure['variant']}."
        )

    expected_keys = {
        (bi, ri)
        for bi, block in enumerate(structure["blocks"])
        for ri, record in enumerate(block["records"])
        if record.get("is_text")
    }
    found_keys = set(entries)
    missing = sorted(expected_keys - found_keys)
    extra = sorted(found_keys - expected_keys)

    if missing or extra:
        parts = []
        if missing:
            parts.append(
                "faltando "
                + ", ".join(f"B{b:03d}:E{e:03d}" for b, e in missing[:10])
            )
        if extra:
            parts.append(
                "extras "
                + ", ".join(f"B{b:03d}:E{e:03d}" for b, e in extra[:10])
            )
        raise ValueError(
            "TXT BMD não corresponde ao arquivo original: " + "; ".join(parts)
        )

    out = bytearray()
    out += BMD_MAGIC
    out += b"\x00\x00\x00\x00"

    block_table_pos = len(out)
    out += b"\x00\x00\x00\x00" * len(structure["blocks"])
    out += b"\x00\x00\x00\x00"
    out += structure["header_extra"]

    new_block_offsets = []

    for block_index, block in enumerate(structure["blocks"]):
        old_block_start = block["old_start"]
        old_block_end = block["old_end"]
        old_payload_start = block["table_end"] + 4

        new_block_start = len(out)
        new_block_offsets.append(new_block_start)

        patch_positions = {}
        for record_index, record in enumerate(block["records"]):
            out += record["meta"]
            patch_positions[record_index] = len(out)
            out += struct.pack(">I", record["value"])

        out += block["terminator"]

        text_new_ptrs = {}
        delta_events = []
        cursor = old_payload_start
        cumulative_delta = 0

        for old_text_start, old_text_end, record_index in block["texts"]:
            if old_text_start < cursor:
                raise ValueError(
                    f"Bloco {block_index}: textos sobrepostos/fora de ordem."
                )

            out += original_data[cursor:old_text_start]

            record = block["records"][record_index]
            translated = entries[(block_index, record_index)]
            encoded = _encode_bmd_entry(
                block_index,
                record_index,
                record,
                translated,
                source_encoding,
                output_encoding,
            )

            text_new_ptrs[record_index] = len(out)
            out += encoded
            out += b"\x00"

            old_length = old_text_end - old_text_start
            new_length = len(encoded) + 1
            cumulative_delta += new_length - old_length
            delta_events.append((old_text_end, cumulative_delta))
            cursor = old_text_end

        out += original_data[cursor:old_block_end]

        def map_old_payload_pointer(old_pointer):
            shift = 0
            for boundary, cumulative in delta_events:
                if old_pointer >= boundary:
                    shift = cumulative
                else:
                    break
            return new_block_start + (old_pointer - old_block_start) + shift

        for record_index, record in enumerate(block["records"]):
            patch_pos = patch_positions[record_index]
            if record.get("is_text"):
                struct.pack_into(
                    ">I",
                    out,
                    patch_pos,
                    text_new_ptrs[record_index],
                )
            else:
                old_value = record["value"]
                if (
                    block["record_size"] == 12
                    and old_value
                    and old_payload_start <= old_value < old_block_end
                ):
                    struct.pack_into(
                        ">I",
                        out,
                        patch_pos,
                        map_old_payload_pointer(old_value),
                    )

    struct.pack_into(">I", out, 4, len(out))

    for index, block_offset in enumerate(new_block_offsets):
        struct.pack_into(
            ">I",
            out,
            block_table_pos + index * 4,
            block_offset,
        )

    rebuilt = bytes(out)
    check = _detect_bmd_structure(rebuilt)
    if check["variant"] != structure["variant"]:
        raise ValueError(
            f"Rebuild mudou a variante BMD de {structure['variant']} para {check['variant']}."
        )

    return rebuilt


def _rebuild_bmd_from_txt(bmd_path: Path):
    txt_path = bmd_path.with_suffix(bmd_path.suffix + ".txt")
    if not txt_path.exists():
        raise FileNotFoundError(
            f"TXT não encontrado: {txt_path.name}. Extraia o BMD antes de recompilar."
        )

    original_data = bmd_path.read_bytes()
    source_encoding, output_encoding, variant, entries = _read_bmd_txt(txt_path)

    rebuilt = _rebuild_bmd_bytes(
        original_data,
        source_encoding,
        output_encoding,
        entries,
        expected_variant=variant,
    )

    backup_path = bmd_path.with_suffix(bmd_path.suffix + ".bak")
    if not backup_path.exists():
        backup_path.write_bytes(original_data)

    bmd_path.write_bytes(rebuilt)
    return backup_path, len(rebuilt)


def _extract_bmd(file_paths: List[Path]):
    for path in file_paths:
        _log(
            bt("bmd_extracting", name=path.name),
            color=COLOR_LOG_YELLOW,
        )
        try:
            txt_path, blocks, entries, encoding, variant = _extract_bmd_to_txt(path)
            _log(
                bt("bmd_detected", variant=variant),
                color=COLOR_LOG_YELLOW,
            )
            _log(
                bt(
                    "bmd_extracted",
                    src=path.name,
                    dst=txt_path.name,
                    blocks=blocks,
                    entries=entries,
                    encoding=encoding,
                ),
                color=COLOR_LOG_GREEN,
            )
        except Exception as exc:
            _log(
                bt("bmd_error", name=path.name, error=str(exc)),
                color=COLOR_LOG_RED,
            )

    _log(bt("bmd_done"), color=COLOR_LOG_GREEN)


def _import_bmd(file_paths: List[Path]):
    for path in file_paths:
        _log(
            bt("bmd_rebuilding", name=path.name),
            color=COLOR_LOG_YELLOW,
        )
        try:
            structure = _detect_bmd_structure(path.read_bytes())
            _log(
                bt("bmd_detected", variant=structure["variant"]),
                color=COLOR_LOG_YELLOW,
            )
            backup_path, size = _rebuild_bmd_from_txt(path)
            _log(
                bt("bmd_rebuilt", name=path.name, size=size),
                color=COLOR_LOG_GREEN,
            )
            _log(
                bt("bmd_backup", path=str(backup_path)),
                color=COLOR_LOG_YELLOW,
            )
        except Exception as exc:
            _log(
                bt("bmd_error", name=path.name, error=str(exc)),
                color=COLOR_LOG_RED,
            )

    _log(bt("bmd_done"), color=COLOR_LOG_GREEN)


fp_bmd_extract = ft.FilePicker(
    on_result=lambda e: (
        _extract_bmd([Path(f.path) for f in e.files])
        if e.files
        else _log(bt("cancelled"), color=COLOR_LOG_YELLOW)
    )
)

fp_bmd_import = ft.FilePicker(
    on_result=lambda e: (
        _import_bmd([Path(f.path) for f in e.files])
        if e.files
        else _log(bt("cancelled"), color=COLOR_LOG_YELLOW)
    )
)


def action_extract_bmd():
    fp_bmd_extract.pick_files(
        allowed_extensions=["bmd"],
        allow_multiple=True,
        dialog_title=bt("select_bmd_files"),
    )


def action_import_bmd():
    fp_bmd_import.pick_files(
        allowed_extensions=["bmd"],
        allow_multiple=True,
        dialog_title=bt("select_bmd_files"),
    )

# ==============================================================================
# ENTRY POINT (REGISTRO) - FILES + NTX3/DDS + BMD
# ==============================================================================
def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, get_option, current_lang, host_page
    logger = log_func
    get_option = option_getter
    current_lang = host_language
    host_page = page

    if host_page:
        for picker in (
            fp_extract, fp_reimport, fp_ntx_extract, fp_ntx_import,
            fp_bmd_extract, fp_bmd_import,
        ):
            if picker not in host_page.overlay:
                host_page.overlay.append(picker)
        host_page.update()

    return {
        "name": bt("plugin_name"),
        "description": bt("plugin_description"),
        "commands": [
            {"label": t("extract_file"), "action": action_extract_file},
            {"label": t("import_files"), "action": action_import_files},
            {"label": t("extract_ntx"), "action": action_extract_ntx},
            {"label": t("import_dds"), "action": action_import_dds},
            {"label": bt("extract_bmd"), "action": action_extract_bmd},
            {"label": bt("import_bmd"), "action": action_import_bmd},
        ],
    }
