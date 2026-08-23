"""
msg2_capcom.py

Plugin para o All For One: extrai e remonta arquivos .msg com cabeçalho MSG2 (Xbox 360).
Segue o mesmo padrão de plugin do MSG1 (msg_lost-planet.py): traduções, FilePicker (flet),
opções de jogo, comandos e register_plugin().

Cada caractere no formato MSG2 ocupa 4 bytes: dois uint16 big-endian {coordenada, valor}.

Tabelas de caracteres extraídas das planilhas:
  - Editor_MSG2_XBOX360_DMC4.xlsm      -> DMC4 (Xbox360)
  - Editor_MSG2_XBOX360-RE5.xlsm       -> RE5 (Xbox360)
  - Editor_DLCs_RE5_MSG2_XBOX360.xlsm  -> RE5 DLCs (Xbox360)
"""

import struct
from pathlib import Path
import flet as ft

# ==============================================================================
# TRADUÇÕES DO PLUGIN
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "MSG2 Capcom (DMC4 / RE5 - Xbox360)",
        "select_game": "Escolha o Jogo",
        "plugin_description": "Converte arquivos .msg(MSG2) para texto e vice-versa",
        "extract_text": "Converter MSG para TXT",
        "rebuild_text": "Converter TXT para MSG",
        "select_msg_file": "Selecione arquivo .MSG",
        "select_txt_file": "Selecione arquivo .TXT",
        "msg_files": "Arquivos MSG",
        "txt_files": "Arquivos TXT",
        "all_files": "Todos os arquivos",
        "success": "Sucesso",
        "extraction_success": "Arquivo convertido: {path}",
        "recreation_success": "Arquivo recriado: {path}",
        "error": "Erro",
        "extraction_error": "Erro na conversão: {error}",
        "recreation_error": "Erro na conversão reversa: {error}",
        "invalid_magic": "Arquivo não é válido (Magic Number não é MSG2)",
        "processing_file": "Processando arquivo: {file}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída.",
        "unmapped_char": "Caractere sem mapeamento em {file}: {char} (ignorado)",
        "invalid_header": "Primeira linha deve conter o cabeçalho MSG2 em hexadecimal",
        "empty_txt": "Arquivo TXT vazio",
    },
    "en_US": {
        "plugin_name": "MSG2 Capcom (DMC4 / RE5 - Xbox360)",
        "select_game": "Select the Game",
        "plugin_description": "Converts .msg(MSG2) files to text and vice versa",
        "extract_text": "Convert MSG to TXT",
        "rebuild_text": "Convert TXT to MSG",
        "select_msg_file": "Select .MSG file",
        "select_txt_file": "Select .TXT file",
        "msg_files": "MSG Files",
        "txt_files": "TXT Files",
        "all_files": "All Files",
        "success": "Success",
        "extraction_success": "File converted: {path}",
        "recreation_success": "File rebuilt: {path}",
        "error": "Error",
        "extraction_error": "Conversion error: {error}",
        "recreation_error": "Reverse conversion error: {error}",
        "invalid_magic": "File is not valid (Magic Number is not MSG2)",
        "processing_file": "Processing file: {file}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed.",
        "unmapped_char": "Unmapped character in {file}: {char} (ignored)",
        "invalid_header": "First line must contain the MSG2 header in hexadecimal",
        "empty_txt": "Empty TXT file",
    },
    "es_ES": {
        "plugin_name": "MSG2 Capcom (DMC4 / RE5 - Xbox360)",
        "select_game": "Elige el Juego",
        "plugin_description": "Convierte archivos .msg(MSG2) a texto y viceversa",
        "extract_text": "Convertir MSG a TXT",
        "rebuild_text": "Convertir TXT a MSG",
        "select_msg_file": "Seleccionar archivo .MSG",
        "select_txt_file": "Seleccionar archivo .TXT",
        "msg_files": "Archivos MSG",
        "txt_files": "Archivos TXT",
        "all_files": "Todos los archivos",
        "success": "Éxito",
        "extraction_success": "Archivo convertido: {path}",
        "recreation_success": "Archivo recreado: {path}",
        "error": "Error",
        "extraction_error": "Error de conversión: {error}",
        "recreation_error": "Error de conversión inversa: {error}",
        "invalid_magic": "Archivo no es válido (Magic Number no es MSG2)",
        "processing_file": "Procesando archivo: {file}",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "operation_completed": "Operación completada.",
        "unmapped_char": "Carácter sin mapeo en {file}: {char} (ignorado)",
        "invalid_header": "La primera línea debe contener el encabezado MSG2 en hexadecimal",
        "empty_txt": "Archivo TXT vacío",
    },
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
# TABELAS DE CARACTERES (geradas a partir dos .xlsm) - mantidas intactas
# ==============================================================================

DMC4_X360_TABLE = {
    (0, 19712): '0',
    (2, 11776): '1',
    (4, 17408): '2',
    (6, 17408): '3',
    (8, 15104): '4',
    (10, 15104): '5',
    (12, 15104): '6',
    (14, 15104): '7',
    (16, 15104): '8',
    (18, 15104): '9',
    (20, 5888): '!',
    (22, 15360): '?',
    (24, 15104): '(',
    (26, 15104): ')',
    (28, 10240): ' ',
    (30, 5632): '&',
    (32, 5632): ':',
    (34, 15104): ';',
    (36, 5632): ',',
    (38, 5888): '.',
    (40, 15104): '"',
    (42, 5888): "'",
    (44, 15104): '~',
    (46, 8192): '-',
    (48, 8192): '+',
    (50, 15104): '/',
    (52, 15104): '@',
    (54, 15104): '$',
    (56, 24832): 'A',
    (58, 21248): 'B',
    (60, 20992): 'C',
    (62, 23296): 'D',
    (64, 20736): 'E',
    (66, 19712): 'F',
    (68, 23296): 'G',
    (70, 20224): 'H',
    (72, 7680): 'I',
    (74, 18176): 'J',
    (76, 21504): 'K',
    (78, 19200): 'L',
    (80, 28416): 'M',
    (82, 23040): 'N',
    (84, 25344): 'O',
    (86, 18432): 'P',
    (88, 20736): 'Q',
    (90, 20736): 'R',
    (92, 19712): 'S',
    (94, 20736): 'T',
    (96, 32256): 'U',
    (98, 21504): 'V',
    (100, 32000): 'W',
    (102, 32000): 'X',
    (104, 20480): 'Y',
    (106, 15104): 'Z',
    (108, 15616): 'a',
    (110, 18176): 'b',
    (112, 16384): 'c',
    (114, 17664): 'd',
    (116, 16640): 'e',
    (118, 11008): 'f',
    (120, 17152): 'g',
    (122, 17664): 'h',
    (124, 7424): 'i',
    (126, 6144): 'j',
    (128, 17920): 'k',
    (130, 7168): 'l',
    (132, 27904): 'm',
    (134, 17408): 'n',
    (136, 17664): 'o',
    (138, 17920): 'p',
    (140, 17408): 'q',
    (142, 11264): 'r',
    (144, 15360): 's',
    (146, 10240): 't',
    (148, 17920): 'u',
    (150, 16640): 'v',
    (152, 24320): 'w',
    (154, 24320): 'x',
    (156, 17152): 'y',
    (158, 14080): 'z',
    (160, 15104): '[',
    (162, 15104): ']',
    (168, 15104): '®',
    (172, 15104): 'À',
    (174, 15104): 'Á',
    (176, 15104): 'Â',
    (178, 15104): 'Ã',
    (180, 15104): 'Ç',
    (184, 15104): 'É',
    (186, 15104): 'Ê',
    (192, 15104): 'Í',
    (198, 15104): 'Ñ',
    (202, 15104): 'Ó',
    (204, 15104): 'Ô',
    (206, 15104): 'Õ',
    (208, 15104): 'Ú',
    (216, 15616): 'à',
    (218, 15616): 'á',
    (220, 15616): 'â',
    (222, 15616): 'ã',
    (224, 16384): 'ç',
    (228, 16640): 'é',
    (230, 16640): 'ê',
    (236, 7424): 'í',
    (242, 15104): 'ñ',
    (246, 17664): 'ó',
    (248, 17664): 'ô',
    (250, 17664): 'õ',
    (254, 17920): 'ú',
    (266, 15104): '×',
    (278, 15104): '%',
    (282, 15104): '_',
    (842, 15104): 'β',
    (834, 25088): '∞',
    (0, 772): '|',
}

RE5_X360_TABLE = {
    (0, 15360): '0',
    (2, 15360): '1',
    (4, 15360): '2',
    (6, 15360): '3',
    (8, 15360): '4',
    (10, 15360): '5',
    (12, 15360): '6',
    (14, 15360): '7',
    (16, 15360): '8',
    (18, 15360): '9',
    (20, 15360): '!',
    (22, 15360): '?',
    (24, 15360): '(',
    (26, 15360): ')',
    (28, 15360): ' ',
    (30, 15360): '&',
    (32, 15360): ':',
    (34, 15360): ';',
    (36, 15360): ',',
    (38, 15360): '.',
    (40, 15360): '"',
    (42, 15360): "'",
    (44, 15360): '~',
    (46, 15360): '-',
    (48, 15360): '+',
    (50, 15360): '/',
    (52, 15360): '@',
    (54, 15360): '$',
    (56, 15360): 'A',
    (58, 15360): 'B',
    (60, 15360): 'C',
    (62, 15360): 'D',
    (64, 15360): 'E',
    (66, 15360): 'F',
    (68, 15360): 'G',
    (70, 15360): 'H',
    (72, 15360): 'I',
    (74, 15360): 'J',
    (76, 15360): 'K',
    (78, 15360): 'L',
    (80, 15360): 'M',
    (82, 15360): 'N',
    (84, 15360): 'O',
    (86, 15360): 'P',
    (88, 15360): 'Q',
    (90, 15360): 'R',
    (92, 15360): 'S',
    (94, 15360): 'T',
    (96, 15360): 'U',
    (98, 15360): 'V',
    (100, 15360): 'W',
    (102, 15360): 'X',
    (104, 15360): 'Y',
    (106, 15360): 'Z',
    (108, 15360): 'a',
    (110, 15360): 'b',
    (112, 15360): 'c',
    (114, 15360): 'd',
    (116, 15360): 'e',
    (118, 15360): 'f',
    (120, 15360): 'g',
    (122, 15360): 'h',
    (124, 15360): 'i',
    (126, 15360): 'j',
    (128, 15360): 'k',
    (130, 15360): 'l',
    (132, 15360): 'm',
    (134, 15360): 'n',
    (136, 15360): 'o',
    (138, 15360): 'p',
    (140, 15360): 'q',
    (142, 15360): 'r',
    (144, 15360): 's',
    (146, 15360): 't',
    (148, 15360): 'u',
    (150, 15360): 'v',
    (152, 15360): 'w',
    (154, 15360): 'x',
    (156, 15360): 'y',
    (158, 15360): 'z',
    (160, 15360): '[',
    (162, 15360): ']',
    (168, 15360): '®',
    (172, 15360): 'À',
    (174, 15360): 'Á',
    (176, 15360): 'Â',
    (178, 15360): 'Ã',
    (180, 15360): 'Ç',
    (184, 15360): 'É',
    (186, 15360): 'Ê',
    (192, 15360): 'Í',
    (198, 15360): 'Ñ',
    (202, 15360): 'Ó',
    (204, 15360): 'Ô',
    (206, 15360): 'Õ',
    (208, 15360): 'Ú',
    (216, 15360): 'à',
    (218, 15360): 'á',
    (220, 15360): 'â',
    (222, 15360): 'ã',
    (224, 15360): 'ç',
    (228, 15360): 'é',
    (230, 15360): 'ê',
    (236, 15360): 'í',
    (242, 15360): 'ñ',
    (246, 15360): 'ó',
    (248, 15360): 'ô',
    (250, 15360): 'õ',
    (254, 15360): 'ú',
    (266, 15360): '×',
    (278, 15360): '%',
    (282, 15360): '_',
    (842, 15360): 'β',
    (834, 25088): '∞',
    (0, 772): '|',
}

RE5_DLC_X360_TABLE = {
    (0, 15104): '0',
    (2, 15104): '1',
    (4, 15104): '2',
    (6, 15104): '3',
    (8, 15104): '4',
    (10, 15104): '5',
    (12, 15104): '6',
    (14, 15104): '7',
    (16, 15104): '8',
    (18, 15104): '9',
    (20, 15104): '!',
    (22, 15104): '?',
    (24, 15104): '(',
    (26, 15104): ')',
    (28, 15104): ' ',
    (30, 15104): '&',
    (32, 15104): ':',
    (34, 15104): ';',
    (36, 15104): ',',
    (38, 15104): '.',
    (40, 15104): '"',
    (42, 15104): "'",
    (44, 15104): '~',
    (46, 15104): '-',
    (48, 15104): '+',
    (50, 15104): '/',
    (52, 15104): '@',
    (54, 15104): '$',
    (56, 15104): 'A',
    (58, 15104): 'B',
    (60, 15104): 'C',
    (62, 15104): 'D',
    (64, 15104): 'E',
    (66, 15104): 'F',
    (68, 15104): 'G',
    (70, 15104): 'H',
    (72, 12544): 'I',
    (74, 14848): 'J',
    (76, 15104): 'K',
    (78, 15104): 'L',
    (80, 15104): 'M',
    (82, 15104): 'N',
    (84, 15104): 'O',
    (86, 15104): 'P',
    (88, 15104): 'Q',
    (90, 15104): 'R',
    (92, 15104): 'S',
    (94, 15104): 'T',
    (96, 15104): 'U',
    (98, 15104): 'V',
    (100, 15104): 'W',
    (102, 15104): 'X',
    (104, 15104): 'Y',
    (106, 15104): 'Z',
    (108, 15104): 'a',
    (110, 15104): 'b',
    (112, 15104): 'c',
    (114, 15104): 'd',
    (116, 15104): 'e',
    (118, 15104): 'f',
    (120, 15104): 'g',
    (122, 15104): 'h',
    (124, 13568): 'i',
    (126, 12032): 'j',
    (128, 15104): 'k',
    (130, 15104): 'l',
    (132, 15104): 'm',
    (134, 15104): 'n',
    (136, 15104): 'o',
    (138, 15104): 'p',
    (140, 15104): 'q',
    (142, 15104): 'r',
    (144, 15104): 's',
    (146, 15104): 't',
    (148, 15104): 'u',
    (150, 15104): 'v',
    (152, 15104): 'w',
    (154, 15104): 'x',
    (156, 15104): 'y',
    (158, 15104): 'z',
    (160, 15104): '[',
    (162, 15104): ']',
    (168, 15104): '®',
    (172, 15104): 'À',
    (174, 15104): 'Á',
    (176, 15104): 'Â',
    (178, 15104): 'Ã',
    (180, 15104): 'Ç',
    (184, 15104): 'É',
    (186, 15104): 'Ê',
    (192, 15104): 'Í',
    (198, 15104): 'Ñ',
    (202, 15104): 'Ó',
    (204, 15104): 'Ô',
    (206, 15104): 'Õ',
    (208, 15104): 'Ú',
    (216, 15104): 'à',
    (218, 15104): 'á',
    (220, 15104): 'â',
    (222, 15104): 'ã',
    (224, 15104): 'ç',
    (228, 15104): 'é',
    (230, 15104): 'ê',
    (236, 15104): 'í',
    (242, 15104): 'ñ',
    (246, 15104): 'ó',
    (248, 15104): 'ô',
    (250, 15104): 'õ',
    (254, 15104): 'ú',
    (266, 15104): '×',
    (278, 15104): '%',
    (282, 15104): '_',
    (842, 15104): 'β',
    (834, 25088): '∞',
    (0, 772): '|',
}

GAME_TABLES = {
    "DMC4 (X360)": DMC4_X360_TABLE,
    "RE5 Base (X360)": RE5_X360_TABLE,
    "RE5 DLCs (X360)": RE5_DLC_X360_TABLE,
}

DEFAULT_GAME = "DMC4 (X360)"

# Aliases aceitos para nomes antigos/variantes vindos do host (option_getter).
GAME_ALIASES = {
    "dmc4": "DMC4 (X360)",
    "dmc4 (xbox360)": "DMC4 (X360)",
    "dmc4 (x360)": "DMC4 (X360)",
    "re5": "RE5 Base (X360)",
    "re5 (xbox360)": "RE5 Base (X360)",
    "re5 (x360)": "RE5 Base (X360)",
    "re5 base (x360)": "RE5 Base (X360)",
    "re5 dlcs (xbox360)": "RE5 DLCs (X360)",
    "re5 dlcs (x360)": "RE5 DLCs (X360)",
}

MAGIC = b"MSG2"
HEADER_SIZE = 64
UNIT = 4                 # cada caractere ocupa 2 uint16 (BE) = {coordenada, valor}
NO_TERM_MARK = "{NOTERM}"
TERMINATOR = (0, 0)      # unidade 00 00 00 00 = fim de string
# Marcadores de fim de mensagem: cada um encerra uma linha no TXT (uma fala por linha),
# do mesmo jeito que o TXT usado no editor .xlsm.
END_MARKS = {(0, 260)}
LINE_SEP = "\r\n"        # mesmo separador usado pelo editor .xlsm (vbCrLf)


def resolve_game(game) -> str:
    """Normaliza o nome do jogo vindo do host para uma chave valida de GAME_TABLES."""
    if not game:
        return DEFAULT_GAME
    name = str(game).strip()
    if name in GAME_TABLES:
        return name
    key = name.lower()
    if key in GAME_ALIASES:
        return GAME_ALIASES[key]
    # comparacao tolerante (ignora espacos/parenteses/caixa)
    def norm(v):
        return "".join(ch for ch in v.lower() if ch.isalnum())
    nk = norm(name)
    for real in GAME_TABLES:
        if norm(real) == nk:
            return real
    for real in GAME_TABLES:
        if nk and (nk in norm(real) or norm(real).startswith(nk[:4])):
            return real
    return DEFAULT_GAME


def get_table(game: str):
    return GAME_TABLES[resolve_game(game)]


def reverse_table(table):
    rev = {}
    for code, char in table.items():
        rev.setdefault(char, code)
    return rev


def read_units(data: bytes):
    units = []
    for pos in range(0, len(data) - UNIT + 1, UNIT):
        units.append(struct.unpack_from(">HH", data, pos))
    return units


def units_to_text(units, table) -> str:
    out = []
    for unit in units:
        char = table.get(unit)
        if char is None:
            out.append("{%d,%d}" % unit)
        else:
            out.append(char)
    return "".join(out)


def text_to_units(text: str, rev, on_warn=None):
    units = []
    i = 0
    length = len(text)
    while i < length:
        if text[i] == "{":
            end = text.find("}", i)
            if end != -1:
                inner = text[i + 1:end].replace(" ", "")
                parts = inner.split(",")
                if len(parts) == 2 and all(p.lstrip("-").isdigit() for p in parts):
                    units.append((int(parts[0]) & 0xFFFF, int(parts[1]) & 0xFFFF))
                    i = end + 1
                    continue
        char = text[i]
        code = rev.get(char)
        if code is None:
            if on_warn:
                on_warn(char)
        else:
            units.append(code)
        i += 1
    return units


# ==============================================================================
# MSG2 -> TXT / TXT -> MSG2 (usadas pelos comandos do plugin)
# ==============================================================================

def _convert_msg_to_text(msg_path: Path, txt_path: Path):
    """Convert MSG (MSG2) file to TXT using the selected game table."""
    game = resolve_game(get_option("tabela_jogo") if get_option else None)
    table = get_table(game)

    logger(t("processing_file", file=msg_path.name), color=COLOR_LOG_YELLOW)

    data = msg_path.read_bytes()
    if data[:4] != MAGIC:
        raise ValueError(t("invalid_magic"))

    header = data[:HEADER_SIZE]
    text_start = struct.unpack_from(">I", header, 4)[0]
    if text_start < HEADER_SIZE or text_start >= len(data):
        text_start = HEADER_SIZE

    units = read_units(data[text_start:])

    lines = []
    current = []
    for unit in units:
        if unit == TERMINATOR:
            lines.append(units_to_text(current, table))
            current = []
        elif unit in END_MARKS:
            # marcador de fim de mensagem (ex.: {0,260}) - fecha a linha mantendo o codigo
            current.append(unit)
            lines.append(units_to_text(current, table))
            current = []
        else:
            current.append(unit)
    if current:
        # ultima string sem terminador: marca para remontar identico ao original
        lines.append(units_to_text(current, table) + NO_TERM_MARK)


    header_line = "{" + " ".join(f"{b:02x}" for b in header) + "}"
    out_lines = [header_line]
    if text_start != HEADER_SIZE:
        out_lines.append("{RAW " + data[HEADER_SIZE:text_start].hex() + "}")
    out_lines.extend(lines)

    # Grava igual ao TXT gerado pelo .xlsm: uma string por linha, quebras CRLF
    # e UTF-8 sem BOM (assim o Bloco de Notas nao junta tudo em uma unica linha).
    with open(txt_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(LINE_SEP.join(out_lines) + LINE_SEP)
    return True


def _convert_text_to_msg(txt_path: Path, msg_path: Path):
    """Convert TXT file back to MSG (MSG2) using the selected game table."""
    game = resolve_game(get_option("tabela_jogo") if get_option else None)
    table = get_table(game)
    rev = reverse_table(table)

    logger(t("processing_file", file=txt_path.name), color=COLOR_LOG_YELLOW)

    raw_text = txt_path.read_text(encoding="utf-8-sig")
    raw_lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if raw_lines and raw_lines[-1] == "":
        raw_lines.pop()
    if not raw_lines:
        raise ValueError(t("empty_txt"))

    head = raw_lines[0].strip()
    if not (head.startswith("{") and head.endswith("}")):
        raise ValueError(t("invalid_header"))
    header = bytearray.fromhex(head[1:-1].replace(" ", ""))
    if len(header) != HEADER_SIZE or bytes(header[:4]) != MAGIC:
        raise ValueError(t("invalid_header"))

    body_lines = raw_lines[1:]
    extra = b""
    if body_lines and body_lines[0].startswith("{RAW "):
        extra = bytes.fromhex(body_lines[0][5:-1].strip())
        body_lines = body_lines[1:]

    def on_warn(char):
        logger(t("unmapped_char", file=txt_path.name, char=repr(char)), color=COLOR_LOG_YELLOW)

    payload = bytearray()
    for line in body_lines:
        add_terminator = True
        if line.endswith(NO_TERM_MARK):
            line = line[: -len(NO_TERM_MARK)]
            add_terminator = False
        units = text_to_units(line, rev, on_warn)
        for unit in units:
            payload += struct.pack(">HH", *unit)
        if units and units[-1] in END_MARKS:
            # linha ja termina com marcador de fim de mensagem
            add_terminator = False
        if add_terminator:
            payload += struct.pack(">HH", *TERMINATOR)

    text_start = HEADER_SIZE + len(extra)
    struct.pack_into(">I", header, 4, text_start)
    out = bytearray(bytes(header) + extra + bytes(payload))
    struct.pack_into(">I", out, 8, len(out))  # tamanho total do arquivo

    msg_path.write_bytes(bytes(out))
    return True


# ==============================================================================
# FUNÇÕES DE PROCESSAMENTO EM LOTE
# ==============================================================================

def _process_extract(msg_paths):
    for msg_path in msg_paths:
        logger(t("processing", name=msg_path.name), color=COLOR_LOG_YELLOW)
        try:
            txt_path = msg_path.with_suffix('.txt')
            _convert_msg_to_text(msg_path, txt_path)
            logger(t("extraction_success", path=str(txt_path)), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("extraction_error", error=str(e)), color=COLOR_LOG_RED)
    logger(t("operation_completed"), color=COLOR_LOG_GREEN)


def _process_rebuild(txt_paths):
    for txt_path in txt_paths:
        logger(t("processing", name=txt_path.name), color=COLOR_LOG_YELLOW)
        try:
            msg_path_com_ext = txt_path.with_suffix('.msg')
            msg_path_no_ext = txt_path.with_suffix('')
            if msg_path_com_ext.exists():
                msg_path = msg_path_com_ext
            elif msg_path_no_ext.exists():
                msg_path = msg_path_no_ext
            else:
                msg_path = msg_path_com_ext  # será criado

            _convert_text_to_msg(txt_path, msg_path)
            logger(t("recreation_success", path=str(msg_path)), color=COLOR_LOG_GREEN)
        except Exception as e:
            logger(t("recreation_error", error=str(e)), color=COLOR_LOG_RED)
    logger(t("operation_completed"), color=COLOR_LOG_GREEN)


# ==============================================================================
# AÇÕES DOS COMANDOS
# ==============================================================================

def action_extract():
    fp_extract.pick_files(
        allow_multiple=True,
        allowed_extensions=["msg"],
        dialog_title=t("select_msg_file"),
    )


def action_rebuild():
    fp_rebuild.pick_files(
        allow_multiple=True,
        allowed_extensions=["txt"],
        dialog_title=t("select_txt_file"),
    )


# ==============================================================================
# FilePickers
# ==============================================================================

fp_extract = ft.FilePicker(
    on_result=lambda e: (
        _process_extract([Path(f.path) for f in e.files]) if e.files else logger(t("cancelled"))
    )
)

fp_rebuild = ft.FilePicker(
    on_result=lambda e: (
        _process_rebuild([Path(f.path) for f in e.files]) if e.files else logger(t("cancelled"))
    )
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
        "options": [
            {
                "name": "tabela_jogo",
                "label": t("select_game"),
                "values": list(GAME_TABLES.keys()),
            }
        ],
        "commands": [
            {"label": t("extract_text"), "action": action_extract},
            {"label": t("rebuild_text"), "action": action_rebuild},
        ],
    }
