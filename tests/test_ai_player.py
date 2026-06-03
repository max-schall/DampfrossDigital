"""
Integration tests for AIPlayer: decision legality, determinism, self-play smoke test.
"""
import pytest
import copy

from dampfross.game.state import PlayerState, GameState, JourneyState
from dampfross.game.ai.bot_player import (
    AIPlayer,
    RollBuild, SetBuildStart, PlaceEdge, BuyFerry, EndTurn, DeclareEndBuild,
    RollStart, RollDest, JoinJourney, SelectRoute, CooperateWith,
    Advance, NextJourney,
)
from dampfross.game.ai.profile import AIProfile
from dampfross.game import rules as gr
from .conftest import make_grid, add_city, make_two_player_state, make_bot_state


# ── Helpers ───────────────────────────────────────────────────────────── #

def _apply_action(gs, action):
    """
    Minimal action executor — mirrors MainWindow._apply_ai_action but
    without PyQt, for unit tests.
    """
    if isinstance(action, RollBuild):
        import random
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        pts = d1 + d2
        gs.build_pts_total = pts
        gs.build_pts_used  = 0
        gs.build_rolled    = True
        gs.build_fees_accum.clear()
        cp = gs.current_player
        if gs.round_number == 1 and not cp.track_nodes:
            number = d1 * 10 + d2
            city = gr.city_by_number(gs.grid, number)
            if city is None and gs.grid.cities:
                city = min(gs.grid.cities,
                           key=lambda c: abs(c["number"] - number))
            if city:
                gs.build_last = (city["row"], city["col"])

    elif isinstance(action, SetBuildStart):
        gs.build_last = (action.row, action.col)

    elif isinstance(action, PlaceEdge):
        r2, c2 = action.row, action.col
        if gs.build_last is None:
            return
        r1, c1 = gs.build_last
        if not gr.are_adjacent(r1, c1, r2, c2):
            return
        cp = gs.current_player
        if cp.has_edge(r1, c1, r2, c2):
            return
        cost = gr.build_cost(gs.grid, r1, c1, r2, c2)
        if cost > gs.build_pts_remaining:
            return
        fees = gr.crossing_fees(gs, gs.player_idx, r1, c1, r2, c2)
        if cp.money < sum(fees.values()):
            return
        cp.add_edge(r1, c1, r2, c2)
        gs.build_pts_used += cost
        for pidx, amt in fees.items():
            gs.players[pidx].money += amt
            cp.money -= amt
        gs.build_last = (r2, c2)
        for rc in [(r1, c1), (r2, c2)]:
            city_obj = gr.city_at_hex(gs.grid, *rc)
            if city_obj and city_obj["number"] not in cp.connected_cities:
                bonus = gr.city_bonus(gs, gs.player_idx, city_obj)
                cp.money += bonus
                cp.connected_cities.add(city_obj["number"])
        if gr.check_all_cities_connected(gs) and gs.cities_connected_since is None:
            gs.cities_connected_since = gs.round_number

    elif isinstance(action, EndTurn):
        gs.pending_log.clear()
        gs.advance_player()
        gs.build_rolled    = False
        gs.build_pts_total = 0
        gs.build_pts_used  = 0
        gs.build_last      = None
        gs.build_fees_accum.clear()

    elif isinstance(action, DeclareEndBuild):
        gs.phase       = "operate"
        gs.operate_sub = "roll_start"
        gs.player_idx  = 0

    elif isinstance(action, RollStart):
        (r, w), city = gr.roll_city(gs.grid)
        gs.journey     = JourneyState(start_city=city)
        gs.operate_sub = "roll_dest"

    elif isinstance(action, RollDest):
        if gs.journey is None:
            return
        for _ in range(20):
            (r, w), city = gr.roll_city(gs.grid)
            if city != gs.journey.start_city:
                break
        gs.journey.dest_city = city
        gs.operate_sub = "participate"
        gs.player_idx  = 0

    elif isinstance(action, JoinJourney):
        j = gs.journey
        if j is None:
            return
        j.decided.add(gs.player_idx)
        if action.join:
            j.participating.append(gs.player_idx)
        gs.player_idx = (gs.player_idx + 1) % len(gs.players)
        if len(j.decided) >= len(gs.players):
            if not j.participating:
                gs.operate_sub = "post_journey"
            else:
                sc = (j.start_city["row"], j.start_city["col"])
                dc = (j.dest_city["row"],  j.dest_city["col"])
                for pidx in j.participating:
                    j.route_options[pidx] = gr.route_options_for(gs, pidx, sc, dc)
                j.route_select_idx = 0
                gs.player_idx      = j.participating[0]
                gs.operate_sub     = "route_select"

    elif isinstance(action, SelectRoute):
        j = gs.journey
        if j is None or j.route_select_idx >= len(j.participating):
            return
        pidx = j.participating[j.route_select_idx]
        opts = j.route_options.get(pidx, [])
        if not opts:
            return
        idx = max(0, min(action.option_idx, len(opts) - 1))
        j.routes[pidx]    = opts[idx]
        j.positions[pidx] = 0
        j.route_select_idx += 1
        if j.route_select_idx >= len(j.participating):
            gs.operate_sub = "travel"
            gs.player_idx  = 0
        else:
            gs.player_idx  = j.participating[j.route_select_idx]

    elif isinstance(action, CooperateWith):
        j = gs.journey
        if j is None or action.partner_idx not in j.routes:
            return
        pidx = j.participating[j.route_select_idx]
        j.cooperations[pidx] = action.partner_idx
        j.routes[pidx]       = list(j.routes[action.partner_idx])
        j.positions[pidx]    = 0
        j.route_select_idx  += 1
        if j.route_select_idx >= len(j.participating):
            gs.operate_sub = "travel"
            gs.player_idx  = 0
        else:
            gs.player_idx  = j.participating[j.route_select_idx]

    elif isinstance(action, Advance):
        j = gs.journey
        if j is None:
            return
        import random
        dice = random.randint(2, 12)
        _fe  = gr.built_ferry_edges(gs)
        for pidx in j.participating:
            if pidx in j.arrived_order:
                continue
            route = j.routes.get(pidx, [])
            pos   = j.positions.get(pidx, 0)
            j.positions[pidx] = gr.advance_on_route(gs.grid, route, pos, dice, _fe)
            if j.positions[pidx] >= len(route) - 1:
                j.arrived_order.append(pidx)

    elif isinstance(action, NextJourney):
        j = gs.journey
        if j is None:
            return
        for rank, pidx in enumerate(j.arrived_order, 1):
            prize = 20 if rank == 1 else (10 if rank == 2 else 0)
            gs.players[pidx].money += prize
        for pidx in j.participating:
            route = j.routes.get(pidx, [])
            for owner_idx, amt in gr.route_fees(gs, pidx, route).items():
                gs.players[pidx].money -= amt
                gs.players[owner_idx].money += amt
        winner = next((p for p in gs.players if p.money >= gs.win_target), None)
        if winner:
            gs.winner = winner
            gs.operate_sub = "winner"
            return
        gs.journey_number += 1
        gs.journey     = None
        gs.operate_sub = "roll_start"
        gs.player_idx  = 0


def _run_ai_turn(gs, ai, max_steps=50):
    """Run AI actions until it ends its turn or we hit the step cap."""
    for _ in range(max_steps):
        actions = ai.decide(gs)
        if not actions:
            break
        for act in actions:
            _apply_action(gs, act)
        # Stop after EndTurn / DeclareEndBuild / NextJourney
        if any(isinstance(a, (EndTurn, DeclareEndBuild, NextJourney)) for a in actions):
            break
    return gs


# ── Tests ─────────────────────────────────────────────────────────────── #

class TestAIPlayerLegality:
    def test_build_never_places_illegal_edges(self, default_profile):
        """All edges placed by the AI must be legal build actions."""
        g = make_grid(8, 8)
        add_city(g, 1, 1, "A", 11)
        add_city(g, 6, 6, "B", 66)
        gs = make_two_player_state(g)
        ai = AIPlayer(player_idx=0, profile=default_profile)

        # Run one build turn
        _run_ai_turn(gs, ai)

        # All edges in player 0's network must be adjacent land hexes
        for edge in gs.players[0].track_edges:
            pts = list(edge)
            assert len(pts) == 2
            (r1, c1), (r2, c2) = pts
            assert g.is_land(r1, c1)
            assert g.is_land(r2, c2)
            assert gr.are_adjacent(r1, c1, r2, c2), \
                f"Non-adjacent edge placed: {pts}"

    def test_build_does_not_overspend(self, default_profile):
        """Total build cost must not exceed rolled build points."""
        g = make_grid(8, 8)
        add_city(g, 0, 0, "A", 11)
        add_city(g, 7, 7, "B", 77)
        gs = make_two_player_state(g)
        ai = AIPlayer(player_idx=0, profile=default_profile)

        # Force a specific roll to make test deterministic
        gs.build_pts_total = 5
        gs.build_pts_used  = 0
        gs.build_rolled    = True
        city = g.cities[0]
        gs.build_last = (city["row"], city["col"])
        gs.players[0].track_nodes.add(gs.build_last)

        _run_ai_turn(gs, ai, max_steps=20)
        assert gs.build_pts_used <= 5


class TestAIDeterminism:
    def test_same_seed_same_decisions(self, default_profile):
        """With fixed seed, the AI should produce identical build plans."""
        g = make_grid(8, 8)
        add_city(g, 1, 1, "A", 11)
        add_city(g, 6, 6, "B", 66)

        def _run(seed):
            gs = make_two_player_state(g)
            profile = AIProfile(seed=seed)
            ai = AIPlayer(player_idx=0, profile=profile)
            gs.build_pts_total = 6
            gs.build_pts_used  = 0
            gs.build_rolled    = True
            gs.build_last      = (g.cities[0]["row"], g.cities[0]["col"])
            gs.players[0].track_nodes.add(gs.build_last)
            _run_ai_turn(gs, ai, max_steps=20)
            return set(gs.players[0].track_edges)

        edges1 = _run(42)
        edges2 = _run(42)
        assert edges1 == edges2

    def test_different_seed_may_differ(self, default_profile):
        """Different seeds may (but needn't always) produce different results.
        Just verifies both complete without error."""
        g = make_grid(8, 8)
        add_city(g, 1, 1, "A", 11)
        add_city(g, 6, 6, "B", 66)
        for seed in (0, 1, 99):
            gs = make_two_player_state(g)
            profile = AIProfile(seed=seed)
            ai = AIPlayer(player_idx=0, profile=profile)
            gs.build_pts_total = 6
            gs.build_pts_used  = 0
            gs.build_rolled    = True
            gs.build_last      = (g.cities[0]["row"], g.cities[0]["col"])
            gs.players[0].track_nodes.add(gs.build_last)
            _run_ai_turn(gs, ai, max_steps=20)   # must not raise


class TestAIParticipateDecision:
    def test_participates_on_own_full_route(self, default_profile):
        """AI should join a journey when it owns the entire route."""
        g = make_grid(5, 5)
        c1 = add_city(g, 2, 0, "S", 20)
        c2 = add_city(g, 2, 4, "D", 24)
        gs = make_two_player_state(g)
        for col in range(4):
            gs.players[0].add_edge(2, col, 2, col + 1)
        gs.phase       = "operate"
        gs.operate_sub = "participate"
        j = JourneyState(start_city=c1, dest_city=c2)
        gs.journey = j
        gs.player_idx = 0

        ai = AIPlayer(player_idx=0, profile=default_profile)
        actions = ai.decide(gs)
        join_actions = [a for a in actions if isinstance(a, JoinJourney)]
        assert join_actions, "AI should produce a JoinJourney action"
        assert join_actions[0].join is True


class TestAISmokeTest:
    def test_bot_completes_build_phase(self, default_profile):
        """
        Smoke test: a single bot can complete a full build phase
        (reach EndTurn or DeclareEndBuild) without crashing.
        """
        g = make_grid(10, 10)
        add_city(g, 1, 1, "Nord",  11)
        add_city(g, 8, 8, "Sued",  88)
        gs = make_bot_state(g)
        gs.player_idx = 1   # bot's turn

        ai = AIPlayer(player_idx=1, profile=default_profile)
        gs.build_pts_total = 8
        gs.build_pts_used  = 0
        gs.build_rolled    = False

        ended = False
        for _ in range(60):
            actions = ai.decide(gs)
            if not actions:
                break
            for act in actions:
                _apply_action(gs, act)
            if any(isinstance(a, (EndTurn, DeclareEndBuild)) for a in actions):
                ended = True
                break

        assert ended, "Bot should eventually end its turn"

    def test_ai_explain_output_is_non_empty(self, default_profile):
        """The decision result's __str__ should produce non-empty output."""
        from dampfross.game.ai.explain import DecisionResult, Candidate
        dr = DecisionResult(
            phase="build",
            chosen=(3, 4),
            chosen_score=7.5,
            candidates=[
                Candidate("→(3,4)", (3, 4), 7.5, {"city_reward": 12.0}),
                Candidate("→(2,3)", (2, 3), 3.1, {"city_reward": 0.0}),
            ],
            note="test",
        )
        out = str(dr)
        assert "build" in out
        assert "7.5" in out
