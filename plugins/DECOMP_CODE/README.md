# DECOMP_CODE (Cython)

Os módulos `.pyx` desta pasta podem ser compilados em modo *inplace* com:

```bash
python plugins/DECOMP_CODE/build_cython.py
```

Isso compila os módulos:

- `allz.pyx`
- `aplib.pyx`
- `lzss_codec.pyx`
- `refpack_cy.pyx`

Se quiser passar flags customizadas, use diretamente:

```bash
python plugins/DECOMP_CODE/build_cython.py build_ext --inplace
```

> Requisito: `Cython` instalado no ambiente Python.
