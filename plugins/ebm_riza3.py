import os
import re
import struct
import zlib
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "EBM-GZ - Atelier Ryza 3",
        "plugin_description": "Extrai/importa textos EBM e gerencia arquivos .gz",
        "extract_text": "Extrair texto (EBM → TXT)",
        "import_text": "Importar texto (TXT → EBM)",
        "extract_gz": "Descomprimir .gz",
        "compress_gz": "Comprimir para .gz",
        "extraction_completed": "Extração concluída! {count} eventos para: {path}",
        "import_completed": "Importação concluída! {replaced} eventos. Salvo em: {path}",
        "gz_done": "Operação GZ concluída: {path}",
        "ebm_not_found": "Arquivo EBM correspondente não encontrado.",
        "unexpected_error": "Erro: {error}",
        "cancelled": "Seleção cancelada.",
        "processing_file": "Processando {current}/{total}: {name}"
    },
    "en_US": {
        "plugin_name": "EBM-GZ - Atelier Ryza 3",
        "plugin_description": "Extracts/imports EBM texts and manages .gz files",
        "extract_text": "Extract text",
        "import_text": "Import text",
        "extract_gz": "Decompress .gz",
        "compress_gz": "Compress to .gz",
        "extraction_completed": "Extraction completed! {count} events to: {path}",
        "import_completed": "Import completed! {replaced} events. Saved to: {path}",
        "gz_done": "GZ operation completed: {path}",
        "ebm_not_found": "Corresponding EBM file not found.",
        "unexpected_error": "Error: {error}",
        "cancelled": "Selection cancelled.",
        "processing_file": "Processing {current}/{total}: {name}"
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

logger = None
get_option = None
current_lang = "pt_BR"

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# CLASSES DE SUPORTE (LÓGICA EBM PRESERVADA)
# ==============================================================================

class Reader:
    def __init__(self, buffer: bytes):
        self._buffer = buffer
        self._cursor = 0
    def consume(self, n: int) -> bytes:
        out = self._buffer[self._cursor:self._cursor + n]
        self._cursor += n
        return out
    def peek(self, start, end): return self._buffer[start:end]
    def remaining(self): return self._buffer[self._cursor:]

class Event:
    def __init__(self, header: bytes, data: bytes, footer: bytes):
        self._header = bytearray(header)
        self._data = bytearray(data)
        self._footer = bytearray(footer)
    
    @property
    def data(self) -> str:
        return bytes(self._data).decode('utf-8', errors='replace').rstrip('\x00')
    
    @property
    def length(self) -> int:
        raw = bytes(self._header[60:64])
        data_length = int.from_bytes(raw, byteorder='little', signed=True)
        return len(self._header) + data_length + len(self._footer)

    def writeEventText(self, text: str):
        encoded = text.encode('utf-8')
        length = len(encoded) + 1
        pos = len(self._header) - 4
        self._header[pos:pos+4] = (length).to_bytes(4, byteorder='little', signed=True)
        new_payload = bytearray(length)
        new_payload[0:len(encoded)] = encoded
        self._data = new_payload

    def write(self, dest: bytearray, offset: int):
        total = bytes(self._header) + bytes(self._data) + bytes(self._footer)
        dest[offset:offset+len(total)] = total

class EBM:
    def __init__(self, raw: bytes):
        self._reader = Reader(raw)
        self._length = abs(int.from_bytes(self._reader.consume(4), 'little', signed=True))
        self._events = []
    
    def read(self):
        for _ in range(self._length):
            header = self._reader.consume(60)
            len_bytes = self._reader.consume(4)
            p_len = int.from_bytes(len_bytes, 'little', signed=True)
            payload = self._reader.consume(p_len)
            trailer = self._reader.consume(8)
            self._events.append(Event(header + len_bytes, payload, trailer))

    def save(self) -> bytes:
        rest = self._reader.remaining()
        ev_len = sum(e.length for e in self._events)
        buf = bytearray(4 + ev_len + len(rest))
        buf[0:4] = int(len(self._events)).to_bytes(4, 'little', signed=True)
        off = 4
        for e in self._events:
            e.write(buf, off)
            off += e.length
        buf[off:] = rest
        return bytes(buf)

# ==============================================================================
# LÓGICA DE EXECUÇÃO (MIGRAÇÃO PARA FLET)
# ==============================================================================

def run_extract(files):
    if not files: return
    for i, f_path in enumerate(files, 1):
        try:
            logger(t("processing_file", current=i, total=len(files), name=os.path.basename(f_path)))
            ebm = EBM(Path(f_path).read_bytes())
            ebm.read()
            
            parts = []
            for idx, ev in enumerate(ebm._events):
                type_lbl = "message" if ev._header[0:4] == b'\x02\x00\x00\x00' else "notification"
                parts.append(f"### EVENT {idx:04d} [{type_lbl}]\n{ev.data}\n\n")
            
            out_txt = Path(f_path).with_suffix(".txt")
            out_txt.write_text("".join(parts).strip(), encoding="utf-8")
            logger(t("extraction_completed", count=len(ebm._events), path=out_txt.name), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

def run_import(files):
    if not files: return
    for i, f_path in enumerate(files, 1):
        try:
            txt_path = Path(f_path)
            ebm_path = txt_path.with_suffix(".ebm")
            if not ebm_path.exists():
                logger(t("ebm_not_found"), color=COLOR_LOG_RED)
                continue
            
            ebm = EBM(ebm_path.read_bytes())
            ebm.read()
            
            txt_content = txt_path.read_text(encoding="utf-8")
            mapping = {}
            for m in re.finditer(r"### EVENT (\d{4}) \[.*?\]\s*\n(.*?)(?=\n### EVENT|\Z)", txt_content, re.S):
                mapping[int(m.group(1))] = m.group(2).strip()
            
            replaced = 0
            for idx, ev in enumerate(ebm._events):
                if idx in mapping:
                    ev.writeEventText(mapping[idx])
                    replaced += 1
            
            ebm_path.write_bytes(ebm.save())
            logger(t("import_completed", replaced=replaced, path=ebm_path.name), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

def run_gz_op(files, compress=False):
    if not files: return
    endian = get_option("is_endian") or "little"
    for f_path in files:
        try:
            p = Path(f_path)
            if compress:
                out = p.with_name(p.name + ".gz")
                with p.open('rb') as src, out.open('wb') as dst:
                    while chunk := src.read(16 * 1024):
                        comp = zlib.compress(chunk, level=9)
                        dst.write(len(comp).to_bytes(4, endian))
                        dst.write(comp)
            else:
                out = p.with_suffix('')
                data = p.read_bytes()
                cursor, parts = 0, []
                while cursor < len(data):
                    sz = int.from_bytes(data[cursor:cursor+4], endian)
                    cursor += 4
                    parts.append(zlib.decompress(data[cursor:cursor+sz]))
                    cursor += sz
                out.write_bytes(b"".join(parts))
            logger(t("gz_done", path=out.name), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# REGISTRO DO PLUGIN
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR"):
    global logger, get_option, current_lang
    logger, get_option, current_lang = log_func, option_getter, host_language

    fp_ebm = ft.FilePicker(on_result=lambda e: run_extract([f.path for f in e.files]) if e.files else None)
    fp_txt = ft.FilePicker(on_result=lambda e: run_import([f.path for f in e.files]) if e.files else None)
    fp_gz_dec = ft.FilePicker(on_result=lambda e: run_gz_op([f.path for f in e.files], False) if e.files else None)
    fp_gz_com = ft.FilePicker(on_result=lambda e: run_gz_op([f.path for f in e.files], True) if e.files else None)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "pickers": [fp_ebm, fp_txt, fp_gz_dec, fp_gz_com],
        "options": [
            {"name": "is_endian", "label": "ENDIANNESS", "values": ["little", "big"]}
        ],
        "commands": [
            {"label": t("extract_text"), "action": lambda: fp_ebm.pick_files(allow_multiple=True)},
            {"label": t("import_text"), "action": lambda: fp_txt.pick_files(allow_multiple=True)},
            {"label": t("extract_gz"), "action": lambda: fp_gz_dec.pick_files(allow_multiple=True)},
            {"label": t("compress_gz"), "action": lambda: fp_gz_com.pick_files(allow_multiple=True)},
        ]
    }