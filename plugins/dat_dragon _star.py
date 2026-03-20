import os
import re
import struct
import zlib
import flet as ft

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
        "headers_read": "[+] Cabeçalhos originais lidos (144 bytes por entrada quando presentes).",
        "recompress_log": "[+] Índice {index:04d}: recompress (raw={raw} / zlib={zlib})",
        "raw_file_log": "[+] Índice {index:04d}: usando arquivo {filename} (raw)",
        "missing_file_log": "[-] Índice {index:04d}: arquivo faltando na pasta extraída -> reutilizando bloco original",
        "repack_saved": "[+] Repacked salvo em: {path}",
        "unexpected_error": "Erro inesperado: {error}",
        "extracting_to": "Extraindo para: {path}",
        "recreating_to": "Reconstruindo a partir de: {path}",
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
        "headers_read": "[+] Original headers read (144 bytes per entry when present).",
        "recompress_log": "[+] Index {index:04d}: recompress (raw={raw} / zlib={zlib})",
        "raw_file_log": "[+] Index {index:04d}: using file {filename} (raw)",
        "missing_file_log": "[-] Index {index:04d}: file missing in extracted folder -> reusing original block",
        "repack_saved": "[+] Repacked saved at: {path}",
        "unexpected_error": "Unexpected error: {error}",
        "extracting_to": "Extracting to: {path}",
        "recreating_to": "Rebuilding from: {path}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "file_processed": "File processed: {path}"
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

logger = None
get_option = None
current_lang = "pt_BR"

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# LÓGICA DE NEGÓCIO (MANTIDA ORIGINAL)
# ==============================================================================

def detect_extension(data):
    if len(data) < 4: return "bin"
    raw = data[:4]
    reversed_bytes = raw[::-1]
    clean = reversed_bytes.replace(b'\x00', b'')
    try:
        ext = clean.decode("ascii", errors="ignore").strip()
        if ext and ext.isprintable(): return ext.lower()
    except: pass
    return "bin"

def run_extract(filepath):
    if not filepath:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(filepath)), color=COLOR_LOG_YELLOW)

    try:
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

        logger(t("extraction_success", path=output_folder), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

def run_rebuild(original_gdat_path, extracted_folder):
    if not original_gdat_path or not extracted_folder:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(original_gdat_path)), color=COLOR_LOG_YELLOW)

    try:
        with open(original_gdat_path, "rb") as f:
            magic = f.read(4)
            if magic != b"GDAT": raise ValueError(t("invalid_gdat"))

            total_files = struct.unpack("<I", f.read(4))[0]
            logger(t("total_files_prefix", count=total_files), color=COLOR_LOG_YELLOW)

            orig_entries = []
            for i in range(total_files):
                offset = struct.unpack("<I", f.read(4))[0]
                size = struct.unpack("<I", f.read(4))[0]
                orig_entries.append((offset, size))

            original_blocks = []
            header_chunks = []
            for idx, (offset, size) in enumerate(orig_entries):
                f.seek(offset)
                data_suja = f.read(size)
                original_blocks.append(data_suja)
                header_chunks.append(data_suja[:144] if len(data_suja) >= 144 else data_suja)

            logger(t("headers_read"), color=COLOR_LOG_YELLOW)

        extracted_files = {}
        pattern = re.compile(r"^(\d{4})(?:(_unzlib|_nozlib))\.(.+)$", re.IGNORECASE)
        for fname in os.listdir(extracted_folder):
            m = pattern.match(fname)
            if m:
                idx = int(m.group(1))
                extracted_files[idx] = (fname, m.group(2) or "", m.group(3))

        base_dir = os.path.dirname(original_gdat_path)
        base_name = os.path.splitext(os.path.basename(original_gdat_path))[0]
        output_path = os.path.join(base_dir, base_name + "_repacked.dat")

        with open(output_path, "wb") as out:
            out.write(b"GDAT")
            out.write(struct.pack("<I", total_files))
            table_offset = out.tell()
            out.write(b"\x00" * (8 * total_files))

            new_entries = []
            current_offset = out.tell()
            for i in range(total_files):
                if i in extracted_files:
                    fname, suffix, ext = extracted_files[i]
                    file_path = os.path.join(extracted_folder, fname)
                    with open(file_path, "rb") as f:
                        file_data = f.read()

                    if suffix.lower() == "_unzlib":
                        header = bytearray(header_chunks[i] if i < len(header_chunks) else 144)
                        compressed = zlib.compress(file_data, level=9)
                        struct.pack_into(">I", header, 132, len(file_data))
                        struct.pack_into(">I", header, 136, len(compressed))
                        entry_bytes = bytes(header) + compressed
                        logger(t("recompress_log", index=i, raw=len(file_data), zlib=len(compressed)))
                    else:
                        entry_bytes = file_data
                        logger(t("raw_file_log", index=i, filename=fname))
                else:
                    entry_bytes = original_blocks[i]
                    logger(t("missing_file_log", index=i), color=COLOR_LOG_RED)

                out.seek(current_offset)
                out.write(entry_bytes)
                new_entries.append((current_offset, len(entry_bytes)))
                current_offset += len(entry_bytes)

            out.seek(table_offset)
            for offset, size in new_entries:
                out.write(struct.pack("<II", offset, size))

        logger(t("rebuild_success", path=output_path), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# ENTRY POINT (FLET)
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR"):
    global logger, get_option, current_lang
    logger = log_func
    get_option = option_getter
    current_lang = host_language

    # Variável temporária para o Rebuild que exige dois passos
    rebuild_context = {"original_dat": None}

    # Pickers
    fp_extract = ft.FilePicker(on_result=lambda e: run_extract(e.files[0].path) if e.files else None)
    
    # Lógica do Rebuild: Passo 1 (DAT) -> Passo 2 (Pasta)
    def on_rebuild_folder_result(e):
        if e.path and rebuild_context["original_dat"]:
            run_rebuild(rebuild_context["original_dat"], e.path)
            rebuild_context["original_dat"] = None

    def on_rebuild_dat_result(e):
        if e.files:
            rebuild_context["original_dat"] = e.files[0].path
            fp_rebuild_folder.get_directory_path(window_title=t("select_extracted_folder"))

    fp_rebuild_dat = ft.FilePicker(on_result=on_rebuild_dat_result)
    fp_rebuild_folder = ft.FilePicker(on_result=on_rebuild_folder_result)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "pickers": [fp_extract, fp_rebuild_dat, fp_rebuild_folder],
        "commands": [
            {
                "label": t("extract_file"), 
                "action": lambda: fp_extract.pick_files(
                    allowed_extensions=["dat"], 
                    dialog_title=t("select_gdat_file")
                )
            },
            {
                "label": t("rebuild_file"), 
                "action": lambda: fp_rebuild_dat.pick_files(
                    allowed_extensions=["dat"], 
                    dialog_title=t("select_gdat_file")
                )
            }
        ]
    }