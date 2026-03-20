# Plugin Dead Rising ARC
import os
import struct
import zlib
import flet as ft
from pathlib import Path

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
        "success": "Sucesso",
        "extraction_success": "{count} arquivos extraídos para: {path}",
        "recreation_success": "Arquivo {file} remontado com sucesso",
        "invalid_magic": "Magic inválido. Esperado \\x00CRA ou ARC\\x00",
        "version_warning": "Feito para versão 0.4. Encontrado: 0.{version}",
        "processing_file": "Processando: {file}",
        "writing_file": "Gravando: {file}",
        "file_error": "Erro no arquivo '{file}': {error}",
        "compression_mode": "Modo de Compactação",
        "compression_attempt": "Tentando {method} em '{file}'",
        "compression_failed": "Falha ao comprimir '{file}': {error}",
        "rebuilding_at": "Reinserindo em offset: {offset}",
        "header_update": "Atualizando cabeçalhos",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
    },
    "en_US": {
        "plugin_name": "Dead Rising V 0.4 XBOX 360/PC ARC",
        "plugin_description": "Extracts and rebuilds Dead Rising .arc files for Xbox 360/PC",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild File",
        "select_arc_file": "Select .ARC file",
        "success": "Success",
        "extraction_success": "{count} files extracted to: {path}",
        "recreation_success": "File {file} rebuilt successfully",
        "invalid_magic": "Invalid magic. Expected \\x00CRA or ARC\\x00",
        "version_warning": "Made for version 0.4. Found: 0.{version}",
        "processing_file": "Processing: {file}",
        "writing_file": "Writing: {file}",
        "file_error": "File error '{file}': {error}",
        "compression_mode": "Compression Mode",
        "compression_attempt": "Trying {method} on '{file}'",
        "compression_failed": "Compression failed '{file}': {error}",
        "rebuilding_at": "Rebuilding at offset: {offset}",
        "header_update": "Updating headers",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
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
# FUNÇÕES AUXILIARES
# ==============================================================================
def determine_endian(magic):
    if magic == b'\x00CRA': return '>'
    elif magic == b'ARC\x00': return '<'
    return None

def try_decompression(data, original_size, compressed_size, filename):
    if original_size <= compressed_size:
        return data
    try:
        return zlib.decompress(data)
    except zlib.error:
        try:
            return zlib.decompress(data, -zlib.MAX_WBITS)
        except zlib.error as e:
            if logger: logger(t("compression_failed", file=filename, error=str(e)), color=COLOR_LOG_RED)
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
        if logger: logger(t("compression_failed", file="", error=str(e)), color=COLOR_LOG_RED)
        return data

# ==============================================================================
# OPERAÇÕES ARC
# ==============================================================================
def extract_arc(arc_path):
    try:
        if not arc_path: return
        path_obj = Path(arc_path)
        with path_obj.open('rb') as f:
            magic = f.read(4)
            endian = determine_endian(magic)
            if not endian:
                if logger: logger(t("invalid_magic"), color=COLOR_LOG_RED)
                return

            version = struct.unpack(endian + 'H', f.read(2))[0]
            if version != 4:
                if logger: logger(t("version_warning", version=version), color=COLOR_LOG_YELLOW)

            file_count = struct.unpack(endian + 'H', f.read(2))[0]
            entries = []

            for _ in range(file_count):
                name_bytes = f.read(64)
                name_str = name_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
                file_id = f.read(4).hex().upper()
                full_name = f"{name_str}_{file_id}"
                
                c_size = struct.unpack(endian + 'I', f.read(4))[0]
                o_size = struct.unpack(endian + 'I', f.read(4))[0]
                offset = struct.unpack(endian + 'I', f.read(4))[0]
                entries.append((full_name, c_size, o_size, offset))

        output_dir = path_obj.with_name(path_obj.stem)
        output_dir.mkdir(exist_ok=True)

        with path_obj.open('rb') as f:
            for name, c_size, o_size, offset in entries:
                try:
                    if logger: logger(t("processing_file", file=name), color=COLOR_LOG_YELLOW)
                    out_path = output_dir / name
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    f.seek(offset)
                    data = f.read(c_size)
                    data = try_decompression(data, o_size, c_size, name)
                    out_path.write_bytes(data)
                except Exception as fe:
                    if logger: logger(t("file_error", file=name, error=str(fe)), color=COLOR_LOG_RED)

        if logger: logger(t("extraction_success", count=file_count, path=str(output_dir)), color=COLOR_LOG_GREEN)
    except Exception as e:
        if logger: logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)

def rebuild_arc(arc_path):
    try:
        if not arc_path: return
        path_obj = Path(arc_path)
        mode = get_option("modo_compactacao") or "zlib"

        with path_obj.open('r+b') as f:
            magic = f.read(4)
            endian = determine_endian(magic)
            if not endian:
                if logger: logger(t("invalid_magic"), color=COLOR_LOG_RED)
                return

            f.seek(6)
            file_count = struct.unpack(endian + 'H', f.read(2))[0]
            header_size = 8 + (80 * file_count)
            f.seek(header_size)
            data_start = f.tell()

            entries = []
            f.seek(8)
            for _ in range(file_count):
                name_bytes = f.read(64)
                name_str = name_bytes.split(b'\x00', 1)[0].decode('utf-8', errors='ignore')
                file_id = f.read(4).hex().upper()
                full_name = f"{name_str}_{file_id}"
                c_size = struct.unpack(endian + 'I', f.read(4))[0]
                o_size = struct.unpack(endian + 'I', f.read(4))[0]
                f.seek(4, 1) # pular offset antigo
                entries.append((full_name, c_size, o_size))

            new_metadata = []
            f.seek(data_start)
            src_dir = path_obj.with_name(path_obj.stem)

            for name, old_c, old_o in entries:
                file_p = src_dir / name
                if not file_p.exists():
                    if logger: logger(t("file_not_found", file=name), color=COLOR_LOG_RED)
                    return
                
                raw_data = file_p.read_bytes()
                curr_offset = f.tell()
                
                if old_o > old_c: # Se era comprimido antes
                    comp_data = apply_compression(raw_data, mode)
                    f.write(comp_data)
                    new_metadata.append((curr_offset, len(raw_data), len(comp_data)))
                else:
                    f.write(raw_data)
                    new_metadata.append((curr_offset, len(raw_data), len(raw_data)))

            # Atualiza Cabeçalhos
            f.seek(8)
            for i in range(file_count):
                f.seek(64 + 4, 1) # pula nome e ID
                f.write(struct.pack(endian + 'I', new_metadata[i][2])) # comp_size
                f.write(struct.pack(endian + 'I', new_metadata[i][1])) # orig_size
                f.write(struct.pack(endian + 'I', new_metadata[i][0])) # offset

        if logger: logger(t("recreation_success", file=path_obj.name), color=COLOR_LOG_GREEN)
    except Exception as e:
        if logger: logger(t("recreation_error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# FLET FILE PICKERS
# ==============================================================================

fp_extract = ft.FilePicker(on_result=lambda e: [extract_arc(f.path) for f in e.files] if e.files else None)
fp_rebuild = ft.FilePicker(on_result=lambda e: [rebuild_arc(f.path) for f in e.files] if e.files else None)

# ==============================================================================
# REGISTRO
# ==============================================================================
def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, get_option, current_lang, host_page
    logger = log_func
    get_option = option_getter
    current_lang = host_language
    host_page = page

    if host_page:
        host_page.overlay.extend([fp_extract, fp_rebuild])
        host_page.update()

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
            {"label": t("extract_file"), "action": lambda: fp_extract.pick_files(allowed_extensions=["arc"])},
            {"label": t("rebuild_file"), "action": lambda: fp_rebuild.pick_files(allowed_extensions=["arc"])},
        ]
    }