"""
Shared test fixtures for Dampfross AI tests.

Provides small, deterministic game states that can be assembled without
loading any .dmpfmap file or touching PyQt.
"""
import numpy as np
import pytest

from dampfross.core.hex_grid import HexGrid
from dampfross.game.state import GameState, PlayerState, JourneyState
from dampfross.game.ai.profile import AIProfile


# ── Minimal grid factories ──────────────────────────────────────────── #

def make_grid(rows: int = 10, cols: int = 10) -> HexGrid:
    """All-land grid with no mountains and no rivers."""
    cells = np.ones((rows, cols), dtype=bool)
    grid = HexGrid(cells, region_name="test")
    grid.is_mountainous = np.zeros((rows, cols), dtype=bool)
    grid.river_segs = []
    return grid


def add_city(grid: HexGrid, row: int, col: int,
             name: str, number: int) -> dict:
    city = {"row": row, "col": col, "name": name, "number": number,
            "population": 0}
    grid.cities.append(city)
    return city


# ── Game-state factories ────────────────────────────────────────────── #

def make_two_player_state(grid: HexGrid, capital: int = 20) -> GameState:
    """Two human players, build phase, no track yet."""
    p0 = PlayerState("Alice", "#e23b3b", money=capital)
    p1 = PlayerState("Bob",   "#1f6fd9", money=capital)
    return GameState(players=[p0, p1], grid=grid, win_target=250)


def make_bot_state(grid: HexGrid, capital: int = 20) -> GameState:
    """One human + one bot, build phase."""
    p0 = PlayerState("Alice", "#e23b3b", money=capital)
    p1 = PlayerState("Bot",   "#1f6fd9", money=capital, is_bot=True)
    return GameState(players=[p0, p1], grid=grid, win_target=250)


# ── Fixtures ────────────────────────────────────────────────────────── #

@pytest.fixture
def small_grid():
    """10×10 all-land grid with two cities."""
    g = make_grid(10, 10)
    add_city(g, 1, 1, "Nord",  11)
    add_city(g, 8, 8, "Sued",  88)
    return g


@pytest.fixture
def corridor_grid():
    """
    10×10 grid with three cities in a rough horizontal corridor.
    Used for route-scoring tests.
    """
    g = make_grid(10, 10)
    add_city(g, 5, 0, "West",   51)
    add_city(g, 5, 5, "Mitte",  56)
    add_city(g, 5, 9, "Ost",    60)
    return g


@pytest.fixture
def default_profile():
    return AIProfile(seed=42)
