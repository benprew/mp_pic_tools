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

# typedef struct { // Pic98 Header
#     char sig[4];       // [00-"H8"-00] Pic98 signature
#     uint16_t width;    // image width in pixels
#     uint16_t height;   // image height in pixels
#     pal_t pal[16];     // RGB palette for this image (4 bits per component)
#     uint8_t data[];    // block data
# } mp_pic98_t;
Pic98BlockHeader = namedtuple("Pic98BlockHeader", ["sig", "width", "height", "pal"])
# The format string needs to account for the signature (4 bytes),
# width (2 bytes), height (2 bytes), and the palette (16 * 3 bytes for RGB).
# '4s' for the signature (bytes), 'HH' for width and height (unsigned short),
# and '48s' for the palette data (48 bytes as a single bytes object).
pic98_header_format = "<4sHH48s"

Pic98PlaneBlock = namedtuple("Pic98PlaneBlock", ["length"])
# typedef struct { // Pic98 Plane Block
#     uint16_t length;   // length of lz_data for plane
#     uint8_t lz_data[]; // LZSS compressed plane data
# } mp_pic98_plane_t;
pic98_plane_block_format = "<H"

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
