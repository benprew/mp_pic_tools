from collections import namedtuple

# typedef struct {  // PicV3 General Block Header
#     char block_id[2];  // block tag
#     uint16_t length;   // length of the block
#     uint8_t data[];    // remaining block data
# } mp_picV3_block_t;
PicV3BlockHeader = namedtuple("PicV3BlockHeader", ["block_id", "length"])

# typedef struct { // PicV3 Palette Block
#     uint8_t first;          // index of first palette entry
#     uint8_t last;           // index of last palette entry
#     pal_t palette_data[];   // last-first+1 RGB entries
# } mp_picV3_palette_t;
PicV3Palette = namedtuple("PicV3Palette", ["first", "last"])

# typedef struct { // PicV3 Image Block
#     uint16_t width;    // image width in pixels
#     uint16_t height;   // image height in pixels
#     uint8_t max_bits;  // maximum code width for LZW data
#     uint8_t lz_data[]; // RLE+LZW compressed stream
# } mp_picV3_image_t;
PicV3Image = namedtuple("PicV3Image", ["width", "height", "max_bits"])

# SPR header:
# uint32_t length
# uint16_t width
# uint16_t height
# uint16_t unknown
# uint16_t unknown2
# uint16_t num_empty_lines_above
# uint16_t transparent_start
SprHeader = namedtuple(
    "SprHeader",
    [
        "length",
        "width",
        "height",
        "unknown",
        "unknown2",
        "num_empty_lines_above",
        "transparent_start",
    ],
)
SprFormat = "<IHHHHHH"
