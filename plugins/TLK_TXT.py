#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dragon Age 2 TLK Converter (Plugin para ALL FOR ONE)
Baseado no código original de hikami / longod
Portado por Antigravity
"""

import os
import struct
import re
from collections import Counter
import heapq
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import flet as ft

# ==============================================================================
# CONFIGURAÇÕES E TRADUÇÕES
# ==============================================================================

PLUGIN_TRANSLATIONS = {
    "pt_BR": {
        "plugin_name": "Dragon Age TLK Tools",
        "plugin_description": "Extrai e reconstrói textos de arquivos TLK (Dragon Age / GFF)",
        "extract_file": "Extrair (TLK → TXT/XML)",
        "rebuild_file": "Recriar (TXT/XML → TLK)",
        "success": "Sucesso",
        "extraction_success": "Textos salvos em: {path}",
        "recreation_success": "TLK reconstruído com sucesso em: {path}",
        "error": "Erro: {error}",
        "cancelled": "Seleção cancelada.",
        "processing": "Processando: {name}...",
        "platform": "Plataforma de destino",
        "text_format": "Formato de texto",
        "select_tlk": "Selecione o arquivo .tlk",
        "select_txt": "Selecione o arquivo .txt/.xml"
    },
    "en_US": {
        "plugin_name": "Dragon Age TLK Tools",
        "plugin_description": "Extracts and reconstructs text from TLK (GFF) files",
        "extract_file": "Extract (TLK → TXT/XML)",
        "rebuild_file": "Rebuild (TXT/XML → TLK)",
        "success": "Success",
        "extraction_success": "Texts saved to: {path}",
        "recreation_success": "TLK successfully rebuilt at: {path}",
        "error": "Error: {error}",
        "cancelled": "Selection cancelled.",
        "processing": "Processing: {name}...",
        "platform": "Target Platform",
        "text_format": "Text Format",
        "select_tlk": "Select .tlk file",
        "select_txt": "Select .txt/.xml file"
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

# ----------------------------------------------------------------------
# Constantes do formato GFF / TLK
# ----------------------------------------------------------------------
GFF_MAGIC = b' FFG'
GFF_VERSION = b'0.4V'
PLATFORM_PC = b' CP '
PLATFORM_X360 = b'063X'
FILE_TYPE_TLK = b' KLT'
FILE_VERSION = b'5.0V'

# Labels de campo (hardcoded do código original)
LABEL_TAG = 19006
LABEL_DICT_OFFSET = 19007
LABEL_BIT_OFFSET = 19008
LABEL_HSTR_ID = 19004
LABEL_HSTR_OFFSET = 19005

# Estruturas binárias
GFF_HEADER_FMT = '>4s4s4s4s4sII'      # big-endian sempre para os primeiros campos
GFF_STRUCT_FMT = '4sIII'
GFF_FIELD_FMT = 'III'
HTLK_FMT = 'III'                       # tag, dictOffset, bitOffset
HSTR_FMT = 'II'                        # id, ptr
HNODE_FMT = 'ii'                       # left, right (signed 32)

# ----------------------------------------------------------------------
# Classes de dados
# ----------------------------------------------------------------------
class TLKEntry:
    def __init__(self, id_str: str = "", text: str = ""):
        self.id = id_str
        self.str = text
        self.offset: int = 0           # usado durante compressão
        self.bits: List[int] = []      # sequência de bits (0/1)

class HuffmanNode:
    def __init__(self, data: Optional[str] = None, count: int = 0,
                 left: 'HuffmanNode' = None, right: 'HuffmanNode' = None):
        self.data = data          # caractere (str de 1 char) ou None para nó interno
        self.count = count
        self.left = left
        self.right = right
        self.id = 0               # usado na serialização

    def __lt__(self, other):
        return self.count < other.count

# ----------------------------------------------------------------------
# Funções de swap (big-endian opcional)
# ----------------------------------------------------------------------
def swap_u32(val: int) -> int:
    """Converte de big para little endian em u32"""
    return struct.unpack('<I', struct.pack('>I', val))[0]

def swap_u16(val: int) -> int:
    return struct.unpack('<H', struct.pack('>H', val))[0]

# ----------------------------------------------------------------------
# Leitura/Escrita de arquivos TLK
# ----------------------------------------------------------------------
class TLKReader:
    def __init__(self, data: bytes, is_x360: bool = False):
        self.data = data
        self.pos = 0
        self.is_x360 = is_x360

    def read_struct(self, fmt: str):
        size = struct.calcsize(fmt)
        raw = self.data[self.pos:self.pos+size]
        self.pos += size
        if self.is_x360:
            pass
        return struct.unpack(fmt, raw)

    def read_u32(self):
        return self.read_struct('<I')[0]

    def read_s32(self):
        return self.read_struct('<i')[0]

class TLKFile:
    def __init__(self):
        self.entries: List[TLKEntry] = []
        self.dict_raw: List[Tuple[int, int]] = []   # (left, right)
        self.bits_raw: List[int] = []                # lista de bits
        # Metadados do formato PC V0.2 (preservados para reescrita fiel)
        self._pc_v02_unk: int = 4          # u32 @ data_base+0 (normalmente 4)
        self._pc_v02_raw_index: Optional[List[Tuple[int,int]]] = None  # todos os pares (id, ptr) incluindo nulos

    @staticmethod
    def from_binary(filepath: str, log_func=print) -> 'TLKFile':
        with open(filepath, 'rb') as f:
            data = f.read()

        tlk = TLKFile()
        log_func("=== Diagnóstico do cabeçalho (TLK) ===")

        # --- Leitura dos campos ---
        pos = 0
        magic, version, platform, filetype, filever = struct.unpack_from('>4s4s4s4s4s', data, pos)
        pos += struct.calcsize('>4s4s4s4s4s')

        # Determinar endianness baseado na plataforma
        is_big_endian = platform in [b'063X', b'X360', b'PS3 ']

        if is_big_endian:
            struct_count, data_offset = struct.unpack_from('>II', data, pos)
        else:
            struct_count, data_offset = struct.unpack_from('<II', data, pos)
        pos += struct.calcsize('<II')

        log_func(f"Magic       : {magic} (hex: {magic.hex()})")
        log_func(f"Version     : {version} (hex: {version.hex()})")
        log_func(f"Platform    : {platform} (hex: {platform.hex()})")
        log_func(f"FileType    : {filetype} (hex: {filetype.hex()})")
        log_func(f"FileVersion : {filever} (hex: {filever.hex()})")
        log_func(f"StructCount : {struct_count}")
        log_func(f"DataOffset  : {data_offset}")

        # --- Validação detalhada ---
        erros = []

        valid_magics = [b'GFF ', b' FFG']
        if magic not in valid_magics:
            erros.append(f"Magic inválido: {magic.hex()}. Esperado um de {[m.hex() for m in valid_magics]}")

        valid_versions = [b'V4.0', b'0.4V']
        if version not in valid_versions:
            erros.append(f"Version inválida: {version}. Esperado {valid_versions}")

        valid_platforms = [b' CP ', b'063X', b'PC  ', b'X360', b'PS3 ']
        if platform not in valid_platforms:
            erros.append(f"Platform inválida: {platform}. Esperado um de {valid_platforms}")

        valid_filetypes = [b' KLT', b'TLK ', b'TALK']
        if filetype not in valid_filetypes:
            erros.append(f"FileType inválido: {filetype}. Esperado um de {valid_filetypes}")

        valid_filevers = [b'5.0V', b'V0.5', b'3.0V', b'V0.3', b'1.0V', b'V0.1', b'V0.2']
        if filever not in valid_filevers:
            log_func(f"Aviso: FileVersion '{filever}' não está na lista conhecida. Tentando continuar...")
        else:
            log_func(f"FileVersion reconhecido: {filever}")

        if erros:
            raise ValueError("Falha na validação do cabeçalho:\n" + "\n".join(erros))

        # --- PC V0.2: formato simples, sem Huffman, strings UTF-16 LE ---
        if magic == b'GFF ' and platform == b'PC  ' and filever == b'V0.2':
            log_func("Formato detectado: GFF V4.0 PC / TLK V0.2 (sem compressão, UTF-16 LE)")
            data_base = data_offset
            unk_val = struct.unpack_from('<I', data, data_base)[0]
            total_entries = struct.unpack_from('<I', data, data_base + 4)[0]
            log_func(f"Campo TLK @ {data_base}: {unk_val}")
            log_func(f"Total de entradas @ {data_base + 4}: {total_entries}")
            entries_start = data_base + 8
            tlk.entries = []
            raw_index: List[Tuple[int, int]] = []
            for i in range(total_entries):
                pos_e = entries_start + i * 8
                if pos_e + 8 > len(data):
                    break
                str_id = struct.unpack_from('<I', data, pos_e)[0]
                ptr = struct.unpack_from('<I', data, pos_e + 4)[0]
                raw_index.append((str_id, ptr))
                if str_id == 0xFFFFFFFF or ptr == 0xFFFFFFFF:
                    continue
                abs_off = data_base + ptr
                if abs_off + 4 > len(data):
                    continue
                char_count = struct.unpack_from('<I', data, abs_off)[0]
                read_chars = max(0, char_count - 1)
                text_end = abs_off + 4 + read_chars * 2
                if text_end > len(data):
                    text_end = len(data)
                text = data[abs_off + 4:text_end].decode('utf-16-le', errors='replace')
                tlk.entries.append(TLKEntry(id_str=str(str_id), text=text))
            tlk._pc_v02_unk = unk_val
            tlk._pc_v02_raw_index = raw_index
            
            null_count = sum(1 for s, p in raw_index if s == 0xFFFFFFFF or p == 0xFFFFFFFF)
            if null_count:
                log_func(f"Total de strings lidas: {len(tlk.entries)} ({null_count} nulas preservadas)")
            else:
                log_func(f"Total de strings lidas: {len(tlk.entries)}")
            return tlk

        # --- Leitura dos dados internos (HTLK, dicionário, etc.) ---
        endian_fmt = '>' if is_big_endian else '<'

        def read_u32(offset):
            return struct.unpack_from(f'{endian_fmt}I', data, offset)[0]

        # Posição do bloco HTLK
        htlk_pos = data_offset
        tag, dict_offset_rel, bit_offset_rel = struct.unpack_from(f'{endian_fmt}III', data, htlk_pos)
        log_func(f"HTLK tag: 0x{tag:08x}, dict_offset={dict_offset_rel}, bit_offset={bit_offset_rel}")

        # Dicionário da árvore de Huffman
        dict_start = htlk_pos + dict_offset_rel
        dict_len = read_u32(dict_start)
        log_func(f"Dicionário: número de u32 = {dict_len}")
        nodes = []
        for i in range(dict_len // 2):
            left = read_u32(dict_start + 4 + i * 8)
            right = read_u32(dict_start + 4 + i * 8 + 4)
            nodes.append((left, right))

        # Bits compactados
        bit_start = htlk_pos + bit_offset_rel
        bit_len = read_u32(bit_start)
        log_func(f"Bit array: número de u32 = {bit_len}")
        bit_array_u32 = []
        for i in range(bit_len):
            val = read_u32(bit_start + 4 + i * 4)
            bit_array_u32.append(val)

        # Converter u32 para lista de bits (ordem LSB primeiro)
        bit_list = []
        for val in bit_array_u32:
            for _ in range(32):
                bit_list.append(val & 1)
                val >>= 1

        # Tabela de strings (HSTR)
        str_len = read_u32(htlk_pos + 12)
        hstr_start = htlk_pos + 12 + 4
        log_func(f"HSTR: {str_len} entradas")
        hstr_entries = []
        for i in range(str_len):
            hid = read_u32(hstr_start + i * 8)
            hptr = read_u32(hstr_start + i * 8 + 4)
            if hid != 0xFFFFFFFF and hptr != 0xFFFFFFFF:
                hstr_entries.append((hid, hptr))

        # Decodificação das strings usando a árvore de Huffman
        def decode_string(start_bit):
            s = []
            cur = len(nodes) - 1
            i = start_bit
            while i < len(bit_list):
                bit = bit_list[i]
                left, right = nodes[cur]
                nxt = left if bit == 0 else right
                if nxt & 0x80000000:  # folha
                    char_code = 0xFFFFFFFF - nxt
                    if char_code == 0:
                        return (i + 1, ''.join(s))
                    try:
                        s.append(chr(char_code))
                    except ValueError:
                        s.append('\ufffd')
                    cur = len(nodes) - 1
                else:
                    cur = nxt
                i += 1
            return (i + 1, ''.join(s))

        tlk.entries = []
        for hid, offset in hstr_entries:
            _, text = decode_string(offset)
            tlk.entries.append(TLKEntry(id_str=str(hid), text=text))

        log_func(f"Total de strings decodificadas: {len(tlk.entries)}")
        return tlk

    @staticmethod
    def to_binary_pc_v02(entries: List[TLKEntry], tlk_src: 'TLKFile' = None) -> bytes:
        if not entries:
            raise ValueError("Nenhuma entrada para comprimir.")

        id_map: Dict[str, str] = {e.id: e.str for e in entries}

        DATA_BASE = 96
        unk_val = tlk_src._pc_v02_unk if tlk_src and tlk_src._pc_v02_unk is not None else 4

        if tlk_src and tlk_src._pc_v02_raw_index:
            raw_index = tlk_src._pc_v02_raw_index
            N = len(raw_index)
            str_pool_rel_start = 8 + N * 8
        else:
            id_entries = []
            for e in entries:
                try:
                    id_int = int(e.id)
                except ValueError:
                    raise ValueError(f"ID inválido: {e.id}")
                id_entries.append((id_int, e.str))
            id_entries.sort(key=lambda x: x[0])
            raw_index = [(id_int, None) for id_int, _ in id_entries]
            N = len(raw_index)
            str_pool_rel_start = 8 + N * 8

        string_pool = bytearray()
        cache: Dict[str, int] = {}
        final_index: List[Tuple[int, int]] = []

        for str_id_raw, ptr_orig in raw_index:
            id_str = str(str_id_raw)
            if str_id_raw == 0xFFFFFFFF or ptr_orig == 0xFFFFFFFF:
                final_index.append((str_id_raw, 0xFFFFFFFF))
                continue
            if id_str in id_map:
                text = id_map[id_str]
            else:
                final_index.append((0xFFFFFFFF, 0xFFFFFFFF))
                continue

            if text in cache:
                ptr = cache[text]
            else:
                ptr = str_pool_rel_start + len(string_pool)
                cache[text] = ptr
                char_count = len(text) + 1
                encoded = struct.pack('<I', char_count) + text.encode('utf-16-le') + b'\x00\x00'
                string_pool.extend(encoded)
                padding = (-len(string_pool)) % 4
                if padding:
                    string_pool.extend(b'\xFF' * padding)

            final_index.append((str_id_raw, ptr))

        out = bytearray()
        out.extend(struct.pack('>4s4s4s4s4s', b'GFF ', b'V4.0', b'PC  ', b'TLK ', b'V0.2'))
        out.extend(struct.pack('<II', 2, DATA_BASE))

        out.extend(struct.pack('>4s', b'TLK '))
        out.extend(struct.pack('<III', 1, 60, 4))
        out.extend(struct.pack('>4s', b'STRN'))
        out.extend(struct.pack('<III', 2, 72, 8))

        out.extend(struct.pack('<III', 19001, 0xc0000001, 0))
        out.extend(struct.pack('<III', 19002, 0x00000004, 0))
        out.extend(struct.pack('<III', 19003, 0x0000000e, 4))

        assert len(out) == DATA_BASE

        out.extend(struct.pack('<I', unk_val))
        out.extend(struct.pack('<I', N))
        for str_id_val, ptr_val in final_index:
            out.extend(struct.pack('<II', str_id_val, ptr_val))

        out.extend(string_pool)
        return bytes(out)

    @staticmethod
    def to_binary(entries: List[TLKEntry], target_platform: str = "pc") -> bytes:
        if not entries:
            raise ValueError("Nenhuma entrada para comprimir.")

        if target_platform == "pc_v02":
            return TLKFile.to_binary_pc_v02(entries)

        if target_platform == "ps3":
            magic = b'GFF '
            version = b'V4.0'
            platform = b'PS3 '
            filetype = b'TLK '
            filever = b'V0.5'
            endian = '>'
            htlk_struct_type = b'HTLK'
            hstr_struct_type = b'HSTR'
        elif target_platform == "x360":
            magic = b' FFG'
            version = b'0.4V'
            platform = b'063X'
            filetype = b' KLT'
            filever = b'5.0V'
            endian = '>'
            htlk_struct_type = b'KLTH'
            hstr_struct_type = b'RTSH'
        else:
            magic = b' FFG'
            version = b'0.4V'
            platform = b' CP '
            filetype = b' KLT'
            filever = b'5.0V'
            endian = '<'
            htlk_struct_type = b'KLTH'
            hstr_struct_type = b'RTSH'

        # Coletar caracteres e contar frequências
        freq = Counter()
        cache_offset: Dict[str, Tuple[int, List[int]]] = {}
        final_entries = []

        id_entries = []
        for e in entries:
            try:
                id_int = int(e.id)
            except ValueError:
                raise ValueError(f"ID inválido: {e.id}")
            id_entries.append((id_int, e.str))
            
        id_entries.sort(key=lambda x: x[0])

        for _, s in id_entries:
            for ch in s:
                freq[ch] += 1
            freq['\0'] += 1

        if not freq:
            raise ValueError("Nenhum caractere para comprimir.")

        # Construir árvore de Huffman
        heap = [HuffmanNode(data=ch, count=c) for ch, c in freq.items()]
        heapq.heapify(heap)
        while len(heap) > 1:
            left = heapq.heappop(heap)
            right = heapq.heappop(heap)
            parent = HuffmanNode(count=left.count + right.count, left=left, right=right)
            heapq.heappush(heap, parent)
        root = heap[0]

        # Gerar códigos de Huffman
        codes: Dict[str, List[int]] = {}
        def traverse(node, code):
            if node.data is not None:
                codes[node.data] = code.copy()
            else:
                code.append(0)
                traverse(node.left, code)
                code.pop()
                code.append(1)
                traverse(node.right, code)
                code.pop()
        traverse(root, [])

        null_code = codes['\0']

        offset = 0
        for id_int, s in id_entries:
            if s in cache_offset:
                off = cache_offset[s][0]
                bits = []
            else:
                off = offset
                bits = []
                for ch in s:
                    bits.extend(codes[ch])
                bits.extend(null_code)
                offset += len(bits)
                cache_offset[s] = (off, bits)
            final_entries.append((id_int, s, off, bits))

        hstr_raw = []
        for id_int, _, off, _ in final_entries:
            hstr_raw.append((id_int, off))

        all_bits = []
        for _, _, _, bits in final_entries:
            all_bits.extend(bits)

        bit_array_u32 = []
        for i in range(0, len(all_bits), 32):
            chunk = all_bits[i:i+32]
            val = 0
            for j, bit in enumerate(chunk):
                val |= (bit << j)
            bit_array_u32.append(val)
        if not bit_array_u32:
            bit_array_u32.append(0)

        queue = [root]
        index = 0
        indices = []
        while queue:
            node = queue.pop(0)
            if node.left == node.right:
                node.id = 0xFFFFFFFF - ord(node.data)
            else:
                node.id = index
                index += 1
                indices.insert(0, node)
            if node.right:
                queue.append(node.right)
            if node.left:
                queue.append(node.left)

        dsize = len(indices)
        dict_nodes = []
        for node in indices:
            l = node.left.id
            r = node.right.id
            if not (l & 0x80000000):
                node.left.id = (dsize - 1) - l
            if not (r & 0x80000000):
                node.right.id = (dsize - 1) - r
            dict_nodes.append((node.left.id, node.right.id))

        dict_length = len(dict_nodes) * 2
        dict_raw = []
        for left, right in dict_nodes:
            dict_raw.extend([left, right])

        htlk_size = struct.calcsize(f'{endian}III')
        hstr_count = len(hstr_raw)
        hstr_size = hstr_count * 8
        dict_data_size = len(dict_raw) * 4
        bits_size = len(bit_array_u32)

        dict_offset_rel = htlk_size + 4 + hstr_size
        bit_offset_rel = dict_offset_rel + 4 + dict_data_size

        out = bytearray()
        out.extend(struct.pack('>4s4s4s4s4s', magic, version, platform, filetype, filever))
        out.extend(struct.pack(f'{endian}II', 2, 0))

        out.extend(struct.pack('>4s', htlk_struct_type))
        out.extend(struct.pack(f'{endian}III', 3, 60, 12))
        
        out.extend(struct.pack('>4s', hstr_struct_type))
        out.extend(struct.pack(f'{endian}III', 2, 96, 8))

        out.extend(struct.pack(f'{endian}III', 19006, 0xc0000001, 0))
        out.extend(struct.pack(f'{endian}III', 19007, 0x80000005, 4))
        out.extend(struct.pack(f'{endian}III', 19008, 0x80000004, 8))
        out.extend(struct.pack(f'{endian}III', 19004, 0x00000004, 0))
        out.extend(struct.pack(f'{endian}III', 19005, 0x00000004, 4))

        data_offset = len(out)
        struct.pack_into(f'{endian}I', out, 20 + 4, data_offset)

        out.extend(struct.pack(f'{endian}III', 0x0000000c, dict_offset_rel, bit_offset_rel))

        out.extend(struct.pack(f'{endian}I', hstr_count))
        for hid, ptr in hstr_raw:
            out.extend(struct.pack(f'{endian}II', hid, ptr))

        out.extend(struct.pack(f'{endian}I', dict_length))
        for val in dict_raw:
            out.extend(struct.pack(f'{endian}I', val & 0xFFFFFFFF))

        out.extend(struct.pack(f'{endian}I', bits_size))
        for val in bit_array_u32:
            out.extend(struct.pack(f'{endian}I', val))

        return bytes(out)

# ----------------------------------------------------------------------
# Parsers de texto (TXT -> lista de TLKEntry)
# ----------------------------------------------------------------------
def parse_txt(text: str) -> List[TLKEntry]:
    entries = []
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('{') and line.endswith('}'):
            id_str = line[1:-1].strip()
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip() != '':
                text_lines.append(lines[i].rstrip('\r\n'))
                i += 1
            text_block = '\n'.join(text_lines)
            text_block = text_block.replace('\\n', '\n').replace('\\r', '\r')
            entries.append(TLKEntry(id_str=id_str, text=text_block))
        i += 1
    return entries

def parse_troika(text: str) -> List[TLKEntry]:
    entries = []
    pattern = r'\{(.*?)\}\s*\r?\n\{((?:[^}]|\}[^\{])*)\}'
    matches = re.findall(pattern, text, re.DOTALL)
    for id_str, txt in matches:
        entries.append(TLKEntry(id_str=id_str.strip(), text=txt.strip()))
    return entries

def parse_xml(text: str) -> List[TLKEntry]:
    entries = []
    try:
        root = ET.fromstring(text)
        for elem in root.findall('tlkElement'):
            id_elem = elem.find('tlkID')
            str_elem = elem.find('tlkString')
            if id_elem is not None and str_elem is not None:
                entries.append(TLKEntry(id_str=id_elem.text, text=str_elem.text or ""))
    except ET.ParseError:
        entries = []
        i = 0
        while i < len(text):
            start = text.find('<tlkElement>', i)
            if start == -1: break
            end = text.find('</tlkElement>', start)
            if end == -1: break
            chunk = text[start:end+len('</tlkElement>')]
            id_start = chunk.find('<tlkID>')
            id_end = chunk.find('</tlkID>')
            str_start = chunk.find('<tlkString>')
            str_end = chunk.find('</tlkString>')
            if id_start != -1 and str_start != -1:
                id_str = chunk[id_start+7:id_end].strip()
                txt = chunk[str_start+11:str_end].strip()
                entries.append(TLKEntry(id_str=id_str, text=txt))
            i = end + 1
    return entries

# ==============================================================================
# LÓGICA DE NEGÓCIO DO PLUGIN
# ==============================================================================

def run_extraction(filepath):
    try:
        path = Path(filepath)
        logger(t("processing", name=path.name), color=COLOR_LOG_YELLOW)

        # Obter o formato de texto das opções
        fmt_label = get_option("text_format")
        fmt_map = {
            "Padrão (DAO Toolset)": "default",
            "XML": "xml",
            "Troika (aninhado)": "troika"
        }
        fmt = fmt_map.get(fmt_label, "default")

        # Ler e decodificar o TLK
        tlk = TLKFile.from_binary(str(path), lambda msg: logger(msg, color=COLOR_LOG_YELLOW))
        entries = tlk.entries

        # Gerar o texto de saída
        output_lines = []
        if fmt == "xml":
            output_lines.append('<?xml version="1.0" encoding="UTF-16"?>')
            output_lines.append('<tlkList>')
            for e in entries:
                output_lines.append('  <tlkElement>')
                output_lines.append(f'    <tlkID>{e.id}</tlkID>')
                safe_text = e.str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                output_lines.append(f'    <tlkString>{safe_text}</tlkString>')
                output_lines.append('  </tlkElement>')
            output_lines.append('</tlkList>')
            text_out = '\n'.join(output_lines)
            outpath = path.with_suffix('.xml')
            with open(outpath, 'wb') as f:
                f.write(b'\xff\xfe')
                f.write(text_out.encode('utf-16-le'))
        elif fmt == "troika":
            for e in entries:
                output_lines.append('{' + e.id + '}')
                output_lines.append('{' + e.str + '}')
                output_lines.append('')
            text_out = '\r\n'.join(output_lines)
            outpath = path.with_suffix('.txt')
            with open(outpath, 'wb') as f:
                f.write(b'\xff\xfe')
                f.write(text_out.encode('utf-16-le'))
        else:  # default DAO format
            for e in entries:
                escaped = e.str.replace('\r', '\\r').replace('\n', '\\n')
                output_lines.append('{' + e.id + '}')
                output_lines.append(escaped)
                output_lines.append('')
            text_out = '\r\n'.join(output_lines)
            outpath = path.with_suffix('.txt')
            with open(outpath, 'wb') as f:
                f.write(b'\xff\xfe')
                f.write(text_out.encode('utf-16-le'))

        logger(t("extraction_success", path=outpath.name), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("error", error=str(e)), color=COLOR_LOG_RED)

def run_rebuild(filepath):
    try:
        path = Path(filepath)
        logger(t("processing", name=path.name), color=COLOR_LOG_YELLOW)

        # Ler arquivo de entrada como UTF-16 LE
        with open(path, 'rb') as f:
            raw = f.read()
        if raw[:2] == b'\xff\xfe':
            text = raw[2:].decode('utf-16-le')
        else:
            text = raw.decode('utf-8-sig')
            logger("Aviso: Arquivo de entrada sem BOM UTF-16, interpretado como UTF-8.", color=COLOR_LOG_YELLOW)

        # Obter o formato de texto das opções
        fmt_label = get_option("text_format")
        fmt_map = {
            "Padrão (DAO Toolset)": "default",
            "XML": "xml",
            "Troika (aninhado)": "troika"
        }
        fmt = fmt_map.get(fmt_label, "default")

        if fmt == "xml":
            entries = parse_xml(text)
        elif fmt == "troika":
            entries = parse_troika(text)
        else:
            entries = parse_txt(text)

        if not entries:
            raise ValueError("Nenhuma entrada válida encontrada no arquivo de texto.")

        # Obter plataforma das opções
        plat_label = get_option("platform")
        plat_map = {
            "PC (V0.2 - sem compressão)": "pc_v02",
            "PC (V0.5 - Huffman)": "pc",
            "Xbox 360": "x360",
            "PS3": "ps3"
        }
        plat = plat_map.get(plat_label, "pc_v02")

        # Gerar o arquivo .tlk na mesma pasta (como new.tlk ou com sufixo _new.tlk)
        outpath = path.with_name(path.stem + ".tlk")

        if plat == 'pc_v02':
            # Tenta carregar TLK original para preservar os índices e nulos
            base_no_ext = str(path.with_suffix(''))
            for suffix in ('_new', '_traduzido', '_pt', '_ptbr'):
                if base_no_ext.endswith(suffix):
                    base_no_ext = base_no_ext[:-len(suffix)]
                    break
            orig_tlk = base_no_ext + '.tlk'
            tlk_src = None
            if os.path.isfile(orig_tlk):
                try:
                    tlk_src = TLKFile.from_binary(orig_tlk, lambda x: None)
                    logger(f"TLK original carregado para preservar índice: {os.path.basename(orig_tlk)}", color=COLOR_LOG_GREEN)
                except Exception:
                    tlk_src = None
            if tlk_src is None:
                logger("Aviso: TLK original não encontrado. Índice será gerado sem entradas nulas.", color=COLOR_LOG_YELLOW)
            
            bin_data = TLKFile.to_binary_pc_v02(entries, tlk_src)
        else:
            bin_data = TLKFile.to_binary(entries, plat)

        with open(outpath, 'wb') as f:
            f.write(bin_data)

        logger(t("recreation_success", path=outpath.name), color=COLOR_LOG_GREEN)
    except Exception as e:
        logger(t("error", error=str(e)), color=COLOR_LOG_RED)

# ==============================================================================
# FILEPICKERS GLOBAIS
# ==============================================================================


def on_extract_result(e: ft.FilePickerResultEvent):

    if e.path:

        arquivos = list(Path(e.path).rglob("*.tlk"))

        if not arquivos:
            logger("Nenhum arquivo .tlk encontrado", color=COLOR_LOG_YELLOW)
            return

        for f in arquivos:
            run_extraction(str(f))

    else:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)


def on_rebuild_result(e: ft.FilePickerResultEvent):

    if e.path:

        arquivos_txt = list(Path(e.path).rglob("*.txt"))
        arquivos_xml = list(Path(e.path).rglob("*.xml"))

        arquivos = arquivos_txt + arquivos_xml

        if not arquivos:
            logger("Nenhum arquivo .txt ou .xml encontrado", color=COLOR_LOG_YELLOW)
            return

        for f in arquivos:
            run_rebuild(str(f))

    else:
        logger(t("cancelled"), color=COLOR_LOG_YELLOW)


fp_extract = ft.FilePicker(on_result=on_extract_result)
fp_rebuild = ft.FilePicker(on_result=on_rebuild_result)


def action_extract_tlk():

    fp_extract.get_directory_path(
        dialog_title=t("select_tlk")
    )


def action_rebuild_tlk():

    fp_rebuild.get_directory_path(
        dialog_title=t("select_txt")
    )

# ==============================================================================
# ENTRY POINT DO PLUGIN
# ==============================================================================

def register_plugin(log_func, option_getter, host_language="pt_BR", page=None):
    global logger, get_option, current_lang, host_page
    logger = log_func
    get_option = option_getter
    current_lang = host_language
    host_page = page

    if host_page:
        host_page.overlay.extend([fp_extract, fp_rebuild])
        host_page.update()

    return {
        "name": t("plugin_name"),
        "description": t("plugin_description"),
        "options": [
            {
                "name": "platform",
                "label": t("platform"),
                "type": "dropdown",
                "values": [
                    "PC (V0.2 - sem compressão)",
                    "PC (V0.5 - Huffman)",
                    "Xbox 360",
                    "PS3"
                ],
                "default": "PC (V0.2 - sem compressão)"
            },
            {
                "name": "text_format",
                "label": t("text_format"),
                "type": "dropdown",
                "values": [
                    "Padrão (DAO Toolset)",
                    "XML",
                    "Troika (aninhado)"
                ],
                "default": "Padrão (DAO Toolset)"
            }
        ],
        "commands": [
            {"label": t("extract_file"), "action": action_extract_tlk},
            {"label": t("rebuild_file"), "action": action_rebuild_tlk},
        ]
    }
