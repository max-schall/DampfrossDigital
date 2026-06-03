"""
MusicPlayer — phase-aware background music controller (pygame backend).

Scans dampfross/music/ at startup. Each subfolder maps to a game phase:
  Mainmenu/  → "menu"   (played when music_menu pref is on)
  Buildphase/ → "build"  (played during build phase)
  Racephase/  → "race"   (played during operate/race phase)
  <anything>/ → lowercased folder name

Multiple tracks per folder are shuffled and looped. The same phase playing
already is never restarted mid-track.

Uses pygame.mixer.music so audio follows PipeWire device routing (including
Bluetooth headphones) rather than being pinned to the ALSA node at
startup like Qt's FFmpeg multimedia backend.
"""
from __future__ import annotations
import random
from pathlib import Path

import pygame

from PyQt6.QtCore import QObject, QTimer

_MUSIC_DIR = Path(__file__).parent.parent / "music"

_FOLDER_MAP: dict[str, str] = {
    "mainmenu":     "menu",
    "menu":         "menu",
    "buildphase":   "build",
    "build":        "build",
    "racephase":    "race",
    "race":         "race",
    "results":      "results",
    "resultscreen": "results",
}

_VOLUMES = {0: 0.35, 1: 0.65, 2: 1.0}


def _scan() -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {}
    if not _MUSIC_DIR.is_dir():
        return out
    for folder in sorted(_MUSIC_DIR.iterdir()):
        if not folder.is_dir():
            continue
        phase = _FOLDER_MAP.get(folder.name.lower(), folder.name.lower())
        tracks = sorted(
            f for f in folder.iterdir()
            if f.suffix.lower() in (".mp3", ".ogg", ".wav", ".flac", ".m4a")
        )
        if tracks:
            out.setdefault(phase, []).extend(tracks)
    return out


def _ensure_mixer() -> None:
    if not pygame.mixer.get_init():
        pygame.mixer.pre_init(44100, -16, 2, 2048)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)


class MusicPlayer(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        _ensure_mixer()
        self._tracks = _scan()
        self._current_phase: str | None = None
        self._queue: list[Path] = []
        self._playing = False

        self._enabled      = False
        self._menu_enabled = False
        self._volume_idx   = 0
        self._apply_volume()

        # Poll for track-end since pygame doesn't emit Qt signals
        self._poll = QTimer(self)
        self._poll.timeout.connect(self._check_ended)
        self._poll.start(400)

    # ── public ──────────────────────────────────────────────────────── #

    def apply_prefs(self, prefs: dict) -> None:
        self._enabled      = bool(prefs.get("music_enabled", False))
        self._menu_enabled = bool(prefs.get("music_menu",    False))
        new_vol = int(prefs.get("music_volume", 0))
        vol_changed = (new_vol != self._volume_idx)
        self._volume_idx = new_vol
        if vol_changed:
            self._apply_volume()
        if self._current_phase is not None:
            self._evaluate(self._current_phase, force_restart=False)

    def play_phase(self, phase: str | None) -> None:
        if phase == self._current_phase:
            if not self._playing:
                self._evaluate(phase, force_restart=True)
            return
        self._current_phase = phase
        self._evaluate(phase, force_restart=True)

    def stop(self) -> None:
        self._current_phase = None
        self._hard_stop()

    # ── internal ────────────────────────────────────────────────────── #

    def _evaluate(self, phase: str | None, *, force_restart: bool) -> None:
        if phase is None:
            self._hard_stop()
            return

        should_play = (
            (phase == "menu" and self._menu_enabled)
            or (phase != "menu" and self._enabled)
        )
        tracks = self._tracks.get(phase, [])

        if not should_play or not tracks:
            self._hard_stop()
            return

        if not force_restart and self._playing:
            return

        self._queue = list(tracks)
        random.shuffle(self._queue)
        self._play_next()

    def _play_next(self) -> None:
        if not self._queue:
            phase = self._current_phase
            tracks = self._tracks.get(phase, []) if phase else []
            if not tracks:
                return
            self._queue = list(tracks)
            random.shuffle(self._queue)
        track = self._queue.pop(0)
        try:
            pygame.mixer.music.load(str(track))
            self._apply_volume()
            pygame.mixer.music.play()
            self._playing = True
        except Exception:
            self._playing = False

    def _hard_stop(self) -> None:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self._queue = []
        self._playing = False

    def _apply_volume(self) -> None:
        try:
            pygame.mixer.music.set_volume(_VOLUMES.get(self._volume_idx, 0.35))
        except Exception:
            pass

    def _check_ended(self) -> None:
        if self._playing and not pygame.mixer.music.get_busy():
            self._playing = False
            if self._current_phase is not None:
                self._play_next()
