# cython: language_level=3, boundscheck=False, wraparound=False

from libc.stdlib cimport malloc, free
cimport cython

# ==========================================================
# PARAM PARSER
# ==========================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef tuple parse_params(object parameters):
    cdef int vals[5]
    cdef int i

    for i in range(5):
        vals[i] = 0

    if parameters is None:
        return (12, 4, 2, 0, 0)

    if isinstance(parameters, bytes):
        try:
            parameters = parameters.decode()
        except Exception:
            return (12, 4, 2, 0, 0)

    parts = str(parameters).split()

    for i in range(min(5, len(parts))):
        try:
            vals[i] = int(parts[i])
        except Exception:
            vals[i] = 0

    if len(parts) >= 5:
        return (vals[0], vals[1], vals[2], vals[3], vals[4])

    return (12, 4, 2, 0, 0)

# ==========================================================
# WINDOW INIT
# ==========================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cdef void lzss_set_window_mv(unsigned char[:] window_mv, int init_chr) nogil:
    cdef Py_ssize_t n = window_mv.shape[0]
    cdef Py_ssize_t i
    cdef Py_ssize_t pos
    cdef unsigned char v

    if init_chr == -1:
        for i in range(n):
            window_mv[i] = 0
        i = 0
        while True:
            pos = (i * 8) + 6
            if pos >= n:
                break
            window_mv[pos] = i & 0xFF
            i += 1

    elif init_chr == -2:
        for i in range(n):
            window_mv[i] = i & 0xFF

    elif init_chr == -3:
        for i in range(n - 1, -1, -1):
            window_mv[i] = i & 0xFF

    else:
        v = <unsigned char>(init_chr & 0xFF)
        for i in range(n):
            window_mv[i] = v

# ==========================================================
# DECOMPRESSOR
# ==========================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef bytes unlzss(bytes src, object parameters=None):
    cdef int EI, EJ, P, rless, init_chr
    cdef Py_ssize_t N, F
    cdef bytearray slide
    cdef unsigned char[:] slide_mv
    cdef bytearray dst
    cdef Py_ssize_t r
    cdef unsigned int flags
    cdef Py_ssize_t pos, src_len
    cdef const unsigned char[:] src_mv
    cdef Py_ssize_t N_mask, F_mask
    cdef unsigned char c
    cdef int i_val, j_val
    cdef Py_ssize_t length
    cdef Py_ssize_t k

    EI, EJ, P, rless, init_chr = parse_params(parameters)

    N = 1 << EI
    F = 1 << EJ

    slide = bytearray(N)
    slide_mv = slide
    lzss_set_window_mv(slide_mv, init_chr)

    dst = bytearray()

    r = (N - F) - rless
    flags = 0
    pos = 0
    src_len = len(src)
    src_mv = src

    N_mask = N - 1
    F_mask = F - 1

    while pos < src_len:
        flags >>= 1
        if not (flags & 0x100):
            flags = (<unsigned int>src_mv[pos]) | 0xFF00
            pos += 1

        if flags & 1:
            c = src_mv[pos]
            pos += 1
            dst.append(c)
            slide_mv[r] = c
            r = (r + 1) & N_mask
        else:
            i_val = src_mv[pos]
            j_val = src_mv[pos + 1]
            pos += 2

            i_val |= ((j_val >> EJ) << 8)
            length = (j_val & F_mask) + P

            k = 0
            while k <= length:
                c = slide_mv[(i_val + k) & N_mask]
                dst.append(c)
                slide_mv[r] = c
                r = (r + 1) & N_mask
                k += 1

    return bytes(dst)

# ==========================================================
# COMPRESSOR
# ==========================================================

cdef class LZSSCompressor:
    cdef const unsigned char[:] data_mv
    cdef Py_ssize_t size
    cdef int EI, EJ, P, init_chr
    cdef Py_ssize_t N, F, THRESHOLD, NIL
    cdef unsigned char[:] text_buf
    cdef int *lson
    cdef int *rson
    cdef int *dad

    def __cinit__(self):
        self.lson = NULL
        self.rson = NULL
        self.dad = NULL

    def __dealloc__(self):
        if self.lson != NULL:
            free(self.lson)
        if self.rson != NULL:
            free(self.rson)
        if self.dad != NULL:
            free(self.dad)

    def init(self, bytes data, int EI, int EJ, int P, int init_chr):
        self.data_mv = data
        self.size = len(data)
        self.EI = EI
        self.EJ = EJ
        self.P = P
        self.init_chr = init_chr

        if EI >= 16:
            self.N = EI
        else:
            self.N = 1 << EI

        self.F = (1 << EJ) + P
        self.THRESHOLD = P
        self.NIL = self.N

        cdef bytearray tb = bytearray(self.N + self.F - 1)
        self.text_buf = tb

        self.lson = <int *> malloc((self.N + 1) * sizeof(int))
        self.dad = <int *> malloc((self.N + 1) * sizeof(int))
        self.rson = <int *> malloc((self.N + 257) * sizeof(int))

        if not self.lson or not self.dad or not self.rson:
            raise MemoryError("malloc failed")

    cdef void InitTree(self):
        cdef Py_ssize_t i
        for i in range(self.N + 1, self.N + 257):
            self.rson[i] = self.NIL
        for i in range(self.N):
            self.dad[i] = self.NIL

    cpdef bytes compress(self):
        cdef Py_ssize_t s, r, in_pos, textsize
        cdef Py_ssize_t read_len, i
        cdef int match_length = 0

        self.InitTree()
        lzss_set_window_mv(self.text_buf, self.init_chr)

        in_pos = 0
        s = 0
        r = self.N - self.F

        read_len = self.size if self.size < self.F else self.F

        for i in range(read_len):
            self.text_buf[r + i] = self.data_mv[i]

        in_pos += read_len
        textsize = read_len

        out = bytearray()

        while textsize > 0:
            out.append(self.text_buf[r])
            r = (r + 1) & (self.N - 1)
            textsize -= 1

        return bytes(out)

# ==========================================================
# PUBLIC WRAPPER
# ==========================================================

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef bytes lzss_compress(bytes data, object parameters=None):
    cdef int EI, EJ, P, rless, init_chr
    EI, EJ, P, rless, init_chr = parse_params(parameters)

    cdef LZSSCompressor comp = LZSSCompressor()
    comp.init(data, EI, EJ, P, init_chr)
    try:
        return comp.compress()
    finally:
        del comp
