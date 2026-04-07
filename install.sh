#!/bin/bash
set -e

if command -v apt &>/dev/null; then
    sudo apt install imagemagick ffmpeg python3-nautilus
elif command -v dnf &>/dev/null; then
    sudo dnf install imagemagick ffmpeg python3-nautilus
elif command -v pacman &>/dev/null; then
    sudo pacman -S imagemagick ffmpeg nautilus-python
else
    echo "Distro not supported"
fi

if [ -d ~/.nautilus-convert ]; then
    :
else
    git clone https://github.com/dumbovita/nautilus-convert.git ~/.nautilus-convert
fi

cp ~/.nautilus-convert/nautilus_convert.py ~/.local/share/nautilus-python/extensions/
