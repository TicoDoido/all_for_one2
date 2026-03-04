import os
import struct
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "XUS Tools (Xbox 360)",
        "plugin_description": "Converte .xus para XML e reconverte de volta. Corrige janelas em segundo plano.",
        "extract_text": "Extrair XUS -> XML",
        "rebuild_file": "Recriar XML -> XUS",
        "success_extract": "XML salvo em: {path}",
        "success_rebuild": "XUS salvo em: {path}",
        "processing": "Processando: {name}...",
        "select_xus": "Selecione o arquivo .xus",
        "select_xml": "Selecione o arquivo .xml",
        "error_magic": "Magic number inválido ou arquivo corrompido.",
        "error_generic": "Erro: {error}",
        "cancelled": "Seleção cancelada."
    },
    "en_US": {
        "plugin_name": "XUS Tools (Xbox 360)",
        "plugin_description": "Converts .xus to XML and back. Fixes background window issues.",
        "extract_text": "Extract XUS -> XML",
        "rebuild_file": "Rebuild XML -> XUS",
        "success_extract": "XML saved at: {path}",
        "success_rebuild": "XUS saved at: {path}",
        "processing": "Processing: {name}...",
        "select_xus": "Select .xus file",
        "select_xml": "Select .xml file",
        "error_magic": "Invalid magic number.",
        "error_generic": "Error: {error}",
        "cancelled": "Selection cancelled."
    },
    "es_ES": {
        "plugin_name": "Herramientas XUS (Xbox 360)",
        "plugin_description": "Convierte .xus a XML y viceversa. Arregla ventanas en segundo plano.",
        "extract_text": "Extraer XUS -> XML",
        "rebuild_file": "Reconstruir XML -> XUS",
        "success_extract": "XML guardado en: {path}",
        "success_rebuild": "XUS guardado en: {path}",
        "processing": "Procesando: {name}...",
        "select_xus": "Seleccionar archivo .xus",
        "select_xml": "Seleccionar archivo .xml",
        "error_magic": "Número mágico inválido.",
        "error_generic": "Error: {error}",
        "cancelled": "Selección cancelada."
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
    root.withdraw() # Esconde a janela principal feia do tk
    root.wm_attributes('-topmost', 1) # FORÇA FICAR NA FRENTE DE TUDO
    
    file_path = filedialog.askopenfilename(
        parent=root,
        title=title, 
        filetypes=file_types
    )
    
    root.destroy() # Limpa a memória do tk
    return file_path

# ==============================================================================
# LÓGICA DE NEGÓCIO (CONVERSÃO)
# ==============================================================================

def get_magic_number_from_xus(file_path):
    with open(file_path, 'rb') as file:
        return file.read(6)

def action_extract_xus():
    path = pick_file_topmost(t("select_xus"), [("XUS Files", "*.xus")])
    
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    output_xml_path = path.rsplit('.', 1)[0] + '.xml'
    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)

    try:
        with open(path, 'rb') as file:
            magic_number = file.read(6)
            valid_magic = [b'XUIS\x01\x02', b'XUIS\x01\x00']
            if magic_number not in valid_magic:
                raise ValueError(t("error_magic"))

            file.seek(10)
            num_items = struct.unpack('>H', file.read(2))[0]
            if magic_number == b'XUIS\x01\x00':
                num_items *= 2

            root = ET.Element("Root")
            for i in range(num_items):
                count = struct.unpack('>H', file.read(2))[0]
                text = file.read(count * 2).decode('utf-16-be').replace('\r\n', '[0D0A]')
                item = ET.Element(f"Item_{i+1}")
                item.text = text
                root.append(item)

        xml_str = ET.tostring(root, encoding='unicode', method='xml')
        xml_str = '\n' + xml_str.replace('><', '>\n<') + '\n'

        with open(output_xml_path, 'w', encoding='utf-8') as out:
            out.write(xml_str)

        logger(t("success_extract", path=os.path.basename(output_xml_path)), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("error_generic", error=str(e)), color=COLOR_LOG_RED)

def action_rebuild_xus():
    path = pick_file_topmost(t("select_xml"), [("XML Files", "*.xml")])
    
    if not path:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)
        return

    # Tenta achar o arquivo original para pegar o magic number, senão usa padrão
    original_guess = path.rsplit('.', 1)[0] + '.xus'
    output_xus_path = path.rsplit('.', 1)[0] + '_new.xus'
    
    logger(t("processing", name=os.path.basename(path)), color=COLOR_LOG_YELLOW)

    try:
        new_magic = b'XUIS\x01\x02' # Padrão
        if os.path.exists(original_guess):
            original_magic = get_magic_number_from_xus(original_guess)
            if original_magic == b'XUIS\x01\x00':
                new_magic = b'XUIS\x01\x00'

        tree = ET.parse(path)
        root = tree.getroot()
        items_data = []

        for item in root:
            text = (item.text or '').replace('[0D0A]', '\r\n')
            text_bytes = text.encode('utf-16-be')
            count = len(text_bytes) // 2
            items_data.append(struct.pack('>H', count) + text_bytes)

        num_items = len(items_data)
        if new_magic == b'XUIS\x01\x00':
            num_items //= 2

        with open(output_xus_path, 'wb+') as file:
            file.write(new_magic)
            file.seek(10)
            file.write(struct.pack('>H', num_items))
            for item in items_data:
                file.write(item)
            file_size = file.tell()
            file.seek(6)
            file.write(struct.pack('>I', file_size))

        logger(t("success_rebuild", path=os.path.basename(output_xus_path)), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("error_generic", error=str(e)), color=COLOR_LOG_RED)

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
        "commands": [
            {
                "label": t("extract_text"), 
                "action": action_extract_xus
            },
            {
                "label": t("rebuild_file"), 
                "action": action_rebuild_xus
            }
        ]
    }