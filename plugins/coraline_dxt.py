import os
import traceback
from pathlib import Path
from struct import unpack
from collections import OrderedDict

# Verificação segura da biblioteca Pillow
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

HEADER_SIZE = 0x80

# ==============================================================================
# TRADUÇÕES DO PLUGIN
# ==============================================================================
STRINGS = {
    "pt_BR": {
        "name": "Coraline (Wii) - DXT ↔ PNG",
        "desc": "Extrai texturas .dxt para .png e injeta .png de volta no formato .dxt.",
        "folder": "Pasta dos Arquivos",
        "subfolders": "Incluir Subpastas",
        "yes": "Sim",
        "no": "Não",
        "btn_unpack": "Converter DXT para PNG",
        "btn_pack": "Converter PNG para DXT",
        "no_folder": "Selecione uma pasta válida nas configurações.",
        "no_pil": "Erro fatal: A biblioteca 'Pillow' não está instalada.\nAbra o terminal e digite: pip install Pillow",
        "start_unpack": "Procurando arquivos .dxt em: {path}...",
        "start_pack": "Procurando arquivos .dxt.png em: {path}...",
        "found": "{count} arquivo(s) encontrado(s).",
        "success": "Concluído: {src} -> {dst}",
        "err_colors": "Erro: Cores demais na imagem '{file}'! O limite é 256 cores indexadas.",
        "err_base": "Erro: Arquivo original '{base}' não encontrado. Ele é necessário para injetar o PNG.",
        "err_generic": "Erro ao processar '{file}': {err}",
        "finished": "Processo concluído com sucesso!"
    },
    "en_US": {
        "name": "Coraline (Wii) - DXT ↔ PNG",
        "desc": "Unpack .dxt textures to .png and pack .png back to .dxt format.",
        "folder": "Files Folder",
        "subfolders": "Include Subfolders",
        "yes": "Yes",
        "no": "No",
        "btn_unpack": "Convert DXT to PNG",
        "btn_pack": "Convert PNG to DXT",
        "no_folder": "Please select a valid folder in the settings.",
        "no_pil": "Fatal error: 'Pillow' library is missing.\nOpen terminal and run: pip install Pillow",
        "start_unpack": "Searching for .dxt files in: {path}...",
        "start_pack": "Searching for .dxt.png files in: {path}...",
        "found": "{count} file(s) found.",
        "success": "Success: {src} -> {dst}",
        "err_colors": "Error: Too many colors in '{file}'! Max allowed is 256 indexed colors.",
        "err_base": "Error: Original base file '{base}' not found. It is required to pack the PNG.",
        "err_generic": "Error processing '{file}': {err}",
        "finished": "Process finished successfully!"
    },
    "es_ES": {
        "name": "Coraline (Wii) - DXT ↔ PNG",
        "desc": "Extrae texturas .dxt a .png e inyecta .png de vuelta al formato .dxt.",
        "folder": "Carpeta de Archivos",
        "subfolders": "Incluir Subcarpetas",
        "yes": "Sí",
        "no": "No",
        "btn_unpack": "Convertir DXT a PNG",
        "btn_pack": "Convertir PNG a DXT",
        "no_folder": "Seleccione una carpeta válida en la configuración.",
        "no_pil": "Error fatal: Falta la biblioteca 'Pillow'.\nAbra la terminal y ejecute: pip install Pillow",
        "start_unpack": "Buscando archivos .dxt en: {path}...",
        "start_pack": "Buscando archivos .dxt.png en: {path}...",
        "found": "{count} archivo(s) encontrado(s).",
        "success": "Éxito: {src} -> {dst}",
        "err_colors": "Error: ¡Demasiados colores en '{file}'! El máximo permitido es 256 colores.",
        "err_base": "Error: Archivo original '{base}' no encontrado. Es necesario para inyectar el PNG.",
        "err_generic": "Error al procesar '{file}': {err}",
        "finished": "¡Proceso terminado con éxito!"
    }
}

# ==============================================================================
# LÓGICA CORE DO SCRIPT ORIGINAL
# ==============================================================================
class Texture:
    """[Wii] Color Index 8-bits (C8) + Palette RGBA8"""
    def __init__(self, path, offset, w, h, pal_offset):
        self.path = str(path)
        self.offset = offset
        self.w = w
        self.h = h
        self.pal_offset = pal_offset

    def to_png(self, png_path):
        im = Image.new("RGBA", (self.w, self.h))
        pixels = im.load()

        with open(self.path, "rb") as f:
            f.seek(self.offset)
            b = f.read(self.w * self.h)

            f.seek(self.pal_offset)
            b_pal = f.read(256 * 4)

            pal = []
            for i in range(256):
                index = i * 2
                pal.append((b_pal[index+1],        # R
                            b_pal[index+0],        # G
                            b_pal[index+1+0x200],  # B
                            b_pal[index+0+0x200])) # A

            tw, th = 8, 4
            bytes_in_tile = tw * th
            bytes_in_row = self.w * th

            x, y = 0, 0
            for i in range(self.w * self.h):
                index = i // bytes_in_row * bytes_in_row
                index += x // tw * bytes_in_tile
                index += (y % th) * tw + x % tw

                c = b[index]
                pixels[x, y] = pal[c]
                x += 1
                if x == self.w:
                    x = 0
                    y += 1

        im.save(str(png_path), "PNG")

    def from_png(self, bin_path, base_path=None):
        im = Image.open(self.path).convert("RGBA")
        pixels = im.load()
        self.w, self.h = im.size

        if not base_path:
            self.offset = 0
            self.pal_offset = self.w * self.h
            b = bytearray(self.w * self.h + 256 * 4)
        else:
            with open(str(base_path), "rb") as f:
                b = bytearray(f.read())

        pal = OrderedDict()
        pal_i = 0
        b_img = bytearray(self.w * self.h)

        tw, th = 8, 4
        bytes_in_tile = tw * th
        bytes_in_row = self.w * th

        i = 0
        for y in range(self.h):
            for x in range(self.w):
                c = pixels[x, y]
                if c not in pal:
                    if len(pal) >= 256:
                        raise ValueError("TOO_MANY_COLORS")
                    else:
                        pal[c] = pal_i
                        pal_i += 1

                index = i // bytes_in_row * bytes_in_row
                index += x // tw * bytes_in_tile
                index += (y % th) * tw + x % tw

                b_img[index] = pal[c]
                i += 1

        b[self.offset: self.offset + self.w * self.h] = b_img

        pal_list = list(pal.keys())
        pal_list += [(0, 0, 0, 0)] * (256 - len(pal_list)) # Unused colors

        for i in range(256):
            index1 = self.pal_offset + i * 2
            index2 = self.pal_offset + i * 2 + 0x200
            cR, cG, cB, cA = pal_list[i]
            b[index2+0] = cA
            b[index2+1] = cB
            b[index1+0] = cG
            b[index1+1] = cR

        with open(str(bin_path), "wb") as f:
            f.write(b)

def dxt_to_png(path):
    with open(str(path), "rb") as f:
        f.seek(0x0A)
        w, h = unpack("<BB", f.read(2))
        w = 1 << w
        h = 1 << h
    png_path = path.with_name(path.name + ".png")
    Texture(path, HEADER_SIZE, w, h, HEADER_SIZE + w * h).to_png(png_path)
    return png_path

def png_to_dxt(path):
    bin_path = path.with_suffix('') # Remove .png
    if not bin_path.exists():
        raise FileNotFoundError("MISSING_BASE")
        
    with open(str(bin_path), "rb") as f:
        f.seek(0x0A)
        w, h = unpack("<BB", f.read(2))
        w = 1 << w
        h = 1 << h
    Texture(path, HEADER_SIZE, None, None, HEADER_SIZE + w * h).from_png(bin_path, bin_path)
    return bin_path

# ==============================================================================
# INTEGRAÇÃO COM ALL FOR ONE
# ==============================================================================
def execute_unpack(log, get_opt, t):
    if not HAS_PIL:
        log(t("no_pil"), color="#EF4444")
        return

    folder = get_opt("folder")
    if not folder or not os.path.isdir(folder):
        log(t("no_folder"), color="#FACC15")
        return

    subfolders = get_opt("subfolders") == t("yes")
    base_path = Path(folder)
    
    log(t("start_unpack", path=folder))
    pattern = "**/*.dxt" if subfolders else "*.dxt"
    files = list(base_path.glob(pattern))

    if not files:
        log(t("found", count=0), color="#FACC15")
        return

    log(t("found", count=len(files)))
    for p in files:
        try:
            png_path = dxt_to_png(p)
            log(t("success", src=p.name, dst=png_path.name))
        except Exception as e:
            log(t("err_generic", file=p.name, err=str(e)), color="#EF4444")
            traceback.print_exc()

    log(t("finished"), color="#4ADE80")


def execute_pack(log, get_opt, t):
    if not HAS_PIL:
        log(t("no_pil"), color="#EF4444")
        return

    folder = get_opt("folder")
    if not folder or not os.path.isdir(folder):
        log(t("no_folder"), color="#FACC15")
        return

    subfolders = get_opt("subfolders") == t("yes")
    base_path = Path(folder)
    
    log(t("start_pack", path=folder))
    pattern = "**/*.dxt.png" if subfolders else "*.dxt.png"
    files = list(base_path.glob(pattern))

    if not files:
        log(t("found", count=0), color="#FACC15")
        return

    log(t("found", count=len(files)))
    for p in files:
        try:
            bin_path = png_to_dxt(p)
            log(t("success", src=p.name, dst=bin_path.name))
        except ValueError as ve:
            if str(ve) == "TOO_MANY_COLORS":
                log(t("err_colors", file=p.name), color="#EF4444")
            else:
                log(t("err_generic", file=p.name, err=str(ve)), color="#EF4444")
        except FileNotFoundError as fnf:
            if str(fnf) == "MISSING_BASE":
                # Para empacotar, o DXT original precisa estar junto do PNG na mesma pasta
                base_name = p.name.replace(".png", "")
                log(t("err_base", base=base_name), color="#EF4444")
        except Exception as e:
            log(t("err_generic", file=p.name, err=str(e)), color="#EF4444")
            traceback.print_exc()

    log(t("finished"), color="#4ADE80")


def register_plugin(log_callback, get_opt, language, page=None):
    # Helper para tradução dentro do plugin
    def t(key, **kwargs):
        txt = STRINGS.get(language, STRINGS["pt_BR"]).get(key, key)
        return txt.format(**kwargs) if kwargs else txt

    return {
        "name": t("name"),
        "description": t("desc"),
        "options": [
            {
                "name": "folder",
                "type": "folder",
                "label": t("folder")
            },
            {
                "name": "subfolders",
                "type": "dropdown",
                "label": t("subfolders"),
                "values": [t("yes"), t("no")],
                "default": t("yes")
            }
        ],
        "commands": [
            {
                "label": t("btn_unpack"),
                "action": lambda: execute_unpack(log_callback, get_opt, t)
            },
            {
                "label": t("btn_pack"),
                "action": lambda: execute_pack(log_callback, get_opt, t)
            }
        ]
    }