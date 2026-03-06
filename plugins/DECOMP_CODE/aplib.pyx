# aPLib implementation converted to Cython
# File: aplib_cython.pyx
#
# Build instructions (create setup.py as shown below, then run:)
#   python setup.py build_ext --inplace
#
# Example setup.py:
# ------------------
# from setuptools import setup
# from Cython.Build import cythonize
#
# setup(
#     name="aplib_cython",
#     ext_modules=cythonize(["aplib_cython.pyx"], annotate=True),
# )
# ------------------
# The annotate=True option generates an HTML file showing which parts were C-accelerated.

# Notes:
# - This conversion aims to keep the original algorithm and behavior exactly, while
#   adding Cython type hints to speed up hot paths.
# - The implementation still uses Python-level bytearray/bytes operations for clarity
#   and to maintain exact semantics. If you need even more speed, critical inner loops
#   can be rewritten using memoryviews and pure C loops.

from cpython.bytes cimport PyBytes_FromStringAndSize
cimport cython
from libc.stdint cimport uint8_t, uint64_t
from libc.stdlib cimport malloc, free

# ----------------------------
# Helpers
# ----------------------------

cdef inline bytes int2lebin(unsigned long long value, Py_ssize_t size):
    """Retorna o valor em bytes little-endian com tamanho 'size'."""
    cdef bytearray result = bytearray(size)
    cdef Py_ssize_t i
    for i in range(size):
        result[i] = <uint8_t>((value >> (8 * i)) & 0xFF)
    return bytes(result)


cdef inline bytearray modifybuffer(bytearray buf, bytes sub, Py_ssize_t offset):
    """Substitui em 'buf' (bytearray) os bytes a partir do offset por 'sub'."""
    buf[offset:offset + len(sub)] = sub
    return buf


cdef inline int getbinlen(unsigned long long value):
    """Retorna o número de bits necessários para representar 'value'."""
    cdef int result = 0
    if value == 0:
        return 1
    while value:
        value >>= 1
        result += 1
    return result


cdef inline int lengthdelta(unsigned long long offset):
    if offset < 0x80 or 0x7D00 <= offset:
        return 2
    elif 0x500 <= offset:
        return 1
    return 0


# ----------------------------
# Máquina de bits para compressão
# ----------------------------

cdef class BitsCompress:
    """Escreve bits com tags de tamanho variável usando um bytearray para saída."""
    cdef public bytearray out
    cdef int __tagsize
    cdef unsigned long long __tag
    cdef Py_ssize_t __tagoffset
    cdef int __maxbit
    cdef int __curbit
    cdef bint __isfirsttag

    def __cinit__(self):
        pass

    def __init__(self, int tagsize):
        self.out = bytearray()
        self.__tagsize = tagsize
        self.__tag = 0
        self.__tagoffset = -1
        self.__maxbit = (self.__tagsize * 8) - 1
        self.__curbit = 0
        self.__isfirsttag = True

    cpdef bytes getdata(self):
        # patcha o tag reservado no buffer antes de devolver
        if self.__tagoffset >= 0:
            tag_bytes = int2lebin(self.__tag, self.__tagsize)
            modifybuffer(self.out, tag_bytes, self.__tagoffset)
        return bytes(self.out)

    cpdef void write_bit(self, int value):
        if self.__curbit != 0:
            self.__curbit -= 1
        else:
            # Se não é o primeiro tag, já insere os bits escritos
            if not self.__isfirsttag:
                # preserva o tag atual no buffer
                self.getdata()
            else:
                self.__isfirsttag = False
            self.__tagoffset = len(self.out)
            # reserva espaço para o tag
            self.out += b"\x00" * self.__tagsize
            self.__curbit = self.__maxbit
            self.__tag = 0
        if value:
            self.__tag |= (1 << self.__curbit)
        return

    cpdef void write_bitstring(self, s):
        # s é uma string contendo '0' e '1'
        for c in s:
            self.write_bit(1 if c == '1' else 0)
        return

    cpdef void write_byte(self, b):
        if isinstance(b, int):
            self.out.append(b)
        else:
            # assume-se bytes-like
            self.out += b[:1]
        return

    cpdef void write_fixednumber(self, unsigned long long value, int nbbit):
        cdef int i
        for i in range(nbbit - 1, -1, -1):
            self.write_bit((value >> i) & 1)
        return

    cpdef void write_variablenumber(self, unsigned long long value):
        """Codifica um número variável (valor >=2) conforme a lógica do Kabopan."""
        assert value >= 2
        cdef int length = getbinlen(value) - 2
        # Escreve o bit mais significativo (pode ser 0 ou 1)
        self.write_bit(1 if (value & (1 << length)) else 0)
        cdef int i
        for i in range(length - 1, -1, -1):
            self.write_bit(1)
            self.write_bit(1 if (value & (1 << i)) else 0)
        self.write_bit(0)
        return


# ----------------------------
# Máquina de bits para descompressão
# ----------------------------

cdef class BitsDecompress:
    """Lê bits de um buffer de dados (bytes ou bytearray) com tags de tamanho variável."""
    cdef int __curbit
    cdef Py_ssize_t __offset
    cdef unsigned long long __tag
    cdef int __tagsize
    cdef object _in
    cdef public bytearray out

    def __cinit__(self):
        pass

    def __init__(self, data, int tagsize):
        self.__curbit = 0
        self.__offset = 0
        self.__tag = 0
        self.__tagsize = tagsize
        self._in = data
        self.out = bytearray()

    cpdef Py_ssize_t getoffset(self):
        return self.__offset

    cpdef int read_bit(self):
        if self.__curbit != 0:
            self.__curbit -= 1
        else:
            self.__curbit = (self.__tagsize * 8) - 1
            # lê tag little-endian
            self.__tag = int.from_bytes(self._in[self.__offset:self.__offset + self.__tagsize], 'little')
            self.__offset += self.__tagsize
        # obtém o bit mais significativo do tag corrente
        cdef unsigned long long tagmask = (self.__tagsize * 8) - 1
        # desloca e pega o bit mais à esquerda
        bit = (self.__tag >> ((self.__tagsize * 8) - 1)) & 0x01
        # rotaciona o tag para a esquerda (efetivamente)
        self.__tag = (self.__tag << 1) & ((1 << (self.__tagsize * 8)) - 1)
        return <int>bit

    cpdef bint is_end(self):
        return self.__offset == len(self._in) and self.__curbit == 1

    cpdef bytes read_byte(self):
        result = self._in[self.__offset:self.__offset + 1]
        self.__offset += 1
        return result

    cpdef unsigned long long read_fixednumber(self, int nbbit, unsigned long long init=0):
        cdef unsigned long long result = init
        cdef int i
        for i in range(nbbit):
            result = (result << 1) | self.read_bit()
        return result

    cpdef unsigned long long read_variablenumber(self):
        cdef unsigned long long result = 1
        result = (result << 1) | self.read_bit()
        while self.read_bit():
            result = (result << 1) | self.read_bit()
        return result

    cpdef unsigned long long read_setbits(self, unsigned long long max_, int set_=1):
        cdef unsigned long long result = 0
        while result < max_ and self.read_bit() == set_:
            result += 1
        return result

    cpdef void back_copy(self, Py_ssize_t offset, Py_ssize_t length=1):
        cdef Py_ssize_t i
        for i in range(length):
            # Copia o byte anterior relativo ao offset
            self.out.append(self.out[-offset])
        return

    cpdef void read_literal(self, value=None):
        if value is None:
            self.out += self.read_byte()
        else:
            self.out += value
        return


# ----------------------------
# Busca de correspondência (LZ77)
# ----------------------------

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef tuple find_longest_match(bytes s, bytes sub):
    """
    Procura a maior sequência em 's' (dicionário) que casa com o início de 'sub'.
    Retorna (offset, tamanho_da_correspondência).
    """
    if not sub:
        return 0, 0
    cdef Py_ssize_t limit = len(s)
    cdef bytes dic = s[:]  # cópia do dicionário
    cdef Py_ssize_t l = 0
    cdef Py_ssize_t offset = 0
    cdef Py_ssize_t length = 0
    cdef bytes word = b""
    word += sub[l:l + 1]
    cdef Py_ssize_t pos = dic.rfind(word, 0, limit + 1)
    if pos == -1:
        return offset, length
    offset = limit - pos
    length = len(word)
    dic += sub[l:l + 1]
    while l < len(sub) - 1:
        l += 1
        word += sub[l:l + 1]
        pos = dic.rfind(word, 0, limit + 1)
        if pos == -1:
            return offset, length
        offset = limit - pos
        length = len(word)
        dic += sub[l:l + 1]
    return offset, length


# ----------------------------
# Compressor aPLib
# ----------------------------

cdef class AplibCompressor(BitsCompress):
    """Implementa a compressão aPLib (baseada em LZ77)."""
    cdef bytes __in
    cdef Py_ssize_t __length
    cdef Py_ssize_t __offset
    cdef Py_ssize_t __lastoffset
    cdef bint __pair

    def __cinit__(self):
        pass

    def __init__(self, data, length=None):
        super().__init__(1)
        self.__in = data
        self.__length = length if length is not None else len(data)
        self.__offset = 0
        self.__lastoffset = 0
        self.__pair = True

    cdef void __literal(self, bint marker=True):
        if marker:
            self.write_bit(0)
        self.write_byte(self.__in[self.__offset:self.__offset + 1])
        self.__offset += 1
        self.__pair = True

    cdef void __block(self, Py_ssize_t offset, Py_ssize_t match_len):
        cdef unsigned long long high
        cdef int low
        assert offset >= 2
        self.write_bitstring("10")
        if self.__pair and self.__lastoffset == offset:
            self.write_variablenumber(2)
            self.write_variablenumber(match_len)
        else:
            high = (offset >> 8) + 2
            if self.__pair:
                high += 1
            self.write_variablenumber(high)
            low = offset & 0xFF
            self.write_byte(low)
            self.write_variablenumber(match_len - lengthdelta(offset))
        self.__offset += match_len
        self.__lastoffset = offset
        self.__pair = False

    cdef void __shortblock(self, Py_ssize_t offset, Py_ssize_t match_len):
        assert 2 <= match_len <= 3
        assert 0 < offset <= 127
        self.write_bitstring("110")
        cdef int b_val = (offset << 1) + (match_len - 2)
        self.write_byte(b_val)
        self.__offset += match_len
        self.__lastoffset = offset
        self.__pair = False

    cdef void __singlebyte(self, Py_ssize_t offset):
        assert 0 <= offset < 16
        self.write_bitstring("111")
        self.write_fixednumber(offset, 4)
        self.__offset += 1
        self.__pair = True

    cdef void __end(self):
        self.write_bitstring("110")
        self.write_byte(0)

    cpdef bytes do(self):
        # Inicia com um literal sem marcador
        self.__literal(False)
        while self.__offset < self.__length:
            offset, match_len = find_longest_match(self.__in[:self.__offset],
                                                    self.__in[self.__offset:])
            if match_len == 0:
                c = self.__in[self.__offset:self.__offset + 1]
                if c == b"\x00":
                    self.__singlebyte(0)
                else:
                    self.__literal()
            elif match_len == 1 and 0 <= offset < 16:
                self.__singlebyte(offset)
            elif 2 <= match_len <= 3 and 0 < offset <= 127:
                self.__shortblock(offset, match_len)
            elif match_len >= 3 and offset >= 2:
                self.__block(offset, match_len)
            else:
                self.__literal()
        self.__end()
        return self.getdata()


# ----------------------------
# Descompressor aPLib
# ----------------------------

cdef class AplibDecompressor(BitsDecompress):
    """Implementa a descompressão aPLib."""
    cdef bint __pair
    cdef Py_ssize_t __lastoffset

    def __cinit__(self):
        pass

    def __init__(self, data):
        super().__init__(data, 1)
        self.__pair = True
        self.__lastoffset = 0

    cdef bint __literal(self):
        self.read_literal()
        self.__pair = True
        return False

    cdef bint __block(self):
        cdef unsigned long long b_val
        cdef unsigned long long offset
        cdef unsigned long long match_len
        cdef unsigned long long high

        b_val = self.read_variablenumber()
        if b_val == 2 and self.__pair:
            offset = self.__lastoffset
            match_len = self.read_variablenumber()
        else:
            high = b_val - 2
            if self.__pair:
                high -= 1
            offset = (high << 8) + int.from_bytes(self.read_byte(), 'little')
            match_len = self.read_variablenumber()
            match_len += lengthdelta(offset)
        self.__lastoffset = <Py_ssize_t>offset
        self.back_copy(<Py_ssize_t>offset, <Py_ssize_t>match_len)
        self.__pair = False
        return False

    cdef bint __shortblock(self):
        cdef int b_val = int.from_bytes(self.read_byte(), 'little')
        if b_val <= 1:
            return True
        cdef Py_ssize_t match_len = 2 + (b_val & 0x01)
        cdef Py_ssize_t offset = b_val >> 1
        self.back_copy(offset, match_len)
        self.__lastoffset = offset
        self.__pair = False
        return False

    cdef bint __singlebyte(self):
        cdef unsigned long long offset = self.read_fixednumber(4)
        if offset:
            self.back_copy(<Py_ssize_t>offset)
        else:
            self.read_literal(b"\x00")
        self.__pair = True
        return False

    cpdef bytes do(self):
        # lê o primeiro literal (sem marcador)
        self.read_literal()
        while True:
            idx = self.read_setbits(3)
            # idx deve ser 0..3
            if idx == 0:
                if self.__literal():
                    break
            elif idx == 1:
                if self.__block():
                    break
            elif idx == 2:
                if self.__shortblock():
                    break
            else:
                if self.__singlebyte():
                    break
        return bytes(self.out)


# ----------------------------
# Wrappers públicos
# ----------------------------

cpdef bytes compress(bytes data, length=None):
    """
    Retorna os dados comprimidos (tipo bytes).
    'data' deve ser do tipo bytes.
    """
    cdef AplibCompressor c = AplibCompressor(data, length)
    return c.do()


cpdef bytes decompress(bytes data):
    """
    Retorna os dados descomprimidos (tipo bytes).
    'data' deve ser do tipo bytes.
    """
    cdef AplibDecompressor d = AplibDecompressor(data)
    return d.do()

