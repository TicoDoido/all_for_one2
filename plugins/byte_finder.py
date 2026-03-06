import os

# ==============================================================================
# TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "Byte Finder",
        "plugin_description": "Busca texto ou hex dentro de arquivos.",
        "cmd_scan": "Escanear",
        "folder": "Pasta",
        "text_patterns": "Texto (um por linha)",
        "hex_patterns": "HEX (um por linha)",
        "extensions": "Extensões (*.bin,*.dat,*.*)",
        "all_files": "Todos os arquivos",
        "subfolders": "Subpastas",
        "encoding": "Encoding",
        "scan_start": "Iniciando varredura...",
        "no_patterns": "Nenhum padrão válido.",
        "found": "Ocorrências encontradas: {count}",
        "yes": "Sim",
        "no": "Não"
    },
    "en_US": {
        "plugin_name": "Byte Finder",
        "plugin_description": "Search text or hex patterns inside files.",
        "cmd_scan": "Scan",
        "folder": "Folder",
        "text_patterns": "Text (one per line)",
        "hex_patterns": "HEX (one per line)",
        "extensions": "Extensions (*.bin,*.dat,*.*)",
        "all_files": "All files",
        "subfolders": "Subfolders",
        "encoding": "Encoding",
        "scan_start": "Starting scan...",
        "no_patterns": "No valid patterns.",
        "found": "Matches found: {count}",
        "yes": "Yes",
        "no": "No"
    },
    "es_ES": {
        "plugin_name": "Buscador de Bytes",
        "plugin_description": "Busca texto o hex dentro de archivos.",
        "cmd_scan": "Escanear",
        "folder": "Carpeta",
        "text_patterns": "Texto (uno por línea)",
        "hex_patterns": "HEX (uno por línea)",
        "extensions": "Extensiones (*.bin,*.dat,*.*)",
        "all_files": "Todos los archivos",
        "subfolders": "Subcarpetas",
        "encoding": "Encoding",
        "scan_start": "Iniciando escaneo...",
        "no_patterns": "Ningún patrón válido.",
        "found": "Coincidencias: {count}",
        "yes": "Sí",
        "no": "No",
    }
}

state = {
    "logger": None,
    "lang": "pt_BR"
}

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(
        state["lang"],
        PLUGIN_TRANSLATIONS["pt_BR"]
    ).get(key, key).format(**kwargs)

# ==============================================================================
# BACKEND
# ==============================================================================

CHUNK = 1024 * 1024

def parse_patterns(text, hexp, encoding):
    patterns = []
    if text:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                patterns.append(line.encode(encoding))
            except:
                pass
    if hexp:
        for line in hexp.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                patterns.append(bytes.fromhex(line))
            except:
                pass
    return patterns


def scan_file(path, patterns):
    results = []
    max_pat = max(len(p) for p in patterns)
    with open(path, "rb") as f:
        overlap = max_pat
        prev = b""
        offset = 0
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            data = prev + chunk
            for pat in patterns:
                start = 0
                while True:
                    pos = data.find(pat, start)
                    if pos == -1:
                        break
                    real = offset - len(prev) + pos
                    results.append(real)
                    start = pos + 1
            prev = data[-overlap:]
            offset += len(chunk)
    return results

def run_scan(folder, patterns, recursive, extensions, all_files):
    matches = 0
    walker = os.walk(folder) if recursive else [(folder, None, os.listdir(folder))]
    for root, _, files in walker:
        for file in files:
            path = os.path.join(root, file)
            if not os.path.isfile(path):
                continue
            if not all_files and extensions:
                if not any(file.lower().endswith(e) for e in extensions):
                    continue
            try:
                hits = scan_file(path, patterns)
                for h in hits:
                    state["logger"](f"{path} | 0x{h:X}")
                matches += len(hits)
            except:
                pass
    state["logger"](t("found", count=matches))

# ==============================================================================
# REGISTRO DO PLUGIN
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    state["logger"] = log_func
    state["lang"] = host_language

    def execute():
        folder        = option_getter("folder")
        text          = option_getter("text")
        hexp          = option_getter("hex")
        encoding      = option_getter("encoding") or "utf-8"
        recursive_raw = option_getter("recursive")
        recursive     = recursive_raw == t("yes")
        extensions    = option_getter("extensions") or "*.*"

        patterns = parse_patterns(text, hexp, encoding)
        if not patterns:
            state["logger"](t("no_patterns"))
            return

        if extensions.strip() == "*.*":
            ext_list = []
            all_files = True
        else:
            ext_list = [e.strip().lstrip("*") for e in extensions.split(",")]
            all_files = False

        state["logger"](t("scan_start"))
        run_scan(folder, patterns, recursive, ext_list, all_files)

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "options": [
            {"name": "folder",     "label": t("folder"),        "type": "folder"},
            {"name": "recursive",  "label": t("subfolders"),    "type": "dropdown", "values": [t("yes"), t("no")], "default": t("yes")},
            {"name": "extensions", "label": t("extensions"),    "type": "text",     "default": "*.*"},
            {"name": "encoding",   "label": t("encoding"),      "type": "dropdown", "values": ["utf-8", "latin-1", "utf-16le", "utf-16be", "shift-jis"], "default": "utf-8"},
            {"name": "text",       "label": t("text_patterns"), "type": "text"},
            {"name": "hex",        "label": t("hex_patterns"),  "type": "text"},
        ],
        "commands": [{"label": t("cmd_scan"), "action": execute}]
    }