# Parte do script feito por Krisp
import os
import struct
from pathlib import Path
from collections import defaultdict
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "AFS (PS2) Extrai e remonta arquivos",
        "plugin_description": "Extrai e recria arquivos AFS de Playstation 2",
        "extract_file": "Extrair Arquivo",
        "rebuild_file": "Reconstruir AFS",
        "select_afs_file": "Selecione um arquivo AFS",
        "select_original_afs": "Selecione o AFS ORIGINAL (será sobrescrito)",
        "select_extracted_folder": "Selecione a pasta extraída (se necessário)",
        "invalid_file_magic": "Arquivo inválido: Magic incorreto (esperado 'AFS\\x00').",
        "metadata_pointer_found": "Ponteiro da tabela de metadados encontrado!!!",
        "invalid_metadata_pointer": "Ponteiro de metadados inválido ou nulo. Extraindo sem nomes de grupo.",
        "metadata_pointer_not_found": "Não foi possível encontrar o ponteiro para a tabela de metadados. Extraindo sem nomes de grupo.",
        "extracting_to_group": "Extraindo:{file}",
        "extracting_to_root": "Extraindo: {file}",
        "completed": "Concluído",
        "extraction_completed": "Extração de {count} arquivos concluída em: {path}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "unexpected_error": "Ocorreu um erro inesperado: {error}",
        "detailed_error": "Erro detalhado: {error}",
        "afs_files": "Arquivos AFS",
        "all_files": "Todos os arquivos",
        "rebuild_started": "Reconstrução iniciada",
        "rebuild_ok": "AFS reconstruído (sobrescrito) em: {path}",
        "list_missing": "Lista .txt não encontrada: {path}",
        "folder_missing": "Pasta de extração não encontrada: {path}",
        "list_count_mismatch": "A contagem de arquivos na lista ({lst}) difere da do AFS original ({afs}). Operação abortada.",
        "missing_extracted_file": "Arquivo listado não existe na pasta extraída: {path}",
        "reading_list": "Lendo lista: {path}",
        "writing_file": "Escrevendo arquivo {i}/{n}: {name}",
        "metadata_copied": "Bloco de metadados copiado para o final (novo ponteiro: 0x{ptr:08X}).",
        "header_updated": "Tabela de posições/tamanhos e ponteiro de metadados atualizados.",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "AFS (PS2) Extract and rebuild files",
        "plugin_description": "Extracts and recreates AFS files from Playstation 2",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild AFS",
        "select_afs_file": "Select an AFS file",
        "select_original_afs": "Select the ORIGINAL AFS (will be overwritten)",
        "select_extracted_folder": "Select the extracted folder (if needed)",
        "invalid_file_magic": "Invalid file: Incorrect magic (expected 'AFS\\x00').",
        "metadata_pointer_found": "Metadata table pointer found!!!",
        "invalid_metadata_pointer": "Invalid or null metadata pointer. Extracting without group names.",
        "metadata_pointer_not_found": "Could not find pointer to metadata table. Extracting without group names.",
        "extracting_to_group": "Extracting:{file}",
        "extracting_to_root": "Extracting: {file}",
        "completed": "Completed",
        "extraction_completed": "Extraction of {count} files completed in: {path}",
        "file_not_found": "File not found: {file}",
        "unexpected_error": "An unexpected error occurred: {error}",
        "detailed_error": "Detailed error: {error}",
        "afs_files": "AFS files",
        "all_files": "All files",
        "rebuild_started": "Rebuild started",
        "rebuild_ok": "AFS rebuilt (overwritten) at: {path}",
        "list_missing": "List .txt not found: {path}",
        "folder_missing": "Extracted folder not found: {path}",
        "list_count_mismatch": "File count in list ({lst}) differs from original AFS ({afs}). Aborting.",
        "missing_extracted_file": "Listed file does not exist in extracted folder: {path}",
        "reading_list": "Reading list: {path}",
        "writing_file": "Writing file {i}/{n}: {name}",
        "metadata_copied": "Metadata block copied to the end (new pointer: 0x{ptr:08X}).",
        "header_updated": "Offsets/sizes table and metadata pointer updated.",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "AFS (PS2) Extraer y reconstruir archivos",
        "plugin_description": "Extrae y recrea archivos AFS de Playstation 2",
        "extract_file": "Extraer Archivo",
        "rebuild_file": "Reconstruir AFS",
        "select_afs_file": "Seleccionar un archivo AFS",
        "select_original_afs": "Seleccione el AFS ORIGINAL (será sobrescrito)",
        "select_extracted_folder": "Seleccione la carpeta extraída (si es necesario)",
        "invalid_file_magic": "Archivo inválido: Magic incorrecto (se esperaba 'AFS\\x00').",
        "metadata_pointer_found": "¡Puntero de tabla de metadatos encontrado!",
        "invalid_metadata_pointer": "Puntero de metadatos inválido o nulo. Extrayendo sin nombres de grupo.",
        "metadata_pointer_not_found": "No se pudo encontrar el puntero a la tabla de metadatos. Extrayendo sin nombres de grupo.",
        "extracting_to_group": "Extrayendo:{file}",
        "extracting_to_root": "Extrayendo: {file}",
        "completed": "Completado",
        "extraction_completed": "Extracción de {count} archivos completada en: {path}",
        "file_not_found": "Archivo no encontrado: {file}",
        "unexpected_error": "Ocurrió un error inesperado: {error}",
        "detailed_error": "Error detallado: {error}",
        "afs_files": "Archivos AFS",
        "all_files": "Todos los archivos",
        "rebuild_started": "Reconstrucción iniciada",
        "rebuild_ok": "AFS reconstruido (sobrescrito) en: {path}",
        "list_missing": "No se encontró la lista .txt: {path}",
        "folder_missing": "Carpeta extraída no encontrada: {path}",
        "list_count_mismatch": "El número de archivos en la lista ({lst}) difiere del AFS original ({afs}). Abortando.",
        "missing_extracted_file": "El archivo listado no existe en la carpeta extraída: {path}",
        "reading_list": "Leyendo lista: {path}",
        "writing_file": "Escribiendo archivo {i}/{n}: {name}",
        "metadata_copied": "Bloque de metadatos copiado al final (nuevo puntero: 0x{ptr:08X}).",
        "header_updated": "Tabla de offsets/tamaños y puntero de metadatos actualizados.",
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
    on_result=lambda e: _extrair_afs(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

fp_rebuild = ft.FilePicker(
    on_result=lambda e: _reconstruir_afs_inplace(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# FUNÇÕES AUXILIARES (MANTIDAS DO ORIGINAL)
# ==============================================================================
def pad_to_boundary(fobj, boundary):
    cur = fobj.tell()
    pad = (-cur) % boundary
    if pad:
        fobj.write(b"\x00" * pad)

# ==============================================================================
# EXTRAÇÃO (ADAPTADA PARA USAR PATH E LOGGER)
# ==============================================================================
def _extrair_afs(arquivo_afs: Path):
    try:
        with open(arquivo_afs, 'rb') as f:
            magic = f.read(4)
            if magic != b'AFS\x00':
                logger(t("invalid_file_magic"), color=COLOR_LOG_RED)
                return

            total_itens = struct.unpack('<I', f.read(4))[0]
            posicoes, tamanhos = [], []
            for _ in range(total_itens):
                posicoes.append(struct.unpack('<I', f.read(4))[0])
                tamanhos.append(struct.unpack('<I', f.read(4))[0])

            nomes_grupos = []
            if tamanhos[-1] == 0:
                ponteiro_meta = posicoes[-1]
                posicoes.pop(); tamanhos.pop()
            else:
                ponteiro_meta = struct.unpack('<I', f.read(4))[0]

            if ponteiro_meta > 0:
                logger(t("metadata_pointer_found"), color=COLOR_LOG_YELLOW)
                f.seek(ponteiro_meta)
                for _ in range(len(posicoes)):
                    nome_bytes = f.read(32)
                    if len(nome_bytes) < 32:
                        nomes_grupos.append("")
                        continue
                    try:
                        nome_limpo = nome_bytes.strip(b'\x00').decode('shift_jis', errors='ignore').strip()
                    except Exception:
                        nome_limpo = ""
                    nomes_grupos.append(nome_limpo)
                    f.seek(16, 1)
            else:
                logger(t("metadata_pointer_not_found"), color=COLOR_LOG_YELLOW)
                nomes_grupos = [""] * len(posicoes)

            pasta_saida = arquivo_afs.parent / arquivo_afs.stem
            pasta_saida.mkdir(parents=True, exist_ok=True)

            contagem_sufixos = defaultdict(int)
            base_nome_afs = arquivo_afs.stem
            lista_arquivos = []

            for i, (pos, tamanho, grupo) in enumerate(zip(posicoes, tamanhos, nomes_grupos)):
                if tamanho == 0:
                    continue
                f.seek(pos)
                dados = f.read(tamanho)

                if grupo:
                    nome_base = grupo
                    nome_arquivo = nome_base
                    caminho_saida = pasta_saida / nome_arquivo
                    contador = 1
                    while caminho_saida.exists():
                        nome_arquivo = f"{nome_base}_{contador}"
                        caminho_saida = pasta_saida / nome_arquivo
                        contador += 1
                    logger(t("extracting_to_group", file=nome_arquivo), color=COLOR_LOG_YELLOW)
                else:
                    contagem_sufixos['__root__'] += 1
                    nome_arquivo = f"{base_nome_afs}_{contagem_sufixos['__root__']:05d}.bin"
                    caminho_saida = pasta_saida / nome_arquivo
                    logger(t("extracting_to_root", file=nome_arquivo), color=COLOR_LOG_YELLOW)

                with open(caminho_saida, 'wb') as saida:
                    saida.write(dados)

                nome_arquivo = os.path.normpath(nome_arquivo)
                lista_arquivos.append(nome_arquivo)

            lista_txt = arquivo_afs.parent / (arquivo_afs.stem + ".txt")
            with open(lista_txt, 'w', encoding='utf-8', newline='\n') as arquivo_lista:
                for nome in lista_arquivos:
                    arquivo_lista.write(nome + '\n')

            logger(t("extraction_completed", count=len(posicoes), path=str(pasta_saida)), color=COLOR_LOG_GREEN)

    except FileNotFoundError:
        logger(t("file_not_found", file=str(arquivo_afs)), color=COLOR_LOG_RED)
    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# RECONSTRUÇÃO (ADAPTADA PARA USAR PATH E LOGGER)
# ==============================================================================
def _reconstruir_afs_inplace(afs_original_path: Path):
    try:
        with open(afs_original_path, 'r+b') as f:
            magic = f.read(4)
            if magic != b'AFS\x00':
                logger(t("invalid_file_magic"), color=COLOR_LOG_RED)
                return

            total_itens = struct.unpack('<I', f.read(4))[0]
            orig_pos = []
            orig_size = []
            for _ in range(total_itens):
                orig_pos.append(struct.unpack('<I', f.read(4))[0])
                orig_size.append(struct.unpack('<I', f.read(4))[0])

            meta_as_entry = False
            if orig_size[-1] == 0:
                meta_as_entry = True
                orig_meta_ptr = orig_pos[-1]
                data_count = total_itens - 1
            else:
                orig_meta_ptr = struct.unpack('<I', f.read(4))[0]
                data_count = total_itens

            f.seek(0, os.SEEK_END)
            file_end = f.tell()
            if orig_meta_ptr > 0 and orig_meta_ptr < file_end:
                f.seek(orig_meta_ptr)
                metadata_blob = f.read()
            else:
                metadata_blob = b""

            table_size = total_itens * 8
            ptr_offset_pos = 8 + table_size

            base = afs_original_path.stem
            extracted_dir = afs_original_path.parent / base
            list_txt = afs_original_path.parent / (base + ".txt")

            if not list_txt.is_file():
                logger(t("list_missing", path=str(list_txt)), color=COLOR_LOG_RED)
                return
            if not extracted_dir.is_dir():
                logger(t("folder_missing", path=str(extracted_dir)), color=COLOR_LOG_RED)
                return

            logger(t("reading_list", path=str(list_txt)), color=COLOR_LOG_YELLOW)

            lines = None
            for enc in ('utf-8', 'cp1252', 'latin-1'):
                try:
                    with open(list_txt, 'r', encoding=enc) as fh:
                        lines = [ln.strip() for ln in fh.readlines() if ln.strip()]
                    break
                except Exception:
                    continue
            if lines is None:
                with open(list_txt, 'r', errors='ignore') as fh:
                    lines = [ln.strip() for ln in fh.readlines() if ln.strip()]

            if len(lines) != data_count:
                logger(t("list_count_mismatch", lst=len(lines), afs=data_count), color=COLOR_LOG_RED)
                return

            file_paths = []
            for rel in lines:
                candidate = extracted_dir / rel
                if not candidate.is_file():
                    alt = extracted_dir / os.path.basename(rel)
                    if alt.is_file():
                        candidate = alt
                    else:
                        logger(t("missing_extracted_file", path=str(candidate)), color=COLOR_LOG_RED)
                        return
                file_paths.append(candidate)

            first_data_offset = orig_pos[0]
            f.seek(first_data_offset, os.SEEK_SET)

            new_pos = []
            new_size = []

            for idx, path in enumerate(file_paths, start=1):
                logger(t("writing_file", i=idx, n=len(file_paths), name=path.name), color=COLOR_LOG_YELLOW)

                start = f.tell()
                with open(path, 'rb') as rf:
                    data = rf.read()
                f.write(data)
                size = len(data)

                pad_to_boundary(f, 2048)

                new_pos.append(start)
                new_size.append(size)

            new_meta_ptr = f.tell()
            if metadata_blob:
                f.write(metadata_blob)
            logger(t("metadata_copied", ptr=new_meta_ptr), color=COLOR_LOG_YELLOW)

            f.seek(8, os.SEEK_SET)

            if meta_as_entry:
                for p, s in zip(new_pos, new_size):
                    f.write(struct.pack('<I', p))
                    f.write(struct.pack('<I', s))
                f.write(struct.pack('<I', new_meta_ptr))
                f.write(struct.pack('<I', 0))
            else:
                for p, s in zip(new_pos, new_size):
                    f.write(struct.pack('<I', p))
                    f.write(struct.pack('<I', s))
                f.seek(ptr_offset_pos, os.SEEK_SET)
                f.write(struct.pack('<I', new_meta_ptr))

            logger(t("header_updated"), color=COLOR_LOG_YELLOW)

        logger(t("rebuild_ok", path=str(afs_original_path)), color=COLOR_LOG_GREEN)

    except FileNotFoundError as e:
        logger(t("file_not_found", file=str(e)), color=COLOR_LOG_RED)
    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================
def action_extract():
    fp_extract.pick_files(
        allowed_extensions=["afs"],
        dialog_title=t("select_afs_file")
    )

def action_rebuild():
    fp_rebuild.pick_files(
        allowed_extensions=["afs"],
        dialog_title=t("select_original_afs")
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