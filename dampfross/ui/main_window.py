import math
from pathlib import Path


def _maps_dir() -> Path:
    """'maps/' folder next to the project root, or home as fallback."""
    d = Path(__file__).parent.parent.parent / "maps"
    return d if d.is_dir() else Path.home()

from PyQt6.QtCore import QThread, QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.grid_builder import build_grid, _compute_mountainous, recompute_cells, _CITY_NUMBERS
from ..core.region_fetcher import RegionFetcher
from ..core.world_data import fetch_rivers_ne
from ..game import rules as game_rules
from ..game.state import GameState, PlayerState
from ..game.ai.bot_player import (
    AIPlayer,
    RollBuild, SetBuildStart, PlaceEdge, BuyFerry, EndTurn, DeclareEndBuild,
    RollStart, RollDest, JoinJourney, SelectRoute, CooperateWith,
    Advance, NextJourney, ProposeAlliance, RespondAlliance,
)
from ..game.ai.profile import AIProfile
from .dialogs import CityEditDialog, LoadRegionDialog, ProgressDialog
from .game_panel import GamePanel
from .design_tokens import (
    S_PAPER, S_SURFACE, S_SURFACE_2, S_SUNK,
    S_INK, S_INK_1, S_INK_2, S_INK_3, S_INK_4,
    S_RULE, S_RULE_SOFT,
    S_TERRAIN_MOUNTAIN, S_TERRAIN_WATER, S_RIVER,
    S_SUCCESS, S_WARN, S_DANGER, S_INFO,
)
from .hex_map_widget import HexMapWidget
from .main_menu import MainMenuWidget
from .map_view_screen import MapViewScreen
from .race_screen import RaceScreen
from .scoreboard_screen import ScoreboardScreen
from .results_screen import ResultsScreen
from .settings_screen import SettingsScreen, get_prefs as _settings_get_prefs
from .music_player import MusicPlayer
from .sfx_player import SfxPlayer
from .game_setup_screen import GameSetupScreen
from .lobby_screen import LobbyScreen
from .components import TurnToastWidget
from .score_overlay import ScoreOverlay

def _make_ai_profile(difficulty: int) -> "AIProfile":
    """Return an AIProfile tuned to difficulty 0=easy, 1=normal, 2=hard."""
    if difficulty == 0:
        return AIProfile(
            city_connection_w=6.0,
            fee_penalty_w=1.0,
            hop_w=0.2,
            participate_ev_threshold=2.0,
            build_lookahead_w=0.0,
        )
    if difficulty == 2:
        return AIProfile(
            city_connection_w=18.0,
            fee_penalty_w=3.0,
            hop_w=0.6,
            participate_ev_threshold=-1.0,
            contention_urgency_w=2.0,
            build_lookahead_w=0.8,
        )
    return AIProfile()  # normal = defaults


_PAGE_MENU       = 0
_PAGE_MAP        = 1
_PAGE_MAP_VIEW   = 2
_PAGE_RACE       = 3
_PAGE_SCOREBOARD = 4
_PAGE_RESULTS    = 5
_PAGE_SETTINGS   = 6
_PAGE_GAME_SETUP = 7
_PAGE_LOBBY      = 8

_TOOLBAR_STYLE = (
    f"background-color: {S_SURFACE}; border-bottom: 1px solid {S_RULE};"
)
_TOOL_BTN = f"""
QPushButton {{
    background: {S_SURFACE}; color: {S_INK_1};
    border: 1px solid {S_RULE}; border-radius: 4px;
    padding: 4px 14px; font-size: 12px;
}}
QPushButton:hover   {{ background: {S_SUNK}; color: {S_INK}; }}
QPushButton:pressed {{ background: {S_RULE}; }}
QPushButton:checked {{ background: {S_SUNK}; border-color: {S_INK_3}; color: {S_INK}; }}
"""
_LBL_STYLE = f"color: {S_INK_2}; font-size: 12px; background: transparent;"


class _RiverWorker(QThread):
    """Fetches and traces rivers after the map is already visible."""
    status   = pyqtSignal(str)
    finished = pyqtSignal(list)   # list[tuple[str, np.ndarray]]

    def __init__(self, grid):
        super().__init__()
        self._grid = grid

    def run(self) -> None:
        import numpy as np
        from pyproj import Transformer

        grid = self._grid
        try:
            lat_min, lon_min, lat_max, lon_max = grid.bbox_wgs84
            self.status.emit("Flüsse laden…")
            rivers = fetch_rivers_ne(lat_min, lon_min, lat_max, lon_max)
            if not rivers:
                self.status.emit("Keine Flüsse gefunden.")
                self.finished.emit([])
                return

            self.status.emit(f"{len(rivers)} Flüsse verfolgen…")
            fwd = Transformer.from_crs("EPSG:4326", grid.laea_proj, always_xy=True)
            # Each sub-segment (NaN-separated piece) must be at least 15 km.
            # Checking total path length would let short stubs ride along with
            # a long main channel and render as nubs.
            min_unit_len = 15_000.0 / grid.hex_size_m
            nan_row = np.full((1, 2), float("nan"), dtype=np.float32)
            segs_list = []
            for _name, coords in rivers:  # _name: str, coords: list[(lon,lat)]
                lons = [p[0] for p in coords]
                lats = [p[1] for p in coords]
                xs, ys = fwd.transform(lons, lats)
                segs = grid.trace_river(
                    list(zip(xs, ys)), grid.hex_size_m, grid.x_origin, grid.y_origin
                )
                if len(segs) == 0:
                    continue
                # Split on NaN, filter each sub-segment individually
                good_subs = []
                sub_start = 0
                for idx in range(len(segs) + 1):
                    if idx == len(segs) or np.isnan(segs[idx, 0]):
                        sub = segs[sub_start:idx]
                        if len(sub) >= 2:
                            diffs = sub[1:] - sub[:-1]
                            if float(np.sqrt((diffs ** 2).sum(axis=1)).sum()) >= min_unit_len:
                                good_subs.append(sub)
                        sub_start = idx + 1
                if not good_subs:
                    continue
                parts = []
                for sub in good_subs:
                    if parts:
                        parts.append(nan_row)
                    parts.append(sub)
                segs_list.append((_name, np.vstack(parts)))
            self.finished.emit(segs_list)
        except Exception as exc:
            self.status.emit(f"Flüsse nicht verfügbar ({exc})")
            self.finished.emit([])


class _Worker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object, str)
    error    = pyqtSignal(str)

    def __init__(self, query: str, grid_w: int, grid_h: int):
        super().__init__()
        self._query, self._grid_w, self._grid_h = query, grid_w, grid_h

    def run(self) -> None:
        try:
            self.progress.emit(3, "Contacting Nominatim…")
            geom, name = RegionFetcher().fetch(self._query)
            self.progress.emit(8, f'Got boundary for "{name}"…')
            grid = build_grid(geom, name,
                              grid_w=self._grid_w, grid_h=self._grid_h,
                              progress=self.progress.emit)
            self.finished.emit(grid, name)
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DampfrossDigital")
        self.resize(1200, 850)
        self.menuBar().setVisible(False)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Page 0 – main menu
        self._menu = MainMenuWidget()
        self._menu.load_region_clicked.connect(self._load_region)
        self._menu.open_map_clicked.connect(self._load_map)
        self._menu.play_clicked.connect(self._on_play_clicked)
        self._menu.multiplayer_clicked.connect(self._on_multiplayer_clicked)
        self._menu.options_clicked.connect(self._go_to_settings)
        self._menu.exit_clicked.connect(self.close)
        self._stack.addWidget(self._menu)

        # Page 1 – map (_build_map_page sets self._xxx attributes for all controls)
        self._map_page, self._map = self._build_map_page()
        self._map.hex_selected.connect(self._on_hex_selected)
        self._map.hex_painted.connect(self._on_hex_painted)
        self._map.corner_clicked.connect(self._on_corner_clicked)
        self._map.escape_pressed.connect(self._cancel_ferry)
        self._map.enter_pressed.connect(self._finish_ferry)
        self._map.game_hex_clicked.connect(self._game_hex_clicked)
        self._map.ferry_line_clicked.connect(self._game_ferry_clicked)
        self._map.ferry_line_clicked.connect(self._editor_ferry_delete)
        self._river_slider.valueChanged.connect(self._on_river_slider_changed)
        self._cov_sl.valueChanged.connect(self._on_terrain_changed)
        self._prom_sl.valueChanged.connect(self._on_terrain_changed)
        self._scat_sl.valueChanged.connect(self._on_terrain_changed)
        self._blobs_sl.valueChanged.connect(self._on_terrain_changed)
        self._stack.addWidget(self._map_page)

        # Page 2 – map view (observer mode)
        self._map_view = MapViewScreen()
        self._map_view.settings_clicked.connect(self._go_to_settings)
        self._stack.addWidget(self._map_view)

        # Page 3 – race phase
        self._race_screen = RaceScreen()
        self._race_screen.settings_clicked.connect(self._go_to_settings)
        self._stack.addWidget(self._race_screen)

        # Page 4 – scoreboard
        self._scoreboard = ScoreboardScreen()
        self._stack.addWidget(self._scoreboard)

        # Page 5 – end-of-round results
        self._results = ResultsScreen()
        self._results.next_round_clicked.connect(self._go_to_menu)
        self._results.back_clicked.connect(self._go_to_menu)
        self._stack.addWidget(self._results)

        # Page 6 – settings
        self._settings = SettingsScreen()
        self._settings.theme_changed.connect(self._on_theme_changed)
        self._settings.back_clicked.connect(self._go_back_from_settings)
        self._settings.pref_changed.connect(self._on_pref_changed)
        self._stack.addWidget(self._settings)
        self._settings_prev_page = _PAGE_MENU

        # Page 7 – game setup (replaces dialog)
        self._game_setup = GameSetupScreen()
        self._game_setup.back_clicked.connect(self._go_to_menu)
        self._game_setup.start_clicked.connect(self._on_game_setup_start)
        self._stack.addWidget(self._game_setup)

        # Page 8 – multiplayer lobby
        self._lobby = LobbyScreen()
        self._lobby.back_clicked.connect(self._go_to_menu)
        self._lobby.host_game_ready.connect(self._on_host_game_ready)
        self._lobby.client_game_ready.connect(self._on_client_game_ready)
        self._stack.addWidget(self._lobby)

        self._game_panel.roll_build.connect(self._game_roll_build)
        self._game_panel.end_turn.connect(self._game_end_turn)
        self._game_panel.declare_end_build.connect(self._game_declare_end_build)
        self._game_panel.undo_last.connect(self._game_undo_last)
        self._game_panel.delete_plan.connect(self._game_delete_plan)
        self._game_panel.roll_start.connect(self._game_roll_start)
        self._game_panel.roll_dest.connect(self._game_roll_dest)
        self._game_panel.join_journey.connect(self._game_join)
        self._game_panel.select_route.connect(self._game_select_route)
        self._game_panel.cooperate_with.connect(self._game_cooperate_with)
        self._game_panel.advance.connect(self._game_advance)
        self._game_panel.next_journey.connect(self._game_next_journey)
        self._game_panel.propose_alliance.connect(self._game_propose_alliance)
        self._game_panel.respond_alliance.connect(self._game_respond_alliance)
        self._game_panel.draw_custom_route.connect(self._on_draw_custom_route)
        self._game_panel.confirm_custom_route.connect(self._on_confirm_custom_route)
        self._game_panel.cancel_custom_route.connect(self._on_cancel_custom_route)

        self._display_name = ""
        self._land_count   = 0
        self._save_path:   Path | None = None
        self._game_state:  GameState | None = None
        self._ferry_wip:   list = []   # (row, col, corner_idx) waypoints in progress
        self._ai_players:  dict = {}   # player_idx → AIPlayer
        self._bot_acting:  bool = False   # True while _run_ai_step executes
        self._advance_timer:   QTimer | None = None
        self._advance_targets: dict = {}   # pidx → target position index
        self._boat_timer:      QTimer | None = None
        self._boat_anim_pidx:  int | None = None
        self._boat_anim_t:     float = 0.0
        self._boat_anim_ferry_idx: int = -1
        self._boat_anim_reverse: bool = False

        # Pref-driven timing and difficulty (updated live via _on_pref_changed)
        self._anim_speed_ms: int = 250
        self._bot_delay_ms:  int = 120
        self._ai_difficulty: int = 1

        # Custom route drawing state
        self._custom_route_mode: bool = False
        self._custom_route: list = []     # list of (r,c) tuples
        self._custom_route_pidx: int = -1

        # Network multiplayer state
        self._net_bridge = None     # NetworkBridge | None
        self._net_role   = "local"  # "local" | "host" | "client"
        self._net_slot   = 0        # this player's slot index (client mode)
        self._last_toast_player_idx = -1
        # Brief input-lock after a turn ends: prevents the previous player's
        # mouse from accidentally triggering the next player's first build click.
        self._build_input_blocked = False
        self._last_sound_player_idx = -1
        self._turn_toast = TurnToastWidget(self._map)

        # Turn notification sound (pygame Sound so it follows PipeWire routing)
        import pygame
        from .sfx_player import _ensure_mixer
        _ensure_mixer()
        _snd_path = Path(__file__).parent.parent / "sfx" / "notification.wav"
        try:
            self._turn_sound = pygame.mixer.Sound(str(_snd_path))
            self._turn_sound.set_volume(0.8)
        except Exception:
            self._turn_sound = None

        self._game_panel.route_hover.connect(self._on_route_hover)

        # Debounce timer for coastline recomputation (can be slow on large grids)
        self._coastline_timer = QTimer(self)
        self._coastline_timer.setSingleShot(True)
        self._coastline_timer.setInterval(180)
        self._coastline_timer.timeout.connect(self._apply_coastline)

        # Apply saved prefs to timers and map widget
        _sp = _settings_get_prefs()
        self._anim_speed_ms = {0: 400, 1: 250, 2: 100}.get(int(_sp.get("anim_speed", 1)), 250)
        self._bot_delay_ms  = {0: 300, 1: 120, 2: 0}.get(int(_sp.get("ai_speed", 1)), 120)
        self._ai_difficulty = int(_sp.get("ai_difficulty", 1))
        self._map.apply_prefs(_sp)

        self._music = MusicPlayer(self)
        self._music.apply_prefs(_sp)
        self._music.play_phase("menu")

        self._sfx = SfxPlayer(self)
        self._sfx.apply_prefs(_sp)

        self._stack.setCurrentIndex(_PAGE_MENU)
        self.statusBar().hide()

        self._worker: _Worker | None = None
        self._river_worker: _RiverWorker | None = None
        self._progress_dlg: ProgressDialog | None = None

        # Propagate saved theme to all screens (set_theme was called by
        # SettingsScreen.load_prefs but widgets were built before it ran)
        import dampfross.ui.design_tokens as _dt
        if _dt.current_theme() != "light":
            self._on_theme_changed(_dt.current_theme())

        # Apply saved accessibility prefs (font scale, CVD palette, etc.)
        self._apply_accessibility_prefs()

    # ------------------------------------------------------------------ #
    # Map page                                                             #
    # ------------------------------------------------------------------ #

    def _build_map_page(self):
        """
        Build the map page and set self._xxx for every interactive control.
        Returns (page_widget, hex_map_widget).
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── shared helpers ────────────────────────────────────────────── #
        _SEP_SS = f"color: {S_RULE}; background: transparent;"
        _PNL_SS = (
            f"background-color: {S_SURFACE_2}; border-bottom: 1px solid {S_RULE};"
        )

        def _sep(layout):
            l = QLabel("|"); l.setStyleSheet(_SEP_SS); layout.addWidget(l)

        def _slider(lo, hi, default, step, groove_clr, handle_clr):
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(lo, hi); sl.setValue(default)
            sl.setSingleStep(step); sl.setPageStep(step * 5)
            sl.setFixedWidth(100)
            sl.setStyleSheet(
                f"QSlider::groove:horizontal{{height:4px;background:{groove_clr};border-radius:2px;}}"
                f"QSlider::handle:horizontal{{width:12px;height:12px;margin:-4px 0;"
                f"background:{handle_clr};border-radius:6px;}}"
            )
            return sl

        def _lbl(text, color=S_INK_2):
            l = QLabel(text)
            l.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")
            return l

        def _title(text, color=S_INK_1):
            l = QLabel(text)
            l.setStyleSheet(
                f"color: {color}; font-size: 11px; font-weight: 600; background: transparent;"
            )
            return l

        # ── toolbar ──────────────────────────────────────────────────── #
        toolbar = QWidget()
        toolbar.setStyleSheet(_TOOLBAR_STYLE)
        toolbar.setFixedHeight(40)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 0, 8, 0)
        tl.setSpacing(8)

        back_btn = QPushButton("◀  Hauptmenü")
        back_btn.setStyleSheet(_TOOL_BTN)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self._go_to_menu)
        tl.addWidget(back_btn)

        _MENU_SS = (
            f"QMenu{{background:{S_SURFACE};color:{S_INK_1};border:1px solid {S_RULE};}}"
            f"QMenu::item{{padding:5px 22px;font-size:12px;}}"
            f"QMenu::item:selected{{background:{S_SUNK};color:{S_INK};}}"
            f"QMenu::separator{{height:1px;background:{S_RULE};margin:3px 0;}}"
        )
        file_btn = QPushButton("Datei  ▾")
        file_btn.setStyleSheet(_TOOL_BTN)
        file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        _file_menu = QMenu(file_btn)
        _file_menu.setStyleSheet(_MENU_SS)
        _file_menu.addAction("Karte öffnen…",         self._load_map)
        _file_menu.addAction("Speichern  Ctrl+S",     self._save_map)
        _file_menu.addAction("Speichern unter…",      self._save_map_as)
        _file_menu.addSeparator()
        _file_menu.addAction("PNG exportieren…",      self._export_png)
        _file_menu.addAction("PDF exportieren…",      self._export_pdf)
        file_btn.setMenu(_file_menu)
        tl.addWidget(file_btn)

        self._region_label = QLabel("")
        self._region_label.setStyleSheet(_LBL_STYLE)
        self._region_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._region_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tl.addWidget(self._region_label)

        self._river_label = QLabel("Flüsse: —")
        self._river_label.setStyleSheet(_LBL_STYLE)
        tl.addWidget(self._river_label)

        self._river_slider = QSlider(Qt.Orientation.Horizontal)
        self._river_slider.setRange(0, 0)
        self._river_slider.setValue(0)
        self._river_slider.setEnabled(False)
        self._river_slider.setFixedWidth(120)
        self._river_slider.setStyleSheet(
            f"QSlider::groove:horizontal{{height:4px;background:{S_RULE};border-radius:2px;}}"
            f"QSlider::handle:horizontal{{width:12px;height:12px;margin:-4px 0;"
            f"background:{S_INK_3};border-radius:6px;}}"
        )
        tl.addWidget(self._river_slider)

        for label, attr in [("Gelände",      "_terrain_btn"),
                             ("Küstenlinie", "_coast_btn"),
                             ("Bearbeiten",  "_edit_btn"),
                             ("Fähren",      "_ferry_btn")]:
            btn = QPushButton(label)
            btn.setStyleSheet(_TOOL_BTN)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            tl.addWidget(btn)
            setattr(self, attr, btn)

        fit_btn = QPushButton("Einpassen  [Ctrl+0]")
        fit_btn.setStyleSheet(_TOOL_BTN)
        fit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        tl.addWidget(fit_btn)

        layout.addWidget(toolbar)

        # ── terrain panel ─────────────────────────────────────────────── #
        terrain_panel = QWidget()
        terrain_panel.setStyleSheet(_PNL_SS)
        terrain_panel.setFixedHeight(38)
        tp = QHBoxLayout(terrain_panel)
        tp.setContentsMargins(10, 0, 10, 0); tp.setSpacing(10)

        tp.addWidget(_title("Gebirge:", S_TERRAIN_MOUNTAIN))

        self._cov_lbl  = _lbl("Abdeckung: oben 35%")
        self._cov_sl   = _slider(0, 95, 65,  1,  S_RULE, S_TERRAIN_MOUNTAIN)
        tp.addWidget(self._cov_lbl); tp.addWidget(self._cov_sl); _sep(tp)

        self._prom_lbl = _lbl("Min. Prominenz: 220 m")
        self._prom_sl  = _slider(0, 500, 220, 10, S_RULE, S_TERRAIN_MOUNTAIN)
        tp.addWidget(self._prom_lbl); tp.addWidget(self._prom_sl); _sep(tp)

        self._scat_lbl = _lbl("Streuung: 150 m")
        self._scat_sl  = _slider(0, 300, 150,  5,  S_RULE, S_TERRAIN_MOUNTAIN)
        tp.addWidget(self._scat_lbl); tp.addWidget(self._scat_sl); _sep(tp)

        self._blobs_lbl = _lbl("Flecken: 4")
        self._blobs_sl  = _slider(0, 20,  4,  1,  S_RULE, S_TERRAIN_MOUNTAIN)
        tp.addWidget(self._blobs_lbl); tp.addWidget(self._blobs_sl)
        tp.addStretch()

        terrain_panel.setVisible(False)
        self._terrain_btn.toggled.connect(terrain_panel.setVisible)
        layout.addWidget(terrain_panel)
        self._terrain_panel = terrain_panel

        # ── coastline panel ───────────────────────────────────────────── #
        coast_panel = QWidget()
        coast_panel.setStyleSheet(_PNL_SS)
        coast_panel.setFixedHeight(38)
        cp = QHBoxLayout(coast_panel)
        cp.setContentsMargins(10, 0, 10, 0); cp.setSpacing(10)

        cp.addWidget(_title("Küstenlinie:", S_RIVER))

        self._erosion_lbl = _lbl("Erosion: 28%")
        self._erosion_sl  = _slider(0, 50, 28, 1, S_RULE, S_RIVER)
        cp.addWidget(self._erosion_lbl); cp.addWidget(self._erosion_sl); _sep(cp)

        self._bridge_lbl  = _lbl("Brücken: 3×3")
        self._bridge_sl   = _slider(0, 2, 1, 1, S_RULE, S_RIVER)
        cp.addWidget(self._bridge_lbl); cp.addWidget(self._bridge_sl)
        cp.addStretch()

        coast_panel.setVisible(False)
        self._coast_btn.toggled.connect(coast_panel.setVisible)
        self._erosion_sl.valueChanged.connect(self._on_coastline_slider)
        self._bridge_sl.valueChanged.connect(self._on_coastline_slider)
        layout.addWidget(coast_panel)
        self._coast_panel = coast_panel

        # ── edit panel ────────────────────────────────────────────────── #
        def _brush_ss(c, bg, bc):
            return (
                f"QPushButton{{background:{S_SURFACE};color:{c};"
                f"border:1px solid {S_RULE};border-radius:4px;"
                f"padding:3px 12px;font-size:11px;}}"
                f"QPushButton:checked{{background:{bg};border-color:{bc};color:{S_INK};}}"
                f"QPushButton:hover{{background:{S_SUNK};}}"
            )

        edit_panel = QWidget()
        edit_panel.setStyleSheet(_PNL_SS)
        edit_panel.setFixedHeight(38)
        ep = QHBoxLayout(edit_panel)
        ep.setContentsMargins(10, 0, 10, 0); ep.setSpacing(8)

        ep.addWidget(_title("Pinsel:"))

        self._brush_sea    = QPushButton("Meer")
        self._brush_plain  = QPushButton("Ebene")
        self._brush_mtn    = QPushButton("Gebirge")
        self._brush_forest = QPushButton("Wald")
        self._brush_desert = QPushButton("Wüste")
        self._brush_swamp  = QPushButton("Sumpf")
        self._brush_other  = QPushButton("Sonstiges")
        self._brush_city   = QPushButton("Stadt")
        for btn, c, bg, bc in [
            (self._brush_sea,    S_RIVER,             "#dde9fb",   S_RIVER),
            (self._brush_plain,  S_INK_2,             S_SUNK,      S_INK_3),
            (self._brush_mtn,    S_TERRAIN_MOUNTAIN,  "#e8e0d0",   S_TERRAIN_MOUNTAIN),
            (self._brush_forest, "#1f7a4a",            "#d9e7d1",   "#1f7a4a"),
            (self._brush_desert, "#8a6500",            "#ecd6a8",   "#8a6500"),
            (self._brush_swamp,  "#5a5f6a",            "#c9c8b1",   "#5a5f6a"),
            (self._brush_other,  S_INK_3,             S_RULE,      S_INK_4),
            (self._brush_city,   S_DANGER,             "#fcdede",   S_DANGER),
        ]:
            btn.setCheckable(True)
            btn.setStyleSheet(_brush_ss(c, bg, bc))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            ep.addWidget(btn)
        self._brush_plain.setChecked(True)

        self._brush_sea.clicked.connect(lambda: self._set_brush("sea"))
        self._brush_plain.clicked.connect(lambda: self._set_brush("plain"))
        self._brush_mtn.clicked.connect(lambda: self._set_brush("mountain"))
        self._brush_forest.clicked.connect(lambda: self._set_brush("forest"))
        self._brush_desert.clicked.connect(lambda: self._set_brush("desert"))
        self._brush_swamp.clicked.connect(lambda: self._set_brush("swamp"))
        self._brush_other.clicked.connect(lambda: self._set_brush("other"))
        self._brush_city.clicked.connect(lambda: self._set_brush("city"))
        ep.addStretch()

        edit_panel.setVisible(False)
        self._edit_btn.toggled.connect(edit_panel.setVisible)
        self._edit_btn.toggled.connect(self._on_edit_toggled)
        layout.addWidget(edit_panel)
        self._edit_panel = edit_panel

        # ── ferry panel ───────────────────────────────────────────────── #
        _FBTN_SS = (
            f"QPushButton{{background:{S_SURFACE};color:{S_INK_1};"
            f"border:1px solid {S_RULE};border-radius:4px;"
            f"padding:3px 10px;font-size:11px;}}"
            f"QPushButton:hover{{background:{S_SUNK};}}"
            f"QPushButton:checked{{background:{S_SUNK};border-color:{S_INK_3};}}"
            f"QPushButton:disabled{{color:{S_INK_4};border-color:{S_RULE};}}"
        )
        ferry_panel = QWidget()
        ferry_panel.setStyleSheet(_PNL_SS)
        ferry_panel.setFixedHeight(38)
        fp = QHBoxLayout(ferry_panel)
        fp.setContentsMargins(10, 0, 10, 0); fp.setSpacing(10)

        fp.addWidget(_title("Fähren:", S_RIVER))

        self._ferry_status = _lbl("Startfeld klicken, dann Routenfelder, dann Endfeld  (0 / 5)")
        fp.addWidget(self._ferry_status)

        self._ferry_finish_btn = QPushButton("Fertig")
        self._ferry_finish_btn.setStyleSheet(_FBTN_SS)
        self._ferry_finish_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ferry_finish_btn.setEnabled(False)
        fp.addWidget(self._ferry_finish_btn)

        self._ferry_cancel_btn = QPushButton("Abbrechen")
        self._ferry_cancel_btn.setStyleSheet(_FBTN_SS)
        self._ferry_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fp.addWidget(self._ferry_cancel_btn)

        _sep(fp)

        self._ferry_delete_btn = QPushButton("Nächste löschen")
        self._ferry_delete_btn.setCheckable(True)
        self._ferry_delete_btn.setStyleSheet(_FBTN_SS)
        self._ferry_delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fp.addWidget(self._ferry_delete_btn)

        _sep(fp)

        self._ferry_count_lbl = _lbl("0 Routen")
        fp.addWidget(self._ferry_count_lbl)

        _sep(fp)

        fp.addWidget(_title("Max. Fähren/Spieler:", S_RIVER))
        self._ferry_max_sl = QSlider(Qt.Orientation.Horizontal)
        self._ferry_max_sl.setRange(1, 5)
        self._ferry_max_sl.setValue(1)
        self._ferry_max_sl.setFixedWidth(80)
        self._ferry_max_sl.setStyleSheet(
            f"QSlider::groove:horizontal{{height:4px;background:{S_RULE};border-radius:2px;}}"
            f"QSlider::handle:horizontal{{width:12px;height:12px;margin:-4px 0;"
            f"background:{S_RIVER};border-radius:6px;}}"
        )
        fp.addWidget(self._ferry_max_sl)
        self._ferry_max_val_lbl = _lbl("1")
        fp.addWidget(self._ferry_max_val_lbl)
        self._ferry_max_sl.valueChanged.connect(self._on_ferry_max_changed)

        fp.addStretch()

        self._ferry_finish_btn.clicked.connect(self._finish_ferry)
        self._ferry_cancel_btn.clicked.connect(self._cancel_ferry)
        self._ferry_delete_btn.toggled.connect(self._on_ferry_delete_toggled)
        ferry_panel.setVisible(False)
        self._ferry_btn.toggled.connect(ferry_panel.setVisible)
        self._ferry_btn.toggled.connect(self._on_ferry_toggled)
        layout.addWidget(ferry_panel)
        self._ferry_panel = ferry_panel

        # ── hex map + game panel ──────────────────────────────────────── #
        content_w = QWidget()
        content_l = QHBoxLayout(content_w)
        content_l.setContentsMargins(0, 0, 0, 0)
        content_l.setSpacing(0)

        hex_map = HexMapWidget()
        fit_btn.clicked.connect(hex_map.fit_to_view)
        content_l.addWidget(hex_map, stretch=1)

        self._game_panel = GamePanel()
        self._game_panel.hide()
        content_l.addWidget(self._game_panel)

        layout.addWidget(content_w)

        QShortcut(QKeySequence("Ctrl+S"), page).activated.connect(self._save_map)
        QShortcut(QKeySequence("Ctrl+O"), page).activated.connect(self._load_map)

        # Score overlay — child of the map page so it covers the whole game view
        self._score_overlay = ScoreOverlay(page)
        self._score_overlay.raise_()
        QShortcut(QKeySequence(Qt.Key.Key_Tab), page).activated.connect(
            self._toggle_score_overlay
        )

        return page, hex_map

    # ------------------------------------------------------------------ #
    # Editor visibility                                                    #
    # ------------------------------------------------------------------ #

    def _set_editor_visible(self, visible: bool) -> None:
        for w in (self._river_label, self._river_slider,
                  self._terrain_btn, self._coast_btn,
                  self._edit_btn, self._ferry_btn):
            w.setVisible(visible)
        if not visible:
            for panel in (self._terrain_panel, self._coast_panel,
                          self._edit_panel, self._ferry_panel):
                panel.setVisible(False)
            for btn in (self._terrain_btn, self._coast_btn,
                        self._edit_btn, self._ferry_btn):
                btn.setChecked(False)

    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #

    def _go_to_menu(self) -> None:
        self._stack.setCurrentIndex(_PAGE_MENU)
        self.setWindowTitle("DampfrossDigital")
        self.statusBar().hide()
        self._music.play_phase("menu")

    def _go_to_settings(self) -> None:
        self._settings_prev_page = self._stack.currentIndex()
        self._stack.setCurrentIndex(_PAGE_SETTINGS)

    def _go_back_from_settings(self) -> None:
        self._stack.setCurrentIndex(self._settings_prev_page)

    _ACCESSIBILITY_KEYS = frozenset((
        "color_vision", "high_contrast", "font_size", "bold_labels",
        "reduce_motion", "reduce_pan", "disable_blink",
        "extended_focus", "persistent_tooltips", "screenreader",
    ))

    def _on_pref_changed(self, key: str, val) -> None:
        if key == "anim_speed":
            self._anim_speed_ms = {0: 400, 1: 250, 2: 100}.get(int(val), 250)
        elif key == "ai_speed":
            self._bot_delay_ms = {0: 300, 1: 120, 2: 0}.get(int(val), 120)
        elif key == "ai_difficulty":
            self._ai_difficulty = int(val)
        elif key in ("mouse_zoom", "zoom_invert", "scroll_sensitivity"):
            self._map.apply_prefs({key: val})
        elif key in ("music_enabled", "music_menu", "music_volume"):
            self._music.apply_prefs(_settings_get_prefs())
        elif key == "sfx_enabled":
            self._sfx.apply_prefs(_settings_get_prefs())
        elif key in ("show_name_labels", "highlight_ferries"):
            self._map.apply_prefs({key: val})
        elif key == "hud_scale":
            self._game_panel.apply_prefs({"hud_scale": val})
        elif key in self._ACCESSIBILITY_KEYS:
            self._apply_accessibility_prefs()

    def _apply_accessibility_prefs(self) -> None:
        """Re-apply all Barrierefreiheit settings from saved prefs."""
        import dampfross.ui.design_tokens as _dt
        from .settings_screen import get_prefs as _get_prefs

        prefs = _get_prefs()
        _dt.apply_accessibility(prefs)

        # persistent_tooltips: -1 = never hide automatically
        # (setToolTipDuration is not available in all PyQt6 builds — guard it)
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None and hasattr(app, "setToolTipDuration"):
            app.setToolTipDuration(-1 if prefs.get("persistent_tooltips") else 10_000)

        # screenreader: set accessible names on key interactive elements
        if prefs.get("screenreader", False):
            self._set_accessible_names()

        # Visual refresh — propagates font scale, CVD colors, contrast, focus ring
        self._on_theme_changed(_dt.current_theme())

    def _set_accessible_names(self) -> None:
        """Annotate key widgets with accessible names for AT software."""
        self._menu.setAccessibleName("Hauptmenü")
        self._map.setAccessibleName("Spielkarte")
        self._game_panel.setAccessibleName("Spielpanel")
        self._settings.setAccessibleName("Einstellungen")
        self._scoreboard.setAccessibleName("Punktestand")
        self._results.setAccessibleName("Spielergebnis")
        self._game_setup.setAccessibleName("Spielvorbereitung")
        self._lobby.setAccessibleName("Mehrspieler-Lobby")

    def _go_to_map_view(self) -> None:
        self._stack.setCurrentIndex(_PAGE_MAP_VIEW)

    def _go_to_race(self) -> None:
        self._stack.setCurrentIndex(_PAGE_RACE)

    def _go_to_scoreboard(self) -> None:
        self._stack.setCurrentIndex(_PAGE_SCOREBOARD)

    def _go_to_results(self) -> None:
        self._stack.setCurrentIndex(_PAGE_RESULTS)

    def _toggle_score_overlay(self) -> None:
        gs = self._game_state
        if gs is None or self._stack.currentIndex() != _PAGE_MAP:
            return
        if self._score_overlay.isVisible():
            self._score_overlay.hide_scoreboard()
        else:
            self._score_overlay.show_scoreboard(gs)

    def _show_results(self) -> None:
        gs = self._game_state
        if gs is None:
            return
        self._results.populate(gs)
        self._stack.setCurrentIndex(_PAGE_RESULTS)

    def _on_theme_changed(self, theme_name: str) -> None:
        import dampfross.ui.design_tokens as _dt
        QApplication.instance().setStyleSheet(_dt.app_stylesheet())
        self._menu.refresh_theme()
        self._map.refresh_theme()
        self._game_panel.refresh_theme()
        self._settings.refresh_theme()
        self._map_view.refresh_theme()
        self._race_screen.refresh_theme()
        self._scoreboard.refresh_theme()
        self._results.refresh_theme()
        self._game_setup.refresh_theme()
        self._lobby.refresh_theme()
        if self._game_state is not None:
            self._game_refresh_ui()

    def _show_map(self) -> None:
        self._stack.setCurrentIndex(_PAGE_MAP)
        self.statusBar().show()

    # ------------------------------------------------------------------ #
    # Load region                                                          #
    # ------------------------------------------------------------------ #

    def _load_region(self) -> None:
        dlg = LoadRegionDialog(self)
        if dlg.exec() != LoadRegionDialog.DialogCode.Accepted:
            return
        query = dlg.region_name()
        if not query:
            return
        grid_w, grid_h = dlg.grid_size()

        self._progress_dlg = ProgressDialog("Region laden", self)
        self._progress_dlg.show()

        self._river_slider.setEnabled(False)
        self._river_label.setText("Rivers: —")

        self._worker = _Worker(query, grid_w, grid_h)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, pct: int, msg: str) -> None:
        if self._progress_dlg:
            self._progress_dlg.update_progress(pct, msg)

    def _apply_grid(self, grid, display_name: str) -> None:
        """Wire a loaded/built grid into all UI widgets."""
        self._game_state = None
        self._map.set_game_mode(None)
        self._map.set_player_tracks([])
        self._map.set_train_positions([])
        self._map.set_game_reachable(set())
        self._map.set_build_endpoint(None)
        self._game_panel.hide()
        self._set_editor_visible(True)
        self._map.set_grid(grid)
        self._display_name = display_name
        self._land_count   = int(grid.cells.sum())

        n_rivers = len(grid.river_segs)
        self._river_slider.blockSignals(True)
        self._river_slider.setRange(0, n_rivers)
        self._river_slider.setValue(grid.river_count)
        self._river_slider.blockSignals(False)
        self._river_slider.setEnabled(n_rivers > 0)
        self._river_label.setText(f"Flüsse: {grid.river_count}")
        self._map.set_river_count(grid.river_count)

        self._update_region_label(grid)
        self._refresh_ferry_count(grid)
        self.setWindowTitle(f"DampfrossDigital  —  {display_name}")
        self.statusBar().show()
        self.statusBar().showMessage("Scrollen zum Zoomen · Ziehen zum Verschieben · Klicken zum Auswählen")
        self._show_map()

    def _on_finished(self, grid, display_name: str) -> None:
        if self._progress_dlg:
            self._progress_dlg.accept()
            self._progress_dlg = None

        # Keep other_land (surrounding world land) but drop the border lines
        grid.country_border_segs = []

        self._apply_grid(grid, display_name)
        self._save_path = None

        # Start river fetch in background now that map is visible
        self._river_worker = _RiverWorker(grid)
        self._river_worker.status.connect(self.statusBar().showMessage)
        self._river_worker.finished.connect(self._on_rivers_finished)
        self._river_worker.start()

    def _on_rivers_finished(self, segs_list: list) -> None:
        grid = self._map.hex_grid
        if grid is None:
            return
        if segs_list and isinstance(segs_list[0], tuple):
            grid.river_names = [item[0] for item in segs_list]
            grid.river_segs  = [item[1] for item in segs_list]
        else:
            grid.river_segs  = segs_list   # backwards-compat (loaded .dmpfmap)
        n = len(grid.river_segs)
        default = min(10, n)
        grid.river_count = default

        self._river_slider.blockSignals(True)
        self._river_slider.setRange(0, n)
        self._river_slider.setValue(default)
        self._river_slider.blockSignals(False)
        self._river_slider.setEnabled(n > 0)
        self._river_label.setText(f"Flüsse: {default}")
        self._map.set_river_count(default)

        msg = f"{n} Flüsse geladen" if n else "Keine Flüsse gefunden"
        self.statusBar().showMessage(
            f"Scrollen zum Zoomen · Ziehen zum Verschieben · Klicken zum Auswählen · {msg}"
        )

    def _on_error(self, msg: str) -> None:
        if self._progress_dlg:
            self._progress_dlg.reject()
            self._progress_dlg = None
        QMessageBox.critical(self, "Fehler beim Laden der Region", msg)

    # ------------------------------------------------------------------ #
    # File operations — open / save / export                              #
    # ------------------------------------------------------------------ #

    def _load_map(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Karte öffnen", str(_maps_dir()), "DampfrossMap-Dateien (*.dmpfmap)"
        )
        if not path:
            return
        try:
            from ..core.map_file import load_map
            grid = load_map(path)
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Laden der Karte", str(exc))
            return
        self._apply_grid(grid, grid.region_name)
        self._save_path = Path(path)

    def _save_map(self) -> None:
        if self._map.hex_grid is None:
            return
        if self._save_path is None:
            self._save_map_as()
        else:
            self._do_save(self._save_path)

    def _save_map_as(self) -> None:
        if self._map.hex_grid is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Karte speichern", str(Path.home()), "DampfrossMap-Dateien (*.dmpfmap)"
        )
        if not path:
            return
        if not path.endswith(".dmpfmap"):
            path += ".dmpfmap"
        self._do_save(Path(path))

    def _do_save(self, path: Path) -> None:
        try:
            from ..core.map_file import save_map
            save_map(self._map.hex_grid, path)
            self._save_path = path
            self.statusBar().showMessage(f"Gespeichert  {path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Speichern der Karte", str(exc))

    def _export_png(self) -> None:
        grid = self._map.hex_grid
        if grid is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "PNG exportieren", str(Path.home()), "PNG-Bilder (*.png)"
        )
        if not path:
            return
        if not path.endswith(".png"):
            path += ".png"
        from ..core.hex_grid import SQRT3
        hex_size = min(
            2000.0 / max(grid.cols * SQRT3,          1),
            2000.0 / max((grid.rows - 1) * 1.5 + 2, 1),
            40.0,
        )
        pix = self._map.render_for_export(target_hex_px=max(hex_size, 6.0), crop_hexes=1)
        if not pix.save(path):
            QMessageBox.critical(self, "Export fehlgeschlagen", f"Konnte nicht schreiben: {path}")
        else:
            self.statusBar().showMessage(f"PNG exportiert  {Path(path).name}")

    def _export_pdf(self) -> None:
        grid = self._map.hex_grid
        if grid is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "PDF exportieren", str(Path.home()), "PDF-Dateien (*.pdf)"
        )
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"
        try:
            from PyQt6.QtGui import QPainter, QPdfWriter, QPageLayout, QPageSize
            from PyQt6.QtCore import QMarginsF
            from ..core.hex_grid import SQRT3

            writer = QPdfWriter(path)
            page_size = QPageSize(QPageSize.PageSizeId.A3)
            layout = QPageLayout(
                page_size,
                QPageLayout.Orientation.Landscape,
                QMarginsF(0, 0, 0, 0),
            )
            writer.setPageLayout(layout)
            writer.setResolution(150)

            rect = writer.pageLayout().paintRectPixels(150)
            pw, ph = rect.width(), rect.height()

            hex_size = min(
                pw / max(grid.cols * SQRT3,          1),
                ph / max((grid.rows - 1) * 1.5 + 2, 1),
            ) * 0.99

            pix = self._map.render_for_export(
                target_hex_px=max(hex_size, 2.0), crop_hexes=1
            )
            scaled = pix.scaled(
                pw, ph,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter = QPainter(writer)
            x = (pw - scaled.width())  // 2
            y = (ph - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()

            self.statusBar().showMessage(f"PDF exportiert  {Path(path).name}")
        except Exception as exc:
            QMessageBox.critical(self, "Export fehlgeschlagen", str(exc))

    # ------------------------------------------------------------------ #
    # River slider                                                         #
    # ------------------------------------------------------------------ #

    def _on_river_slider_changed(self, val: int) -> None:
        self._river_label.setText(f"Flüsse: {val}")
        self._map.set_river_count(val)

    # ------------------------------------------------------------------ #
    # Terrain sliders                                                      #
    # ------------------------------------------------------------------ #

    def _on_terrain_changed(self) -> None:
        grid = self._map.hex_grid
        if grid is None or grid.elevation is None:
            return
        self._recompute_mountains(grid)
        self._map.refresh_overview()
        self._map.update()

    def _recompute_mountains(self, grid) -> None:
        pct   = self._cov_sl.value()
        prom  = self._prom_sl.value()
        scat  = self._scat_sl.value()
        blobs = self._blobs_sl.value()

        cov_text = "keine" if pct == 0 else f"oben {100 - pct}%"
        self._cov_lbl.setText(f"Abdeckung: {cov_text}")
        self._prom_lbl.setText(f"Min. Prominenz: {prom} m")
        self._scat_lbl.setText(f"Streuung: {scat} m")
        self._blobs_lbl.setText(f"Flecken: {blobs}")

        if pct == 0:
            import numpy as np
            grid.is_mountainous = np.zeros((grid.rows, grid.cols), dtype=bool)
            self._update_region_label(grid)
            return

        grid.is_mountainous = _compute_mountainous(
            grid.elevation, 1,
            grid.rows, grid.cols, grid.cells,
            river_mask=grid.river_mask,
            percentile=pct,
            prom_floor=float(prom),
            scatter_prom=float(scat),
            scatter_max=blobs,
            scatter_blob=5,
        )
        for city in grid.cities:
            if grid.is_mountainous is not None:
                grid.is_mountainous[city["row"], city["col"]] = False

        self._update_region_label(grid)

    # ------------------------------------------------------------------ #
    # Coastline sliders                                                    #
    # ------------------------------------------------------------------ #

    def _on_coastline_slider(self) -> None:
        self._coastline_timer.start()   # restart debounce

    def _apply_coastline(self) -> None:
        grid = self._map.hex_grid
        if grid is None or grid.proj_geom is None:
            return

        erosion     = self._erosion_sl.value() / 100.0
        bridge_idx  = self._bridge_sl.value()
        bridge_kern = [0, 3, 5][bridge_idx]

        self._erosion_lbl.setText(f"Erosion: {int(erosion * 100)}%")
        self._bridge_lbl.setText(f"Brücken: {['Keine', '3×3', '5×5'][bridge_idx]}")

        grid.cells = recompute_cells(grid, erosion, bridge_kern)
        grid.compute_border_segs()
        self._land_count = int(grid.cells.sum())

        if grid.elevation is not None:
            self._recompute_mountains(grid)
        else:
            self._update_region_label(grid)

        self._map.refresh_overview()
        self._map.update()

    # ------------------------------------------------------------------ #
    # Edit / paint mode                                                    #
    # ------------------------------------------------------------------ #

    def _on_edit_toggled(self, enabled: bool) -> None:
        self._map.set_paint_mode(enabled)

    def _set_brush(self, brush: str) -> None:
        for btn, name in [
            (self._brush_sea,    "sea"),
            (self._brush_plain,  "plain"),
            (self._brush_mtn,    "mountain"),
            (self._brush_forest, "forest"),
            (self._brush_desert, "desert"),
            (self._brush_swamp,  "swamp"),
            (self._brush_other,  "other"),
            (self._brush_city,   "city"),
        ]:
            btn.setChecked(name == brush)
        self._map.set_brush(brush)

    def _on_hex_painted(self, row: int, col: int, brush: str) -> None:
        import numpy as np
        grid = self._map.hex_grid
        if grid is None or not grid.is_valid(row, col):
            return

        if grid.is_mountainous is None:
            grid.is_mountainous = np.zeros((grid.rows, grid.cols), dtype=bool)
        if grid.other_land is None:
            grid.other_land = np.zeros((grid.rows, grid.cols), dtype=bool)

        if brush == "sea":
            grid.cells[row, col]          = False
            grid.is_mountainous[row, col] = False
            grid.other_land[row, col]     = False
            grid.terrain_overrides.pop((row, col), None)
            grid.compute_border_segs()
        elif brush == "plain":
            grid.cells[row, col]          = True
            grid.is_mountainous[row, col] = False
            grid.other_land[row, col]     = False
            grid.terrain_overrides.pop((row, col), None)
            grid.compute_border_segs()
        elif brush == "mountain":
            grid.cells[row, col]          = True
            grid.is_mountainous[row, col] = True
            grid.other_land[row, col]     = False
            grid.terrain_overrides.pop((row, col), None)
            grid.compute_border_segs()
        elif brush in ("forest", "desert", "swamp"):
            grid.cells[row, col]          = True
            grid.is_mountainous[row, col] = False
            grid.other_land[row, col]     = False
            grid.terrain_overrides[(row, col)] = brush
            grid.compute_border_segs()
        elif brush == "other":
            grid.cells[row, col]          = False
            grid.is_mountainous[row, col] = False
            grid.other_land[row, col]     = True
            grid.terrain_overrides.pop((row, col), None)
            # other_land doesn't affect border_segs — no recompute needed
        elif brush == "city":
            self._edit_city(grid, row, col)
            return   # _edit_city handles its own refresh

        self._map.refresh_overview()
        self._map.update()
        self._update_region_label(grid)

    def _edit_city(self, grid, row: int, col: int) -> None:
        existing = next(
            (c for c in grid.cities if c["row"] == row and c["col"] == col), None
        )
        if existing:
            dlg = CityEditDialog(existing["name"], is_new=False, parent=self)
            if dlg.exec() == CityEditDialog.DialogCode.Accepted:
                if dlg.was_deleted():
                    grid.cities.remove(existing)
                else:
                    name = dlg.city_name()
                    if name:
                        existing["name"] = name
        elif grid.is_land(row, col):
            dlg = CityEditDialog("New City", is_new=True, parent=self)
            if dlg.exec() == CityEditDialog.DialogCode.Accepted:
                name = dlg.city_name()
                if name:
                    used = {c["number"] for c in grid.cities}
                    next_num = next((n for n in _CITY_NUMBERS if n not in used), 99)
                    grid.cities.append({
                        "row": row, "col": col,
                        "name": name,
                        "population": 0,
                        "number": next_num,
                    })

        self._map.refresh_overview()
        self._map.update()
        self._update_region_label(grid)

    def _update_region_label(self, grid) -> None:
        self._land_count = int(grid.cells.sum())
        mtn = int(grid.is_mountainous.sum()) if grid.is_mountainous is not None else 0
        self._region_label.setText(
            f"{self._display_name}   ·   {self._land_count:,} Land   ·   {mtn:,} Bergfelder"
        )

    # ------------------------------------------------------------------ #
    # Ferry routing                                                        #
    # ------------------------------------------------------------------ #

    def _on_ferry_toggled(self, enabled: bool) -> None:
        self._map.set_ferry_mode(enabled)
        if not enabled:
            self._cancel_ferry()

    def _on_ferry_max_changed(self, value: int) -> None:
        self._ferry_max_val_lbl.setText(str(value))
        grid = self._map.hex_grid
        if grid is not None:
            grid.max_ferries_per_player = value

    def _on_corner_clicked(self, row: int, col: int, ci: int) -> None:
        grid = self._map.hex_grid
        if grid is None:
            return

        is_first = len(self._ferry_wip) == 0
        if is_first and not grid.is_land(row, col):
            self._ferry_status.setText("Startfeld muss Landfeld sein")
            return

        self._ferry_wip.append((row, col))
        n = len(self._ferry_wip)
        self._ferry_status.setText(
            f"{n} / 5 Felder"
            + ("  —  Rechtsklick oder Fertig zum Bestätigen" if n >= 2 else "")
        )
        self._ferry_finish_btn.setEnabled(n >= 2)
        self._map.set_ferry_wip(list(self._ferry_wip))

        if n >= 5:
            self._finish_ferry()

    def _finish_ferry(self) -> None:
        if len(self._ferry_wip) < 2:
            return
        grid = self._map.hex_grid
        if grid is None:
            return
        er, ec = self._ferry_wip[-1]
        if not grid.is_land(er, ec):
            self._ferry_status.setText("Endfeld muss Landfeld sein")
            return
        grid.ferries.append({"waypoints": list(self._ferry_wip)})
        self._refresh_ferry_count(grid)
        self._cancel_ferry()
        self._map.update()

    def _on_ferry_delete_toggled(self, enabled: bool) -> None:
        self._map.set_ferry_delete_mode(enabled)
        if enabled:
            self._cancel_ferry()   # discard any WIP route
            self._ferry_status.setText("Fährlinie zum Löschen anklicken")
        else:
            self._ferry_status.setText(
                "Startfeld klicken, dann Routenfelder, dann Endfeld  (0 / 5)"
            )

    def _editor_ferry_delete(self, fidx: int) -> None:
        """Delete a ferry by index — only active in editor delete mode."""
        if self._game_state is not None:
            return   # game mode handles ferry_line_clicked separately
        if not self._ferry_delete_btn.isChecked():
            return
        grid = self._map.hex_grid
        if grid is None or fidx >= len(grid.ferries):
            return
        grid.ferries.pop(fidx)
        self._refresh_ferry_count(grid)
        self._map.update()

    def _cancel_ferry(self) -> None:
        self._ferry_wip.clear()
        self._ferry_status.setText(
            "Startfeld klicken, dann Routenfelder, dann Endfeld  (0 / 5)"
        )
        self._ferry_finish_btn.setEnabled(False)
        self._map.set_ferry_wip([])

    def _refresh_ferry_count(self, grid) -> None:
        n = len(grid.ferries)
        self._ferry_count_lbl.setText(f"{n} Route{'n' if n != 1 else ''}")
        max_f = getattr(grid, "max_ferries_per_player", 1)
        self._ferry_max_sl.blockSignals(True)
        self._ferry_max_sl.setValue(max_f)
        self._ferry_max_sl.blockSignals(False)
        self._ferry_max_val_lbl.setText(str(max_f))

    @staticmethod
    def _nearest_ferry_idx(grid, row: int, col: int, ci: int) -> int:
        """Return index of the ferry whose nearest waypoint is closest to (row,col,ci)."""
        from ..core.hex_grid import HexGrid
        cx, cy = HexGrid.hex_center(row, col, 1.0)
        click_x, click_y = HexGrid.hex_corners(cx, cy, 1.0)[ci]
        best_idx, best_d = -1, float("inf")
        for i, ferry in enumerate(grid.ferries):
            for r, c, cii in ferry.get("waypoints", []):
                cx2, cy2 = HexGrid.hex_center(r, c, 1.0)
                wx, wy = HexGrid.hex_corners(cx2, cy2, 1.0)[cii]
                d = math.hypot(wx - click_x, wy - click_y)
                if d < best_d:
                    best_d, best_idx = d, i
        return best_idx if best_d < 1.5 else -1

    # ------------------------------------------------------------------ #
    # Hex selection                                                        #
    # ------------------------------------------------------------------ #

    def _on_hex_selected(self, row: int, col: int, hex_id: int) -> None:
        grid = self._map.hex_grid
        if grid is None:
            return
        kind = "land" if grid.is_land(row, col) else "sea"
        city_info = next(
            (c for c in grid.cities if c["row"] == row and c["col"] == col), None
        )
        if city_info:
            pop = city_info["population"]
            pop_str = f"{pop:,}" if pop else "pop unknown"
            msg = (f"City {city_info['number']} · {city_info['name']}  "
                   f"({pop_str})  ·  row {row}  col {col}  id {hex_id}")
        else:
            msg = f"Selected · row {row}  col {col}  id {hex_id}  [{kind}]"
        self.statusBar().showMessage(msg)

    # ------------------------------------------------------------------ #
    # Gameplay                                                             #
    # ------------------------------------------------------------------ #

    def _on_play_clicked(self) -> None:
        self._stack.setCurrentIndex(_PAGE_GAME_SETUP)

    def _on_multiplayer_clicked(self) -> None:
        self._lobby.reset()
        self._stack.setCurrentIndex(_PAGE_LOBBY)

    def _on_host_game_ready(self, bridge, player_configs: list,
                             map_path: str, capital: int, win_target: int,
                             game_options: dict) -> None:
        """Host starts the multiplayer game."""
        try:
            from ..core.map_file import load_map
            grid = load_map(map_path)
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Laden der Karte", str(exc))
            return
        self._apply_grid(grid, grid.region_name)
        self._save_path = Path(map_path)
        self._net_bridge = bridge
        self._net_role   = "host"
        self._net_slot   = 0
        bridge.action_received.connect(self._on_remote_action)
        self._start_game(grid, player_configs, capital, win_target, game_options)

    def _on_client_game_ready(self, bridge, player_configs: list) -> None:
        """Client receives game start — loads map from bytes then begins."""
        map_bytes = getattr(bridge, "_pending_map_bytes", None)
        if not map_bytes:
            QMessageBox.critical(self, "Fehler", "Kartendaten nicht vom Host empfangen.")
            return
        try:
            from ..core.map_file import load_map_bytes
            grid = load_map_bytes(map_bytes)
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Laden der Karte", str(exc))
            return
        self._apply_grid(grid, grid.region_name)
        self._net_bridge = bridge
        self._net_role   = "client"
        # Use the slot confirmed by join_ack; fall back to slot-matching by name/color
        if bridge._my_slot >= 0:
            self._net_slot = bridge._my_slot
        else:
            my_name  = bridge._name
            my_color = bridge._color
            self._net_slot = next(
                (pc["slot"] for pc in player_configs
                 if pc.get("name") == my_name and pc.get("color") == my_color),
                1,
            )
        bridge.state_received.connect(self._apply_network_state)
        self._start_game(grid, player_configs, 20, 250)  # capital/win overridden by state

    def _apply_network_state(self, state_dict: dict) -> None:
        """Client: replace game state from host broadcast and refresh UI."""
        gs = self._game_state
        if gs is None:
            return
        old_roll = gs.last_roll
        from ..net.serializer import deserialize_state
        try:
            new_gs = deserialize_state(state_dict, gs.grid)
        except Exception as exc:
            self.statusBar().showMessage(f"[net] state error: {exc}")
            return
        # Show dice animation if a new roll arrived since the last broadcast
        if new_gs.last_roll and new_gs.last_roll != old_roll:
            d1, d2 = new_gs.last_roll
            city_mode = (new_gs.phase == "operate")
            self._show_dice_roll(d1, d2, new_gs.players[new_gs.player_idx].name,
                                 city_mode=city_mode)
        self._game_state = new_gs
        self._game_refresh_ui()

    def _on_remote_action(self, sender_slot: int, action_dict: dict) -> None:
        """Host: apply an action received from a remote client."""
        gs = self._game_state
        if gs is None or gs.winner is not None:
            return
        # Verify the action is from the player whose turn it is
        # (or a journey participant for Advance)
        t = action_dict.get("type", "")
        if t == "Advance":
            pass  # any participant can trigger advance
        elif gs.player_idx != sender_slot:
            return  # not this player's turn

        self._apply_remote_action_dict(t, action_dict)
        self._net_broadcast_state()

    def _apply_remote_action_dict(self, t: str, d: dict) -> None:
        """Dispatch an action dict from a remote client to the right handler."""
        if t == "RollBuild":
            self._bot_acting = True
            try:
                self._game_roll_build()
            finally:
                self._bot_acting = False
        elif t == "PlaceEdge":
            self._bot_acting = True
            try:
                self._game_hex_clicked(d["row"], d["col"])
            finally:
                self._bot_acting = False
        elif t == "BuyFerry":
            gs = self._game_state
            if gs:
                self._bot_acting = True
                try:
                    self._game_ferry_clicked(d["ferry_idx"])
                finally:
                    self._bot_acting = False
        elif t == "EndTurn":
            self._game_end_turn()
        elif t == "DeclareEndBuild":
            self._game_declare_end_build()
        elif t == "RollStart":
            self._bot_acting = True
            try:
                self._game_roll_start()
            finally:
                self._bot_acting = False
        elif t == "RollDest":
            self._bot_acting = True
            try:
                self._game_roll_dest()
            finally:
                self._bot_acting = False
        elif t == "JoinJourney":
            self._game_join(d.get("join", False))
        elif t == "SelectRoute":
            self._game_select_route(d.get("option_idx", 0))
        elif t == "CooperateWith":
            self._game_cooperate_with(d.get("partner_idx", 0))
        elif t == "Advance":
            self._game_advance()
        elif t == "NextJourney":
            self._game_next_journey()
        elif t == "ProposeAlliance":
            self._game_propose_alliance(d.get("target_idx", 0))
        elif t == "RespondAlliance":
            self._game_respond_alliance(d.get("accept", False))
        elif t == "SelectCustomRoute":
            raw = d.get("route", [])
            route = [tuple(rc) for rc in raw]
            gs2 = self._game_state
            if gs2:
                self._game_apply_custom_route(gs2, route)

    def _net_broadcast_state(self) -> None:
        """Host: serialize and broadcast the current game state."""
        gs = self._game_state
        if gs is None or self._net_bridge is None or self._net_role != "host":
            return
        from ..net.serializer import serialize_state
        self._net_bridge.broadcast_state(serialize_state(gs))

    def _net_send_action(self, action_dict: dict) -> None:
        """Client: send an action to the host and do NOT apply locally."""
        if self._net_bridge:
            self._net_bridge.send_action(action_dict)

    def _maybe_show_turn_toast(self, gs) -> None:
        idx = gs.player_idx
        if idx == self._last_toast_player_idx:
            return
        self._last_toast_player_idx = idx
        player = gs.players[idx]
        is_mine = (idx == self._net_slot)
        self._turn_toast.show_for(player.name, player.color_hex, is_mine)

    def _maybe_play_turn_sound(self, gs) -> None:
        idx = gs.player_idx
        # Determine whether the local human should hear a sound for this turn
        if self._net_role == "local":
            should_play = idx not in self._ai_players
        else:
            should_play = idx == self._net_slot
        # Always advance the tracker so non-playing turns don't re-trigger
        if not should_play:
            self._last_sound_player_idx = idx
            return
        if idx == self._last_sound_player_idx:
            return
        if self._turn_sound is not None:
            self._turn_sound.play()
        self._last_sound_player_idx = idx

    def _on_game_setup_start(self) -> None:
        setup = self._game_setup
        map_path = setup.map_path()
        if map_path is None:
            return
        try:
            from ..core.map_file import load_map
            grid = load_map(str(map_path))
        except Exception as exc:
            QMessageBox.critical(self, "Fehler beim Laden der Karte", str(exc))
            return
        self._apply_grid(grid, grid.region_name)
        self._save_path = map_path
        self._start_game(
            grid,
            setup.player_configs(),
            setup.starting_capital(),
            setup.win_target(),
            setup.game_options(),
        )

    def _start_game(self, grid, player_configs: list, capital: int, win_target: int,
                    options: dict | None = None) -> None:
        players = [
            PlayerState(
                name=pc["name"],
                color_hex=pc["color"],
                money=capital,
                is_bot=pc.get("is_bot", False),
            )
            for pc in player_configs
        ]
        self._game_state = GameState(players=players, grid=grid, win_target=win_target)
        if options:
            self._game_state.shared_roll = bool(options.get("shared_roll", False))
        self._game_state.build_money          = {}
        self._game_state.score_history        = []
        self._game_state.score_history_labels = []
        # Build an AIPlayer for every bot slot
        self._ai_players: dict[int, AIPlayer] = {
            i: AIPlayer(player_idx=i, profile=_make_ai_profile(self._ai_difficulty))
            for i, p in enumerate(players)
            if p.is_bot
        }
        self._last_toast_player_idx = -1
        self._last_sound_player_idx = -1
        self._build_input_blocked   = False
        self._custom_route_mode = False
        self._custom_route = []
        self._custom_route_pidx = -1
        self._set_editor_visible(False)
        self._map.set_game_mode("build")
        self._map.set_player_tracks([(p.color_hex, p.track_edges) for p in players])
        self._game_panel.show()
        self._map.fit_to_view()
        self._music.play_phase("build")
        self._game_refresh_ui()
        self.statusBar().showMessage("Aufbauphase — würfeln und Gleise bauen!")

    def _on_route_hover(self, route: list) -> None:
        gs = self._game_state
        if gs is None or not route:
            self._map.set_route_hover_overlay([])
            return
        j = gs.journey
        if j is not None and j.route_select_idx < len(j.participating):
            color = gs.players[j.participating[j.route_select_idx]].color_hex
        else:
            color = "#FFFFFF"
        start_rc = (j.start_city["row"], j.start_city["col"]) if j else None
        end_rc   = (j.dest_city["row"],  j.dest_city["col"])  if (j and j.dest_city) else None
        self._map.set_route_hover_overlay(route, color, start_rc, end_rc)

    def _game_refresh_ui(self) -> None:
        gs = self._game_state
        if gs is None:
            return
        # Schedule an AI turn if the current player is a bot.
        # Use singleShot(0) so the UI repaints before the AI acts.
        if (gs.winner is None
                and gs.player_idx in self._ai_players):
            QTimer.singleShot(self._bot_delay_ms, self._run_ai_step)
        is_bot_turn   = gs.player_idx in self._ai_players
        is_local_turn = (not is_bot_turn
                         and (self._net_role == "local"
                              or gs.player_idx == self._net_slot))
        if gs.phase == "build":
            self._game_panel.refresh_build(gs)
            self._game_panel.set_actions_visible(is_local_turn)
            if not is_bot_turn and gs.build_rolled and gs.build_last is not None:
                self._map.set_game_reachable(self._compute_reachable(gs))
            else:
                self._map.set_game_reachable(set())
            self._map.set_build_endpoint(None if is_bot_turn else gs.build_last)
            self._map.set_journey_highlight(None, None)
        elif gs.phase == "operate":
            # Sync custom-route drawing state to panel before refresh
            if self._custom_route_mode and gs.journey is not None:
                dest_rc = (gs.journey.dest_city["row"], gs.journey.dest_city["col"])
                dest_reached = bool(self._custom_route) and self._custom_route[-1] == dest_rc
                self._game_panel.set_custom_route_mode(
                    drawing=True,
                    route_len=len(self._custom_route),
                    dest_reached=dest_reached,
                )
            else:
                self._game_panel.set_custom_route_mode(False)
            self._game_panel.refresh_operate(gs)
            self._game_panel.set_actions_visible(is_local_turn)
            # Show reachable next steps during custom route drawing
            if self._custom_route_mode:
                self._map.set_game_reachable(
                    self._custom_route_reachable(gs)
                )
                preview_color = gs.players[self._custom_route_pidx].color_hex \
                    if self._custom_route_pidx >= 0 else "#FFFFFF"
                if len(self._custom_route) > 1:
                    self._map.set_route_previews(
                        [(self._custom_route, preview_color, 220)]
                    )
                else:
                    self._map.set_route_previews([])
            else:
                self._map.set_game_reachable(set())
            self._map.set_build_endpoint(None)
            trains = []
            j = gs.journey
            if j:
                for pidx in j.participating:
                    p = gs.players[pidx]
                    route = j.routes.get(pidx, [])
                    pos = j.positions.get(pidx, 0)
                    if route and pos < len(route):
                        trains.append((p.color_hex, route[pos], p.name))
                sc = j.start_city
                dc = j.dest_city
                start_rc = (sc["row"], sc["col"]) if sc else None
                dest_rc  = (dc["row"], dc["col"]) if dc else None
                self._map.set_journey_highlight(start_rc, dest_rc)
            else:
                self._map.set_journey_highlight(None, None)
            self._map.set_train_positions(trains)
        # Separate confirmed vs pending edges for dotted rendering
        pending_set   = {entry["edge"] for entry in gs.pending_log}
        pending_costs = {entry["edge"]: entry["cost"] for entry in gs.pending_log}
        tracks = []
        for i, p in enumerate(gs.players):
            confirmed = p.track_edges - pending_set if i == gs.player_idx else p.track_edges
            tracks.append((p.color_hex, confirmed))
        self._map.set_player_tracks(tracks)
        self._map.set_pending_edges(gs.current_player.color_hex, pending_set, pending_costs)
        # Ferry ownership display
        ferry_owners = {}
        for fidx, ferry in enumerate(getattr(gs.grid, "ferries", [])):
            owner_i = game_rules.ferry_owner_idx(gs, fidx)
            ferry_owners[fidx] = gs.players[owner_i].color_hex if owner_i is not None else None
        self._map.set_ferry_owners(ferry_owners)
        self._map.update()
        # Turn announcement (multiplayer only)
        if self._net_role != "local" and gs.winner is None:
            self._maybe_show_turn_toast(gs)
        # Turn notification sound
        if gs.winner is None:
            self._maybe_play_turn_sound(gs)
        # Broadcast updated state to all clients after every UI refresh (host only)
        if self._net_role == "host" and not self._bot_acting:
            self._net_broadcast_state()

    def _compute_reachable(self, gs) -> set:
        if gs.build_last is None:
            return set()
        grid = gs.grid
        pts_left = gs.build_pts_remaining
        visited = {gs.build_last: 0}
        frontier = [gs.build_last]
        while frontier:
            next_f = []
            for rc in frontier:
                r, c = rc
                for nr, nc in game_rules.neighbors_of(r, c):
                    if not (0 <= nr < grid.rows and 0 <= nc < grid.cols):
                        continue
                    if not grid.is_land(nr, nc):
                        continue
                    cost = game_rules.build_cost(grid, r, c, nr, nc)
                    total = visited[rc] + cost
                    if total > pts_left:
                        continue
                    if (nr, nc) not in visited or visited[(nr, nc)] > total:
                        visited[(nr, nc)] = total
                        next_f.append((nr, nc))
            frontier = next_f
        return set(visited.keys()) - {gs.build_last}

    def _game_hex_clicked(self, row: int, col: int) -> None:
        gs = self._game_state
        if gs is None:
            return
        # Ignore clicks during the post-turn lock window (prevents accidental
        # carry-over clicks from the previous player landing on the map).
        if self._build_input_blocked and not self._bot_acting:
            return
        if self._custom_route_mode:
            self._custom_route_extend(gs, row, col)
            return
        if gs.phase != "build" or not gs.build_rolled:
            return
        if not self._bot_acting and gs.player_idx in self._ai_players:
            return
        if (self._net_role == "client" and gs.player_idx == self._net_slot
                and not self._bot_acting):
            self._net_send_action({"type": "PlaceEdge", "row": row, "col": col})
            return
        grid = gs.grid
        cp = gs.current_player

        if not grid.is_land(row, col):
            return

        ferry_eps = game_rules.owned_ferry_accessible_endpoints(
            gs, gs.player_idx
        )

        if gs.build_last is None:
            # Must start from own existing network (or an accessible ferry endpoint)
            if not cp.has_node(row, col) and (row, col) not in ferry_eps:
                return
            gs.build_last = (row, col)
            self._game_refresh_ui()
            return

        r1, c1 = gs.build_last
        r2, c2 = row, col

        if not game_rules.are_adjacent(r1, c1, r2, c2):
            # Allow re-selecting a different start point within the player's own network
            if cp.has_node(row, col) or (row, col) in ferry_eps:
                gs.build_last = (row, col)
                self._game_refresh_ui()
            return

        if cp.has_edge(r1, c1, r2, c2):
            return

        cost = game_rules.build_cost(grid, r1, c1, r2, c2)
        if cost > gs.build_pts_remaining:
            return

        fees = game_rules.crossing_fees(gs, gs.player_idx, r1, c1, r2, c2)
        if cp.money < sum(fees.values()):
            return

        # Build pending log entry BEFORE committing changes
        log_entry = {
            "edge": frozenset(((r1, c1), (r2, c2))),
            "cost": cost,
            "fees": dict(fees),
            "bonuses": [],
            "cities_connected_was": gs.cities_connected_since,
            "build_last_was": gs.build_last,
        }

        cp.add_edge(r1, c1, r2, c2)
        gs.build_pts_used += cost
        for pidx, amt in fees.items():
            gs.players[pidx].money += amt
            cp.money -= amt
            gs.build_fees_accum[pidx] = gs.build_fees_accum.get(pidx, 0) + amt
        gs.build_last = (r2, c2)

        for r_c, c_c in [(r1, c1), (r2, c2)]:
            city_obj = game_rules.city_at_hex(grid, r_c, c_c)
            if city_obj and city_obj["number"] not in cp.connected_cities:
                bonus = game_rules.city_bonus(gs, gs.player_idx, city_obj)
                cp.money += bonus
                cp.connected_cities.add(city_obj["number"])
                log_entry["bonuses"].append((city_obj["number"], bonus))

        if game_rules.check_all_cities_connected(gs) and gs.cities_connected_since is None:
            gs.cities_connected_since = gs.round_number

        gs.pending_log.append(log_entry)
        self._sfx.play("buildsound")
        self._game_refresh_ui()

    # ------------------------------------------------------------------ #
    # Dice animation helper                                               #
    # ------------------------------------------------------------------ #

    def _show_dice_roll(self, d1: int, d2: int, label: str = "",
                        city_mode: bool = False) -> None:
        """Show the animated dice dialog settling on (d1, d2)."""
        from .dialogs import DiceRollDialog
        from PyQt6.QtGui import QColor
        bg1 = QColor(0xFF, 0xEB, 0xEB) if city_mode else None
        dlg = DiceRollDialog(d1, d2, label=label, die1_bg=bg1, parent=self)
        dlg.exec()

    # ------------------------------------------------------------------ #

    def _game_roll_build(self) -> None:
        gs = self._game_state
        if gs is None:
            return
        if gs.player_idx in self._ai_players:
            return
        if self._net_role == "client" and gs.player_idx == self._net_slot:
            self._net_send_action({"type": "RollBuild"})
            return
        d1, d2 = game_rules.roll_two()
        self._sfx.play("diceroll")
        pts = d1 + d2
        gs.last_roll = (d1, d2)
        gs.build_pts_total = pts
        gs.build_pts_used  = 0
        gs.build_rolled    = True
        gs.build_fees_accum.clear()
        if gs.shared_roll and gs.round_number > 1:
            gs.shared_roll_total = pts

        cp = gs.current_player
        # Round 1: the same dice roll also determines the starting city
        if gs.round_number == 1 and not cp.track_nodes:
            number = d1 * 10 + d2
            city = game_rules.city_by_number(gs.grid, number)
            if city is None and gs.grid.cities:
                city = min(gs.grid.cities,
                           key=lambda c: abs(c["number"] - number))
            if city:
                gs.build_last = (city["row"], city["col"])
                self.statusBar().showMessage(
                    f"{cp.name} startet in {city['name']} "
                    f"(Stadt {d1}×10+{d2}={city['number']}) — "
                    f"{pts} Baupunkte"
                )
            else:
                gs.build_last = None
                self.statusBar().showMessage(
                    f"{cp.name} würfelt: {d1}+{d2} = {pts} Punkte"
                )
        else:
            gs.build_last = None
            self.statusBar().showMessage(
                f"{cp.name} würfelt: {d1}+{d2} = {pts} Punkte"
            )
        if self._net_role == "host":
            self._net_broadcast_state()
        self._show_dice_roll(d1, d2, "Baupunkte würfeln")
        self._game_refresh_ui()

    def _game_end_turn(self) -> None:
        gs = self._game_state
        if gs is None:
            return
        if self._net_role == "client" and gs.player_idx == self._net_slot:
            self._net_send_action({"type": "EndTurn"})
            return
        gs.pending_log.clear()   # commit all pending edges permanently
        prev_round = gs.round_number
        gs.advance_player()
        # Snapshot after every complete build round so the chart shows the full game.
        if gs.phase == "build" and gs.round_number > prev_round:
            gs.score_history.append({i: p.money for i, p in enumerate(gs.players)})
            gs.score_history_labels.append(f"B{prev_round}")
        gs.build_rolled    = False
        gs.build_pts_total = 0
        gs.build_pts_used  = 0
        gs.build_last      = None
        gs.build_fees_accum.clear()
        # Lock hex-map input briefly so the previous player's cursor position
        # cannot accidentally trigger the first build click of the new turn.
        self._build_input_blocked = True
        QTimer.singleShot(350, lambda: setattr(self, "_build_input_blocked", False))
        # If shared-roll is active and the roller already set a value this round,
        # pre-apply it so the next player's turn starts without a separate roll.
        if gs.shared_roll and gs.shared_roll_total > 0:
            gs.build_pts_total = gs.shared_roll_total
            gs.build_rolled    = True
        cp = gs.current_player
        if gs.shared_roll and gs.shared_roll_total > 0:
            roller = gs.players[gs.round_start_player]
            self.statusBar().showMessage(
                f"{cp.name} ist dran — {roller.name}s Würfelwurf: "
                f"{gs.shared_roll_total} Punkte"
            )
        else:
            self.statusBar().showMessage(f"{cp.name} ist dran.")
        self._game_refresh_ui()

    def _game_undo_one(self, gs) -> None:
        """Reverse the last pending log entry without refreshing the UI."""
        entry = gs.pending_log.pop()
        cp = gs.current_player
        cp.track_edges.discard(entry["edge"])
        cp.track_nodes = {n for e in cp.track_edges for n in e}
        gs.build_pts_used -= entry["cost"]
        for pidx, amt in entry["fees"].items():
            gs.players[pidx].money -= amt
            cp.money += amt
            gs.build_fees_accum[pidx] = max(0, gs.build_fees_accum.get(pidx, 0) - amt)
        for city_num, bonus in entry["bonuses"]:
            cp.connected_cities.discard(city_num)
            cp.money -= bonus
        gs.cities_connected_since = entry["cities_connected_was"]
        gs.build_last = entry["build_last_was"]

    def _game_undo_last(self) -> None:
        gs = self._game_state
        if gs is None or not gs.pending_log:
            return
        if self._net_role == "client":
            return   # undo not supported in network mode (state comes from host)
        self._game_undo_one(gs)
        self._game_refresh_ui()

    def _game_delete_plan(self) -> None:
        gs = self._game_state
        if gs is None or not gs.pending_log:
            return
        while gs.pending_log:
            self._game_undo_one(gs)
        self._game_refresh_ui()

    def _game_ferry_clicked(self, fidx: int) -> None:
        gs = self._game_state
        if gs is None or gs.phase != "build" or not gs.build_rolled:
            return
        if gs.player_idx in self._ai_players:
            return
        if self._net_role == "client" and gs.player_idx == self._net_slot:
            self._net_send_action({"type": "BuyFerry", "ferry_idx": fidx})
            return
        grid = gs.grid
        cp   = gs.current_player
        ferries = getattr(grid, "ferries", [])
        if fidx >= len(ferries):
            return
        if game_rules.ferry_owner_idx(gs, fidx) is not None:
            return   # already built by someone
        max_f = getattr(gs.grid, "max_ferries_per_player", 1)
        if len(cp.owned_ferries) >= max_f:
            QMessageBox.information(self, "Fähre",
                                    "Du hast bereits dein Fährlimit erreicht.")
            return
        if cp.money < 6:
            QMessageBox.information(self, "Fähre",
                                    "Nicht genug Kredite (6 benötigt).")
            return
        ep = game_rules.ferry_endpoints(ferries[fidx])
        if ep is None:
            return
        at_ep = (cp.has_node(*ep[0]) or cp.has_node(*ep[1])
                 or gs.build_last == ep[0] or gs.build_last == ep[1])
        if not at_ep:
            QMessageBox.information(self, "Fähre",
                                    "Dein Netz muss einen Endpunkt der Fähre erreichen.")
            return
        ans = QMessageBox.question(
            self,
            "Fähre bauen?",
            "Fährlinie für 6 Kredite erwerben?\n"
            "Andere Spieler zahlen 3 Kredite Gebühr bei Nutzung.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            cp.money -= 6
            cp.owned_ferries.append(fidx)
            if not cp.track_nodes and gs.build_last is not None:
                cp.track_nodes.add(gs.build_last)
            self._game_refresh_ui()

    def _game_declare_end_build(self) -> None:
        gs = self._game_state
        if gs is None:
            return
        if self._net_role == "client" and gs.player_idx == self._net_slot:
            self._net_send_action({"type": "DeclareEndBuild"})
            return
        gs.pending_log.clear()   # commit any pending tracks so they render as confirmed
        gs.phase = "operate"
        gs.operate_sub = "roll_start"
        gs.player_idx  = 0
        # Snapshot money at build→operate transition to split build/race scores
        gs.build_money = {i: p.money for i, p in enumerate(gs.players)}
        self._map.set_game_mode("operate")
        self.statusBar().showMessage("Betriebsphase beginnt!")
        self._music.play_phase("race")
        self._game_refresh_ui()

    def _game_roll_start(self) -> None:
        gs = self._game_state
        if gs is None:
            return
        if not self._bot_acting and gs.player_idx in self._ai_players:
            return
        if (self._net_role == "client" and gs.player_idx == self._net_slot
                and not self._bot_acting):
            self._net_send_action({"type": "RollStart"})
            return
        (r, w), city = game_rules.roll_city(gs.grid)
        self._sfx.play("diceroll")
        gs.last_roll = (r, w)
        from ..game.state import JourneyState
        gs.journey = JourneyState(start_city=city)
        gs.operate_sub = "roll_dest"
        self.statusBar().showMessage(
            f"Start: {city['name']} ({city['number']})  —  {r} × 10 + {w}"
        )
        if self._net_role == "host":
            self._net_broadcast_state()
        self._show_dice_roll(r, w, "Startbahnhof würfeln", city_mode=True)
        self._game_refresh_ui()

    def _game_roll_dest(self) -> None:
        gs = self._game_state
        if gs is None or gs.journey is None:
            return
        if not self._bot_acting and gs.player_idx in self._ai_players:
            return
        if (self._net_role == "client" and gs.player_idx == self._net_slot
                and not self._bot_acting):
            self._net_send_action({"type": "RollDest"})
            return
        for _ in range(20):
            (r, w), city = game_rules.roll_city(gs.grid)
            if city != gs.journey.start_city:
                break
        self._sfx.play("diceroll")
        gs.last_roll = (r, w)
        gs.journey.dest_city = city
        gs.operate_sub = "participate"
        gs.player_idx  = 0
        self.statusBar().showMessage(
            f"Ziel: {city['name']} ({city['number']})  —  {r} × 10 + {w}"
        )
        if self._net_role == "host":
            self._net_broadcast_state()
        self._show_dice_roll(r, w, "Ziel würfeln", city_mode=True)
        self._game_refresh_ui()

    def _game_join(self, join: bool) -> None:
        gs = self._game_state
        if gs is None or gs.journey is None:
            return
        if self._net_role == "client" and gs.player_idx == self._net_slot:
            self._net_send_action({"type": "JoinJourney", "join": join})
            return
        j = gs.journey
        j.decided.add(gs.player_idx)
        if join:
            j.participating.append(gs.player_idx)
        self._advance_participate(gs)

    def _advance_participate(self, gs) -> None:
        """Find the next undecided player or finish the participate phase."""
        j = gs.journey
        n = len(gs.players)
        if len(j.decided) >= n:
            self._finish_participate(gs)
            return
        # Scan forward for the next undecided player
        for offset in range(1, n + 1):
            nxt = (gs.player_idx + offset) % n
            if nxt not in j.decided:
                gs.player_idx = nxt
                break
        self._game_refresh_ui()

    def _finish_participate(self, gs) -> None:
        j = gs.journey
        if not j.participating:
            gs.operate_sub = "post_journey"
        else:
            sc = (j.start_city["row"], j.start_city["col"])
            dc = (j.dest_city["row"],  j.dest_city["col"])
            for pidx in j.participating:
                j.route_options[pidx] = game_rules.route_options_for(
                    gs, pidx, sc, dc
                )
            j.route_select_idx = 0
            gs.player_idx = j.participating[0]
            gs.operate_sub = "route_select"
        self._game_refresh_ui()

    def _game_propose_alliance(self, target_idx: int) -> None:
        gs = self._game_state
        if gs is None or gs.journey is None or gs.operate_sub != "participate":
            return
        j = gs.journey
        if j.pending_alliance_from is not None:
            return
        if self._net_role == "client" and gs.player_idx == self._net_slot:
            self._net_send_action({"type": "ProposeAlliance", "target_idx": target_idx})
            return
        j.pending_alliance_from = gs.player_idx
        j.pending_alliance_to   = target_idx
        gs.player_idx = target_idx
        self._game_refresh_ui()

    def _game_respond_alliance(self, accept: bool) -> None:
        gs = self._game_state
        if gs is None or gs.journey is None or gs.operate_sub != "participate":
            return
        j = gs.journey
        if j.pending_alliance_from is None:
            return
        if self._net_role == "client" and gs.player_idx == self._net_slot:
            self._net_send_action({"type": "RespondAlliance", "accept": accept})
            return
        proposer = j.pending_alliance_from
        target   = j.pending_alliance_to
        j.pending_alliance_from = None
        j.pending_alliance_to   = None
        if accept:
            j.alliances.append(frozenset({proposer, target}))
            j.decided.add(proposer)
            j.decided.add(target)
            j.participating.append(proposer)
            j.participating.append(target)
            self._advance_participate(gs)
        else:
            j.declined_proposals.add((proposer, target))
            j.decided.add(target)
            gs.player_idx = proposer   # back to proposer for join/skip
            self._game_refresh_ui()

    # ── Custom route drawing ─────────────────────────────────────────── #

    def _custom_route_reachable(self, gs) -> set:
        """Track-adjacent hexes from the end of the current partial route."""
        if not self._custom_route:
            return set()
        last_rc = self._custom_route[-1]
        adj: set = set()
        for p in gs.players:
            for edge in p.track_edges:
                pts = list(edge)
                if pts[0] == last_rc:
                    adj.add(pts[1])
                elif pts[1] == last_rc:
                    adj.add(pts[0])
        for fidx, ferry in enumerate(getattr(gs.grid, "ferries", [])):
            if game_rules.ferry_owner_idx(gs, fidx) is not None:
                ep = game_rules.ferry_endpoints(ferry)
                if ep:
                    if ep[0] == last_rc:
                        adj.add(ep[1])
                    elif ep[1] == last_rc:
                        adj.add(ep[0])
        route_set = set(self._custom_route)
        # Allow revisiting only the first hex (so the dest can be the start)
        return adj - (route_set - {self._custom_route[0]})

    def _custom_route_extend(self, gs, row: int, col: int) -> None:
        """Extend or truncate the custom route based on a hex click."""
        rc = (row, col)
        if not self._custom_route:
            return
        # Clicking an existing hex: truncate back to it
        if rc in self._custom_route:
            idx = self._custom_route.index(rc)
            self._custom_route = self._custom_route[:idx + 1]
            self._game_refresh_ui()
            return
        # Clicking a reachable new hex: extend
        reachable = self._custom_route_reachable(gs)
        if rc in reachable:
            self._custom_route.append(rc)
            self._game_refresh_ui()

    def _on_draw_custom_route(self) -> None:
        gs = self._game_state
        if gs is None or gs.journey is None or gs.operate_sub != "route_select":
            return
        j = gs.journey
        if j.route_select_idx >= len(j.participating):
            return
        pidx = j.participating[j.route_select_idx]
        sc = (j.start_city["row"], j.start_city["col"])
        self._custom_route_mode = True
        self._custom_route      = [sc]
        self._custom_route_pidx = pidx
        self._game_refresh_ui()

    def _on_confirm_custom_route(self) -> None:
        gs = self._game_state
        if gs is None or gs.journey is None or gs.operate_sub != "route_select":
            return
        if not self._custom_route:
            return
        route = list(self._custom_route)
        self._custom_route_mode = False
        self._custom_route = []
        self._map.set_route_previews([])
        self._map.set_route_hover_overlay([])
        self._map.set_game_reachable(set())
        if self._net_role == "client":
            j = gs.journey
            if (j.route_select_idx < len(j.participating)
                    and j.participating[j.route_select_idx] == self._net_slot):
                self._net_send_action({
                    "type": "SelectCustomRoute",
                    "route": [list(rc) for rc in route],
                })
            return
        self._game_apply_custom_route(gs, route)

    def _on_cancel_custom_route(self) -> None:
        self._custom_route_mode = False
        self._custom_route = []
        self._custom_route_pidx = -1
        self._map.set_route_previews([])
        self._map.set_game_reachable(set())
        self._game_refresh_ui()

    def _game_apply_custom_route(self, gs, route: list) -> None:
        """Insert a custom-drawn route as an option and select it."""
        j = gs.journey
        if j.route_select_idx >= len(j.participating):
            return
        pidx = j.participating[j.route_select_idx]
        opts = j.route_options.setdefault(pidx, [])
        # Avoid duplicate entries
        if route not in opts:
            opts.append(route)
        option_idx = opts.index(route)
        j.routes[pidx]    = route
        j.positions[pidx] = 0
        j.route_select_idx += 1
        self._custom_route_pidx = -1
        self._map.set_route_previews([])
        self._advance_route_select(gs)

    # ────────────────────────────────────────────────────────────────── #

    def _game_select_route(self, option_idx: int) -> None:
        gs = self._game_state
        if gs is None or gs.journey is None or gs.operate_sub != "route_select":
            return
        j = gs.journey
        if (self._net_role == "client"
                and j.route_select_idx < len(j.participating)
                and j.participating[j.route_select_idx] == self._net_slot):
            self._net_send_action({"type": "SelectRoute", "option_idx": option_idx})
            return
        if j.route_select_idx >= len(j.participating):
            return
        pidx = j.participating[j.route_select_idx]
        opts = j.route_options.get(pidx, [])
        if not opts:
            return
        option_idx = max(0, min(option_idx, len(opts) - 1))
        j.routes[pidx]    = opts[option_idx]
        j.positions[pidx] = 0
        j.route_select_idx += 1
        self._map.set_route_previews([])
        self._map.set_route_hover_overlay([])
        self._advance_route_select(gs)

    def _game_cooperate_with(self, partner_idx: int) -> None:
        gs = self._game_state
        if gs is None or gs.journey is None or gs.operate_sub != "route_select":
            return
        j = gs.journey
        if (self._net_role == "client"
                and j.route_select_idx < len(j.participating)
                and j.participating[j.route_select_idx] == self._net_slot):
            self._net_send_action({"type": "CooperateWith", "partner_idx": partner_idx})
            return
        if j.route_select_idx >= len(j.participating):
            return
        pidx = j.participating[j.route_select_idx]
        if partner_idx not in j.routes:
            return   # partner hasn't selected yet
        j.cooperations[pidx] = partner_idx
        j.routes[pidx]       = list(j.routes[partner_idx])
        j.positions[pidx]    = 0
        j.route_select_idx += 1
        self._map.set_route_previews([])
        self._map.set_route_hover_overlay([])
        self._advance_route_select(gs)

    def _advance_route_select(self, gs) -> None:
        """Move to next player's route selection, or start travel when all done."""
        j = gs.journey
        if j.route_select_idx >= len(j.participating):
            gs.operate_sub = "travel"
            gs.player_idx  = j.participating[0]
            self._game_refresh_ui()
            return

        pidx = j.participating[j.route_select_idx]
        gs.player_idx = pidx

        # Allied players always travel together: if this player's alliance
        # partner already has a route, auto-apply cooperation.
        for pair in j.alliances:
            if pidx in pair:
                partner = next(p for p in pair if p != pidx)
                if partner in j.routes:
                    j.cooperations[pidx] = partner
                    j.routes[pidx]       = list(j.routes[partner])
                    j.positions[pidx]    = 0
                    j.route_select_idx  += 1
                    self._advance_route_select(gs)
                    return

        self._game_refresh_ui()

    def _game_advance(self) -> None:
        """Roll dice and advance only the current player's train."""
        gs = self._game_state
        if gs is None or gs.journey is None or self._advance_timer is not None:
            return
        if self._net_role == "client":
            self._net_send_action({"type": "Advance"})
            return
        j = gs.journey
        pidx = gs.player_idx
        if pidx in j.arrived_order:
            self._advance_next_traveler(gs)
            return
        d1, d2 = game_rules.roll_two()
        gs.last_roll = (d1, d2)
        dice = d1 + d2
        player_name = gs.players[pidx].name
        self.statusBar().showMessage(f"{player_name} fährt: {d1} + {d2} = {dice}")
        if self._net_role == "host":
            self._net_broadcast_state()
        self._show_dice_roll(d1, d2, "Fahrt würfeln")
        route = j.routes.get(pidx, [])
        if not route:
            j.arrived_order.append(pidx)
            self._advance_next_traveler(gs)
            return
        pos = j.positions.get(pidx, 0)
        target = game_rules.advance_on_route(gs.grid, route, pos, dice,
                                             game_rules.built_ferry_edges(gs))
        self._start_advance_animation({pidx: target})

    def _start_advance_animation(self, targets: dict) -> None:
        """Animate train movement to target positions step by step."""
        self._advance_targets = targets
        # reduce_motion: skip frame-by-frame animation, jump directly to final
        import dampfross.ui.design_tokens as _dt
        if _dt.A_REDUCE_MOTION:
            gs = self._game_state
            if gs is not None and gs.journey is not None:
                j = gs.journey
                for pidx, tgt in targets.items():
                    j.positions[pidx] = tgt
                    route = j.routes.get(pidx, [])
                    if j.positions.get(pidx, 0) >= len(route) - 1:
                        if pidx not in j.arrived_order:
                            j.arrived_order.append(pidx)
                self._advance_targets = {}
                self._advance_next_traveler(gs)
            return
        self._advance_timer = QTimer(self)
        self._advance_timer.timeout.connect(self._advance_step)
        self._advance_timer.start(self._anim_speed_ms)

    def _advance_step(self) -> None:
        gs = self._game_state
        if gs is None or gs.journey is None:
            self._advance_timer.stop()
            self._advance_timer = None
            self._advance_targets = {}
            return
        j = gs.journey
        ferry_edges = game_rules.built_ferry_edges(gs)
        any_moving = False
        ferry_cross = None   # (pidx, ferry_idx, reverse) if a ferry is hit this step

        for pidx, target in self._advance_targets.items():
            cur = j.positions.get(pidx, 0)
            if cur >= target:
                continue
            route = j.routes.get(pidx, [])
            if cur + 1 < len(route):
                edge = frozenset((route[cur], route[cur + 1]))
                if edge in ferry_edges and ferry_cross is None:
                    fidx, reverse = self._ferry_idx_for_edge(edge, route[cur])
                    if fidx >= 0:
                        ferry_cross = (pidx, fidx, reverse)
                        continue   # don't increment yet — boat animation will do it
            j.positions[pidx] = cur + 1
            any_moving = True

        self._update_train_display()

        if ferry_cross:
            # Pause advance animation and play boat crossing
            self._advance_timer.stop()
            self._advance_timer = None
            pidx, fidx, reverse = ferry_cross
            self._start_ferry_crossing_anim(pidx, fidx, reverse, gs.players[pidx].color_hex)
            return

        if not any_moving:
            self._advance_timer.stop()
            self._advance_timer = None
            for pidx in list(self._advance_targets.keys()):
                route = j.routes.get(pidx, [])
                if j.positions.get(pidx, 0) >= len(route) - 1:
                    if pidx not in j.arrived_order:
                        j.arrived_order.append(pidx)
            self._advance_targets = {}
            self._advance_next_traveler(gs)

    def _advance_next_traveler(self, gs) -> None:
        """After one player's advance animation, move to the next participant."""
        j = gs.journey
        remaining = [p for p in j.participating if p not in j.arrived_order]
        if not remaining:
            # Everyone arrived — fall through to post_journey UI
            self._game_refresh_ui()
            return
        # Cycle to the next participant after the current one
        try:
            cur_pos = j.participating.index(gs.player_idx)
        except ValueError:
            cur_pos = -1
        n = len(j.participating)
        for offset in range(1, n + 1):
            candidate = j.participating[(cur_pos + offset) % n]
            if candidate not in j.arrived_order:
                gs.player_idx = candidate
                break
        self._game_refresh_ui()

    # ── ferry crossing animation ──────────────────────────────────────── #

    def _ferry_idx_for_edge(self, edge: frozenset, from_hex: tuple) -> tuple[int, bool]:
        """Return (ferry_idx, reverse) for the ferry whose endpoints match edge."""
        gs = self._game_state
        if gs is None:
            return -1, False
        for fidx, ferry in enumerate(getattr(gs.grid, "ferries", [])):
            ep = game_rules.ferry_endpoints(ferry)
            if ep and frozenset(ep) == edge:
                a, b = ep
                return fidx, (from_hex == b)
        return -1, False

    def _start_ferry_crossing_anim(
        self, pidx: int, ferry_idx: int, reverse: bool, color_hex: str
    ) -> None:
        self._sfx.play("shiphorn")
        self._boat_anim_pidx      = pidx
        self._boat_anim_ferry_idx = ferry_idx
        self._boat_anim_reverse   = reverse
        self._boat_anim_t         = 0.0
        import dampfross.ui.design_tokens as _dt
        if _dt.A_REDUCE_MOTION:
            # Skip boat animation — update position immediately and resume advance
            gs2 = self._game_state
            if gs2 and gs2.journey:
                gs2.journey.positions[pidx] = \
                    gs2.journey.positions.get(pidx, 0) + 1
            self._map.clear_boat_animation()
            self._update_train_display()
            self._advance_timer = QTimer(self)
            self._advance_timer.timeout.connect(self._advance_step)
            self._advance_timer.start(0)
            return
        start_t = 1.0 if reverse else 0.0
        self._map.set_boat_animation(ferry_idx, start_t, color_hex)
        self._update_train_display()
        self._boat_timer = QTimer(self)
        self._boat_timer.timeout.connect(self._boat_anim_tick)
        self._boat_timer.start(40)   # 40 ms ≈ 25 fps

    def _boat_anim_tick(self) -> None:
        self._boat_anim_t += 0.045   # ~22 frames → ~880 ms total
        if self._boat_anim_t >= 1.0:
            self._boat_timer.stop()
            self._boat_timer = None
            self._map.clear_boat_animation()

            gs = self._game_state
            if gs and gs.journey:
                pidx = self._boat_anim_pidx
                j = gs.journey
                j.positions[pidx] = j.positions.get(pidx, 0) + 1
                route  = j.routes.get(pidx, [])
                target = self._advance_targets.get(pidx,
                             j.positions.get(pidx, 0))
                if j.positions.get(pidx, 0) >= len(route) - 1:
                    if pidx not in j.arrived_order:
                        j.arrived_order.append(pidx)
                self._boat_anim_pidx = None
                self._update_train_display()

                if j.positions.get(pidx, 0) < target:
                    # Still more movement left — resume regular advance
                    self._advance_timer = QTimer(self)
                    self._advance_timer.timeout.connect(self._advance_step)
                    self._advance_timer.start(self._anim_speed_ms)
                else:
                    self._advance_targets = {}
                    self._advance_next_traveler(gs)
            return

        t = 1.0 - self._boat_anim_t if self._boat_anim_reverse else self._boat_anim_t
        gs = self._game_state
        color = (gs.players[self._boat_anim_pidx].color_hex
                 if gs and self._boat_anim_pidx is not None else "#888888")
        self._map.set_boat_animation(self._boat_anim_ferry_idx, t, color)

    def _update_train_display(self) -> None:
        """Lightweight map update for animation frames (no AI scheduling)."""
        gs = self._game_state
        j = gs.journey if gs else None
        if j is None:
            return
        trains = []
        for pidx in j.participating:
            if pidx == self._boat_anim_pidx and self._boat_timer is not None:
                continue   # this player is shown as a boat mid-ferry
            p = gs.players[pidx]
            route = j.routes.get(pidx, [])
            pos = j.positions.get(pidx, 0)
            if route and pos < len(route):
                trains.append((p.color_hex, route[pos], p.name))
        self._map.set_train_positions(trains)
        self._map.update()

    def _game_next_journey(self) -> None:
        gs = self._game_state
        if gs is None or gs.journey is None:
            return
        if self._net_role == "client":
            self._net_send_action({"type": "NextJourney"})
            return
        j = gs.journey

        for rank, pidx in enumerate(j.arrived_order, 1):
            prize = 20 if rank == 1 else (10 if rank == 2 else 0)
            gs.players[pidx].money += prize

        for pidx in j.participating:
            route = j.routes.get(pidx, [])
            for owner_idx, amt in game_rules.route_fees(gs, pidx, route).items():
                gs.players[pidx].money -= amt
                gs.players[owner_idx].money += amt

        # Record score snapshot after each journey
        gs.score_history.append({i: p.money for i, p in enumerate(gs.players)})
        gs.score_history_labels.append(f"J{gs.journey_number + 1}")

        winner = next((p for p in gs.players if p.money >= gs.win_target), None)
        if winner:
            gs.winner = winner
            gs.operate_sub = "winner"
            self._map.set_train_positions([])
            self._game_refresh_ui()
            QTimer.singleShot(600, self._show_results)
            return

        gs.journey_number += 1
        gs.journey     = None
        gs.operate_sub = "roll_start"
        gs.player_idx  = 0
        self._game_refresh_ui()

    # ------------------------------------------------------------------ #
    # AI integration                                                       #
    # ------------------------------------------------------------------ #

    def _run_ai_step(self) -> None:
        """Execute one action from the current bot player's decision."""
        gs = self._game_state
        if gs is None or gs.winner is not None:
            return
        self._bot_acting = True
        try:
            ai = self._ai_players.get(gs.player_idx)
            if ai is None:
                return
            actions = ai.decide(gs)
            for act in actions:
                self._apply_ai_action(act)
        finally:
            self._bot_acting = False
            # Broadcast state after bot step completes (host only)
            if self._net_role == "host":
                self._net_broadcast_state()

    def _apply_ai_action(self, action) -> None:
        """Translate an AI Action into the same state mutations the UI uses."""
        gs = self._game_state
        if gs is None or gs.winner is not None:
            return

        if isinstance(action, RollBuild):
            # Roll without the animated dialog
            d1, d2 = game_rules.roll_two()
            self._sfx.play("diceroll")
            gs.last_roll = (d1, d2)
            pts = d1 + d2
            gs.build_pts_total = pts
            gs.build_pts_used  = 0
            gs.build_rolled    = True
            gs.build_fees_accum.clear()
            if gs.shared_roll and gs.round_number > 1:
                gs.shared_roll_total = pts
            cp = gs.current_player
            if gs.round_number == 1 and not cp.track_nodes:
                number = d1 * 10 + d2
                city = game_rules.city_by_number(gs.grid, number)
                if city is None and gs.grid.cities:
                    city = min(gs.grid.cities,
                               key=lambda c: abs(c["number"] - number))
                if city:
                    gs.build_last = (city["row"], city["col"])
            self.statusBar().showMessage(
                f"[Bot] {cp.name} würfelt: {d1}+{d2} = {pts}"
            )
            self._game_refresh_ui()

        elif isinstance(action, SetBuildStart):
            gs.build_last = (action.row, action.col)
            self._game_refresh_ui()

        elif isinstance(action, PlaceEdge):
            log_len_before = len(gs.pending_log)
            self._game_hex_clicked(action.row, action.col)
            if len(gs.pending_log) == log_len_before:
                # PlaceEdge was a no-op (edge already exists or invalid move).
                # Reset the bot's plan so it doesn't keep retrying, then end turn.
                ai = self._ai_players.get(gs.player_idx)
                if ai is not None:
                    ai.reset_plan()
                self._game_end_turn()

        elif isinstance(action, BuyFerry):
            cp = gs.current_player
            ferries = getattr(gs.grid, "ferries", [])
            max_f = getattr(gs.grid, "max_ferries_per_player", 1)
            if action.ferry_idx < len(ferries):
                if game_rules.ferry_owner_idx(gs, action.ferry_idx) is None:
                    if len(cp.owned_ferries) < max_f:
                        ep = game_rules.ferry_endpoints(ferries[action.ferry_idx])
                        # build_last counts as "at" an endpoint for players that
                        # haven't built any track yet (e.g. round-1 island spawn).
                        at_ep = (ep is not None and (
                            cp.has_node(*ep[0]) or cp.has_node(*ep[1])
                            or gs.build_last == ep[0] or gs.build_last == ep[1]
                        ))
                        if at_ep and cp.money >= 6:
                            cp.money -= 6
                            cp.owned_ferries.append(action.ferry_idx)
                            # Seed track_nodes with the spawn point so that
                            # owned_ferry_accessible_endpoints works next turn.
                            if not cp.track_nodes and gs.build_last is not None:
                                cp.track_nodes.add(gs.build_last)
                            self.statusBar().showMessage(
                                f"[Bot] {cp.name} kauft Fähre {action.ferry_idx}"
                            )
                            self._game_refresh_ui()

        elif isinstance(action, EndTurn):
            self._game_end_turn()

        elif isinstance(action, DeclareEndBuild):
            self._game_declare_end_build()

        elif isinstance(action, RollStart):
            self._game_roll_start()

        elif isinstance(action, RollDest):
            self._game_roll_dest()

        elif isinstance(action, JoinJourney):
            self.statusBar().showMessage(
                f"[Bot] {gs.current_player.name}: "
                f"{'nimmt teil' if action.join else 'passt'}"
            )
            self._game_join(action.join)

        elif isinstance(action, SelectRoute):
            self.statusBar().showMessage(
                f"[Bot] {gs.players[gs.journey.participating[gs.journey.route_select_idx]].name}"
                f" wählt Route {action.option_idx}"
            )
            self._game_select_route(action.option_idx)

        elif isinstance(action, CooperateWith):
            partner = gs.players[action.partner_idx].name
            cur = gs.players[gs.journey.participating[gs.journey.route_select_idx]].name
            self.statusBar().showMessage(
                f"[Bot] {cur} kooperiert mit {partner}"
            )
            self._game_cooperate_with(action.partner_idx)

        elif isinstance(action, Advance):
            self._game_advance()

        elif isinstance(action, NextJourney):
            self._game_next_journey()

        elif isinstance(action, ProposeAlliance):
            target = gs.players[action.target_idx].name
            self.statusBar().showMessage(
                f"[Bot] {gs.current_player.name} schlägt Allianz mit {target} vor"
            )
            self._game_propose_alliance(action.target_idx)

        elif isinstance(action, RespondAlliance):
            gs2 = self._game_state
            if gs2 and gs2.journey and gs2.journey.pending_alliance_from is not None:
                proposer = gs2.players[gs2.journey.pending_alliance_from].name
                resp = "annehmen" if action.accept else "ablehnen"
                self.statusBar().showMessage(
                    f"[Bot] {gs2.current_player.name} Allianz mit {proposer}: {resp}"
                )
            self._game_respond_alliance(action.accept)
