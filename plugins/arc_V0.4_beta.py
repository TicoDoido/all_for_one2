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
        "plugin_name": "ARC de Dead Rising V 0.4 XBOX 360/PC",
        "plugin_description": "Extrai e recria .arc Dead Rising Xbox 360/PC",
        "extract_file": "Extrair Arquivo",
        "rebuild_file": "Reconstruir Arquivo",
        "select_arc_file": "Selecione arquivo .ARC",
        "arc_files": "Arquivos ARC",
        "all_files": "Todos os arquivos",
        "success": "Sucesso",
        "extraction_success": "{count} arquivos extraídos para: {path}",
        "recreation_success": "Arquivo {file} remontado com sucesso",
        "error": "Erro",
        "extraction_error": "Erro durante extração: {error}",
        "recreation_error": "Erro durante reconstrução: {error}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "invalid_magic": "Magic inválido. Esperado \\x00CRA ou ARC\\x00",
        "version_warning": "Feito para versão 0.4\nEncontrado: 0.{version}",
        "processing_file": "Processando: {file}",
        "writing_file": "Gravando: {file}",
        "file_error": "Erro no arquivo '{file}': {error}",
        "compression_mode": "Modo de Compactação",
        "zlib": "ZLIB (padrão)",
        "deflate": "DEFLATE (raw)",
        "N/A": "Sem compressão",
        "compression_attempt": "Tentando {method} em '{file}'",
        "compression_failed": "Falha ao comprimir '{file}': {error}",
        "rebuilding_at": "Reinserindo em offset: {offset}",
        "header_update": "Atualizando cabeçalhos",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "Dead Rising V 0.4 XBOX 360/PC ARC",
        "plugin_description": "Extracts and rebuilds Dead Rising .arc files for Xbox 360/PC",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild File",
        "select_arc_file": "Select .ARC file",
        "arc_files": "ARC Files",
        "all_files": "All files",
        "success": "Success",
        "extraction_success": "{count} files extracted to: {path}",
        "recreation_success": "File {file} rebuilt successfully",
        "error": "Error",
        "extraction_error": "Error during extraction: {error}",
        "recreation_error": "Error during rebuilding: {error}",
        "file_not_found": "File not found: {file}",
        "invalid_magic": "Invalid magic. Expected \\x00CRA or ARC\\x00",
        "version_warning": "Made for version 0.4\nFound: 0.{version}",
        "processing_file": "Processing: {file}",
        "writing_file": "Writing: {file}",
        "file_error": "File error '{file}': {error}",
        "compression_mode": "Compression Mode",
        "zlib": "ZLIB (standard)",
        "deflate": "DEFLATE (raw)",
        "N/A": "No compression",
        "compression_attempt": "Trying {method} on '{file}'",
        "compression_failed": "Compression failed '{file}': {error}",
        "rebuilding_at": "Rebuilding at offset: {offset}",
        "header_update": "Updating headers",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "ARC Dead Rising V 0.4 XBOX 360/PC",
        "plugin_description": "Extrae y recrea archivos .arc Dead Rising Xbox 360/PC",
        "extract_file": "Extraer Archivo",
        "rebuild_file": "Reconstruir Archivo",
        "select_arc_file": "Seleccionar archivo .ARC",
        "arc_files": "Archivos ARC",
        "all_files": "Todos los archivos",
        "success": "Éxito",
        "extraction_success": "{count} archivos extraídos en: {path}",
        "recreation_success": "Archivo {file} recreado con éxito",
        "error": "Error",
        "extraction_error": "Error durante extracción: {error}",
        "recreation_error": "Error durante reconstrucción: {error}",
        "file_not_found": "Archivo no encontrado: {file}",
        "invalid_magic": "Magic inválido. Se esperaba \\x00CRA o ARC\\x00",
        "version_warning": "Hecho para versión 0.4\nEncontrado: 0.{version}",
        "processing_file": "Procesando: {file}",
        "writing_file": "Escribiendo: {file}",
        "file_error": "Error en archivo '{file}': {error}",
        "compression_mode": "Modo de Compresión",
        "zlib": "ZLIB (estándar)",
        "deflate": "DEFLATE (raw)",
        "N/A": "Sin compresión",
        "compression_attempt": "Intentando {method} en '{file}'",
        "compression_failed": "Fallo al comprimir '{file}': {error}",
        "rebuilding_at": "Reinsertando en offset: {offset}",
        "header_update": "Actualizando cabeceras",
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
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    file_path = filedialog.askopenfilename(parent=root, title=title, filetypes=file_types)
    root.destroy()
    return file_path

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def determine_endian(magic):
    if magic == b'\x00CRA':
        return '>'
    elif magic == b'ARC\x00':
        return '<'
    return None

def try_decompression(data, original_size, compressed_size, filename):
    if original_size <= compressed_size:
        return data
    try:
        return zlib.decompress(data)
    except zlib.error as err_zlib:
        logger(t("compression_attempt", method="ZLIB", file=filename), color=COLOR_LOG_YELLOW)
        logger(t("compression_failed", file=filename, error=str(err_zlib)), color=COLOR_LOG_RED)
        try:
            return zlib.decompress(data, -zlib.MAX_WBITS)
        except zlib.error as err_deflate:
            logger(t("compression_attempt", method="DEFLATE", file=filename), color=COLOR_LOG_YELLOW)
            logger(t("compression_failed", file=filename, error=str(err_deflate)), color=COLOR_LOG_RED)
            return data

def apply_compression(data, mode):
    if mode == "N/A" or not data:
        return data
    try:
        if mode == "deflate":
            compress_obj = zlib.compressobj(wbits=-15)
            return compress_obj.compress(data) + compress_obj.flush()
        else:  # zlib
            return zlib.compress(data)
    except Exception as e:
        logger(t("compression_failed", file="", error=str(e)), color=COLOR_LOG_RED)
        return data

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA USAR LOGGER)
# ==============================================================================
def extract_arc(arc_path):
    try:
        arc_path = Path(arc_path)
        with arc_path.open('rb') as f:
            magic = f.read(4)
            endian = determine_endian(magic)
            if not endian:
                logger(t("invalid_magic"), color=COLOR_LOG_RED)
                return False

            version = struct.unpack(endian + 'H', f.read(2))[0]
            if version != 4:
                logger(t("version_warning", version=version), color=COLOR_LOG_YELLOW)

            file_count = struct.unpack(endian + 'H', f.read(2))[0]
            entries = []

            for _ in range(file_count):
                name_bytes = f.read(64)
                name_str = name_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
                file_id = f.read(4).hex().upper()
                full_name = f"{name_str}_{file_id}"

                compressed_size = struct.unpack(endian + 'I', f.read(4))[0]
                original_size = struct.unpack(endian + 'I', f.read(4))[0]
                offset = struct.unpack(endian + 'I', f.read(4))[0]

                entries.append((full_name, compressed_size, original_size, offset))

        output_dir = arc_path.with_name(arc_path.stem)
        output_dir.mkdir(exist_ok=True)
        logger(t("extracting_to", path=str(output_dir)), color=COLOR_LOG_YELLOW)

        with arc_path.open('rb') as f:
            for name, compressed_size, original_size, offset in entries:
                try:
                    logger(t("processing_file", file=name), color=COLOR_LOG_YELLOW)
                    output_path = output_dir / name
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    f.seek(offset)
                    file_data = f.read(compressed_size)

                    file_data = try_decompression(file_data, original_size, compressed_size, name)

                    output_path.write_bytes(file_data)
                    logger(t("writing_file", file=name), color=COLOR_LOG_GREEN)

                except Exception as file_error:
                    logger(t("file_error", file=name, error=str(file_error)), color=COLOR_LOG_RED)
                    continue

        logger(t("extraction_success", count=file_count, path=str(output_dir)), color=COLOR_LOG_GREEN)
        return True

    except Exception as e:
        logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)
        return False

def rebuild_arc(arc_path):
    try:
        arc_path = Path(arc_path)
        compression_mode = get_option("modo_compactacao") or "zlib"

        with arc_path.open('r+b') as f:
            magic = f.read(4)
            endian = determine_endian(magic)
            if not endian:
                logger(t("invalid_magic"), color=COLOR_LOG_RED)
                return False

            f.seek(4)
            version = struct.unpack(endian + 'H', f.read(2))[0]
            if version != 4:
                logger(t("version_warning", version=version), color=COLOR_LOG_YELLOW)

            file_count = struct.unpack(endian + 'H', f.read(2))[0]
            logger(f"Total files: {file_count}", color=COLOR_LOG_YELLOW)

            header_size = 8 + (80 * file_count)
            f.seek(header_size)
            data_start = f.tell()
            logger(t("rebuilding_at", offset=data_start), color=COLOR_LOG_YELLOW)

            entries = []
            f.seek(8)
            for _ in range(file_count):
                name_bytes = f.read(64)
                name_str = name_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
                file_id = f.read(4).hex().upper()
                full_name = f"{name_str}_{file_id}"

                compressed_size = struct.unpack(endian + 'I', f.read(4))[0]
                original_size = struct.unpack(endian + 'I', f.read(4))[0]
                offset = struct.unpack(endian + 'I', f.read(4))[0]

                entries.append((full_name, compressed_size, original_size))

            new_data = []
            f.seek(data_start)
            extracted_dir = arc_path.with_name(arc_path.stem)

            for name, original_compressed, original_size in entries:
                file_path = extracted_dir / name
                if not file_path.exists():
                    logger(t("file_not_found", file=str(file_path)), color=COLOR_LOG_RED)
                    return False

                file_data = file_path.read_bytes()
                current_offset = f.tell()
                logger(t("rebuilding_at", offset=current_offset), color=COLOR_LOG_YELLOW)

                if original_size > original_compressed:
                    compressed_data = apply_compression(file_data, compression_mode)
                    f.write(compressed_data)
                    new_compressed = len(compressed_data)
                    logger(f"[OK] {t(compression_mode)}: {name}", color=COLOR_LOG_GREEN)
                else:
                    f.write(file_data)
                    new_compressed = len(file_data)
                    logger(f"[OK] Sem compressão: {name}", color=COLOR_LOG_GREEN)

                new_data.append((current_offset, len(file_data), new_compressed))

            logger(t("header_update"), color=COLOR_LOG_YELLOW)
            f.seek(8)
            for idx in range(file_count):
                f.seek(68, 1)
                f.write(struct.pack(endian + 'I', new_data[idx][2]))
                if compression_mode != "N/A":
                    f.write(struct.pack(endian + 'I', new_data[idx][1]))
                else:
                    f.seek(4, 1)
                f.write(struct.pack(endian + 'I', new_data[idx][0]))

        logger(t("recreation_success", file=arc_path.name), color=COLOR_LOG_GREEN)
        return True

    except Exception as e:
        logger(t("recreation_error", error=str(e)), color=COLOR_LOG_RED)
        return False

# ==============================================================================
# AÇÕES DOS COMANDOS (SEM THREADING)
# ==============================================================================
def action_extract():
    path = pick_file_topmost(t("select_arc_file"), [(t("arc_files"), "*.arc"), (t("all_files"), "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return
    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
    extract_arc(path)

def action_rebuild():
    path = pick_file_topmost(t("select_arc_file"), [(t("arc_files"), "*.arc"), (t("all_files"), "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return
    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
    rebuild_arc(path)

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
            {
                "name": "modo_compactacao",
                "label": t("compression_mode"),
                "values": ["zlib", "deflate", "N/A"]
            }
        ],
        "commands": [
            {"label": t("extract_file"), "action": action_extract},
            {"label": t("rebuild_file"), "action": action_rebuild},
        ]
    }