import os
import struct
import zlib
import flet as ft
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "FEAR 1 - CAT/MATCAT Tool",
        "plugin_description": "Extrai e recria contêineres (.CAT/.MATCAT) do FEAR 1 (PS3/X360)",
        "extract_file": "Extrair Arquivo (CAT → Pasta)",
        "rebuild_file": "Reconstruir Arquivo (Pasta → CAT)",
        "select_fear_file": "Selecione o arquivo .CAT ou .MATCAT",
        "log_extract_start": "Iniciando extração de: {name}",
        "log_rebuild_start": "Iniciando reconstrução de: {name}",
        "log_processing": "Processado: {file} | Off: {pos}",
        "log_success_ext": "Extração concluída em: {path}",
        "log_success_reb": "Arquivo recriado: {path}",
        "err_filelist": "Erro: Arquivo '_filelist.txt' não encontrado.",
        "err_missing_file": "Erro: Arquivo {file} não encontrado na pasta.",
        "err_unexpected": "Erro inesperado: {error}",
    },
    "en_US": {
        "plugin_name": "FEAR 1 - CAT/MATCAT Tool",
        "plugin_description": "Extracts and recreates FEAR 1 containers (.CAT/.MATCAT)",
        "extract_file": "Extract File (CAT → Folder)",
        "rebuild_file": "Rebuild File (Folder → CAT)",
        "select_fear_file": "Select .CAT or .MATCAT file",
        "log_extract_start": "Extracting: {name}",
        "log_rebuild_start": "Rebuilding: {name}",
        "log_processing": "Processed: {file} | Off: {pos}",
        "log_success_ext": "Extraction finished at: {path}",
        "log_success_reb": "File recreated at: {path}",
        "err_filelist": "Error: '_filelist.txt' not found.",
        "err_missing_file": "Error: File {file} not found in folder.",
        "err_unexpected": "Unexpected error: {error}",
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

logger = None
current_lang = "pt_BR"
host_page = None

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# AUXILIARES
# ==============================================================================

def pad_to_32_bytes(data: bytes) -> bytes:
    padding_length = (32 - (len(data) % 32)) % 32
    return data + (b'\x00' * padding_length)

# ==============================================================================
# LÓGICA DE EXTRAÇÃO
# ==============================================================================

def run_extraction(file_path: str):
    try:
        base_path = Path(file_path)
        extract_folder = base_path.with_suffix('')
        file_list_path = base_path.with_name(f"{base_path.stem}_filelist.txt")
        
        if logger: logger(t("log_extract_start", name=base_path.name), color=COLOR_LOG_YELLOW)

        with open(file_path, 'rb') as f:
            f.seek(4)
            start_pointers = struct.unpack('>I', f.read(4))[0]
            num_pointers = struct.unpack('>I', f.read(8)[4:8])[0] # seek(8) + read(4)
            
            f.seek(12)
            start_names = struct.unpack('>I', f.read(4))[0]
            size_names = struct.unpack('>I', f.read(4))[0]

            f.seek(start_names)
            names_block = f.read(size_names).replace(b'MSF\x01', b'wav')
            file_names = names_block.split(b'\x00')

            extract_folder.mkdir(parents=True, exist_ok=True)

            with open(file_list_path, 'w', encoding='utf-8') as fl:
                for i in range(num_pointers):
                    f.seek(start_pointers + i * 16)
                    f.read(4) # Identificador
                    pointer = struct.unpack('>I', f.read(4))[0]
                    uncomp_size = struct.unpack('>I', f.read(4))[0]
                    comp_size = struct.unpack('>I', f.read(4))[0]

                    f.seek(pointer)
                    compressed_data = f.read(comp_size)
                    
                    name = file_names[i].decode('utf-8')
                    output_path = extract_folder / name
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        data = zlib.decompress(compressed_data)
                        fl.write(f"{name}\n")
                    except zlib.error:
                        data = compressed_data
                        fl.write(f"{name},uncompressed\n")

                    output_path.write_bytes(data)
                    if logger: logger(t("log_processing", file=name, pos=hex(pointer).upper()))

        if logger: logger(t("log_success_ext", path=extract_folder.name), color=COLOR_LOG_GREEN)

    except Exception as e:
        if logger: logger(t("err_unexpected", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# LÓGICA DE RECONSTRUÇÃO
# ==============================================================================

def run_rebuild(file_path: str):
    try:
        base_path = Path(file_path)
        folder_path = base_path.with_suffix('')
        new_file_path = base_path.with_name(f"{base_path.stem}_mod{base_path.suffix}")
        file_list_path = base_path.with_name(f"{base_path.stem}_filelist.txt")

        if not file_list_path.exists():
            if logger: logger(t("err_filelist"), color=COLOR_LOG_RED)
            return

        if logger: logger(t("log_rebuild_start", name=base_path.name), color=COLOR_LOG_YELLOW)

        # Ler cabeçalho original
        with open(file_path, 'rb') as orig:
            orig.seek(20)
            data_offset = struct.unpack('>I', orig.read(4))[0]
            orig.seek(0)
            header = orig.read(data_offset)

        file_infos = []
        current_ptr = data_offset

        with open(new_file_path, 'wb') as new_f:
            new_f.write(header)
            
            lines = file_list_path.read_text(encoding='utf-8').splitlines()
            for line in lines:
                is_uncompressed = ',uncompressed' in line
                fname = line.replace(',uncompressed', '').strip()
                local_file = folder_path / fname

                if not local_file.exists():
                    if logger: logger(t("err_missing_file", file=fname), color=COLOR_LOG_RED)
                    continue

                data = local_file.read_bytes()
                uncomp_size = len(data)

                if not is_uncompressed:
                    data = zlib.compress(data)
                
                comp_size = len(data)
                padded_data = pad_to_32_bytes(data)
                
                file_infos.append((current_ptr, uncomp_size, comp_size))
                new_f.write(padded_data)
                current_ptr += len(padded_data)

        # Atualizar ponteiros no cabeçalho do novo arquivo
        with open(new_file_path, 'r+b') as mod_f:
            mod_f.seek(32)
            for info in file_infos:
                mod_f.read(4) # Identificador
                mod_f.write(struct.pack('>I', info[0])) # Pointer
                mod_f.write(struct.pack('>I', info[1])) # Uncompressed Size
                mod_f.write(struct.pack('>I', info[2])) # Compressed Size

        if logger: logger(t("log_success_reb", path=new_file_path.name), color=COLOR_LOG_GREEN)

    except Exception as e:
        if logger: logger(t("err_unexpected", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# INTERFACE FLET
# ==============================================================================

fp_extract = ft.FilePicker(on_result=lambda e: run_extraction(e.files[0].path) if e.files else None)
fp_rebuild = ft.FilePicker(on_result=lambda e: run_rebuild(e.files[0].path) if e.files else None)

def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, current_lang, host_page
    logger = log_func
    current_lang = host_language
    host_page = page

    if host_page:
        host_page.overlay.extend([fp_extract, fp_rebuild])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {
                "label": t("extract_file"), 
                "action": lambda: fp_extract.pick_files(
                    allowed_extensions=["cat", "matcat"],
                    dialog_title=t("select_fear_file")
                )
            },
            {
                "label": t("rebuild_file"), 
                "action": lambda: fp_rebuild.pick_files(
                    allowed_extensions=["cat", "matcat"],
                    dialog_title=t("select_fear_file")
                )
            },
        ]
    }