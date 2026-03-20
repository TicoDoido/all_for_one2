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
        "plugin_name": "PACKED - Clive Barker's Jericho",
        "plugin_description": "Extrai e reinsere arquivos de containers .packed",
        "extract_container": "Extrair Container",
        "reinsert_files": "Reinserir Arquivos",
        "select_packed_file": "Selecione o arquivo .packed",
        "packed_files": "Arquivos Packed",
        "all_files": "Todos os arquivos",
        "invalid_file": "Arquivo inválido",
        "invalid_packed_file": "Arquivo não é um container .packed válido.",
        "extraction_completed": "Extração concluída! Arquivos salvos em: {path}",
        "reinsertion_completed": "Reinserção concluída com sucesso!",
        "cancelled": "Cancelado",
        "extraction_cancelled": "Extração cancelada pelo usuário",
        "reinsertion_cancelled": "Reinserção cancelada pelo usuário",
        "file_not_found": "Arquivo não encontrado: {file}",
        "dir_not_found": "Diretório não encontrado: {dir}",
        "processing": "Processando: {name}...",
        "extracting_to": "Extraindo para: {path}",
        "file_extracted": "Arquivo extraído: {name}",
        "progress_status": "{percent}% - {current}/{total} arquivos",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "PACKED - Clive Barker's Jericho",
        "plugin_description": "Extracts and reinserts files from .packed containers",
        "extract_container": "Extract Container",
        "reinsert_files": "Reinsert Files",
        "select_packed_file": "Select .packed file",
        "packed_files": "Packed Files",
        "all_files": "All files",
        "invalid_file": "Invalid file",
        "invalid_packed_file": "File is not a valid .packed container.",
        "extraction_completed": "Extraction completed! Files saved to: {path}",
        "reinsertion_completed": "Reinsertion completed successfully!",
        "cancelled": "Cancelled",
        "extraction_cancelled": "Extraction cancelled by user",
        "reinsertion_cancelled": "Reinsertion cancelled by user",
        "file_not_found": "File not found: {file}",
        "dir_not_found": "Directory not found: {dir}",
        "processing": "Processing: {name}...",
        "extracting_to": "Extracting to: {path}",
        "file_extracted": "File extracted: {name}",
        "progress_status": "{percent}% - {current}/{total} files",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "PACKED - Clive Barker's Jericho",
        "plugin_description": "Extrae y reinserta archivos de contenedores .packed",
        "extract_container": "Extraer Contenedor",
        "reinsert_files": "Reinsertar Archivos",
        "select_packed_file": "Seleccionar archivo .packed",
        "packed_files": "Archivos Packed",
        "all_files": "Todos los archivos",
        "invalid_file": "Archivo inválido",
        "invalid_packed_file": "El archivo no es un contenedor .packed válido.",
        "extraction_completed": "¡Extracción completada! Archivos guardados en: {path}",
        "reinsertion_completed": "¡Reinserción completada con éxito!",
        "cancelled": "Cancelado",
        "extraction_cancelled": "Extracción cancelada por el usuario",
        "reinsertion_cancelled": "Reinserción cancelada por el usuario",
        "file_not_found": "Archivo no encontrado: {file}",
        "dir_not_found": "Directorio no encontrado: {dir}",
        "processing": "Procesando: {name}...",
        "extracting_to": "Extrayendo a: {path}",
        "file_extracted": "Archivo extraído: {name}",
        "progress_status": "{percent}% - {current}/{total} archivos",
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
    on_result=lambda e: _extract_packed_container(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)
fp_reinsert = ft.FilePicker(
    on_result=lambda e: _reinsert_files(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA RECEBER PATH)
# ==============================================================================

def _extract_packed_container(container_path: Path):
    """Extrai arquivos do container .packed."""
    logger(t("processing", name=container_path.name), color=COLOR_LOG_YELLOW)

    base_name = container_path.stem
    output_dir = container_path.parent / base_name
    output_dir.mkdir(parents=True, exist_ok=True)
    logger(t("extracting_to", path=str(output_dir)), color=COLOR_LOG_YELLOW)

    with open(container_path, 'rb') as f:
        if f.read(4) != b'BFPK':
            raise ValueError(t("invalid_packed_file"))

        version = struct.unpack('<I', f.read(4))[0]
        num_files = struct.unpack('<I', f.read(4))[0]

        for i in range(num_files):
            name_size = struct.unpack('<I', f.read(4))[0]
            name = f.read(name_size).decode('utf-8').replace('/', os.sep)
            decompressed_size = struct.unpack('<I', f.read(4))[0]
            file_offset = struct.unpack('<I', f.read(4))[0]

            current_pos = f.tell()
            f.seek(file_offset)
            compressed_size = struct.unpack('<I', f.read(4))[0]
            compressed_data = f.read(compressed_size)
            f.seek(current_pos)

            output_path = output_dir / name
            output_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                decompressed_data = zlib.decompress(compressed_data)
            except zlib.error:
                f.seek(file_offset)
                decompressed_data = f.read(compressed_size + 4)

            with open(output_path, 'wb') as out_file:
                out_file.write(decompressed_data)

            percent = int((i + 1) / num_files * 100)
            logger(t("progress_status", percent=percent, current=i+1, total=num_files), color=COLOR_LOG_YELLOW)
            logger(t("file_extracted", name=name), color=COLOR_LOG_GREEN)

    logger(t("extraction_completed", path=str(output_dir)), color=COLOR_LOG_GREEN)
    return output_dir


def _get_file_list(container_path: Path):
    """Retorna lista de nomes de arquivos e posição final do cabeçalho."""
    with open(container_path, 'rb') as f:
        if f.read(4) != b'BFPK':
            raise ValueError(t("invalid_packed_file"))
        f.seek(8)
        num_files = struct.unpack('<I', f.read(4))[0]

        file_list = []
        for _ in range(num_files):
            name_size = struct.unpack('<I', f.read(4))[0]
            name = f.read(name_size).decode('utf-8').replace('/', os.sep)
            f.seek(8, 1)  # skip decompressed size and offset
            file_list.append(name)

        header_end = f.tell()

    return file_list, header_end


def _reinsert_files(container_path: Path):
    """Reinsere arquivos no container .packed a partir da pasta extraída."""
    logger(t("processing", name=container_path.name), color=COLOR_LOG_YELLOW)

    input_dir = container_path.parent / container_path.stem
    if not input_dir.exists():
        raise FileNotFoundError(t("dir_not_found", dir=str(input_dir)))

    file_list, header_end = _get_file_list(container_path)
    total_files = len(file_list)
    temp_path = container_path.with_suffix(".new")

    with open(container_path, 'rb') as f, open(temp_path, 'w+b') as out:
        out.write(f.read(header_end))
        novos_dados = []

        for i, name in enumerate(file_list):
            input_file = input_dir / name
            if not input_file.exists():
                raise FileNotFoundError(t("file_not_found", file=str(input_file)))

            with open(input_file, 'rb') as fin:
                original_data = fin.read()
                compressed_data = zlib.compress(original_data)
                pointer = out.tell()
                out.write(struct.pack('<I', len(compressed_data)))
                out.write(compressed_data)
                novos_dados.append((pointer, len(original_data)))

            percent = int((i + 1) / total_files * 100)
            logger(t("progress_status", percent=percent, current=i+1, total=total_files), color=COLOR_LOG_YELLOW)

        out.seek(12)
        for (pointer, size) in novos_dados:
            name_size = struct.unpack('<I', out.read(4))[0]
            out.seek(name_size, 1)
            out.write(struct.pack('<I', size))
            out.write(struct.pack('<I', pointer))

    temp_path.replace(container_path)
    logger(t("reinsertion_completed"), color=COLOR_LOG_GREEN)
    return True


# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================

def action_extract():
    fp_extract.pick_files(
        allowed_extensions=["packed"],
        dialog_title=t("select_packed_file")
    )

def action_reinsert():
    fp_reinsert.pick_files(
        allowed_extensions=["packed"],
        dialog_title=t("select_packed_file")
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
        host_page.overlay.extend([fp_extract, fp_reinsert])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_container"), "action": action_extract},
            {"label": t("reinsert_files"), "action": action_reinsert},
        ]
    }