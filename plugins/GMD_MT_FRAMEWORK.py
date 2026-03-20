import os
import struct
import re
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "GMD Arquivos de texto MT Framework (RE6)",
        "plugin_description": "Extrai e reinsere textos de arquivos GMD (Resident Evil 6)",
        "extract_texts": "Extrair Textos (GMD → TXT)",
        "insert_texts": "Reinserir Textos (TXT → GMD)",
        "success": "Sucesso",
        "extraction_success": "Textos salvos em: {path}",
        "insertion_success": "Textos reinseridos no arquivo GMD",
        "error": "Erro: {error}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
    },
    "en_US": {
        "plugin_name": "GMD Text MT Framework (RE6)",
        "plugin_description": "Extracts and reinserts texts from GMD files (Resident Evil 6)",
        "extract_texts": "Extract Texts",
        "insert_texts": "Insert Texts",
        "success": "Success",
        "extraction_success": "Texts saved to: {path}",
        "insertion_success": "Texts reinserted into GMD file",
        "error": "Error: {error}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
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
# LÓGICA DE MANIPULAÇÃO GMD
# ==============================================================================

def run_extraction(gmd_path):
    try:
        p = Path(gmd_path)
        logger(t("processing", name=p.name), color=COLOR_LOG_YELLOW)
        
        with p.open('rb') as f:
            f.seek(20)
            ptr_count = struct.unpack('<I', f.read(4))[0]
            ptr_table_end = (ptr_count * 4) + 28

            valid_ptrs = []
            for _ in range(ptr_count):
                raw = f.read(4)
                if raw != b'\xFF\xFF\xFF\xFF':
                    valid_ptrs.append(struct.unpack('<I', raw)[0])

            texts = []
            for ptr in valid_ptrs:
                f.seek(ptr_table_end + ptr)
                text_bytes = bytearray()
                while (b := f.read(1)) != b'\x00' and b:
                    text_bytes += b
                texts.append(text_bytes.decode('utf-8', errors='replace'))

        out_txt = p.with_suffix('.txt')
        with out_txt.open('w', encoding='utf-8') as f_out:
            for txt in texts:
                f_out.write(txt.replace("\r\n", "[BR]") + "[END]\n")
        
        logger(t("extraction_success", path=out_txt.name), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("error", error=str(e)), color=COLOR_LOG_RED)

def run_insertion(gmd_path):
    try:
        p = Path(gmd_path)
        txt_path = p.with_suffix('.txt')
        if not txt_path.exists():
            raise FileNotFoundError(f"Arquivo {txt_path.name} não encontrado.")

        logger(t("processing", name=p.name), color=COLOR_LOG_YELLOW)

        # Carregar textos do TXT
        content = txt_path.read_text(encoding='utf-8')
        texts = [txt.replace("[BR]", "\r\n") for txt in content.split("[END]\n") if txt.strip()]

        with p.open('r+b') as f:
            f.seek(20)
            ptr_count = struct.unpack('<I', f.read(4))[0]
            ptr_table_end = (ptr_count * 4) + 28

            # Mapear posições dos ponteiros válidos
            f.seek(24)
            valid_ptr_pos = []
            for _ in range(ptr_count):
                curr_pos = f.tell()
                if f.read(4) != b'\xFF\xFF\xFF\xFF':
                    valid_ptr_pos.append(curr_pos)

            # Escrever novos textos
            f.seek(ptr_table_end)
            offsets = []
            for txt in texts:
                offsets.append(f.tell() - ptr_table_end)
                f.write(txt.encode('utf-8') + b'\x00')

            # Atualizar Header (tamanho dos dados)
            final_size = f.tell()
            f.seek(ptr_table_end - 4)
            f.write(struct.pack('<I', final_size - ptr_table_end))

            # Atualizar Ponteiros
            for i, pos in enumerate(valid_ptr_pos):
                if i < len(offsets):
                    f.seek(pos)
                    f.write(struct.pack('<I', offsets[i]))

        logger(t("insertion_success"), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# REGISTRO DO PLUGIN (FLET)
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR"):
    global logger, get_option, current_lang
    logger = log_func
    get_option = option_getter
    current_lang = host_language

    # Handlers para os Pickers
    def on_extract_result(e: ft.FilePickerResultEvent):
        if e.files:
            for f in e.files: run_extraction(f.path)
        else:
            logger(t("cancelled"), color=COLOR_LOG_YELLOW)

    def on_insert_result(e: ft.FilePickerResultEvent):
        if e.files:
            for f in e.files: run_insertion(f.path)
        else:
            logger(t("cancelled"), color=COLOR_LOG_YELLOW)

    # Instanciar Pickers
    fp_extract = ft.FilePicker(on_result=on_extract_result)
    fp_insert = ft.FilePicker(on_result=on_insert_result)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "pickers": [fp_extract, fp_insert], # Essencial para o PATCHER_V2 registrar na page.overlay
        "commands": [
            {
                "label": t("extract_texts"), 
                "action": lambda: fp_extract.pick_files(
                    allow_multiple=True, 
                    allowed_extensions=["gmd"]
                )
            },
            {
                "label": t("insert_texts"), 
                "action": lambda: fp_insert.pick_files(
                    allow_multiple=True, 
                    allowed_extensions=["gmd"]
                )
            },
        ]
    }