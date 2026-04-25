import os
import struct
import zlib
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "CAT/MATCAT Arquivo FEAR 1 PS3/XBOX 360",
        "plugin_description": "Extrai e recria contêineres (.CAT/.MATCAT) FEAR 1",
        "extract_file": "Extrair Arquivo",
        "rebuild_file": "Reconstruir Arquivo",
        "select_fear_file": "Selecione arquivo .CAT ou .MATCAT",
        "fear_files": "Arquivos FEAR (.cat, .matcat)",
        "all_files": "Todos os arquivos",
        "success": "Sucesso",
        "extraction_success": "Arquivos extraídos com sucesso!",
        "recreation_success": "Arquivo recriado com sucesso!",
        "error": "Erro",
        "extraction_error": "Erro durante extração: {error}",
        "recreation_error": "Erro durante reconstrução: {error}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "filelist_not_found": "Arquivo de lista de arquivos não encontrado.",
        "processing_file": "Processado: {file}, Posição: {position}",
        "adding_compressed": "Adicionando {file} comprimido.",
        "extracting_to": "Extraindo para: {path}",
        "recreating_to": "Recriando arquivo: {path}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "CAT/MATCAT FEAR 1 PS3/XBOX 360 File",
        "plugin_description": "Extracts and recreates FEAR 1 containers (.CAT/.MATCAT)",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild File",
        "select_fear_file": "Select .CAT or .MATCAT file",
        "fear_files": "FEAR Files (.cat, .matcat)",
        "all_files": "All files",
        "success": "Success",
        "extraction_success": "Files extracted successfully!",
        "recreation_success": "File recreated successfully!",
        "error": "Error",
        "extraction_error": "Error during extraction: {error}",
        "recreation_error": "Error during recreation: {error}",
        "file_not_found": "File not found: {file}",
        "filelist_not_found": "File list not found.",
        "processing_file": "Processed: {file}, Position: {position}",
        "adding_compressed": "Adding compressed: {file}",
        "extracting_to": "Extracting to: {path}",
        "recreating_to": "Recreating file: {path}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "CAT/MATCAT Archivo FEAR 1 PS3/XBOX 360",
        "plugin_description": "Extrae y recrea contenedores (.CAT/.MATCAT) FEAR 1",
        "extract_file": "Extraer Archivo",
        "rebuild_file": "Reconstruir Archivo",
        "select_fear_file": "Seleccionar archivo .CAT o .MATCAT",
        "fear_files": "Archivos FEAR (.cat, .matcat)",
        "all_files": "Todos los archivos",
        "success": "Éxito",
        "extraction_success": "¡Archivos extraídos con éxito!",
        "recreation_success": "¡Archivo recreado con éxito!",
        "error": "Error",
        "extraction_error": "Error durante extracción: {error}",
        "recreation_error": "Error durante reconstrucción: {error}",
        "file_not_found": "Archivo no encontrado: {file}",
        "filelist_not_found": "Archivo de lista no encontrado.",
        "processing_file": "Procesado: {file}, Posición: {position}",
        "adding_compressed": "Añadiendo comprimido: {file}",
        "extracting_to": "Extrayendo a: {path}",
        "recreating_to": "Recreando archivo: {path}",
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
host_page = None

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FilePickers globais
# ==============================================================================

fp_extract = ft.FilePicker(
    on_result=lambda e: _read_file_info(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)
fp_rebuild = ft.FilePicker(
    on_result=lambda e: _recreate_file(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def pad_to_32_bytes(data):
    padding_length = (32 - (len(data) % 32)) % 32
    return data + b'\x00' * padding_length

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA USAR PATH E LOGGER)
# ==============================================================================
def _read_file_info(file_path: Path):
    """Extrai arquivos do container .CAT/.MATCAT."""
    logger(t("processing", name=file_path.name), color=COLOR_LOG_YELLOW)

    try:
        base_path = file_path
        extract_folder = base_path.with_suffix('')

        with open(file_path, 'rb') as f:
            f.seek(4)
            start_pointers = struct.unpack('>I', f.read(4))[0]
            f.seek(8)
            num_pointers = struct.unpack('>I', f.read(4))[0]
            f.seek(12)
            start_block_names = struct.unpack('>I', f.read(4))[0]
            f.seek(16)
            size_block_names = struct.unpack('>I', f.read(4))[0]

            f.seek(start_block_names)
            names_block = f.read(size_block_names)
            names_block = names_block.replace(b'MSF\x01', b'wav')
            file_names = names_block.split(b'\x00')

            file_list_name = base_path.with_name(f"{base_path.stem}_filelist.txt")
            extract_folder.mkdir(parents=True, exist_ok=True)

            with open(file_list_name, 'w', encoding='utf-8') as file_list:
                for i in range(num_pointers):
                    f.seek(start_pointers + i * 16)
                    f.read(4)  # ignorar identificador
                    pointer = struct.unpack('>I', f.read(4))[0]
                    uncompressed_size = struct.unpack('>I', f.read(4))[0]
                    compressed_size = struct.unpack('>I', f.read(4))[0]

                    f.seek(pointer)
                    compressed_data = f.read(compressed_size)

                    file_name = file_names[i].decode('utf-8')
                    output_path = extract_folder / file_name

                    if uncompressed_size > compressed_size:
                        decompressed_data = zlib.decompress(compressed_data)
                        data_to_write = decompressed_data
                        file_list.write(f"{file_name},decompressed\n")
                    else:
                        data_to_write = compressed_data
                        file_list.write(f"{file_name}\n")

                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(data_to_write)

                    logger(t("processing_file", file=file_name, position=hex(pointer).upper()), color=COLOR_LOG_YELLOW)

        logger(t("extracting_to", path=str(extract_folder)), color=COLOR_LOG_YELLOW)
        logger(t("extraction_success"), color=COLOR_LOG_GREEN)
        return True
    except Exception as e:
        logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)
        return False

def _recreate_file(file_path: Path):
    """Reconstrói o container .CAT/.MATCAT a partir da pasta extraída."""
    logger(t("processing", name=file_path.name), color=COLOR_LOG_YELLOW)

    try:
        base_path = file_path
        folder_name = base_path.with_suffix('')
        new_file_path = base_path.with_name(f"{base_path.stem}_mod{base_path.suffix}")
        file_list_path = base_path.with_name(f"{base_path.stem}_filelist.txt")

        if not file_list_path.exists():
            raise FileNotFoundError(t("filelist_not_found"))

        with open(file_path, 'rb') as original_file:
            original_file.seek(20)
            data_start_offset = struct.unpack('>I', original_file.read(4))[0]
            original_file.seek(0)
            header = original_file.read(data_start_offset)

        file_infos = []
        logger(t("recreating_to", path=str(new_file_path)), color=COLOR_LOG_YELLOW)

        with open(new_file_path, 'wb') as new_file:
            new_file.write(header)
            current_pointer = data_start_offset

            with open(file_list_path, 'r', encoding='utf-8') as file_list:
                for line in file_list:
                    line = line.strip()
                    uncompressed = ',decompressed' in line
                    file_name = line.replace(',decompressed', '')
                    file_path_local = folder_name / file_name

                    if not file_path_local.exists():
                        raise FileNotFoundError(t("file_not_found", file=str(file_path_local)))

                    data = file_path_local.read_bytes()
                    data_size = len(data)
                    if uncompressed:
                        logger(t("adding_compressed", file=file_name), color=COLOR_LOG_YELLOW)
                        data = zlib.compress(data, level=6)

                    compressed_size = len(data)
                    compressed_data = pad_to_32_bytes(data)
                    file_infos.append((current_pointer, data_size, compressed_size))
                    new_file.write(compressed_data)
                    current_pointer += len(compressed_data)

        with open(new_file_path, 'r+b') as new_file:
            new_file.seek(32)
            for file_info in file_infos:
                new_file.read(4)  # ignorar identificador
                new_file.write(struct.pack('>I', file_info[0]))  # offset
                new_file.write(struct.pack('>I', file_info[1]))  # tamanho descomprimido
                new_file.write(struct.pack('>I', file_info[2]))  # tamanho comprimido

        logger(t("recreation_success"), color=COLOR_LOG_GREEN)
        return True
    except Exception as e:
        logger(t("recreation_error", error=str(e)), color=COLOR_LOG_RED)
        return False

# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================
def action_extract():
    fp_extract.pick_files(
        allowed_extensions=["cat", "matcat"],
        dialog_title=t("select_fear_file")
    )

def action_rebuild():
    fp_rebuild.pick_files(
        allowed_extensions=["cat", "matcat"],
        dialog_title=t("select_fear_file")
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
        host_page.overlay.extend([fp_extract, fp_rebuild])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_file"), "action": action_extract},
            {"label": t("rebuild_file"), "action": action_rebuild},
        ]
    }