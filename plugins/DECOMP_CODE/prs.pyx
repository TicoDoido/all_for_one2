# cython: boundscheck=False, wraparound=False, initializedcheck=False

cimport cython
from libc.stdint cimport uint8_t

# ----------------------------
# Contexto
# ----------------------------

cdef class PRSContext:
    cdef bytes src
    cdef Py_ssize_t src_pos
    cdef bytearray dst

    cdef int control_byte
    cdef int bit_pos_dec

    cdef Py_ssize_t control_byte_idx
    cdef int bit_pos_comp
    cdef int comp_control_byte

    def __cinit__(self, bytes data):
        self.src = data
        self.src_pos = 0
        self.dst = bytearray()

        self.control_byte = 0
        self.bit_pos_dec = 8

        self.control_byte_idx = 0
        self.bit_pos_comp = 8
        self.comp_control_byte = 0


# ----------------------------
# DESCOMPRESSOR
# ----------------------------

cdef inline int read_bit(PRSContext ctx):
    if ctx.bit_pos_dec >= 8:
        if ctx.src_pos < len(ctx.src):
            ctx.control_byte = ctx.src[ctx.src_pos]
            ctx.src_pos += 1
        ctx.bit_pos_dec = 0

    cdef int result = ctx.control_byte & 1
    ctx.control_byte >>= 1
    ctx.bit_pos_dec += 1
    return result


cpdef bytes prs_decompress(bytes data):
    cdef PRSContext ctx = PRSContext(data)
    cdef int low, high, offset, count
    cdef Py_ssize_t pos

    while True:
        if read_bit(ctx) == 1:
            if ctx.src_pos < len(ctx.src):
                ctx.dst.append(ctx.src[ctx.src_pos])
                ctx.src_pos += 1
        else:
            if read_bit(ctx) == 1:
                if ctx.src_pos + 1 >= len(ctx.src):
                    break

                low = ctx.src[ctx.src_pos]
                high = ctx.src[ctx.src_pos + 1]
                ctx.src_pos += 2

                offset = (high << 8) | low
                if offset == 0:
                    break

                count = offset & 7
                offset = (offset >> 3) | -8192

                if count == 0:
                    count = ctx.src[ctx.src_pos] + 1
                    ctx.src_pos += 1
                else:
                    count += 2
            else:
                count = ((read_bit(ctx) << 1) | read_bit(ctx)) + 2
                offset = ctx.src[ctx.src_pos] | -256
                ctx.src_pos += 1

            for _ in range(count):
                pos = len(ctx.dst) + offset
                if pos >= 0:
                    ctx.dst.append(ctx.dst[pos])

    return bytes(ctx.dst)


# ----------------------------
# COMPRESSOR
# ----------------------------

cdef inline void set_bit(PRSContext ctx, int bit):
    if ctx.bit_pos_comp == 0:
        ctx.dst[ctx.control_byte_idx] = ctx.comp_control_byte
        ctx.control_byte_idx = len(ctx.dst)
        ctx.dst.append(0)
        ctx.comp_control_byte = 0
        ctx.bit_pos_comp = 8

    ctx.comp_control_byte >>= 1
    if bit != 0:
        ctx.comp_control_byte |= 128
    ctx.bit_pos_comp -= 1


cdef void write_block(PRSContext ctx, int offset, int length):
    if 2 <= length <= 5 and offset >= -256:
        set_bit(ctx, 0)
        set_bit(ctx, 0)
        set_bit(ctx, (length - 2) & 2)
        set_bit(ctx, (length - 2) & 1)
        ctx.dst.append(offset & 0xFF)

    elif length <= 9:
        set_bit(ctx, 0)
        set_bit(ctx, 1)
        ctx.dst.append(((offset << 3) & 0xF8) | ((length - 2) & 0x07))
        ctx.dst.append((offset >> 5) & 0xFF)

    else:
        set_bit(ctx, 0)
        set_bit(ctx, 1)
        ctx.dst.append((offset << 3) & 0xF8)
        ctx.dst.append((offset >> 5) & 0xFF)
        ctx.dst.append((length - 1) & 0xFF)


cpdef bytes prs_compress(bytes data):
    cdef PRSContext ctx = PRSContext(data)
    cdef Py_ssize_t src_len = len(data)
    cdef int best_off, best_len
    cdef int i, length, search_limit

    ctx.dst.append(0)

    while ctx.src_pos < src_len:
        best_off = 0
        best_len = 0

        search_limit = ctx.src_pos - 8176
        if search_limit < 0:
            search_limit = 0

        for i in range(ctx.src_pos - 1, search_limit - 1, -1):
            length = 0
            while (length < 256 and
                   ctx.src_pos + length < src_len and
                   ctx.src[i + length] == ctx.src[ctx.src_pos + length]):
                length += 1

            if (length >= 3) or (length >= 2 and i - ctx.src_pos >= -256):
                if length > best_len:
                    best_off = i - ctx.src_pos
                    best_len = length

            if best_len == 256:
                break

        if best_len == 0:
            set_bit(ctx, 1)
            ctx.dst.append(ctx.src[ctx.src_pos])
            ctx.src_pos += 1
        else:
            write_block(ctx, best_off, best_len)
            ctx.src_pos += best_len

    # EOF
    set_bit(ctx, 0)
    set_bit(ctx, 1)

    ctx.comp_control_byte >>= ctx.bit_pos_comp
    ctx.dst[ctx.control_byte_idx] = ctx.comp_control_byte
    ctx.dst.extend([0, 0])

    return bytes(ctx.dst)