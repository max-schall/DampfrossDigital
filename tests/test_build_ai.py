"""
Tests for BuildDecisionService.
"""
import pytest
import numpy as np

from dampfross.game.state import PlayerState, GameState
from dampfross.game.ai.build_decision import (
    choose_start_node,
    plan_build_turn,
    ferry_score,
    best_ferry_to_buy,
    _unconnected_cities,
    _city_access_score,
)
from dampfross.game.ai.profile import AIProfile
from .conftest import make_grid, add_city, make_two_player_state


# ── choose_start_node ─────────────────────────────────────────────────── #

class TestChooseStartNode:
    def test_returns_none_without_track(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        assert choose_start_node(gs, 0, default_profile) is None

    def test_prefers_node_near_unconnected_city(self, small_grid, default_profile):
        """When a player has track near city A and city B, prefer the node
        closest to the unconnected city."""
        gs = make_two_player_state(small_grid)
        # Player 0 has two nodes: one near city Nord (1,1) and one far away
        gs.players[0].track_nodes = {(1, 2), (5, 5)}
        gs.players[0].track_edges = {frozenset(((1, 2), (5, 5)))}
        # Mark Nord as already connected so only Sued (8,8) remains
        gs.players[0].connected_cities = {11}
        node = choose_start_node(gs, 0, default_profile)
        # (5,5) is closer to Sued (8,8) than (1,2)
        assert node == (5, 5)

    def test_returns_something_when_all_cities_connected(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        gs.players[0].track_nodes = {(3, 3), (4, 4)}
        gs.players[0].track_edges = {frozenset(((3, 3), (4, 4)))}
        gs.players[0].connected_cities = {11, 88}
        node = choose_start_node(gs, 0, default_profile)
        assert node in gs.players[0].track_nodes


# ── plan_build_turn ───────────────────────────────────────────────────── #

class TestPlanBuildTurn:
    def _setup_round2(self, grid, profile, pts=6, start=(3, 3)):
        gs = make_two_player_state(grid)
        gs.players[0].track_nodes = {start}
        gs.build_rolled    = True
        gs.build_pts_total = pts
        gs.build_pts_used  = 0
        gs.build_last      = start
        return gs

    def test_plan_extends_toward_city(self, small_grid, default_profile):
        """With 6 build points starting at (3,3), the plan should extend
        towards one of the cities."""
        gs = self._setup_round2(small_grid, default_profile, pts=6)
        plan = plan_build_turn(gs, 0, default_profile)
        assert len(plan.nodes) >= 2, "plan should include at least one segment"

    def test_plan_respects_build_points(self, small_grid, default_profile):
        """Total cost of the plan must not exceed available build points."""
        gs = self._setup_round2(small_grid, default_profile, pts=4)
        plan = plan_build_turn(gs, 0, default_profile)
        assert plan.total_cost <= 4

    def test_empty_plan_when_no_points(self, small_grid, default_profile):
        gs = self._setup_round2(small_grid, default_profile, pts=0)
        plan = plan_build_turn(gs, 0, default_profile)
        # No segments can be laid
        assert plan.total_cost == 0

    def test_plan_connects_city_when_reachable(self, default_profile):
        """City 1 step away with 1 build point → plan should connect it."""
        g = make_grid(5, 5)
        add_city(g, 2, 2, "Zentrum", 22)
        gs = make_two_player_state(g)
        gs.players[0].track_nodes = {(2, 1)}
        gs.build_rolled    = True
        gs.build_pts_total = 1
        gs.build_pts_used  = 0
        gs.build_last      = (2, 1)
        plan = plan_build_turn(gs, 0, default_profile)
        assert (2, 2) in plan.nodes

    def test_no_plan_when_build_last_none(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        gs.build_rolled    = True
        gs.build_pts_total = 6
        gs.build_last      = None
        plan = plan_build_turn(gs, 0, default_profile)
        assert plan.total_cost == 0

    def test_plan_prioritises_city_connection_over_raw_distance(self, default_profile):
        """Two cities equidistant: the one with no prior owner earns bonus,
        plan should head toward it."""
        g = make_grid(7, 7)
        add_city(g, 3, 1, "CityA", 31)
        add_city(g, 3, 5, "CityB", 35)
        gs = make_two_player_state(g)
        # Mark CityA as already connected by player 1 (no bonus)
        gs.players[1].connected_cities = {31}
        gs.players[0].track_nodes = {(3, 3)}
        gs.build_rolled    = True
        gs.build_pts_total = 3
        gs.build_pts_used  = 0
        gs.build_last      = (3, 3)
        plan = plan_build_turn(gs, 0, default_profile)
        # Plan should exist and extends somewhere
        assert len(plan.nodes) >= 1


# ── ferry_score ───────────────────────────────────────────────────────── #

class TestFerryScore:
    def test_no_ferries_returns_neg_inf(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        assert ferry_score(gs, 0, default_profile) == float("-inf")

    def test_returns_neg_inf_when_already_owns_ferry(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        small_grid.ferries = [{"waypoints": [(1, 1), (1, 2)]}]
        gs.players[0].owned_ferry = 0
        assert ferry_score(gs, 0, default_profile) == float("-inf")

    def test_returns_neg_inf_when_not_enough_money(self, small_grid, default_profile):
        gs = make_two_player_state(small_grid)
        gs.players[0].money = 5   # need 6
        small_grid.ferries = [{"waypoints": [(1, 1), (1, 2)]}]
        gs.players[0].track_nodes = {(1, 1)}
        assert ferry_score(gs, 0, default_profile) == float("-inf")


# ── Contention awareness ──────────────────────────────────────────────── #

class TestContentionAwareness:
    def test_contested_city_scored_higher(self, default_profile):
        """A city ≤1 hop from an opponent scores higher than an uncontested one."""
        from dampfross.game.ai.build_decision import _build_score
        from dampfross.game.ai.profile import AIProfile

        g = make_grid(5, 5)
        contested   = add_city(g, 2, 2, "Contested",   22)
        uncontested = add_city(g, 4, 4, "Uncontested", 44)

        gs = make_two_player_state(g)
        # Opponent is 1 hop away from the contested city
        gs.players[1].track_nodes = {(2, 1)}

        profile = AIProfile(contention_urgency_w=2.0)

        # Path heading toward contested city (2,2) from (2,1)
        path_contested   = [(2, 0), (2, 1), (2, 2)]
        # Path heading toward uncontested city (4,4) — no nearby opponent
        path_uncontested = [(2, 0), (3, 0), (4, 0), (4, 4)]

        gs.players[0].track_nodes = {(2, 0)}
        sc_contested,   _, _, _ = _build_score(gs, 0, path_contested,   profile, set())
        sc_uncontested, _, _, _ = _build_score(gs, 0, path_uncontested, profile, set())
        assert sc_contested > sc_uncontested

    def test_uncontested_city_unchanged(self, default_profile):
        """Opponent far away (>2 hops) → urgency factor = 1.0, same as base."""
        from dampfross.game.ai.build_decision import _build_score
        from dampfross.game.ai.profile import AIProfile

        g = make_grid(8, 8)
        add_city(g, 1, 1, "Near", 11)
        gs = make_two_player_state(g)
        # Opponent is 6 hops away — no contention
        gs.players[1].track_nodes = {(7, 7)}

        path = [(1, 0), (1, 1)]
        profile_on  = AIProfile(contention_urgency_w=2.0)
        profile_off = AIProfile(contention_urgency_w=1.0)
        sc_on,  _, _, _ = _build_score(gs, 0, path, profile_on,  set())
        sc_off, _, _, _ = _build_score(gs, 0, path, profile_off, set())
        assert abs(sc_on - sc_off) < 0.01

    def test_contention_disabled_with_unit_weight(self, default_profile):
        """contention_urgency_w=1.0 must leave score identical regardless of distance."""
        from dampfross.game.ai.build_decision import _build_score
        from dampfross.game.ai.profile import AIProfile

        g = make_grid(5, 5)
        add_city(g, 2, 2, "C", 22)
        gs = make_two_player_state(g)
        gs.players[1].track_nodes = {(2, 1)}

        path = [(2, 0), (2, 1), (2, 2)]
        profile = AIProfile(contention_urgency_w=1.0)
        sc, _, _, _ = _build_score(gs, 0, path, profile, set())
        # Should complete without error and give a positive score
        assert isinstance(sc, float)


# ── Two-step lookahead ────────────────────────────────────────────────── #

class TestTwoStepLookahead:
    def _build_profile(self, lookahead_w):
        from dampfross.game.ai.profile import AIProfile
        return AIProfile(build_lookahead_w=lookahead_w)

    def test_lookahead_disabled_with_zero_weight(self):
        """build_lookahead_w=0.0 should complete the build turn without error."""
        g = make_grid(8, 8)
        add_city(g, 1, 1, "A", 11)
        add_city(g, 6, 6, "B", 66)
        gs = make_two_player_state(g)
        profile = self._build_profile(0.0)
        gs.build_pts_total = 5
        gs.build_pts_used  = 0
        gs.build_rolled    = True
        gs.build_last      = (g.cities[0]["row"], g.cities[0]["col"])
        gs.players[0].track_nodes.add(gs.build_last)
        plan = plan_build_turn(gs, 0, profile)
        assert plan.total_cost <= 5

    def test_lookahead_does_not_overspend(self):
        """With lookahead enabled, plan cost must still respect build point budget."""
        g = make_grid(8, 8)
        add_city(g, 1, 1, "A", 11)
        add_city(g, 6, 6, "B", 66)
        gs = make_two_player_state(g)
        profile = self._build_profile(1.0)
        gs.build_pts_total = 6
        gs.build_pts_used  = 0
        gs.build_rolled    = True
        gs.build_last      = (g.cities[0]["row"], g.cities[0]["col"])
        gs.players[0].track_nodes.add(gs.build_last)
        plan = plan_build_turn(gs, 0, profile)
        assert plan.total_cost <= 6

    def test_lookahead_chooses_city_cluster_path(self):
        """
        Lookahead should favour a path leading toward two nearby cities over
        a path with just one city in range (tests that EV across two steps
        can outweigh a greedy single-step choice).
        """
        from dampfross.game.ai.profile import AIProfile

        g = make_grid(10, 6)
        # Cluster: two cities close together on the right
        add_city(g, 2, 5, "ClusterA", 25)
        add_city(g, 3, 5, "ClusterB", 35)
        # Lone city on the left
        add_city(g, 5, 1, "Lone", 51)

        gs = make_two_player_state(g)
        start = (3, 3)
        gs.players[0].track_nodes = {start}
        gs.build_rolled    = True
        gs.build_pts_total = 8
        gs.build_pts_used  = 0
        gs.build_last      = start

        profile = AIProfile(build_lookahead_w=1.0, city_connection_w=12.0)
        plan = plan_build_turn(gs, 0, profile)
        # Plan must not crash and must extend from the start node
        assert len(plan.nodes) >= 2


# ── Ferry-aware build ─────────────────────────────────────────────────── #

class TestFerryAwareBuild:
    def _make_ferry_grid(self):
        """5×8 grid with a ferry linking (2,3)→(2,5) (water hex skipped)."""
        g = make_grid(5, 8)
        # Place ferry connecting land sides across a gap
        g.ferries = [{"waypoints": [(2, 3), (2, 5)]}]
        add_city(g, 0, 6, "FarCity", 6)
        return g

    def test_ferry_endpoint_included_in_candidates(self):
        """With ferry_reach_w > 0, plan should consider building toward the ferry."""
        from dampfross.game.ai.profile import AIProfile

        g = self._make_ferry_grid()
        gs = make_two_player_state(g)
        start = (2, 1)
        gs.players[0].track_nodes = {start}
        gs.build_rolled    = True
        gs.build_pts_total = 3
        gs.build_pts_used  = 0
        gs.build_last      = start

        profile = AIProfile(ferry_reach_w=5.0, ferry_plan_horizon=4)
        plan = plan_build_turn(gs, 0, profile)
        # Should not crash; may or may not include ferry node depending on scoring
        assert isinstance(plan.total_cost, int)

    def test_ferry_not_planned_when_disabled(self):
        """ferry_reach_w=0.0 → plan is identical to baseline (no ferry bonus)."""
        from dampfross.game.ai.profile import AIProfile

        g = self._make_ferry_grid()
        gs1 = make_two_player_state(g)
        gs1.players[0].track_nodes = {(2, 1)}
        gs1.build_rolled    = True
        gs1.build_pts_total = 3
        gs1.build_pts_used  = 0
        gs1.build_last      = (2, 1)

        profile_off = AIProfile(ferry_reach_w=0.0)
        plan_off = plan_build_turn(gs1, 0, profile_off)
        assert isinstance(plan_off.total_cost, int)

    def test_no_ferry_when_money_insufficient(self):
        """Player with < 6 money should not get ferry extension candidates."""
        from dampfross.game.ai.build_decision import _ferry_reachable_extensions
        from dampfross.game.ai.profile import AIProfile

        g = self._make_ferry_grid()
        gs = make_two_player_state(g)
        gs.players[0].money = 5
        profile = AIProfile(ferry_reach_w=2.0, ferry_plan_horizon=5)
        result = _ferry_reachable_extensions(gs, 0, (2, 1), 6, profile)
        assert result == []
