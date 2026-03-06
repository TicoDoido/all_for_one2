# cython: language_level=3, boundscheck=False, wraparound=False
# ALLZ compression / decompression (Cython core) - full-fidelity encoder

from libc.stdint cimport uint8_t, uint32_t
cimport cython
from cpython cimport bool
from cpython.dict cimport PyDict_New

# ----------------------------
# Decoder (unchanged / faithful)
# ----------------------------

cdef class ALLZDecoder:
    cdef bytes data
    cdef Py_ssize_t ptr
    cdef uint8_t bits
    cdef int cnt
    cdef uint8_t f1, f2, f3, f4
    cdef uint32_t size

    def __init__(self, bytes data):
        self.data = data
        self.ptr = 12
        self.bits = 0
        self.cnt = 0
        self.f1 = data[4]
        self.f2 = data[5]
        self.f3 = data[6]
        self.f4 = data[7]
        self.size = <uint32_t>(data[8] | (data[9]<<8) | (data[10]<<16) | (data[11]<<24))

    cdef inline int read_bit(self):
        if self.cnt == 0:
            if self.ptr >= len(self.data):
                return 0
            self.bits = self.data[self.ptr]
            self.ptr += 1
            self.cnt = 8
        cdef int bit = self.bits & 1
        self.bits >>= 1
        self.cnt -= 1
        return bit

    cdef inline uint32_t read_int(self, int n):
        cdef uint32_t res = 0
        cdef int i
        for i in range(n):
            res |= (self.read_bit() << i)
        return res

    cdef uint32_t read_al_flag(self, int start_bits):
        cdef int bits = start_bits
        while self.read_bit():
            bits += 1
        cdef uint32_t result = self.read_int(bits)
        result += ((1 << (bits - start_bits)) - 1) << start_bits
        return result

    cpdef bytes decode(self):
        cdef bytearray dst = bytearray(self.size)
        cdef Py_ssize_t d_ptr = 0
        cdef uint32_t dist, length
        while d_ptr < self.size:
            if not self.read_bit():
                length = self.read_al_flag(self.f4) + 1
                while length and d_ptr < self.size:
                    dst[d_ptr] = self.data[self.ptr]
                    d_ptr += 1
                    self.ptr += 1
                    length -= 1
            if d_ptr < self.size:
                dist = self.read_al_flag(self.f3) + 1
                length = self.read_al_flag(self.f2) + 3
                while length and d_ptr < self.size:
                    dst[d_ptr] = dst[d_ptr - dist]
                    d_ptr += 1
                    length -= 1
        return bytes(dst)


# ----------------------------
# Encoder (FULL-FIDELITY port of the Python algorithm)
# ----------------------------

cdef class ALLZEncoder:
    cdef bytes data
    cdef const unsigned char[:] data_mv
    cdef Py_ssize_t size
    cdef uint8_t f1, f2, f3, f4
    cdef bytearray out
    cdef int bit_cnt
    cdef Py_ssize_t bit_ptr
    cdef Py_ssize_t window_size
    cdef dict hash_chain  # mapping tuple(key) -> list of positions

    def __init__(self, bytes data, uint8_t f1=0, uint8_t f2=0, uint8_t f3=10, uint8_t f4=1):
        self.data = data
        self.data_mv = data  # memoryview for fast access
        self.size = len(data)
        self.f1, self.f2, self.f3, self.f4 = f1, f2, f3, f4
        self.out = bytearray(b'ALLZ')
        self.out.extend([f1, f2, f3, f4])
        self.out.extend(self.size.to_bytes(4, 'little'))
        self.bit_cnt = 0
        self.bit_ptr = -1
        self.window_size = 1048576
        self.hash_chain = {}

    cdef inline void write_bit(self, int bit):
        if self.bit_cnt == 0:
            self.bit_ptr = len(self.out)
            self.out.append(0)
        if bit:
            self.out[self.bit_ptr] |= (1 << self.bit_cnt)
        self.bit_cnt = (self.bit_cnt + 1) & 7

    cdef inline void write_int(self, uint32_t val, int n):
        cdef int i
        for i in range(n):
            self.write_bit((val >> i) & 1)

    cdef void write_al_flag(self, int start_bits, uint32_t value):
        cdef uint32_t bit_mask = 0
        cdef int bits = start_bits
        while bit_mask + ((1 << bits) - 1) < value:
            bits += 1
            bit_mask = ((1 << (bits - start_bits)) - 1) << start_bits
            self.write_bit(1)
        self.write_bit(0)
        self.write_int(value - bit_mask, bits)

    cpdef tuple find_match(self, Py_ssize_t p):
        """Retorna (best_len, best_off) como no algoritmo Python."""
        cdef Py_ssize_t best_l = 0
        cdef Py_ssize_t best_o = 0
        cdef Py_ssize_t count = 0
        cdef Py_ssize_t idx
        cdef Py_ssize_t l
        if p + 3 >= self.size:
            return 0, 0
        cdef tuple key = (self.data_mv[p], self.data_mv[p+1], self.data_mv[p+2])
        cdef list candidates = self.hash_chain.get(key)
        if not candidates:
            return 0, 0
        for idx in candidates[::-1]:
            if p - idx > self.window_size or count > 1024:
                break
            l = 3
            while p + l < self.size and l < 258 and self.data_mv[idx + l] == self.data_mv[p + l]:
                l += 1
            if l > best_l:
                best_l = l
                best_o = p - idx
            if l == 258:
                break
            count += 1
        return best_l, best_o

    cpdef bytes encode(self):
        cdef Py_ssize_t s_ptr = 0
        cdef list matches = []
        cdef Py_ssize_t i
        cdef Py_ssize_t m_len
        cdef Py_ssize_t m_off
        cdef Py_ssize_t l_len
        cdef Py_ssize_t l_off

        # Build matches using same heuristic as Python
        while s_ptr < self.size:
            m_len, m_off = self.find_match(s_ptr)
            if m_len >= 3:
                l_len, l_off = self.find_match(s_ptr + 1)
                if l_len > m_len + 1:
                    m_len = 0
            if m_len >= 3:
                matches.append((s_ptr, m_off, m_len))
                for i in range(s_ptr, s_ptr + m_len):
                    if i + 3 < self.size:
                        key = (self.data_mv[i], self.data_mv[i+1], self.data_mv[i+2])
                        lst = self.hash_chain.get(key)
                        if lst is None:
                            lst = []
                            self.hash_chain[key] = lst
                        lst.append(i)
                s_ptr += m_len
            else:
                if s_ptr + 3 < self.size:
                    key = (self.data_mv[s_ptr], self.data_mv[s_ptr+1], self.data_mv[s_ptr+2])
                    lst = self.hash_chain.get(key)
                    if lst is None:
                        lst = []
                        self.hash_chain[key] = lst
                    lst.append(s_ptr)
                s_ptr += 1
        # dummy final match
        matches.append((self.size, 1, 3))

        # Emit bitstream
        s_ptr = 0
        for m_pos, m_dist, m_len in matches:
            plain = m_pos - s_ptr
            if plain > 0:
                self.write_bit(0)
                self.write_al_flag(self.f4, plain - 1)
                # append literals
                self.out.extend(self.data[s_ptr:s_ptr+plain])
                s_ptr += plain
            else:
                self.write_bit(1)
            if s_ptr < self.size:
                self.write_al_flag(self.f3, m_dist - 1)
                self.write_al_flag(self.f2, m_len - 3)
                s_ptr += m_len
        return bytes(self.out)


# ----------------------------
# API pública
# ----------------------------

cpdef bytes allz_decompress(bytes data):
    return ALLZDecoder(data).decode()

cpdef bytes allz_compress(bytes data, uint8_t f1=0, uint8_t f2=0, uint8_t f3=10, uint8_t f4=1):
    return ALLZEncoder(data, f1, f2, f3, f4).encode()

