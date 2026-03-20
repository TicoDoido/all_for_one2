import os
import struct
import time
import flet as ft
from pathlib import Path

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "Extrator DAT+HD2 (Dark Cloud PS2)",
        "plugin_description": "Extrai pares .hd2 + .dat de jogos PS2 (Dark Cloud)",
        "extract_cmd": "Extrair DAT+HD2",
        "select_hd2": "Selecione o arquivo .hd2",
        "error_dat": "Arquivo DAT não encontrado: {path}",
        "error_hd2": "HD2 inválido ou curto.",
        "log_files": "Arquivos detectados: {count}",
        "log_extracting": "[{i}] {name} ({size} bytes)",
        "success": "Extração concluída em: {folder}",
        "cancelled": "Seleção cancelada.",
    },
    "en_US": {
        "plugin_name": "DAT+HD2 Extractor (Dark Cloud)",
        "plugin_description": "Extracts .hd2 + .dat pairs from Dark Cloud (PS2)",
        "extract_cmd": "Extract DAT+HD2",
        "select_hd2": "Select .hd2 file",
        "error_dat": "DAT file not found: {path}",
        "error_hd2": "Invalid or short HD2.",
        "log_files": "Files detected: {count}",
        "log_extracting": "[{i}] {name} ({size} bytes)",
        "success": "Extraction finished in: {folder}",
        "cancelled": "Selection cancelled.",
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

logger = None
current_lang = "pt_BR"

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# BACKEND DE EXTRAÇÃO
# ==============================================================================

def get_str(f, offset):
    old_pos = f.tell()
    f.seek(offset)
    res = bytearray()
    while (b := f.read(1)) != b"\x00" and b:
        res += b
    f.seek(old_pos)
    return res.decode("shift-jis", errors="ignore")

def start_extraction(hd2_path):
    try:
        hd2_p = Path(hd2_path)
        dat_p = hd2_p.with_suffix('.dat')

        if not dat_p.exists():
            logger(t("error_dat", path=dat_p.name), color=COLOR_LOG_RED)
            return

        out_dir = hd2_p.parent / hd2_p.stem
        out_dir.mkdir(exist_ok=True)

        with open(hd2_p, "rb") as hd2:
            h_size = struct.unpack("<I", hd2.read(4))[0]
            entries = h_size // 32
            logger(t("log_files", count=entries), color=COLOR_LOG_YELLOW)

            hd2.seek(0)
            with open(dat_p, "rb") as dat:
                for i in range(entries):
                    data = hd2.read(32)
                    if len(data) < 32: break

                    name_off = struct.unpack("<I", data[0:4])[0]
                    off = struct.unpack("<I", data[16:20])[0]
                    size = struct.unpack("<I", data[20:24])[0]
                    name = get_str(hd2, name_off)

                    if i % 100 == 0: # Log a cada 100 para performance
                        logger(t("log_extracting", i=i, name=name, size=size))

                    if size > 0:
                        dat.seek(off)
                        payload = dat.read(size)
                        target = out_dir / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(payload)

        logger(t("success", folder=out_dir.name), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(f"Erro: {str(e)}", color=COLOR_LOG_RED)

# ==============================================================================
# PLUGIN REGISTRATION
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR"):
    global logger, current_lang
    logger = log_func
    current_lang = host_language

    def on_res(e: ft.FilePickerResultEvent):
        if e.files:
            # Recomendo disparar em uma thread se o seu Manager suportar, 
            # ou apenas chamar diretamente se for rodar scripts pequenos.
            start_extraction(e.files[0].path)
        else:
            logger(t("cancelled"), color=COLOR_LOG_YELLOW)

    picker = ft.FilePicker(on_result=on_res)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "pickers": [picker], # O Manager deve adicionar isso à page.overlay
        "commands": [
            {
                "label": t("extract_cmd"), 
                "action": lambda: picker.pick_files(
                    dialog_title=t("select_hd2"),
                    allowed_extensions=["hd2"]
                )
            },
        ]
    }