import os
import re
import struct
import zlib
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "EBM-GZ - Atelier Ryza 3",
        "plugin_description": "Extrai e importa textos de arquivos EBM (Atelier Ryza 3)",
        "extract_text": "Extrair texto",
        "import_text": "Importar texto",
        "extract_gz": "Extrair .gz",
        "compress_gz": "Compactar .gz",
        "select_ebm_files": "Selecione os arquivos .ebm",
        "select_txt_files": "Selecione os arquivos .txt",
        "select_gz_files": "Selecione os arquivos .gz",
        "select_compress_files": "Selecione os arquivos para compactar",
        "ebm_files": "Arquivos EBM",
        "text_files": "Arquivos de Texto",
        "gz_files": "Arquivos GZ",
        "all_files": "Todos os arquivos",
        "extraction_completed": "Extração concluída! {count} eventos extraídos para: {path}",
        "import_completed": "Importação concluída! {replaced} eventos importados. Salvo em: {path}",
        "gz_extraction_completed": "Descompressão concluída! Arquivo salvo em: {path}",
        "gz_compression_completed": "Compressão concluída! Arquivo salvo em: {path}",
        "ebm_not_found": "Arquivo EBM correspondente não encontrado: {path}",
        "invalid_ebm_file": "Arquivo EBM inválido: {path}",
        "negative_payload": "Comprimento de payload negativo encontrado",
        "invalid_event_type": "Tipo de evento inválido",
        "header_too_small": "Cabeçalho muito pequeno para escrever comprimento",
        "buffer_too_small": "Buffer muito pequeno para escrever evento",
        "unexpected_error": "Erro inesperado: {error}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "processing_file": "Processando arquivo {current}/{total}: {name}",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "EBM-GZ - Atelier Ryza 3",
        "plugin_description": "Extracts and imports texts from EBM files (Atelier Ryza 3)",
        "extract_text": "Extract text",
        "import_text": "Import text",
        "extract_gz": "Extract .gz",
        "compress_gz": "Compress .gz",
        "select_ebm_files": "Select .ebm files",
        "select_txt_files": "Select .txt files",
        "select_gz_files": "Select .gz files",
        "select_compress_files": "Select files to compress",
        "ebm_files": "EBM Files",
        "text_files": "Text Files",
        "gz_files": "GZ Files",
        "all_files": "All files",
        "extraction_completed": "Extraction completed! {count} events extracted to: {path}",
        "import_completed": "Import completed! {replaced} events imported. Saved to: {path}",
        "gz_extraction_completed": "Decompression completed! File saved to: {path}",
        "gz_compression_completed": "Compression completed! File saved to: {path}",
        "ebm_not_found": "Corresponding EBM file not found: {path}",
        "invalid_ebm_file": "Invalid EBM file: {path}",
        "negative_payload": "Negative payload length encountered",
        "invalid_event_type": "Invalid event type",
        "header_too_small": "Header too small to write length",
        "buffer_too_small": "Buffer too small to write event",
        "unexpected_error": "Unexpected error: {error}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "processing_file": "Processing file {current}/{total}: {name}",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "EBM-GZ - Atelier Ryza 3",
        "plugin_description": "Extrae e importa textos de archivos EBM (Atelier Ryza 3)",
        "extract_text": "Extraer texto",
        "import_text": "Importar texto",
        "extract_gz": "Extraer .gz",
        "compress_gz": "Comprimir .gz",
        "select_ebm_files": "Seleccionar archivos .ebm",
        "select_txt_files": "Seleccionar archivos .txt",
        "select_gz_files": "Seleccionar archivos .gz",
        "select_compress_files": "Seleccionar archivos para comprimir",
        "ebm_files": "Archivos EBM",
        "text_files": "Archivos de Texto",
        "gz_files": "Archivos GZ",
        "all_files": "Todos los archivos",
        "extraction_completed": "¡Extracción completada! {count} eventos extraídos a: {path}",
        "import_completed": "¡Importación completada! {replaced} eventos importados. Guardado en: {path}",
        "gz_extraction_completed": "¡Descompresión completada! Archivo guardado en: {path}",
        "gz_compression_completed": "¡Compresión completada! Archivo guardado en: {path}",
        "ebm_not_found": "Archivo EBM correspondiente no encontrado: {path}",
        "invalid_ebm_file": "Archivo EBM inválido: {path}",
        "negative_payload": "Longitud de carga útil negativa encontrada",
        "invalid_event_type": "Tipo de evento inválido",
        "header_too_small": "Encabezado demasiado pequeño para escribir longitud",
        "buffer_too_small": "Buffer demasiado pequeño para escribir evento",
        "unexpected_error": "Error inesperado: {error}",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "processing_file": "Procesando archivo {current}/{total}: {name}",
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
# FilePickers globais (todos suportam múltiplos arquivos)
# ==============================================================================

fp_extract_ebm = ft.FilePicker(
    on_result=lambda e: _extract_text([Path(f.path) for f in e.files]) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW),

)

fp_import_txt = ft.FilePicker(
    on_result=lambda e: _import_text([Path(f.path) for f in e.files]) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW),

)

fp_extract_gz = ft.FilePicker(
    on_result=lambda e: _extract_gz([Path(f.path) for f in e.files]) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW),

)

fp_compress_gz = ft.FilePicker(
    on_result=lambda e: _compress_gz([Path(f.path) for f in e.files]) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW),

)

# ==============================================================================
# CLASSES ORIGINAIS (MANTIDAS INTACTAS)
# ==============================================================================

class Reader:
    def __init__(self, buffer: bytes):
        self._buffer = buffer
        self._cursor = 0

    @property
    def length(self) -> int:
        return len(self._buffer) - self._cursor

    @property
    def buffer(self) -> bytes:
        return self._buffer

    @property
    def cursor(self) -> int:
        return self._cursor

    def peek(self, start: int, end: int) -> Optional[bytes]:
        if start > end:
            return None
        if end > len(self._buffer):
            raise EOFError("Peek range extends past buffer end")
        return self._buffer[start:end]

    def consume(self, n: int) -> bytes:
        if self._cursor + n > len(self._buffer):
            raise EOFError("Attempt to consume past end of buffer")
        out = self._buffer[self._cursor:self._cursor + n]
        self._cursor += n
        return out

    def remaining(self) -> bytes:
        return self._buffer[self._cursor:]

class Event:
    def __init__(self, header: bytes, data: bytes, footer: bytes):
        self._header = bytearray(header)
        self._data = bytearray(data)
        self._footer = bytearray(footer)

    @property
    def header(self) -> bytes:
        return bytes(self._header)

    @property
    def data(self) -> str:
        try:
            s = bytes(self._data).decode('utf-8', errors='replace')
        except Exception:
            s = bytes(self._data).decode('latin1', errors='replace')
        return s.rstrip('\x00')

    @property
    def footer(self) -> bytes:
        return bytes(self._footer)

    @property
    def length(self) -> int:
        if len(self._header) < 64:
            data_length = 0
        else:
            raw = bytes(self._header[60:64])
            data_length = int.from_bytes(raw, byteorder='little', signed=True)
        return len(self._header) + data_length + len(self._footer)

    def writeEventText(self, text: str) -> None:
        encoded = text.encode('utf-8')
        length = len(encoded) + 1
        if len(self._header) < 4:
            raise ValueError(t("header_too_small"))
        pos = len(self._header) - 4
        self._header[pos:pos + 4] = (length).to_bytes(4, byteorder='little', signed=True)
        new_payload = bytearray(length)
        new_payload[0:len(encoded)] = encoded
        self._data = new_payload

    def write(self, dest: bytearray, offset: int = 0) -> None:
        total = bytes(self._header) + bytes(self._data) + bytes(self._footer)
        end = offset + len(total)
        if end > len(dest):
            raise ValueError(t("buffer_too_small"))
        dest[offset:end] = total

    def clone(self) -> "Event":
        return Event(bytes(self._header), bytes(self._data), bytes(self._footer))

class EBM:
    EVENT_MESSAGE_TYPE = bytes([0x02, 0x00, 0x00, 0x00])
    EVENT_NOTIFICATION_TYPE = bytes([0x03, 0x00, 0x00, 0x00])

    def __init__(self, path: str):
        p = Path(path).expanduser().resolve()
        if not p.exists() or not p.is_file():
            raise ValueError(t("invalid_ebm_file", path=path))
        raw = p.read_bytes()
        self._reader = Reader(raw)
        first4 = self._reader.consume(4)
        self._length = abs(int.from_bytes(first4, byteorder='little', signed=True))
        self._events: List[Event] = []
        self._path = str(p)

    @property
    def events(self) -> List[Event]:
        return self._events

    @property
    def path(self) -> str:
        return self._path

    def readEvent(self) -> None:
        start = self._reader.cursor
        type_bytes = self._reader.peek(start, start + 4)
        if type_bytes is None or (type_bytes != EBM.EVENT_MESSAGE_TYPE and type_bytes != EBM.EVENT_NOTIFICATION_TYPE):
            raise ValueError(t("invalid_event_type"))
        header = self._reader.consume(60)
        length_bytes = self._reader.consume(4)
        payload_length = int.from_bytes(length_bytes, byteorder='little', signed=True)
        if payload_length < 0:
            raise ValueError(t("negative_payload"))
        payload = self._reader.consume(payload_length)
        trailer = self._reader.consume(8)
        header_and_length = header + length_bytes
        self._events.append(Event(header_and_length, payload, trailer))

    def read(self) -> None:
        if not self._length:
            raise ValueError(t("invalid_ebm_file", path=self._path))
        for _ in range(self._length):
            self.readEvent()

    def save(self, path: str) -> None:
        rest_of_bytes = self._reader.remaining()
        events_length = sum(event.length for event in self._events)
        buf = bytearray(4 + events_length + len(rest_of_bytes))
        buf[0:4] = int(self._length).to_bytes(4, byteorder='little', signed=True)
        offset = 4
        for event in self._events:
            event.write(buf, offset)
            offset += event.length
        buf[offset:offset + len(rest_of_bytes)] = rest_of_bytes
        Path(path).write_bytes(bytes(buf))

def event_type_label(event: Event) -> str:
    h = event.header
    if len(h) >= 4:
        t = h[0:4]
        if t == EBM.EVENT_MESSAGE_TYPE:
            return "message"
        if t == EBM.EVENT_NOTIFICATION_TYPE:
            return "notification"
    return "unknown"

def build_txt_from_ebm(ebm: EBM) -> str:
    parts: List[str] = []
    for idx, ev in enumerate(ebm.events):
        parts.append(f"### EVENT {idx:04d} [{event_type_label(ev)}]\n")
        parts.append(ev.data.rstrip("\n"))
        parts.append("\n\n")
    return "".join(parts).rstrip() + "\n"

def parse_txt_to_event_texts(txt: str) -> Dict[int, str]:
    pattern = re.compile(r"^### EVENT (?P<idx>\d{4}) \[(?P<type>.*?)\]\s*$", flags=re.M)
    matches = list(pattern.finditer(txt))
    result: Dict[int, str] = {}
    if not matches:
        result[0] = txt.rstrip("\n")
        return result

    for i, m in enumerate(matches):
        idx = int(m.group("idx"))
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(txt)
        content = txt[start:end].lstrip("\n").rstrip("\n")
        result[idx] = content
    return result

# ==============================================================================
# FUNÇÕES DE PROCESSAMENTO (ADAPTADAS PARA RECEBER LISTA DE PATHS)
# ==============================================================================

def _extract_text(file_paths: List[Path]):
    """Extrai textos de arquivos .ebm."""
    total = len(file_paths)
    for idx, filepath in enumerate(file_paths, 1):
        logger(t("processing_file", current=idx, total=total, name=filepath.name), color=COLOR_LOG_YELLOW)
        try:
            ebm = EBM(str(filepath))
            ebm.read()
            content = build_txt_from_ebm(ebm)
            out_txt = filepath.with_suffix(".txt")
            out_txt.write_text(content, encoding="utf-8")
            logger(t("extraction_completed", count=len(ebm.events), path=str(out_txt)), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

def _import_text(file_paths: List[Path]):
    """Importa textos de .txt para os .ebm correspondentes."""
    total = len(file_paths)
    for idx, txt_path in enumerate(file_paths, 1):
        logger(t("processing_file", current=idx, total=total, name=txt_path.name), color=COLOR_LOG_YELLOW)
        try:
            ebm_candidate = txt_path.with_suffix(".ebm")
            if not ebm_candidate.exists():
                raise FileNotFoundError(t("ebm_not_found", path=str(ebm_candidate)))
            ebm = EBM(str(ebm_candidate))
            ebm.read()
            txt_content = txt_path.read_text(encoding="utf-8")
            mapping = parse_txt_to_event_texts(txt_content)
            replaced = 0

            for ev_idx, ev in enumerate(ebm.events):
                if ev_idx in mapping:
                    ev.writeEventText(mapping[ev_idx])
                    replaced += 1

            ebm.save(str(ebm_candidate))
            logger(t("import_completed", replaced=replaced, path=str(ebm_candidate)), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

def _extract_gz(file_paths: List[Path]):
    """Descomprime arquivos .gz."""
    total = len(file_paths)
    for idx, gz_path in enumerate(file_paths, 1):
        logger(t("processing_file", current=idx, total=total, name=gz_path.name), color=COLOR_LOG_YELLOW)
        try:
            out_path = gz_path.with_suffix('')
            data = gz_path.read_bytes()
            endian = "big" if data.startswith(b'\x00\x00') else "little"
            cursor = 0
            decompressed_parts: List[bytes] = []
            total_len = len(data)

            while cursor < total_len:
                if cursor + 4 > total_len:
                    break
                size_bytes = data[cursor:cursor + 4]
                cursor += 4
                block_size = int.from_bytes(size_bytes, byteorder=endian, signed=False)
                if block_size == 0:
                    continue
                if cursor + block_size > total_len:
                    raise EOFError("Block size extends past end of file")
                block = data[cursor:cursor + block_size]
                cursor += block_size
                try:
                    dec = zlib.decompress(block)
                except zlib.error as ze:
                    raise ValueError(f"zlib decompression failed: {ze}")
                decompressed_parts.append(dec)

            full = b"".join(decompressed_parts)
            out_path.write_bytes(full)
            logger(t("gz_extraction_completed", path=str(out_path)), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

def _compress_gz(file_paths: List[Path]):
    """Comprime arquivos em .gz (adiciona extensão .gz)."""
    endian = get_option("is_endiam")
    CHUNK_SIZE = 16 * 1024  # 16 KB
    total = len(file_paths)
    for idx, src_path in enumerate(file_paths, 1):
        logger(t("processing_file", current=idx, total=total, name=src_path.name), color=COLOR_LOG_YELLOW)
        try:
            out_path = src_path.with_name(src_path.name + '.gz')
            with src_path.open('rb') as src, out_path.open('wb') as dst:
                while True:
                    chunk = src.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    compressor = zlib.compressobj(
                        level=9,
                        method=zlib.DEFLATED,
                        wbits=15,
                        memLevel=9,
                        strategy=zlib.Z_DEFAULT_STRATEGY
                    )
                    comp = compressor.compress(chunk)
                    comp += compressor.flush(zlib.Z_FINISH)
                    size_bytes = len(comp).to_bytes(4, byteorder=endian, signed=False)
                    dst.write(size_bytes)
                    dst.write(comp)
            logger(t("gz_compression_completed", path=str(out_path)), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# AÇÕES DOS COMANDOS (CHAMAM OS FILEPICKERS)
# ==============================================================================

def action_extract():
    fp_extract_ebm.pick_files(
        allowed_extensions=["ebm"],
        dialog_title=t("select_ebm_files"),
    )

def action_import():
    fp_import_txt.pick_files(
        allowed_extensions=["txt"],
        dialog_title=t("select_txt_files"),
    )

def action_extract_gz():
    fp_extract_gz.pick_files(
        allowed_extensions=["gz"],
        dialog_title=t("select_gz_files"),
    )

def action_compress_gz():
    fp_compress_gz.pick_files(
        allowed_extensions=["*"],
        dialog_title=t("select_compress_files"),
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
        host_page.overlay.extend([fp_extract_ebm, fp_import_txt, fp_extract_gz, fp_compress_gz])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "options": [
            {
                "name": "is_endiam",
                "label": ("ENDIAM"),
                "values": ["big", "little"]
            }
        ],
        "commands": [
            {"label": t("extract_text"), "action": action_extract},
            {"label": t("import_text"), "action": action_import},
            {"label": t("extract_gz"), "action": action_extract_gz},
            {"label": t("compress_gz"), "action": action_compress_gz},
        ]
    }