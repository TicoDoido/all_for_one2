# huffman.py — Codec Coalesced
# Por OALEEX
from __future__ import annotations
import struct
import heapq
from typing import Dict, Iterable, List, Sequence, Tuple

# Constantes
MARCADORES_VAZIOS = {0x00000000, 0xFFFFFFFF}
SIMBOLO_INTERNO = 0xFFFF

# ---------- primitivas de leitura/escrita ----------
def ler_u16be(dados: bytes, posicao: int) -> int:
    return struct.unpack_from(">H", dados, posicao)[0]

def ler_u32be(dados: bytes, posicao: int) -> int:
    return struct.unpack_from(">I", dados, posicao)[0]

def gravar_u16be(valor: int) -> bytes:
    return struct.pack(">H", valor)

def gravar_u32be(valor: int) -> bytes:
    return struct.pack(">I", valor & 0xFFFFFFFF)

def inverter32(valor: int) -> int:
    return (~valor) & 0xFFFFFFFF

# ---------- conversão UTF-16 ----------
def unidades_utf16_de_texto(texto: str) -> List[int]:
    bruto = texto.encode("utf-16-le")
    return [bruto[i] | (bruto[i + 1] << 8) for i in range(0, len(bruto), 2)]

def texto_de_unidades_utf16(unidades: Sequence[int]) -> str:
    bruto = bytearray()
    for unidade in unidades:
        bruto.extend(struct.pack("<H", unidade))
    return bruto.decode("utf-16-le")

# ---------- nó da árvore ----------
class NoArvore:
    __slots__ = ("simbolo", "esquerda", "direita")
    def __init__(self, simbolo: int, esquerda: int, direita: int):
        self.simbolo = simbolo
        self.esquerda = esquerda
        self.direita = direita

# ---------- Codec Coalesced (Huffman) ----------
class CodecCoalesced:
    def __init__(self, nos: Sequence[NoArvore]):
        if not nos:
            raise ValueError("arvore vazia")
        self.nos = list(nos)
        self.mapa_codigos = self._montar_mapa_codigos()

    @classmethod
    def de_cabecalho(cls, cabecalho: bytes) -> "CodecCoalesced":
        if len(cabecalho) < 4:
            raise ValueError("cabecalho pequeno demais")
        quantidade_nos = ler_u32be(cabecalho, 0)
        tamanho_esperado = 4 + quantidade_nos * 6
        if len(cabecalho) != tamanho_esperado:
            raise ValueError(
                f"cabecalho com tamanho inesperado: esperado {tamanho_esperado}, veio {len(cabecalho)}"
            )
        posicao = 4
        nos = []
        for _ in range(quantidade_nos):
            simbolo, esq, direita = struct.unpack_from(">HHH", cabecalho, posicao)
            nos.append(NoArvore(simbolo, esq, direita))
            posicao += 6
        return cls(nos)

    @classmethod
    def de_textos(cls, textos: Iterable[str]) -> "CodecCoalesced":
        frequencias: Dict[int, int] = {}
        for texto in textos:
            for unidade in unidades_utf16_de_texto(texto):
                frequencias[unidade] = frequencias.get(unidade, 0) + 1
            frequencias[0] = frequencias.get(0, 0) + 1
        if not frequencias:
            frequencias[0] = 1
        fila = []
        serial = 0
        for simbolo, freq in sorted(frequencias.items()):
            heapq.heappush(fila, (freq, serial, ("folha", simbolo)))
            serial += 1
        while len(fila) > 1:
            a = heapq.heappop(fila)
            b = heapq.heappop(fila)
            soma = a[0] + b[0]
            heapq.heappush(fila, (soma, serial, ("interno", a[2], b[2])))
            serial += 1
        raiz = fila[0][2]

        nos_temp = []
        def despejar(no) -> int:
            indice = len(nos_temp)
            nos_temp.append(None)
            tipo = no[0]
            if tipo == "folha":
                nos_temp[indice] = NoArvore(no[1], SIMBOLO_INTERNO, SIMBOLO_INTERNO)
                return indice
            esq = despejar(no[1])
            direita = despejar(no[2])
            nos_temp[indice] = NoArvore(SIMBOLO_INTERNO, esq, direita)
            return indice

        idx_raiz = despejar(raiz)
        if idx_raiz != 0:
            raise RuntimeError("raiz inesperada")
        return cls([n for n in nos_temp if n is not None])

    def para_cabecalho(self) -> bytes:
        saida = bytearray()
        saida.extend(gravar_u32be(len(self.nos)))
        for no in self.nos:
            saida.extend(struct.pack(">HHH", no.simbolo, no.esquerda, no.direita))
        return bytes(saida)

    def _montar_mapa_codigos(self) -> Dict[int, str]:
        mapa = {}
        def passear(indice: int, bits: str):
            no = self.nos[indice]
            if no.simbolo != SIMBOLO_INTERNO:
                mapa[no.simbolo] = bits or "0"
                return
            passear(no.esquerda, bits + "0")
            passear(no.direita, bits + "1")
        passear(0, "")
        return mapa

    def decodificar_unidades_huffman(self, dados: bytes, inicio: int, qtd: int) -> Tuple[List[int], int]:
        unidades = []
        idx_no = 0
        pos = inicio
        while len(unidades) < qtd:
            if pos >= len(dados):
                raise ValueError("fim inesperado na decodificação Huffman")
            byte = dados[pos]
            pos += 1
            for bit_i in range(8):
                bit = (byte >> bit_i) & 1
                idx_no = self.nos[idx_no].esquerda if bit == 0 else self.nos[idx_no].direita
                no = self.nos[idx_no]
                if no.simbolo != SIMBOLO_INTERNO:
                    unidades.append(no.simbolo)
                    idx_no = 0
                    if len(unidades) >= qtd:
                        break
        return unidades, pos - inicio

    def codificar_unidades_huffman(self, unidades: Sequence[int]) -> bytes:
        bits = []
        for u in unidades:
            codigo = self.mapa_codigos[u]
            bits.extend(1 if c == "1" else 0 for c in codigo)
        saida = bytearray()
        byte_atual = 0
        pos_bit = 0
        for bit in bits:
            if bit:
                byte_atual |= 1 << pos_bit
            pos_bit += 1
            if pos_bit == 8:
                saida.append(byte_atual)
                byte_atual = 0
                pos_bit = 0
        if pos_bit:
            saida.append(byte_atual)
        return bytes(saida)