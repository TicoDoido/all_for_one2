import os
import struct
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "RCF - Radcore Cement Library VER:1.2/2.1",
        "plugin_description": "Extrai e recria arquivos RCF de jogos da Radical Entertainment",
        "extract_file": "Extrair Arquivo",
        "rebuild_file": "Recriar Arquivo",
        "select_rcf_file": "Selecione o arquivo .rcf",
        "select_txt_file": "Selecione o arquivo .txt",
        "rcf_files": "Arquivos RCF",
        "text_files": "Arquivos de Texto",
        "all_files": "Todos os arquivos",
        "unsupported_file": "Arquivo não suportado!",
        "extraction_completed": "Arquivos extraídos com sucesso para: {path}",
        "recreation_completed": "Novo arquivo RCF criado em: {path}",
        "folder_not_found": "Pasta não encontrada: {folder}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "error_creating_dir": "Erro ao criar diretório: {error}",
        "version_21_le": "Versão é 2.1 MODO LITTLE ENDIAN",
        "version_21_be": "Versão é 2.1 MODO BIG ENDIAN",
        "version_12_le": "Versão é 1.2 MODO LITTLE ENDIAN",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "extracting_to": "Extraindo para: {path}",
        "file_extracted": "Arquivo extraído: {name}",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "RCF - Radcore Cement Library VER:1.2/2.1",
        "plugin_description": "Extracts and recreates RCF files from Radical Entertainment games",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild File",
        "select_rcf_file": "Select .rcf file",
        "select_txt_file": "Select .txt file",
        "rcf_files": "RCF Files",
        "text_files": "Text Files",
        "all_files": "All files",
        "unsupported_file": "Unsupported file!",
        "extraction_completed": "Files successfully extracted to: {path}",
        "recreation_completed": "New RCF file created at: {path}",
        "folder_not_found": "Folder not found: {folder}",
        "file_not_found": "File not found: {file}",
        "error_creating_dir": "Error creating directory: {error}",
        "version_21_le": "Version 2.1 LITTLE ENDIAN MODE",
        "version_21_be": "Version 2.1 BIG ENDIAN MODE",
        "version_12_le": "Version 1.2 LITTLE ENDIAN MODE",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "extracting_to": "Extracting to: {path}",
        "file_extracted": "File extracted: {name}",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "RCF - Radcore Cement Library VER:1.2/2.1",
        "plugin_description": "Extrae y recrea archivos RCF de juegos de Radical Entertainment",
        "extract_file": "Extraer Archivo",
        "rebuild_file": "Recrear Archivo",
        "select_rcf_file": "Seleccionar archivo .rcf",
        "select_txt_file": "Seleccionar archivo .txt",
        "rcf_files": "Archivos RCF",
        "text_files": "Archivos de Texto",
        "all_files": "Todos los archivos",
        "unsupported_file": "¡Archivo no soportado!",
        "extraction_completed": "Archivos extraídos exitosamente a: {path}",
        "recreation_completed": "Nuevo archivo RCF creado en: {path}",
        "folder_not_found": "Carpeta no encontrada: {folder}",
        "file_not_found": "Archivo no encontrado: {file}",
        "error_creating_dir": "Error al crear directorio: {error}",
        "version_21_le": "Versión 2.1 MODO LITTLE ENDIAN",
        "version_21_be": "Versión 2.1 MODO BIG ENDIAN",
        "version_12_le": "Versión 1.2 MODO LITTLE ENDIAN",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "extracting_to": "Extrayendo a: {path}",
        "file_extracted": "Archivo extraído: {name}",
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
    on_result=lambda e: _extract_files(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# Para rebuild: precisamos de dois pickers encadeados
_rcf_path_for_rebuild = None

def _on_rcf_selected(e):
    global _rcf_path_for_rebuild
    if e.files:
        _rcf_path_for_rebuild = Path(e.files[0].path)
        fp_rebuild_txt.pick_files(
            allowed_extensions=["txt"],
            dialog_title=t("select_txt_file")
        )
    else:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)

def _on_txt_selected(e):
    global _rcf_path_for_rebuild
    if e.files and _rcf_path_for_rebuild:
        txt_path = Path(e.files[0].path)
        _recreate_rcf(_rcf_path_for_rebuild, txt_path)
        _rcf_path_for_rebuild = None
    else:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)

fp_rebuild_rcf = ft.FilePicker(on_result=_on_rcf_selected)
fp_rebuild_txt = ft.FilePicker(on_result=_on_txt_selected)

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def calculate_padding(size, allocation=512):
    if size % allocation == 0:
        return size
    return ((size // allocation) + 1) * allocation

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA RECEBER PATH)
# ==============================================================================
def _extract_files(file_path: Path):
    """Extrai arquivos do RCF selecionado."""
    logger(t("processing", name=file_path.name), color=COLOR_LOG_YELLOW)

    base_directory = file_path.parent
    base_filename = file_path.stem
    extraction_directory = base_directory / base_filename

    try:
        extraction_directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger(t("error_creating_dir", error=str(e)), color=COLOR_LOG_RED)
        return

    logger(t("extracting_to", path=str(extraction_directory)), color=COLOR_LOG_YELLOW)

    with open(file_path, 'rb') as file:
        file.seek(32)
        file_version = file.read(4)

        if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:
            endian_format = '<' if file_version == b'\x02\x01\x00\x01' else '>'
            logger(t("version_21_le") if endian_format == '<' else t("version_21_be"), color=COLOR_LOG_YELLOW)

            file.seek(36)
            pointers_offset = struct.unpack(f'{endian_format}I', file.read(4))[0]
            file.seek(4, os.SEEK_CUR)
            names_offset = struct.unpack(f'{endian_format}I', file.read(4))[0]
            file.seek(4, os.SEEK_CUR)

            file.seek(56)
            total_items = struct.unpack(f'{endian_format}I', file.read(4))[0]

            pointers = []
            file.seek(pointers_offset)
            for _ in range(total_items):
                file.seek(4, os.SEEK_CUR)
                file_offset = struct.unpack(f'{endian_format}I', file.read(4))[0]
                file_size = struct.unpack(f'{endian_format}I', file.read(4))[0]
                pointers.append((file_offset, file_size))

            names = []
            if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:
                file.seek(names_offset + 5)
            else:
                file.seek(names_offset + 8)
            
            for _ in range(total_items):
                if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:
                    file.seek(15, 1)
                else:
                    file.seek(12, 1)
                name_size = struct.unpack('<I', file.read(4))[0]
                name_bytes = file.read(name_size)
                try:
                    name = name_bytes.decode('utf-8').strip('\x00')
                    names.append(name)
                except UnicodeDecodeError:
                    names.append(f"unknown_{len(names)}")

            if file_version == b'\x02\x01\x00\x01':
                pointers.sort(key=lambda x: x[0])

            for i, (file_offset, file_size) in enumerate(pointers):
                if i >= len(names):
                    break
                file.seek(file_offset)
                data = file.read(file_size)
                file_name = names[i].strip()
                complete_path = extraction_directory / file_name.lstrip("/\\")
                complete_path.parent.mkdir(parents=True, exist_ok=True)
                with open(complete_path, 'wb') as f:
                    f.write(data)
                logger(t("file_extracted", name=file_name), color=COLOR_LOG_GREEN)

            names_list_path = base_directory / f"{base_filename}.txt"
            with open(names_list_path, 'w', encoding='utf-8') as names_list:
                for name in names:
                    names_list.write(name + '\n')

        elif file_version == b'\x01\x02\x00\x01':
            logger(t("version_12_le"), color=COLOR_LOG_YELLOW)

            file.seek(2048)
            total_items = struct.unpack('<I', file.read(4))[0]
            names_offset = struct.unpack('<I', file.read(4))[0]
            file.seek(8, os.SEEK_CUR)

            pointers = []
            for _ in range(total_items):
                file.seek(4, os.SEEK_CUR)
                file_offset = struct.unpack('<I', file.read(4))[0]
                file_size = struct.unpack('<I', file.read(4))[0]
                pointers.append((file_offset, file_size))

            names = []
            file.seek(names_offset + 4)
            for _ in range(total_items):
                file.seek(4, os.SEEK_CUR)
                name_size = struct.unpack('<I', file.read(4))[0]
                name_bytes = file.read(name_size)
                try:
                    name = name_bytes.decode('utf-8').strip('\x00')
                    names.append(name)
                except UnicodeDecodeError:
                    names.append(f"unknown_{len(names)}")

            for i, (file_offset, file_size) in enumerate(pointers):
                if i >= len(names):
                    break
                file.seek(file_offset)
                data = file.read(file_size)
                file_name = names[i].strip()
                complete_path = extraction_directory / file_name.lstrip("/\\")
                complete_path.parent.mkdir(parents=True, exist_ok=True)
                with open(complete_path, 'wb') as f:
                    f.write(data)
                logger(t("file_extracted", name=file_name), color=COLOR_LOG_GREEN)

            names_list_path = base_directory / f"{base_filename}.txt"
            with open(names_list_path, 'w', encoding='utf-8') as names_list:
                for name in names:
                    names_list.write(name + '\n')

        else:
            logger(t("unsupported_file"), color=COLOR_LOG_RED)
            return

    logger(t("extraction_completed", path=str(extraction_directory)), color=COLOR_LOG_GREEN)


def _recreate_rcf(original_file_path: Path, txt_names_path: Path):
    """Reconstroi o arquivo RCF a partir da pasta extraída e da lista de nomes."""
    logger(t("processing", name=original_file_path.name), color=COLOR_LOG_YELLOW)

    base_filename = original_file_path.stem
    base_directory = original_file_path.parent
    new_rcf_path = base_directory / f"{base_filename}_MOD.rcf"
    extracted_files_directory = base_directory / base_filename

    if not extracted_files_directory.exists():
        logger(
            t("folder_not_found", folder=str(extracted_files_directory)),
            color=COLOR_LOG_RED
        )
        return

    if not txt_names_path.exists():
        logger(
            t("file_not_found", file=str(txt_names_path)),
            color=COLOR_LOG_RED
        )
        return

    # ==========================================================================
    # LER INFORMAÇÕES DO RCF ORIGINAL
    # ==========================================================================

    original_pointer_order = []
    pointers_offset = None
    total_items = 0

    with open(original_file_path, 'rb') as original_file:

        original_file.seek(32)
        file_version = original_file.read(4)

        # ======================================================================
        # RCF 2.1
        # ======================================================================

        if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:

            endian_format = '<' if file_version == b'\x02\x01\x00\x01' else '>'

            logger(
                t("version_21_le")
                if endian_format == '<'
                else t("version_21_be"),
                color=COLOR_LOG_YELLOW
            )

            # ------------------------------------------------------------------
            # Lê o offset da tabela de ponteiros
            # ------------------------------------------------------------------

            original_file.seek(36)

            pointers_offset = struct.unpack(
                f'{endian_format}I',
                original_file.read(4)
            )[0]

            # ------------------------------------------------------------------
            # Informações usadas para calcular o tamanho do header
            # ------------------------------------------------------------------

            original_file.seek(44)

            offset_value = struct.unpack(
                f'{endian_format}I',
                original_file.read(4)
            )[0]

            original_file.seek(48)

            size_value = struct.unpack(
                f'{endian_format}I',
                original_file.read(4)
            )[0]

            # ------------------------------------------------------------------
            # Quantidade de arquivos
            # ------------------------------------------------------------------

            original_file.seek(56)

            total_items = struct.unpack(
                f'{endian_format}I',
                original_file.read(4)
            )[0]

            # ------------------------------------------------------------------
            # Lê a tabela ORIGINAL de ponteiros.
            #
            # Guardamos:
            #
            #   (
            #       índice_original_da_tabela,
            #       offset_original,
            #       tamanho_original
            #   )
            #
            # Isso é necessário porque o extrator reorganiza os ponteiros
            # da versão 02 01 00 01 antes de associá-los aos nomes.
            # ------------------------------------------------------------------

            original_pointers = []

            original_file.seek(pointers_offset)

            for index in range(total_items):

                # Campo desconhecido / ID
                original_file.seek(4, os.SEEK_CUR)

                file_offset = struct.unpack(
                    f'{endian_format}I',
                    original_file.read(4)
                )[0]

                file_size = struct.unpack(
                    f'{endian_format}I',
                    original_file.read(4)
                )[0]

                original_pointers.append(
                    (
                        index,
                        file_offset,
                        file_size
                    )
                )

            # ------------------------------------------------------------------
            # IMPORTANTE:
            #
            # Na extração da versão 02 01 00 01 existe:
            #
            #     pointers.sort(key=lambda x: x[0])
            #
            # Portanto os nomes são associados aos arquivos pela ordem crescente
            # dos offsets e NÃO pela posição original na tabela.
            #
            # Aqui construímos o mapeamento inverso:
            #
            # índice do nome -> slot original da tabela
            #
            # Exemplo:
            #
            # tabela original:
            #
            # slot 0 = offset 5000
            # slot 1 = offset 3000
            # slot 2 = offset 7000
            # slot 3 = offset 4000
            #
            # depois do sort:
            #
            # nome 0 = slot 1
            # nome 1 = slot 3
            # nome 2 = slot 0
            # nome 3 = slot 2
            #
            # original_pointer_order:
            #
            # [1, 3, 0, 2]
            # ------------------------------------------------------------------

            if file_version == b'\x02\x01\x00\x01':

                sorted_original_pointers = sorted(
                    original_pointers,
                    key=lambda x: x[1]
                )

                original_pointer_order = [
                    original_index
                    for original_index, file_offset, file_size
                    in sorted_original_pointers
                ]

            else:
                # --------------------------------------------------------------
                # 2.1 Big Endian.
                #
                # O extrator NÃO ordena os ponteiros nessa versão.
                # Portanto a associação nomes -> tabela é direta.
                # --------------------------------------------------------------

                original_pointer_order = list(range(total_items))

            # ------------------------------------------------------------------
            # Copia o header original
            # ------------------------------------------------------------------

            header_size = offset_value + size_value
            adjusted_header_size = calculate_padding(header_size)

            original_file.seek(0)
            header = original_file.read(adjusted_header_size)

        # ======================================================================
        # RCF 1.2 LITTLE ENDIAN
        # ======================================================================

        elif file_version == b'\x01\x02\x00\x01':

            logger(
                t("version_12_le"),
                color=COLOR_LOG_YELLOW
            )

            endian_format = '<'

            original_file.seek(2048)

            total_items = struct.unpack(
                '<I',
                original_file.read(4)
            )[0]

            names_offset = struct.unpack(
                '<I',
                original_file.read(4)
            )[0]

            # ------------------------------------------------------------------
            # Na versão 1.2 os ponteiros não são ordenados durante a extração.
            # A ordem dos nomes corresponde diretamente à tabela.
            # ------------------------------------------------------------------

            original_pointer_order = list(range(total_items))

            # ------------------------------------------------------------------
            # Percorre a tabela de nomes para descobrir o fim do header.
            # ------------------------------------------------------------------

            original_file.seek(names_offset + 4)

            for _ in range(total_items):

                original_file.seek(
                    4,
                    os.SEEK_CUR
                )

                name_size = struct.unpack(
                    '<I',
                    original_file.read(4)
                )[0]

                original_file.read(name_size)

            header_size = original_file.tell()
            adjusted_header_size = calculate_padding(header_size)

            original_file.seek(0)
            header = original_file.read(adjusted_header_size)

        # ======================================================================
        # VERSÃO NÃO SUPORTADA
        # ======================================================================

        else:

            logger(
                t("unsupported_file"),
                color=COLOR_LOG_RED
            )

            return

    # ==========================================================================
    # LER LISTA DE NOMES
    # ==========================================================================

    names = []

    with open(txt_names_path, 'r', encoding='utf-8') as txt_names:

        for line in txt_names:

            file_name = line.lstrip("/\\").strip()

            if file_name:
                names.append(file_name)

    # ==========================================================================
    # CRIAR NOVO RCF
    # ==========================================================================

    with open(new_rcf_path, 'w+b') as new_rcf:

        # ----------------------------------------------------------------------
        # Copia o header original primeiro.
        # ----------------------------------------------------------------------

        new_rcf.write(header)

        # ----------------------------------------------------------------------
        # Aqui guardamos:
        #
        # (
        #     índice_do_nome,
        #     novo_offset,
        #     novo_tamanho
        # )
        #
        # O índice do nome é importante para podermos aplicar posteriormente
        # o mapeamento original da tabela.
        # ----------------------------------------------------------------------

        new_pointers = []

        current_position = adjusted_header_size

        # ----------------------------------------------------------------------
        # Escreve os arquivos seguindo EXATAMENTE a ordem da lista TXT.
        #
        # Essa é a mesma ordem usada pelo extrator para associar:
        #
        # names[i] <-> pointers[i]
        # ----------------------------------------------------------------------

        for name_index, file_name in enumerate(names):

            file_path = extracted_files_directory / file_name

            if not file_path.exists():

                logger(
                    t("file_not_found", file=str(file_path)),
                    color=COLOR_LOG_YELLOW
                )

                continue

            with open(file_path, 'rb') as f_file:
                file_data = f_file.read()

            original_size = len(file_data)

            size_with_padding = calculate_padding(
                original_size
            )

            # ------------------------------------------------------------------
            # Offset onde este arquivo começa no novo RCF
            # ------------------------------------------------------------------

            new_file_offset = current_position

            # ------------------------------------------------------------------
            # Grava os dados
            # ------------------------------------------------------------------

            new_rcf.write(file_data)

            # ------------------------------------------------------------------
            # Padding para múltiplos de 512
            # ------------------------------------------------------------------

            padding_size = (
                size_with_padding -
                original_size
            )

            if padding_size > 0:

                new_rcf.write(
                    b'\x00' * padding_size
                )

            # ------------------------------------------------------------------
            # Guarda novo ponteiro
            # ------------------------------------------------------------------

            new_pointers.append(
                (
                    name_index,
                    new_file_offset,
                    original_size
                )
            )

            current_position += size_with_padding

        # ======================================================================
        # ATUALIZAR A TABELA DE PONTEIROS
        # ======================================================================

        # ----------------------------------------------------------------------
        # RCF 2.1
        # ----------------------------------------------------------------------

        if file_version in [b'\x02\x01\x00\x01', b'\x02\x01\x01\x01']:

            endian_format = (
                '<'
                if file_version == b'\x02\x01\x00\x01'
                else '>'
            )

            # ------------------------------------------------------------------
            # Criamos uma tabela com a quantidade EXATA de slots do arquivo
            # original.
            #
            # Cada elemento representa:
            #
            # slot_original -> (novo_offset, novo_tamanho)
            # ------------------------------------------------------------------

            reordered_pointers = [None] * total_items

            # ------------------------------------------------------------------
            # Transforma:
            #
            # nome -> novo ponteiro
            #
            # em:
            #
            # slot original -> novo ponteiro
            # ------------------------------------------------------------------

            for name_index, pointer, original_size in new_pointers:

                if name_index >= len(original_pointer_order):
                    continue

                original_slot = original_pointer_order[
                    name_index
                ]

                reordered_pointers[
                    original_slot
                ] = (
                    pointer,
                    original_size
                )

            # ------------------------------------------------------------------
            # IMPORTANTE:
            #
            # Usamos pointers_offset lido do próprio RCF original.
            #
            # Isso é mais seguro do que assumir que a tabela sempre começa
            # obrigatoriamente no offset 60.
            # ------------------------------------------------------------------

            new_rcf.seek(pointers_offset)

            for pointer_data in reordered_pointers:

                # --------------------------------------------------------------
                # Cada entrada possui:
                #
                # 4 bytes = campo original que não alteramos
                # 4 bytes = offset
                # 4 bytes = tamanho
                #
                # --------------------------------------------------------------

                new_rcf.seek(
                    4,
                    os.SEEK_CUR
                )

                if pointer_data is None:

                    # ----------------------------------------------------------
                    # Se algum arquivo não tiver sido encontrado, mantemos
                    # os 8 bytes existentes no header copiado.
                    #
                    # Isso preserva o comportamento mais próximo possível do
                    # RCF original sem deslocar os outros slots.
                    # ----------------------------------------------------------

                    new_rcf.seek(
                        8,
                        os.SEEK_CUR
                    )

                    continue

                pointer, original_size = pointer_data

                new_rcf.write(
                    struct.pack(
                        f'{endian_format}I',
                        pointer
                    )
                )

                new_rcf.write(
                    struct.pack(
                        f'{endian_format}I',
                        original_size
                    )
                )

        # ----------------------------------------------------------------------
        # RCF 1.2
        # ----------------------------------------------------------------------

        elif file_version == b'\x01\x02\x00\x01':

            # ------------------------------------------------------------------
            # A tabela de ponteiros começa em 2064:
            #
            # 2048 = início da estrutura
            # + 4 = total_items
            # + 4 = names_offset
            # + 8 = outros campos
            #
            # = 2064
            # ------------------------------------------------------------------

            new_rcf.seek(2064)

            # ------------------------------------------------------------------
            # Como 1.2 não sofre sort na extração, os índices correspondem
            # diretamente aos slots.
            # ------------------------------------------------------------------

            pointers_by_name = {
                name_index: (
                    pointer,
                    original_size
                )
                for name_index, pointer, original_size
                in new_pointers
            }

            for slot_index in range(total_items):

                # Campo de 4 bytes que não modificamos
                new_rcf.seek(
                    4,
                    os.SEEK_CUR
                )

                pointer_data = pointers_by_name.get(
                    slot_index
                )

                if pointer_data is None:

                    # Mantém os valores originais caso o arquivo esteja ausente
                    new_rcf.seek(
                        8,
                        os.SEEK_CUR
                    )

                    continue

                pointer, original_size = pointer_data

                new_rcf.write(
                    struct.pack(
                        '<I',
                        pointer
                    )
                )

                new_rcf.write(
                    struct.pack(
                        '<I',
                        original_size
                    )
                )

    logger(
        t("recreation_completed", path=str(new_rcf_path)),
        color=COLOR_LOG_GREEN
    )


# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================

def action_extract():
    fp_extract.pick_files(
        allowed_extensions=["rcf"],
        dialog_title=t("select_rcf_file")
    )

def action_rebuild():
    fp_rebuild_rcf.pick_files(
        allowed_extensions=["rcf"],
        dialog_title=t("select_rcf_file")
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
        host_page.overlay.extend([fp_extract, fp_rebuild_rcf, fp_rebuild_txt])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_file"), "action": action_extract},
            {"label": t("rebuild_file"), "action": action_rebuild},
        ]
    }