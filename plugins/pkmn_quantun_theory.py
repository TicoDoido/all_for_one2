import os
import struct
import zlib
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "PKMN Tool - Quantum Theory",
        "plugin_description": "Extrai e reconstrói arquivos .pkmn do jogo Quantum Theory (PS3/X360)",
        "extract_file": "Extrair .pkmn",
        "rebuild_file": "Reconstruir .pkmn",
        "select_pkmn_file": "Selecione o arquivo .pkmn",
        "select_original_file": "Selecione o arquivo .pkmn original",
        "select_decomp_file": "Selecione um arquivo .decomp (qualquer)",
        "pkmn_files": "Arquivos PKMN",
        "decomp_files": "Arquivos decomp",
        "all_files": "Todos os arquivos",
        "log_extract_start": "Extraindo {name}...",
        "log_found_block": "Bloco {idx} em offset 0x{offset:08X} ({type})",
        "log_extract_success": "Bloco {idx} salvo como {name}",
        "log_extract_error": "Erro no bloco {idx}: {error}",
        "log_rebuild_start": "Reconstruindo {name}...",
        "log_rebuild_block": "Substituindo bloco {idx} em 0x{offset:08X} com {file}",
        "log_rebuild_success": "Novo arquivo salvo: {path}",
        "log_rebuild_error": "Erro na reconstrução: {error}",
        "err_magic": "Magic inválido (esperado 0x00004000) em 0x{offset:08X}",
        "err_no_decomp": "Nenhum arquivo .decomp encontrado para o prefixo {prefix}",
        "err_invalid_prefix": "Não foi possível extrair prefixo do nome do arquivo: {name}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "operation_completed": "Operação concluída."
    },
    "en_US": {
        "plugin_name": "PKMN Tool - Quantum Theory",
        "plugin_description": "Extracts and rebuilds .pkmn files from Quantum Theory (PS3/X360)",
        "extract_file": "Extract .pkmn",
        "rebuild_file": "Rebuild .pkmn",
        "select_pkmn_file": "Select .pkmn file",
        "select_original_file": "Select original .pkmn file",
        "select_decomp_file": "Select a .decomp file (any)",
        "pkmn_files": "PKMN Files",
        "decomp_files": "Decomp files",
        "all_files": "All files",
        "log_extract_start": "Extracting {name}...",
        "log_found_block": "Block {idx} at offset 0x{offset:08X} ({type})",
        "log_extract_success": "Block {idx} saved as {name}",
        "log_extract_error": "Error on block {idx}: {error}",
        "log_rebuild_start": "Rebuilding {name}...",
        "log_rebuild_block": "Replacing block {idx} at 0x{offset:08X} with {file}",
        "log_rebuild_success": "New file saved: {path}",
        "log_rebuild_error": "Rebuild error: {error}",
        "err_magic": "Invalid magic (expected 0x00004000) at 0x{offset:08X}",
        "err_no_decomp": "No .decomp files found for prefix {prefix}",
        "err_invalid_prefix": "Could not extract prefix from filename: {name}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "operation_completed": "Operation completed."
    },
    "es_ES": {
        "plugin_name": "PKMN Tool - Quantum Theory",
        "plugin_description": "Extrae y reconstruye archivos .pkmn de Quantum Theory (PS3/X360)",
        "extract_file": "Extraer .pkmn",
        "rebuild_file": "Reconstruir .pkmn",
        "select_pkmn_file": "Seleccione el archivo .pkmn",
        "select_original_file": "Seleccione el archivo .pkmn original",
        "select_decomp_file": "Seleccione un archivo .decomp (cualquiera)",
        "pkmn_files": "Archivos PKMN",
        "decomp_files": "Archivos decomp",
        "all_files": "Todos los archivos",
        "log_extract_start": "Extrayendo {name}...",
        "log_found_block": "Bloque {idx} en offset 0x{offset:08X} ({type})",
        "log_extract_success": "Bloque {idx} guardado como {name}",
        "log_extract_error": "Error en bloque {idx}: {error}",
        "log_rebuild_start": "Reconstruyendo {name}...",
        "log_rebuild_block": "Reemplazando bloque {idx} en 0x{offset:08X} con {file}",
        "log_rebuild_success": "Nuevo archivo guardado: {path}",
        "log_rebuild_error": "Error en reconstrucción: {error}",
        "err_magic": "Magic inválido (se esperaba 0x00004000) en 0x{offset:08X}",
        "err_no_decomp": "No se encontraron archivos .decomp para el prefijo {prefix}",
        "err_invalid_prefix": "No se pudo extraer prefijo del nombre: {name}",
        "cancelled": "Selección cancelada.",
        "processing": "Procesando: {name}...",
        "operation_completed": "Operación completada."
    }
}

COLOR_LOG_GREEN = "#4ADE80"
COLOR_LOG_YELLOW = "#FACC15"
COLOR_LOG_RED = "#EF4444"

logger = None
get_option = None
current_lang = "pt_BR"
host_page = None

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# ==============================================================================
# FilePickers globais
# ==============================================================================

fp_extract = ft.FilePicker(
    on_result=lambda e: _extract_pkmn(Path(e.files[0].path)) if e.files else logger(t("cancelled"), color=COLOR_LOG_YELLOW)
)

# Rebuild requer dois passos: primeiro seleciona o .pkmn original, depois um .decomp
_rebuild_original = None

def _on_original_selected(e):
    global _rebuild_original
    if e.files:
        _rebuild_original = Path(e.files[0].path)
        fp_rebuild_decomp.pick_files(
            allowed_extensions=["decomp"],
            dialog_title=t("select_decomp_file")
        )
    else:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)

def _on_decomp_selected(e):
    global _rebuild_original
    if e.files and _rebuild_original:
        decomp_path = Path(e.files[0].path)
        _rebuild_pkmn(_rebuild_original, decomp_path)
        _rebuild_original = None
    else:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)

fp_rebuild_original = ft.FilePicker(on_result=_on_original_selected)
fp_rebuild_decomp = ft.FilePicker(on_result=_on_decomp_selected)

# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

def alinhar_16_write(f):
    pos = f.tell()
    resto = pos % 16
    if resto != 0:
        f.write(b"\x00" * (16 - resto))

def alinhar_16_read(f):
    pos = f.tell()
    resto = pos % 16
    if resto != 0:
        f.seek(16 - resto, 1)

def detectar_tipo(data):
    if data.startswith(b"DGSM"):
        return "text"
    elif data.startswith(b"\x00\x00\x00\x20"):
        return "tex"
    else:
        return "bin"

# ==============================================================================
# EXTRAÇÃO
# ==============================================================================

def _extract_pkmn(caminho: Path):
    logger(t("processing", name=caminho.name), color=COLOR_LOG_YELLOW)
    base_dir = caminho.parent
    nome_base = caminho.stem

    contador_bloco = 1

    try:
        with open(caminho, "rb") as f:
            tamanho_arquivo = caminho.stat().st_size

            while f.tell() < tamanho_arquivo:
                inicio_bloco = f.tell()
                magic = f.read(4)
                if len(magic) < 4:
                    break

                if magic != b"\x00\x00\x40\x00":
                    logger(t("err_magic", offset=inicio_bloco), color=COLOR_LOG_RED)
                    break

                total_chunks = struct.unpack(">I", f.read(4))[0]
                total_size = struct.unpack(">I", f.read(4))[0]

                tamanhos = [struct.unpack(">I", f.read(4))[0] for _ in range(total_chunks)]

                dados_descomprimidos = b""

                for tamanho in tamanhos:
                    chunk_data = f.read(tamanho)
                    try:
                        dados_descomprimidos += zlib.decompress(chunk_data)
                    except:
                        pass

                alinhar_16_read(f)

                tipo = detectar_tipo(dados_descomprimidos)

                nome_saida = f"{nome_base}_{contador_bloco:02d}_{tipo}.decomp"
                caminho_saida = base_dir / nome_saida

                with open(caminho_saida, "wb") as out:
                    out.write(dados_descomprimidos)

                logger(t("log_extract_success", idx=contador_bloco, name=nome_saida), color=COLOR_LOG_GREEN)
                contador_bloco += 1

        logger(t("operation_completed"), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("log_extract_error", idx=contador_bloco, error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# RECONSTRUÇÃO
# ==============================================================================

def _rebuild_pkmn(original: Path, decomp_qualquer: Path):
    logger(t("processing", name=original.name), color=COLOR_LOG_YELLOW)

    pasta = decomp_qualquer.parent
    nome = decomp_qualquer.name

    # Extrai prefixo removendo os últimos dois underscores e a extensão
    partes = nome.split("_")
    if len(partes) < 3:
        logger(t("err_invalid_prefix", name=nome), color=COLOR_LOG_RED)
        return

    prefixo = "_".join(partes[:-2])  # remove _XX_tipo.decomp

    arquivos = [p for p in pasta.glob(f"{prefixo}_*.decomp")]
    arquivos.sort()  # ordem numérica

    if not arquivos:
        logger(t("err_no_decomp", prefix=prefixo), color=COLOR_LOG_RED)
        return

    try:
        with open(original, "rb") as f:
            data = bytearray(f.read())

        offset = 0
        bloco_index = 0

        while offset < len(data) and bloco_index < len(arquivos):
            if data[offset:offset+4] != b"\x00\x00\x40\x00":
                offset += 1
                continue

            logger(t("log_rebuild_block", idx=bloco_index+1, offset=offset, file=arquivos[bloco_index].name), color=COLOR_LOG_YELLOW)

            with open(arquivos[bloco_index], "rb") as f:
                raw = f.read()

            # dividir em chunks de 0x4000
            chunks = [raw[i:i+0x4000] for i in range(0, len(raw), 0x4000)]

            comp_chunks = [zlib.compress(c, 9) for c in chunks]
            tamanhos = [len(c) for c in comp_chunks]

            novo_bloco = bytearray()
            novo_bloco += b"\x00\x00\x40\x00"
            novo_bloco += struct.pack(">I", len(comp_chunks))
            novo_bloco += struct.pack(">I", len(raw))

            for t in tamanhos:
                novo_bloco += struct.pack(">I", t)

            for c in comp_chunks:
                novo_bloco += c

            # padding para 16 bytes
            while len(novo_bloco) % 16 != 0:
                novo_bloco += b"\x00"

            # calcular tamanho do bloco original
            tmp = offset + 4
            n = struct.unpack(">I", data[tmp:tmp+4])[0]
            tmp += 8
            sizes = [struct.unpack(">I", data[tmp+i*4:tmp+i*4+4])[0] for i in range(n)]
            tmp += n*4
            tamanho_antigo = tmp - offset + sum(sizes)
            while tamanho_antigo % 16 != 0:
                tamanho_antigo += 1

            data[offset:offset+tamanho_antigo] = novo_bloco

            offset += len(novo_bloco)
            bloco_index += 1

        out_path = original.parent / (original.stem + "_mod" + original.suffix)
        with open(out_path, "wb") as f:
            f.write(data)

        logger(t("log_rebuild_success", path=str(out_path)), color=COLOR_LOG_GREEN)

    except Exception as e:
        logger(t("log_rebuild_error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# AÇÕES DOS COMANDOS
# ==============================================================================

def action_extract():
    fp_extract.pick_files(
        allowed_extensions=["pkmn"],
        dialog_title=t("select_pkmn_file")
    )

def action_rebuild():
    fp_rebuild_original.pick_files(
        allowed_extensions=["pkmn"],
        dialog_title=t("select_original_file")
    )

# ==============================================================================
# ENTRY POINT
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, get_option, current_lang, host_page
    logger = log_func
    get_option = option_getter
    current_lang = host_language
    host_page = page

    if host_page:
        host_page.overlay.extend([fp_extract, fp_rebuild_original, fp_rebuild_decomp])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "commands": [
            {"label": t("extract_file"), "action": action_extract},
            {"label": t("rebuild_file"), "action": action_rebuild},
        ]
    }