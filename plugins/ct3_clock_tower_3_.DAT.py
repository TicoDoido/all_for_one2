import os
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "CT3PACK - Clock Tower 3 (PS2)",
        "plugin_description": "Extrai e recria arquivos ct3pack.dat do jogo Clock Tower 3 (PS2)",
        "extract_file": "Extrair Arquivo",
        "rebuild_file": "Recriar Arquivo",
        "select_ct3_file": "Selecione o arquivo *.dat",
        "select_txt_file": "Selecione o arquivo *_filelist.txt",
        "ct3_files": "Arquivos CT3",
        "text_files": "Arquivos de Texto",
        "all_files": "Todos os arquivos",
        "extraction_completed": "Extração concluída com sucesso!\nArquivos salvos em: {path}",
        "recreation_completed": "Arquivo reconstruído com sucesso!\nSalvo em: {path}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "folder_not_found": "Pasta não encontrada: {folder}",
        "empty_file_list": "A lista de arquivos está vazia",
        "name_decode_error": "Erro ao decodificar nome: {error}\nBytes lidos: {bytes}",
        "unexpected_error": "Ocorreu um erro inesperado: {error}",
        "success": "Sucesso",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "file_processed": "Arquivo processado: {path}"
    },
    "en_US": {
        "plugin_name": "CT3PACK - Clock Tower 3 (PS2)",
        "plugin_description": "Extracts and rebuilds ct3pack.dat files from Clock Tower 3 (PS2)",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild File",
        "select_ct3_file": "Select *.dat file",
        "select_txt_file": "Select *_filelist.txt file",
        "ct3_files": "CT3 Files",
        "text_files": "Text Files",
        "all_files": "All files",
        "extraction_completed": "Extraction completed successfully!\nFiles saved to: {path}",
        "recreation_completed": "File rebuilt successfully!\nSaved to: {path}",
        "file_not_found": "File not found: {file}",
        "folder_not_found": "Folder not found: {folder}",
        "empty_file_list": "File list is empty",
        "name_decode_error": "Error decoding name: {error}\nBytes read: {bytes}",
        "unexpected_error": "An unexpected error occurred: {error}",
        "success": "Success",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "file_processed": "File processed: {path}"
    },
    "es_ES": {
        "plugin_name": "CT3PACK - Clock Tower 3 (PS2)",
        "plugin_description": "Extrae y reconstruye archivos ct3pack.dat del juego Clock Tower 3 (PS2)",
        "extract_file": "Extraer Archivo",
        "rebuild_file": "Reconstruir Archivo",
        "select_ct3_file": "Seleccionar archivo *.dat",
        "select_txt_file": "Seleccionar archivo *_filelist.txt",
        "ct3_files": "Archivos CT3",
        "text_files": "Archivos de Texto",
        "all_files": "Todos los archivos",
        "extraction_completed": "¡Extracción completada con éxito!\nArchivos guardados en: {path}",
        "recreation_completed": "¡Archivo reconstruido con éxito!\nGuardado en: {path}",
        "file_not_found": "Archivo no encontrado: {file}",
        "folder_not_found": "Carpeta no encontrada: {folder}",
        "empty_file_list": "La lista de archivos está vacía",
        "name_decode_error": "Error al decodificar nombre: {error}\nBytes leídos: {bytes}",
        "unexpected_error": "Ocurrió un error inesperado: {error}",
        "success": "Éxito",
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
host_page = None

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FilePickers globais
# ==============================================================================

fp_extract = ft.FilePicker(
    on_result=lambda e: _extract_file(e.files[0].path) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)
fp_rebuild = ft.FilePicker(
    on_result=lambda e: _rebuild_file(e.files[0].path) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# LÓGICA DE NEGÓCIO (EXTRAÇÃO E RECRIAÇÃO) - FUNÇÕES INTERNAS
# ==============================================================================

def _extract_file(path):
    """Extrai o arquivo .dat selecionado."""
    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)

    try:
        if not os.path.exists(path):
            raise FileNotFoundError(t("file_not_found", file=path))

        base_name = os.path.splitext(os.path.basename(path))[0]
        output_dir = os.path.join(os.path.dirname(path), base_name)
        os.makedirs(output_dir, exist_ok=True)

        filelist_path = os.path.join(os.path.dirname(path), f"{base_name}_filelist.txt")

        with open(path, 'rb') as f:
            file_names = []
            pointers = []
            sizes = []
            extracted_files = []

            total_items = f.read(4)
            total_items_int = int.from_bytes(total_items, byteorder='little')

            f.seek(2048)

            for _ in range(total_items_int):
                name_bytes = f.read(16)
                try:
                    name = name_bytes.decode('utf-8').strip('\x00')
                    file_names.append(name)
                except UnicodeDecodeError as e:
                    logger(t("name_decode_error", error=str(e), bytes=name_bytes), color=COLOR_LOG_RED)
                    file_names.append(f"unknown_{len(file_names)}")

                f.seek(4, 1)  # pula 4 bytes desconhecidos
                size = f.read(4)
                size_int = int.from_bytes(size, byteorder='little')
                sizes.append(size_int)

                offset = f.read(4)
                offset_int = int.from_bytes(offset, byteorder='little')
                pointers.append(offset_int * 2048)
                f.seek(4, 1)  # pula mais 4 bytes

            for i, (pointer, size, name) in enumerate(zip(pointers, sizes, file_names)):
                output_file_path = os.path.join(output_dir, name)

                f.seek(pointer)
                file_data = f.read(size)

                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                with open(output_file_path, 'wb') as output_file:
                    output_file.write(file_data)

                extracted_files.append(name)
                logger(t("file_processed", path=output_file_path))

            with open(filelist_path, 'w', encoding='utf-8') as filelist_file:
                filelist_file.write("\n".join(extracted_files))

        logger(t("extraction_completed", path=output_dir), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)


def _rebuild_file(filelist_path):
    """Recria o arquivo .dat a partir da lista de arquivos e da pasta extraída."""
    logger(t("processing", name=os.path.basename(filelist_path)), color=COLOR_LOG_YELLOW)

    try:
        base_name = os.path.splitext(os.path.basename(filelist_path))[0].replace("_filelist", "")
        output_dir = os.path.join(os.path.dirname(filelist_path), base_name)
        recreated_file = os.path.join(os.path.dirname(filelist_path), f"{base_name}_new.dat")
        original_file = os.path.join(os.path.dirname(filelist_path), f"{base_name}.dat")

        if not os.path.exists(output_dir):
            raise FileNotFoundError(t("folder_not_found", folder=output_dir))

        with open(filelist_path, 'r', encoding='utf-8') as fl:
            file_names = fl.read().splitlines()

        if not file_names:
            raise ValueError(t("empty_file_list"))

        file_pointers = []
        file_sizes = []
        tamanhos_com_pad = []

        with open(original_file, 'rb') as arquivo_original:
            arquivo_original.seek(4)
            header_size = arquivo_original.read(4)
            header_size_int = int.from_bytes(header_size, byteorder='little')
            arquivo_original.seek(0)
            header = arquivo_original.read(header_size_int)

        with open(recreated_file, 'w+b') as new_file:
            new_file.write(header)

            for file_name in file_names:
                file_path = os.path.join(output_dir, file_name)
                if not os.path.exists(file_path):
                    logger(t("file_not_found", file=file_path), color=COLOR_LOG_RED)
                    continue

                pointer = new_file.tell()
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    new_file.write(file_data)

                file_pointers.append(pointer)
                file_sizes.append(len(file_data))

                tamanho_atual = new_file.tell()
                padding = (2048 - (tamanho_atual % 2048)) % 2048
                new_file.write(b'\x00' * padding)
                tamanho_com_pad = len(file_data) + padding
                tamanhos_com_pad.append(tamanho_com_pad)

            new_file.seek(2048)

            for pointer, size, size_pad in zip(file_pointers, file_sizes, tamanhos_com_pad):
                new_file.seek(20, 1)  # pula 20 bytes (nome + desconhecido)
                new_file.write(size.to_bytes(4, byteorder='little'))
                new_file.write((pointer // 2048).to_bytes(4, byteorder='little'))
                new_file.write((size_pad // 2048).to_bytes(4, byteorder='little'))

        logger(t("recreation_completed", path=recreated_file), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)


# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================

def action_extract():
    fp_extract.pick_files(
        allowed_extensions=["dat"],
        dialog_title=t("select_ct3_file")
    )

def action_rebuild():
    fp_rebuild.pick_files(
        allowed_extensions=["txt"],
        dialog_title=t("select_txt_file")
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
            {"label": t("rebuild_file"), "action": action_rebuild}
        ]
    }