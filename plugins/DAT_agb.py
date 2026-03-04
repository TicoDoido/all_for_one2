import os
import struct
import zlib
import math
import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "DAT Angry Birds Trilogy para arquivos de texto",
        "plugin_description": "Extrai e reinsere strings .loc em arquivos .dat Angry Birds Trilogy",
        "extract_strings": "Extrair Strings",
        "reinsert_strings": "Reinserir Strings",
        "select_dat_file": "Selecione o arquivo .dat",
        "dat_files": "Arquivos .dat",
        "all_files": "Todos os arquivos",
        "success": "Sucesso",
        "extraction_success": "Arquivo extraído com sucesso: {path}",
        "reinsert_success": "Arquivo modificado salvo em: {path}",
        "error": "Erro",
        "extraction_error": "Erro durante extração: {error}",
        "reinsert_error": "Erro durante reinserção: {error}",
        "file_not_found": "Arquivo não encontrado: {file}",
        "invalid_loc_id": "ID inválido no .loc. Esperado {expected}, encontrado {found}",
        "unterminated_string": "String não terminada após 0x{position:X}",
        "invalid_line_format": "Formato inválido na linha {line}: {content}",
        "invalid_hash": "Hash inválido na linha {line}: {hash}",
        "invalid_chunk": "RAWM não encontrado",
        "marker_not_found": "MARKER não encontrado após RAWM",
        "txt_not_found": "Arquivo .txt não encontrado: {file}",
        "compression_mode": "Modo de Compressão",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "file_processed": "Arquivo processado: {path}"
    },
    "en_US": {
        "plugin_name": "DAT Angry Birds Trilogy Text Files",
        "plugin_description": "Extracts and reinserts .loc strings in Angry Birds Trilogy .dat files",
        "extract_strings": "Extract Strings",
        "reinsert_strings": "Reinsert Strings",
        "select_dat_file": "Select .dat file",
        "dat_files": ".dat Files",
        "all_files": "All files",
        "success": "Success",
        "extraction_success": "File extracted successfully: {path}",
        "reinsert_success": "Modified file saved to: {path}",
        "error": "Error",
        "extraction_error": "Error during extraction: {error}",
        "reinsert_error": "Error during reinsertion: {error}",
        "file_not_found": "File not found: {file}",
        "invalid_loc_id": "Invalid .loc ID. Expected {expected}, found {found}",
        "unterminated_string": "Unterminated string after 0x{position:X}",
        "invalid_line_format": "Invalid format on line {line}: {content}",
        "invalid_hash": "Invalid hash on line {line}: {hash}",
        "invalid_chunk": "RAWM not found",
        "marker_not_found": "MARKER not found after RAWM",
        "txt_not_found": "TXT file not found: {file}",
        "compression_mode": "Compression Mode",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "file_processed": "File processed: {path}"
    },
    "es_ES": {
        "plugin_name": "DAT Angry Birds Trilogy para archivos de texto",
        "plugin_description": "Extrae y reinserta cadenas .loc en archivos .dat de Angry Birds Trilogy",
        "extract_strings": "Extraer Cadenas",
        "reinsert_strings": "Reinsertar Cadenas",
        "select_dat_file": "Seleccionar archivo .dat",
        "dat_files": "Archivos .dat",
        "all_files": "Todos los archivos",
        "success": "Éxito",
        "extraction_success": "Archivo extraído con éxito: {path}",
        "reinsert_success": "Archivo modificado guardado en: {path}",
        "error": "Error",
        "extraction_error": "Error durante extracción: {error}",
        "reinsert_error": "Error durante reinserción: {error}",
        "file_not_found": "Archivo no encontrado: {file}",
        "invalid_loc_id": "ID inválido en .loc. Esperado {expected}, encontrado {found}",
        "unterminated_string": "Cadena no terminada después de 0x{position:X}",
        "invalid_line_format": "Formato inválido en línea {line}: {content}",
        "invalid_hash": "Hash inválido en línea {line}: {hash}",
        "invalid_chunk": "RAWM no encontrado",
        "marker_not_found": "MARKER no encontrado después de RAWM",
        "txt_not_found": "Archivo .txt no encontrado: {file}",
        "compression_mode": "Modo de Compresión",
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

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FUNÇÃO PARA CORRIGIR A JANELA (TOPMOST)
# ==============================================================================
def pick_file_topmost(title, file_types):
    """Cria uma janela Tk invisível, força ela pro topo e abre o diálogo."""
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    file_path = filedialog.askopenfilename(parent=root, title=title, filetypes=file_types)
    root.destroy()
    return file_path

# ==============================================================================
# FUNÇÕES LOC (mantidas inalteradas)
# ==============================================================================
def parse_loc_to_txt_lines(loc_data: bytes) -> list[str]:
    loc_id = struct.unpack('>I', loc_data[0:4])[0]
    if loc_id != 0x10:  # LOC_ID_TAG
        raise ValueError(t("invalid_loc_id", expected="0x10", found=f"0x{loc_id:X}"))

    txt_lines = []
    cursor = 0x10  # LOC_HEADER_SIZE
    while cursor < len(loc_data):
        hash_val = struct.unpack('>I', loc_data[cursor:cursor+4])[0]
        num_tags = struct.unpack('>H', loc_data[cursor+4:cursor+6])[0]
        cursor += 6 + (num_tags * 4)

        str_end = loc_data.find(b'\x00', cursor)  # LOC_STRING_TERM
        if str_end == -1:
            raise ValueError(t("unterminated_string", position=cursor))

        string_bytes = loc_data[cursor:str_end]
        decoded_string = string_bytes.decode('utf-8')
        cursor = str_end + 1

        processed = decoded_string.replace('\n', '<nl>')
        txt_lines.append(f"{hash_val:08X} = {processed}")

    return txt_lines

def build_loc_from_txt(txt: str) -> bytes:
    body = bytearray()
    tag_pattern = re.compile(b'<<.*?>>')

    for i, line in enumerate(txt.splitlines(), 1):
        if not line.strip() or line.strip().startswith('#'):
            continue

        parts = line.split('=', 1)
        if len(parts) != 2:
            raise ValueError(t("invalid_line_format", line=i, content=line))

        try:
            hash_val = int(parts[0].strip(), 16)
        except ValueError:
            raise ValueError(t("invalid_hash", line=i, hash=parts[0]))

        final_str = parts[1].strip().replace('<nl>', '\n')
        encoded = final_str.encode('utf-8')

        tag_positions = []
        for match in tag_pattern.finditer(encoded):
            tag_positions.extend([match.start(), match.end()])

        body.extend(struct.pack('>I', hash_val))
        body.extend(struct.pack('>H', len(tag_positions) // 2))
        if tag_positions:
            body.extend(struct.pack(f'>{len(tag_positions)}H', *tag_positions))
        body.extend(encoded + b'\x00')

    header = struct.pack('>II', 0x10, 0x10 + len(body)) + b'\x00' * 8
    return header + body

# ==============================================================================
# MANIPULAÇÃO DE .DAT (mantida inalterada)
# ==============================================================================
def find_chunk_offset(data: bytes) -> int:
    RAWM_TAG = b'RAWM'
    MARKER = b'\xFA\xD8\xC1\x68'

    pos_rawm = data.find(RAWM_TAG)
    if pos_rawm < 0:
        raise ValueError(t("invalid_chunk"))

    pos_marker = data.find(MARKER, pos_rawm + len(RAWM_TAG))
    if pos_marker < 0:
        raise ValueError(t("marker_not_found"))

    count = struct.unpack('>I', data[pos_marker+4:pos_marker+8])[0]
    return count * 0x40  # ALIGN

def detect_patch(data: bytes) -> int | None:
    ID_TAG = b'KSP0'
    return max(
        [off for off in range(0, len(data), 0x40)
         if data[off:off+4] == ID_TAG and data[off+0x10:off+0x14] == ID_TAG],
        default=None
    )

# ==============================================================================
# FUNÇÕES PRINCIPAIS (adaptadas para usar logger)
# ==============================================================================
def extract(input_path: Path):
    data = input_path.read_bytes()
    off = find_chunk_offset(data)
    header = data[off:off+0x30]  # HEADER_SIZE
    comp_size = struct.unpack('>I', header[4:8])[0]
    comp_data = data[off+0x30:off+0x30+comp_size]

    try:
        decomp_data = zlib.decompress(comp_data, -zlib.MAX_WBITS)
    except zlib.error:
        decomp_data = zlib.decompress(comp_data)

    txt_lines = parse_loc_to_txt_lines(decomp_data)
    txt_path = input_path.with_suffix('.txt')
    txt_path.write_text('\n'.join(txt_lines) + '\n', encoding='utf-8')
    logger(t("extraction_success", path=str(txt_path)), color=COLOR_LOG_GREEN)

def reinsert(input_path: Path):
    compression_mode = get_option("modo_compactacao")

    raw_data = input_path.read_bytes()
    orig_off = find_chunk_offset(raw_data)
    header_original = raw_data[orig_off:orig_off+0x30]
    data = raw_data
    p_off = detect_patch(data)

    if p_off is not None:
        data = data[:p_off]

    prefix = bytearray(data)
    txt_path = input_path.with_suffix('.txt')

    if not txt_path.exists():
        raise FileNotFoundError(t("txt_not_found", file=str(txt_path)))

    txt_content = txt_path.read_text(encoding='utf-8')
    loc_data = build_loc_from_txt(txt_content)

    if compression_mode == "Zlib (X360)":
        comp_data = zlib.compress(loc_data, level=9)
    else:  # "Deflate (PS3)"
        comp_obj = zlib.compressobj(level=9, wbits=-zlib.MAX_WBITS)
        comp_data = comp_obj.compress(loc_data)
        comp_data += comp_obj.flush()
        comp_data += b'\x00\x01'   # seu sufixo

    comp_size, decomp_size = len(comp_data), len(loc_data)
    ALIGN = 0x40
    pad1 = (-len(prefix)) % ALIGN
    new_offset = len(prefix) + pad1
    new_count = new_offset // ALIGN

    RAWM_TAG = b'RAWM'
    MARKER = b'\xFA\xD8\xC1\x68'
    ID_TAG = b'KSP0'

    pos_rawm = prefix.find(RAWM_TAG)
    pos_marker = prefix.find(MARKER, pos_rawm + len(RAWM_TAG))
    count_pos = pos_marker + 4
    prefix[count_pos:count_pos+4] = struct.pack('>I', new_count)
    prefix.extend(b'\x00' * pad1)

    new_chunk_count = math.ceil((0x30 + comp_size) / ALIGN)
    header = bytearray(header_original)
    header[0:4] = header[0x10:0x14] = ID_TAG
    header[4:8] = struct.pack('>I', comp_size)
    header[8:12] = struct.pack('>I', decomp_size)
    header[12:16] = struct.pack('>I', new_chunk_count)

    buf = prefix + header + comp_data
    buf.extend(b'\x00' * ((-len(buf)) % ALIGN))

    out_path = input_path.with_name(f"{input_path.stem}_mod.dat")
    out_path.write_bytes(buf)
    logger(t("reinsert_success", path=str(out_path)), color=COLOR_LOG_GREEN)

# ==============================================================================
# AÇÕES DOS COMANDOS (USAM O SELETOR DE ARQUIVO TOPMOST)
# ==============================================================================
def action_extract():
    path = pick_file_topmost(t("select_dat_file"), [(t("dat_files"), "*.dat"), (t("all_files"), "*.*")])

    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)

    try:
        extract(Path(path))
    except Exception as e:
        logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)

def action_reinsert():
    path = pick_file_topmost(t("select_dat_file"), [(t("dat_files"), "*.dat"), (t("all_files"), "*.*")])

    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)

    try:
        reinsert(Path(path))
    except Exception as e:
        logger(t("reinsert_error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# ENTRY POINT (REGISTRO)
# ==============================================================================
def register_plugin(log_func, option_getter, host_language="pt_BR"):
    global logger, get_option, current_lang
    logger = log_func
    get_option = option_getter
    current_lang = host_language

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "options": [
            {
                "name": "modo_compactacao",
                "label": t("compression_mode"),
                "values": ["Zlib (X360)", "Deflate (PS3)"]   # valores fixos em inglês
            }
        ],
        "commands": [
            {"label": t("extract_strings"), "action": action_extract},
            {"label": t("reinsert_strings"), "action": action_reinsert}
        ]
    }