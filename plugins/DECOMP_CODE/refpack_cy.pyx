# === File: refpack_cy.pyx ===
# Cython port of refpack.py (encoder + decoder) - helpers moved to module-level
# Converted for Windows (CPython extension module)
# Keep these notes in mind: compile with setup.py (see BUILD_WINDOWS.md)

from cpython.buffer cimport PyObject_GetBuffer, PyBuffer_Release, Py_buffer
cimport cython

# --- Module-level helper functions (cdef inline) ---
@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline int _hash_c(unsigned char[:] data, int offset) nogil:
    return (data[offset] * 1089 + data[offset + 1] * 33 + data[offset + 2]) & (16384 - 1)

@cython.boundscheck(False)
@cython.wraparound(False)
cdef inline int _match_len_c(unsigned char[:] data, int s, int d, int max_match):
    cdef int current = 0
    cdef int n = data.shape[0]
    while current < max_match and d + current < n and s + current < n and data[s + current] == data[d + current]:
        current += 1
    return current

# Public API functions are cpdef so they can be called from Python

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int get_big_endian_word(unsigned char[:] data, int offset):
    return (data[offset] << 8) | data[offset + 1]

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int get_big_endian_dword(unsigned char[:] data, int offset):
    return (data[offset] << 24) | (data[offset + 1] << 16) | \
           (data[offset + 2] << 8) | data[offset + 3]

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef bint is_ref(object compressed_data):
    if compressed_data is None:
        return False
    cdef unsigned char[:] buf = compressed_data
    if buf.shape[0] < 2:
        return False
    cdef int pack_type = (buf[0] << 8) | buf[1]
    return (pack_type == 0x10fb or pack_type == 0x11fb or
            pack_type == 0x90fb or pack_type == 0x91fb)

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int size(object compressed_data):
    if compressed_data is None:
        return 0
    cdef unsigned char[:] buf = compressed_data
    cdef int pack_type = (buf[0] << 8) | buf[1]
    cdef int size_size = 4 if (pack_type & 0x8000) != 0 else 3
    cdef int offset = 2 + size_size if (pack_type & 0x100) != 0 else 2
    if size_size == 4:
        return get_big_endian_dword(buf, offset)
    else:
        return (buf[offset] << 16) | (buf[offset + 1] << 8) | buf[offset + 2]

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef tuple decode(bytearray dest, object compressed_data):
    """Decode compressed_data into dest (bytearray).
    Returns (uncompressed_length, compressed_size)
    """
    if compressed_data is None:
        return 0, 0

    cdef unsigned char[:] src = compressed_data
    cdef unsigned char[:] out = dest

    # Declare all local C variables at top of function to satisfy Cython rules
    cdef int source_index
    cdef int dest_index
    cdef int uncompressed_length
    cdef int type_val
    cdef int first
    cdef int second
    cdef int third
    cdef int fourth
    cdef int local_run
    cdef int ref_index
    cdef int literal_run
    cdef int eof_run
    cdef int i
    cdef int compressed_size

    source_index = 0
    dest_index = 0
    uncompressed_length = 0

    type_val = (src[source_index] << 8) | src[source_index + 1]
    source_index += 2
    if (type_val & 0x8000) != 0:
        if (type_val & 0x100) != 0:
            source_index += 4
        uncompressed_length = get_big_endian_dword(src, source_index)
        source_index += 4
    else:
        if (type_val & 0x100) != 0:
            source_index += 3
        uncompressed_length = (src[source_index] << 16) | (src[source_index + 1] << 8) | src[source_index + 2]
        source_index += 3

    while True:
        first = src[source_index]
        # literal copy + short reference
        if (first & 0x80) == 0:
            while True:
                second = src[source_index + 1]
                source_index += 2
                local_run = first & 3
                if local_run > 0:
                    out[dest_index:dest_index+local_run] = src[source_index:source_index+local_run]
                    source_index += local_run
                    dest_index += local_run
                ref_index = dest_index - 1 - (((first & 0x60) << 3) + second)
                local_run = ((first & 0x1c) >> 2) + 3
                # copy
                for i in range(local_run):
                    out[dest_index + i] = out[ref_index + i]
                dest_index += local_run
                first = src[source_index]
                if (first & 0x80) != 0:
                    break
        # other encodings
        if (first & 0x40) == 0:
            second = src[source_index + 1]
            third = src[source_index + 2]
            source_index += 3
            local_run = second >> 6
            if local_run > 0:
                out[dest_index:dest_index+local_run] = src[source_index:source_index+local_run]
                source_index += local_run
                dest_index += local_run
            ref_index = dest_index - 1 - (((second & 0x3f) << 8) + third)
            local_run = (first & 0x3f) + 4
            for i in range(local_run):
                out[dest_index + i] = out[ref_index + i]
            dest_index += local_run
            continue
        if (first & 0x20) == 0:
            second = src[source_index + 1]
            third = src[source_index + 2]
            fourth = src[source_index + 3]
            source_index += 4
            local_run = first & 3
            if local_run > 0:
                out[dest_index:dest_index+local_run] = src[source_index:source_index+local_run]
                source_index += local_run
                dest_index += local_run
            ref_index = dest_index - 1 - ((((first & 0x10) >> 4) << 16) + (second << 8) + third)
            local_run = (((first & 0x0c) >> 2) << 8) + fourth + 5
            for i in range(local_run):
                out[dest_index + i] = out[ref_index + i]
            dest_index += local_run
            continue
        source_index += 1
        literal_run = ((first & 0x1f) << 2) + 4
        if literal_run <= 112:
            out[dest_index:dest_index+literal_run] = src[source_index:source_index+literal_run]
            dest_index += literal_run
            source_index += literal_run
            continue
        eof_run = first & 3
        if eof_run > 0:
            out[dest_index:dest_index+eof_run] = src[source_index:source_index+eof_run]
            dest_index += eof_run
            source_index += eof_run
        break

    compressed_size = source_index
    return uncompressed_length, compressed_size


cdef class RefPackEncoder:
    cdef public int HASHSIZE
    cdef public int MAXMAXBACK

    def __cinit__(self):
        self.HASHSIZE = 16384
        self.MAXMAXBACK = 131072

    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef inline int _hash(self, unsigned char[:] data, int offset):
        # kept as thin wrapper calling module-level function
        return _hash_c(data, offset)

    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef inline int _match_len(self, unsigned char[:] data, int s, int d, int max_match):
        return _match_len_c(data, s, d, max_match)

    @cython.boundscheck(False)
    @cython.wraparound(False)
    cpdef int encode(self, bytearray compressed_data_buffer, object source, int source_size, int quick=0):
        """Encode source (bytes/bytearray) into compressed_data_buffer (bytearray).
        Returns number of bytes written (int).
        """
        # Declaração de todas as variáveis (no topo da função)
        cdef unsigned char[:] src = source
        cdef unsigned char[:] dest = compressed_data_buffer
        cdef int HASHSIZE = 16384
        cdef int MAXMAXBACK = 131072
        cdef int max_back = MAXMAXBACK
        cdef int max_back_mask
        cdef object hash_table  # lista python contendo ints
        cdef object link_table  # lista python ou None
        cdef int dest_index
        cdef int current_run
        cdef int cptr
        cdef int rptr
        cdef int length
        cdef int b_offset
        cdef int b_len
        cdef int b_cost
        cdef int m_len
        cdef int hash_val
        cdef int h_offset
        cdef int min_h_offset
        cdef int tptr
        cdef int t_len
        cdef int t_offset
        cdef int t_cost
        cdef int hash_val2
        cdef int h_offset2
        cdef int hash_val_local
        cdef int h_offset_local
        cdef int i

        if quick >= 2 and max_back > 16383:
            max_back = 16383
        max_back_mask = max_back - 1

        # allocate tables (usando listas python; mantém compatibilidade)
        hash_table = [-1] * HASHSIZE
        if quick >= 2:
            link_table = None
        else:
            link_table = [-1] * MAXMAXBACK

        dest_index = 0
        # write header
        if source_size > 0xFFFFFF:
            # two-byte header for large sizes
            dest[dest_index:dest_index+2] = bytes([0x90, 0xFB])
            dest_index += 2
            # write 4 bytes big endian
            dest[dest_index:dest_index+4] = source_size.to_bytes(4, 'big')
            dest_index += 4
        else:
            dest[dest_index:dest_index+2] = bytes([0x10, 0xFB])
            dest_index += 2
            dest[dest_index:dest_index+3] = source_size.to_bytes(3, 'big')
            dest_index += 3

        current_run = 0
        cptr = 0
        rptr = 0
        length = source_size - 4

        while length >= 0:
            b_offset = 0
            b_len = 2
            b_cost = 2
            m_len = 1028 if length >= 1028 else length
            if quick >= 2 and m_len > 67:
                m_len = 67

            hash_val = _hash_c(src, cptr)
            h_offset = hash_table[hash_val]
            min_h_offset = cptr - max_back_mask
            if min_h_offset < 1:
                min_h_offset = 1

            if h_offset >= min_h_offset:
                while True:
                    tptr = h_offset
                    # safety: ensure indices in bounds
                    if cptr + b_len < source_size and tptr + b_len < source_size and src[cptr + b_len] == src[tptr + b_len]:
                        t_len = _match_len_c(src, cptr, tptr, m_len)
                        t_offset = cptr - 1 - tptr
                        if t_offset < 1024 and t_len <= 10:
                            t_cost = 2
                        elif t_offset < 16384 and t_len <= 67:
                            t_cost = 3
                        else:
                            t_cost = 4

                        if (t_len - t_cost + 4) > (b_len - b_cost + 4):
                            b_len = t_len
                            b_cost = t_cost
                            b_offset = t_offset
                            if b_len >= 1028:
                                break

                    if quick >= 2:
                        break
                    if link_table is None:
                        break
                    h_offset = link_table[h_offset & max_back_mask]
                    if h_offset < min_h_offset:
                        break

            if b_cost >= b_len or length < 4:
                h_offset = cptr
                if quick != 2 and link_table is not None:
                    link_table[h_offset & max_back_mask] = hash_table[hash_val]
                hash_table[hash_val] = h_offset
                current_run += 1
                cptr += 1
                length -= 1
            else:
                while current_run > 3:
                    t_len = current_run & ~3
                    if t_len > 112:
                        t_len = 112
                    current_run -= t_len
                    dest[dest_index] = (0xE0 + (t_len >> 2) - 1) & 0xFF
                    dest_index += 1
                    dest[dest_index:dest_index+t_len] = src[rptr:rptr+t_len]
                    rptr += t_len
                    dest_index += t_len

                # write reference according to cost
                if b_cost == 2:
                    dest[dest_index] = (((b_offset >> 8) << 5) + ((b_len - 3) << 2) + current_run) & 0xFF
                    dest_index += 1
                    dest[dest_index] = b_offset & 0xFF
                    dest_index += 1
                elif b_cost == 3:
                    dest[dest_index] = (0x80 + (b_len - 4)) & 0xFF
                    dest_index += 1
                    dest[dest_index] = ((current_run << 6) + (b_offset >> 8)) & 0xFF
                    dest_index += 1
                    dest[dest_index] = b_offset & 0xFF
                    dest_index += 1
                else:
                    dest[dest_index] = (0xC0 + ((b_offset >> 16) << 4) + (((b_len - 5) >> 8) << 2) + current_run) & 0xFF
                    dest_index += 1
                    dest[dest_index] = (b_offset >> 8) & 0xFF
                    dest_index += 1
                    dest[dest_index] = b_offset & 0xFF
                    dest_index += 1
                    dest[dest_index] = (b_len - 5) & 0xFF
                    dest_index += 1

                if current_run > 0:
                    dest[dest_index:dest_index+current_run] = src[rptr:rptr+current_run]
                    dest_index += current_run
                    current_run = 0

                if quick > 0:
                    h_offset = cptr
                    if quick >= 2:
                        hash_table[hash_val] = h_offset
                    else:
                        link_table[h_offset & max_back_mask] = hash_table[hash_val]
                        hash_table[hash_val] = h_offset
                    cptr += b_len
                else:
                    for _ in range(b_len):
                        hash_val2 = _hash_c(src, cptr)
                        h_offset2 = cptr
                        link_table[h_offset2 & max_back_mask] = hash_table[hash_val2]
                        hash_table[hash_val2] = h_offset2
                        cptr += 1

                rptr = cptr
                length -= b_len

        # finalize
        length += 4
        current_run += length

        while current_run > 3:
            t_len = current_run & ~3
            if t_len > 112:
                t_len = 112
            current_run -= t_len
            dest[dest_index] = (0xE0 + (t_len >> 2) - 1) & 0xFF
            dest_index += 1
            dest[dest_index:dest_index+t_len] = src[rptr:rptr+t_len]
            rptr += t_len
            dest_index += t_len

        dest[dest_index] = (0xFC + current_run) & 0xFF
        dest_index += 1
        if current_run > 0:
            dest[dest_index:dest_index+current_run] = src[rptr:rptr+current_run]
            dest_index += current_run

        return dest_index
