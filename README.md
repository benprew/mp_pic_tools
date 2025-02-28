```
   __  _______________  ____  ___  ___  ____  ________
  /  |/  /  _/ ___/ _ \/ __ \/ _ \/ _ \/ __ \/ __/ __/
 / /|_/ // // /__/ , _/ /_/ / ___/ , _/ /_/ /\ \/ _/  
/_/  /_/___/\___/_/|_|\____/_/  /_/|_|\____/___/___/  
 ⣀⡀ ⠄ ⢀⣀    ⣰⡀ ⢀⡀ ⢀⡀ ⡇ ⢀⣀
 ⡧⠜ ⠇ ⠣⠤ ⠤⠤ ⠘⠤ ⠣⠜ ⠣⠜ ⠣ ⠭⠕

```

## PIC Tools

Tools for converting to/from Microprose files. You can convert PNG files to PIC and SPR formats, and vice versa.

## Prerequisites

- Python 3
- Pillow (Python Imaging Library fork)

You can install Pillow using pip:

```sh
pip3 install --user pillow
```

## Scripts Overview

1. **png2pic.py**: Converts PNG files to PICv3 files.
2. **pic2png.py**: Converts PIC files to PNG files.
3. **spr2png.py**: Converts SPR files to PNG files.
4. **png2spr.py**: Converts PNG files to SPR files.

### 1. Converting PNG to PICv3

**Script**: png2pic.py

**Description**: This script converts PNG files to PICv3 files.

**Usage**:

```sh
python png2pic.py <png_file> [-p <palette_file>] [-v]
```

**Arguments**:
- `<png_file>`: The PNG file you want to convert.
- `-p <palette_file>`: (Optional) The palette file to use.
- `-v`: (Optional) Enable verbose mode for more detailed output.

**Example**:

```sh
python png2pic.py image.png -p palette.pal -v
```

### 2. Converting PIC to PNG

**Script**: `pic2png.py`

**Description**: This script converts PIC files to PNG files.

**Usage**:

```sh
python pic2png.py <pic_file> [-p <palette_file>] [-v]
```

**Arguments**:
- `<pic_file>`: The PIC file you want to convert.
- `-p <palette_file>`: (Optional) The palette file to use.
- `-v`: (Optional) Enable verbose mode for more detailed output.

**Example**:

```sh
python pic2png.py image.pic -p palette.pal -v
```

### 3. Converting SPR to PNG

**Script**: `spr2png.py`

**Description**: This script converts SPR files to PNG files.

**Usage**:

```sh
python spr2png.py <spr_file> [-p <palette_file>] [-v]
```

**Arguments**:
- `<spr_file>`: The SPR file you want to convert.
- `-p <palette_file>`: (Optional) The palette file to use.
- `-v`: (Optional) Enable verbose mode for more detailed output.

**Example**:

```sh
python spr2png.py image.spr -p palette.pal -v

```

### 4. Converting PNG to SPR

**Script**: `png2spr.py`

**Description**: This script converts PNG files to SPR files.

**Usage**:

```sh
python png2spr.py <png_files> -o <output_spr_file> [-v]
```

**Arguments**:
- `<png_files>`: One or more PNG files you want to convert.
- `-o <output_spr_file>`: The name of the output SPR file.
- `-v`: (Optional) Enable verbose mode for more detailed output.

**Example**:

```sh
python png2spr.py image1.png image2.png -o output.spr -v
```

## Additional Information

- **Verbose Mode**: Use the `-v` flag to enable verbose mode, which provides more detailed output and can help with troubleshooting.
- **Palette Files**: Some conversions require a palette file. Make sure you have the appropriate palette file for your images.

## Acknowledgments

- Canadian Avenger's excellent [article on PIC file format](https://canadianavenger.io/2024/09/17/pic-as-we-know-it/#pic-aliases)
- Joel "Quadko" McIntyre's [PicFileFormat.txt](https://www.joelmcintyre.com/PicFileFormat.txt)
- Ciroth Ungol's [PicViewer Tools](https://www.slightlymagic.net/forum/viewtopic.php?f=25&t=7509)
- Celestial Amber's [SprDecoder](https://github.com/CelestialAmber/ShandalarImageToolbox/blob/master/ShandalarImageToolbox/File%20Format%20Helpers/SprDecoder.cs)

