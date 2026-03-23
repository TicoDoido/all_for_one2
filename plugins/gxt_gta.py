import os
import struct
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "GXT de texto GTA 4",
        "plugin_description": "Extrai e recria textos de arquivos .GXT (GTA 4)",
        "extract_file": "Extrair (GXT → TXT)",
        "rebuild_file": "Recriar (TXT → GXT)",
        "success": "Sucesso",
        "extraction_success": "Textos salvos em: {path}",
        "recreation_success": "GXT reconstruído com sucesso",
        "error": "Erro: {error}",
        "detected_endian": "Endianness: {endian}",
        "invalid_header": "Cabeçalho GXT inválido",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
    },
    "en_US": {
        "plugin_name": "GXT Text GTA 4",
        "plugin_description": "Extracts and rebuilds text from .GXT files (GTA 4)",
        "extract_file": "Extract (GXT → TXT)",
        "rebuild_file": "Rebuild (TXT → GXT)",
        "success": "Success",
        "extraction_success": "Texts saved to: {path}",
        "recreation_success": "GXT successfully rebuilt",
        "error": "Error: {error}",
        "detected_endian": "Endianness: {endian}",
        "invalid_header": "Invalid GXT header",
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
# FUNÇÕES AUXILIARES E LÓGICA GXT
# ==============================================================================

def get_endian(path: Path):
    with path.open('rb') as f:
        header = f.read(2)
        if struct.unpack('>H', header)[0] == 4: return '>'
        if struct.unpack('<H', header)[0] == 4: return '<'
    raise ValueError(t("invalid_header"))

def run_extraction(filepath):
    try:
        path = Path(filepath)
        endian = get_endian(path)
        logger(t("processing", name=path.name), color=COLOR_LOG_YELLOW)

        with path.open('rb') as f:
            f.seek(8)
            val1 = struct.unpack(endian + 'I', f.read(4))[0]
            ptr_count = val1 // 8
            
            ptrs = []
            for _ in range(ptr_count):
                ptr = struct.unpack(endian + 'I', f.read(4))[0]
                f.seek(4, 1) # Skip unknown
                ptrs.append(20 + ptr + val1)

            blocks = []
            for pos in ptrs:
                f.seek(pos)
                txt = bytearray()
                while (b := f.read(1)) != b'\x00' and b:
                    txt += b
                
                # Tratamento de TAB e marcador de fim de bloco
                processed = txt.replace(b'\x09', b'[TAB]')
                blocks.append(processed.decode('ansi', errors='replace') + "[FIM]")

        out_txt = path.with_suffix('.txt')
        out_txt.write_text("\n".join(blocks), encoding='utf-8')
        logger(t("extraction_success", path=out_txt.name), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("error", error=str(e)), color=COLOR_LOG_RED)

def run_rebuild(txt_filepath):
    try:
        txt_path = Path(txt_filepath)
        gxt_path = txt_path.with_suffix('.GXT')
        
        if not gxt_path.exists():
            raise FileNotFoundError(f"GXT original não encontrado para {txt_path.name}")
            
        endian = get_endian(gxt_path)
        logger(t("processing", name=txt_path.name), color=COLOR_LOG_YELLOW)

        # Ler TXT e separar blocos
        raw_content = txt_path.read_text(encoding='utf-8')
        blocks = [b.replace("[TAB]", "\t") for b in raw_content.split("[FIM]\n")]
        if blocks and not blocks[-1].strip(): blocks.pop() # Remove última linha vazia

        with gxt_path.open('r+b') as f:
            f.seek(8)
            val1 = struct.unpack(endian + 'I', f.read(4))[0]
            text_start = 20 + val1

            # Escrever blocos e coletar offsets
            f.seek(text_start)
            new_ptrs = []
            for b in blocks:
                new_ptrs.append(f.tell() - text_start)
                f.write(b.encode('ansi', errors='replace') + b'\x00')
            
            f.truncate() # Limpa lixo residual se o arquivo diminuir

            # Atualizar ponteiros na tabela
            f.seek(12)
            for ptr in new_ptrs:
                f.write(struct.pack(endian + 'I', ptr))
                f.seek(4, 1)

        logger(t("recreation_success"), color=COLOR_LOG_GREEN)
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

    def on_extract_res(e: ft.FilePickerResultEvent):
        if e.files:
            for f in e.files: run_extraction(f.path)
        else: logger(t("cancelled"), color=COLOR_LOG_YELLOW)

    def on_rebuild_res(e: ft.FilePickerResultEvent):
        if e.files:
            for f in e.files: run_rebuild(f.path)
        else: logger(t("cancelled"), color=COLOR_LOG_YELLOW)

    fp_extract = ft.FilePicker(on_result=on_extract_res)
    fp_rebuild = ft.FilePicker(on_result=on_rebuild_res)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "pickers": [fp_extract, fp_rebuild],
        "commands": [
            {
                "label": t("extract_file"), 
                "action": lambda: fp_extract.pick_files(
                allowed_extensions=["gxt"]
                )
            },
            {
                "label": t("rebuild_file"), 
                "action": lambda: fp_rebuild.pick_files(
                allowed_extensions=["txt"]
                )
            },
        ]
    }