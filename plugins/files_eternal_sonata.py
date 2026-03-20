import os
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
        "plugin_name": "FILES|TEX|P3TEX... (Eternal Sonata PS3)",
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
    allow_multiple=True
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
            entry_size = 40

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
        allow_multiple=True
    )

def action_import_dds():
    fp_ntx_import.pick_files(
        allowed_extensions=["tex", "p3tex"],
        dialog_title=t("select_ntx_file")
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
        host_page.overlay.extend([fp_extract, fp_reimport, fp_ntx_extract, fp_ntx_import])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_file"), "action": action_extract_file},
            {"label": t("import_files"), "action": action_import_files},
            {"label": t("extract_ntx"), "action": action_extract_ntx},
            {"label": t("import_dds"), "action": action_import_dds},
        ]
    }