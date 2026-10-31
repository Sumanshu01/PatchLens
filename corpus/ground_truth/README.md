# Ground Truth: zlib 1.2.11 -> 1.2.12 (CVE-2018-25032)

Derived directly from the upstream `madler/zlib` Git repository.

## Security Fix Commit (`5c44459c3b28a9bd3283aaceab7c615f8020c531`)

> Fix a bug that can crash deflate on some input when using Z_FIXED.

This bug was reported by Danilo Ramos of Eideticom, Inc. It has
lain in wait 13 years before being found! The bug was introduced
in zlib 1.2.2.2, with the addition of the Z_FIXED option. That
option forces the use of fixed Huffman codes. For rare inputs with
a large number of distant matches, the pending buffer into which
the compressed data is written can overwrite the distance symbol
table which it overlays. That results in corrupted output due to
invalid distances, and can result in out-of-bound accesses,
crashing the application.

The fix here combines the distance buffer and literal/length
buffers into a single symbol buffer. Now three bytes of pending
buffer space are opened up for each literal or length/distance
pair consumed, instead of the previous two bytes. This assures
that the pending buffer cannot overwrite the symbol table, since
the maximum fixed code compressed length/distance is 31 bits, and
since there are four bytes of pending space for every three bytes
of symbol space.

### Functions Modified in CVE-2018-25032 Fix Commit

- **`deflate.c`**: `deflateCopy`, `deflateInit2_`, `deflatePrime`, `deflate_fast`, `deflate_huff`, `deflate_rle`, `deflate_slow`
- **`trees.c`**: `compress_block`, `init_block`

## Full Release Diff (`v1.2.11` .. `v1.2.12`)

All core library functions modified across the entire `1.2.11 -> 1.2.12` release:

- **`crc32.c`**: `braid`, `byte_swap`, `crc32`, `crc32_big`, `crc32_combine`, `crc32_combine64`, `crc32_combine_`, `crc32_combine_gen`, `crc32_combine_gen64`, `crc32_combine_op`, `crc32_little`, `crc32_z`, `crc_word`, `crc_word_big`, `get_crc_table`, `gf2_matrix_square`, `gf2_matrix_times`, `main`, `make_crc_table`, `multmodp`, `once`, `test_and_set`, `write_table`, `write_table32hi`, `write_table64`, `x2nmodp`
- **`deflate.c`**: `deflate`, `deflateCopy`, `deflateInit2_`, `deflateParams`, `deflatePrime`, `deflateResetKeep`, `deflate_fast`, `deflate_huff`, `deflate_rle`, `deflate_slow`, `deflate_stored`, `fill_window`
- **`gzlib.c`**: `gz_reset`, `gzseek64`
- **`gzread.c`**: `gz_read`, `gzgetc`, `gzread`
- **`gzwrite.c`**: `gz_comp`, `gz_write`, `gzprintf`, `gzputs`, `gzvprintf`
- **`infback.c`**: `inflateBack`
- **`inffast.c`**: `inflate_fast`
- **`inflate.c`**: `inflate`, `inflateResetKeep`, `inflateSync`, `inflateValidate`
- **`inftrees.c`**: `inflate_table`
- **`trees.c`**: `_tr_stored_block`, `compress_block`, `detect_data_type`, `init_block`
