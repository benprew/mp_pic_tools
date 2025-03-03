The SPR file format is a palette-based image format designed to store multiple images with transparency support. Here's a detailed breakdown of the structure:

### Overall Structure
- **Multi-image Container**: The file contains multiple images, each prefixed with a size field. The end of the image list is marked by a size value of `0xFFFFFFFF`.
- **Palette-Based**: Images use an external palette where each byte in the image data represents an index into this palette.

### Image Header (16 bytes per image)
1. **Image Data Size** (4 bytes, little-endian): Total size of the image data, including the header.
2. **Width** (2 bytes, little-endian): Image width in pixels.
3. **Height** (2 bytes, little-endian): Image height in pixels.
4. **Unknown Values** (2+2 bytes): Two 2-byte fields (purpose not clear from the code).
5. **Empty Lines Above** (2 bytes): Number of fully transparent lines at the top of the image.
6. **Cutoff Offset Y** (2 bytes): Line number where transparency resumes at the bottom (relative to the top empty lines).

### Image Data
- **Vertical Transparency**: Regions above `empty_lines_above` and below `empty_lines_above + cutoff_offset_y` are entirely transparent.
- **Line Encoding** (for non-transparent regions):
  1. **Transparent Pixel Markers**: `0xFF` bytes are skipped (may indicate inter-line padding or transparent runs).
  2. **Transparent Pixels Count** (1 byte): Number of transparent pixels at the start of the line.
  3. **Data Control Byte** (1 byte `unknown3`):
     - If `unknown3` is `0xFE` or `0xFF`, read an additional byte for **data pixel count**.
     - Otherwise, `unknown3` is the data pixel count, and the line may contain embedded transparency (`0x00` values).
  4. **Data Pixels**: Indexed palette values. If embedded transparency is enabled (`line_has_transparent_pixels`), `0x00` indicates a transparent pixel.
  5. **Post-Data Transparency**: Pixels beyond `transparent_pixels_amount + number_of_pixels_in_data` are transparent.

### Key Features
- **Efficient Transparency**: Uses both vertical/horizontal regions and inline markers (`0x00`, `0xFF`) to minimize data size.
- **Variable-Length Encoding**: Lines vary in storage size based on transparency patterns, controlled by header fields and inline markers.
- **Palette Indices**: Non-transparent pixels reference colors in an external RGBA palette (alpha set to 255 unless transparent).

### Example Flow for a Line
1. Skip leading `0xFF` bytes.
2. Read `transparent_pixels_amount` (e.g., 5 → first 5 pixels are transparent).
3. Determine `number_of_pixels_in_data` from control bytes (e.g., 10 pixels).
4. Read 10 data bytes, interpreting `0x00` as transparent if enabled.
5. Remaining pixels in the line (after 5 + 10) are transparent.

### Unresolved Aspects
- **Unknown Header Fields**: Two 2-byte values in the header are read but not used.
- **Exact Role of `0xFF`**: May serve as padding or multi-byte transparent run markers (partially handled by skipping).

This format balances compact storage with flexibility for transparency, suitable for sprite sheets or animations where multiple images and transparency are common.
