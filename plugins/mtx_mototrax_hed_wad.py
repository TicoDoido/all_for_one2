import os
import struct
import traceback
from pathlib import Path

# ==============================================================================
# HED / WAD - MTX Mototrax
# ==============================================================================
#
# HED:
#   4 bytes LE -> offset no WAD
#   4 bytes LE -> tamanho no WAD
#   nome terminado em 0x00
#   padding até múltiplo de 4
#   FF FF FF FF -> fim das entradas
#
# WAD:
#   cada arquivo remontado recebe padding 0x00 até múltiplo de 0x800
#
# ==============================================================================

HED_ALIGNMENT = 4
WAD_ALIGNMENT = 0x800
TERMINATOR = 0xFFFFFFFF
FILENAME_ENCODING = "cp1252"

COLOR_GREEN = "#4ADE80"
COLOR_YELLOW = "#FACC15"
COLOR_RED = "#EF4444"


# ==============================================================================
# TRADUÇÕES DO PLUGIN
# ==============================================================================

STRINGS = {
    "pt_BR": {
        "name": "HED / WAD - MTX Mototrax (PSP)",
        "desc": "Extrai e remonta os containers .HED/.WAD de MTX Mototrax preservando a lista e a ordem do HED original.",
        "btn_unpack": "Extrair HED / WAD",
        "btn_pack": "Remontar HED / WAD",
        "pick_unpack_hed": "Selecione o arquivo HED de MTX Mototrax para extrair",
        "pick_pack_hed": "Selecione o HED ORIGINAL de MTX Mototrax para remontar",
        "pick_source_folder": "Selecione a pasta com os arquivos extraídos/editados",
        "cancelled": "Operação cancelada.",
        "wad_not_found": "Não foi encontrado o arquivo WAD correspondente a '{hed}'.",
        "hed_reading": "Lendo cabeçalho HED: {path}",
        "hed_entries": "{count} entrada(s) encontrada(s) no HED.",
        "wad_opening": "Abrindo WAD: {path}",
        "extract_folder": "Pasta de extração: {path}",
        "extract_start": "Iniciando extração do container...",
        "extract_entry": "[{current}/{total}] Extraído: {file} | Offset: 0x{offset:08X} | Tamanho: 0x{size:08X}",
        "extract_finished": "Extração concluída com sucesso! {count} arquivo(s) extraído(s) para: {path}",
        "default_folder": "Usando automaticamente a pasta extraída: {path}",
        "source_folder": "Pasta usada para remontagem: {path}",
        "rebuild_start": "Iniciando remontagem do container...",
        "checking_files": "Verificando os arquivos exigidos pelo HED original...",
        "missing_files": "Faltam {count} arquivo(s) necessários para remontar o container.",
        "missing_item": "Arquivo ausente: {file}",
        "extra_ignored": "A remontagem usa somente a lista e a ordem do HED original; arquivos extras na pasta são ignorados.",
        "rebuild_entry": "[{current}/{total}] Inserido: {file} | Offset: 0x{offset:08X} | Tamanho: 0x{size:08X} | Padding: 0x{padding:X}",
        "writing_hed": "Gerando o novo HED com offsets e tamanhos recalculados...",
        "new_hed": "Novo HED criado: {path}",
        "new_wad": "Novo WAD criado: {path}",
        "rebuild_finished": "Remontagem concluída com sucesso! {count} arquivo(s) inserido(s).",
        "err_hed_end": "Fim inesperado do HED antes do marcador FF FF FF FF.",
        "err_size_field": "Entrada {index}: HED truncado antes do campo de tamanho.",
        "err_name_null": "Entrada {index}: nome sem terminador nulo.",
        "err_empty_name": "Entrada {index}: nome de arquivo vazio.",
        "err_hed_alignment": "Entrada {index}: o alinhamento ultrapassa o fim do HED.",
        "err_unsafe_path": "Caminho inseguro encontrado no HED: {name}",
        "err_invalid_name": "Nome de arquivo vazio ou inválido encontrado no HED.",
        "err_wad_range": "Entrada {index} ('{file}') ultrapassa o tamanho do WAD: offset 0x{offset:X} + tamanho 0x{size:X}, WAD 0x{wad_size:X}.",
        "err_read_file": "Falha ao ler completamente o arquivo '{file}' do WAD.",
        "err_source_folder": "A pasta dos arquivos para remontagem não foi encontrada: {path}",
        "err_offset_32": "O offset do arquivo '{file}' ultrapassou o limite de 32 bits.",
        "err_size_32": "O tamanho do arquivo '{file}' ultrapassou o limite de 32 bits.",
        "err_generic": "Erro: {err}",
    },

    "en_US": {
        "name": "HED / WAD - MTX Mototrax (PSP)",
        "desc": "Extracts and rebuilds MTX Mototrax .HED/.WAD containers while preserving the original HED file list and order.",
        "btn_unpack": "Extract HED / WAD",
        "btn_pack": "Rebuild HED / WAD",
        "pick_unpack_hed": "Select the MTX Mototrax HED file to extract",
        "pick_pack_hed": "Select the ORIGINAL MTX Mototrax HED file to rebuild",
        "pick_source_folder": "Select the folder containing the extracted/edited files",
        "cancelled": "Operation cancelled.",
        "wad_not_found": "The WAD file corresponding to '{hed}' was not found.",
        "hed_reading": "Reading HED header: {path}",
        "hed_entries": "{count} HED entrie(s) found.",
        "wad_opening": "Opening WAD: {path}",
        "extract_folder": "Extraction folder: {path}",
        "extract_start": "Starting container extraction...",
        "extract_entry": "[{current}/{total}] Extracted: {file} | Offset: 0x{offset:08X} | Size: 0x{size:08X}",
        "extract_finished": "Extraction completed successfully! {count} file(s) extracted to: {path}",
        "default_folder": "Automatically using extracted folder: {path}",
        "source_folder": "Folder used for rebuilding: {path}",
        "rebuild_start": "Starting container rebuild...",
        "checking_files": "Checking files required by the original HED...",
        "missing_files": "{count} file(s) required to rebuild the container are missing.",
        "missing_item": "Missing file: {file}",
        "extra_ignored": "Rebuilding uses only the file list and order from the original HED; extra files in the folder are ignored.",
        "rebuild_entry": "[{current}/{total}] Inserted: {file} | Offset: 0x{offset:08X} | Size: 0x{size:08X} | Padding: 0x{padding:X}",
        "writing_hed": "Generating the new HED with recalculated offsets and sizes...",
        "new_hed": "New HED created: {path}",
        "new_wad": "New WAD created: {path}",
        "rebuild_finished": "Rebuild completed successfully! {count} file(s) inserted.",
        "err_hed_end": "Unexpected end of HED before the FF FF FF FF marker.",
        "err_size_field": "Entry {index}: HED is truncated before the size field.",
        "err_name_null": "Entry {index}: filename has no null terminator.",
        "err_empty_name": "Entry {index}: empty filename.",
        "err_hed_alignment": "Entry {index}: alignment goes beyond the end of the HED.",
        "err_unsafe_path": "Unsafe path found in HED: {name}",
        "err_invalid_name": "Empty or invalid filename found in HED.",
        "err_wad_range": "Entry {index} ('{file}') exceeds WAD size: offset 0x{offset:X} + size 0x{size:X}, WAD 0x{wad_size:X}.",
        "err_read_file": "Failed to completely read '{file}' from the WAD.",
        "err_source_folder": "The folder containing files for rebuilding was not found: {path}",
        "err_offset_32": "The offset for '{file}' exceeds the 32-bit limit.",
        "err_size_32": "The size of '{file}' exceeds the 32-bit limit.",
        "err_generic": "Error: {err}",
    },

    "es_ES": {
        "name": "HED / WAD - MTX Mototrax (PSP)",
        "desc": "Extrae y reconstruye contenedores .HED/.WAD de MTX Mototrax conservando la lista y el orden del HED original.",
        "btn_unpack": "Extraer HED / WAD",
        "btn_pack": "Reconstruir HED / WAD",
        "pick_unpack_hed": "Selecciona el archivo HED de MTX Mototrax para extraer",
        "pick_pack_hed": "Selecciona el HED ORIGINAL de MTX Mototrax para reconstruir",
        "pick_source_folder": "Selecciona la carpeta con los archivos extraídos/editados",
        "cancelled": "Operación cancelada.",
        "wad_not_found": "No se encontró el archivo WAD correspondiente a '{hed}'.",
        "hed_reading": "Leyendo cabecera HED: {path}",
        "hed_entries": "Se encontraron {count} entrada(s) en el HED.",
        "wad_opening": "Abriendo WAD: {path}",
        "extract_folder": "Carpeta de extracción: {path}",
        "extract_start": "Iniciando extracción del contenedor...",
        "extract_entry": "[{current}/{total}] Extraído: {file} | Offset: 0x{offset:08X} | Tamaño: 0x{size:08X}",
        "extract_finished": "¡Extracción completada con éxito! {count} archivo(s) extraído(s) en: {path}",
        "default_folder": "Usando automáticamente la carpeta extraída: {path}",
        "source_folder": "Carpeta usada para la reconstrucción: {path}",
        "rebuild_start": "Iniciando reconstrucción del contenedor...",
        "checking_files": "Comprobando los archivos requeridos por el HED original...",
        "missing_files": "Faltan {count} archivo(s) necesarios para reconstruir el contenedor.",
        "missing_item": "Archivo ausente: {file}",
        "extra_ignored": "La reconstrucción utiliza solamente la lista y el orden del HED original; los archivos adicionales de la carpeta se ignoran.",
        "rebuild_entry": "[{current}/{total}] Insertado: {file} | Offset: 0x{offset:08X} | Tamaño: 0x{size:08X} | Padding: 0x{padding:X}",
        "writing_hed": "Generando el nuevo HED con offsets y tamaños recalculados...",
        "new_hed": "Nuevo HED creado: {path}",
        "new_wad": "Nuevo WAD creado: {path}",
        "rebuild_finished": "¡Reconstrucción completada con éxito! {count} archivo(s) insertado(s).",
        "err_hed_end": "Fin inesperado del HED antes del marcador FF FF FF FF.",
        "err_size_field": "Entrada {index}: el HED está truncado antes del campo de tamaño.",
        "err_name_null": "Entrada {index}: el nombre no tiene terminador nulo.",
        "err_empty_name": "Entrada {index}: nombre de archivo vacío.",
        "err_hed_alignment": "Entrada {index}: la alineación supera el final del HED.",
        "err_unsafe_path": "Ruta insegura encontrada en el HED: {name}",
        "err_invalid_name": "Se encontró un nombre de archivo vacío o inválido en el HED.",
        "err_wad_range": "La entrada {index} ('{file}') supera el tamaño del WAD: offset 0x{offset:X} + tamaño 0x{size:X}, WAD 0x{wad_size:X}.",
        "err_read_file": "No se pudo leer completamente '{file}' desde el WAD.",
        "err_source_folder": "No se encontró la carpeta de archivos para la reconstrucción: {path}",
        "err_offset_32": "El offset del archivo '{file}' supera el límite de 32 bits.",
        "err_size_32": "El tamaño del archivo '{file}' supera el límite de 32 bits.",
        "err_generic": "Error: {err}",
    },
}


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def align_up(value, alignment):
    return (value + alignment - 1) & ~(alignment - 1)


def padding_size(value, alignment):
    return (-value) % alignment


def find_matching_wad(hed_path):
    wanted_stem = hed_path.stem.lower()

    for item in hed_path.parent.iterdir():
        if item.is_file() and item.stem.lower() == wanted_stem and item.suffix.lower() == ".wad":
            return item

    return None


def safe_relative_path(raw_name, t):
    name = raw_name.decode(FILENAME_ENCODING, errors="replace")
    name = name.replace("/", "\\")
    name = name.lstrip("\\")

    parts = []

    for part in name.split("\\"):
        if not part or part == ".":
            continue

        if part == "..":
            raise ValueError(t("err_unsafe_path", name=name))

        parts.append(part)

    if not parts:
        raise ValueError(t("err_invalid_name"))

    return Path(*parts)


def parse_hed(hed_path, t):
    data = hed_path.read_bytes()

    entries = []
    pos = 0
    index = 0

    while True:
        if pos + 4 > len(data):
            raise ValueError(t("err_hed_end"))

        wad_offset = struct.unpack_from("<I", data, pos)[0]

        if wad_offset == TERMINATOR:
            break

        if pos + 8 > len(data):
            raise ValueError(t("err_size_field", index=index))

        size = struct.unpack_from("<I", data, pos + 4)[0]

        name_start = pos + 8
        name_end = data.find(b"\x00", name_start)

        if name_end == -1:
            raise ValueError(t("err_name_null", index=index))

        name_raw = data[name_start:name_end]

        if not name_raw:
            raise ValueError(t("err_empty_name", index=index))

        next_pos = align_up(name_end + 1, HED_ALIGNMENT)

        if next_pos > len(data):
            raise ValueError(t("err_hed_alignment", index=index))

        entries.append({
            "index": index,
            "wad_offset": wad_offset,
            "size": size,
            "name_raw": name_raw,
            "relative_path": safe_relative_path(name_raw, t),
        })

        pos = next_pos
        index += 1

    return entries


# ==============================================================================
# SELETORES
# ==============================================================================

def pick_hed_file(title):
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    try:
        path = filedialog.askopenfilename(
            parent=root,
            title=title,
            filetypes=[
                ("HED", "*.hed *.HED"),
                ("All files", "*.*"),
            ],
        )
        return Path(path) if path else None
    finally:
        root.destroy()


def pick_folder(title, initialdir=None):
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    kwargs = {"parent": root, "title": title}

    if initialdir:
        kwargs["initialdir"] = str(initialdir)

    try:
        path = filedialog.askdirectory(**kwargs)
        return Path(path) if path else None
    finally:
        root.destroy()


# ==============================================================================
# EXTRAÇÃO
# ==============================================================================

def extract_container(hed_path, logger, t):
    hed_path = hed_path.resolve()

    logger(t("hed_reading", path=hed_path))

    entries = parse_hed(hed_path, t)
    logger(t("hed_entries", count=len(entries)))

    wad_path = find_matching_wad(hed_path)

    if wad_path is None:
        raise FileNotFoundError(t("wad_not_found", hed=hed_path.name))

    logger(t("wad_opening", path=wad_path))

    output_dir = hed_path.parent / hed_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    logger(t("extract_folder", path=output_dir))

    wad_size = wad_path.stat().st_size
    total = len(entries)

    with wad_path.open("rb") as wad:
        for current, entry in enumerate(entries, 1):
            offset = entry["wad_offset"]
            size = entry["size"]
            rel_path = entry["relative_path"]

            if offset + size > wad_size:
                raise ValueError(
                    t(
                        "err_wad_range",
                        index=entry["index"],
                        file=str(rel_path),
                        offset=offset,
                        size=size,
                        wad_size=wad_size,
                    )
                )

            output_file = output_dir / rel_path
            output_file.parent.mkdir(parents=True, exist_ok=True)

            wad.seek(offset)
            remaining = size

            with output_file.open("wb") as dst:
                while remaining:
                    chunk = wad.read(min(1024 * 1024, remaining))

                    if not chunk:
                        raise IOError(t("err_read_file", file=str(rel_path)))

                    dst.write(chunk)
                    remaining -= len(chunk)

            logger(
                t(
                    "extract_entry",
                    current=current,
                    total=total,
                    file=str(rel_path),
                    offset=offset,
                    size=size,
                )
            )

    return output_dir, len(entries)


def execute_unpack(logger, get_opt, t):
    try:
        hed_path = pick_hed_file(t("pick_unpack_hed"))

        if not hed_path:
            logger(t("cancelled"), color=COLOR_YELLOW)
            return

        logger(t("extract_start"))

        output_dir, count = extract_container(hed_path, logger, t)

        logger(
            t("extract_finished", count=count, path=output_dir),
            color=COLOR_GREEN,
        )

    except Exception as e:
        logger(t("err_generic", err=str(e)), color=COLOR_RED)
        traceback.print_exc()


# ==============================================================================
# REMONTAGEM
# ==============================================================================

def rebuild_container(original_hed, source_dir, logger, t):
    original_hed = original_hed.resolve()
    source_dir = source_dir.resolve()

    logger(t("hed_reading", path=original_hed))

    entries = parse_hed(original_hed, t)
    logger(t("hed_entries", count=len(entries)))

    if not source_dir.is_dir():
        raise NotADirectoryError(t("err_source_folder", path=source_dir))

    logger(t("checking_files"))

    missing = []

    for entry in entries:
        file_path = source_dir / entry["relative_path"]

        if not file_path.is_file():
            missing.append(entry["relative_path"])

    if missing:
        logger(t("missing_files", count=len(missing)), color=COLOR_RED)

        for rel_path in missing:
            logger(t("missing_item", file=str(rel_path)), color=COLOR_RED)

        raise FileNotFoundError(t("missing_files", count=len(missing)))

    logger(t("extra_ignored"), color=COLOR_YELLOW)

    out_hed = original_hed.parent / (original_hed.stem + "_novo.hed")
    out_wad = original_hed.parent / (original_hed.stem + "_novo.wad")

    tmp_hed = Path(str(out_hed) + ".tmp")
    tmp_wad = Path(str(out_wad) + ".tmp")

    rebuilt_entries = []

    try:
        with tmp_wad.open("wb") as wad:
            total = len(entries)

            for current, entry in enumerate(entries, 1):
                rel_path = entry["relative_path"]
                input_file = source_dir / rel_path

                wad_offset = wad.tell()
                size = input_file.stat().st_size

                if wad_offset > 0xFFFFFFFF:
                    raise OverflowError(t("err_offset_32", file=str(rel_path)))

                if size > 0xFFFFFFFF:
                    raise OverflowError(t("err_size_32", file=str(rel_path)))

                with input_file.open("rb") as src:
                    while True:
                        chunk = src.read(1024 * 1024)

                        if not chunk:
                            break

                        wad.write(chunk)

                pad = padding_size(wad.tell(), WAD_ALIGNMENT)

                if pad:
                    wad.write(b"\x00" * pad)

                rebuilt_entries.append({
                    "wad_offset": wad_offset,
                    "size": size,
                    "name_raw": entry["name_raw"],
                })

                logger(
                    t(
                        "rebuild_entry",
                        current=current,
                        total=total,
                        file=str(rel_path),
                        offset=wad_offset,
                        size=size,
                        padding=pad,
                    )
                )

        logger(t("writing_hed"))

        with tmp_hed.open("wb") as hed:
            for entry in rebuilt_entries:
                hed.write(struct.pack("<I", entry["wad_offset"]))
                hed.write(struct.pack("<I", entry["size"]))

                # Preserva exatamente os bytes do nome do HED original.
                hed.write(entry["name_raw"])
                hed.write(b"\x00")

                pad = padding_size(hed.tell(), HED_ALIGNMENT)

                if pad:
                    hed.write(b"\x00" * pad)

            hed.write(struct.pack("<I", TERMINATOR))

        os.replace(tmp_wad, out_wad)
        os.replace(tmp_hed, out_hed)

    except Exception:
        for tmp in (tmp_hed, tmp_wad):
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass

        raise

    return out_hed, out_wad, len(entries)


def execute_pack(logger, get_opt, t):
    try:
        original_hed = pick_hed_file(t("pick_pack_hed"))

        if not original_hed:
            logger(t("cancelled"), color=COLOR_YELLOW)
            return

        default_folder = original_hed.parent / original_hed.stem

        if default_folder.is_dir():
            source_dir = default_folder
            logger(t("default_folder", path=source_dir))
        else:
            source_dir = pick_folder(
                t("pick_source_folder"),
                original_hed.parent,
            )

            if not source_dir:
                logger(t("cancelled"), color=COLOR_YELLOW)
                return

        logger(t("source_folder", path=source_dir))
        logger(t("rebuild_start"))

        out_hed, out_wad, count = rebuild_container(
            original_hed,
            source_dir,
            logger,
            t,
        )

        logger(t("new_hed", path=out_hed), color=COLOR_GREEN)
        logger(t("new_wad", path=out_wad), color=COLOR_GREEN)
        logger(t("rebuild_finished", count=count), color=COLOR_GREEN)

    except Exception as e:
        logger(t("err_generic", err=str(e)), color=COLOR_RED)
        traceback.print_exc()


# ==============================================================================
# INTEGRAÇÃO COM ALL FOR ONE
# ==============================================================================

def register_plugin(logger, get_opt, language, page=None):
    def t(key, **kwargs):
        txt = STRINGS.get(language, STRINGS["pt_BR"]).get(key, key)
        return txt.format(**kwargs) if kwargs else txt

    return {
        "name": t("name"),
        "description": t("desc"),
        "options": [],
        "commands": [
            {
                "label": t("btn_unpack"),
                "action": lambda: execute_unpack(logger, get_opt, t),
            },
            {
                "label": t("btn_pack"),
                "action": lambda: execute_pack(logger, get_opt, t),
            },
        ],
    }
