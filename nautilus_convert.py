import hashlib
import os
import re
import shutil
import subprocess
import threading
from typing import Dict, List, Set, Tuple

from gi.repository import Gio, GLib, GObject, Nautilus

_has_magick = True
_has_ffmpeg = True

def _check_deps() -> None:
    global _has_magick, _has_ffmpeg
    if not shutil.which("magick"):
        _has_magick = False
    if not shutil.which("ffmpeg"):
        _has_ffmpeg = False

IMAGE_FORMATS: Dict[str, List[str]] = {
    "image/jpeg": ["jpg", "png", "webp", "gif", "tiff", "bmp", "avif", "ico"],
    "image/png": ["jpg", "webp", "gif", "tiff", "bmp", "avif", "ico"],
    "image/webp": ["jpg", "png", "gif", "tiff", "bmp"],
    "image/gif": ["jpg", "png", "webp", "tiff", "bmp"],
    "image/tiff": ["jpg", "png", "webp", "gif", "bmp", "pdf"],
    "image/bmp": ["jpg", "png", "webp", "gif", "tiff"],
    "image/avif": ["jpg", "png", "webp", "tiff"],
    "image/heic": ["jpg", "png", "webp", "tiff"],
    "image/heif": ["jpg", "png", "webp", "tiff"],
    "image/x-tga": ["jpg", "png", "webp", "tiff", "bmp"],
    "image/x-portable-pixmap": ["jpg", "png", "tiff", "bmp"],
    "image/svg+xml": ["jpg", "png", "webp", "tiff", "bmp"],
}

VIDEO_FORMATS: Dict[str, List[str]] = {
    "video/mp4": ["gif", "webm", "mkv", "avi", "mov"],
    "video/x-matroska": ["mp4", "webm", "avi", "gif", "mov"],
    "video/x-msvideo": ["mp4", "webm", "mkv", "gif"],
    "video/webm": ["mp4", "mkv", "gif", "avi"],
    "video/quicktime": ["mp4", "webm", "mkv", "gif"],
    "video/x-flv": ["mp4", "webm", "mkv"],
    "video/3gpp": ["mp4", "webm"],
}

def _get_output_path(src_path: str, target_ext: str) -> str:
    directory = os.path.dirname(src_path)
    basename = os.path.basename(src_path)
    name_match = re.match(r"^(.+)\.[^.]+$", basename)
    name = name_match.group(1) if name_match else basename
    output_path = os.path.join(directory, f"{name}_converted.{target_ext}")
    counter = 1
    while os.path.exists(output_path):
        output_path = os.path.join(directory, f"{name}_converted_{counter}.{target_ext}")
        counter += 1
    return output_path

def _do_image_convert(src_path: str, target_ext: str, output_path: str) -> Tuple[int, str]:
    cmd = ["magick", src_path]
    if target_ext == "jpg":
        cmd.extend(["-quality", "100", "-sampling-factor", "4:4:4"])
    elif target_ext == "webp":
        cmd.extend(["-quality", "100", "-define", "webp:lossless=false"])
    elif target_ext == "gif":
        cmd.extend(["-layers", "optimize"])
    elif target_ext == "avif":
        cmd.extend(["-quality", "100"])
    elif target_ext == "tiff":
        cmd.extend(["-compress", "lzw"])
    elif target_ext == "ico":
        cmd.extend(["-define", "icon:auto-resize=256,128,64,48,32,16"])
    elif target_ext == "pdf":
        cmd.extend(["-compress", "lzw", "-density", "300"])
    cmd.append(output_path)
    result = subprocess.run(cmd, capture_output=True, check=False)
    return result.returncode, result.stderr.decode() if result.stderr else ""

def _do_video_to_gif(src_path: str, output_path: str) -> Tuple[int, str]:
    palette_hash = hashlib.md5(src_path.encode()).hexdigest()
    palette_path = f"/tmp/{palette_hash}_palette.png"
    cmd1 = ["ffmpeg", "-y", "-i", src_path, "-threads", "4", "-vf", "fps=15,scale=-1:480:flags=lanczos,palettegen", palette_path]
    result1 = subprocess.run(cmd1, capture_output=True, check=False)
    if result1.returncode != 0:
        return result1.returncode, result1.stderr.decode() if result1.stderr else ""
    cmd2 = ["ffmpeg", "-y", "-i", src_path, "-i", palette_path, "-threads", "4", "-lavfi", "fps=15,scale=-1:480:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5", output_path]
    result2 = subprocess.run(cmd2, capture_output=True, check=False)
    try:
        os.remove(palette_path)
    except OSError:
        pass
    return result2.returncode, result2.stderr.decode() if result2.stderr else ""


def _do_video_convert(src_path: str, target_ext: str, output_path: str) -> Tuple[int, str]:
    if target_ext == "gif":
        return _do_video_to_gif(src_path, output_path)
    cmd = ["ffmpeg", "-y", "-i", src_path, "-threads", "4"]
    if target_ext == "webm":
        cmd.extend(["-c:v", "libvpx-vp9", "-crf", "15", "-b:v", "0", "-c:a", "libopus", "-b:a", "128k"])
    else:
        cmd.extend(["-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac", "-b:a", "192k"])
    cmd.append(output_path)
    result = subprocess.run(cmd, capture_output=True, check=False)
    return result.returncode, result.stderr.decode() if result.stderr else ""


def _do_convert(src_path: str, target_ext: str, media_type: str) -> None:
    if src_path.lower().endswith(f".{target_ext.lower()}"):
        return
    output_path = _get_output_path(src_path, target_ext)
    if media_type == "image":
        returncode = _do_image_convert(src_path, target_ext, output_path)
    else:
        returncode = _do_video_convert(src_path, target_ext, output_path)
    if returncode == 0:
        uri = Gio.File.new_for_path(output_path).get_uri()
        try:
            connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            connection.call("org.freedesktop.FileManager1", "/org/freedesktop/FileManager1", "org.freedesktop.FileManager1", "ShowItems", GLib.Variant("(ass)", ([uri], "")), None, Gio.DBusCallFlags.NONE, -1, None, None)
        except Exception:
            pass


class NautilusConvert(GObject.GObject, Nautilus.MenuProvider):
    def get_file_items(self, files: List[Nautilus.FileInfo]) -> List[Nautilus.MenuItem]:
        image_targets: Set[str] = set()
        video_targets: Set[str] = set()

        for file in files:
            mime = file.get_mime_type()
            if _has_magick and mime in IMAGE_FORMATS:
                image_targets.update(IMAGE_FORMATS[mime])
            elif _has_ffmpeg and mime in VIDEO_FORMATS:
                video_targets.update(VIDEO_FORMATS[mime])

        if not image_targets and not video_targets:
            return []

        submenu = Nautilus.Menu()
        all_targets: Dict[str, str] = {}
        for tgt in sorted(image_targets):
            all_targets[tgt] = "image"
        for tgt in sorted(video_targets):
            all_targets[tgt] = "video"

        for target_ext, media_type in all_targets.items():
            item = Nautilus.MenuItem(name=f"Convert::to_{target_ext}", label=f"→ {target_ext.upper()}")
            item.connect("activate", self._on_activate, files, target_ext, media_type)
            submenu.append_item(item)

        menu_item = Nautilus.MenuItem(name="Convert::menu", label="Convert To")
        menu_item.set_submenu(submenu)
        return [menu_item]

    def _on_activate(self, item: Nautilus.MenuItem, files: List[Nautilus.FileInfo], target_ext: str, media_type: str) -> None:
        for file in files:
            src_path = file.get_location().get_path()
            if not src_path:
                continue
            threading.Thread(target=_do_convert, args=(src_path, target_ext, media_type), daemon=True).start()

_check_deps()
