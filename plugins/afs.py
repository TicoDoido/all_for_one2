# Parte do script feito por Krisp
import os
import struct
import flet as ft
from pathlib import Path
from collections import defaultdict

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
        "invalid_file_magic": "Arquivo inválido: Magic incorreto (esperado 'AFS\\x00').",
        "metadata_pointer_found": "Ponteiro da tabela de metadados encontrado!!!",
        "metadata_pointer_not_found": "Não foi possível encontrar o ponteiro para a tabela de metadados. Extraindo sem nomes de grupo.",
        "extracting_to_group": "Extraindo: {file}",
        "extracting_to_root": "Extraindo: {file}",
        "extraction_completed": "Extração de {count} arquivos concluída em: {path}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "unexpected_error": "Ocorreu um erro inesperado: {error}",
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
    },
    "en_US": {
        "plugin_name": "AFS (PS2) Extract and rebuild files",
        "plugin_description": "Extracts and recreates AFS files from Playstation 2",
        "extract_file": "Extract File",
        "rebuild_file": "Rebuild AFS",
        "select_afs_file": "Select an AFS file",
        "select_original_afs": "Select the ORIGINAL AFS (will be overwritten)",
        "invalid_file_magic": "Invalid file: Incorrect magic (expected 'AFS\\x00').",
        "metadata_pointer_found": "Metadata table pointer found!!!",
        "metadata_pointer_not_found": "Could not find pointer to metadata table. Extracting without group names.",
        "extracting_to_group": "Extracting: {file}",
        "extracting_to_root": "Extracting: {file}",
        "extraction_completed": "Extraction of {count} files completed in: {path}",
        "file_not_found": "File not found: {file}",
        "unexpected_error": "An unexpected error occurred: {error}",
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
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

# Variáveis globais
logger = None
get_option = None
current_lang = "pt_BR"
host_page = None

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================
def pad_to_boundary(fobj, boundary):
    cur = fobj.tell()
    pad = (-cur) % boundary
    if pad:
        fobj.write(b"\x00" * pad)

# ==============================================================================
# LÓGICA DE EXTRAÇÃO E RECONSTRUÇÃO
# ==============================================================================
def extrair_afs(arquivo_afs):
    try:
        if not arquivo_afs: return
        with open(arquivo_afs, 'rb') as f:
            magic = f.read(4)
            if magic != b'AFS\x00':
                if logger: logger(t("invalid_file_magic"), color=COLOR_LOG_RED)
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
                if logger: logger(t("metadata_pointer_found"), color=COLOR_LOG_YELLOW)
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
                if logger: logger(t("metadata_pointer_not_found"), color=COLOR_LOG_YELLOW)
                nomes_grupos = [""] * len(posicoes)

            pasta_saida = os.path.join(os.path.dirname(arquivo_afs), os.path.splitext(os.path.basename(arquivo_afs))[0])
            os.makedirs(pasta_saida, exist_ok=True)

            contagem_sufixos = defaultdict(int)
            base_nome_afs = os.path.splitext(os.path.basename(arquivo_afs))[0]
            lista_arquivos = []

            for i, (pos, tamanho, grupo) in enumerate(zip(posicoes, tamanhos, nomes_grupos)):
                if tamanho == 0: continue
                f.seek(pos)
                dados = f.read(tamanho)

                if grupo:
                    nome_base = grupo
                    nome_arquivo = nome_base
                    caminho_saida = os.path.join(pasta_saida, nome_arquivo)
                    contador = 1
                    while os.path.exists(caminho_saida):
                        nome_arquivo = f"{nome_base}_{contador}"
                        caminho_saida = os.path.join(pasta_saida, nome_arquivo)
                        contador += 1
                else:
                    contagem_sufixos['__root__'] += 1
                    nome_arquivo = f"{base_nome_afs}_{contagem_sufixos['__root__']:05d}.bin"
                    caminho_saida = os.path.join(pasta_saida, nome_arquivo)

                if logger: logger(t("processing", name=nome_arquivo), color=COLOR_LOG_YELLOW)
                with open(caminho_saida, 'wb') as saida:
                    saida.write(dados)

                lista_arquivos.append(os.path.normpath(nome_arquivo))

            lista_txt = os.path.join(os.path.dirname(arquivo_afs), os.path.splitext(os.path.basename(arquivo_afs))[0]) + ".txt"
            with open(lista_txt, 'w', encoding='utf-8', newline='\n') as arquivo_lista:
                for nome in lista_arquivos:
                    arquivo_lista.write(nome + '\n')

            if logger: logger(t("extraction_completed", count=len(posicoes), path=pasta_saida), color=COLOR_LOG_GREEN)

    except Exception as e:
        if logger: logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

def reconstruir_afs_inplace(afs_original_path):
    try:
        if not afs_original_path: return
        with open(afs_original_path, 'r+b') as f:
            magic = f.read(4)
            if magic != b'AFS\x00':
                if logger: logger(t("invalid_file_magic"), color=COLOR_LOG_RED)
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
            metadata_blob = b""
            if 0 < orig_meta_ptr < file_end:
                f.seek(orig_meta_ptr)
                metadata_blob = f.read()

            base = os.path.splitext(os.path.basename(afs_original_path))[0]
            extracted_dir = os.path.join(os.path.dirname(afs_original_path), base)
            list_txt = os.path.join(os.path.dirname(afs_original_path), base + ".txt")

            if not os.path.isfile(list_txt):
                if logger: logger(t("list_missing", path=list_txt), color=COLOR_LOG_RED)
                return
            if not os.path.isdir(extracted_dir):
                if logger: logger(t("folder_missing", path=extracted_dir), color=COLOR_LOG_RED)
                return

            if logger: logger(t("reading_list", path=list_txt), color=COLOR_LOG_YELLOW)

            lines = None
            for enc in ('utf-8', 'cp1252', 'latin-1'):
                try:
                    with open(list_txt, 'r', encoding=enc) as fh:
                        lines = [ln.strip() for ln in fh.readlines() if ln.strip()]
                    break
                except: continue
            
            if lines is None:
                with open(list_txt, 'r', errors='ignore') as fh:
                    lines = [ln.strip() for ln in fh.readlines() if ln.strip()]

            if len(lines) != data_count:
                if logger: logger(t("list_count_mismatch", lst=len(lines), afs=data_count), color=COLOR_LOG_RED)
                return

            file_paths = []
            for rel in lines:
                candidate = os.path.join(extracted_dir, rel)
                if not os.path.isfile(candidate):
                    alt = os.path.join(extracted_dir, os.path.basename(rel))
                    if os.path.isfile(alt): candidate = alt
                    else:
                        if logger: logger(t("missing_extracted_file", path=candidate), color=COLOR_LOG_RED)
                        return
                file_paths.append(candidate)

            first_data_offset = orig_pos[0]
            f.seek(first_data_offset, os.SEEK_SET)

            new_pos = []
            new_size = []

            for idx, path in enumerate(file_paths, start=1):
                if logger: logger(t("writing_file", i=idx, n=len(file_paths), name=os.path.basename(path)), color=COLOR_LOG_YELLOW)
                start = f.tell()
                with open(path, 'rb') as rf:
                    data = rf.read()
                f.write(data)
                size = len(data)
                pad_to_boundary(f, 2048)
                new_pos.append(start)
                new_size.append(size)

            new_meta_ptr = f.tell()
            if metadata_blob: f.write(metadata_blob)
            if logger: logger(t("metadata_copied", ptr=new_meta_ptr), color=COLOR_LOG_YELLOW)

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
                f.seek(8 + (total_itens * 8), os.SEEK_SET)
                f.write(struct.pack('<I', new_meta_ptr))

            if logger: logger(t("header_updated"), color=COLOR_LOG_YELLOW)
            if logger: logger(t("rebuild_ok", path=afs_original_path), color=COLOR_LOG_GREEN)

    except Exception as e:
        if logger: logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# FLET FILE PICKERS
# ==============================================================================

fp_extract = ft.FilePicker(
    on_result=lambda e: (
        [extrair_afs(f.path) for f in e.files] if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
    )
)

fp_rebuild = ft.FilePicker(
    on_result=lambda e: (
        [reconstruir_afs_inplace(f.path) for f in e.files] if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
    )
)

# ==============================================================================
# REGISTRO DO PLUGIN
# ==============================================================================
def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, get_option, current_lang, host_page
    logger = log_func
    get_option = option_getter
    current_lang = host_language or "pt_BR"
    host_page = page

    # Injeta os componentes invisíveis na tela do Flet
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
                    allowed_extensions=["afs"],
                    allow_multiple=True
                )
            },
            {
                "label": t("rebuild_file"),
                "action": lambda: fp_rebuild.pick_files(
                    allowed_extensions=["afs"],
                    allow_multiple=True
                )
            },
        ]
    }