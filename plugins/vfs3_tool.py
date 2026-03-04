# Script de extração original nesse repositório LinkOFF7
# https://github.com/LinkOFF7/GameReverseScripts
import os
import struct
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "VFS Extrator / Repacker SOTDH",
        "plugin_description": "Extrai e reinsere arquivos de um VFS Shadow of the Dammed Hella Remastered",
        "extract_file": "Extrair VFS",
        "reinsert_file": "Reinserir arquivos no VFS",
        "select_vfs_file": "Selecione o arquivo VFS",
        "log_magic": "Magic {magic_hex} no offset {offset}",
        "log_invalid_magic": "Arquivo inválido (magic mismatch): {magic_hex}",
        "log_directory_count": "Contagem de diretórios: {count} no offset {offset}",
        "log_directory_offset": "Diretório {i}: offset {offset}",
        "log_data_start_aligned": "Data start alinhado em: {data_start}",
        "log_file_entry_offset": "File entry {i}: offset {offset}",
        "log_filename_table": "Tabela de nomes em offset {offset}",
        "log_processing": "Processando: {filepath} no offset de dados {data_offset}",
        "log_reinsert_data_start": "data_start = {data_start}",
        "log_reinsert_filename_ptr": "filename_offset (original) = {filename_offset}, pointer pos = {pointer_pos}",
        "log_warn_not_in_metadata": "Aviso: {path} não encontrado no metadata, pulando...",
        "log_warn_invalid_entry_index": "Aviso: entry_index inválido para {path}, pulando...",
        "log_warn_local_missing": "Arquivo local não encontrado, pulando: {path}",
        "log_reinserted": "Reinserted {path} at {abs_pos} (rel {rel_pos}) size {size}",
        "log_reinsert_done_filename_written": "Escreveu tabela de nomes no final, novo offset {new_offset}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "extracting_to": "Extraindo para: {path}",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "VFS Extractor / Repacker SOTDH",
        "plugin_description": "Extracts and reinserts files from a VFS Shadow of the Dammed Hella Remastered",
        "extract_file": "Extract VFS",
        "reinsert_file": "Reinsert files into VFS",
        "select_vfs_file": "Select VFS file",
        "log_magic": "Magic {magic_hex} at offset {offset}",
        "log_invalid_magic": "Invalid file (magic mismatch): {magic_hex}",
        "log_directory_count": "Directory count: {count} at offset {offset}",
        "log_directory_offset": "Directory {i}: offset {offset}",
        "log_data_start_aligned": "Data start aligned at: {data_start}",
        "log_file_entry_offset": "File entry {i}: offset {offset}",
        "log_filename_table": "Filename table at offset {offset}",
        "log_processing": "Processing: {filepath} at data offset {data_offset}",
        "log_reinsert_data_start": "data_start = {data_start}",
        "log_reinsert_filename_ptr": "filename_offset (original) = {filename_offset}, pointer pos = {pointer_pos}",
        "log_warn_not_in_metadata": "Warning: {path} not found in metadata, skipping...",
        "log_warn_invalid_entry_index": "Warning: invalid entry_index for {path}, skipping...",
        "log_warn_local_missing": "Local file not found, skipping: {path}",
        "log_reinserted": "Reinserted {path} at {abs_pos} (rel {rel_pos}) size {size}",
        "log_reinsert_done_filename_written": "Wrote filename table to end, new offset {new_offset}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "extracting_to": "Extracting to: {path}",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "VFS Extractor / Repacker SOTDH",
        "plugin_description": "Extrae y reinserta archivos de un VFS Shadow of the Dammed Hella Remastered",
        "extract_file": "Extraer VFS",
        "reinsert_file": "Reinsertar archivos en VFS",
        "select_vfs_file": "Seleccionar archivo VFS",
        "log_magic": "Magic {magic_hex} en offset {offset}",
        "log_invalid_magic": "Archivo inválido (magic mismatch): {magic_hex}",
        "log_directory_count": "Número de directorios: {count} en offset {offset}",
        "log_directory_offset": "Directorio {i}: offset {offset}",
        "log_data_start_aligned": "Inicio de datos alineado en: {data_start}",
        "log_file_entry_offset": "Entrada de archivo {i}: offset {offset}",
        "log_filename_table": "Tabla de nombres en offset {offset}",
        "log_processing": "Procesando: {filepath} en offset de datos {data_offset}",
        "log_reinsert_data_start": "data_start = {data_start}",
        "log_reinsert_filename_ptr": "filename_offset (original) = {filename_offset}, pointer pos = {pointer_pos}",
        "log_warn_not_in_metadata": "Aviso: {path} no encontrado en metadata, saltando...",
        "log_warn_invalid_entry_index": "Aviso: entry_index inválido para {path}, saltando...",
        "log_warn_local_missing": "Archivo local no encontrado, saltando: {path}",
        "log_reinserted": "Reinsertado {path} en {abs_pos} (rel {rel_pos}) tamaño {size}",
        "log_reinsert_done_filename_written": "Escribió tabla de nombres al final, nuevo offset {new_offset}",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "extracting_to": "Extrayendo a: {path}",
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
# CLASSES AUXILIARES (MANTIDAS DO ORIGINAL)
# ==============================================================================
class DirEntry:
    def __init__(self, f):
        self.start_pos = f.tell()
        self.index, self.var04, self.var08, self.var0C = struct.unpack('<4i', f.read(0x10))
        self.var10, self.var14, self.var18 = struct.unpack('<iiI', f.read(0xC))

class FileEntry:
    def __init__(self, f):
        self.start_pos = f.tell()
        self.offset, self.compressedSize, self.decompressedSize = struct.unpack('<3Q', f.read(0x18))
        self.unk18, self.filenameIndex, self.dirIndex, self.unk24, self.unk26 = struct.unpack('<3I2h', f.read(0x10))

def readcstr(f):
    cstr = bytearray()
    while True:
        ch = f.read(2)
        if ch == b'':
            return str(cstr, "utf-16")
        if ch == b'\x00\x00':
            return str(cstr, "utf-16")
        cstr += ch

def align(var, boundary=16):
    if var % boundary != 0:
        return var + (boundary - (var % boundary))
    return var

def read_filenames(f, offset):
    cur = f.tell()
    f.seek(offset)
    file_count = struct.unpack('<I', f.read(4))[0]
    dirs = []
    files = []
    for i in range(file_count):
        files.append(readcstr(f))
    dir_count = struct.unpack('<I', f.read(4))[0]
    for i in range(dir_count):
        dirs.append(readcstr(f))
    f.seek(cur)
    return files, dirs

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA USAR LOGGER)
# ==============================================================================
def extract(vfs_file):
    metadata = {}
    with open(vfs_file, 'rb') as f:
        magic_offset = f.tell()
        magic, start_offset, dir_count, pad = struct.unpack('<4I', f.read(16))
        magic_hex = f"0x{magic:X}"
        logger(t("log_magic", magic_hex=magic_hex, offset=magic_offset), color=COLOR_LOG_YELLOW)
        if magic != 0x33534656:
            logger(t("log_invalid_magic", magic_hex=magic_hex), color=COLOR_LOG_RED)
            return

        logger(t("log_directory_count", count=dir_count, offset=(f.tell()-4)), color=COLOR_LOG_YELLOW)

        dirs = []
        for i in range(dir_count):
            d = DirEntry(f)
            dirs.append(d)

        count = dirs[-1].var18
        data_start = f.tell() + (count * 0x28) + (0x8 * 3)
        data_start = align(data_start)
        logger(t("log_data_start_aligned", data_start=data_start), color=COLOR_LOG_YELLOW)

        entries = []
        for i in range(count):
            e = FileEntry(f)
            e.entry_index = i
            entries.append(e)

        f.read(16)
        filename_offset = struct.unpack('<Q', f.read(8))[0]
        logger(t("log_filename_table", offset=filename_offset), color=COLOR_LOG_YELLOW)

        filenames, dirnames = read_filenames(f, filename_offset)

        for entry in entries:
            entry.data_pointer_start = data_start + entry.offset

        entries_sorted = sorted(entries, key=lambda x: x.data_pointer_start)

        txt_list_path = os.path.splitext(vfs_file)[0] + '_extraction_order.txt'
        extrac_patch = os.path.splitext(vfs_file)[0]
        with open(txt_list_path, 'w', encoding='utf-8') as list_file:
            for entry in entries_sorted:
                try:
                    dir_path = dirnames[entry.dirIndex]
                    filename = filenames[entry.filenameIndex]
                except Exception:
                    dir_path = ''
                    filename = f'UNKNOWN_{entry.entry_index}'
                filepath = os.path.join(dir_path, filename)
                list_file.write(f'{entry.data_pointer_start}: {filepath}\n')

        metadata['files'] = []
        metadata['dirs'] = dirnames

        for entry in entries_sorted:
            dir_path = ''
            try:
                dir_path = dirnames[entry.dirIndex]
            except Exception:
                dir_path = ''
            try:
                filename = filenames[entry.filenameIndex]
            except Exception:
                filename = f'UNKNOWN_{entry.entry_index}'

            if dir_path == '' or dir_path is None:
                filepath = filename
            else:
                filepath = os.path.join(extrac_patch, dir_path, filename)
            filepath = os.path.normpath(filepath)
            full_dir = os.path.dirname(filepath)
            if full_dir and not os.path.exists(full_dir):
                os.makedirs(full_dir, exist_ok=True)

            logger(t("log_processing", filepath=filepath, data_offset=entry.data_pointer_start), color=COLOR_LOG_YELLOW)

            f.seek(entry.data_pointer_start)
            data = f.read(entry.decompressedSize)
            with open(filepath, 'wb') as r:
                r.write(data)

            metadata['files'].append({
                'filepath': filepath,
                'dirIndex': entry.dirIndex,
                'filenameIndex': entry.filenameIndex,
                'offset': entry.offset,
                'compressedSize': entry.compressedSize,
                'decompressedSize': entry.decompressedSize,
                'data_pointer_start': entry.data_pointer_start,
                'start_pos': entry.start_pos,
                'entry_index': entry.entry_index
            })

    json_path = os.path.splitext(vfs_file)[0] + '_metadata.json'
    with open(json_path, 'w', encoding='utf-8') as jf:
        json.dump(metadata, jf, indent=4, ensure_ascii=False)

    logger(t("operation_completed"), color=COLOR_LOG_GREEN)

def reinsert_files(vfs_file):
    json_path = os.path.splitext(vfs_file)[0] + '_metadata.json'
    if not os.path.exists(json_path):
        logger(t("log_warn_not_in_metadata", path=json_path), color=COLOR_LOG_RED)
        return

    with open(json_path, 'r', encoding='utf-8') as jf:
        metadata = json.load(jf)

    txt_list_path = os.path.splitext(vfs_file)[0] + '_extraction_order.txt'
    if not os.path.exists(txt_list_path):
        logger(t("log_warn_not_in_metadata", path=txt_list_path), color=COLOR_LOG_RED)
        return

    reinsertion_order = []
    with open(txt_list_path, 'r', encoding='utf-8') as tf:
        for line in tf:
            if not line.strip():
                continue
            try:
                offset_str, filepath = line.strip().split(': ', 1)
                reinsertion_order.append((int(offset_str), os.path.normpath(filepath)))
            except Exception:
                continue

    if not reinsertion_order:
        logger(t("log_warn_not_in_metadata", path=txt_list_path), color=COLOR_LOG_RED)
        return

    first_offset = reinsertion_order[0][0]
    current_data_pos = first_offset

    file_lookup = {os.path.normpath(f['filepath']): f for f in metadata['files']}

    repack_info = []

    with open(vfs_file, 'r+b') as f:
        f.seek(0)
        magic, start_offset, dir_count, pad = struct.unpack('<4I', f.read(16))

        dirs = []
        for i in range(dir_count):
            d = DirEntry(f)
            dirs.append(d)

        count = dirs[-1].var18
        data_start = f.tell() + (count * 0x28) + (0x8 * 3)
        data_start = align(data_start)
        logger(t("log_reinsert_data_start", data_start=data_start), color=COLOR_LOG_YELLOW)

        entries = []
        for i in range(count):
            e = FileEntry(f)
            e.entry_index = i
            entries.append(e)

        f.read(16)
        filename_offset_pos = f.tell()
        filename_offset = struct.unpack('<Q', f.read(8))[0]
        logger(t("log_reinsert_filename_ptr", filename_offset=filename_offset, pointer_pos=filename_offset_pos), color=COLOR_LOG_YELLOW)

        cur = f.tell()
        f.seek(filename_offset)
        filename_table = f.read()
        f.seek(cur)
        extrac_patch = os.path.splitext(vfs_file)[0]

        for offset_val, filepath in reinsertion_order:
            norm_path = os.path.join(extrac_patch, filepath)
            norm_path = os.path.normpath(norm_path)

            if norm_path not in file_lookup:
                logger(t("log_warn_not_in_metadata", path=norm_path), color=COLOR_LOG_YELLOW)
                continue

            file_meta = file_lookup[norm_path]
            entry_index = int(file_meta.get('entry_index', -1))
            if entry_index < 0 or entry_index >= len(entries):
                logger(t("log_warn_invalid_entry_index", path=norm_path), color=COLOR_LOG_YELLOW)
                continue

            entry = entries[entry_index]

            if not os.path.exists(norm_path):
                logger(t("log_warn_local_missing", path=norm_path), color=COLOR_LOG_YELLOW)
                continue

            with open(norm_path, 'rb') as rf:
                data = rf.read()
            new_size = len(data)

            f.seek(current_data_pos)
            f.write(data)
            f.truncate()

            new_rel_offset = current_data_pos - data_start
            f.seek(entry.start_pos)
            f.write(struct.pack('<3Q', new_rel_offset, new_size, new_size))

            logger(t("log_reinserted", path=norm_path, abs_pos=current_data_pos, rel_pos=new_rel_offset, size=new_size), color=COLOR_LOG_GREEN)

            repack_info.append({
                'filepath': norm_path,
                'entry_index': entry.entry_index,
                'new_absolute_offset': current_data_pos,
                'new_relative_offset': new_rel_offset,
                'new_size': new_size
            })

            current_data_pos = align(current_data_pos + new_size, 16)

        f.seek(0, os.SEEK_END)
        new_filename_offset = f.tell()
        f.write(filename_table)
        logger(t("log_reinsert_done_filename_written", new_offset=new_filename_offset), color=COLOR_LOG_YELLOW)

        f.seek(filename_offset_pos)
        f.write(struct.pack('<Q', new_filename_offset))
        f.flush()

    repack_json_path = os.path.splitext(vfs_file)[0] + '_repacked_metadata.json'
    with open(repack_json_path, 'w', encoding='utf-8') as jf:
        json.dump(repack_info, jf, indent=4, ensure_ascii=False)

    logger(t("operation_completed"), color=COLOR_LOG_GREEN)

# ==============================================================================
# AÇÕES DOS COMANDOS (SEM THREADING)
# ==============================================================================
def action_extract():
    path = pick_file_topmost(t("select_vfs_file"), [("VFS files", "*.vfs"), ("All files", "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return
    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
    try:
        extract(path)
    except Exception as e:
        logger(t("log_warn_not_in_metadata", path=str(e)), color=COLOR_LOG_RED)

def action_reinsert():
    path = pick_file_topmost(t("select_vfs_file"), [("VFS files", "*.vfs"), ("All files", "*.*")])
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return
    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
    try:
        reinsert_files(path)
    except Exception as e:
        logger(t("log_warn_not_in_metadata", path=str(e)), color=COLOR_LOG_RED)

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
            {"label": t("reinsert_file"), "action": action_reinsert},
        ]
    }