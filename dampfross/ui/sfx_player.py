"""
SfxPlayer — one-shot sound-effect dispatcher (pygame backend).

Scans dampfross/sfx/ at startup. Files are grouped by their stem prefix
(trailing digits stripped), so diceroll1.wav/diceroll2.wav/diceroll4.mp3
all land in the "diceroll" group and one is chosen at random each time.

Uses pygame.mixer so audio follows PipeWire device routing (including
Bluetooth headphones) rather than being pinned to the ALSA node at
startup like Qt's FFmpeg multimedia backend.

Usage:
    sfx = SfxPlayer(parent)
    sfx.apply_prefs(prefs_dict)   # call once at startup and on pref change
    sfx.play("diceroll")          # picks a random file from the group
"""
from __future__ import annotations
import random
from pathlib import Path

import pygame

from PyQt6.QtCore import QObject

_SFX_DIR = Path(__file__).parent.parent / "sfx"
_EXTS = {".wav", ".mp3", ".ogg", ".flac"}


def _scan(sfx_dir: Path) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = {}
    if not sfx_dir.is_dir():
        return result
    for f in sorted(sfx_dir.iterdir()):
        if f.suffix.lower() not in _EXTS:
            continue
        key = f.stem.rstrip("0123456789").lower()
        result.setdefault(key, []).append(f)
    return result


def _ensure_mixer() -> None:
    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)


class SfxPlayer(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._files = _scan(_SFX_DIR)
        self._enabled = True
        self._sounds: dict[Path, pygame.mixer.Sound] = {}
        _ensure_mixer()

    def apply_prefs(self, prefs: dict) -> None:
        self._enabled = bool(prefs.get("sfx_enabled", True))

    def play(self, name: str) -> None:
        if not self._enabled:
            return
        files = self._files.get(name.lower(), [])
        if not files:
            return
        path = random.choice(files)
        sound = self._sounds.get(path)
        if sound is None:
            try:
                sound = pygame.mixer.Sound(str(path))
                sound.set_volume(0.8)
                self._sounds[path] = sound
            except Exception:
                return
        sound.play()
