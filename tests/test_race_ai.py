"""
Tests for RaceDecisionService: participate, route choice, end-build declaration.
"""
import pytest

from dampfross.game.state import PlayerState, GameState, JourneyState
from dampfross.game.ai.race_decision import (
    decide_participate,
    decide_route,
    should_declare_end_build,
    should_declare_end_build_early,
)
from dampfross.game.ai.profile import AIProfile
from .conftest import make_grid, add_city, make_two_player_state


def _journey(start_city, dest_city):
    return JourneyState(start_city=start_city, dest_city=dest_city)


# ── decide_participate ────────────────────────────────────────────────── #

class TestDecideParticipate:
    def test_no_journey_returns_false(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        gs.phase       = "operate"
        gs.operate_sub = "participate"
        # No journey set
        result = decide_participate(gs, 0, default_profile)
        assert result.chosen is False

    def test_participates_when_owns_all_track(self, default_profile):
        """If the player owns 100 % of the route, they should always join."""
        g = make_grid(5, 5)
        c1 = add_city(g, 2, 0, "Start", 20)
        c2 = add_city(g, 2, 4, "End",   24)
        gs = make_two_player_state(g)
        # Build a full route for player 0
        for col in range(4):
            gs.players[0].add_edge(2, col, 2, col + 1)
        gs.phase       = "operate"
        gs.operate_sub = "participate"
        gs.journey     = _journey(c1, c2)
        result = decide_participate(gs, 0, default_profile)
        assert result.chosen is True

    def test_skips_when_no_path_exists(self, default_profile):
        """With isolated players and no track at all, no route → skip."""
        g = make_grid(5, 5)
        c1 = add_city(g, 0, 0, "A", 11)
        c2 = add_city(g, 4, 4, "B", 44)
        gs = make_two_player_state(g)
        gs.phase       = "operate"
        gs.operate_sub = "participate"
        gs.journey     = _journey(c1, c2)
        # No track → find_route returns None → no route → skip
        result = decide_participate(gs, 0, default_profile)
        assert result.chosen is False

    def test_result_has_candidates(self, default_profile):
        g = make_grid(5, 5)
        c1 = add_city(g, 2, 0, "S", 20)
        c2 = add_city(g, 2, 4, "D", 24)
        gs = make_two_player_state(g)
        for col in range(4):
            gs.players[0].add_edge(2, col, 2, col + 1)
        gs.phase       = "operate"
        gs.operate_sub = "participate"
        gs.journey     = _journey(c1, c2)
        result = decide_participate(gs, 0, default_profile)
        assert isinstance(result.candidates, list)


# ── decide_route ─────────────────────────────────────────────────────── #

class TestDecideRoute:
    def _make_journey_with_routes(self, grid, gs, pidx):
        c1 = grid.cities[0]
        c2 = grid.cities[1] if len(grid.cities) > 1 else grid.cities[0]
        from dampfross.game.rules import route_options_for
        sc = (c1["row"], c1["col"])
        dc = (c2["row"], c2["col"])
        j = JourneyState(start_city=c1, dest_city=c2)
        j.participating = [pidx]
        j.route_select_idx = 0
        j.route_options[pidx] = route_options_for(gs, pidx, sc, dc)
        return j

    def test_returns_valid_route_index(self, default_profile):
        g = make_grid(5, 5)
        add_city(g, 0, 0, "A", 11)
        add_city(g, 4, 4, "B", 44)
        gs = make_two_player_state(g)
        for r in range(4):
            gs.players[0].add_edge(r, 0, r + 1, 0)
        for c in range(4):
            gs.players[0].add_edge(4, c, 4, c + 1)
        gs.journey = self._make_journey_with_routes(g, gs, 0)
        gs.phase = "operate"
        gs.operate_sub = "route_select"
        result = decide_route(gs, 0, default_profile)
        opts = gs.journey.route_options.get(0, [])
        assert isinstance(result.chosen, int)
        assert 0 <= result.chosen < len(opts)

    def test_fallback_when_no_journey(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        gs.phase = "operate"
        gs.operate_sub = "route_select"
        result = decide_route(gs, 0, default_profile)
        assert result.chosen == 0

    def test_chooses_cheaper_route_when_fees_differ(self, default_profile):
        """If route B has zero fees and route A has high fees, choose B."""
        g = make_grid(6, 6)
        add_city(g, 0, 0, "A", 11)
        add_city(g, 5, 5, "B", 55)
        gs = make_two_player_state(g)
        # Route 0: shorter but player 1 owns it → fees
        route_expensive = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (5, 5)]
        for i in range(len(route_expensive) - 1):
            r1, c1 = route_expensive[i]
            r2, c2 = route_expensive[i + 1]
            gs.players[1].add_edge(r1, c1, r2, c2)
        # Route 1: longer but player 0 owns it → no fees
        route_own = [(0, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (5, 5)]
        for i in range(len(route_own) - 1):
            r1, c1 = route_own[i]
            r2, c2 = route_own[i + 1]
            gs.players[0].add_edge(r1, c1, r2, c2)

        j = JourneyState(start_city=g.cities[0], dest_city=g.cities[1])
        j.participating = [0]
        j.route_select_idx = 0
        j.route_options[0] = [route_expensive, route_own]
        gs.journey = j
        gs.phase = "operate"
        gs.operate_sub = "route_select"

        result = decide_route(gs, 0, default_profile)
        # Should prefer own route (index 1) despite being longer
        assert result.chosen == 1


# ── should_declare_end_build ──────────────────────────────────────────── #

class TestShouldDeclareEndBuild:
    def test_false_when_cities_not_connected(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        gs.cities_connected_since = None
        gs.build_pts_remaining    # property; just access
        assert should_declare_end_build(gs, 0, default_profile) is False

    def test_false_when_pts_remaining(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        gs.cities_connected_since = 2
        gs.build_pts_total = 6
        gs.build_pts_used  = 3
        assert should_declare_end_build(gs, 0, default_profile) is False

    def test_true_when_connected_and_no_pts(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        gs.cities_connected_since = 2
        gs.build_pts_total = 6
        gs.build_pts_used  = 6
        assert should_declare_end_build(gs, 0, default_profile) is True

    def test_early_false_when_not_connected(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        gs.cities_connected_since = None
        assert should_declare_end_build_early(gs, 0, default_profile, -5.0) is False

    def test_early_true_when_connected_and_negative_score(
        self, small_grid, default_profile
    ):
        gs = make_two_player_state(small_grid)
        gs.cities_connected_since = 1
        assert should_declare_end_build_early(gs, 0, default_profile, -1.0) is True

    def test_early_false_when_positive_score(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        gs.cities_connected_since = 1
        assert should_declare_end_build_early(gs, 0, default_profile, 5.0) is False


# ── Adaptive participation threshold ─────────────────────────────────── #

class TestAdaptiveThreshold:
    def _make_journey_gs(self, p0_money, p1_money):
        """Two-player state with a simple route and given money amounts."""
        g = make_grid(5, 5)
        c1 = add_city(g, 2, 0, "S", 20)
        c2 = add_city(g, 2, 4, "D", 24)
        gs = make_two_player_state(g)
        for col in range(4):
            gs.players[0].add_edge(2, col, 2, col + 1)
        gs.players[0].money = p0_money
        gs.players[1].money = p1_money
        gs.phase       = "operate"
        gs.operate_sub = "participate"
        gs.journey     = _journey(c1, c2)
        return gs

    def test_trailing_player_joins_more_readily(self):
        """A player trailing by 40 money should accept a marginal route."""
        from dampfross.game.ai.profile import AIProfile
        from dampfross.game.ai.race_decision import _adaptive_ev_threshold

        gs = self._make_journey_gs(p0_money=10, p1_money=50)
        # gap = 40; shift = 40 * 0.05 = 2.0 → threshold = -2.0 - 2.0 = -4.0
        profile = AIProfile(
            participate_ev_threshold=-2.0,
            threshold_gap_scale=0.05,
            threshold_desperation_cap=5.0,
        )
        threshold = _adaptive_ev_threshold(gs, 0, profile)
        assert threshold < profile.participate_ev_threshold

    def test_leading_player_skips_marginal_journey(self):
        """A player leading by 40 money should be more conservative."""
        from dampfross.game.ai.profile import AIProfile
        from dampfross.game.ai.race_decision import _adaptive_ev_threshold

        gs = self._make_journey_gs(p0_money=50, p1_money=10)
        # gap = -40 → shift clamped to -caution_cap → threshold raised
        profile = AIProfile(
            participate_ev_threshold=-2.0,
            threshold_gap_scale=0.05,
            threshold_caution_cap=3.0,
        )
        threshold = _adaptive_ev_threshold(gs, 0, profile)
        assert threshold > profile.participate_ev_threshold

    def test_zero_gap_scale_unchanged(self):
        """threshold_gap_scale=0.0 → effective threshold equals the fixed value."""
        from dampfross.game.ai.profile import AIProfile
        from dampfross.game.ai.race_decision import _adaptive_ev_threshold

        gs = self._make_journey_gs(p0_money=10, p1_money=50)
        profile = AIProfile(participate_ev_threshold=-2.0, threshold_gap_scale=0.0)
        threshold = _adaptive_ev_threshold(gs, 0, profile)
        assert abs(threshold - profile.participate_ev_threshold) < 1e-9

    def test_threshold_capped_at_desperation_cap(self):
        """Extreme gap should not shift the threshold beyond desperation_cap."""
        from dampfross.game.ai.profile import AIProfile
        from dampfross.game.ai.race_decision import _adaptive_ev_threshold

        gs = self._make_journey_gs(p0_money=0, p1_money=1000)
        profile = AIProfile(
            participate_ev_threshold=-2.0,
            threshold_gap_scale=0.5,       # would shift by 500 without cap
            threshold_desperation_cap=5.0,
        )
        threshold = _adaptive_ev_threshold(gs, 0, profile)
        # threshold = -2.0 - 5.0 = -7.0 (capped)
        assert abs(threshold - (-2.0 - 5.0)) < 1e-9
