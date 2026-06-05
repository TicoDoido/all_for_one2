import argparse
import os
import zlib
from dataclasses import dataclass
from pathlib import Path

try:
    import flet as ft
except ImportError:  # Allows command-line use without Flet installed.
    ft = None


PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "PAK - Star Wars Battlefront III",
        "plugin_description": "Extrai arquivos PAK PBCK do Star Wars Battlefront III usando os segmentos .pak.00 e nomes opcionais .pak.str.",
        "extract_file": "Extrair PAK",
        "repack_folder": "Recriar PAK",
        "select_pak_file": "Selecione o arquivo .pak",
        "select_extracted_folder": "Selecione a pasta extraida",
        "cancelled": "Selecao cancelada.",
        "processing": "Processando: {name}",
        "extracting_to": "Extraindo para: {path}",
        "repacking_to": "Recriando em: {path}",
        "metadata": "Arquivos: {files} | Chunks: {chunks} | Endian: {endian}",
        "repack_metadata": "Arquivos: {files} | Novos chunks: {chunks} | Segmentos: {segments}",
        "names_missing": "Arquivo de nomes nao encontrado; usando indice e CRC nos nomes.",
        "progress": "{current}/{total} arquivos extraidos",
        "repack_progress": "{current}/{total} arquivos adicionados",
        "completed": "Extracao concluida: {count} arquivos em {path}",
        "repack_completed": "Repack concluido: {pak}",
        "original_missing": "PAK original nao encontrado: {path}",
        "missing_file": "Arquivo extraido ausente: {path}",
        "error": "Erro: {error}",
    },
    "en_US": {
        "plugin_name": "PAK - Star Wars Battlefront III",
        "plugin_description": "Extracts Star Wars Battlefront III PBCK PAK files using .pak.00 segments and optional .pak.str names.",
        "extract_file": "Extract PAK",
        "repack_folder": "Rebuild PAK",
        "select_pak_file": "Select .pak file",
        "select_extracted_folder": "Select extracted folder",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}",
        "extracting_to": "Extracting to: {path}",
        "repacking_to": "Rebuilding to: {path}",
        "metadata": "Files: {files} | Chunks: {chunks} | Endian: {endian}",
        "repack_metadata": "Files: {files} | New chunks: {chunks} | Segments: {segments}",
        "names_missing": "Name file not found; using index and CRC in output names.",
        "progress": "{current}/{total} files extracted",
        "repack_progress": "{current}/{total} files added",
        "completed": "Extraction completed: {count} files in {path}",
        "repack_completed": "Repack completed: {pak}",
        "original_missing": "Original PAK not found: {path}",
        "missing_file": "Extracted file missing: {path}",
        "error": "Error: {error}",
    },
    "es_ES": {
        "plugin_name": "PAK - Star Wars Battlefront III",
        "plugin_description": "Extrae archivos PAK PBCK de Star Wars Battlefront III usando segmentos .pak.00 y nombres opcionales .pak.str.",
        "extract_file": "Extraer PAK",
        "repack_folder": "Reconstruir PAK",
        "select_pak_file": "Seleccione el archivo .pak",
        "select_extracted_folder": "Seleccione la carpeta extraida",
        "cancelled": "Seleccion cancelada.",
        "processing": "Procesando: {name}",
        "extracting_to": "Extrayendo a: {path}",
        "repacking_to": "Reconstruyendo en: {path}",
        "metadata": "Archivos: {files} | Chunks: {chunks} | Endian: {endian}",
        "repack_metadata": "Archivos: {files} | Nuevos chunks: {chunks} | Segmentos: {segments}",
        "names_missing": "Archivo de nombres no encontrado; usando indice y CRC en los nombres.",
        "progress": "{current}/{total} archivos extraidos",
        "repack_progress": "{current}/{total} archivos agregados",
        "completed": "Extraccion completada: {count} archivos en {path}",
        "repack_completed": "Repack completado: {pak}",
        "original_missing": "PAK original no encontrado: {path}",
        "missing_file": "Archivo extraido ausente: {path}",
        "error": "Error: {error}",
    },
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

CHUNK_SIZE = 0x4000
HEADER_SIZE = 24
ENTRY_SIZE = 20

logger = None
current_lang = "pt_BR"


def t(key, **kwargs):
    text = PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key)
    return text.format(**kwargs)


def _log(message, color=None):
    if logger:
        logger(message, color=color)
    else:
        print(message)


@dataclass
class PakHeader:
    endian: str
    dummy: int
    files: int
    chunks_off: int
    chunks_size: int
    unk1: int
    unk2: int


@dataclass
class PakEntry:
    index: int
    crc: int
    size: int
    zsize: int
    offset: int
    chunk_idx: int
    pak_num: int
    name: str


@dataclass
class RepackResult:
    pak_path: Path
    segment_paths: list
    files: int
    chunks: int


def _read_int(data, offset, size, endian):
    chunk = data[offset:offset + size]
    if len(chunk) != size:
        raise ValueError("Unexpected end of file while reading integer")
    return int.from_bytes(chunk, endian)


def _int_bytes(value, size, endian):
    if value < 0 or value >= (1 << (size * 8)):
        raise ValueError(f"Value does not fit in {size} bytes: {value}")
    return value.to_bytes(size, endian)


def _u24(data, offset, endian):
    raw = data[offset:offset + 3]
    if len(raw) != 3:
        raise ValueError("Unexpected end of file while reading 24-bit integer")
    return int.from_bytes(raw, endian)


def _detect_header(data):
    if len(data) < HEADER_SIZE or data[:4] != b"PBCK":
        raise ValueError("Invalid PAK: expected PBCK magic")

    candidates = []
    for endian in ("big", "little"):
        dummy = _read_int(data, 4, 4, endian)
        files = _read_int(data, 8, 4, endian)
        chunks_off = _read_int(data, 12, 4, endian)
        chunks_size = _read_int(data, 16, 4, endian)
        unk1 = _read_int(data, 20, 2, endian)
        unk2 = _read_int(data, 22, 2, endian)

        table_start = HEADER_SIZE + (files * ENTRY_SIZE)
        if (
            0 < files < 1_000_000
            and table_start <= chunks_off <= len(data)
            and 0 <= chunks_size <= len(data) - chunks_off
        ):
            score = 0
            if chunks_off == table_start:
                score += 2
            if chunks_size:
                score += 1
            candidates.append((score, PakHeader(endian, dummy, files, chunks_off, chunks_size, unk1, unk2)))

    if not candidates:
        raise ValueError("Invalid PAK header: could not determine endian/layout")
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _read_packed_15bit_values(data, count, endian):
    values = []
    bit_pos = 0
    total_bits = len(data) * 8

    for _ in range(count):
        if bit_pos + 15 > total_bits:
            break

        value = 0
        for bit_index in range(15):
            byte_value = data[bit_pos // 8]
            if endian == "big":
                bit = (byte_value >> (7 - (bit_pos % 8))) & 1
                value = (value << 1) | bit
            else:
                bit = (byte_value >> (bit_pos % 8)) & 1
                value |= bit << bit_index
            bit_pos += 1
        values.append(value)

    return values


def _pack_15bit_values(values, endian):
    total_bits = len(values) * 15
    packed = bytearray((total_bits + 7) // 8)
    bit_pos = 0

    for value in values:
        if value < 0 or value >= (1 << 15):
            raise ValueError(f"Chunk size does not fit in 15 bits: {value}")

        if endian == "big":
            bit_indexes = range(14, -1, -1)
        else:
            bit_indexes = range(15)

        for bit_index in bit_indexes:
            bit = (value >> bit_index) & 1
            if endian == "big":
                packed[bit_pos // 8] |= bit << (7 - (bit_pos % 8))
            else:
                packed[bit_pos // 8] |= bit << (bit_pos % 8)
            bit_pos += 1

    return bytes(packed)


def _decode_c_string(data, offset):
    end = data.find(b"\x00", offset)
    if end < 0:
        end = len(data)
    raw = data[offset:end]
    for encoding in ("utf-8", "cp1252", "shift_jis"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore").strip()


def _load_names(pak_path, files, endian):
    str_path = Path(str(pak_path) + ".str")
    if not str_path.is_file():
        return None

    data = str_path.read_bytes()
    offsets_size = files * 4
    if len(data) < offsets_size:
        raise ValueError(f"Invalid STR file: too short ({str_path.name})")

    base_off = offsets_size
    names = []
    for index in range(files):
        rel_off = _read_int(data, index * 4, 4, endian)
        abs_off = base_off + rel_off
        if abs_off < 0 or abs_off >= len(data):
            names.append("")
        else:
            names.append(_decode_c_string(data, abs_off))
    return names


def _safe_relative_path(name, index, crc):
    if not name:
        name = f"{index:05d}_{crc:08X}.bin"

    cleaned = name.replace("\\", "/").strip().lstrip("/")
    parts = []
    invalid_chars = '<>:"|?*'

    for part in cleaned.split("/"):
        if part in ("", ".", ".."):
            continue
        safe_part = "".join("_" if char in invalid_chars or ord(char) < 32 else char for char in part)
        safe_part = safe_part.rstrip(" .")
        if safe_part:
            parts.append(safe_part)

    if not parts:
        parts = [f"{index:05d}_{crc:08X}.bin"]
    return Path(*parts)


def _unique_output_path(output_dir, rel_path, seen):
    target = output_dir / rel_path
    key = os.path.normcase(str(target))
    if key not in seen:
        seen.add(key)
        return target

    parent = rel_path.parent
    stem = rel_path.stem
    suffix = rel_path.suffix
    counter = 1
    while True:
        candidate_rel = parent / f"{stem}_{counter:04d}{suffix}"
        candidate = output_dir / candidate_rel
        key = os.path.normcase(str(candidate))
        if key not in seen:
            seen.add(key)
            return candidate
        counter += 1


class SWBF3Pak:
    def __init__(self, pak_path):
        self.pak_path = Path(pak_path)
        self.data = self.pak_path.read_bytes()
        self.header = _detect_header(self.data)
        self.chunk_sizes = self._read_chunk_sizes()
        self.names = _load_names(self.pak_path, self.header.files, self.header.endian)
        self.entries = self._read_entries()

    def _read_chunk_sizes(self):
        start = self.header.chunks_off
        end = start + self.header.chunks_size
        packed = self.data[start:end]
        count = (self.header.chunks_size * 8) // 15
        return _read_packed_15bit_values(packed, count, self.header.endian)

    def _read_entries(self):
        entries = []
        endian = self.header.endian
        for index in range(self.header.files):
            offset = HEADER_SIZE + (index * ENTRY_SIZE)
            crc = _read_int(self.data, offset, 4, endian)
            size = _read_int(self.data, offset + 4, 4, endian)
            zsize = _read_int(self.data, offset + 8, 4, endian)
            data_offset = _read_int(self.data, offset + 12, 4, endian)
            chunk_idx = _u24(self.data, offset + 16, endian)
            pak_num = self.data[offset + 19]
            name = self.names[index] if self.names and index < len(self.names) else ""
            entries.append(PakEntry(index, crc, size, zsize, data_offset, chunk_idx, pak_num, name))
        return entries


class SegmentPool:
    def __init__(self, pak_path):
        self.pak_path = Path(pak_path)
        self.handles = {}

    def get(self, pak_num):
        if pak_num not in self.handles:
            segment_path = Path(f"{self.pak_path}.{pak_num:02d}")
            if not segment_path.is_file():
                raise FileNotFoundError(f"Segment not found: {segment_path}")
            self.handles[pak_num] = segment_path.open("rb")
        return self.handles[pak_num]

    def close(self):
        for handle in self.handles.values():
            handle.close()
        self.handles.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def _read_exact(handle, offset, size):
    handle.seek(offset)
    data = handle.read(size)
    if len(data) != size:
        raise EOFError(f"Unexpected end of segment at offset 0x{offset:X}")
    return data


def _write_limited(out_file, payload, remaining):
    if remaining <= 0:
        return 0
    chunk = payload[:remaining]
    out_file.write(chunk)
    return len(chunk)


def _extract_entry(entry, out_file, segments, chunk_sizes):
    source = segments.get(entry.pak_num)

    if entry.zsize == 0:
        payload = _read_exact(source, entry.offset, entry.size)
        out_file.write(payload)
        return

    written = 0
    offset = entry.offset
    chunk_idx = entry.chunk_idx

    while written < entry.size:
        if chunk_idx >= len(chunk_sizes):
            raise ValueError(f"Chunk index out of range: {chunk_idx}")

        chunk_zsize = chunk_sizes[chunk_idx]
        remaining = entry.size - written

        if chunk_zsize == CHUNK_SIZE:
            payload = _read_exact(source, offset, CHUNK_SIZE)
            written += _write_limited(out_file, payload, remaining)
            offset += chunk_zsize
        elif chunk_zsize == 0:
            payload = _read_exact(source, offset, CHUNK_SIZE)
            written += _write_limited(out_file, payload, remaining)
        elif chunk_zsize > CHUNK_SIZE:
            zero_size = CHUNK_SIZE - (chunk_zsize - CHUNK_SIZE)
            written += _write_limited(out_file, b"\x00" * zero_size, remaining)
        else:
            payload = _read_exact(source, offset, chunk_zsize)
            decompressed = zlib.decompress(payload)
            written += _write_limited(out_file, decompressed, remaining)
            offset += chunk_zsize

        chunk_idx += 1


def extract_pak(pak_path, output_dir=None, progress=None):
    archive = SWBF3Pak(pak_path)
    pak_path = Path(pak_path)
    output_dir = Path(output_dir) if output_dir else pak_path.parent / pak_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    seen_paths = set()
    with SegmentPool(pak_path) as segments:
        for entry in archive.entries:
            rel_path = _safe_relative_path(entry.name, entry.index, entry.crc)
            target = _unique_output_path(output_dir, rel_path, seen_paths)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as out_file:
                _extract_entry(entry, out_file, segments, archive.chunk_sizes)

            if progress:
                progress(entry.index + 1, len(archive.entries), target)

    return archive, output_dir


def _copy_stream(in_file, out_file):
    total = 0
    while True:
        chunk = in_file.read(1024 * 1024)
        if not chunk:
            break
        out_file.write(chunk)
        total += len(chunk)
    return total


def _write_repacked_compressed_file(source_path, out_segment, chunk_sizes):
    chunk_idx = len(chunk_sizes)
    zsize = 0

    with source_path.open("rb") as in_file:
        while True:
            chunk = in_file.read(CHUNK_SIZE)
            if not chunk:
                break

            compressed = zlib.compress(chunk, 9)
            if len(compressed) < CHUNK_SIZE:
                out_segment.write(compressed)
                chunk_sizes.append(len(compressed))
                zsize += len(compressed)
            else:
                raw_chunk = chunk if len(chunk) == CHUNK_SIZE else chunk.ljust(CHUNK_SIZE, b"\x00")
                out_segment.write(raw_chunk)
                chunk_sizes.append(CHUNK_SIZE)
                zsize += CHUNK_SIZE

    return chunk_idx, zsize


def _build_pak_bytes(archive, entries, chunk_sizes):
    endian = archive.header.endian
    chunk_table = _pack_15bit_values(chunk_sizes, endian)
    chunks_off = HEADER_SIZE + (len(entries) * ENTRY_SIZE)

    data = bytearray()
    data += b"PBCK"
    data += _int_bytes(archive.header.dummy, 4, endian)
    data += _int_bytes(len(entries), 4, endian)
    data += _int_bytes(chunks_off, 4, endian)
    data += _int_bytes(len(chunk_table), 4, endian)
    data += _int_bytes(archive.header.unk1, 2, endian)
    data += _int_bytes(archive.header.unk2, 2, endian)

    for entry in entries:
        data += _int_bytes(entry.crc, 4, endian)
        data += _int_bytes(entry.size, 4, endian)
        data += _int_bytes(entry.zsize, 4, endian)
        data += _int_bytes(entry.offset, 4, endian)
        data += _int_bytes(entry.chunk_idx, 3, endian)
        data += _int_bytes(entry.pak_num, 1, endian)

    data += chunk_table
    return bytes(data)


def _copy_str_file(original_pak, output_pak):
    original_str = Path(str(original_pak) + ".str")
    if not original_str.is_file():
        return None

    output_str = Path(str(output_pak) + ".str")
    output_str.write_bytes(original_str.read_bytes())
    return output_str


def _find_original_pak(extracted_dir):
    extracted_dir = Path(extracted_dir)
    candidate = extracted_dir.with_suffix(".pak")
    if candidate.is_file():
        return candidate
    candidate = extracted_dir.parent / f"{extracted_dir.name}.pak"
    if candidate.is_file():
        return candidate
    return extracted_dir.parent / f"{extracted_dir.name}.pak"


def repack_pak(original_pak, extracted_dir, output_pak=None, progress=None):
    original_pak = Path(original_pak)
    extracted_dir = Path(extracted_dir)
    if not original_pak.is_file():
        raise FileNotFoundError(t("original_missing", path=str(original_pak)))
    if not extracted_dir.is_dir():
        raise FileNotFoundError(str(extracted_dir))

    archive = SWBF3Pak(original_pak)
    output_pak = Path(output_pak) if output_pak else original_pak.with_name(f"{original_pak.stem}_repack{original_pak.suffix}")
    if output_pak.resolve() == original_pak.resolve():
        raise ValueError("Output PAK must be different from the original PAK")
    output_pak.parent.mkdir(parents=True, exist_ok=True)

    chunk_sizes = []
    new_entries = []
    segment_handles = {}
    segment_paths = {}
    seen_paths = set()

    def get_out_segment(pak_num):
        if pak_num not in segment_handles:
            segment_path = Path(f"{output_pak}.{pak_num:02d}")
            segment_path.parent.mkdir(parents=True, exist_ok=True)
            segment_handles[pak_num] = segment_path.open("wb")
            segment_paths[pak_num] = segment_path
        return segment_handles[pak_num]

    try:
        for original_entry in archive.entries:
            rel_path = _safe_relative_path(original_entry.name, original_entry.index, original_entry.crc)
            source_path = _unique_output_path(extracted_dir, rel_path, seen_paths)
            if not source_path.is_file():
                raise FileNotFoundError(t("missing_file", path=str(source_path)))

            pak_num = original_entry.pak_num
            out_segment = get_out_segment(pak_num)
            data_offset = out_segment.tell()
            size = source_path.stat().st_size

            if original_entry.zsize == 0:
                with source_path.open("rb") as in_file:
                    _copy_stream(in_file, out_segment)
                zsize = 0
                chunk_idx = original_entry.chunk_idx
            else:
                chunk_idx, zsize = _write_repacked_compressed_file(source_path, out_segment, chunk_sizes)

            new_entries.append(
                PakEntry(
                    original_entry.index,
                    original_entry.crc,
                    size,
                    zsize,
                    data_offset,
                    chunk_idx,
                    pak_num,
                    original_entry.name,
                )
            )

            if progress:
                progress(original_entry.index + 1, len(archive.entries), source_path)
    finally:
        for handle in segment_handles.values():
            handle.close()

    output_pak.write_bytes(_build_pak_bytes(archive, new_entries, chunk_sizes))
    _copy_str_file(original_pak, output_pak)

    return RepackResult(
        output_pak,
        [segment_paths[key] for key in sorted(segment_paths)],
        len(new_entries),
        len(chunk_sizes),
    )


def _start_extraction(pak_path):
    try:
        pak_path = Path(pak_path)
        _log(t("processing", name=pak_path.name), COLOR_LOG_YELLOW)
        archive = SWBF3Pak(pak_path)
        out_dir = pak_path.parent / pak_path.stem

        _log(t("extracting_to", path=str(out_dir)), COLOR_LOG_YELLOW)
        _log(t("metadata", files=archive.header.files, chunks=len(archive.chunk_sizes), endian=archive.header.endian), COLOR_LOG_YELLOW)
        if archive.names is None:
            _log(t("names_missing"), COLOR_LOG_YELLOW)

        def progress(current, total, target):
            if current == 1 or current == total or current % 100 == 0:
                _log(t("progress", current=current, total=total), COLOR_LOG_YELLOW)

        extract_pak(pak_path, out_dir, progress=progress)
        _log(t("completed", count=len(archive.entries), path=str(out_dir)), COLOR_LOG_GREEN)
    except Exception as exc:
        _log(t("error", error=str(exc)), COLOR_LOG_RED)


def _start_repack(extracted_dir):
    try:
        extracted_dir = Path(extracted_dir)
        original_pak = _find_original_pak(extracted_dir)
        if not original_pak.is_file():
            _log(t("original_missing", path=str(original_pak)), COLOR_LOG_RED)
            return

        output_pak = original_pak.with_name(f"{original_pak.stem}_repack{original_pak.suffix}")
        _log(t("processing", name=extracted_dir.name), COLOR_LOG_YELLOW)
        _log(t("repacking_to", path=str(output_pak)), COLOR_LOG_YELLOW)

        def progress(current, total, target):
            if current == 1 or current == total or current % 100 == 0:
                _log(t("repack_progress", current=current, total=total), COLOR_LOG_YELLOW)

        result = repack_pak(original_pak, extracted_dir, output_pak, progress=progress)
        _log(t("repack_metadata", files=result.files, chunks=result.chunks, segments=len(result.segment_paths)), COLOR_LOG_YELLOW)
        _log(t("repack_completed", pak=str(result.pak_path)), COLOR_LOG_GREEN)
    except Exception as exc:
        _log(t("error", error=str(exc)), COLOR_LOG_RED)


def register_plugin(log_func, option_getter=None, host_language="pt_BR", page=None):
    global logger, current_lang
    logger = log_func
    current_lang = host_language

    if ft is None:
        raise RuntimeError("Flet is required to load this plugin in the GUI")

    def on_result(event):
        if event.files:
            _start_extraction(event.files[0].path)
        else:
            _log(t("cancelled"), COLOR_LOG_YELLOW)

    def on_repack_result(event):
        if event.path:
            _start_repack(event.path)
        else:
            _log(t("cancelled"), COLOR_LOG_YELLOW)

    picker = ft.FilePicker(on_result=on_result)
    repack_picker = ft.FilePicker(on_result=on_repack_result)
    if page is not None:
        page.overlay.append(picker)
        page.overlay.append(repack_picker)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "pickers": [picker, repack_picker],
        "commands": [
            {
                "label": t("extract_file"),
                "action": lambda: picker.pick_files(
                    dialog_title=t("select_pak_file"),
                    allowed_extensions=["pak"],
                ),
            },
            {
                "label": t("repack_folder"),
                "action": lambda: repack_picker.get_directory_path(
                    dialog_title=t("select_extracted_folder"),
                ),
            },
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract or rebuild Star Wars Battlefront III PBCK PAK archives.")
    parser.add_argument("path", help="Path to the .pak file, or extracted folder when using --repack")
    parser.add_argument("-o", "--output", help="Output directory for extraction, or output .pak for --repack.")
    parser.add_argument("--list", action="store_true", help="Only list archive entries")
    parser.add_argument("--repack", action="store_true", help="Rebuild a PAK from an extracted folder")
    parser.add_argument("--original", help="Original .pak used as the repack template. Defaults to <folder>.pak.")
    args = parser.parse_args(argv)

    if args.repack:
        extracted_dir = Path(args.path)
        original_pak = Path(args.original) if args.original else _find_original_pak(extracted_dir)

        def progress(current, total, target):
            if current == 1 or current == total or current % 100 == 0:
                print(f"{current}/{total}: {target}")

        result = repack_pak(original_pak, extracted_dir, args.output, progress=progress)
        print(f"Repacked {result.files} files to {result.pak_path}")
        for segment_path in result.segment_paths:
            print(f"Segment: {segment_path}")
        return 0

    archive = SWBF3Pak(args.path)
    if args.list:
        print(f"files={archive.header.files} chunks={len(archive.chunk_sizes)} endian={archive.header.endian}")
        for entry in archive.entries:
            name = entry.name or f"{entry.index:05d}_{entry.crc:08X}.bin"
            print(
                f"{entry.index:05d} crc={entry.crc:08X} size={entry.size} "
                f"zsize={entry.zsize} pak={entry.pak_num:02d} offset=0x{entry.offset:X} name={name}"
            )
        return 0

    def progress(current, total, target):
        if current == 1 or current == total or current % 100 == 0:
            print(f"{current}/{total}: {target}")

    _, out_dir = extract_pak(args.path, args.output, progress=progress)
    print(f"Extracted {len(archive.entries)} files to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
