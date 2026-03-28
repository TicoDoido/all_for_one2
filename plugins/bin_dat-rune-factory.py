import os
import struct
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "bin/dat Tool - Rune Factory: Frontier",
        "plugin_description": "Extrai e reconstrói arquivos .bin/.dat do jogo Rune Factory: Frontier (Wii)",
        "extract_file": "Extrair arquivos (selecione o .bin)",
        "rebuild_file": "Reconstruir arquivos (selecione o .bin original)",
        "select_bin_file": "Selecione o arquivo .bin",
        "invalid_file_magic": "Arquivo inválido: Magic incorreto (esperado 'NLCM').",
        "file_not_found": "Arquivo não encontrado: {file}",
        "extraction_completed": "Extração concluída! Arquivos salvos em: {path}",
        "rebuild_completed": "Reconstrução concluída! Arquivo gerado: {path}",
        "list_file_not_found": "Arquivo de lista (.txt) não encontrado: {path}",
        "extracted_folder_not_found": "Pasta extraída não encontrada: {folder}",
        "missing_files": "Arquivos faltando na pasta extraída: {files}",
        "file_count_mismatch": "Número de arquivos na lista ({list}) difere do original ({orig}). Abortando.",
        "error": "Erro",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "extracting_to": "Extraindo para: {path}",
        "recreating_to": "Reconstruindo a partir de: {path}",
        "file_extracted": "Arquivo extraído: {name}",
        "file_reinserted": "Arquivo reinserido: {name}",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "bin/dat Tool - Rune Factory: Frontier",
        "plugin_description": "Extracts and rebuilds .bin/.dat files from Rune Factory: Frontier (Wii)",
        "extract_file": "Extract files (select .bin)",
        "rebuild_file": "Rebuild files (select original .bin)",
        "select_bin_file": "Select .bin file",
        "invalid_file_magic": "Invalid file: Incorrect magic (expected 'NLCM').",
        "file_not_found": "File not found: {file}",
        "extraction_completed": "Extraction completed! Files saved in: {path}",
        "rebuild_completed": "Rebuild completed! File generated: {path}",
        "list_file_not_found": "List file (.txt) not found: {path}",
        "extracted_folder_not_found": "Extracted folder not found: {folder}",
        "missing_files": "Missing files in extracted folder: {files}",
        "file_count_mismatch": "Number of files in list ({list}) differs from original ({orig}). Aborting.",
        "error": "Error",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "extracting_to": "Extracting to: {path}",
        "recreating_to": "Rebuilding from: {path}",
        "file_extracted": "File extracted: {name}",
        "file_reinserted": "File reinserted: {name}",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "bin/dat Tool - Rune Factory: Frontier",
        "plugin_description": "Extrae y reconstruye archivos .bin/.dat de Rune Factory: Frontier (Wii)",
        "extract_file": "Extraer archivos (seleccione el .bin)",
        "rebuild_file": "Reconstruir archivos (seleccione el .bin original)",
        "select_bin_file": "Seleccione el archivo .bin",
        "invalid_file_magic": "Archivo inválido: Magic incorrecto (se esperaba 'NLCM').",
        "file_not_found": "Archivo no encontrado: {file}",
        "extraction_completed": "¡Extracción completada! Archivos guardados en: {path}",
        "rebuild_completed": "¡Reconstrucción completada! Archivo generado: {path}",
        "list_file_not_found": "Archivo de lista (.txt) no encontrado: {path}",
        "extracted_folder_not_found": "Carpeta extraída no encontrada: {folder}",
        "missing_files": "Archivos faltantes en la carpeta extraída: {files}",
        "file_count_mismatch": "El número de archivos en la lista ({list}) difiere del original ({orig}). Abortando.",
        "error": "Error",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "extracting_to": "Extrayendo a: {path}",
        "recreating_to": "Reconstruyendo desde: {path}",
        "file_extracted": "Archivo extraído: {name}",
        "file_reinserted": "Archivo reinsertado: {name}",
        "operation_completed": "Operación completada."
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

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
    on_result=lambda e: _extrair_bin(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

fp_rebuild = ft.FilePicker(
    on_result=lambda e: _reconstruir_bin(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# FUNÇÕES PRINCIPAIS
# ==============================================================================

def _extrair_bin(file_path: Path):
    """Extrai arquivos do container .bin/.dat."""
    logger(t("processing", name=file_path.name), color=COLOR_LOG_YELLOW)

    try:
        with open(file_path, "rb") as f:
            magic = f.read(4)
            if magic != b"NLCM":
                logger(t("invalid_file_magic"), color=COLOR_LOG_RED)
                return

            header_size = struct.unpack(">I", f.read(4))[0]
            f.read(4)  # campo ignorado
            file_count = struct.unpack(">I", f.read(4))[0]

            f.seek(header_size)

            # Lê tabela de entradas: cada entrada tem 16 bytes (tamanho, ignorado, offset, ignorado)
            entries = []
            for _ in range(file_count):
                tamanho = struct.unpack(">I", f.read(4))[0]
                f.read(4)  # ignorado
                offset = struct.unpack(">I", f.read(4))[0]
                f.read(4)  # ignorado
                entries.append((tamanho, offset))

        dat_path = file_path.with_suffix(".dat")
        if not dat_path.exists():
            logger(t("file_not_found", file=str(dat_path)), color=COLOR_LOG_RED)
            return

        out_dir = file_path.parent / file_path.stem
        out_dir.mkdir(parents=True, exist_ok=True)

        logger(t("extracting_to", path=str(out_dir)), color=COLOR_LOG_YELLOW)

        extracted_files = []
        with open(dat_path, "rb") as dat:
            for i, (tamanho, offset) in enumerate(entries):
                dat.seek(offset)
                data = dat.read(tamanho)

                # Tenta detectar extensão pelos primeiros bytes
                ext = ".bin"
                if len(data) >= 8:
                    try:
                        sig = data[:8].decode("ascii", errors="ignore").strip()
                        if sig and sig.isprintable():
                            ext = "." + sig
                    except:
                        pass

                filename = f"{i+1:04d}{ext}"
                extracted_files.append(filename)

                out_path = out_dir / filename
                with open(out_path, "wb") as out:
                    out.write(data)

                logger(t("file_extracted", name=filename), color=COLOR_LOG_GREEN)

        # Salva lista de arquivos extraídos (para reconstrução)
        list_path = file_path.parent / (file_path.stem + ".txt")
        with open(list_path, "w", encoding="utf-8") as lst:
            for name in extracted_files:
                lst.write(name + "\n")

        logger(t("extraction_completed", path=str(out_dir)), color=COLOR_LOG_GREEN)

    except FileNotFoundError as e:
        logger(t("file_not_found", file=str(e)), color=COLOR_LOG_RED)
    except Exception as e:
        logger(t("error") + ": " + str(e), color=COLOR_LOG_RED)


def _reconstruir_bin(bin_path: Path):
    """Reconstrói o .bin e .dat a partir da pasta extraída e do arquivo de lista."""
    logger(t("processing", name=bin_path.name), color=COLOR_LOG_YELLOW)

    # Localiza pasta extraída e arquivo de lista
    extracted_dir = bin_path.parent / bin_path.stem
    list_path = bin_path.parent / (bin_path.stem + ".txt")

    if not extracted_dir.is_dir():
        logger(t("extracted_folder_not_found", folder=str(extracted_dir)), color=COLOR_LOG_RED)
        return
    if not list_path.is_file():
        logger(t("list_file_not_found", path=str(list_path)), color=COLOR_LOG_RED)
        return

    # Lê lista de nomes (ordem original)
    with open(list_path, "r", encoding="utf-8") as lst:
        filenames = [ln.strip() for ln in lst if ln.strip()]

    # Lê o arquivo .bin original completo para copiar o cabeçalho
    with open(bin_path, "rb") as f:
        magic = f.read(4)
        if magic != b"NLCM":
            logger(t("invalid_file_magic"), color=COLOR_LOG_RED)
            return
        header_size = struct.unpack(">I", f.read(4))[0]
        unknown1 = f.read(4)
        orig_file_count = struct.unpack(">I", f.read(4))[0]

        # Valida número de arquivos
        if len(filenames) != orig_file_count:
            logger(t("file_count_mismatch", list=len(filenames), orig=orig_file_count), color=COLOR_LOG_RED)
            return

        # Volta ao início e lê todo o cabeçalho (até header_size)
        f.seek(0)
        header_data = bytearray(f.read(header_size))

        # Agora lê os dados restantes (a partir de header_size) para obter a tabela de entradas
        # e o restante do arquivo (se houver). Vamos preservar tudo.
        f.seek(header_size)

    # Verifica se todos os arquivos da lista existem na pasta extraída
    missing = [f for f in filenames if not (extracted_dir / f).is_file()]
    if missing:
        logger(t("missing_files", files=", ".join(missing)), color=COLOR_LOG_RED)
        return

    # Prepara novos dados do .dat e a tabela de entradas
    new_dat = bytearray()
    new_entries = []  # (tamanho, offset)
    ALIGN = 0x800

    for name in filenames:
        file_path = extracted_dir / name
        with open(file_path, "rb") as f:
            data = f.read()
        offset = len(new_dat)
        new_dat.extend(data)
        current_pos = len(new_dat)
        pad = (ALIGN - (current_pos % ALIGN)) % ALIGN
        if pad:
            new_dat.extend(b"\x00" * pad)
        new_entries.append((len(data), offset))

    # Atualiza o cabeçalho copiado: sobrescreve file_count (offset 12)
    struct.pack_into(">I", header_data, 12, len(filenames))

    table_start = header_size
    table_size = len(filenames) * 16

    # Garante que header_data tenha tamanho suficiente
    header_data.extend(b"\x00" * table_size)

    # Escreve a nova tabela
    pos = table_start
    for size, offset in new_entries:
        header_data[pos:pos+4] = struct.pack(">I", size)
        header_data[pos+4:pos+8] = b"\x00\x00\x00\x00"  # campo ignorado
        header_data[pos+8:pos+12] = struct.pack(">I", offset)
        header_data[pos+12:pos+16] = b"\x00\x00\x00\x00"  # campo ignorado
        pos += 16

    # Agora escrevemos o novo .bin
    new_bin_path = bin_path.parent / (bin_path.stem + "_new.bin")
    with open(new_bin_path, "wb") as f:
        f.write(header_data)

    # Cria novo .dat
    new_dat_path = bin_path.parent / (bin_path.stem + "_new.dat")
    with open(new_dat_path, "wb") as f:
        f.write(new_dat)

    logger(t("rebuild_completed", path=str(new_bin_path)), color=COLOR_LOG_GREEN)
    logger(f"Arquivo .dat gerado: {new_dat_path}", color=COLOR_LOG_GREEN)


# ==============================================================================
# AÇÕES DOS COMANDOS
# ==============================================================================

def action_extract():
    fp_extract.pick_files(
        allowed_extensions=["bin"],
        dialog_title=t("select_bin_file")
    )

def action_rebuild():
    fp_rebuild.pick_files(
        allowed_extensions=["bin"],
        dialog_title=t("select_bin_file")
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