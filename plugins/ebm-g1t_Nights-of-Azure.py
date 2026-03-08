# plugins/noa_ebm_g1t_tool.py
import os
import struct
import tkinter as tk
from tkinter import filedialog


logger = None
get_option = None
current_lang = "pt_BR"
host_page = None

# -----------------------------
# TRANSLATIONS
# -----------------------------
PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "EBM & G1T Tool - Nights of Azure",
        "plugin_description": "Extrai/importa textos EBM e exporta/importa imagens G1T.",
        "extract_file": "Extrair textos (EBM → TXT)",
        "import_file": "Importar TXT → EBM (reconstruir)",
        "select_ebm": "Selecione um arquivo EBM",
        "select_g1t": "Selecione um arquivo G1T (.g1t/.g1tg)",
        "cancelled": "Operação cancelada.",
        "invalid_header": "Cabeçalho inválido (arquivo muito curto).",
        "endian_big": "Endianness detectado: BIG",
        "endian_little": "Endianness detectado: LITTLE",
        "total_texts": "Total de textos: {n}",
        "reading_text": "Lendo texto {i}/{n} (tamanho {s})",
        "text_short_read": "AVISO: não foi possível ler todos os bytes esperados para o texto {i}.",
        "saving_txt": "Salvando TXT: {path}",
        "extraction_completed": "Extração concluída: {count} textos -> {path}",
        "error": "Erro: {err}",

        # g1t
        "g1t_export_start": "Exportando imagens do G1T...",
        "g1t_export_done": "Exportação concluída: {count} imagens -> {base}_#.dds",
        "g1t_export_img": "Exportado imagem {idx} -> {out}",
        "g1t_import_start": "Importando DDS para G1T...",
        "g1t_import_done": "Importação concluída: {out}",
        "g1t_txt_missing": "DDS(s) não encontrados (esperado: {base}_{idx}.dds).",
        "g1t_size_mismatch": "Tamanho do DDS ({got}) difere do esperado ({exp}) para imagem {idx}. Pulando (ou preenchendo se menor).",
        "g1t_unhandled_format": "Formato de pixel não suportado: {pf}. Pulando imagem {idx}.",
        "g1t_invalid_magic": "Magic inválido no arquivo G1T.",
    },
    "en_US": {
        "plugin_name": "EBM & G1T Tool - Nights of Azure",
        "plugin_description": "Extract/import EBM texts and export/import G1T images.",
        "extract_file": "Extract texts (EBM → TXT)",
        "import_file": "Import TXT → EBM (rebuild)",
        "select_ebm": "Select EBM file",
        "select_g1t": "Select G1T file (.g1t/.g1tg)",
        "cancelled": "Cancelled.",
        "invalid_header": "Invalid header (file too short).",
        "endian_big": "Endian detected: BIG",
        "endian_little": "Endian detected: LITTLE",
        "total_texts": "Total texts: {n}",
        "reading_text": "Reading text {i}/{n} (size {s})",
        "text_short_read": "WARN: couldn't read all expected bytes for text {i}.",
        "saving_txt": "Saving TXT: {path}",
        "extraction_completed": "Extraction completed: {count} texts -> {path}",
        "error": "Error: {err}",

        # g1t
        "g1t_export_start": "Exporting images from G1T...",
        "g1t_export_done": "Export completed: {count} images -> {base}_#.dds",
        "g1t_export_img": "Converted image {idx} -> {out}",
        "g1t_import_start": "Importing DDS into G1T...",
        "g1t_import_done": "Import completed: {out}",
        "g1t_txt_missing": "DDS(s) not found (expected: {base}_{idx}.dds).",
        "g1t_size_mismatch": "DDS size ({got}) differs from expected ({exp}) for image {idx}. Skipping (or zero-fill if smaller).",
        "g1t_unhandled_format": "Unhandled pixel format: {pf}. Skipping image {idx}.",
        "g1t_invalid_magic": "Invalid magic in G1T file.",
    },
    "es_ES": {
        "plugin_name": "EBM & G1T Tool - Nights of Azure",
        "plugin_description": "Extrae/importa textos EBM y exporta/importa imágenes G1T.",
        "extract_file": "Extraer textos (EBM → TXT)",
        "import_file": "Importar TXT → EBM (reconstruir)",
        "select_ebm": "Seleccione archivo EBM",
        "select_g1t": "Seleccione archivo G1T (.g1t/.g1tg)",
        "cancelled": "Cancelado.",
        "invalid_header": "Encabezado inválido (archivo demasiado corto).",
        "endian_big": "Endian detectado: BIG",
        "endian_little": "Endian detectado: LITTLE",
        "total_texts": "Total de textos: {n}",
        "reading_text": "Leyendo texto {i}/{n} (tamaño {s})",
        "text_short_read": "AVISO: no se pudieron leer todos los bytes esperados para el texto {i}.",
        "saving_txt": "Guardando TXT: {path}",
        "extraction_completed": "Extracción completada: {count} textos -> {path}",
        "error": "Error: {err}",

        # g1t
        "g1t_export_start": "Exportando imágenes de G1T...",
        "g1t_export_done": "Exportación completada: {count} imágenes -> {base}_#.dds",
        "g1t_export_img": "Convertida imagen {idx} -> {out}",
        "g1t_import_start": "Importando DDS a G1T...",
        "g1t_import_done": "Importación completada: {out}",
        "g1t_txt_missing": "DDS(s) no encontrados (esperado: {base}_{idx}.dds).",
        "g1t_size_mismatch": "El tamaño del DDS ({got}) difiere del esperado ({exp}) para la imagen {idx}. Omitiendo (o rellenando con ceros si es menor).",
        "g1t_unhandled_format": "Formato de píxel no soportado: {pf}. Omitiendo imagen {idx}.",
        "g1t_invalid_magic": "Magic inválido en el archivo G1T.",
    }
}

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# -----------------------------
# UI Helper (topmost file dialog)
# -----------------------------
def pick_file_topmost(title, file_types):
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    try:
        path = filedialog.askopenfilename(parent=root, title=title, filetypes=file_types)
    finally:
        try:
            root.destroy()
        except:
            pass
    return path

# -----------------------------
# EBM: extraction / import (as before)
# -----------------------------
def extract_ebm(path):
    try:
        with open(path, "rb") as f:
            header = f.read(4)
            if len(header) < 4:
                logger(t("invalid_header"), color="#EF4444")
                return None

            if header.startswith(b"\x00\x00"):
                endian = "big"
                logger(t("endian_big"))
            else:
                endian = "little"
                logger(t("endian_little"))

            total_texts = int.from_bytes(header, endian)
            logger(t("total_texts", n=total_texts))

            texts = []
            for idx in range(total_texts):
                human_i = idx + 1
                try:
                    f.seek(32, 1)
                except Exception:
                    logger(t("text_short_read", i=human_i), color="#FACC15")
                    break

                size_bytes = f.read(4)
                if len(size_bytes) < 4:
                    logger(t("text_short_read", i=human_i), color="#FACC15")
                    break

                size = int.from_bytes(size_bytes, endian)
                logger(t("reading_text", i=human_i, n=total_texts, s=size))

                data = f.read(size)
                # skip extra 4 bytes as you indicated earlier
                try:
                    f.seek(4, 1)
                except:
                    pass

                data = data.rstrip(b"\x00")
                try:
                    text = data.decode("utf-8")
                except:
                    text = data.decode("utf-8", errors="replace")

                texts.append(text)

        out = os.path.splitext(path)[0] + ".txt"
        logger(t("saving_txt", path=out))
        try:
            with open(out, "w", encoding="utf-8", newline="\n") as fo:
                for line in texts:
                    fo.write(line + "\n")
        except Exception as e:
            logger(t("error", err=str(e)), color="#EF4444")
            return None

        logger(t("extraction_completed", count=len(texts), path=out))
        return out

    except Exception as e:
        logger(t("error", err=str(e)), color="#EF4444")
        return None

def import_ebm(path):
    try:
        base = os.path.splitext(path)[0]
        txt_path = base + ".txt"
        if not os.path.exists(txt_path):
            logger(t("error", err=t("g1t_txt_missing", base=base, idx=0)), color="#EF4444")
            return None

        with open(txt_path, "r", encoding="utf-8") as tf:
            lines = [l.rstrip("\n") for l in tf.readlines()]

        blocks = []
        with open(path, "rb") as f:
            header = f.read(4)
            if header.startswith(b"\x00\x00"):
                endian = "big"
            else:
                endian = "little"

            total = int.from_bytes(header, endian)
            logger(t("import_start"))

            for i in range(total):
                header32 = f.read(32)
                size = int.from_bytes(f.read(4), endian)
                f.seek(size, 1)
                f.seek(4, 1)

                text = lines[i].encode("utf-8")
                new_size = len(text) + 1
                block = header32 + new_size.to_bytes(4, endian) + text + b"\x00" + b"\x00\x00\x00\x00"
                blocks.append(block)

        out = base + "_rebuild.ebm"
        with open(out, "wb") as o:
            # write total back
            with open(path, "rb") as f:
                header_orig = f.read(4)
            o.write(header_orig)
            for b in blocks:
                o.write(b)

        logger(t("import_done", path=out))
        return out

    except Exception as e:
        logger(t("error", err=str(e)), color="#EF4444")
        return None

# -----------------------------
# G1T: export -> DDS
# -----------------------------
def export_g1t(path):
    try:
        with open(path, "rb") as f:
            file_data = f.read()

        pos = 0
        magic = file_data[pos:pos+4]; pos += 4

        if magic == b'G1TG':
            endian_str = '>'
        elif magic == b'GT1G':
            endian_str = '<'
        else:
            logger(t("g1t_invalid_magic"), color="#EF4444")
            return None

        # read header fields
        version = file_data[pos:pos+4]; pos += 4
        file_size, = struct.unpack(endian_str + 'I', file_data[pos:pos+4]); pos += 4
        header_size, = struct.unpack(endian_str + 'I', file_data[pos:pos+4]); pos += 4
        num_images, = struct.unpack(endian_str + 'I', file_data[pos:pos+4]); pos += 4
        unk14, = struct.unpack(endian_str + 'I', file_data[pos:pos+4]); pos += 4
        unk18, = struct.unpack(endian_str + 'I', file_data[pos:pos+4]); pos += 4

        # read unk1c list
        unk1c = []
        for _ in range(num_images):
            u, = struct.unpack(endian_str + 'I', file_data[pos:pos+4])
            unk1c.append(u); pos += 4

        # read offsets list
        offsets = []
        for _ in range(num_images):
            o, = struct.unpack(endian_str + 'I', file_data[pos:pos+4])
            offsets.append(o); pos += 4

        base_name = os.path.splitext(path)[0]

        exported = 0
        logger(t("g1t_export_start"))
        for idx in range(num_images):
            img_pos = header_size + offsets[idx]

            # image header
            unk00 = file_data[img_pos]
            pixel_format = file_data[img_pos+1]
            packed_dim = file_data[img_pos+2]
            unk03 = file_data[img_pos+3]
            unk04 = file_data[img_pos+4]
            unk05 = file_data[img_pos+5]
            unk06 = file_data[img_pos+6]
            is_extended = file_data[img_pos+7]
            img_pos += 8

            if is_extended == 0:
                img_header_size = 8
            elif is_extended in [1, 16]:
                img_header_size = 20
                # skip extended fields
                # unk08, unk0c, unk10 (we don't need their values now)
                img_pos += 12
            else:
                logger(t("g1t_unhandled_format", pf=is_extended, idx=idx), color="#FACC15")
                continue

            width = 1 << ((packed_dim >> 4) & 0x0F)
            height = 1 << (packed_dim & 0x0F)

            # map formats like original script
            is_compressed = False
            block_size = 0
            bpp = 0
            dds_fourcc = b'\0\0\0\0'
            use_dx10 = False
            dx10_dxgi = 0

            if pixel_format == 1:  # RGBA8888
                is_compressed = False
                block_size = 0
                bpp = 32
                dds_pf_flags = 0x1 | 0x40
                dds_fourcc = b'\0\0\0\0'
                dds_bitcount = 32
                dds_rmask = 0x000000FF
                dds_gmask = 0x0000FF00
                dds_bmask = 0x00FF0000
                dds_amask = 0xFF000000
            elif pixel_format in [6, 96]:  # DXT1
                is_compressed = True
                block_size = 8
                bpp = 4
                dds_fourcc = b'DXT1'
            elif pixel_format in [8, 98]:  # DXT5
                is_compressed = True
                block_size = 16
                bpp = 8
                dds_fourcc = b'DXT5'
            elif pixel_format == 102:  # BC7 -> DX10
                is_compressed = True
                block_size = 16
                bpp = 8
                dds_fourcc = b'DX10'
                use_dx10 = True
                dx10_dxgi = 98
            else:
                logger(t("g1t_unhandled_format", pf=pixel_format, idx=idx), color="#FACC15")
                continue

            if is_compressed:
                num_blocks_w = max(1, (width + 3) // 4)
                num_blocks_h = max(1, (height + 3) // 4)
                data_size = num_blocks_w * num_blocks_h * block_size
            else:
                data_size = width * height * (bpp // 8)

            data_start = header_size + offsets[idx] + img_header_size
            img_data = file_data[data_start : data_start + data_size]
            if len(img_data) != data_size:
                logger(t("g1t_size_mismatch", got=len(img_data), exp=data_size, idx=idx), color="#FACC15")
                # continue (still write what we have)
            # Build basic DDS container (DDS header minimal + data). We keep header conservative:
            dds = b'DDS '
            # pack a minimal 124-byte DDS header (kept simple, sufficient for many tools)
            hdr_size = 124
            # flags & pitch/linear size
            if is_compressed:
                hdr_flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x80000
                pitch_linear = max(1, (width + 3) // 4) * block_size
            else:
                hdr_flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x8
                pitch_linear = (width * bpp + 7) // 8

            hdr_height = height
            hdr_width = width
            hdr_depth = 0
            hdr_mipcount = 0
            reserved1 = [0] * 11

            # pack header fields (little-endian as DDS expects)
            dds += struct.pack('<I', hdr_size)
            dds += struct.pack('<I', hdr_flags)
            dds += struct.pack('<I', hdr_height)
            dds += struct.pack('<I', hdr_width)
            dds += struct.pack('<I', pitch_linear)
            dds += struct.pack('<I', hdr_depth)
            dds += struct.pack('<I', hdr_mipcount)
            for r in reserved1:
                dds += struct.pack('<I', r)

            # pixel format structure
            pf_size = 32
            dds_pf_flags = 0
            dds_bitcount = 0
            dds_rmask = dds_gmask = dds_bmask = dds_amask = 0

            if dds_fourcc == b'\0\0\0\0':
                # uncompressed RGBA8888
                dds_pf_flags = 0x1 | 0x40
                dds_bitcount = 32
                dds_rmask = 0x000000FF
                dds_gmask = 0x0000FF00
                dds_bmask = 0x00FF0000
                dds_amask = 0xFF000000
            else:
                dds_pf_flags = 0x4
                dds_bitcount = 0
                dds_rmask = dds_gmask = dds_bmask = dds_amask = 0

            dds += struct.pack('<I', pf_size)
            dds += struct.pack('<I', dds_pf_flags)
            dds += dds_fourcc
            dds += struct.pack('<I', dds_bitcount)
            dds += struct.pack('<I', dds_rmask)
            dds += struct.pack('<I', dds_gmask)
            dds += struct.pack('<I', dds_bmask)
            dds += struct.pack('<I', dds_amask)

            # caps
            caps1 = 0x1000
            caps2 = caps3 = caps4 = reserved2 = 0
            dds += struct.pack('<I', caps1)
            dds += struct.pack('<I', caps2)
            dds += struct.pack('<I', caps3)
            dds += struct.pack('<I', caps4)
            dds += struct.pack('<I', reserved2)

            # DX10 header if needed
            if use_dx10:
                dds += struct.pack('<5I', dx10_dxgi, 3, 0, 1, 0)

            dds += img_data

            out_file = f"{base_name}_{idx}.dds"
            with open(out_file, "wb") as of:
                of.write(dds)

            logger(t("g1t_export_img", idx=idx, out=out_file))
            exported += 1

        logger(t("g1t_export_done", count=exported, base=base_name))
        return exported

    except Exception as e:
        logger(t("error", err=str(e)), color="#EF4444")
        return None

# -----------------------------
# G1T: import <- DDS (prático)
# -----------------------------
def import_g1t(path):
    """
    Import DDS files named base_{idx}.dds into the G1T original file.
    If DDS payload is smaller than expected data region, it will be zero-padded.
    If DDS payload is larger than expected data region, the image is skipped (to avoid offset recalculation).
    """
    try:
        with open(path, "rb") as f:
            file_data = bytearray(f.read())

        pos = 0
        magic = bytes(file_data[pos:pos+4]); pos += 4

        if magic == b'G1TG':
            endian_str = '>'
        elif magic == b'GT1G':
            endian_str = '<'
        else:
            logger(t("g1t_invalid_magic"), color="#EF4444")
            return None

        version = bytes(file_data[pos:pos+4]); pos += 4
        file_size, = struct.unpack(endian_str + 'I', bytes(file_data[pos:pos+4])); pos += 4
        header_size, = struct.unpack(endian_str + 'I', bytes(file_data[pos:pos+4])); pos += 4
        num_images, = struct.unpack(endian_str + 'I', bytes(file_data[pos:pos+4])); pos += 4
        unk14, = struct.unpack(endian_str + 'I', bytes(file_data[pos:pos+4])); pos += 4
        unk18, = struct.unpack(endian_str + 'I', bytes(file_data[pos:pos+4])); pos += 4

        unk1c = []
        for _ in range(num_images):
            u, = struct.unpack(endian_str + 'I', bytes(file_data[pos:pos+4]))
            unk1c.append(u); pos += 4

        offsets = []
        for _ in range(num_images):
            o, = struct.unpack(endian_str + 'I', bytes(file_data[pos:pos+4]))
            offsets.append(o); pos += 4

        base_name = os.path.splitext(path)[0]
        logger(t("g1t_import_start"))

        # We'll assemble a new bytearray to write out (start from original to preserve headers)
        new_data = bytearray(file_data)  # mutable copy

        for idx in range(num_images):
            img_pos = header_size + offsets[idx]
            pixel_format = new_data[img_pos+1]
            packed_dim = new_data[img_pos+2]
            is_extended = new_data[img_pos+7]

            # compute img header size
            if is_extended == 0:
                img_header_size = 8
            elif is_extended in [1, 16]:
                img_header_size = 20
            else:
                logger(t("g1t_unhandled_format", pf=is_extended, idx=idx), color="#FACC15")
                continue

            width = 1 << ((packed_dim >> 4) & 0x0F)
            height = 1 << (packed_dim & 0x0F)

            # map formats to compute data_size similarly to export
            if pixel_format == 1:
                is_compressed = False
                bpp = 32
                block_size = 0
            elif pixel_format == 6:
                is_compressed = True
                block_size = 8
                bpp = 4
            elif pixel_format in [8, 98]:
                is_compressed = True
                block_size = 16
                bpp = 8
            elif pixel_format == 102:
                is_compressed = True
                block_size = 16
                bpp = 8
            else:
                logger(t("g1t_unhandled_format", pf=pixel_format, idx=idx), color="#FACC15")
                continue

            if is_compressed:
                num_blocks_w = max(1, (width + 3) // 4)
                num_blocks_h = max(1, (height + 3) // 4)
                data_size = num_blocks_w * num_blocks_h * block_size
            else:
                data_size = width * height * (bpp // 8)

            # compute positions
            # locate start of img_data within file
            # read img_header size to get to payload (we need original img_header_size bytes)
            # read actual stored img_header_size from file:
            img_header_real_size = 8
            if is_extended in [1, 16]:
                img_header_real_size = 20

            data_start = header_size + offsets[idx] + img_header_real_size
            data_end = data_start + data_size

            expected_len = data_size

            # DDS file expected name
            dds_file = f"{base_name}_{idx}.dds"
            if not os.path.exists(dds_file):
                logger(t("g1t_txt_missing", base=base_name, idx=idx), color="#FACC15")
                continue

            # parse DDS to get payload bytes
            with open(dds_file, "rb") as df:
                dds_bytes = df.read()

            # minimal DDS parser: skip "DDS " + 124 header (+20 if DX10)
            if len(dds_bytes) < 4 + 124:
                logger(t("error", err=f"DDS too small: {dds_file}"), color="#FACC15")
                continue
            dds_magic = dds_bytes[0:4]
            if dds_magic != b'DDS ':
                logger(t("error", err=f"Not a DDS: {dds_file}"), color="#FACC15")
                continue
            # check ddspf.fourCC located at offset 4 + 76 (4 + 32 + 4 + ... )
            # But simple approach: read ddspf.fourCC at bytes 4 + 76 .. 4 + 80
            fourcc = dds_bytes[4 + 76 : 4 + 80]
            offset_payload = 4 + 124
            if fourcc == b'DX10':
                offset_payload += 20

            payload = dds_bytes[offset_payload:]

            got = len(payload)
            exp = expected_len

            if got > exp:
                logger(t("g1t_size_mismatch", got=got, exp=exp, idx=idx), color="#FACC15")
                logger(f"Skipping image {idx} (DDS larger than expected).", color="#FACC15")
                continue
            elif got < exp:
                logger(t("g1t_size_mismatch", got=got, exp=exp, idx=idx), color="#FACC15")
                # zero-fill trailing bytes so file size remains same
                new_payload = payload + (b'\x00' * (exp - got))
            else:
                new_payload = payload

            # write new_payload into new_data
            new_data[data_start:data_end] = new_payload

        # write out new file
        out_file = base_name + "_imported.g1t"
        with open(out_file, "wb") as of:
            of.write(new_data)

        logger(t("g1t_import_done", out=out_file))
        return out_file

    except Exception as e:
        logger(t("error", err=str(e)), color="#EF4444")
        return None

# -----------------------------
# ACTIONS (dialog + logger)
# -----------------------------
def action_extract_ebm():
    p = pick_file_topmost(t("select_ebm"), [("EBM files", "*.ebm"), ("All files", "*.*")])
    if not p:
        logger(t("cancelled"))
        return
    extract_ebm(p)

def action_import_ebm():
    p = pick_file_topmost(t("select_ebm"), [("EBM files", "*.ebm"), ("All files", "*.*")])
    if not p:
        logger(t("cancelled"))
        return
    import_ebm(p)

def action_export_g1t():
    p = pick_file_topmost(t("select_g1t"), [("G1T files", "*.g1t *.g1tg"), ("All files", "*.*")])
    if not p:
        logger(t("cancelled"))
        return
    export_g1t(p)

def action_import_g1t():
    p = pick_file_topmost(t("select_g1t"), [("G1T files", "*.g1t *.g1tg"), ("All files", "*.*")])
    if not p:
        logger(t("cancelled"))
        return
    import_g1t(p)

# -----------------------------
# REGISTER PLUGIN
# -----------------------------
def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, get_option, current_lang, host_page
    logger = log_func
    get_option = option_getter
    current_lang = host_language or "pt_BR"
    host_page = page

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "options": [],
        "commands": [
            {"label": t("extract_file"), "action": action_extract_ebm},
            {"label": t("import_file"), "action": action_import_ebm},
            {"label": "Export G1T → DDS", "action": action_export_g1t},
            {"label": "Import DDS → G1T", "action": action_import_g1t},
        ]
    }