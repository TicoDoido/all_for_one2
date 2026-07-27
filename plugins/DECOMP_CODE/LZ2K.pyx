# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
"""
Cython version of the LZ2K decompressor.

Build with a setup.py using cythonize, e.g.:

    from setuptools import setup
    from Cython.Build import cythonize
    setup(ext_modules=cythonize("LZ2K.pyx", language_level=3))

then: python setup.py build_ext --inplace
"""

from libc.stdint cimport uint32_t, uint64_t, uint8_t, uint16_t

# Constant sizes of the internal tables (kept as plain ints so they can be
# used both as fixed C-array sizes and inside range()/comparisons).
DEF CHUNK_SIZE_CONST = 0x2000      # 8192
DEF SMALL_BYTE_LEN = 20
DEF LARGE_BYTE_LEN = 510
DEF SMALL_WORD_LEN = 256
DEF LARGE_WORD_LEN = 4096
DEF PARALLEL_LEN = 1024


cdef class UnLZ2K:
    # ---- fixed size C buffers (replace the Python bytearrays/lists) ----
    cdef unsigned char _chunk_buffer[CHUNK_SIZE_CONST]
    cdef unsigned char _small_byte_buffer[SMALL_BYTE_LEN]
    cdef unsigned char _large_byte_buffer[LARGE_BYTE_LEN]
    cdef unsigned short _small_word_buffer[SMALL_WORD_LEN]
    cdef unsigned short _large_word_buffer[LARGE_WORD_LEN]
    cdef unsigned short _parallel_buffer0[PARALLEL_LEN]
    cdef unsigned short _parallel_buffer1[PARALLEL_LEN]

    # ---- source buffer (read-only view over whatever bytes-like object) ----
    cdef const unsigned char[:] _src_buffer

    # ---- scalar decoder state ----
    cdef uint32_t _bit_stream
    cdef int _previous_bit_align
    cdef unsigned int _last_byte_read
    cdef Py_ssize_t _src_offset
    cdef int _literals_to_copy
    cdef int _chunks_with_current_setup
    cdef int _read_offset

    def __cinit__(self):
        self._bit_stream = 0
        self._previous_bit_align = 0
        self._last_byte_read = 0
        self._src_offset = 0
        self._literals_to_copy = 0
        self._chunks_with_current_setup = 0
        self._read_offset = 0

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    cpdef decompress(self, const unsigned char[:] src_buffer, unsigned char[:] dst_buffer):
        cdef Py_ssize_t bytes_left, dst_offset, chunk_size, i

        if dst_buffer.shape[0] == 0:
            return

        self._src_buffer = src_buffer

        self._bit_stream = 0
        self._previous_bit_align = 0
        self._last_byte_read = 0
        self._src_offset = 0
        self._literals_to_copy = 0
        self._chunks_with_current_setup = 0
        self._read_offset = 0

        bytes_left = dst_buffer.shape[0]
        dst_offset = 0

        self._load_into_bitstream(0x20)

        while bytes_left != 0:
            chunk_size = bytes_left if bytes_left < CHUNK_SIZE_CONST else CHUNK_SIZE_CONST
            self._decode_chunk(chunk_size)
            for i in range(chunk_size):
                dst_buffer[dst_offset + i] = self._chunk_buffer[i]
            dst_offset += chunk_size
            bytes_left -= chunk_size

    # ------------------------------------------------------------------
    # Bitstream reader
    # ------------------------------------------------------------------
    cdef void _load_into_bitstream(self, int bits) noexcept:
        cdef uint64_t bs

        bs = (<uint64_t>self._bit_stream) << bits
        self._bit_stream = <uint32_t>(bs & 0xFFFFFFFFULL)

        if bits > self._previous_bit_align:
            while bits > self._previous_bit_align:
                bits -= self._previous_bit_align
                bs = (<uint64_t>self._bit_stream) | ((<uint64_t>self._last_byte_read) << bits)
                self._bit_stream = <uint32_t>(bs & 0xFFFFFFFFULL)

                if self._src_offset < self._src_buffer.shape[0]:
                    self._last_byte_read = self._src_buffer[self._src_offset]
                    self._src_offset += 1
                else:
                    self._last_byte_read = 0
                self._previous_bit_align = 8

        self._previous_bit_align -= bits
        self._bit_stream = <uint32_t>((self._bit_stream | (self._last_byte_read >> self._previous_bit_align)) & 0xFFFFFFFFU)

    # ------------------------------------------------------------------
    # Chunk decoding (LZ77-ish copy/literal loop)
    # ------------------------------------------------------------------
    cdef void _decode_chunk(self, Py_ssize_t chunk_size) except *:
        cdef Py_ssize_t dst_offset = 0
        cdef int decoded_bit_stream, literals

        self._literals_to_copy -= 1
        if self._literals_to_copy >= 0:
            while self._literals_to_copy >= 0:
                self._chunk_buffer[dst_offset] = self._chunk_buffer[self._read_offset]
                dst_offset += 1
                self._read_offset = (self._read_offset + 1) & 0x1FFF
                if dst_offset == chunk_size:
                    return
                self._literals_to_copy -= 1

        while dst_offset < chunk_size:
            decoded_bit_stream = self._decode_bit_stream()
            if decoded_bit_stream <= 255:
                self._chunk_buffer[dst_offset] = <unsigned char>decoded_bit_stream
                dst_offset += 1
                if dst_offset == chunk_size:
                    return
            else:
                literals = self._decode_bit_stream_for_literals()
                self._read_offset = (<int>(dst_offset - literals - 1)) & 0x1FFF
                self._literals_to_copy = decoded_bit_stream - 254

                while self._literals_to_copy >= 0:
                    self._chunk_buffer[dst_offset] = self._chunk_buffer[self._read_offset]
                    dst_offset += 1
                    self._read_offset = (self._read_offset + 1) & 0x1FFF
                    if dst_offset == chunk_size:
                        return
                    self._literals_to_copy -= 1

    # ------------------------------------------------------------------
    # Main symbol decoder (uses the "large" huffman-like tables)
    # ------------------------------------------------------------------
    cdef int _decode_bit_stream(self) except *:
        cdef int tmp_value
        cdef unsigned int mask

        if self._chunks_with_current_setup == 0:
            self._chunks_with_current_setup = <int>((self._bit_stream >> 16) & 0xFFFF)
            self._load_into_bitstream(16)
            self._fill_small_dicts(19, 5, 3)
            self._fill_large_dicts()
            self._fill_small_dicts(14, 4, -1)

        self._chunks_with_current_setup -= 1

        tmp_value = self._large_word_buffer[self._bit_stream >> 20]
        if tmp_value >= LARGE_BYTE_LEN:
            mask = 0x80000
            while tmp_value >= LARGE_BYTE_LEN:
                if (self._bit_stream & mask) == 0:
                    tmp_value = self._parallel_buffer0[tmp_value]
                else:
                    tmp_value = self._parallel_buffer1[tmp_value]
                mask >>= 1

        self._load_into_bitstream(self._large_byte_buffer[tmp_value])
        return tmp_value

    # ------------------------------------------------------------------
    # Literal-count decoder (uses the "small" huffman-like tables)
    # ------------------------------------------------------------------
    cdef int _decode_bit_stream_for_literals(self) noexcept:
        cdef int tmp_value
        cdef unsigned int mask
        cdef uint32_t tmp_bit_stream

        tmp_value = self._small_word_buffer[self._bit_stream >> 24]
        if tmp_value >= 14:
            mask = 0x800000
            while tmp_value >= 14:
                if (self._bit_stream & mask) == 0:
                    tmp_value = self._parallel_buffer0[tmp_value]
                else:
                    tmp_value = self._parallel_buffer1[tmp_value]
                mask >>= 1

        self._load_into_bitstream(self._small_byte_buffer[tmp_value])

        if tmp_value == 0:
            return 0
        elif tmp_value == 1:
            return 2

        tmp_value -= 1
        tmp_bit_stream = self._bit_stream >> (32 - tmp_value)
        self._load_into_bitstream(tmp_value)
        return <int>tmp_bit_stream + (1 << tmp_value)

    # ------------------------------------------------------------------
    # Small dictionary (code-length table) construction
    # ------------------------------------------------------------------
    cdef void _fill_small_dicts(self, int length, int bits, int special_ind) except *:
        cdef unsigned int tmp_value1, mask, counter
        cdef uint32_t tmp_bit_stream
        cdef int tmp_value2, bits_used, special_length, i

        tmp_value1 = (self._bit_stream >> (32 - bits)) & ((1 << bits) - 1)
        self._load_into_bitstream(bits)

        if tmp_value1 != 0:
            tmp_value2 = 0
            while tmp_value2 < <int>tmp_value1:
                tmp_bit_stream = self._bit_stream >> 29
                bits_used = 3

                if tmp_bit_stream == 7:
                    mask = 0x10000000
                    if (self._bit_stream & mask) == 0:
                        bits_used = 4
                    else:
                        counter = 0
                        while (self._bit_stream & mask) != 0:
                            mask >>= 1
                            counter += 1
                        bits_used = <int>counter + 4
                        tmp_bit_stream += counter

                self._load_into_bitstream(bits_used)
                self._small_byte_buffer[tmp_value2] = <unsigned char>tmp_bit_stream
                tmp_value2 += 1

                if tmp_value2 == special_ind:
                    special_length = <int>((self._bit_stream >> 30) & 0x3)
                    self._load_into_bitstream(2)
                    for i in range(special_length):
                        if tmp_value2 < SMALL_BYTE_LEN:
                            self._small_byte_buffer[tmp_value2] = 0
                            tmp_value2 += 1

            while tmp_value2 < length:
                self._small_byte_buffer[tmp_value2] = 0
                tmp_value2 += 1

            self._fill_words_using_bytes(length, self._small_byte_buffer, 8,
                                          self._small_word_buffer)
        else:
            tmp_value1 = (self._bit_stream >> (32 - bits)) & ((1 << bits) - 1)
            self._load_into_bitstream(bits)
            for i in range(length):
                self._small_byte_buffer[i] = 0
            for i in range(SMALL_WORD_LEN):
                self._small_word_buffer[i] = <unsigned short>tmp_value1

    # ------------------------------------------------------------------
    # Large dictionary (code-length table) construction
    # ------------------------------------------------------------------
    cdef void _fill_large_dicts(self) except *:
        cdef unsigned int tmp_value1, tmp_value2b, mask
        cdef int tmp_length, tmp_value2, i
        cdef Py_ssize_t bytes_count

        tmp_value1 = (self._bit_stream >> 23) & 0x1FF
        self._load_into_bitstream(9)

        if tmp_value1 == 0:
            tmp_value2b = (self._bit_stream >> 23) & 0x1FF
            self._load_into_bitstream(9)
            for i in range(LARGE_BYTE_LEN):
                self._large_byte_buffer[i] = 0
            for i in range(LARGE_WORD_LEN):
                self._large_word_buffer[i] = <unsigned short>tmp_value2b
            return

        bytes_count = 0
        while bytes_count < tmp_value1:
            tmp_length = <int>((self._bit_stream >> 24) & 0xFF)
            tmp_value2 = self._small_word_buffer[tmp_length]

            if tmp_value2 >= 19:
                mask = 0x800000
                while tmp_value2 >= 19:
                    if (self._bit_stream & mask) == 0:
                        tmp_value2 = self._parallel_buffer0[tmp_value2]
                    else:
                        tmp_value2 = self._parallel_buffer1[tmp_value2]
                    mask >>= 1

            self._load_into_bitstream(self._small_byte_buffer[tmp_value2])

            if tmp_value2 > 2:
                self._large_byte_buffer[bytes_count] = <unsigned char>(tmp_value2 - 2)
                bytes_count += 1
            else:
                if tmp_value2 == 0:
                    tmp_length = 1
                elif tmp_value2 == 1:
                    tmp_value2 = <int>((self._bit_stream >> 28) & 0xF)
                    self._load_into_bitstream(4)
                    tmp_length = tmp_value2 + 3
                else:
                    tmp_value2 = <int>((self._bit_stream >> 23) & 0x1FF)
                    self._load_into_bitstream(9)
                    tmp_length = tmp_value2 + 20

                for i in range(tmp_length):
                    if bytes_count < LARGE_BYTE_LEN:
                        self._large_byte_buffer[bytes_count] = 0
                        bytes_count += 1

        while bytes_count < LARGE_BYTE_LEN:
            self._large_byte_buffer[bytes_count] = 0
            bytes_count += 1

        self._fill_words_using_bytes(LARGE_BYTE_LEN, self._large_byte_buffer, 12,
                                      self._large_word_buffer)

    # ------------------------------------------------------------------
    # Canonical-huffman style table builder (shared by small/large dicts)
    # ------------------------------------------------------------------
    cdef void _fill_words_using_bytes(self, int bytes_length, unsigned char *bytes_buffer,
                                       int pivot, unsigned short *words_buffer) except *:
        cdef int src_buffer[17]
        cdef int dest_buffer[18]
        cdef int i, ind, shift, tmp_value, tmp_value_copy, low, high
        cdef int comp1, comp2, tmp_byte
        cdef Py_ssize_t tmp_offset, new_length, tmp_value2, dest_value, src_value, mask, j
        cdef unsigned short *tmp_buffer

        for i in range(17):
            src_buffer[i] = 0
        for i in range(18):
            dest_buffer[i] = 0

        for i in range(bytes_length):
            src_buffer[bytes_buffer[i]] += 1

        shift = 14
        ind = 1
        while ind <= 16:
            low = src_buffer[ind] << (shift + 1)
            high = src_buffer[ind + 1] << shift
            low += dest_buffer[ind]
            ind += 4
            high += low
            high &= 0xFFFF
            dest_buffer[ind - 3] = low
            dest_buffer[ind - 2] = high

            low = src_buffer[ind - 2] << (shift - 1)
            low += high
            high = src_buffer[ind - 1] << (shift - 2)
            high += low
            dest_buffer[ind - 1] = low
            dest_buffer[ind] = high
            shift -= 4

        if dest_buffer[17] != 0:
            raise Exception("Wrong table.")

        shift = pivot - 1
        tmp_value = 16 - pivot
        tmp_value_copy = tmp_value

        for i in range(1, pivot + 1):
            dest_buffer[i] >>= tmp_value
            src_buffer[i] = 1 << shift
            shift -= 1

        tmp_value -= 1
        for i in range(pivot + 1, 17):
            src_buffer[i] = 1 << tmp_value
            tmp_value -= 1

        comp1 = dest_buffer[pivot + 1] >> (16 - pivot)
        comp2 = 1 << pivot
        if comp1 != comp2:
            for i in range(comp1, comp2):
                words_buffer[i] = 0

        if bytes_length <= 0:
            return

        shift = 15 - pivot
        mask = 1 << shift
        tmp_value2 = bytes_length

        for i in range(bytes_length):
            tmp_byte = bytes_buffer[i]
            if tmp_byte != 0:
                dest_value = dest_buffer[tmp_byte]
                src_value = src_buffer[tmp_byte]
                src_value += dest_value

                if tmp_byte > pivot:
                    tmp_buffer = words_buffer
                    tmp_offset = dest_value >> tmp_value_copy
                    new_length = tmp_byte - pivot

                    while new_length != 0:
                        if tmp_buffer[tmp_offset] == 0:
                            self._parallel_buffer0[tmp_value2] = 0
                            self._parallel_buffer1[tmp_value2] = 0
                            tmp_buffer[tmp_offset] = <unsigned short>tmp_value2
                            tmp_value2 += 1

                        tmp_offset = tmp_buffer[tmp_offset]
                        if (dest_value & mask) == 0:
                            tmp_buffer = &self._parallel_buffer0[0]
                        else:
                            tmp_buffer = &self._parallel_buffer1[0]
                        dest_value <<= 1
                        new_length -= 1

                    tmp_buffer[tmp_offset] = <unsigned short>i
                else:
                    if dest_value < src_value:
                        for j in range(dest_value, src_value):
                            words_buffer[j] = <unsigned short>i

                dest_buffer[tmp_byte] = <int>src_value


# ----------------------------------------------------------------------
# Module-level function to keep the same call interface as the pure
# Python / C# versions:  decompress(src_buffer, dst_buffer)
# ----------------------------------------------------------------------
cpdef decompress(const unsigned char[:] src_buffer, unsigned char[:] dst_buffer):
    cdef UnLZ2K decompressor = UnLZ2K()
    decompressor.decompress(src_buffer, dst_buffer)
