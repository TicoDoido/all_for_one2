BMD_MAGIC = b"BMD "
BMD_TXT_VERSION = 2
BMD_RECORD_SIZE_TEXT16 = 16
BMD_RECORD_SIZE_TEXT12 = 12

BMD_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "FILES/TEX/P3TEX/BMD (Eternal Sonata PS3)",
        "plugin_description": "Extrai e recria FILES, texturas NTX3 e textos BMD de Eternal Sonata.",
        "extract_bmd": "Extrair BMD -> TXT",
        "import_bmd": "Recompilar BMD <- TXT",
        "select_bmd_files": "Selecione arquivo(s) .BMD",
        "bmd_extracting": "Extraindo textos BMD: {name}",
        "bmd_detected": "Formato BMD detectado: {variant}",
        "bmd_extracted": "[OK] BMD extraído: {src} -> {dst} ({blocks} blocos / {entries} textos / {encoding})",
        "bmd_rebuilding": "Recompilando BMD: {name}",
        "bmd_rebuilt": "[OK] BMD recompilado: {name} ({size} bytes)",
        "bmd_backup": "Backup original: {path}",
        "bmd_not_text": "BMD {variant} não usa tabela de texto deste plugin. Recursos detectados: {details}",
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
        "bmd_detected": "Detected BMD format: {variant}",
        "bmd_extracted": "[OK] BMD extracted: {src} -> {dst} ({blocks} blocks / {entries} texts / {encoding})",
        "bmd_rebuilding": "Rebuilding BMD: {name}",
        "bmd_rebuilt": "[OK] BMD rebuilt: {name} ({size} bytes)",
        "bmd_backup": "Original backup: {path}",
        "bmd_not_text": "BMD {variant} does not use this plugin's text table. Detected resources: {details}",
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
        "bmd_detected": "Formato BMD detectado: {variant}",
        "bmd_extracted": "[OK] BMD extraído: {src} -> {dst} ({blocks} bloques / {entries} textos / {encoding})",
        "bmd_rebuilding": "Recompilando BMD: {name}",
        "bmd_rebuilt": "[OK] BMD recompilado: {name} ({size} bytes)",
        "bmd_backup": "Copia original: {path}",
        "bmd_not_text": "BMD {variant} no usa la tabla de texto de este plugin. Recursos detectados: {details}",
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


def _parse_bmd_block_header(data: bytes):
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
        raise ValueError("BMD sem tabela de blocos.")
    if block_offsets != sorted(block_offsets) or len(set(block_offsets)) != len(block_offsets):
        raise ValueError("Offsets de blocos BMD não são crescentes/únicos.")
    if block_offsets[0] < pos:
        raise ValueError("Primeiro bloco BMD invade o cabeçalho.")

    return block_offsets, data[pos:block_offsets[0]]


def _try_parse_bmd_text16(data: bytes):
    try:
        block_offsets, header_extra = _parse_bmd_block_header(data)
    except Exception:
        return None

    blocks = []
    for block_index, block_start in enumerate(block_offsets):
        block_end = (
            block_offsets[block_index + 1]
            if block_index + 1 < len(block_offsets)
            else len(data)
        )
        if block_start + 16 > block_end:
            return None

        first_ptr = _bmd_u32(data, block_start + 12)
        delta = first_ptr - block_start
        if first_ptr <= block_start or first_ptr >= block_end:
            return None
        if delta < 4 or (delta - 4) % 16:
            return None

        record_count = (delta - 4) // 16
        table_end = block_start + record_count * 16
        if record_count <= 0 or data[table_end:table_end + 4] != b"\x00" * 4:
            return None

        records = []
        text_intervals = []
        for record_index in range(record_count):
            rec_pos = block_start + record_index * 16
            ptr = _bmd_u32(data, rec_pos + 12)
            if not (table_end + 4 <= ptr < block_end):
                return None
            zero = data.find(b"\x00", ptr, block_end)
            if zero < 0:
                return None
            raw = data[ptr:zero]
            records.append(
                {
                    "meta": data[rec_pos:rec_pos + 12],
                    "value": ptr,
                    "is_text": True,
                    "ptr": ptr,
                    "raw": raw,
                    "end": zero + 1,
                }
            )
            text_intervals.append((ptr, zero + 1, record_index))

        blocks.append(
            {
                "old_start": block_start,
                "old_end": block_end,
                "table_end": table_end,
                "record_size": 16,
                "records": records,
                "texts": sorted(text_intervals),
                "terminator": data[table_end:table_end + 4],
            }
        )

    return {
        "variant": "TEXT16",
        "header_extra": header_extra,
        "blocks": blocks,
    }


def _try_parse_bmd_text12(data: bytes):
    try:
        block_offsets, header_extra = _parse_bmd_block_header(data)
    except Exception:
        return None

    blocks = []
    for block_index, block_start in enumerate(block_offsets):
        block_end = (
            block_offsets[block_index + 1]
            if block_index + 1 < len(block_offsets)
            else len(data)
        )

        record_count = None
        max_records = (block_end - block_start) // 12
        for candidate in range(1, max_records + 1):
            table_end = block_start + candidate * 12
            if data[table_end:table_end + 4] != b"\x00" * 4:
                continue
            if all(
                _bmd_u32(data, block_start + i * 12) == 0xFFFFD8F0
                for i in range(candidate)
            ):
                record_count = candidate
                break

        if record_count is None:
            return None

        table_end = block_start + record_count * 12
        records = []
        text_intervals = []

        for record_index in range(record_count):
            rec_pos = block_start + record_index * 12
            first, rec_type, value = struct.unpack_from(">III", data, rec_pos)
            if first != 0xFFFFD8F0:
                return None

            rec = {
                "meta": data[rec_pos:rec_pos + 8],
                "type": rec_type,
                "value": value,
                "is_text": False,
            }

            if value and table_end + 4 <= value < block_end:
                zero = data.find(b"\x00", value, block_end)
                if zero >= 0:
                    raw = data[value:zero]
                    if raw.startswith(b"<d"):
                        try:
                            raw.decode("cp932", errors="strict")
                            rec.update(
                                {
                                    "is_text": True,
                                    "ptr": value,
                                    "raw": raw,
                                    "end": zero + 1,
                                }
                            )
                            text_intervals.append((value, zero + 1, record_index))
                        except UnicodeDecodeError:
                            pass

            records.append(rec)

        blocks.append(
            {
                "old_start": block_start,
                "old_end": block_end,
                "table_end": table_end,
                "record_size": 12,
                "records": records,
                "texts": sorted(text_intervals),
                "terminator": data[table_end:table_end + 4],
            }
        )

    if not any(block["texts"] for block in blocks):
        return None

    return {
        "variant": "TEXT12",
        "header_extra": header_extra,
        "blocks": blocks,
    }


def _try_detect_bmd_pack(data: bytes):
    if len(data) < 12 or data[:4] != BMD_MAGIC:
        return None
    if _bmd_u32(data, 4) != len(data):
        return None

    count = _bmd_u32(data, 8)
    if count <= 0 or count > 100000:
        return None

    candidates = []
    for table_start in range(0x0C, 0x44, 4):
        table_end = table_start + count * 4
        if table_end > len(data):
            continue

        pointers = [_bmd_u32(data, table_start + i * 4) for i in range(count)]
        nonzero = [p for p in pointers if p]
        if not nonzero:
            continue
        if nonzero != sorted(nonzero) or len(nonzero) != len(set(nonzero)):
            continue
        if nonzero[0] < table_end or nonzero[-1] >= len(data):
            continue

        sample = nonzero[: min(100, len(nonzero))]
        printable = 0
        for ptr in sample:
            tag = data[ptr:ptr + 4]
            if tag == b"\x89PNG" or (
                len(tag) == 4 and all(0x20 <= b < 0x7F for b in tag)
            ):
                printable += 1

        if printable < max(1, int(len(sample) * 0.8)):
            continue

        gap = nonzero[0] - table_end
        candidates.append((printable, -gap, table_start, pointers))

    if not candidates:
        return None

    candidates.sort(reverse=True)
    _, _, table_start, pointers = candidates[0]
    tags = []
    for ptr in pointers:
        if not ptr:
            continue
        tag = data[ptr:ptr + 4]
        if tag == b"\x89PNG":
            name = "PNG"
        else:
            name = tag.decode("ascii", errors="replace")
        tags.append(name)

    tag_counts = {}
    for tag in tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if tags and all(tag == "NOBJ" for tag in tags):
        variant = "PACK_NOBJ"
    else:
        variant = "PACK_RESOURCE"

    details = ", ".join(
        f"{tag}:{count}" for tag, count in
        sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
    )

    return {
        "variant": variant,
        "count": count,
        "table_start": table_start,
        "pointers": pointers,
        "details": details or "desconhecido",
    }


def _detect_bmd_structure(data: bytes):
    parsed = _try_parse_bmd_text16(data)
    if parsed:
        return parsed

    parsed = _try_parse_bmd_text12(data)
    if parsed:
        return parsed

    packed = _try_detect_bmd_pack(data)
    if packed:
        return packed

    raise ValueError("Variante BMD ainda não reconhecida.")


def _detect_bmd_encoding(structure) -> str:
    raw_texts = [
        rec["raw"]
        for block in structure["blocks"]
        for rec in block["records"]
        if rec.get("is_text")
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
    structure = _detect_bmd_structure(data)

    if structure["variant"].startswith("PACK_"):
        raise ValueError(
            bt(
                "bmd_not_text",
                variant=structure["variant"],
                details=structure.get("details", "desconhecido"),
            )
        )

    source_encoding = _detect_bmd_encoding(structure)
    txt_path = bmd_path.with_suffix(bmd_path.suffix + ".txt")

    lines = [
        f"# Eternal Sonata BMD TXT v{BMD_TXT_VERSION}",
        f"# source_file={bmd_path.name}",
        f"# bmd_variant={structure['variant']}",
        f"# source_encoding={source_encoding}",
        f"# output_encoding={source_encoding}",
        "# Edite somente o texto depois da TAB. O texto é uma string JSON UTF-8.",
        "# Os IDs mantêm bloco e índice do registro original.",
    ]

    entry_count = 0
    for block_index, block in enumerate(structure["blocks"]):
        for record_index, record in enumerate(block["records"]):
            if not record.get("is_text"):
                continue
            text = _decode_bmd_text(record["raw"], source_encoding)
            payload = json.dumps(text, ensure_ascii=False)
            lines.append(f"B{block_index:03d}:E{record_index:03d}\t{payload}")
            entry_count += 1

    txt_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    return (
        txt_path,
        len(structure["blocks"]),
        entry_count,
        source_encoding,
        structure["variant"],
    )


def _read_bmd_txt(txt_path: Path):
    source_encoding = None
    output_encoding = None
    variant = None
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
                elif line.startswith("# bmd_variant="):
                    variant = line.split("=", 1)[1].strip()
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

    return source_encoding, output_encoding, variant, entries


def _encode_bmd_entry(
    block_index,
    record_index,
    record,
    translated,
    source_encoding,
    output_encoding,
):
    original_text = _decode_bmd_text(record["raw"], source_encoding)

    if (
        translated == original_text
        and output_encoding.lower() == source_encoding.lower()
    ):
        encoded = record["raw"]
    else:
        try:
            encoded = translated.encode(output_encoding, errors="strict")
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

    return encoded


def _rebuild_bmd_bytes(
    original_data: bytes,
    source_encoding: str,
    output_encoding: str,
    entries,
    expected_variant=None,
):
    structure = _detect_bmd_structure(original_data)
    if structure["variant"].startswith("PACK_"):
        raise ValueError(
            bt(
                "bmd_not_text",
                variant=structure["variant"],
                details=structure.get("details", "desconhecido"),
            )
        )

    if expected_variant and expected_variant != structure["variant"]:
        raise ValueError(
            f"O TXT é {expected_variant}, mas o BMD original é {structure['variant']}."
        )

    expected_keys = {
        (bi, ri)
        for bi, block in enumerate(structure["blocks"])
        for ri, record in enumerate(block["records"])
        if record.get("is_text")
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
        old_block_start = block["old_start"]
        old_block_end = block["old_end"]
        old_payload_start = block["table_end"] + 4

        new_block_start = len(out)
        new_block_offsets.append(new_block_start)

        patch_positions = {}
        for record_index, record in enumerate(block["records"]):
            out += record["meta"]
            patch_positions[record_index] = len(out)
            out += struct.pack(">I", record["value"])

        out += block["terminator"]

        text_new_ptrs = {}
        delta_events = []
        cursor = old_payload_start
        cumulative_delta = 0

        for old_text_start, old_text_end, record_index in block["texts"]:
            if old_text_start < cursor:
                raise ValueError(
                    f"Bloco {block_index}: textos sobrepostos/fora de ordem."
                )

            out += original_data[cursor:old_text_start]

            record = block["records"][record_index]
            translated = entries[(block_index, record_index)]
            encoded = _encode_bmd_entry(
                block_index,
                record_index,
                record,
                translated,
                source_encoding,
                output_encoding,
            )

            text_new_ptrs[record_index] = len(out)
            out += encoded
            out += b"\x00"

            old_length = old_text_end - old_text_start
            new_length = len(encoded) + 1
            cumulative_delta += new_length - old_length
            delta_events.append((old_text_end, cumulative_delta))
            cursor = old_text_end

        out += original_data[cursor:old_block_end]

        def map_old_payload_pointer(old_pointer):
            shift = 0
            for boundary, cumulative in delta_events:
                if old_pointer >= boundary:
                    shift = cumulative
                else:
                    break
            return new_block_start + (old_pointer - old_block_start) + shift

        for record_index, record in enumerate(block["records"]):
            patch_pos = patch_positions[record_index]
            if record.get("is_text"):
                struct.pack_into(
                    ">I",
                    out,
                    patch_pos,
                    text_new_ptrs[record_index],
                )
            else:
                old_value = record["value"]
                if (
                    block["record_size"] == 12
                    and old_value
                    and old_payload_start <= old_value < old_block_end
                ):
                    struct.pack_into(
                        ">I",
                        out,
                        patch_pos,
                        map_old_payload_pointer(old_value),
                    )

    struct.pack_into(">I", out, 4, len(out))

    for index, block_offset in enumerate(new_block_offsets):
        struct.pack_into(
            ">I",
            out,
            block_table_pos + index * 4,
            block_offset,
        )

    rebuilt = bytes(out)
    check = _detect_bmd_structure(rebuilt)
    if check["variant"] != structure["variant"]:
        raise ValueError(
            f"Rebuild mudou a variante BMD de {structure['variant']} para {check['variant']}."
        )

    return rebuilt


def _rebuild_bmd_from_txt(bmd_path: Path):
    txt_path = bmd_path.with_suffix(bmd_path.suffix + ".txt")
    if not txt_path.exists():
        raise FileNotFoundError(
            f"TXT não encontrado: {txt_path.name}. Extraia o BMD antes de recompilar."
        )

    original_data = bmd_path.read_bytes()
    source_encoding, output_encoding, variant, entries = _read_bmd_txt(txt_path)

    rebuilt = _rebuild_bmd_bytes(
        original_data,
        source_encoding,
        output_encoding,
        entries,
        expected_variant=variant,
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
            txt_path, blocks, entries, encoding, variant = _extract_bmd_to_txt(path)
            _log(
                bt("bmd_detected", variant=variant),
                color=COLOR_LOG_YELLOW,
            )
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
            structure = _detect_bmd_structure(path.read_bytes())
            _log(
                bt("bmd_detected", variant=structure["variant"]),
                color=COLOR_LOG_YELLOW,
            )
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
