import os
import re
import struct
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "DCT/DICT - Extrator e Reinseridor de Texto",
        "plugin_description": "Extrai e reinsere textos de arquivos DCT/DICT",
        "extract_texts": "Extrair Textos",
        "reinsert_texts": "Reinserir Textos",
        "select_binary_file": "Selecione o arquivo binário",
        "select_dct_file": "Selecione o arquivo .dct",
        "binary_files": "Arquivos Binários",
        "dct_files": "Arquivos DCT",
        "all_files": "Todos os arquivos",
        "extraction_completed": "Extração finalizada! Textos extraídos: {count}\nArquivo salvo em: {path}",
        "reinsertion_completed": "Reinserção concluída com sucesso! Ponteiros atualizados: {count}\nArquivo gerado: {path}",
        "txt_file_not_found": "Arquivo TXT correspondente não encontrado: {path}",
        "no_valid_pointers": "Nenhum ponteiro válido encontrado",
        "unexpected_error": "Erro inesperado: {error}",
        "auto": "Auto (UTF-8 → CP1252)",
        "utf8": "UTF-8",
        "cp1252": "CP1252 (Windows)",
        "extract_encoding": "Codificação de Extração",
        "reinsert_encoding": "Codificação de Reinserção",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "extracting_to": "Extraindo para: {path}",
        "recreating_to": "Reconstruindo a partir de: {path}",
        "log_extracting": "Extraindo texto {idx}..."
    },
    "en_US": {
        "plugin_name": "DCT/DICT - Text Extractor and Reinserter",
        "plugin_description": "Extracts and reinserts texts from DCT/DICT files",
        "extract_texts": "Extract Texts",
        "reinsert_texts": "Reinsert Texts",
        "select_binary_file": "Select binary file",
        "select_dct_file": "Select .dct file",
        "binary_files": "Binary Files",
        "dct_files": "DCT Files",
        "all_files": "All files",
        "extraction_completed": "Extraction completed! Texts extracted: {count}\nFile saved at: {path}",
        "reinsertion_completed": "Reinsertion completed successfully! Pointers updated: {count}\nFile generated: {path}",
        "txt_file_not_found": "Corresponding TXT file not found: {path}",
        "no_valid_pointers": "No valid pointers found",
        "unexpected_error": "Unexpected error: {error}",
        "auto": "Auto (UTF-8 → CP1252)",
        "utf8": "UTF-8",
        "cp1252": "CP1252 (Windows)",
        "extract_encoding": "Extraction Encoding",
        "reinsert_encoding": "Reinsertion Encoding",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "extracting_to": "Extracting to: {path}",
        "recreating_to": "Rebuilding from: {path}",
        "log_extracting": "Extracting text {idx}..."
    },
    "es_ES": {
        "plugin_name": "DCT/DICT - Extractor y Reinsertador de Texto",
        "plugin_description": "Extrae y reinserta textos de archivos DCT/DICT",
        "extract_texts": "Extraer Textos",
        "reinsert_texts": "Reinsertar Textos",
        "select_binary_file": "Seleccionar archivo binario",
        "select_dct_file": "Seleccionar archivo .dct",
        "binary_files": "Archivos Binarios",
        "dct_files": "Archivos DCT",
        "all_files": "Todos los archivos",
        "extraction_completed": "¡Extracción finalizada! Textos extraídos: {count}\nArchivo guardado en: {path}",
        "reinsertion_completed": "¡Reinserción completada con éxito! Punteros actualizados: {count}\nArchivo generado: {path}",
        "txt_file_not_found": "Archivo TXT correspondiente no encontrado: {path}",
        "no_valid_pointers": "No se encontraron punteros válidos",
        "unexpected_error": "Error inesperado: {error}",
        "auto": "Auto (UTF-8 → CP1252)",
        "utf8": "UTF-8",
        "cp1252": "CP1252 (Windows)",
        "extract_encoding": "Codificación de Extracción",
        "reinsert_encoding": "Codificación de Reinserción",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "extracting_to": "Extrayendo a: {path}",
        "recreating_to": "Reconstruyendo desde: {path}",
        "log_extracting": "Extrayendo texto {idx}..."
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
# FUNÇÕES AUXILIARES (DECODIFICAÇÃO/CODIFICAÇÃO)
# ==============================================================================

def decode_texto(bytes_data, encoding_choice):
    """Decodifica bytes conforme a escolha do usuário (utf-8 ou cp1252)."""
    if encoding_choice == "utf-8":
        return bytes_data.decode("utf-8", errors="ignore")
    elif encoding_choice == "cp1252":
        return bytes_data.decode("cp1252", errors="ignore")
    else:
        # Fallback padrão
        try:
            return bytes_data.decode("utf-8", errors="ignore")
        except Exception:
            return bytes_data.decode("cp1252", errors="ignore")

def encode_texto(text, encoding_choice):
    """Codifica texto para bytes conforme a escolha do usuário."""
    if encoding_choice == "utf-8":
        return text.encode("utf-8", errors="ignore")
    elif encoding_choice == "cp1252":
        return text.encode("cp1252", errors="ignore")
    else:
        # Fallback padrão
        return text.encode("cp1252", errors="ignore")

def ler_textos_do_txt(caminho_txt):
    """Lê o .txt (sempre em UTF-8) e retorna mapping {idx: text}."""
    with open(caminho_txt, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    pattern = re.compile(r"====\s*Texto\s*(\d+)\s*====\s*\r?\n", re.IGNORECASE)
    parts = []
    mapping = {}

    for m in pattern.finditer(content):
        idx = int(m.group(1))
        if parts:
            prev_idx, prev_start = parts[-1]
            block_text = content[prev_start:m.start()]
            mapping[prev_idx] = block_text.rstrip("\r\n")
        parts.append((idx, m.end()))

    if parts:
        last_idx, last_pos = parts[-1]
        mapping[last_idx] = content[last_pos:].rstrip("\r\n")

    return mapping

# ==============================================================================
# FUNÇÕES PRINCIPAIS (ADAPTADAS PARA USAR LOGGER)
# ==============================================================================

def action_extract():
    caminho = pick_file_topmost(t("select_binary_file"), [(t("binary_files"), "*.*")])

    if not caminho:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    logger(t("processing", name=os.path.basename(caminho)), color=COLOR_LOG_YELLOW)

    try:
        extract_encoding = get_option("extract_encoding")
        if extract_encoding is None:
            extract_encoding = "utf-8"  # fallback

        with open(caminho, "rb") as f:
            inicio_ponteiros = 0x14
            f.seek(24)
            inicio_textos = struct.unpack("<I", f.read(4))[0] + 25
            pointer_block_size = inicio_textos - inicio_ponteiros

            textos = []
            idx_logico = 1
            f.seek(inicio_ponteiros)
            pos_atual = f.tell()

            while pos_atual < inicio_textos:
                chunk = f.read(4)
                id_bin = struct.unpack("<I", chunk)[0]

                if id_bin == 0:
                    continue

                pos_atual = f.tell()
                if pos_atual >= inicio_textos:
                    break

                chunk_ptr = f.read(4)
                ponteiro_rel = struct.unpack("<I", chunk_ptr)[0]
                offset_texto = ponteiro_rel + pos_atual + 1
                pos_atual += 4

                f.seek(offset_texto)
                texto_bytes = bytearray()

                while True:
                    b = f.read(1)
                    if not b or b == b"\x00":
                        break
                    texto_bytes += b

                texto = decode_texto(bytes(texto_bytes), extract_encoding)
                texto = texto.replace("\r\n", "\\r\\n").replace("\n", "\\n")
                textos.append(f"==== Texto {idx_logico} ====\n{texto}")
                logger(t("log_extracting", idx=idx_logico), color=COLOR_LOG_YELLOW)
                idx_logico += 1
                f.seek(pos_atual)

        nome_saida = os.path.splitext(caminho)[0] + ".txt"
        with open(nome_saida, "w", encoding="utf-8", errors="ignore") as out:
            out.write("\n".join(textos))

        logger(t("extraction_completed", count=len(textos), path=nome_saida), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

def action_reinsert():
    caminho_bin = pick_file_topmost(t("select_dct_file"), [(t("dct_files"), "*.dct"), (t("all_files"), "*.*")])

    if not caminho_bin:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    caminho_txt = os.path.splitext(caminho_bin)[0] + ".txt"
    if not os.path.exists(caminho_txt):
        logger(t("txt_file_not_found", path=caminho_txt), color=COLOR_LOG_RED)
        return

    logger(t("processing", name=os.path.basename(caminho_bin)), color=COLOR_LOG_YELLOW)
    logger(t("recreating_to", path=caminho_txt), color=COLOR_LOG_YELLOW)

    try:
        reinsert_encoding = get_option("reinsert_encoding")
        if reinsert_encoding is None:
            reinsert_encoding = "cp1252"

        textos_map = ler_textos_do_txt(caminho_txt)
        textos_map = {int(k): v for k, v in textos_map.items()}
        inicio_ponteiros = 0x14

        with open(caminho_bin, "rb") as f:
            f.seek(24)
            inicio_textos = struct.unpack("<I", f.read(4))[0] + 25
            pointer_block_size = inicio_textos - inicio_ponteiros
            ponteiros = []
            f.seek(inicio_ponteiros)
            pos_atual = f.tell()

            while pos_atual < inicio_textos:
                id_bin = struct.unpack("<I", f.read(4))[0]
                if id_bin == 0:
                    continue
                entry_pos = f.tell()
                if entry_pos >= inicio_textos:
                    break
                ponteiro_rel = struct.unpack("<I", f.read(4))[0]
                ponteiros.append(entry_pos)
                pos_atual = f.tell()

            if not ponteiros:
                logger(t("no_valid_pointers"), color=COLOR_LOG_RED)
                return

        novo_nome = os.path.splitext(caminho_bin)[0] + "_MOD" + os.path.splitext(caminho_bin)[1]

        with open(caminho_bin, "rb") as src, open(novo_nome, "wb") as dst:
            src.seek(0)
            dst.write(src.read(inicio_textos))
            absolute_offsets = []
            cur_offset = inicio_textos

            for i in range(len(ponteiros)):
                absolute_offsets.append(cur_offset)
                texto = textos_map.get(i + 1, "")
                texto = texto.replace("\\r\\n", "\r\n").replace("\\n", "\n")
                texto_bytes = encode_texto(texto, reinsert_encoding) + b"\x00"
                dst.write(texto_bytes)
                cur_offset += len(texto_bytes)

        with open(novo_nome, "r+b") as f:
            for i, (entry_pos) in enumerate(ponteiros):
                absolute_offset = absolute_offsets[i]
                ponteiro_rel_new = absolute_offset - entry_pos - 1
                f.seek(entry_pos)
                f.write(struct.pack("<I", ponteiro_rel_new))

        logger(t("reinsertion_completed", count=len(ponteiros), path=novo_nome), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("unexpected_error", error=str(e)), color=COLOR_LOG_RED)

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
                "name": "extract_encoding",
                "label": t("extract_encoding"),
                "values": ["utf-8", "cp1252"]   # valores fixos em inglês
            },
            {
                "name": "reinsert_encoding",
                "label": t("reinsert_encoding"),
                "values": ["utf-8", "cp1252"]
            }
        ],
        "commands": [
            {"label": t("extract_texts"), "action": action_extract},
            {"label": t("reinsert_texts"), "action": action_reinsert},
        ]
    }