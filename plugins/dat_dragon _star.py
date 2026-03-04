import os
import re
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
        "plugin_name": "GDAT - Dragon Star VARNIR",
        "plugin_description": "Extrai e reconstrói arquivos .dat (GDAT) do jogo Dragon Star VARNIR",
        "extract_file": "Extrair GDAT",
        "rebuild_file": "Reconstruir GDAT",
        "select_gdat_file": "Selecione o arquivo .dat",
        "select_extracted_folder": "Selecione a pasta com arquivos extraídos",
        "gdat_files": "Arquivos DAT",
        "all_files": "Todos os arquivos",
        "invalid_gdat": "Arquivo não é um GDAT válido.",
        "total_files_prefix": "[+] Total de arquivos: {count}",
        "extracted_prefix": "[+] Extraído: {filename}",
        "extraction_success": "Extração finalizada! Arquivos salvos em: {path}",
        "rebuild_success": "Repack finalizado! Arquivo salvo em: {path}",
        "invalid_original_gdat": "Arquivo GDAT original inválido.",
        "invalid_extracted_folder": "Pasta extraída inválida.",
        "headers_read": "[+] Cabeçalhos originais lidos (144 bytes por entrada quando presentes).",
        "recompress_log": "[+] Índice {index:04d}: recompress (raw={raw} / zlib={zlib})",
        "raw_file_log": "[+] Índice {index:04d}: usando arquivo {filename} (raw)",
        "missing_file_log": "[-] Índice {index:04d}: arquivo faltando na pasta extraída -> reutilizando bloco original",
        "repack_saved": "[+] Repacked salvo em: {path}",
        "unexpected_error": "Erro inesperado: {error}",
        "select_valid_file": "Selecione um arquivo válido.",
        "select_valid_gdat": "Selecione um GDAT original válido.",
        "select_valid_folder": "Selecione a pasta extraída correspondente.",
        "extracting_to": "Extraindo para: {path}",
        "recreating_to": "Reconstruindo a partir de: {path}",
        "completed": "Concluído",
        "error": "Erro",
        "cancel_button": "Cancelar",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "file_processed": "Arquivo processado: {path}"
    },
    "en_US": {
        "plugin_name": "GDAT - Dragon Star VARNIR",
        "plugin_description": "Extracts and rebuilds .dat (GDAT) files from Dragon Star VARNIR game",
        "extract_file": "Extract GDAT",
        "rebuild_file": "Rebuild GDAT",
        "select_gdat_file": "Select .dat file",
        "select_extracted_folder": "Select folder with extracted files",
        "gdat_files": "DAT Files",
        "all_files": "All files",
        "invalid_gdat": "File is not a valid GDAT.",
        "total_files_prefix": "[+] Total files: {count}",
        "extracted_prefix": "[+] Extracted: {filename}",
        "extraction_success": "Extraction completed! Files saved in: {path}",
        "rebuild_success": "Repack completed! File saved at: {path}",
        "invalid_original_gdat": "Invalid original GDAT file.",
        "invalid_extracted_folder": "Invalid extracted folder.",
        "headers_read": "[+] Original headers read (144 bytes per entry when present).",
        "recompress_log": "[+] Index {index:04d}: recompress (raw={raw} / zlib={zlib})",
        "raw_file_log": "[+] Index {index:04d}: using file {filename} (raw)",
        "missing_file_log": "[-] Index {index:04d}: file missing in extracted folder -> reusing original block",
        "repack_saved": "[+] Repacked saved at: {path}",
        "unexpected_error": "Unexpected error: {error}",
        "select_valid_file": "Select a valid file.",
        "select_valid_gdat": "Select a valid original GDAT.",
        "select_valid_folder": "Select the corresponding extracted folder.",
        "extracting_to": "Extracting to: {path}",
        "recreating_to": "Rebuilding from: {path}",
        "completed": "Completed",
        "error": "Error",
        "cancel_button": "Cancel",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "file_processed": "File processed: {path}"
    },
    "es_ES": {
        "plugin_name": "GDAT - Dragon Star VARNIR",
        "plugin_description": "Extrae y reconstruye archivos .dat (GDAT) del juego Dragon Star VARNIR",
        "extract_file": "Extraer GDAT",
        "rebuild_file": "Reconstruir GDAT",
        "select_gdat_file": "Seleccionar archivo .dat",
        "select_extracted_folder": "Seleccionar carpeta con archivos extraídos",
        "gdat_files": "Archivos DAT",
        "all_files": "Todos los archivos",
        "invalid_gdat": "El archivo no es un GDAT válido.",
        "total_files_prefix": "[+] Archivos totales: {count}",
        "extracted_prefix": "[+] Extraído: {filename}",
        "extraction_success": "¡Extracción completada! Archivos guardados en: {path}",
        "rebuild_success": "¡Reempaquetado completado! Archivo guardado en: {path}",
        "invalid_original_gdat": "Archivo GDAT original inválido.",
        "invalid_extracted_folder": "Carpeta extraída inválida.",
        "headers_read": "[+] Cabeceras originales leídas (144 bytes por entrada cuando están presentes).",
        "recompress_log": "[+] Índice {index:04d}: recomprimir (raw={raw} / zlib={zlib})",
        "raw_file_log": "[+] Índice {index:04d}: usando archivo {filename} (raw)",
        "missing_file_log": "[-] Índice {index:04d}: archivo faltante en la carpeta extraída -> reutilizando bloque original",
        "repack_saved": "[+] Reempaquetado guardado en: {path}",
        "unexpected_error": "Error inesperado: {error}",
        "select_valid_file": "Seleccione un archivo válido.",
        "select_valid_gdat": "Seleccione un GDAT original válido.",
        "select_valid_folder": "Seleccione la carpeta extraída correspondiente.",
        "extracting_to": "Extrayendo a: {path}",
        "recreating_to": "Reconstruyendo desde: {path}",
        "completed": "Completado",
        "error": "Error",
        "cancel_button": "Cancelar",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "file_processed": "Archivo procesado: {path}"
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

def pick_folder_topmost(title):
    """Cria uma janela Tk invisível, força ela pro topo e abre o diálogo de pasta."""
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    folder_path = filedialog.askdirectory(parent=root, title=title)
    root.destroy()
    return folder_path

# ==============================================================================
# FUNÇÕES PRINCIPAIS (adaptadas para usar logger)
# ==============================================================================

def detect_extension(data):
    if len(data) < 4:
        return "bin"

    raw = data[:4]
    reversed_bytes = raw[::-1]
    clean = reversed_bytes.replace(b'\x00', b'')

    try:
        ext = clean.decode("ascii", errors="ignore").strip()
        if ext and ext.isprintable():
            return ext.lower()
    except:
        pass

    return "bin"

def extract_gdat(filepath):
    """Extracts all files from a GDAT container"""
    with open(filepath, "rb") as f:
        magic = f.read(4)
        if magic != b"GDAT":
            raise ValueError(t("invalid_gdat"))

        total_files = struct.unpack("<I", f.read(4))[0]
        logger(t("total_files_prefix", count=total_files), color=COLOR_LOG_YELLOW)

        entries = []
        for i in range(total_files):
            offset = struct.unpack("<I", f.read(4))[0]
            size = struct.unpack("<I", f.read(4))[0]
            entries.append((offset, size))

        base_dir = os.path.dirname(filepath)
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        output_folder = os.path.join(base_dir, base_name)
        os.makedirs(output_folder, exist_ok=True)

        logger(t("extracting_to", path=output_folder), color=COLOR_LOG_YELLOW)

        for index, (offset, size) in enumerate(entries):
            f.seek(offset)
            data_suja = f.read(size)

            ext = detect_extension(data_suja)
            compressed_data = data_suja[144:]
            try:
                data = zlib.decompress(compressed_data)
                is_compressed = "_unzlib"
            except:
                data = data_suja
                is_compressed = "_nozlib"
            filename = f"{index:04d}{is_compressed}.{ext}"
            output_path = os.path.join(output_folder, filename)

            with open(output_path, "wb") as out:
                out.write(data)

            logger(t("extracted_prefix", filename=filename))

        return output_folder

def repack_gdat(original_gdat_path, extracted_folder):
    """Rebuilds the GDAT file using files from the extracted folder"""
    # Read original header to get total_files and original entries
    with open(original_gdat_path, "rb") as f:
        magic = f.read(4)
        if magic != b"GDAT":
            raise ValueError(t("invalid_gdat"))

        total_files = struct.unpack("<I", f.read(4))[0]
        logger(t("total_files_prefix", count=total_files), color=COLOR_LOG_YELLOW)

        orig_entries = []
        for i in range(total_files):
            offset = struct.unpack("<I", f.read(4))[0]
            size = struct.unpack("<I", f.read(4))[0]
            orig_entries.append((offset, size))

        # Read each original block to recover the first 144 bytes headers
        original_blocks = []
        header_chunks = []
        for idx, (offset, size) in enumerate(orig_entries):
            f.seek(offset)
            data_suja = f.read(size)
            original_blocks.append(data_suja)
            if len(data_suja) >= 144:
                header_chunks.append(data_suja[:144])
            else:
                header_chunks.append(data_suja)  # rare case, use all

        logger(t("headers_read"), color=COLOR_LOG_YELLOW)

    # Map extracted files by index from folder
    extracted_files = {}
    pattern = re.compile(r"^(\d{4})(?:(_unzlib|_nozlib))\.(.+)$", re.IGNORECASE)
    for fname in os.listdir(extracted_folder):
        m = pattern.match(fname)
        if m:
            idx = int(m.group(1))
            suffix = m.group(2) or ""
            ext = m.group(3)
            extracted_files[idx] = (fname, suffix, ext)

    # Prepare output path
    base_dir = os.path.dirname(original_gdat_path)
    base_name = os.path.splitext(os.path.basename(original_gdat_path))[0]
    output_path = os.path.join(base_dir, base_name + "_repacked.dat")

    logger(t("recreating_to", path=extracted_folder), color=COLOR_LOG_YELLOW)

    # Write new GDAT
    with open(output_path, "wb") as out:
        # Write magic and total_files
        out.write(b"GDAT")
        out.write(struct.pack("<I", total_files))

        # Reserve space for the entry table (offset+size) -> 8 bytes per entry
        table_offset = out.tell()
        out.write(b"\x00" * (8 * total_files))

        # Write data entries and store new offsets/sizes
        new_entries = []
        current_offset = out.tell()
        for i in range(total_files):
            if i in extracted_files:
                fname, suffix, ext = extracted_files[i]
                file_path = os.path.join(extracted_folder, fname)
                with open(file_path, "rb") as f:
                    file_data = f.read()

                if suffix.lower() == "_unzlib":
                    # Create editable header
                    if i < len(header_chunks):
                        header = bytearray(header_chunks[i])
                    else:
                        header = bytearray(144)

                    compressed = zlib.compress(file_data, level=9)
                    uncompressed_size = len(file_data)
                    compressed_size = len(compressed)

                    struct.pack_into(">I", header, 132, uncompressed_size)
                    struct.pack_into(">I", header, 136, compressed_size)

                    entry_bytes = bytes(header) + compressed

                    logger(t("recompress_log",
                            index=i,
                            raw=uncompressed_size,
                            zlib=compressed_size))
                else:
                    # _nozlib: write raw
                    entry_bytes = file_data
                    logger(t("raw_file_log", index=i, filename=fname))
            else:
                # Fallback: use original block
                entry_bytes = original_blocks[i]
                logger(t("missing_file_log", index=i), color=COLOR_LOG_RED)

            # Write entry bytes
            out.seek(current_offset)
            out.write(entry_bytes)
            new_entries.append((current_offset, len(entry_bytes)))
            current_offset += len(entry_bytes)

        # Write the entry table
        out.seek(table_offset)
        for offset, size in new_entries:
            out.write(struct.pack("<II", offset, size))

    logger(t("repack_saved", path=output_path), color=COLOR_LOG_GREEN)
    return output_path

# ==============================================================================
# AÇÕES DOS COMANDOS
# ==============================================================================

def action_extract():
    filepath = pick_file_topmost(t("select_gdat_file"), [(t("gdat_files"), "*.dat"), (t("all_files"), "*.*")])

    if not filepath:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(filepath)), color=COLOR_LOG_YELLOW)

    try:
        out_dir = extract_gdat(filepath)
        logger(t("extraction_success", path=out_dir), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

def action_rebuild():
    # First, ask for original GDAT file
    original = pick_file_topmost(t("select_gdat_file"), [(t("gdat_files"), "*.dat"), (t("all_files"), "*.*")])

    if not original:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    # Then ask for extracted folder
    folder = pick_folder_topmost(t("select_extracted_folder"))

    if not folder:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(original)), color=COLOR_LOG_YELLOW)

    try:
        output_path = repack_gdat(original, folder)
        logger(t("rebuild_success", path=output_path), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

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
            {"label": t("rebuild_file"), "action": action_rebuild}
        ]
    }