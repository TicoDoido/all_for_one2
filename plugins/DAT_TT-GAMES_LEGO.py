# Lógica retirada do Quick BMS feito pelo Aluigi
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
        "plugin_name": "DAT TT Games TOOL",
        "plugin_description": "Extrai e reimporta arquivos .DAT TT Games",
        "extract_file": "Extrair arquivos",
        "reinsert_file": "Reinserir arquivos (selecionar JSON)",
        "select_dat_file": "Selecione o arquivo DAT",
        "select_json_file": "Selecione o JSON",
        "log_extracting": "EXTRAINDO: {filename}",
        "log_parse_error_short": "Arquivo muito curto para conter header válido.",
        "log_info_off_invalid": "INFO_OFF inválido.",
        "log_unsupported_new_format": "Formato novo (CC40TAD) não suportado",
        "log_failed_old_header": "Falha ao ler cabeçalho do formato antigo.",
        "log_entry_invalid": "Entrada #{i} inválida.",
        "log_written_json": "JSON salvo em: {json_path}",
        "log_extracted_folder": "Arquivos extraídos para: {folder}",
        "log_rebuild_started": "Iniciando rebuild a partir do JSON: {json_path}",
        "log_inserting": "Inserindo: {filename} -> {path}",
        "log_rebuild_completed": "Reconstrução finalizada: {out_path}",
        "log_rebuild_updated_json": "JSON atualizado: {json_path}",
        "log_wrote_info_block": "Escreveu bloco INFO modificado no novo DAT (NEW_INFO_OFF={off}).",
        "message_title_error": "Erro",
        "message_title_success": "Sucesso",
        "message_extraction_complete": "Arquivos extraídos para:\n{folder}\nJSON salvo em:\n{json_path}",
        "message_dat_not_found": "Arquivo DAT original não encontrado:\n{path}",
        "message_extracted_folder_missing": "Pasta extraída não encontrada:\n{path}",
        "rebuild_error_title": "Erro durante rebuild",
        "error_json_invalid": "JSON inválido - esperado lista de entradas",
        "error_entry_off_missing": "ENTRY_OFF ausente na entrada INDEX {index}",
        "error_file_not_found": "Arquivo não encontrado: {path}",
        "error_rel_offset_invalid": "Rel offset inválido para ENTRY_OFF {entry_off} (rel={rel})",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "extracting_to": "Extraindo para: {path}",
        "recreating_to": "Reconstruindo a partir de: {path}"
    },
    "en_US": {
        "plugin_name": "DAT TT Games TOOL",
        "plugin_description": "Extracts and reinserts .DAT TT Games files",
        "extract_file": "Extract files",
        "reinsert_file": "Reinsert files (select JSON)",
        "select_dat_file": "Select DAT file",
        "select_json_file": "Select JSON file",
        "log_extracting": "EXTRACTING: {filename}",
        "log_parse_error_short": "File too short to contain valid header.",
        "log_info_off_invalid": "INFO_OFF invalid.",
        "log_unsupported_new_format": "New format (CC40TAD) not supported",
        "log_failed_old_header": "Failed reading old-format header.",
        "log_entry_invalid": "Entry #{i} invalid.",
        "log_written_json": "JSON saved at: {json_path}",
        "log_extracted_folder": "Files extracted to: {folder}",
        "log_rebuild_started": "Starting rebuild from JSON: {json_path}",
        "log_inserting": "Inserting: {filename} -> {path}",
        "log_rebuild_completed": "Rebuild finished: {out_path}",
        "log_rebuild_updated_json": "JSON updated: {json_path}",
        "log_wrote_info_block": "Wrote modified INFO block in new DAT (NEW_INFO_OFF={off}).",
        "message_title_error": "Error",
        "message_title_success": "Success",
        "message_extraction_complete": "Files extracted to:\n{folder}\nJSON saved at:\n{json_path}",
        "message_dat_not_found": "Original DAT file not found:\n{path}",
        "message_extracted_folder_missing": "Extracted folder not found:\n{path}",
        "rebuild_error_title": "Error during rebuild",
        "error_json_invalid": "Invalid JSON - expected list of entries",
        "error_entry_off_missing": "ENTRY_OFF missing in entry INDEX {index}",
        "error_file_not_found": "File not found: {path}",
        "error_rel_offset_invalid": "Invalid relative offset for ENTRY_OFF {entry_off} (rel={rel})",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "extracting_to": "Extracting to: {path}",
        "recreating_to": "Rebuilding from: {path}"
    },
    "es_ES": {
        "plugin_name": "DAT TT Games TOOL",
        "plugin_description": "Extrae y reimporta archivos .DAT TT Games",
        "extract_file": "Extraer archivos",
        "reinsert_file": "Reinsertar archivos (seleccionar JSON)",
        "select_dat_file": "Seleccionar archivo DAT",
        "select_json_file": "Seleccionar JSON",
        "log_extracting": "EXTRAYENDO: {filename}",
        "log_parse_error_short": "Archivo demasiado corto para contener un header válido.",
        "log_info_off_invalid": "INFO_OFF inválido.",
        "log_unsupported_new_format": "Formato nuevo (CC40TAD) no soportado",
        "log_failed_old_header": "Error al leer el header del formato antiguo.",
        "log_entry_invalid": "Entrada #{i} inválida.",
        "log_written_json": "JSON guardado en: {json_path}",
        "log_extracted_folder": "Archivos extraídos en: {folder}",
        "log_rebuild_started": "Iniciando reconstrucción desde JSON: {json_path}",
        "log_inserting": "Insertando: {filename} -> {path}",
        "log_rebuild_completed": "Reconstrucción finalizada: {out_path}",
        "log_rebuild_updated_json": "JSON actualizado: {json_path}",
        "log_wrote_info_block": "Escribió el bloque INFO modificado en el nuevo DAT (NEW_INFO_OFF={off}).",
        "message_title_error": "Error",
        "message_title_success": "Éxito",
        "message_extraction_complete": "Archivos extraídos en:\n{folder}\nJSON guardado en:\n{json_path}",
        "message_dat_not_found": "Archivo DAT original no encontrado:\n{path}",
        "message_extracted_folder_missing": "Carpeta extraída no encontrada:\n{path}",
        "rebuild_error_title": "Error durante reconstrucción",
        "error_json_invalid": "JSON inválido - se esperaba una lista de entradas",
        "error_entry_off_missing": "ENTRY_OFF ausente en la entrada INDEX {index}",
        "error_file_not_found": "Archivo no encontrado: {path}",
        "error_rel_offset_invalid": "Offset relativo inválido para ENTRY_OFF {entry_off} (rel={rel})",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "extracting_to": "Extrayendo a: {path}",
        "recreating_to": "Reconstruyendo desde: {path}"
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
    on_result=lambda e: _extract_dat(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)
fp_reinsert = ft.FilePicker(
    on_result=lambda e: _do_rebuild(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# ==============================================================================
# CÓDIGO PRINCIPAL (LÓGICA ADAPTADA PARA USAR LOGGER)
# ==============================================================================

ALIGN = 0x200  # 512 bytes

def align_up(x, a):
    return (x + (a - 1)) & ~(a - 1)

def parse_old_format_names(data, INFO_OFF, FILES, name_field_size):
    names_offset_table = INFO_OFF + 8 + FILES * 16
    NAMES = struct.unpack_from("<I", data, names_offset_table)[0]
    name_info_offset = names_offset_table + 4
    names_offset = name_info_offset + NAMES * name_field_size
    names_crc_offset = struct.unpack_from("<I", data, names_offset)[0]
    names_offset_current = names_offset + 4
    names_crc_offset += names_offset_current

    temp_array = [""] * 65536
    names_list = [""] * FILES
    name_index = 0

    for i in range(FILES):
        next_val = 1
        name = ""
        full_path = ""
        while next_val > 0:
            next_val = struct.unpack_from("<h", data, name_info_offset)[0]
            prev = struct.unpack_from("<h", data, name_info_offset + 2)[0]
            name_offset = struct.unpack_from("<i", data, name_info_offset + 4)[0]
            if name_field_size == 12:
                _ = struct.unpack_from("<I", data, name_info_offset + 8)[0]
            name_info_offset += name_field_size

            if name_offset > 0:
                real_offset = names_offset_current + name_offset
                name_bytes = bytearray()
                while real_offset < len(data) and data[real_offset] != 0:
                    name_bytes.append(data[real_offset])
                    real_offset += 1
                name = name_bytes.decode('utf-8', errors='ignore')
                if name and ord(name[0]) >= 0xF0:
                    name = ""

            if prev != 0:
                full_path = temp_array[prev]

            temp_array[name_index] = full_path
            if next_val > 0 and name:
                full_path = full_path + name + "\\"
            name_index += 1

        full_name = full_path + name
        names_list[i] = "\\" + full_name.lower()

    return names_list

def _extract_dat(filepath: Path):
    """Extrai arquivos do .dat selecionado."""
    logger(t("processing", name=filepath.name), color=COLOR_LOG_YELLOW)
    
    with open(filepath, "rb") as f:
        data = f.read()

    try:
        INFO_OFF, INFO_SIZE = struct.unpack_from("<II", data, 0)
    except struct.error:
        logger(t("log_parse_error_short"), color=COLOR_LOG_RED)
        return

    if INFO_OFF & 0x80000000:
        INFO_OFF ^= 0xFFFFFFFF
        INFO_OFF <<= 8
        INFO_OFF += 0x100

    try:
        version_type1 = struct.unpack_from("<I", data, INFO_OFF)[0]
    except Exception:
        logger(t("log_info_off_invalid"), color=COLOR_LOG_RED)
        return

    version_str = version_type1.to_bytes(4, 'little').decode('ascii', errors='ignore')
    if version_str in ['4CC.', '.CC4']:
        logger(t("log_unsupported_new_format"), color=COLOR_LOG_RED)
        return

    try:
        format_byte_order = struct.unpack_from("<I", data, INFO_OFF)[0]
        FILES = struct.unpack_from("<I", data, INFO_OFF + 4)[0]
    except Exception:
        logger(t("log_failed_old_header"), color=COLOR_LOG_RED)
        return

    name_field_size = 12 if format_byte_order <= -5 else 8

    files_info = []
    for i in range(FILES):
        entry_off = INFO_OFF + 8 + i * 16
        try:
            OFFSET_raw, ZSIZE, SIZE = struct.unpack_from("<III", data, entry_off)
        except Exception:
            logger(t("log_entry_invalid", i=i), color=COLOR_LOG_RED)
            return
        OFFSET = OFFSET_raw << 8
        PACKED = data[entry_off + 12]
        files_info.append({
            "INDEX": i,
            "ENTRY_OFF": entry_off,
            "OFFSET": OFFSET,
            "ZSIZE": ZSIZE,
            "SIZE": SIZE,
            "PACKED": PACKED
        })

    names_list = parse_old_format_names(data, INFO_OFF, FILES, name_field_size)

    base_dir = filepath.parent
    dat_name = filepath.stem
    extracted_folder = base_dir / f"{dat_name}_extracted"
    extracted_folder.mkdir(parents=True, exist_ok=True)

    json_path = base_dir / f"{dat_name}.json"

    logger(t("extracting_to", path=str(extracted_folder)), color=COLOR_LOG_YELLOW)

    extracted_data = []
    for i, entry in enumerate(files_info):
        filename = names_list[i].lstrip("\\").replace("\\", os.sep).upper()
        logger(t("log_extracting", filename=filename), color=COLOR_LOG_YELLOW)
        file_data = data[entry['OFFSET']:entry['OFFSET'] + entry['ZSIZE']]
        out_path = extracted_folder / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f_out:
            f_out.write(file_data)

        extracted_data.append({
            "INDEX": entry["INDEX"],
            "ENTRY_OFF": entry["ENTRY_OFF"],
            "OFFSET": entry["OFFSET"],
            "ZSIZE": entry["ZSIZE"],
            "SIZE": entry["SIZE"],
            "PACKED": entry["PACKED"],
            "FILENAME": filename
        })

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(extracted_data, jf, indent=4, ensure_ascii=False)

    logger(t("log_extracted_folder", folder=str(extracted_folder)), color=COLOR_LOG_GREEN)
    logger(t("log_written_json", json_path=str(json_path)), color=COLOR_LOG_GREEN)


def rebuild_dat(original_dat_name, extracted_folder, json_path, out_path):
    FILE_TYPE = 0
    with open(original_dat_name, "rb") as ori_dat:
        ORIGINAL_HEADER = ori_dat.read(512)
        ori_dat.seek(0)
        OLD_INFO_OFF, OLD_INFO_SIZE = struct.unpack("<II", ori_dat.read(8))
        if OLD_INFO_OFF & 0x80000000:
            OLD_INFO_OFF ^= 0xFFFFFFFF
            OLD_INFO_OFF <<= 8
            OLD_INFO_OFF += 0x100
            FILE_TYPE = 1
        ori_dat.seek(OLD_INFO_OFF)
        ORIGINAL_FILE_INFO = ori_dat.read(OLD_INFO_SIZE)

    with open(json_path, "r", encoding="utf-8") as jf:
        file_entries = json.load(jf)

    if not isinstance(file_entries, list):
        raise ValueError(t("error_json_invalid"))

    file_entries.sort(key=lambda x: x["OFFSET"])

    info_bytes = bytearray(ORIGINAL_FILE_INFO)

    with open(out_path, "wb") as f:
        f.write(ORIGINAL_HEADER)
        if FILE_TYPE == 1:
            f.seek(2048)

        for i, entry in enumerate(file_entries):
            in_file = extracted_folder / entry["FILENAME"]
            logger(t("log_inserting", filename=entry["FILENAME"], path=str(in_file)), color=COLOR_LOG_YELLOW)

            if not in_file.exists():
                raise FileNotFoundError(t("error_file_not_found", path=str(in_file)))

            with open(in_file, "rb") as fin:
                data = fin.read()

            if data.startswith(b"LZ2K"):
                entry["PACKED"] = 2
                entry["ZSIZE"] = len(data)
            else:
                entry["PACKED"] = 0
                entry["SIZE"] = len(data)
                entry["ZSIZE"] = len(data)

            offset_now = f.tell()
            entry["OFFSET"] = offset_now
            f.write(data)

            current_align = 0x800 if FILE_TYPE == 1 else 0x200
            if i < len(file_entries) - 1:
                pad = (current_align - (f.tell() % current_align)) % current_align
                if pad:
                    f.write(b"\x00" * pad)
            else:
                ALIGN = 0x800
                pad = (ALIGN - (f.tell() % ALIGN)) % ALIGN
                if pad:
                    f.write(b"\x00" * pad)

            entry_off_abs = entry.get("ENTRY_OFF")
            if entry_off_abs is None:
                raise ValueError(t("error_entry_off_missing", index=entry.get("INDEX")))

            rel = entry_off_abs - OLD_INFO_OFF
            if rel < 0 or rel + 16 > len(info_bytes):
                raise IndexError(t("error_rel_offset_invalid", entry_off=entry_off_abs, rel=rel))

            OFFSET_raw = entry["OFFSET"] >> 8
            ZSIZE = entry["ZSIZE"]
            SIZE = entry["SIZE"]
            PACKED = entry["PACKED"] & 0xFF

            info_bytes[rel:rel+12] = struct.pack("<III", OFFSET_raw, ZSIZE, SIZE)
            info_bytes[rel+12] = PACKED

        NEW_INFO_OFF = f.tell()
        f.write(info_bytes)
        NEW_INFO_SIZE = len(info_bytes)

        f.seek(0)
        if FILE_TYPE == 1:
            NEW_INFO_OFF = NEW_INFO_OFF - 0x100
            NEW_INFO_OFF >>= 8
            NEW_INFO_OFF = NEW_INFO_OFF ^ 0xFFFFFFFF
            f.write(struct.pack("<II", NEW_INFO_OFF, NEW_INFO_SIZE))
        else:
            f.write(struct.pack("<II", NEW_INFO_OFF, NEW_INFO_SIZE))
            f.seek(132)
            f.write(struct.pack("<I", NEW_INFO_OFF))

    logger(t("log_wrote_info_block", off=NEW_INFO_OFF), color=COLOR_LOG_GREEN)

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(file_entries, jf, indent=4, ensure_ascii=False)


def _do_rebuild(json_path: Path):
    """Reconstrói o .dat a partir do JSON selecionado."""
    logger(t("processing", name=json_path.name), color=COLOR_LOG_YELLOW)

    base_dir = json_path.parent
    dat_name = json_path.stem
    original_dat_name = base_dir / f"{dat_name}.dat"
    extracted_folder = base_dir / f"{dat_name}_extracted"
    out_path = base_dir / f"{dat_name}_rebuild.dat"

    if not original_dat_name.exists():
        logger(t("message_dat_not_found", path=str(original_dat_name)), color=COLOR_LOG_RED)
        return
    if not extracted_folder.is_dir():
        logger(t("message_extracted_folder_missing", path=str(extracted_folder)), color=COLOR_LOG_RED)
        return

    logger(t("log_rebuild_started", json_path=str(json_path)), color=COLOR_LOG_YELLOW)
    logger(t("recreating_to", path=str(extracted_folder)), color=COLOR_LOG_YELLOW)

    try:
        rebuild_dat(original_dat_name, extracted_folder, json_path, out_path)
        logger(t("log_rebuild_completed", out_path=str(out_path)), color=COLOR_LOG_GREEN)
        logger(t("log_rebuild_updated_json", json_path=str(json_path)), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("rebuild_error_title") + ": " + str(e), color=COLOR_LOG_RED)


# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================

def action_extract():
    fp_extract.pick_files(
        allowed_extensions=["dat"],
        dialog_title=t("select_dat_file")
    )

def action_reinsert():
    fp_reinsert.pick_files(
        allowed_extensions=["json"],
        dialog_title=t("select_json_file")
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
            {"label": t("extract_file"), "action": action_extract},
            {"label": t("reinsert_file"), "action": action_reinsert},
        ]
    }