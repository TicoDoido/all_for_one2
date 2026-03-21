import os
import struct
import json
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "DAT/HED/DB Eternal Poison (PS2)",
        "plugin_description": "Extrai e reempacota arquivos de containers DAT/HED do Eternal Poison (PS2)",
        "extract_file": "Extrair arquivos .DAT/.HED",
        "rebuild_file": "Reempacotar arquivos .DAT/.HED",
        "extract_db": "Extrair textos .DB",
        "insert_db": "Inserir textos .DB",
        "select_hed_file": "Selecione o arquivo .HED",
        "select_db_file": "Selecione o arquivo .DB ou .TXT",
        "hed_file": "Arquivos HED",
        "all_files": "Todos os arquivos",
        "msg_title_error": "Erro",
        "msg_title_done": "Concluído",
        "msg_done_extract": "Arquivos extraídos em: {folder}",
        "msg_done_repack": "Repack concluído: {dat}\nHED atualizado: {hed}",
        "msg_done_extract_db": "Textos extraídos em: {txt}",
        "msg_done_insert_db": "DB atualizado com sucesso: {db}",
        "log_read_entry": "Entrada {i}: name='{name}' offset={offset} size={size} id={id_hex}",
        "log_skipped": "Entrada {i} ignorada (inválida)",
        "log_extracting": "Extraindo: {name} (offset={offset}, size={size})",
        "log_saved": "Salvo: {path}",
        "log_json_written": "JSON salvo em: {json_path}",
        "log_repacked": "Reinserido: {name} offset={offset} size={size}",
        "warn_missing": "[AVISO] Arquivo não encontrado para reinserção: {name}",
        "log_read_db_entry": "Entrada DB {i}: ID={id_hex} TEXTO='{text}'",
        "err_unexpected": "Erro inesperado: {error}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "file_processed": "Arquivo processado: {path}"
    },
    "en_US": {
        "plugin_name": "DAT/HED/DB Eternal Poison (PS2)",
        "plugin_description": "Extracts and repacks DAT/HED container files from Eternal Poison (PS2)",
        "extract_file": "Extract .DAT/.HED files",
        "rebuild_file": "Repack .DAT/.HED files",
        "extract_db": "Extract .DB texts",
        "insert_db": "Insert .DB texts",
        "select_hed_file": "Select the .HED file",
        "select_db_file": "Select the .DB or .TXT file",
        "hed_file": "HED files",
        "all_files": "All files",
        "msg_title_error": "Error",
        "msg_title_done": "Done",
        "msg_done_extract": "Files extracted to: {folder}",
        "msg_done_repack": "Repack finished: {dat}\nHED updated: {hed}",
        "msg_done_extract_db": "Texts extracted to: {txt}",
        "msg_done_insert_db": "DB successfully updated: {db}",
        "log_read_entry": "Entry {i}: name='{name}' offset={offset} size={size} id={id_hex}",
        "log_skipped": "Entry {i} skipped (invalid)",
        "log_extracting": "Extracting: {name} (offset={offset}, size={size})",
        "log_saved": "Saved: {path}",
        "log_json_written": "JSON saved at: {json_path}",
        "log_repacked": "Reinserted: {name} offset={offset} size={size}",
        "warn_missing": "[WARN] File missing for reinsertion: {name}",
        "log_read_db_entry": "DB Entry {i}: ID={id_hex} TEXT='{text}'",
        "err_unexpected": "Unexpected error: {error}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "file_processed": "File processed: {path}"
    },
    "es_ES": {
        "plugin_name": "DAT/HED/DB Eternal Poison (PS2)",
        "plugin_description": "Extrae y reempaqueta archivos contenedores DAT/HED de Eternal Poison (PS2)",
        "extract_file": "Extraer archivos .DAT/.HED",
        "rebuild_file": "Reempaquetar archivos .DAT/.HED",
        "extract_db": "Extraer textos .DB",
        "insert_db": "Insertar textos .DB",
        "select_hed_file": "Seleccione el archivo .HED",
        "select_db_file": "Seleccione el archivo .DB o .TXT",
        "hed_file": "Archivos HED",
        "all_files": "Todos los archivos",
        "msg_title_error": "Error",
        "msg_title_done": "Completado",
        "msg_done_extract": "Archivos extraídos en: {folder}",
        "msg_done_repack": "Repack completado: {dat}\nHED actualizado: {hed}",
        "msg_done_extract_db": "Textos extraídos en: {txt}",
        "msg_done_insert_db": "DB actualizado con éxito: {db}",
        "log_read_entry": "Entrada {i}: nombre='{name}' offset={offset} tamaño={size} id={id_hex}",
        "log_skipped": "Entrada {i} omitida (inválida)",
        "log_extracting": "Extrayendo: {name} (offset={offset}, tamaño={size})",
        "log_saved": "Guardado: {path}",
        "log_json_written": "JSON guardado en: {json_path}",
        "log_repacked": "Reinsertado: {name} offset={offset} tamaño={size}",
        "warn_missing": "[AVISO] Archivo no encontrado para reinsertar: {name}",
        "log_read_db_entry": "Entrada DB {i}: ID={id_hex} TEXTO='{text}'",
        "err_unexpected": "Error inesperado: {error}",
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

fp_extract_hed = ft.FilePicker(
    on_result=lambda e: _extract_ep(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

fp_rebuild_hed = ft.FilePicker(
    on_result=lambda e: _repack_ep(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

fp_extract_db = ft.FilePicker(
    on_result=lambda e: _extract_db(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# Para inserir DB, precisamos do .db e o .txt associado será inferido
fp_insert_db = ft.FilePicker(
    on_result=lambda e: _insert_db(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# UTILITÁRIOS
# ==============================================================================
def pad_to_boundary_size(n, boundary):
    return (boundary - (n % boundary)) % boundary

# ==============================================================================
# LEITURA DO HED
# ==============================================================================
def read_hed_entries(hed_path: Path):
    entries = []
    try:
        with open(hed_path, "rb") as f:
            f.seek(88)
            i = 0
            while True:
                pos = f.tell()
                data = f.read(44)   # 4 (size) + 4 (offset) + 32 (name) + 4 (id)
                if not data or len(data) < 44:
                    break

                offset, size = struct.unpack("<II", data[:8])  # size then offset (LE)
                raw_name = data[8:40]
                name = raw_name.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
                file_id = data[40:44]
                id_hex = file_id.hex().upper()

                if name == "--DirEnd--" or file_id == b"\x00\x00\x00\x00":
                    logger(t("log_skipped", i=i), color=COLOR_LOG_YELLOW)
                    i += 1
                    continue

                entries.append({
                    "NAME": name,
                    "OFFSET": offset,
                    "SIZE": size,
                    "ID_BIN": file_id,
                    "ID_HEX": id_hex,
                    "HED_POS": pos
                })
                logger(t("log_read_entry", i=i, name=name, offset=offset, size=size, id_hex=id_hex), color=COLOR_LOG_YELLOW)
                i += 1
    except Exception as e:
        logger(t("err_unexpected", error=str(e)), color=COLOR_LOG_RED)
        raise
    return entries

# ==============================================================================
# EXTRAÇÃO DAT/HED
# ==============================================================================
def _extract_ep(hed_path: Path):
    """Extrai arquivos do DAT/HED."""
    logger(t("processing", name=hed_path.name), color=COLOR_LOG_YELLOW)

    if not hed_path.exists():
        logger(t("err_unexpected", error=f"HED not found: {hed_path}"), color=COLOR_LOG_RED)
        return

    dat_path = hed_path.with_suffix(".dat")
    if not dat_path.exists():
        logger(t("err_unexpected", error=f"DAT not found: {dat_path}"), color=COLOR_LOG_RED)
        return

    entries = read_hed_entries(hed_path)
    if not entries:
        logger(t("msg_done_extract", folder=str(hed_path.parent / hed_path.stem)), color=COLOR_LOG_GREEN)
        return

    base_dir = hed_path.parent
    base_name = hed_path.stem
    out_dir = base_dir / base_name
    out_dir.mkdir(parents=True, exist_ok=True)

    logger(t("extracting_to", path=str(out_dir)), color=COLOR_LOG_YELLOW)

    with open(dat_path, "rb") as df:
        for e in entries:
            df.seek(e["OFFSET"])
            data = df.read(e["SIZE"])
            out_path = out_dir / e["NAME"]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as outf:
                outf.write(data)
            logger(t("log_extracting", name=e["NAME"], offset=e["OFFSET"], size=e["SIZE"]), color=COLOR_LOG_YELLOW)
            logger(t("log_saved", path=str(out_path)), color=COLOR_LOG_GREEN)

    logger(t("msg_done_extract", folder=str(out_dir)), color=COLOR_LOG_GREEN)

# ==============================================================================
# REPACK DAT/HED
# ==============================================================================
def _repack_ep(hed_path: Path):
    """Reconstrói o DAT/HED a partir da pasta extraída."""
    logger(t("processing", name=hed_path.name), color=COLOR_LOG_YELLOW)

    entries = read_hed_entries(hed_path)
    if not entries:
        logger(t("msg_done_repack", dat="", hed=str(hed_path)), color=COLOR_LOG_GREEN)
        return

    base_dir = hed_path.parent
    base_name = hed_path.stem
    extracted_folder = base_dir / base_name
    new_dat_path = hed_path.with_suffix(".dat")

    logger(t("recreating_to", path=str(extracted_folder)), color=COLOR_LOG_YELLOW)

    with open(new_dat_path, "wb") as dat_out, open(hed_path, "rb+") as hed_io:
        current_offset = 0
        for e in entries:
            in_path = extracted_folder / e["NAME"]
            if not in_path.exists():
                logger(t("warn_missing", name=e["NAME"]), color=COLOR_LOG_RED)
                continue

            with open(in_path, "rb") as inf:
                data = inf.read()

            dat_out.seek(current_offset)
            dat_out.write(data)

            pad = pad_to_boundary_size(len(data), 0x4000)
            if pad:
                dat_out.write(b"\x00" * pad)

            hed_io.seek(e["HED_POS"])
            hed_io.write(struct.pack("<II", current_offset, len(data)))

            logger(t("log_repacked", name=e["NAME"], offset=current_offset, size=len(data)), color=COLOR_LOG_GREEN)

            current_offset = dat_out.tell()

        dat_out.truncate()

    logger(t("msg_done_repack", dat=str(new_dat_path), hed=str(hed_path)), color=COLOR_LOG_GREEN)

# ==============================================================================
# EXTRAÇÃO DB
# ==============================================================================
def _extract_db(db_path: Path):
    """Extrai textos de um arquivo .db."""
    logger(t("processing", name=db_path.name), color=COLOR_LOG_YELLOW)

    if not db_path.exists():
        logger(t("err_unexpected", error=f"DB not found: {db_path}"), color=COLOR_LOG_RED)
        return

    base_dir = db_path.parent
    base_name = db_path.stem
    out_txt = base_dir / (base_name + ".txt")

    texts = []
    i = 0
    with open(db_path, "rb") as f:
        total_texts_byte = f.read(1)
        total_texts = total_texts_byte[0]
        for i in range(total_texts):
            id_bytes = f.read(4)
            if not id_bytes or len(id_bytes) < 4:
                break
            size_byte = f.read(1)
            if not size_byte:
                break
            size = size_byte[0]
            text_bytes = f.read(size)
            if not text_bytes:
                break
            text = text_bytes.rstrip(b"\x00").decode("ansi", errors="ignore").replace("\n", "[BR]")
            id_hex = id_bytes.hex().upper()
            texts.append(f"{id_hex}:{text}")
            logger(t("log_read_db_entry", i=i, id_hex=id_hex, text=text), color=COLOR_LOG_YELLOW)
            i += 1

    with open(out_txt, "w", encoding="ansi") as out_file:
        out_file.write("\n".join(texts))

    logger(t("msg_done_extract_db", txt=str(out_txt)), color=COLOR_LOG_GREEN)

# ==============================================================================
# INSERÇÃO DB
# ==============================================================================
def _insert_db(db_path: Path):
    """Insere textos de volta no .db a partir do .txt associado."""
    logger(t("processing", name=db_path.name), color=COLOR_LOG_YELLOW)

    txt_path = db_path.with_suffix(".txt")
    if not txt_path.exists():
        logger(t("err_unexpected", error=f"TXT not found: {txt_path}"), color=COLOR_LOG_RED)
        return

    lines = []
    with open(txt_path, "r", encoding="ansi") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                continue
            id_hex, text = line.split(":", 1)
            text_bytes = text.replace("[BR]", "\n").encode("ansi") + b"\x00"
            lines.append((id_hex, text_bytes))

    total_texts = len(lines)

    with open(db_path, "wb") as f:
        f.write(bytes([total_texts]))
        for id_hex, text_bytes in lines[:total_texts]:
            id_bytes_hex = bytes.fromhex(id_hex)
            size = len(text_bytes)
            f.write(id_bytes_hex)
            f.write(bytes([size]))
            f.write(text_bytes)

        f.truncate()

    logger(t("msg_done_insert_db", db=str(db_path)), color=COLOR_LOG_GREEN)

# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================
def action_extract():
    fp_extract_hed.pick_files(
        allowed_extensions=["hed"],
        dialog_title=t("select_hed_file")
    )

def action_rebuild():
    fp_rebuild_hed.pick_files(
        allowed_extensions=["hed"],
        dialog_title=t("select_hed_file")
    )

def action_extract_db():
    fp_extract_db.pick_files(
        allowed_extensions=["db"],
        dialog_title=t("select_db_file")
    )

def action_insert_db():
    fp_insert_db.pick_files(
        allowed_extensions=["db"],
        dialog_title=t("select_db_file")
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
        host_page.overlay.extend([fp_extract_hed, fp_rebuild_hed, fp_extract_db, fp_insert_db])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_file"), "action": action_extract},
            {"label": t("rebuild_file"), "action": action_rebuild},
            {"label": t("extract_db"), "action": action_extract_db},
            {"label": t("insert_db"), "action": action_insert_db}
        ]
    }