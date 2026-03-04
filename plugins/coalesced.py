import os
import struct
from pathlib import Path

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "Coalesced UE3 - Extrator e Reinseridor",
        "plugin_description": "Extrai e reinsere arquivos INI de Coalesced (Unreal Engine 3)",
        "version": "Versão do Coalesced",
        "extract_command": "Extrair Arquivo",
        "recreate_command": "Reconstruir Arquivo",
        "extracting_to": "Extraindo para: {path}",
        "success": "Sucesso",
        "extraction_success": "Extração concluída com sucesso!",
        "extraction_error": "Erro na extração: {error}",
        "recreation_success": "Arquivo recriado com sucesso!",
        "recreation_error": "Erro na recriação: {error}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "select_original_file": "Selecione o arquivo binário original",
        "select_extracted_folder": "Selecione a pasta extraída",
        "select_output_file": "Selecione onde salvar o novo arquivo",
        "recreating_to": "Recriando: {path}",
        "cancelled": "Seleção cancelada.",
        "error_generic": "Erro: {error}",
        "processing": "Processando: {name}...",
        "file_processed": "Arquivo processado: {path}"
    },
    "en_US": {
        "plugin_name": "Coalesced UE3 - Extractor and Reinserter",
        "plugin_description": "Extracts and reinserts INI files from Coalesced (Unreal Engine 3)",
        "version": "Coalesced Version",
        "extract_command": "Extract File",
        "recreate_command": "Rebuild File",
        "extracting_to": "Extracting to: {path}",
        "success": "Success",
        "extraction_success": "Extraction completed successfully!",
        "extraction_error": "Extraction error: {error}",
        "recreation_success": "File recreated successfully!",
        "recreation_error": "Recreation error: {error}",
        "file_not_found": "File not found: {file}",
        "select_original_file": "Select original binary file",
        "select_extracted_folder": "Select extracted folder",
        "select_output_file": "Select where to save the new file",
        "recreating_to": "Recreating: {path}",
        "cancelled": "Selection cancelled.",
        "error_generic": "Error: {error}",
        "processing": "Processing: {name}...",
        "file_processed": "File processed: {path}"
    },
    "es_ES": {
        "plugin_name": "Coalesced UE3 - Extractor y Reinseridor",
        "plugin_description": "Extrae y reinserte archivos INI de Coalesced (Unreal Engine 3)",
        "version": "Versión de Coalesced",
        "extract_command": "Extraer Archivo",
        "recreate_command": "Reconstruir Archivo",
        "extracting_to": "Extrayendo a: {path}",
        "success": "Éxito",
        "extraction_success": "¡Extracción completada con éxito!",
        "extraction_error": "Error en extracción: {error}",
        "recreation_success": "¡Archivo recreado con éxito!",
        "recreation_error": "Error en recreación: {error}",
        "file_not_found": "Archivo no encontrado: {file}",
        "select_original_file": "Seleccionar archivo binario original",
        "select_extracted_folder": "Seleccionar carpeta extraída",
        "select_output_file": "Seleccionar dónde guardar el nuevo archivo",
        "recreating_to": "Recreando: {path}",
        "cancelled": "Selección cancelada.",
        "error_generic": "Error: {error}",
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
import tkinter as tk
from tkinter import filedialog

def pick_file_topmost(title, file_types):
    """Cria uma janela Tk invisível, força ela pro topo e abre o diálogo."""
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    file_path = filedialog.askopenfilename(parent=root, title=title, filetypes=file_types)
    root.destroy()
    return file_path

# ==============================================================================
# LÓGICA DE NEGÓCIO (CONVERSÃO) – Adaptada para usar logger e sem messagebox
# ==============================================================================

def read_binary_file(file_path):
    tipo = get_option("tipo_arquivo")
    
    if tipo == "1.0":
        try:
            input_path = Path(file_path)
            output_folder = input_path.parent / input_path.stem
            output_folder.mkdir(exist_ok=True)

            logger(t("extracting_to", path=str(output_folder)), color=COLOR_LOG_YELLOW)

            with open(file_path, 'rb') as f:
                f.seek(4)

                while True:
                    name_len_data = f.read(4)
                    if not name_len_data:
                        break

                    name_len = struct.unpack('>I', name_len_data)[0]
                    name = f.read(name_len).strip(b'\x00').decode('ansi').replace('..\\', '').replace('../', '')
                
                    content_len_data = f.read(4)
                    if not content_len_data:
                        break
                    content_len = struct.unpack('>I', content_len_data)[0]
                    content = f.read(content_len).strip(b'\x00')

                    output_path = output_folder / name
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(output_path, 'wb') as out_file:
                        out_file.write(content)

                    logger(t("file_processed", path=str(output_path)))

            logger(t("extraction_success"), color=COLOR_LOG_GREEN)
            return True

        except Exception as e:
            logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)
            return False
    
    elif tipo == "2.0":
        try:
            output_base_dir = os.path.splitext(file_path)[0]
            os.makedirs(output_base_dir, exist_ok=True)
            
            logger(t("extracting_to", path=output_base_dir), color=COLOR_LOG_YELLOW)

            with open(file_path, 'rb') as f:
                f.seek(4)

                while True:
                    filename_length_data = f.read(4)
                    if not filename_length_data:
                        break
                    
                    filename_length = struct.unpack('>I', filename_length_data)[0]
                    filename_data = f.read(filename_length)
                    filename = filename_data.strip(b'\x00').decode('ansi')
                
                    safe_path = os.path.join(output_base_dir, filename.lstrip('..\\'))
                    full_path = os.path.abspath(safe_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                    num_items = struct.unpack('>I', f.read(4))[0]
                        
                    with open(full_path, 'w', encoding='ansi') as out_file:
                        
                        if num_items == 0:
                            out_file.write("")
                        
                        else:
                            
                            for _ in range(num_items):
                                item_name_length = struct.unpack('>I', f.read(4))[0]
                                item_name = f.read(item_name_length).strip(b'\x00').decode('ansi', errors='ignore')
                                item_name = item_name.replace("\n", "\\n")
                                item_name = item_name.replace("\r", "\\r")
                                out_file.write(f"[{item_name}]\n")
                    
                                num_subitems = struct.unpack('>I', f.read(4))[0]
                                for i in range(num_subitems):
                                    
                                    read4sub1 = f.read(4)
                                    
                                    if read4sub1[0] == 0xFF:
                                        char_count = struct.unpack('>I', read4sub1)[0]
                                        subitem_title_length = (4294967295 - char_count) * 2 + 2
                                        subitem_title = f.read(subitem_title_length).decode('utf-16le').rstrip('\x00')
                                        
                                    else:
                                        subitem_title_length = struct.unpack('>I', read4sub1)[0]
                                        subitem_title = f.read(subitem_title_length).strip(b'\x00').decode('ansi', errors='ignore')
                                    subitem_title = subitem_title.replace("\n", "\\n")
                                    subitem_title = subitem_title.replace("\r", "\\r")
                            
                                    read4sub2 = f.read(4)
                                    
                                    if read4sub2[0] == 0xFF:
                                        char_count = struct.unpack('>I', read4sub2)[0]
                                        subitem_value_length = (4294967295 - char_count) * 2 + 2
                                        subitem_value = f.read(subitem_value_length).decode('utf-16le').rstrip('\x00')
                                        
                                    else:
                                        subitem_value_length = struct.unpack('>I', read4sub2)[0]
                                        subitem_value = f.read(subitem_value_length).strip(b'\x00').decode('ansi', errors='ignore')
                                    subitem_value = subitem_value.replace("\n", "\\n")
                                    subitem_value = subitem_value.replace("\r", "\\r")
                            
                                    out_file.write(f"{subitem_title}={subitem_value}\n")
                                
                                if _ + 1 < num_items:
                                    out_file.write("\n")
                    
                    logger(t("file_processed", path=full_path))
            
            logger(t("extraction_success"), color=COLOR_LOG_GREEN)
            return True
                
        except Exception as e:
            logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)
            return False
                
    else:  # Versão 3.0
        try:
            def read_name(file, char_count):
                name_length = char_count * 2 + 2
                name_data = file.read(name_length)
                return name_data.decode('utf-16le').rstrip('\x00')
    
            output_dir = os.path.splitext(file_path)[0]
            os.makedirs(output_dir, exist_ok=True)
    
            logger(t("extracting_to", path=output_dir), color=COLOR_LOG_YELLOW)

            with open(file_path, 'rb') as f:
                endiam_check = f.read(2)
                if endiam_check == b'\x00\x00':
                    endianess = '>'
                    byte_order = 'big'
                else:
                    endianess = '<'
                    byte_order = 'little'
                f.seek(-2, 1)
                
                total_files = struct.unpack(f'{endianess}I', f.read(4))[0]
    
                for _ in range(total_files):
                    char_count_bytes = f.read(4)
                    raw_value = int.from_bytes(char_count_bytes, byteorder=byte_order)
                    char_count = 4294967295 - raw_value
                    file_name = read_name(f, char_count)
                    file_name = os.path.normpath(file_name.replace("..\\", ""))
                    
                    file_path_out = os.path.join(output_dir, file_name)
                    os.makedirs(os.path.dirname(file_path_out), exist_ok=True)
    
                    num_items = struct.unpack(f'{endianess}I', f.read(4))[0]
    
                    items = []
                    for _ in range(num_items):
                        char_count_bytes_item = f.read(4)
                        raw_value_item = int.from_bytes(char_count_bytes_item, byteorder=byte_order)
                        if raw_value_item == 0:
                            item_name = ""
                        else:
                            char_count_item = 4294967295 - raw_value_item
                            item_name = read_name(f, char_count_item)
    
                        num_subitems = struct.unpack(f'{endianess}I', f.read(4))[0]
    
                        subitems = []
                        for _ in range(num_subitems):
                            char_count_bytes_sub_item1 = f.read(4)
                            raw_value_sub_item1 = int.from_bytes(char_count_bytes_sub_item1, byteorder=byte_order)
                            if raw_value_sub_item1 == 0:
                                sub_item_1 = ""
                            else:
                                char_count_sub_item1 = 4294967295 - raw_value_sub_item1
                                sub_item_1 = read_name(f, char_count_sub_item1)
    
                            char_count_bytes_sub_item2 = f.read(4)
                            raw_value_sub_item2 = int.from_bytes(char_count_bytes_sub_item2, byteorder=byte_order)
                            if raw_value_sub_item2 == 0:
                                sub_item_2 = ""
                            else:
                                char_count_sub_item2 = 4294967295 - raw_value_sub_item2
                                sub_item_2 = read_name(f, char_count_sub_item2)
    
                            subitems.append((sub_item_1, sub_item_2))
    
                        items.append((item_name, subitems))
    
                    # Salvar conteúdo em arquivos
                    with open(file_path_out, 'w', encoding='utf-8') as out_file:
                        total_items = len(items)
                    
                        for index, (item_name, subitems) in enumerate(items):
                            total_subitems = len(subitems)
                            if index > 0:
                                out_file.write(f"[{item_name}]\n")
                                for i, (sub_item_1, sub_item_2) in enumerate(subitems):
                                
                                    sub_item_2 = sub_item_2.replace("\n", "\\n")
                                    sub_item_2 = sub_item_2.replace("\r", "\\r")
                                    total_items_subitems = len(subitems)
                                    out_file.write(f"{sub_item_1}=")
                                    if index < total_items -1:
                                        out_file.write(f"{sub_item_2}\n")
                                    else:
                                        if i < total_items_subitems -1:
                                            out_file.write(f"{sub_item_2}\n")
                                        else:
                                            out_file.write(f"{sub_item_2}")
                            
                                if index < total_items -1:
                                    out_file.write(f"\n")
                                        
                            else:
                                if total_subitems > 0:
                                    out_file.write(f"[{item_name}]\n")
                                    for i, (sub_item_1, sub_item_2) in enumerate(subitems):
                                
                                        sub_item_2 = sub_item_2.replace("\n", "\\n")
                                        sub_item_2 = sub_item_2.replace("\r", "\\r")
                                        total_items_subitems = len(subitems)
                                        out_file.write(f"{sub_item_1}=")
                                        if index < total_items -1:
                                            out_file.write(f"{sub_item_2}\n")
                                        else:
                                            if i < total_items_subitems -1:
                                                out_file.write(f"{sub_item_2}\n")
                                            else:
                                                out_file.write(f"{sub_item_2}")
                                    if index < total_items -1:
                                        out_file.write(f"\n")
    
                                else:
                                    if total_items > 1:
                                        out_file.write(f"[{item_name}]\n\n")
                                    else:
                                        out_file.write(f"[{item_name}]")

                    logger(t("file_processed", path=file_path_out))

            logger(t("extraction_success"), color=COLOR_LOG_GREEN)
            return True

        except Exception as e:
            logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)
            return False


def rebuild_binary_file(original_file_path, output_file_path, extracted_folder):
    tipo = get_option("tipo_arquivo")
    
    if tipo == "1.0":
        try:
            extracted_folder = Path(extracted_folder)
            output_file_path = Path(output_file_path)
    
            logger(t("recreating_to", path=str(output_file_path)), color=COLOR_LOG_YELLOW)
    
            file_entries = []
            num_files = 0
    
            with open(original_file_path, 'rb') as orig:
                num_files_data = orig.read(4)
                if len(num_files_data) == 4:
                    num_files = struct.unpack('>I', num_files_data)[0]
    
                while True:
                    name_len_data = orig.read(4)
                    if not name_len_data or len(name_len_data) < 4:
                        break
                    name_len = struct.unpack('>I', name_len_data)[0]
    
                    name = orig.read(name_len).strip(b'\x00').decode('ansi')
    
                    content_len_data = orig.read(4)
                    if not content_len_data or len(content_len_data) < 4:
                        break
                    content_len = struct.unpack('>I', content_len_data)[0]
    
                    orig.seek(content_len, 1)
                    file_entries.append(name)
    
            with open(output_file_path, 'wb') as out:
                out.write(struct.pack('>I', num_files))
    
                for name in file_entries:
                    cleaned_name = name.replace('..\\', '').replace('../', '')
                    file_path = extracted_folder / cleaned_name
    
                    if not file_path.exists():
                        raise FileNotFoundError(t("file_not_found", file=str(file_path)))
    
                    encoded_name = name.encode('ansi') + b'\x00'
                    encoded_content = file_path.read_bytes() + b'\x00'
    
                    out.write(struct.pack('>I', len(encoded_name)))
                    out.write(encoded_name)
                    out.write(struct.pack('>I', len(encoded_content)))
                    out.write(encoded_content)
    
            logger(t("recreation_success"), color=COLOR_LOG_GREEN)
            return True
    
        except Exception as e:
            logger(t("recreation_error", error=str(e)), color=COLOR_LOG_RED)
            return False

    elif tipo == "2.0":
        try:
            extracted_folder = Path(extracted_folder)
            output_file_path = Path(output_file_path)
            
            file_names = []
            with open(original_file_path, 'rb') as orig:
                orig.seek(4)
                
                while True:
                    name_length_data = orig.read(4)
                    if not name_length_data:
                        break
                        
                    name_length = struct.unpack('>I', name_length_data)[0]
                    name_data = orig.read(name_length)
                    file_names.append(name_data)
                    
                    num_items = struct.unpack('>I', orig.read(4))[0]
                   
                    if num_items != 0:
                        for _ in range(num_items):
                            item_name_len = struct.unpack('>I', orig.read(4))[0]
                            orig.seek(item_name_len, 1)
                            sub_count = struct.unpack('>I', orig.read(4))[0]
                            for __ in range(sub_count):
                                
                                read4key = orig.read(4)
                            
                                if read4key[0] == 0xFF:
                                    char_count = struct.unpack('>I', read4key)[0]
                                    key_len = (4294967295 - char_count) * 2 + 2
                                else:
                                    key_len = struct.unpack('>I', read4key)[0]
                                    
                                orig.seek(key_len, 1)
                                
                                read4val = orig.read(4)
                                
                                if read4val[0] == 0xFF:
                                    char_count = struct.unpack('>I', read4val)[0]
                                    val_len = (4294967295 - char_count) * 2 + 2
                                else:
                                    val_len = struct.unpack('>I', read4val)[0]
                                
                                orig.seek(val_len, 1)
            
            logger(t("recreating_to", path=str(output_file_path)), color=COLOR_LOG_YELLOW)

            with open(output_file_path, 'wb') as out:
                out.write(struct.pack('>I', len(file_names)))
                
                for name_data in file_names:
                    out.write(struct.pack('>I', len(name_data)))
                    out.write(name_data)
                    
                    filename = name_data.rstrip(b'\x00').decode('ansi').lstrip('..\\')
                    file_path = extracted_folder / filename
                    
                    if not file_path.exists():
                        raise FileNotFoundError(t("file_not_found", file=str(file_path)))
                        
                    # Processa arquivo INI
                    with open(file_path, 'r', encoding='ansi') as f:
                        blocks = f.read().split('\n\n')
                        if blocks and blocks[-1].strip() == "":
                            blocks.pop()
                
                    out.write(struct.pack('>I', len(blocks)))
                
                    for block in blocks:
                        lines = block.split('\n')
                        
                        if lines:
                            item_name = lines[0][1:-1]  # Remove []
                            item_name_enc = item_name.encode('ansi') + b'\x00'
                            out.write(struct.pack('>I', len(item_name_enc)))
                            out.write(item_name_enc)
                    
                            subitems = lines[1:]
                            
                            if subitems and subitems[-1].strip() == "":
                                subitems.pop()
                                
                            out.write(struct.pack('>I', len(subitems)))
                    
                            for line in subitems:
                                
                                if '=' not in line:
                                    continue
                            
                                key, value = line.split('=', 1)
                                
                                key = key.replace("\\n", "\n").replace("\\r", "\r")
                                value = value.replace("\\n", "\n").replace("\\r", "\r")
                        
                                if key == "":
                                    out.write(struct.pack('>I', 0))
                                else:
                                    key_enc = key.encode('ansi')
                                    out.write(struct.pack('>I', len(key_enc) + 1))
                                    out.write(key_enc + b'\x00')
                            
                                if value == "":
                                    out.write(struct.pack('>I', 0))
                                else:
                                    if value.startswith('"') and value.endswith('"'):
                                        value = value[1:-1]
                                    value_enc = value.encode('ansi')
                                    out.write(struct.pack('>I', len(value_enc) + 1))
                                    out.write(value_enc + b'\x00')
                                
                        else:
                            out.write(struct.pack('>I', 0))
            
            logger(t("recreation_success"), color=COLOR_LOG_GREEN)
            return True
            
        except Exception as e:
            logger(t("recreation_error", error=str(e)), color=COLOR_LOG_RED)
            return False

    else:  # Versão 3.0
        try:
            def read_name(file, char_count):
                name_length = char_count * 2 + 2
                name_data = file.read(name_length)
                return name_data.decode('utf-16le').rstrip('\x00')
    
            # Abrir o arquivo binário original para leitura dos nomes
            file_names = []
            with open(original_file_path, 'rb') as f:
                
                endiam_check = f.read(2)
                if endiam_check == b'\x00\x00':
                    endianess = '>'
                    ordem_dos_bytes = 'big'
                else:
                    endianess = '<'
                    ordem_dos_bytes = 'little'
                f.seek(-2, 1)
                
                total_files = struct.unpack(endianess + 'I', f.read(4))[0]
    
                for _ in range(total_files):
                    char_count_bytes = f.read(4)
                    raw_value = int.from_bytes(char_count_bytes, byteorder=ordem_dos_bytes)
                    char_count = 4294967295 - raw_value
                    file_name = read_name(f, char_count)
                    file_names.append(file_name)
    
                    num_items = struct.unpack(endianess + 'I', f.read(4))[0]
                    for _ in range(num_items):
                        char_count_bytes_item = f.read(4)
                        raw_value_item = int.from_bytes(char_count_bytes_item, byteorder=ordem_dos_bytes)
                        if raw_value_item == 0:
                            char_count_item = ""
                        else:
                            char_count_item = 4294967295 - raw_value_item
                            read_name(f, char_count_item)
    
                        num_subitems = struct.unpack(endianess + 'I', f.read(4))[0]
                        for _ in range(num_subitems):
                            char_count_bytes_sub_item1 = f.read(4)
                            raw_value_sub_item1 = int.from_bytes(char_count_bytes_sub_item1, byteorder=ordem_dos_bytes)
                            if raw_value_sub_item1 != 0:
                                char_count_sub_item1 = 4294967295 - raw_value_sub_item1
                                read_name(f, char_count_sub_item1)
    
                            char_count_bytes_sub_item2 = f.read(4)
                            raw_value_sub_item2 = int.from_bytes(char_count_bytes_sub_item2, byteorder=ordem_dos_bytes)
                            if raw_value_sub_item2 != 0:
                                char_count_sub_item2 = 4294967295 - raw_value_sub_item2
                                read_name(f, char_count_sub_item2)
    
            logger(t("recreating_to", path=output_file_path), color=COLOR_LOG_YELLOW)

            with open(output_file_path, 'wb') as bin_file:
                bin_file.write(struct.pack(endianess + 'I', len(file_names)))
    
                for file_name in file_names:
                    file_path = os.path.join(extracted_folder, os.path.normpath(file_name.replace("..\\", "")))
                    if not os.path.exists(file_path):
                        raise FileNotFoundError(t("file_not_found", file=file_path))
    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        logger(t("file_processed", path=file_path))
                        content = f.read()
                        
                        items = [item for item in content.split('\n\n') if item]
    
                        char_count = len(file_name)
                        char_count_encoded = 4294967295 - char_count
                        bin_file.write(struct.pack(endianess + 'I', char_count_encoded))
                        bin_file.write(file_name.encode('utf-16le') + b'\x00\x00')
    
                        if content:
                            bin_file.write(struct.pack(endianess + 'I', len(items)))
                            for item in items:
                                lines = [line for line in item.split('\n') if line]
                                item_name = lines[0].strip('[]')
                                subitems = lines[1:]
        
                                if len(item_name) > 0:
                                    char_count_item = len(item_name)
                                    char_count_item_encoded = 4294967295 - char_count_item
                                    bin_file.write(struct.pack(endianess + 'I', char_count_item_encoded))
                                    bin_file.write(item_name.encode('utf-16le') + b'\x00\x00')
                                else:
                                    bin_file.write(struct.pack(endianess + 'I', 0))
        
                                bin_file.write(struct.pack(endianess + 'I', len(subitems)))
        
                                for subitem in subitems:
                                    sub_item_1, sub_item_2 = subitem.split('=', 1)
                                    sub_item_2 = sub_item_2.replace('\\n', '\n')
                                    sub_item_2 = sub_item_2.replace('\\r', '\r')
        
                                    char_count_sub_item1 = len(sub_item_1)
                                    if char_count_sub_item1 > 0:
                                        char_count_sub_item1_encoded = 4294967295 - char_count_sub_item1
                                        bin_file.write(struct.pack(endianess + 'I', char_count_sub_item1_encoded))  
                                        bin_file.write(sub_item_1.encode('utf-16le') + b'\x00\x00')
                                    else:
                                        bin_file.write(struct.pack(endianess + 'I', 0))
        
                                    char_count_sub_item2 = len(sub_item_2)
                                    if char_count_sub_item2 > 0:
                                        char_count_sub_item2_encoded = 4294967295 - char_count_sub_item2
                                        bin_file.write(struct.pack(endianess + 'I', char_count_sub_item2_encoded))
                                        bin_file.write(sub_item_2.encode('utf-16le') + b'\x00\x00')
                                    else:
                                        bin_file.write(struct.pack(endianess + 'I', 0))
                        else:
                            bin_file.write(struct.pack(endianess + 'I', 0))
    
            logger(t("recreation_success"), color=COLOR_LOG_GREEN)
            return True
    
        except Exception as e:
            logger(t("recreation_error", error=str(e)), color=COLOR_LOG_RED)
            return False


# ==============================================================================
# AÇÕES DOS COMANDOS (USAM O SELETOR DE ARQUIVO TOPMOST)
# ==============================================================================

def action_extract():
    path = pick_file_topmost(t("select_original_file"), [("Coalesced files", "*.bin;*.xxx"), ("All files", "*.*")])
    
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
    read_binary_file(path)


def action_rebuild():
    original_path = pick_file_topmost(t("select_original_file"), [("Coalesced files", "*.bin;*.xxx"), ("All files", "*.*")])
    
    if not original_path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    # Define caminhos de saída e pasta extraída automaticamente
    extracted_folder = os.path.splitext(original_path)[0]
    file_extension = os.path.splitext(original_path)[1]
    output_path = extracted_folder + "_MOD" + file_extension

    logger(t("processing", name=os.path.basename(original_path)), color=COLOR_LOG_YELLOW)
    rebuild_binary_file(original_path, output_path, extracted_folder)


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
                "name": "tipo_arquivo",
                "label": t("version"),
                "values": ["1.0", "2.0", "3.0"]
            }
        ],
        "commands": [
            {
                "label": t("extract_command"),
                "action": action_extract
            },
            {
                "label": t("recreate_command"),
                "action": action_rebuild
            }
        ]
    }