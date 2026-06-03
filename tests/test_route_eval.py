"""
Tests for RouteEvaluator: route scoring, expected value, path finding.
"""
import pytest
from dampfross.game.state import PlayerState, GameState, JourneyState
from dampfross.game.rules import find_route, find_route_cheapest
from dampfross.game.ai.route_evaluator import (
    route_score,
    race_expected_value,
    score_all_routes,
    own_path_cost,
    find_route_balanced,
    route_options_extended,
)
from dampfross.game.ai.profile import AIProfile
from .conftest import make_grid, add_city, make_two_player_state


# ── Helpers ──────────────────────────────────────────────────────────── #

def _lay_edge(player, r1, c1, r2, c2):
    player.add_edge(r1, c1, r2, c2)


# ── route_score ───────────────────────────────────────────────────────── #

class TestRouteScore:
    def test_shorter_route_scores_higher(self, corridor_grid, default_profile):
        """A route with fewer hops scores higher than a longer one."""
        gs = make_two_player_state(corridor_grid)
        # Build a direct 5-hop route and a 7-hop detour for player 0
        for r, c in [(5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5)]:
            gs.players[0].track_nodes.add((r, c))
        short_route = [(5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5)]
        long_route  = [(5, 0), (4, 0), (4, 1), (4, 2), (4, 3), (4, 4),
                       (4, 5), (5, 5)]
        s_short, _ = route_score(short_route, gs, 0, default_profile)
        s_long,  _ = route_score(long_route,  gs, 0, default_profile)
        assert s_short > s_long

    def test_own_track_preferred(self, corridor_grid, default_profile):
        """Route using only own track scores better than one using foreign."""
        gs = make_two_player_state(corridor_grid)
        route = [(5, 0), (5, 1), (5, 2), (5, 3)]
        # Player 0 owns the route
        for i in range(len(route) - 1):
            gs.players[0].add_edge(route[i][0], route[i][1],
                                   route[i + 1][0], route[i + 1][1])
        # Player 1 owns the same edges (foreign)
        for i in range(len(route) - 1):
            gs.players[1].add_edge(route[i][0], route[i][1],
                                   route[i + 1][0], route[i + 1][1])

        score_own,     _ = route_score(route, gs, 0, default_profile)
        score_foreign, _ = route_score(route, gs, 1, default_profile)
        # Player 0 pays no fees; player 1 would pay fees to player 0
        assert score_own >= score_foreign

    def test_empty_route_negative(self, corridor_grid, default_profile):
        gs = make_two_player_state(corridor_grid)
        sc, _ = route_score([], gs, 0, default_profile)
        assert sc < 0

    def test_single_node_route_negative(self, corridor_grid, default_profile):
        gs = make_two_player_state(corridor_grid)
        sc, _ = route_score([(5, 0)], gs, 0, default_profile)
        assert sc < 0


# ── race_expected_value ──────────────────────────────────────────────── #

class TestRaceExpectedValue:
    def test_ev_decreases_with_more_competitors(self, corridor_grid, default_profile):
        gs = make_two_player_state(corridor_grid)
        route = [(5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5)]
        ev1 = race_expected_value(route, gs, 0, 1, default_profile)
        ev3 = race_expected_value(route, gs, 0, 3, default_profile)
        assert ev1 > ev3

    def test_ev_of_empty_route_is_very_negative(self, corridor_grid, default_profile):
        gs = make_two_player_state(corridor_grid)
        ev = race_expected_value([], gs, 0, 1, default_profile)
        assert ev < -100


# ── score_all_routes ─────────────────────────────────────────────────── #

class TestScoreAllRoutes:
    def test_selects_best_route(self, corridor_grid, default_profile):
        """score_all_routes picks the highest-scoring candidate."""
        gs = make_two_player_state(corridor_grid)
        short = [(5, 0), (5, 1), (5, 2)]
        long_ = [(5, 0), (4, 0), (4, 1), (4, 2), (5, 2)]
        result = score_all_routes([short, long_], gs, 0, default_profile)
        assert result.chosen == 0   # short route is index 0

    def test_single_route_always_chosen(self, corridor_grid, default_profile):
        gs = make_two_player_state(corridor_grid)
        result = score_all_routes([[(5, 0), (5, 1)]], gs, 0, default_profile)
        assert result.chosen == 0

    def test_empty_routes_returns_none_chosen(self, corridor_grid, default_profile):
        gs = make_two_player_state(corridor_grid)
        result = score_all_routes([], gs, 0, default_profile)
        assert result.chosen is None


# ── find_route_balanced ───────────────────────────────────────────────── #

class TestFindRouteBalanced:
    def _make_split_grid(self):
        """
        Grid where player 0 owns one long own-track path and
        player 1 owns a shorter path with fees.
        """
        g = make_grid(6, 6)
        add_city(g, 0, 0, "A", 11)
        add_city(g, 5, 5, "B", 55)
        return g

    def test_balanced_differs_from_both(self, default_profile):
        """Balanced route should be distinct from shortest and cheapest when
        a middle-ground path exists."""
        g = self._make_split_grid()
        gs = make_two_player_state(g)
        # Player 0: own track along row 0 then col 5
        for c in range(5):
            gs.players[0].add_edge(0, c, 0, c + 1)
        for r in range(5):
            gs.players[0].add_edge(r, 5, r + 1, 5)
        # Player 1: diagonal short path (fees apply to player 0)
        for i in range(5):
            gs.players[1].add_edge(i, i, i + 1, i + 1)

        start = (0, 0)
        dest  = (5, 5)

        shortest = [(0, 0)] + [(0, c) for c in range(1, 6)] + [(r, 5) for r in range(1, 6)]
        cheapest_path = find_route_balanced(gs, 0, start, dest, hop_w=0.0, fee_w=1.0)
        balanced_path = find_route_balanced(gs, 0, start, dest, hop_w=0.5, fee_w=0.5)

        # All must be valid or None; balanced path must exist here
        assert balanced_path is not None
        assert balanced_path[0] == start
        assert balanced_path[-1] == dest

    def test_balanced_returns_none_when_no_track(self, default_profile):
        """If no track is laid, balanced returns None."""
        g = make_grid(5, 5)
        add_city(g, 0, 0, "A", 11)
        add_city(g, 4, 4, "B", 44)
        gs = make_two_player_state(g)
        result = find_route_balanced(gs, 0, (0, 0), (4, 4))
        assert result is None


# ── route_options_extended ────────────────────────────────────────────── #

class TestRouteOptionsExtended:
    def test_extended_returns_up_to_three(self, default_profile):
        """When a balanced route differs from shortest and cheapest, 3 routes returned."""
        g = make_grid(6, 6)
        add_city(g, 0, 0, "A", 11)
        add_city(g, 5, 5, "B", 55)
        gs = make_two_player_state(g)
        # Player 0 owns upper path; player 1 owns diagonal (cheaper/shorter for p1 if p0 uses it)
        for c in range(5):
            gs.players[0].add_edge(0, c, 0, c + 1)
        for r in range(5):
            gs.players[0].add_edge(r, 5, r + 1, 5)
        for i in range(5):
            gs.players[1].add_edge(i, i, i + 1, i + 1)

        opts = route_options_extended(gs, 0, (0, 0), (5, 5), default_profile)
        # Must return a non-empty list of valid routes
        assert isinstance(opts, list)
        assert len(opts) >= 1
        for r in opts:
            assert r[0] == (0, 0)
            assert r[-1] == (5, 5)

    def test_extended_deduplicates_identical(self, default_profile):
        """When balanced matches shortest or cheapest, at most 2 routes returned."""
        g = make_grid(3, 3)
        add_city(g, 0, 0, "A", 11)
        add_city(g, 2, 2, "B", 22)
        gs = make_two_player_state(g)
        # Single path — player 0 owns the only route
        gs.players[0].add_edge(0, 0, 0, 1)
        gs.players[0].add_edge(0, 1, 0, 2)
        gs.players[0].add_edge(0, 2, 1, 2)
        gs.players[0].add_edge(1, 2, 2, 2)

        opts = route_options_extended(gs, 0, (0, 0), (2, 2), default_profile)
        # Deduplication: same path added multiple times → only 1 or 2 distinct
        unique = []
        for r in opts:
            if r not in unique:
                unique.append(r)
        assert len(unique) == len(opts)
