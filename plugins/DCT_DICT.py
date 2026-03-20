import os
import re
import struct
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "DCT/DICT - Extrator e Reinseridor",
        "plugin_description": "Extrai e reinsere textos de arquivos DCT/DICT usando ponteiros relativos.",
        "extract_texts": "Extrair Textos",
        "reinsert_texts": "Reinserir Textos",
        "select_file": "Selecione o arquivo DCT",
        "extraction_completed": "Extração finalizada! {count} textos extraídos.",
        "reinsertion_completed": "Reinserção concluída! {count} ponteiros atualizados.",
        "txt_file_not_found": "Arquivo TXT não encontrado.",
        "extract_encoding": "Codificação de Extração",
        "reinsert_encoding": "Codificação de Reinserção",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "log_extracting": "Lendo bloco {idx}..."
    },
    "en_US": {
        "plugin_name": "DCT/DICT - Extractor & Reinserter",
        "plugin_description": "Extracts and reinserts texts from DCT/DICT files using relative pointers.",
        "extract_texts": "Extract Texts",
        "reinsert_texts": "Reinsert Texts",
        "select_file": "Select DCT file",
        "extraction_completed": "Extraction finished! {count} texts extracted.",
        "reinsertion_completed": "Reinsertion finished! {count} pointers updated.",
        "txt_file_not_found": "TXT file not found.",
        "extract_encoding": "Extraction Encoding",
        "reinsert_encoding": "Reinsertion Encoding",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "log_extracting": "Reading block {idx}..."
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
# LÓGICA DE TRATAMENTO DE TEXTO
# ==============================================================================

def ler_textos_do_txt(caminho_txt):
    if not os.path.exists(caminho_txt): return {}
    with open(caminho_txt, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    pattern = re.compile(r"====\s*Texto\s*(\d+)\s*====\s*\r?\n", re.IGNORECASE)
    parts = []
    mapping = {}

    for m in pattern.finditer(content):
        idx = int(m.group(1))
        if parts:
            prev_idx, prev_start = parts[-1]
            mapping[prev_idx] = content[prev_start:m.start()].rstrip("\r\n")
        parts.append((idx, m.end()))

    if parts:
        last_idx, last_pos = parts[-1]
        mapping[last_idx] = content[last_pos:].rstrip("\r\n")
    return mapping

# ==============================================================================
# FUNÇÕES DE EXECUÇÃO
# ==============================================================================

def run_extract(caminho):
    try:
        encoding = get_option("extract_encoding") or "utf-8"
        with open(caminho, "rb") as f:
            f.seek(24)
            inicio_textos = struct.unpack("<I", f.read(4))[0] + 25
            
            textos = []
            idx = 1
            f.seek(0x14) # Início do bloco de ponteiros
            
            while f.tell() < inicio_textos:
                id_bin = struct.unpack("<I", f.read(4))[0]
                if id_bin == 0: continue
                
                pos_ponteiro = f.tell()
                if pos_ponteiro >= inicio_textos: break
                
                ponteiro_rel = struct.unpack("<I", f.read(4))[0]
                offset_texto = ponteiro_rel + pos_ponteiro + 1
                pos_retorno = f.tell()

                f.seek(offset_texto)
                buffer = bytearray()
                while True:
                    b = f.read(1)
                    if not b or b == b"\x00": break
                    buffer += b
                
                texto = buffer.decode(encoding, errors="ignore").replace("\n", "\\n")
                textos.append(f"==== Texto {idx} ====\n{texto}")
                logger(t("log_extracting", idx=idx))
                idx += 1
                f.seek(pos_retorno)

        out_path = os.path.splitext(caminho)[0] + ".txt"
        with open(out_path, "w", encoding="utf-8") as out:
            out.write("\n".join(textos))
        
        logger(t("extraction_completed", count=len(textos)), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(str(e), color=COLOR_LOG_RED)

def run_reinsert(caminho_bin):
    try:
        caminho_txt = os.path.splitext(caminho_bin)[0] + ".txt"
        if not os.path.exists(caminho_txt):
            logger(t("txt_file_not_found"), color=COLOR_LOG_RED)
            return

        encoding = get_option("reinsert_encoding") or "cp1252"
        textos_map = ler_textos_do_txt(caminho_txt)
        ponteiros = []

        with open(caminho_bin, "rb") as f:
            f.seek(24)
            inicio_textos = struct.unpack("<I", f.read(4))[0] + 25
            f.seek(0x14)
            while f.tell() < inicio_textos:
                id_bin = struct.unpack("<I", f.read(4))[0]
                if id_bin == 0: continue
                entry_pos = f.tell()
                if entry_pos >= inicio_textos: break
                f.read(4) # Pula ponteiro original
                ponteiros.append(entry_pos)

        novo_nome = os.path.splitext(caminho_bin)[0] + "_MOD.dct"
        with open(caminho_bin, "rb") as src, open(novo_nome, "wb") as dst:
            dst.write(src.read(inicio_textos))
            new_offsets = []
            
            for i in range(len(ponteiros)):
                texto = textos_map.get(i + 1, "").replace("\\n", "\n")
                encoded = texto.encode(encoding, errors="ignore") + b"\x00"
                new_offsets.append(dst.tell())
                dst.write(encoded)

        # Atualização dos ponteiros relativos
        with open(novo_nome, "r+b") as f:
            for i, entry_pos in enumerate(ponteiros):
                rel_val = new_offsets[i] - entry_pos - 1
                f.seek(entry_pos)
                f.write(struct.pack("<I", rel_val))

        logger(t("reinsertion_completed", count=len(ponteiros)), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(str(e), color=COLOR_LOG_RED)

# ==============================================================================
# REGISTRO
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR"):
    global logger, get_option, current_lang
    logger = log_func
    get_option = option_getter
    current_lang = host_language

    fp_ext = ft.FilePicker(on_result=lambda e: run_extract(e.files[0].path) if e.files else None)
    fp_ins = ft.FilePicker(on_result=lambda e: run_reinsert(e.files[0].path) if e.files else None)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "pickers": [fp_ext, fp_ins],
        "options": [
            {"name": "extract_encoding", "label": t("extract_encoding"), "values": ["utf-8", "cp1252"]},
            {"name": "reinsert_encoding", "label": t("reinsert_encoding"), "values": ["utf-8", "cp1252"]}
        ],
        "commands": [
            {"label": t("extract_texts"), "action": lambda: fp_ext.pick_files()},
            {"label": t("reinsert_texts"), "action": lambda: fp_ins.pick_files(allowed_extensions=["dct"])}
        ]
    }