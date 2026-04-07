# nautilus-convert

Easily convert your media files directly through Nautilus.

## Supported Distros
- Ubuntu/Debian (apt) - not tested, should work
- Fedora (dnf) - not tested, should work
- Arch Linux (pacman)

## Image Formats
JPEG, PNG, WebP, GIF, TIFF, BMP, AVIF, ICO, HEIC, HEIF, TGA, PPM, SVG

## Video Formats
MP4, MKV, AVI, WebM, MOV, FLV, 3GP

## Install
```bash
curl -sSL https://raw.githubusercontent.com/dumbovita/nautilus-convert/main/install.sh | bash
```

## Manual Install
```bash
git clone https://github.com/dumbovita/nautilus-convert.git ~/.nautilus-convert
# Install dependencies (imagemagick, ffmpeg, nautilus-python)
sudo cp ~/.nautilus-convert/nautilus_convert.py /usr/share/nautilus-python/extensions/
```

## Requirements
- ImageMagick
- ffmpeg
- nautilus-python
