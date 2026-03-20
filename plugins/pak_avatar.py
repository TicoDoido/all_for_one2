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
        "plugin_name": "PAK|STR - Avatar The Last Airbender (PS2)",
        "plugin_description": "Extrai e recria arquivos PAK|STR dos jogos Avatar The Last Airbender/The Burning Earth/Into the Inferno para PS2",
        "extract_file": "Extrair Arquivo",
        "rebuild_file": "Recriar Arquivo",
        "extract_text": "Extrair Texto (.str)",
        "reinsert_text": "Remontar texto (.str)",
        "select_pak_file": "Selecione o arquivo .pak",
        "select_txt_file": "Selecione o arquivo .txt",
        "select_str_file": "Selecione o arquivo .str",
        "pak_files": "Arquivos PAK",
        "str_files": "Arquivos STR",
        "text_files": "Arquivos de Texto",
        "all_files": "Todos os arquivos",
        "invalid_magic": "Arquivo não tem o magic esperado!",
        "extraction_completed": "Extração concluída com sucesso! Arquivos em: {folder}",
        "reinsertion_completed": "Reinserção concluída com sucesso!",
        "text_extraction_completed": "Textos extraídos e salvos em: {path}",
        "text_reinsertion_completed": "Textos reinseridos no arquivo binário.",
        "folder_not_found": "Pasta não encontrada: {folder}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "unexpected_error": "Ocorreu um erro inesperado: {error}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "extracting_to": "Extraindo para: {path}",
        "file_extracted": "Arquivo extraído: {name}",
        "progress_status": "{percent}% - {current}/{total} arquivos",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "PAK|STR - Avatar The Last Airbender (PS2)",
        "plugin_description": "Extracts and rebuilds PAK|STR files from Avatar The Last Airbender/The Burning Earth/Into the Inferno PS2 games",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild File",
        "extract_text": "Extract Text (.str)",
        "reinsert_text": "Reinsert Text (.str)",
        "select_pak_file": "Select .pak file",
        "select_txt_file": "Select .txt file",
        "select_str_file": "Select .str file",
        "pak_files": "PAK Files",
        "str_files": "STR Files",
        "text_files": "Text Files",
        "all_files": "All files",
        "invalid_magic": "File does not have expected magic!",
        "extraction_completed": "Extraction completed successfully! Files in: {folder}",
        "reinsertion_completed": "Reinsertion completed successfully!",
        "text_extraction_completed": "Texts extracted and saved to: {path}",
        "text_reinsertion_completed": "Texts reinserted into binary file.",
        "folder_not_found": "Folder not found: {folder}",
        "file_not_found": "File not found: {file}",
        "unexpected_error": "An unexpected error occurred: {error}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "extracting_to": "Extracting to: {path}",
        "file_extracted": "File extracted: {name}",
        "progress_status": "{percent}% - {current}/{total} files",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "PAK|STR - Avatar The Last Airbender (PS2)",
        "plugin_description": "Extrae y reconstruye archivos PAK|STR de los juegos Avatar The Last Airbender/The Burning Earth/Into the Inferno para PS2",
        "extract_file": "Extraer Archivo",
        "rebuild_file": "Reconstruir Archivo",
        "extract_text": "Extraer Texto (.str)",
        "reinsert_text": "Reinsertar Texto (.str)",
        "select_pak_file": "Seleccionar archivo .pak",
        "select_txt_file": "Seleccionar archivo .txt",
        "select_str_file": "Seleccionar archivo .str",
        "pak_files": "Archivos PAK",
        "str_files": "Archivos STR",
        "text_files": "Archivos de Texto",
        "all_files": "Todos los archivos",
        "invalid_magic": "¡El archivo no tiene el magic esperado!",
        "extraction_completed": "¡Extracción completada con éxito! Archivos en: {folder}",
        "reinsertion_completed": "¡Reinserción completada con éxito!",
        "text_extraction_completed": "Textos extraídos y guardados en: {path}",
        "text_reinsertion_completed": "Textos reinsertados en el archivo binario.",
        "folder_not_found": "Carpeta no encontrada: {folder}",
        "file_not_found": "Archivo no encontrado: {file}",
        "unexpected_error": "Ocurrió un error inesperado: {error}",
        "cancelled": "Selección cancelada.",
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

fp_extract_pak = ft.FilePicker(
    on_result=lambda e: _extrair_pak(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)
fp_rebuild_pak = ft.FilePicker(
    on_result=lambda e: _recreate_file(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)
fp_extract_str = ft.FilePicker(
    on_result=lambda e: _extract_str(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)
fp_reinsert_str = ft.FilePicker(
    on_result=lambda e: _reinsert_str(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# FUNÇÕES AUXILIARES (LEITURA LITTLE ENDIAN)
# ==============================================================================
def ler_little_endian(arquivo, tamanho):
    return int.from_bytes(arquivo.read(tamanho), 'little')

def escrever_little_endian(arquivo, valor):
    arquivo.write(valor.to_bytes(4, 'little'))
    return valor

def read_little_endian_int(file):
    return struct.unpack('<I', file.read(4))[0]

# ==============================================================================
# FUNÇÕES PRINCIPAIS (PAK) - ADAPTADAS PARA RECEBER PATH
# ==============================================================================

def _extrair_pak(arquivo_pak):
    """Extrai arquivos do PAK selecionado."""
    logger(t("processing", name=arquivo_pak.name), color=COLOR_LOG_YELLOW)

    diretorio_arquivo = arquivo_pak.parent
    nome_pasta_saida = diretorio_arquivo / arquivo_pak.stem
    nome_pasta_saida = nome_pasta_saida.resolve()
    nome_pasta_saida.mkdir(parents=True, exist_ok=True)
    logger(t("extracting_to", path=str(nome_pasta_saida)), color=COLOR_LOG_YELLOW)

    lista_arquivos_extraidos = []

    with open(arquivo_pak, 'rb') as arquivo:
        magic = arquivo.read(8)
        if magic == b'kcap\x01\x00\x01\x00':
            tamanho_cabecalho = ler_little_endian(arquivo, 4)
            tamanho_total = ler_little_endian(arquivo, 4)
            posicao_nomes = ler_little_endian(arquivo, 4)
            tamanho_nomes = tamanho_cabecalho - posicao_nomes
            numero_itens = ler_little_endian(arquivo, 4)

            itens = []
            for _ in range(numero_itens):
                arquivo.seek(4, 1)
                ponteiro = ler_little_endian(arquivo, 4)
                tamanho_comp = ler_little_endian(arquivo, 4)
                tamanho_descomp = ler_little_endian(arquivo, 4)
                itens.append((ponteiro, tamanho_comp, tamanho_descomp))

            arquivo.seek(posicao_nomes)
            blocos_nomes = arquivo.read(tamanho_nomes)
            nomes_arquivos = blocos_nomes.split(b'\x00')[:numero_itens]
            nomes_arquivos = [nome.decode('utf-8').lstrip("//") for nome in nomes_arquivos if nome]

        elif magic == b'kcap\x01\x00\x02\x00':
            cabecalho_inicio = ler_little_endian(arquivo, 4)
            tamanho_cabecalho_total = ler_little_endian(arquivo, 4)
            tamanho_cabecalho_ponteiros = ler_little_endian(arquivo, 4)
            tamanho_nomes = tamanho_cabecalho_total - tamanho_cabecalho_ponteiros
            numero_itens = ler_little_endian(arquivo, 4)

            arquivo.seek(cabecalho_inicio)
            itens = []
            for _ in range(numero_itens):
                ponteiro = ler_little_endian(arquivo, 4)
                tamanho_descomp = ler_little_endian(arquivo, 4)
                tamanho_comp = ler_little_endian(arquivo, 4)
                itens.append((ponteiro, tamanho_descomp, tamanho_comp))
                arquivo.seek(12, 1)

            posicao_nomes = arquivo.tell()
            blocos_nomes = arquivo.read(tamanho_nomes)
            nomes_arquivos = blocos_nomes.split(b'\x00')[:numero_itens]
            nomes_arquivos = [nome.decode('utf-8').lstrip("//") for nome in nomes_arquivos if nome]

        else:
            raise ValueError(t("invalid_magic"))

        total = len(itens)
        for i, item in enumerate(itens):
            if magic == b'kcap\x01\x00\x01\x00':
                ponteiro, tamanho_comp, tamanho_descomp = item
            else:
                ponteiro, tamanho_descomp, tamanho_comp = item

            arquivo.seek(ponteiro)
            dados = arquivo.read(tamanho_comp)

            if tamanho_descomp > 0:
                try:
                    dados = zlib.decompress(dados)
                except zlib.error:
                    pass
                nome_arquivo = nomes_arquivos[i]
                nome_arquivo_descomprimido = os.path.splitext(nome_arquivo)[0] + "_descomprimido" + os.path.splitext(nome_arquivo)[1]
            else:
                nome_arquivo_descomprimido = nomes_arquivos[i]

            # Garantir caminho seguro
            nome_arquivo_descomprimido = nome_arquivo_descomprimido.replace("\\", "/").lstrip("/")
            caminho_completo = nome_pasta_saida / nome_arquivo_descomprimido
            caminho_completo.parent.mkdir(parents=True, exist_ok=True)

            with open(caminho_completo, 'wb') as saida:
                saida.write(dados)

            lista_arquivos_extraidos.append(nome_arquivo_descomprimido)

            percent = int((i + 1) / total * 100)
            logger(t("progress_status", percent=percent, current=i+1, total=total), color=COLOR_LOG_YELLOW)
            logger(t("file_extracted", name=nome_arquivo_descomprimido), color=COLOR_LOG_GREEN)

    lista_txt = diretorio_arquivo / (arquivo_pak.stem + '.txt')
    with open(lista_txt, 'w') as arquivo_lista:
        for nome in lista_arquivos_extraidos:
            arquivo_lista.write(nome + '\n')

    logger(t("extraction_completed", folder=str(nome_pasta_saida)), color=COLOR_LOG_GREEN)


def _recreate_file(arquivo_txt):
    """Reconstrói o PAK a partir do arquivo .txt de lista e pasta extraída."""
    logger(t("processing", name=arquivo_txt.name), color=COLOR_LOG_YELLOW)

    diretorio_txt = arquivo_txt.parent
    nome_pak = arquivo_txt.stem
    nome_pasta = diretorio_txt / nome_pak

    if not nome_pasta.exists():
        raise FileNotFoundError(t("folder_not_found", folder=str(nome_pasta)))

    with open(arquivo_txt, 'r') as arquivo:
        lista_arquivos = [linha.strip() for linha in arquivo.readlines()]

    arquivo_pak = diretorio_txt / (nome_pak + '.pak')
    if not arquivo_pak.exists():
        raise FileNotFoundError(t("file_not_found", file=str(arquivo_pak)))

    ponteiros = []
    tamanhos_normais = []
    tamanhos_comprimidos = []

    with open(arquivo_pak, 'r+b') as pak:
        magic = pak.read(8)
        if magic == b'kcap\x01\x00\x01\x00':
            pak.seek(28)
            posicao_insercao = ler_little_endian(pak, 4)
            logger(f"Iniciando inserção a partir da posição: 0x{posicao_insercao:08X}", color=COLOR_LOG_YELLOW)
            pak.seek(posicao_insercao)

            for nome_arquivo in lista_arquivos:
                caminho_arquivo = nome_pasta / nome_arquivo
                if not caminho_arquivo.exists():
                    raise FileNotFoundError(t("file_not_found", file=str(caminho_arquivo)))

                with open(caminho_arquivo, 'rb') as f:
                    dados = f.read()

                tamanho_normal = len(dados)
                tamanhos_normais.append(tamanho_normal)

                if '_descomprimido' in nome_arquivo:
                    dados = zlib.compress(dados)

                tamanho_comprimido = len(dados)
                tamanhos_comprimidos.append(tamanho_comprimido)

                if tamanho_comprimido % 2048 != 0:
                    padding = 2048 - (tamanho_comprimido % 2048)
                    dados += b'\x00' * padding

                ponteiro_atual = pak.tell()
                ponteiros.append(ponteiro_atual)
                pak.write(dados)
                posicao_insercao += len(dados)

            pak.truncate()
            pak.seek(24)

            for i in range(len(ponteiros)):
                pak.seek(4, 1)
                escrever_little_endian(pak, ponteiros[i])

                if tamanhos_normais[i] == tamanhos_comprimidos[i]:
                    escrever_little_endian(pak, tamanhos_normais[i])
                    pak.write(b'\x00\x00\x00\x00')
                else:
                    escrever_little_endian(pak, tamanhos_comprimidos[i])
                    escrever_little_endian(pak, tamanhos_normais[i])

        elif magic == b'kcap\x01\x00\x02\x00':
            inicio_ponteiros = ler_little_endian(pak, 4)
            pak.seek(inicio_ponteiros)
            posicao_insercao = ler_little_endian(pak, 4)
            logger(f"Iniciando inserção a partir da posição: 0x{posicao_insercao:08X}", color=COLOR_LOG_YELLOW)
            pak.seek(posicao_insercao)

            for nome_arquivo in lista_arquivos:
                caminho_arquivo = nome_pasta / nome_arquivo
                if not caminho_arquivo.exists():
                    raise FileNotFoundError(t("file_not_found", file=str(caminho_arquivo)))

                with open(caminho_arquivo, 'rb') as f:
                    dados = f.read()

                tamanho_normal = len(dados)
                tamanhos_normais.append(tamanho_normal)

                if '_descomprimido' in nome_arquivo:
                    dados = zlib.compress(dados, level=9)

                tamanho_comprimido = len(dados)
                tamanhos_comprimidos.append(tamanho_comprimido)

                if tamanho_comprimido % 2048 != 0:
                    padding = 2048 - (tamanho_comprimido % 2048)
                    dados += b'\x00' * padding

                ponteiro_atual = pak.tell()
                ponteiros.append(ponteiro_atual)
                pak.write(dados)
                posicao_insercao += len(dados)

            pak.truncate()
            pak.seek(inicio_ponteiros)

            for i in range(len(ponteiros)):
                escrever_little_endian(pak, ponteiros[i])

                if tamanhos_normais[i] == tamanhos_comprimidos[i]:
                    escrever_little_endian(pak, tamanhos_normais[i])
                    escrever_little_endian(pak, tamanhos_normais[i])
                else:
                    escrever_little_endian(pak, tamanhos_normais[i])
                    escrever_little_endian(pak, tamanhos_comprimidos[i])

                pak.seek(12, 1)

        logger(t("reinsertion_completed"), color=COLOR_LOG_GREEN)


# ==============================================================================
# FUNÇÕES PRINCIPAIS (STR) - ADAPTADAS PARA RECEBER PATH
# ==============================================================================

def _extract_str(file_path):
    """Extrai textos de um arquivo .str."""
    logger(t("processing", name=file_path.name), color=COLOR_LOG_YELLOW)

    with open(file_path, 'rb') as file:
        file.seek(8)
        total_texts = read_little_endian_int(file)
        pointers = []
        file.seek(12)

        for _ in range(total_texts):
            file.seek(4, 1)
            pointer = read_little_endian_int(file)
            pointers.append(pointer)
            file.seek(4, 1)

        texts = []
        text_start_position = 20 + (total_texts * 12)

        for pointer in pointers:
            text_position = pointer + text_start_position
            file.seek(text_position)
            text = b""
            while True:
                byte = file.read(1)
                if byte == b'\x00':
                    break
                text += byte
            texts.append(text.decode('utf8', errors='ignore'))

    output_file = file_path.with_suffix('.txt')
    with open(output_file, 'w', encoding='utf8') as f:
        for text in texts:
            f.write(f"{text}[FIM]\n")
    logger(t("text_extraction_completed", path=str(output_file)), color=COLOR_LOG_GREEN)


def _reinsert_str(file_path):
    """Reinsere textos em um arquivo .str."""
    logger(t("processing", name=file_path.name), color=COLOR_LOG_YELLOW)

    txt_file_path = file_path.with_suffix('.txt')
    if not txt_file_path.exists():
        raise FileNotFoundError(t("file_not_found", file=str(txt_file_path)))

    with open(txt_file_path, 'r', encoding='utf8') as f:
        texts = f.read().split("[FIM]\n")
        if texts and texts[-1] == "":
            texts.pop()

    with open(file_path, 'r+b') as file:
        file.seek(8)
        total_texts = read_little_endian_int(file)
        text_start_position = 20 + (total_texts * 12)
        offsets = []
        file.seek(text_start_position)

        for idx, text in enumerate(texts):
            offset = file.tell()
            offsets.append(offset - text_start_position)
            text_bytes = text.encode('utf8') + b'\x00'
            file.write(text_bytes)

        size = file.tell() - text_start_position
        file.seek(12)

        for offset in offsets:
            file.seek(4, 1)
            file.write(struct.pack('<I', offset))
            file.seek(4, 1)

        file.seek(text_start_position - 4)
        file.write(struct.pack('<I', size))

    logger(t("text_reinsertion_completed"), color=COLOR_LOG_GREEN)


# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================

def action_extract_pak():
    fp_extract_pak.pick_files(
        allowed_extensions=["pak"],
        dialog_title=t("select_pak_file")
    )

def action_rebuild_pak():
    fp_rebuild_pak.pick_files(
        allowed_extensions=["txt"],
        dialog_title=t("select_txt_file")
    )

def action_extract_str():
    fp_extract_str.pick_files(
        allowed_extensions=["str"],
        dialog_title=t("select_str_file")
    )

def action_reinsert_str():
    fp_reinsert_str.pick_files(
        allowed_extensions=["str"],
        dialog_title=t("select_str_file")
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
        host_page.overlay.extend([fp_extract_pak, fp_rebuild_pak, fp_extract_str, fp_reinsert_str])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_file"), "action": action_extract_pak},
            {"label": t("rebuild_file"), "action": action_rebuild_pak},
            {"label": t("extract_text"), "action": action_extract_str},
            {"label": t("reinsert_text"), "action": action_reinsert_str},
        ]
    }