# g1t info get here = https://github.com/xdanieldzd/Scarlet/blob/master/Scarlet.IO.ImageFormats/G1TG.cs
# Some minor adaptations for PS4 files...
import os
import struct
import flet as ft
from Swizzle_PS4_MORTON import process_data

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
        "import_done": "Importação concluída: {path}",
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
        "g1t_format_mismatch": "AVISO: Imagem {idx} espera {exp_fcc} mas o DDS tem formato diferente. Pulando."
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
        "import_done": "Import completed: {path}",
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
        "g1t_format_mismatch": "WARN: Image {idx} expects {exp_fcc} but DDS has a different format. Skipping."
    }
}

def t(key, **kwargs):
    return PLUGIN_TRANSLATIONS.get(current_lang, PLUGIN_TRANSLATIONS["pt_BR"]).get(key, key).format(**kwargs)

# -----------------------------
# EBM BSB: extraction / import
# -----------------------------
def extract_ebm(path):
    try:
        with open(path, "rb") as f:
            header = f.read(4)
            if len(header) < 4:
                if logger: logger(t("invalid_header"), color="#EF4444")
                return None

            if header.startswith(b"\x00\x00"):
                endian = "big"
                if logger: logger(t("endian_big"))
            else:
                endian = "little"
                if logger: logger(t("endian_little"))

            total_texts = int.from_bytes(header, endian)
            if logger: logger(t("total_texts", n=total_texts))

            texts = []
            for idx in range(total_texts):
                human_i = idx + 1

                if path.lower().endswith(".bsb"):
                    choices_byte = f.read(4)
                    choices = int.from_bytes(choices_byte, endian)
                    
                    texts.append(f"@{human_i}")
                    for choice in range(choices):
                        size_bytes = f.read(4)
                        size = int.from_bytes(size_bytes, endian)
                        data = f.read(size)
                        data = data.rstrip(b"\x00")
                        text = data.decode("utf-8", errors="replace")
                        texts.append(text)
                
                else:
                    f.seek(32, 1)
                    size_bytes = f.read(4)
                    size = int.from_bytes(size_bytes, endian)
                    data = f.read(size)
                    f.seek(4, 1)

                    data = data.rstrip(b"\x00")
                    text = data.decode("utf-8", errors="replace")

                    texts.append(text)

        out = os.path.splitext(path)[0] + ".txt"
        if logger: logger(t("saving_txt", path=out))
        try:
            with open(out, "w", encoding="utf-8", newline="\n") as fo:
                for line in texts:
                    fo.write(line + "\n")
        except Exception as e:
            if logger: logger(t("error", err=str(e)), color="#EF4444")
            return None

        if logger: logger(t("extraction_completed", count=len(texts), path=out))
        return out

    except Exception as e:
        if logger: logger(t("error", err=str(e)), color="#EF4444")
        return None

def import_ebm(path):
    try:
        base = os.path.splitext(path)[0]
        txt_path = base + ".txt"
        if not os.path.exists(txt_path):
            if logger: logger(t("error", err=f"TXT não encontrado: {txt_path}"), color="#EF4444")
            return None

        with open(txt_path, "r", encoding="utf-8") as tf:
            raw_lines = [l.rstrip("\n") for l in tf.readlines()]

        is_bsb = path.lower().endswith(".bsb")
        blocks_from_txt = []

        if is_bsb:
            current = None
            for ln in raw_lines:
                if ln.startswith("@"):
                    if current is not None:
                        blocks_from_txt.append(current)
                    current = []
                else:
                    if current is None:
                        current = [ln]
                    else:
                        current.append(ln)
            if current is not None:
                blocks_from_txt.append(current)
        else:
            for ln in raw_lines:
                blocks_from_txt.append([ln])

        with open(path, "rb") as f:
            header_orig = f.read(4)
            if len(header_orig) < 4:
                if logger: logger(t("invalid_header"), color="#EF4444")
                return None

            if header_orig.startswith(b"\x00\x00"):
                endian = "big"
            else:
                endian = "little"

            total = int.from_bytes(header_orig, endian)

            if len(blocks_from_txt) < total:
                if logger: logger(t("error", err=f"TXT tem menos blocos ({len(blocks_from_txt)}) que o total declarado no arquivo ({total})."), color="#EF4444")
                return None

            for i in range(total):
                if is_bsb:
                    choices_bytes = f.read(4)
                    if len(choices_bytes) < 4:
                        if logger: logger(t("error", err=f"Erro ao ler choices no bloco {i}"), color="#EF4444")
                        return None
                    choices = int.from_bytes(choices_bytes, endian)
                    for c in range(choices):
                        size_b = f.read(4)
                        if len(size_b) < 4:
                            if logger: logger(t("error", err=f"Erro ao ler size da escolha {c} no bloco {i}"), color="#EF4444")
                            return None
                        size_orig = int.from_bytes(size_b, endian)
                        f.seek(size_orig, 1)
                else:
                    hdr32 = f.read(32)
                    if len(hdr32) < 32:
                        if logger: logger(t("error", err=f"Erro ao ler header32 do bloco {i}"), color="#EF4444")
                        return None
                    size_b = f.read(4)
                    if len(size_b) < 4:
                        if logger: logger(t("error", err=f"Erro ao ler size do bloco {i}"), color="#EF4444")
                        return None
                    size_orig = int.from_bytes(size_b, endian)
                    f.seek(size_orig, 1)
                    f.seek(4, 1)

        new_blocks = []
        for i in range(total):
            block_texts = blocks_from_txt[i] if i < len(blocks_from_txt) else []
            if is_bsb:
                choices_count = len(block_texts)
                block = choices_count.to_bytes(4, endian)
                for txt in block_texts:
                    b = txt.encode("utf-8")
                    size = len(b) + 1
                    block += size.to_bytes(4, endian)
                    block += b
                    block += b'\x00'
                new_blocks.append(block)
            else:
                new_blocks.append(block_texts[0] if block_texts else "")

        if not is_bsb:
            header32_list = []
            with open(path, "rb") as f:
                f.read(4)
                for i in range(total):
                    hdr32 = f.read(32)
                    if len(hdr32) < 32:
                        if logger: logger(t("error", err=f"Erro ao ler header32 original do bloco {i}"), color="#EF4444")
                        return None
                    header32_list.append(hdr32)
                    size_b = f.read(4)
                    if len(size_b) < 4:
                        if logger: logger(t("error", err=f"Erro ao ler size original do bloco {i} na fase de coleta"), color="#EF4444")
                        return None
                    size_orig = int.from_bytes(size_b, endian)
                    f.seek(size_orig, 1)
                    f.seek(4, 1)

            final_blocks = []
            for i in range(total):
                text = new_blocks[i] if isinstance(new_blocks[i], str) else ""
                b = text.encode("utf-8")
                new_size = len(b) + 1
                blk = header32_list[i] + new_size.to_bytes(4, endian) + b + b'\x00' + b'\x00\x00\x00\x00'
                final_blocks.append(blk)
        else:
            final_blocks = new_blocks

        # Determina a extensão correta e gera o cabeçalho original do zero
        ext = ".bsb" if is_bsb else ".ebm"
        out = base + "_rebuild" + ext
        
        with open(out, "wb") as o:
            # 4 bytes do header (total de textos)
            header_bytes = total.to_bytes(4, endian)
            o.write(header_bytes)
            for blk in final_blocks:
                o.write(blk)

        if logger: logger(t("import_done", path=out))
        return out

    except Exception as e:
        if logger: logger(t("error", err=str(e)), color="#EF4444")
        return None

# -----------------------------
# ELIXIR: export ->
# -----------------------------
def export_elixir(path):
    try:
        with open(path, "rb") as f:

            # Nome base
            nome_arquivo_completo = os.path.basename(path)
            nome_pasta = os.path.splitext(nome_arquivo_completo)[0]

            # Diretório original
            diretorio_original = os.path.dirname(path)

            # Pasta de saída
            caminho_nova_pasta = os.path.join(diretorio_original, nome_pasta)
            os.makedirs(caminho_nova_pasta, exist_ok=True)

            header = f.read(4)
            if len(header) < 4:
                if logger: logger(t("invalid_header"), color="#EF4444")
                return None

            if header.startswith(b"CRAE"):
                endian = "little"
                if logger: logger(t("endian_little"))
            else:
                endian = "big"
                if logger: logger(t("endian_big"))

            # pula bytes desconhecidos
            f.seek(16, 1)

            total_files = int.from_bytes(f.read(4), endian)
            f.seek(4, 1)

            infos = []

            # -----------------------------
            # LER TABELA
            # -----------------------------
            for i in range(total_files):
                offset = int.from_bytes(f.read(4), endian)
                size = int.from_bytes(f.read(4), endian)

                filename_bytes = f.read(48)
                file_name = filename_bytes.split(b'\x00')[0].decode("utf-8", errors="ignore")

                infos.append((offset, size, file_name))

            # -----------------------------
            # EXTRAIR ARQUIVOS
            # -----------------------------
            for i, (offset, size, file_name) in enumerate(infos):

                f.seek(offset)
                data = f.read(size)

                output_path = os.path.join(caminho_nova_pasta, file_name)

                with open(output_path, "wb") as out:
                    out.write(data)

                if logger:
                    logger(f"[{i+1}/{total_files}] {file_name}", color="#4ADE80")

            if logger:
                logger(t("extract_done"), color="#4ADE80")

    except Exception as e:
        if logger:
            logger(str(e), color="#EF4444")


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
            if logger: logger(t("g1t_invalid_magic"), color="#EF4444")
            return None

        version = file_data[pos:pos+4]; pos += 4
        file_size, = struct.unpack(endian_str + 'I', file_data[pos:pos+4]); pos += 4
        header_size, = struct.unpack(endian_str + 'I', file_data[pos:pos+4]); pos += 4
        num_images, = struct.unpack(endian_str + 'I', file_data[pos:pos+4]); pos += 4
        unk14, = struct.unpack(endian_str + 'I', file_data[pos:pos+4]); pos += 4
        unk18, = struct.unpack(endian_str + 'I', file_data[pos:pos+4]); pos += 4

        unk1c = []
        for _ in range(num_images):
            u, = struct.unpack(endian_str + 'I', file_data[pos:pos+4])
            unk1c.append(u); pos += 4

        offsets = []
        for _ in range(num_images):
            o, = struct.unpack(endian_str + 'I', file_data[pos:pos+4])
            offsets.append(o); pos += 4

        base_name = os.path.splitext(path)[0]

        exported = 0
        if logger: logger(t("g1t_export_start"))
        for idx in range(num_images):
            img_pos = header_size + offsets[idx]

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
                img_pos += 12
            else:
                if logger: logger(t("g1t_unhandled_format", pf=is_extended, idx=idx), color="#FACC15")
                continue


            exp_hi = (packed_dim >> 4) & 0xF
            exp_lo = packed_dim & 0xF
            
            if magic == b'G1TG':  # little endian
                width = 1 << exp_hi
                height = 1 << exp_lo
            else:  # G1TG big endian
                height = 1 << exp_hi
                width = 1 << exp_lo

            is_compressed = False
            block_size = 0
            bpp = 0
            dds_fourcc = b'\0\0\0\0'
            use_dx10 = False
            dx10_dxgi = 0

            if pixel_format in [1, 9]:
                is_compressed = False
                block_size = 0
                bpp = 32
                dds_fourcc = b'\0\0\0\0'
            elif pixel_format in [6, 96]:
                is_compressed = True
                block_size = 8
                bpp = 4
                dds_fourcc = b'DXT1'
            elif pixel_format in [8, 98]:
                is_compressed = True
                block_size = 16
                bpp = 8
                dds_fourcc = b'DXT5'
            elif pixel_format == 102:
                is_compressed = True
                block_size = 16
                bpp = 8
                dds_fourcc = b'DX10'
                use_dx10 = True
                dx10_dxgi = 98
            else:
                if logger: logger(t("g1t_unhandled_format", pf=pixel_format, idx=idx), color="#FACC15")
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
                if logger: logger(t("g1t_size_mismatch", got=len(img_data), exp=data_size, idx=idx), color="#FACC15")


            dds = b'DDS '
            hdr_size = 124
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

            dds += struct.pack('<I', hdr_size)
            dds += struct.pack('<I', hdr_flags)
            dds += struct.pack('<I', hdr_height)
            dds += struct.pack('<I', hdr_width)
            dds += struct.pack('<I', pitch_linear)
            dds += struct.pack('<I', hdr_depth)
            dds += struct.pack('<I', hdr_mipcount)
            for r in reserved1:
                dds += struct.pack('<I', r)

            pf_size = 32
            dds_pf_flags = 0
            dds_bitcount = 0
            dds_rmask = dds_gmask = dds_bmask = dds_amask = 0

            if dds_fourcc == b'\0\0\0\0':
                dds_pf_flags = 0x1 | 0x40
                dds_bitcount = 32
                dds_rmask = 0x000000FF
                dds_gmask = 0x0000FF00
                dds_bmask = 0x00FF0000
                dds_amask = 0xFF000000
            else:
                dds_pf_flags = 0x4

            dds += struct.pack('<I', pf_size)
            dds += struct.pack('<I', dds_pf_flags)
            dds += dds_fourcc
            dds += struct.pack('<I', dds_bitcount)
            dds += struct.pack('<I', dds_rmask)
            dds += struct.pack('<I', dds_gmask)
            dds += struct.pack('<I', dds_bmask)
            dds += struct.pack('<I', dds_amask)

            caps1 = 0x1000
            caps2 = caps3 = caps4 = reserved2 = 0
            dds += struct.pack('<I', caps1)
            dds += struct.pack('<I', caps2)
            dds += struct.pack('<I', caps3)
            dds += struct.pack('<I', caps4)
            dds += struct.pack('<I', reserved2)

            if use_dx10:
                dds += struct.pack('<5I', dx10_dxgi, 3, 0, 1, 0)


            header = dds
            
            if pixel_format == 102:

                img_data = process_data(
                    header,
                    img_data,
                    "unswizzle",
                    "BC7"
                )
                dds = img_data
                

            if pixel_format == 98:

                img_data = process_data(
                    header,
                    img_data,
                    "unswizzle",
                    "DXT5"
                )
                dds = img_data

            if pixel_format == 96:

                img_data = process_data(
                    header,
                    img_data,
                    "unswizzle",
                    "DXT1"
                )
                dds = img_data

            else:
                dds += img_data

            out_file = f"{base_name}_{idx}.dds"
            with open(out_file, "wb") as of:
                of.write(dds)

            if logger: logger(t("g1t_export_img", idx=idx, out=out_file))
            exported += 1

        if logger: logger(t("g1t_export_done", count=exported, base=base_name))
        return exported

    except Exception as e:
        if logger: logger(t("error", err=str(e)), color="#EF4444")
        return None

# -----------------------------
# G1T: import <- DDS
# -----------------------------
def import_g1t(path):
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
            if logger: logger(t("g1t_invalid_magic"), color="#EF4444")
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
        if logger: logger(t("g1t_import_start"))

        new_data = bytearray(file_data)

        for idx in range(num_images):
            img_pos = header_size + offsets[idx]
            pixel_format = new_data[img_pos+1]
            packed_dim = new_data[img_pos+2]
            is_extended = new_data[img_pos+7]

            if is_extended == 0:
                img_header_size = 8
            elif is_extended in [1, 16]:
                img_header_size = 20
            else:
                if logger: logger(t("g1t_unhandled_format", pf=is_extended, idx=idx), color="#FACC15")
                continue

            exp_hi = (packed_dim >> 4) & 0xF
            exp_lo = packed_dim & 0xF
            
            if magic == b'G1TG':  # little endian
                width = 1 << exp_hi
                height = 1 << exp_lo
            else:  # G1TG big endian
                height = 1 << exp_hi
                width = 1 << exp_lo

            if pixel_format == 1:
                is_compressed = False
                bpp = 32
                block_size = 0
            elif pixel_format in [6, 96]: 
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
                if logger: logger(t("g1t_unhandled_format", pf=pixel_format, idx=idx), color="#FACC15")
                continue

            if is_compressed:
                num_blocks_w = max(1, (width + 3) // 4)
                num_blocks_h = max(1, (height + 3) // 4)
                data_size = num_blocks_w * num_blocks_h * block_size
            else:
                data_size = width * height * (bpp // 8)

            img_header_real_size = 8
            if is_extended in [1, 16]:
                img_header_real_size = 20

            data_start = header_size + offsets[idx] + img_header_real_size
            data_end = data_start + data_size
            expected_len = data_size

            dds_file = f"{base_name}_{idx}.dds"
            if not os.path.exists(dds_file):
                if logger: logger(t("g1t_txt_missing", base=base_name, idx=idx), color="#FACC15")
                continue

            with open(dds_file, "rb") as df:
                dds_bytes = df.read()

            if len(dds_bytes) < 4 + 124:
                if logger: logger(t("error", err=f"DDS too small: {dds_file}"), color="#FACC15")
                continue
            
            dds_magic = dds_bytes[0:4]
            if dds_magic != b'DDS ':
                if logger: logger(t("error", err=f"Not a DDS: {dds_file}"), color="#FACC15")
                continue

            # Validação de Segurança do DDS vs Formato Original
            fourcc = dds_bytes[84:88]
            expected_fourcc = b'\0\0\0\0'
            
            if pixel_format in [6, 96]: 
                expected_fourcc = b'DXT1'
            elif pixel_format in [8, 98]: 
                expected_fourcc = b'DXT5'
            elif pixel_format == 102: 
                expected_fourcc = b'DX10'
                
            if expected_fourcc != b'\0\0\0\0' and fourcc != expected_fourcc:
                exp_str = expected_fourcc.decode('utf-8').strip()
                if logger: logger(t("g1t_format_mismatch", idx=idx, exp_fcc=exp_str), color="#EF4444")
                continue

            offset_payload = 4 + 124
            if fourcc == b'DX10':
                offset_payload += 20

            if pixel_format == 98:
                
                header_bytes = dds_bytes[:offset_payload]
                image_bytes = dds_bytes[offset_payload:]

                dds_bytes = process_data(
                    header_bytes,
                    image_bytes,
                    "swizzle",
                    "DXT5"
                )

            if pixel_format == 96:
                
                header_bytes = dds_bytes[:offset_payload]
                image_bytes = dds_bytes[offset_payload:]

                dds_bytes = process_data(
                    header_bytes,
                    image_bytes,
                    "swizzle",
                    "DXT1"
                )
                
            if pixel_format == 102:
                
                header_bytes = dds_bytes[:offset_payload]
                image_bytes = dds_bytes[offset_payload:]

                dds_bytes = process_data(
                    header_bytes,
                    image_bytes,
                    "swizzle",
                    "BC7"
                )

            payload = dds_bytes[offset_payload:]

            got = len(payload)
            exp = expected_len

            if got > exp:
                if logger: logger(t("g1t_size_mismatch", got=got, exp=exp, idx=idx), color="#FACC15")
                if logger: logger(f"Skipping image {idx} (DDS larger than expected).", color="#FACC15")
                continue
            elif got < exp:
                if logger: logger(t("g1t_size_mismatch", got=got, exp=exp, idx=idx), color="#FACC15")
                new_payload = payload + (b'\x00' * (exp - got))
            else:
                new_payload = payload

            new_data[data_start:data_end] = new_payload

        out_file = base_name + "_imported.g1t"
        with open(out_file, "wb") as of:
            of.write(new_data)

        if logger: logger(t("g1t_import_done", out=out_file))
        return out_file

    except Exception as e:
        if logger: logger(t("error", err=str(e)), color="#EF4444")
        return None

# -----------------------------
# FLET FILE PICKERS
# -----------------------------

fp_extract_ebm = ft.FilePicker(
    on_result=lambda e: (
        [extract_ebm(f.path) for f in e.files]
        if e.files else logger(t("cancelled"))
    )
)

fp_import_ebm = ft.FilePicker(
    on_result=lambda e: (
        [import_ebm(f.path) for f in e.files]
        if e.files else logger(t("cancelled"))
    )
)

fp_export_g1t = ft.FilePicker(
    on_result=lambda e: (
        [export_g1t(f.path) for f in e.files]
        if e.files else logger(t("cancelled"))
    )
)

fp_import_g1t = ft.FilePicker(
    on_result=lambda e: (
        [import_g1t(f.path) for f in e.files]
        if e.files else logger(t("cancelled"))
    )
)

fp_export_elixir = ft.FilePicker(
    on_result=lambda e: (
        [export_elixir(f.path) for f in e.files]
        if e.files else logger(t("cancelled"))
    )
)

fp_import_elixir = ft.FilePicker(
    on_result=lambda e: (
        [import_elixir(f.path) for f in e.files]
        if e.files else logger(t("cancelled"))
    )
)

# -----------------------------
# REGISTER PLUGIN
# -----------------------------
def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, get_option, current_lang, host_page
    logger = log_func
    get_option = option_getter
    current_lang = host_language or "pt_BR"
    host_page = page

    # Injeta os componentes invisíveis na tela do Flet
    if host_page:
        host_page.overlay.extend([fp_extract_ebm, fp_import_ebm, fp_export_g1t, fp_import_g1t, fp_export_elixir, fp_import_elixir])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "options": [],
        "commands": [
            {
                "label": t("extract_file"),
                "action": lambda: fp_extract_ebm.pick_files(
                    allowed_extensions=["ebm", "bsb"],
                    allow_multiple=True
                )
            },
            {
                "label": t("import_file"),
                "action": lambda: fp_import_ebm.pick_files(
                    allowed_extensions=["ebm", "bsb"],
                    allow_multiple=True
                )
            },
            {
                "label": "G1T → DDS",
                "action": lambda: fp_export_g1t.pick_files(
                    allowed_extensions=["g1t", "g1tg"],
                    allow_multiple=True
                )
            },
            {
                "label": "DDS → G1T",
                "action": lambda: fp_import_g1t.pick_files(
                    allowed_extensions=["g1t", "g1tg"],
                    allow_multiple=True
                )
            },
            {
                "label": "extract elixir",
                "action": lambda: fp_export_elixir.pick_files(
                    allowed_extensions=["elixir"],
                    allow_multiple=True
                )
            },
            {
                "label": "import elixir",
                "action": lambda: fp_import_elixir.pick_files(
                    allowed_extensions=["elixir"],
                    allow_multiple=True
                )
            },
        ]
    }