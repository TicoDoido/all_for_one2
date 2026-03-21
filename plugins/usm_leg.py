# Originalmente feito por Denis Moreno
import os
import re
import struct
from pathlib import Path
import flet as ft
from typing import List, Dict, Any, Tuple, Optional

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "USM - Editor de Legendas",
        "plugin_description": "Extrai e reinsere legendas de arquivos USM/SFD (CRI Middleware)",
        "extract_subtitles": "Extrair Legendas",
        "reinsert_subtitles": "Reinserir Legendas",
        "select_usm_file": "Selecione o arquivo .sfd/.usm",
        "select_txt_file": "Selecione o arquivo de legendas .txt",
        "log_import_success": "Importadas {count} entradas de {file}. (contexto mantido em memória)",
        "log_export_success": "Reconstrução concluída. Arquivo salvo como: {file} (Δ {delta} bytes).",
        "log_no_sbt": "Nenhum bloco @SBT encontrado em {file}.",
        "err_context": "Erro: Contexto não encontrado. Importe o arquivo original primeiro.",
        "err_mismatch": "Erro: O número de linhas ({provided}) não condiz com o original ({expected}).",
        "err_unexpected": "Erro inesperado: {error}",
        "processing": "Processando: {name}...",
        "cancelled": "Seleção cancelada."
    },
    "en_US": {
        "plugin_name": "USM - Subtitle Editor",
        "plugin_description": "Extracts and reinserts subtitles from USM/SFD files (CRI Middleware)",
        "extract_subtitles": "Extract Subtitles",
        "reinsert_subtitles": "Reinsert Subtitles",
        "select_usm_file": "Select .sfd/.usm file",
        "select_txt_file": "Select subtitle .txt file",
        "log_import_success": "Imported {count} entries from {file}. (context kept in memory)",
        "log_export_success": "Reconstruction done: {file} (Δ {delta} bytes).",
        "log_no_sbt": "No @SBT blocks found in {file}.",
        "err_context": "Error: Context not found. Import the original file first.",
        "err_mismatch": "Error: Line count mismatch ({provided}/{expected}).",
        "err_unexpected": "Unexpected error: {error}",
        "processing": "Processing: {name}...",
        "cancelled": "Selection cancelled."
    },
    "es_ES": {
        "plugin_name": "USM - Editor de Subtítulos",
        "plugin_description": "Extrae y reinserta subtítulos de archivos USM/SFD (CRI Middleware)",
        "extract_subtitles": "Extraer Subtítulos",
        "reinsert_subtitles": "Reinsertar Subtítulos",
        "select_usm_file": "Seleccionar archivo .sfd/.usm",
        "select_txt_file": "Seleccionar archivo de subtítulos .txt",
        "log_import_success": "Importadas {count} entradas de {file}. (contexto mantenido en memoria)",
        "log_export_success": "Reconstrucción completada: {file} (Δ {delta} bytes).",
        "log_no_sbt": "No se encontraron bloques @SBT en {file}.",
        "err_context": "Error: Contexto no encontrado. Importe el archivo original primero.",
        "err_mismatch": "Error: El número de líneas ({provided}) no coincide con el original ({expected}).",
        "err_unexpected": "Error inesperado: {error}",
        "processing": "Procesando: {name}...",
        "cancelled": "Selección cancelada."
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

# Estado global do plugin
logger = None
current_lang = "pt_BR"
host_page = None
_contexts: Dict[str, Dict[str, Any]] = {}
_last_usm_path: Optional[str] = None

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# UTILITÁRIOS DE TEMPO (mantidos do original)
# ==============================================================================

def format_time_ms(ms: int) -> str:
    ms = max(0, ms)
    milliseconds = ms % 1000
    seconds = (ms // 1000) % 60
    minutes = (ms // (1000 * 60)) % 60
    hours = ms // (1000 * 60 * 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def parse_time_ms(time_str: str) -> int:
    try:
        time_str = time_str.replace('.', ',')
        parts = re.split(r'[:,]', time_str)
        h, m, s, ms = map(int, parts)
        return (h * 3600 + m * 60 + s) * 1000 + ms
    except: return 0

# ==============================================================================
# LÓGICA CORE (EXTRAÇÃO E REINSERÇÃO) – IDÊNTICA AO ORIGINAL
# ==============================================================================

def run_extraction(usm_path: str):
    global _last_usm_path
    try:
        if logger: logger(t("processing", name=os.path.basename(usm_path)), color=COLOR_LOG_YELLOW)
        
        path = Path(usm_path)
        data_bytes = path.read_bytes()
        sbt_offsets = [m.start() for m in re.finditer(b'@SBT', data_bytes)]
        
        if not sbt_offsets:
            if logger: logger(t("log_no_sbt", file=path.name), color=COLOR_LOG_RED)
            return

        rows = []
        metadata = []
        METADATA_SIGS = [b'CRIUSF_DIR_STREAM', b'@UTF', b'#HEADER END', b'#CONTENTS END']

        for offset in sbt_offsets:
            try:
                cursor = offset + 4
                chunk_size = struct.unpack('>I', data_bytes[cursor:cursor + 4])[0]
                cursor += 4
                header_data = data_bytes[cursor:cursor + 40]
                
                if any(sig in header_data for sig in METADATA_SIGS): continue

                langid = struct.unpack_from('<B', header_data, 24)[0]
                start_ms = struct.unpack_from('<I', header_data, 32)[0]
                duration_ms = struct.unpack_from('<I', header_data, 36)[0]
                time_str = f"{format_time_ms(start_ms)}->{format_time_ms(start_ms+duration_ms)}"

                text_size_off = cursor + 40
                text_size = struct.unpack('<I', data_bytes[text_size_off:text_size_off + 4])[0]
                
                text_off = text_size_off + 4
                text = data_bytes[text_off:text_off + text_size].decode('utf-8', errors='ignore').rstrip('\x00')

                rows.append(f"{time_str}|{langid}|{text}")
                metadata.append({
                    'offset': offset,
                    'chunk_size': chunk_size,
                    'original_text_size': text_size,
                    'original_start_ms': start_ms,
                    'original_duration_ms': duration_ms,
                    'original_text': text
                })
            except: continue

        # Salvar contexto para reinserção
        _contexts[usm_path] = {'raw_data': data_bytes, 'metadata': metadata}
        _last_usm_path = usm_path

        # Salvar TXT
        txt_path = path.with_suffix('.txt')
        txt_path.write_text("Time|LangID|Text\n" + "\n".join(rows), encoding='utf-8')
        
        if logger: logger(t("log_import_success", count=len(rows), file=path.name), color=COLOR_LOG_GREEN)

    except Exception as e:
        if logger: logger(t("err_unexpected", error=str(e)), color=COLOR_LOG_RED)

def run_reinsertion(txt_path: str):
    try:
        # Usa o último USM aberto ou tenta achar um com mesmo nome
        usm_path = _last_usm_path
        if not usm_path or usm_path not in _contexts:
            if logger: logger(t("err_context"), color=COLOR_LOG_RED)
            return

        ctx = _contexts[usm_path]
        lines = Path(txt_path).read_text(encoding='utf-8').splitlines()
        if lines and "Time|" in lines[0]: lines = lines[1:] # Skip header

        if len(lines) != len(ctx['metadata']):
            if logger: logger(t("err_mismatch", provided=len(lines), expected=len(ctx['metadata'])), color=COLOR_LOG_RED)
            return

        original_data = ctx['raw_data']
        new_file_data = bytearray()
        last_off = 0
        total_delta = 0

        for meta, line in zip(ctx['metadata'], lines):
            try:
                time_part, lang_part, text = line.split('|', 2)
                t_start, t_end = time_part.split('->')
                n_start = parse_time_ms(t_start)
                n_dur = parse_time_ms(t_end) - n_start
            except: continue

            off = meta['offset']
            new_file_data.extend(original_data[last_off:off])

            # Se idêntico, copia original para manter integridade
            if n_start == meta['original_start_ms'] and n_dur == meta['original_duration_ms'] and text == meta['original_text']:
                chunk_end = off + 8 + meta['chunk_size']
                new_file_data.extend(original_data[off:chunk_end])
                last_off = chunk_end
                continue

            # Reconstrói bloco @SBT
            txt_bytes = text.encode('utf-8')
            new_txt_size = len(txt_bytes)
            
            # Atualiza Header (40 bytes)
            h_bytes = bytearray(original_data[off+8 : off+8+40])
            struct.pack_into('<I', h_bytes, 32, n_start)
            struct.pack_into('<I', h_bytes, 36, max(0, n_dur))

            # Calcula novo tamanho do chunk (alinhado a 4 bytes)
            req_space = 40 + 4 + new_txt_size
            new_chunk_size = (req_space + 11) & ~3 # Padding simples
            
            total_delta += (new_chunk_size - meta['chunk_size'])

            chunk = bytearray(b'@SBT')
            chunk.extend(struct.pack('>I', new_chunk_size))
            chunk.extend(h_bytes)
            chunk.extend(struct.pack('<I', new_txt_size))
            chunk.extend(txt_bytes)
            chunk.extend(b'\x00' * (new_chunk_size - req_space))

            new_file_data.extend(chunk)
            last_off = off + 8 + meta['chunk_size']

        new_file_data.extend(original_data[last_off:])
        
        out_path = Path(usm_path).with_name(f"NEW_{Path(usm_path).name}")
        out_path.write_bytes(new_file_data)
        
        if logger: logger(t("log_export_success", file=out_path.name, delta=total_delta), color=COLOR_LOG_GREEN)

    except Exception as e:
        if logger: logger(t("err_unexpected", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# INTERFACE FLET (FILE PICKERS)
# ==============================================================================

fp_extract = ft.FilePicker(on_result=lambda e: run_extraction(e.files[0].path) if e.files else None)
fp_reinsert = ft.FilePicker(on_result=lambda e: run_reinsertion(e.files[0].path) if e.files else None)

def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, current_lang, host_page
    logger = log_func
    current_lang = host_language
    host_page = page

    if host_page:
        host_page.overlay.extend([fp_extract, fp_reinsert])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {
                "label": t("extract_subtitles"), 
                "action": lambda: fp_extract.pick_files(
                    allowed_extensions=["sfd", "usm"],
                    dialog_title=t("select_usm_file")
                )
            },
            {
                "label": t("reinsert_subtitles"), 
                "action": lambda: fp_reinsert.pick_files(
                    allowed_extensions=["txt"],
                    dialog_title=t("select_txt_file")
                )
            },
        ]
    }