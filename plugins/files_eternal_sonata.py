import json
import re
import struct
from pathlib import Path
from typing import List
import flet as ft

import __files_eternal_sonata_base as _base


COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

logger = None
get_option = None
current_lang = "pt_BR"
host_page = None

BMD_MAGIC = b"BMD "
BMD_TXT_VERSION = 1
BMD_RECORD_SIZE = 16

BMD_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "FILES/TEX/P3TEX/BMD (Eternal Sonata PS3)",
        "plugin_description": "Extrai e recria FILES, texturas NTX3 e textos BMD de Eternal Sonata.",
        "extract_bmd": "Extrair BMD -> TXT",
        "import_bmd": "Recompilar BMD <- TXT",
        "select_bmd_files": "Selecione arquivo(s) .BMD",
        "bmd_extracting": "Extraindo textos BMD: {name}",
        "bmd_extracted": "[OK] BMD extraído: {src} -> {dst} ({blocks} blocos / {entries} textos / {encoding})",
        "bmd_rebuilding": "Recompilando BMD: {name}",
        "bmd_rebuilt": "[OK] BMD recompilado: {name} ({size} bytes)",
        "bmd_backup": "Backup original: {path}",
        "bmd_error": "[ERRO] BMD {name}: {error}",
        "bmd_done": "Operação BMD concluída.",
        "cancelled": "Seleção cancelada.",
    },
    "en_US": {
        "plugin_name": "FILES/TEX/P3TEX/BMD (Eternal Sonata PS3)",
        "plugin_description": "Extracts and rebuilds FILES, NTX3 textures and BMD text from Eternal Sonata.",
        "extract_bmd": "Extract BMD -> TXT",
        "import_bmd": "Rebuild BMD <- TXT",
        "select_bmd_files": "Select .BMD file(s)",
        "bmd_extracting": "Extracting BMD text: {name}",
        "bmd_extracted": "[OK] BMD extracted: {src} -> {dst} ({blocks} blocks / {entries} texts / {encoding})",
        "bmd_rebuilding": "Rebuilding BMD: {name}",
        "bmd_rebuilt": "[OK] BMD rebuilt: {name} ({size} bytes)",
        "bmd_backup": "Original backup: {path}",
        "bmd_error": "[ERROR] BMD {name}: {error}",
        "bmd_done": "BMD operation completed.",
        "cancelled": "Selection cancelled.",
    },
    "es_ES": {
        "plugin_name": "FILES/TEX/P3TEX/BMD (Eternal Sonata PS3)",
        "plugin_description": "Extrae y recompila FILES, texturas NTX3 y textos BMD de Eternal Sonata.",
        "extract_bmd": "Extraer BMD -> TXT",
        "import_bmd": "Recompilar BMD <- TXT",
        "select_bmd_files": "Seleccione archivo(s) .BMD",
        "bmd_extracting": "Extrayendo textos BMD: {name}",
        "bmd_extracted": "[OK] BMD extraído: {src} -> {dst} ({blocks} bloques / {entries} textos / {encoding})",
        "bmd_rebuilding": "Recompilando BMD: {name}",
        "bmd_rebuilt": "[OK] BMD recompilado: {name} ({size} bytes)",
        "bmd_backup": "Copia original: {path}",
        "bmd_error": "[ERROR] BMD {name}: {error}",
        "bmd_done": "Operación BMD completada.",
        "cancelled": "Selección cancelada.",
    },
}


def bt(key, **kwargs):
    text = BMD_TRANSLATIONS.get(
        current_lang, BMD_TRANSLATIONS["pt_BR"]
    ).get(key, key)
    return text.format(**kwargs) if kwargs else text


def _log(message, color=COLOR_LOG_GREEN):
    if logger:
        logger(message, color=color)
    else:
        print(message)


def _bmd_u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"Leitura u32 fora do arquivo em 0x{offset:X}.")
    return struct.unpack_from(">I", data, offset)[0]


def _parse_bmd_structure(data: bytes):
    if len(data) < 12 or data[:4] != BMD_MAGIC:
        raise ValueError("Magic BMD inválido (esperado 'BMD ').")

    declared_size = _bmd_u32(data, 4)
    if declared_size != len(data):
        raise ValueError(
            f"Tamanho BMD inválido: header=0x{declared_size:X}, arquivo=0x{len(data):X}."
        )

    block_offsets = []
    pos = 8
    while pos + 4 <= len(data):
        off = _bmd_u32(data, pos)
        pos += 4
        if off == 0:
            break
        if off >= len(data):
            raise ValueError(f"Offset de bloco fora do arquivo: 0x{off:X}.")
        block_offsets.append(off)
    else:
        raise ValueError("Tabela de blocos BMD sem terminador 00000000.")

    if not block_offsets:
        raise ValueError("BMD não contém blocos.")
    if block_offsets != sorted(block_offsets) or len(set(block_offsets)) != len(block_offsets):
        raise ValueError("Offsets de blocos BMD não são crescentes/únicos.")
    if block_offsets[0] < pos:
        raise ValueError("Primeiro bloco BMD invade o cabeçalho.")

    header_extra = data[pos:block_offsets[0]]
    blocks = []

    for block_index, block_start in enumerate(block_offsets):
        block_end = (
            block_offsets[block_index + 1]
            if block_index + 1 < len(block_offsets)
            else len(data)
        )
        if block_end <= block_start or block_start + BMD_RECORD_SIZE > block_end:
            raise ValueError(f"Bloco {block_index} possui tamanho inválido.")

        first_ptr = _bmd_u32(data, block_start + 12)
        record_count = None
        delta = first_ptr - block_start

        if (
            first_ptr > block_start
            and first_ptr < block_end
            and delta >= 4
            and (delta - 4) % BMD_RECORD_SIZE == 0
        ):
            candidate = (delta - 4) // BMD_RECORD_SIZE
            terminator_pos = block_start + candidate * BMD_RECORD_SIZE
            if (
                candidate > 0
                and terminator_pos + 4 <= block_end
                and data[terminator_pos:terminator_pos + 4] == b"\x00\x00\x00\x00"
            ):
                record_count = candidate

        if record_count is None:
            candidate = 0
            scan = block_start
            while scan + BMD_RECORD_SIZE <= block_end:
                ptr = _bmd_u32(data, scan + 12)
                valid_ptr = scan + BMD_RECORD_SIZE <= ptr < block_end
                if data[scan:scan + 4] == b"\x00\x00\x00\x00" and not valid_ptr:
                    break
                if not valid_ptr:
                    break
                candidate += 1
                scan += BMD_RECORD_SIZE

            if (
                candidate <= 0
                or scan + 4 > block_end
                or data[scan:scan + 4] != b"\x00\x00\x00\x00"
            ):
                raise ValueError(
                    f"Bloco {block_index}: não foi possível localizar o fim da tabela de registros."
                )
            record_count = candidate

        table_end = block_start + record_count * BMD_RECORD_SIZE
        if data[table_end:table_end + 4] != b"\x00\x00\x00\x00":
            raise ValueError(f"Bloco {block_index}: terminador da tabela ausente.")

        records = []
        for record_index in range(record_count):
            rec_pos = block_start + record_index * BMD_RECORD_SIZE
            ptr = _bmd_u32(data, rec_pos + 12)
            if not (table_end + 4 <= ptr < block_end):
                raise ValueError(
                    f"Bloco {block_index}, registro {record_index}: "
                    f"ponteiro 0x{ptr:X} fora da área de texto."
                )

            zero = data.find(b"\x00", ptr, block_end)
            if zero < 0:
                raise ValueError(
                    f"Bloco {block_index}, registro {record_index}: texto sem terminador NUL."
                )

            records.append(
                {
                    "meta": data[rec_pos:rec_pos + 12],
                    "old_ptr": ptr,
                    "raw": data[ptr:zero],
                    "old_end": zero + 1,
                }
            )

        first_text = min(r["old_ptr"] for r in records)
        table_data_end = table_end + 4
        if first_text < table_data_end:
            raise ValueError(f"Bloco {block_index}: texto sobrepõe a tabela.")

        max_text_end = max(r["old_end"] for r in records)
        blocks.append(
            {
                "records": records,
                "table_terminator": data[table_end:table_end + 4],
                "prefix": data[table_data_end:first_text],
                "trailer": data[max_text_end:block_end],
            }
        )

    return {
        "header_extra": header_extra,
        "blocks": blocks,
    }


def _detect_bmd_encoding(structure) -> str:
    raw_texts = [
        rec["raw"]
        for block in structure["blocks"]
        for rec in block["records"]
    ]

    for encoding in ("cp932", "utf-8", "cp1252"):
        try:
            for raw in raw_texts:
                raw.decode(encoding, errors="strict")
            return encoding
        except UnicodeDecodeError:
            continue

    return "cp932"


def _decode_bmd_text(raw: bytes, encoding: str) -> str:
    try:
        return raw.decode(encoding, errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Texto BMD não pôde ser decodificado como {encoding}: {exc}."
        ) from exc


def _extract_bmd_to_txt(bmd_path: Path):
    data = bmd_path.read_bytes()
    structure = _parse_bmd_structure(data)
    source_encoding = _detect_bmd_encoding(structure)
    txt_path = bmd_path.with_suffix(bmd_path.suffix + ".txt")

    lines = [
        f"# Eternal Sonata BMD TXT v{BMD_TXT_VERSION}",
        f"# source_file={bmd_path.name}",
        f"# source_encoding={source_encoding}",
        f"# output_encoding={source_encoding}",
        "# Edite somente o texto depois da TAB. O texto é uma string JSON UTF-8.",
        "# Para usar outra tabela na recompilação, altere output_encoding.",
    ]

    entry_count = 0
    for block_index, block in enumerate(structure["blocks"]):
        for record_index, record in enumerate(block["records"]):
            text = _decode_bmd_text(record["raw"], source_encoding)
            payload = json.dumps(text, ensure_ascii=False)
            lines.append(f"B{block_index:03d}:E{record_index:03d}\t{payload}")
            entry_count += 1

    txt_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    return txt_path, len(structure["blocks"]), entry_count, source_encoding


def _read_bmd_txt(txt_path: Path):
    source_encoding = None
    output_encoding = None
    entries = {}

    with txt_path.open("r", encoding="utf-8-sig", newline=None) as f:
        for line_no, raw_line in enumerate(f, 1):
            line = raw_line.rstrip("\r\n")
            if not line:
                continue

            if line.startswith("#"):
                if line.startswith("# source_encoding="):
                    source_encoding = line.split("=", 1)[1].strip()
                elif line.startswith("# output_encoding="):
                    output_encoding = line.split("=", 1)[1].strip()
                continue

            if "\t" not in line:
                raise ValueError(
                    f"{txt_path.name}, linha {line_no}: esperado ID<TAB>texto JSON."
                )

            key, payload = line.split("\t", 1)
            match = re.fullmatch(
                r"B(\d+):E(\d+)",
                key.strip(),
                flags=re.IGNORECASE,
            )
            if not match:
                raise ValueError(
                    f"{txt_path.name}, linha {line_no}: ID inválido '{key}'."
                )

            entry_key = (int(match.group(1)), int(match.group(2)))
            if entry_key in entries:
                raise ValueError(
                    f"{txt_path.name}, linha {line_no}: ID duplicado {key}."
                )

            try:
                text = json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{txt_path.name}, linha {line_no}: texto JSON inválido: {exc.msg}."
                ) from exc

            if not isinstance(text, str):
                raise ValueError(
                    f"{txt_path.name}, linha {line_no}: o valor precisa ser uma string JSON."
                )

            entries[entry_key] = text

    if not source_encoding:
        source_encoding = "cp932"
    if not output_encoding:
        output_encoding = source_encoding

    try:
        "".encode(source_encoding)
        "".encode(output_encoding)
    except LookupError as exc:
        raise ValueError(f"Encoding BMD desconhecido: {exc}.") from exc

    return source_encoding, output_encoding, entries


def _rebuild_bmd_bytes(
    original_data: bytes,
    source_encoding: str,
    output_encoding: str,
    entries,
):
    structure = _parse_bmd_structure(original_data)

    expected_keys = {
        (bi, ri)
        for bi, block in enumerate(structure["blocks"])
        for ri, _ in enumerate(block["records"])
    }
    found_keys = set(entries)
    missing = sorted(expected_keys - found_keys)
    extra = sorted(found_keys - expected_keys)

    if missing or extra:
        parts = []
        if missing:
            parts.append(
                "faltando "
                + ", ".join(f"B{b:03d}:E{e:03d}" for b, e in missing[:10])
            )
        if extra:
            parts.append(
                "extras "
                + ", ".join(f"B{b:03d}:E{e:03d}" for b, e in extra[:10])
            )
        raise ValueError(
            "TXT BMD não corresponde ao arquivo original: " + "; ".join(parts)
        )

    out = bytearray()
    out += BMD_MAGIC
    out += b"\x00\x00\x00\x00"

    block_table_pos = len(out)
    out += b"\x00\x00\x00\x00" * len(structure["blocks"])
    out += b"\x00\x00\x00\x00"
    out += structure["header_extra"]

    new_block_offsets = []

    for block_index, block in enumerate(structure["blocks"]):
        new_block_offsets.append(len(out))
        pointer_patch_positions = []
        encoded_texts = []

        for record_index, record in enumerate(block["records"]):
            out += record["meta"]
            pointer_patch_positions.append(len(out))
            out += b"\x00\x00\x00\x00"

            translated = entries[(block_index, record_index)]
            original_text = _decode_bmd_text(
                record["raw"],
                source_encoding,
            )

            if translated == original_text:
                encoded = record["raw"]
            else:
                try:
                    encoded = translated.encode(
                        output_encoding,
                        errors="strict",
                    )
                except UnicodeEncodeError as exc:
                    bad = translated[exc.start:exc.end]
                    raise ValueError(
                        f"B{block_index:03d}:E{record_index:03d}: "
                        f"'{bad}' não pode ser codificado em {output_encoding}. "
                        "Altere '# output_encoding=' no TXT se necessário."
                    ) from exc

            if b"\x00" in encoded:
                raise ValueError(
                    f"B{block_index:03d}:E{record_index:03d}: texto contém byte NUL."
                )

            encoded_texts.append(encoded)

        out += block["table_terminator"]
        out += block["prefix"]

        for record_index, encoded in enumerate(encoded_texts):
            text_ptr = len(out)
            struct.pack_into(
                ">I",
                out,
                pointer_patch_positions[record_index],
                text_ptr,
            )
            out += encoded
            out += b"\x00"

        out += block["trailer"]

    struct.pack_into(">I", out, 4, len(out))

    for index, block_offset in enumerate(new_block_offsets):
        struct.pack_into(
            ">I",
            out,
            block_table_pos + index * 4,
            block_offset,
        )

    _parse_bmd_structure(bytes(out))
    return bytes(out)


def _rebuild_bmd_from_txt(bmd_path: Path):
    txt_path = bmd_path.with_suffix(bmd_path.suffix + ".txt")
    if not txt_path.exists():
        raise FileNotFoundError(
            f"TXT não encontrado: {txt_path.name}. Extraia o BMD antes de recompilar."
        )

    original_data = bmd_path.read_bytes()
    source_encoding, output_encoding, entries = _read_bmd_txt(txt_path)

    rebuilt = _rebuild_bmd_bytes(
        original_data,
        source_encoding,
        output_encoding,
        entries,
    )

    backup_path = bmd_path.with_suffix(bmd_path.suffix + ".bak")
    if not backup_path.exists():
        backup_path.write_bytes(original_data)

    bmd_path.write_bytes(rebuilt)
    return backup_path, len(rebuilt)


def _extract_bmd(file_paths: List[Path]):
    for path in file_paths:
        _log(
            bt("bmd_extracting", name=path.name),
            color=COLOR_LOG_YELLOW,
        )
        try:
            txt_path, blocks, entries, encoding = _extract_bmd_to_txt(path)
            _log(
                bt(
                    "bmd_extracted",
                    src=path.name,
                    dst=txt_path.name,
                    blocks=blocks,
                    entries=entries,
                    encoding=encoding,
                ),
                color=COLOR_LOG_GREEN,
            )
        except Exception as exc:
            _log(
                bt("bmd_error", name=path.name, error=str(exc)),
                color=COLOR_LOG_RED,
            )

    _log(bt("bmd_done"), color=COLOR_LOG_GREEN)


def _import_bmd(file_paths: List[Path]):
    for path in file_paths:
        _log(
            bt("bmd_rebuilding", name=path.name),
            color=COLOR_LOG_YELLOW,
        )
        try:
            backup_path, size = _rebuild_bmd_from_txt(path)
            _log(
                bt("bmd_rebuilt", name=path.name, size=size),
                color=COLOR_LOG_GREEN,
            )
            _log(
                bt("bmd_backup", path=str(backup_path)),
                color=COLOR_LOG_YELLOW,
            )
        except Exception as exc:
            _log(
                bt("bmd_error", name=path.name, error=str(exc)),
                color=COLOR_LOG_RED,
            )

    _log(bt("bmd_done"), color=COLOR_LOG_GREEN)


fp_bmd_extract = ft.FilePicker(
    on_result=lambda e: (
        _extract_bmd([Path(f.path) for f in e.files])
        if e.files
        else _log(bt("cancelled"), color=COLOR_LOG_YELLOW)
    )
)

fp_bmd_import = ft.FilePicker(
    on_result=lambda e: (
        _import_bmd([Path(f.path) for f in e.files])
        if e.files
        else _log(bt("cancelled"), color=COLOR_LOG_YELLOW)
    )
)


def action_extract_bmd():
    fp_bmd_extract.pick_files(
        allowed_extensions=["bmd"],
        allow_multiple=True,
        dialog_title=bt("select_bmd_files"),
    )


def action_import_bmd():
    fp_bmd_import.pick_files(
        allowed_extensions=["bmd"],
        allow_multiple=True,
        dialog_title=bt("select_bmd_files"),
    )


def register_plugin(
    log_func,
    option_getter,
    host_language="pt_BR",
    page=None,
):
    global logger, get_option, current_lang, host_page

    logger = log_func
    get_option = option_getter
    current_lang = host_language
    host_page = page

    data = _base.register_plugin(
        log_func,
        option_getter,
        host_language,
        page,
    )
    data = data() if callable(data) else data

    if not isinstance(data, dict):
        raise TypeError("Plugin base do Eternal Sonata não retornou um dicionário.")

    data["name"] = bt("plugin_name")
    data["description"] = bt("plugin_description")

    commands = data.setdefault("commands", [])
    commands.extend(
        [
            {
                "label": bt("extract_bmd"),
                "action": action_extract_bmd,
            },
            {
                "label": bt("import_bmd"),
                "action": action_import_bmd,
            },
        ]
    )

    if host_page:
        for picker in (fp_bmd_extract, fp_bmd_import):
            if picker not in host_page.overlay:
                host_page.overlay.append(picker)
        host_page.update()

    return data
