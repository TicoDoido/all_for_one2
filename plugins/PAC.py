import os
import struct
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "PAC Devil May Cry 3 SE (N. Switch)",
        "plugin_description": "Extrai e reconstrói arquivos PAC do DMC3 para Switch",
        "extract_pac": "Extrair PAC",
        "rebuild_pac": "Reconstruir PAC",
        "select_pac": "Selecione o arquivo .pac",
        "select_list": "Selecione o arquivo .txt de lista",
        "invalid_magic": "Magic incorreto (esperado 'PAC\\x00')",
        "extraction_success": "Extração finalizada em: {path}",
        "rebuild_success": "PAC reconstruído: {file}",
        "error": "Erro: {error}",
        "cancelled": "Cancelado.",
        "processing": "Processando: {name}...",
    },
    "en_US": {
        "plugin_name": "PAC Devil May Cry 3 SE (Switch)",
        "plugin_description": "Extracts and rebuilds PAC files from DMC3 Switch",
        "extract_pac": "Extract PAC",
        "rebuild_pac": "Rebuild PAC",
        "select_pac": "Select .pac file",
        "select_list": "Select .txt list file",
        "invalid_magic": "Invalid magic (expected 'PAC\\x00')",
        "extraction_success": "Extraction finished at: {path}",
        "rebuild_success": "PAC rebuilt: {file}",
        "error": "Error: {error}",
        "cancelled": "Cancelled.",
        "processing": "Processing: {name}...",
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
# LÓGICA DE MANIPULAÇÃO PAC
# ==============================================================================

def run_extraction(file_path):
    try:
        p = Path(file_path)
        logger(t("processing", name=p.name), color=COLOR_LOG_YELLOW)

        with p.open("rb") as f:
            if f.read(4) != b"PAC\x00":
                logger(t("invalid_magic"), color=COLOR_LOG_RED)
                return

            file_count = struct.unpack("<I", f.read(4))[0]
            pointers = [struct.unpack("<I", f.read(4))[0] for _ in range(file_count)]
            
            out_dir = p.parent / p.stem
            out_dir.mkdir(exist_ok=True)

            f.seek(0, 2)
            total_size = f.tell()
            file_names = []

            for i in range(file_count):
                start = pointers[i]
                end = pointers[i+1] if i < file_count - 1 else total_size
                f.seek(start)
                data = f.read(end - start)

                # Identificação básica de extensão
                ext = ".bin"
                if len(data) >= 3 and all(32 <= b < 127 for b in data[:3]):
                    try: ext = "." + data[:3].decode("ascii").strip().lower()
                    except: pass

                name = f"{i+1:04}{ext}"
                file_names.append(name)
                (out_dir / name).write_bytes(data)

            # Criar arquivo de lista para reconstrução
            (p.parent / f"{p.stem}.txt").write_text("\n".join(file_names), encoding="utf-8")

        logger(t("extraction_success", path=out_dir.name), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("error", error=str(e)), color=COLOR_LOG_RED)

def run_rebuild(list_path):
    try:
        lp = Path(list_path)
        folder = lp.parent / lp.stem
        if not folder.is_dir():
            logger(f"Pasta {folder.name} não encontrada.", color=COLOR_LOG_RED)
            return

        lines = [ln.strip() for ln in lp.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines: return

        logger(t("processing", name=lp.name), color=COLOR_LOG_YELLOW)
        
        file_datas = []
        for name in lines:
            f_path = folder / name
            file_datas.append(f_path.read_bytes())

        out_pac = lp.parent / f"{lp.stem}_mod.pac"
        
        # Cabeçalho: Magic(4) + Count(4) + Pointers(4*count)
        base_offset = 8 + (4 * len(lines))
        pointers = []
        curr = base_offset
        for d in file_datas:
            pointers.append(curr)
            curr += len(d)

        with out_pac.open("wb") as out:
            out.write(b"PAC\x00")
            out.write(struct.pack("<I", len(lines)))
            for p in pointers:
                out.write(struct.pack("<I", p))
            for data in file_datas:
                out.write(data)

        logger(t("rebuild_success", file=out_pac.name), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# REGISTRO DO PLUGIN (FLET)
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR"):
    global logger, current_lang
    logger = log_func
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
                "label": t("extract_pac"), 
                "action": lambda: fp_extract.pick_files(
                    allow_multiple=True, 
                    allowed_extensions=["pac"]
                )
            },
            {
                "label": t("rebuild_pac"), 
                "action": lambda: fp_rebuild.pick_files(
                    allow_multiple=True, 
                    allowed_extensions=["txt"]
                )
            },
        ]
    }