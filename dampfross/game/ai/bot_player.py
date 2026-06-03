"""
AIPlayer — top-level orchestrator for an AI-controlled player.

The AIPlayer receives the current GameState and a player_idx, and returns
a sequence of Actions that the game engine (MainWindow) should execute.
It never modifies game state directly; it only produces Action values.

This keeps the AI logic fully testable without any PyQt dependency.
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional, Union

from ..rules import roll_two, roll_city
from .profile import AIProfile
from .explain import DecisionResult
from .build_decision import (
    choose_start_node,
    plan_build_turn,
    best_ferry_to_buy,
    BuildPlan,
)
from .race_decision import (
    decide_participate,
    decide_route,
    find_alliance_proposal_target,
    decide_alliance_response,
    should_declare_end_build,
    should_declare_end_build_early,
)


# ── Action types returned by AIPlayer ────────────────────────────────── #

@dataclass
class RollBuild:
    """AI wants to roll the build dice."""


@dataclass
class SetBuildStart:
    """AI wants to start building from (row, col)."""
    row: int
    col: int


@dataclass
class PlaceEdge:
    """AI wants to build a track segment to (row, col)."""
    row: int
    col: int


@dataclass
class BuyFerry:
    """AI wants to purchase ferry with index ferry_idx."""
    ferry_idx: int


@dataclass
class EndTurn:
    """AI wants to end its build turn."""


@dataclass
class DeclareEndBuild:
    """AI wants to declare end of the build phase."""


@dataclass
class RollStart:
    """AI wants to roll for the start city (operate phase)."""


@dataclass
class RollDest:
    """AI wants to roll for the destination city (operate phase)."""


@dataclass
class JoinJourney:
    """AI's participation decision."""
    join: bool
    decision: DecisionResult = field(default_factory=lambda: DecisionResult(
        phase="participate", chosen=None))


@dataclass
class SelectRoute:
    """AI selects a route by option index."""
    option_idx: int
    decision: DecisionResult = field(default_factory=lambda: DecisionResult(
        phase="route", chosen=None))


@dataclass
class CooperateWith:
    """AI cooperates with a partner player."""
    partner_idx: int
    decision: DecisionResult = field(default_factory=lambda: DecisionResult(
        phase="route", chosen=None))


@dataclass
class Advance:
    """AI rolls dice to advance in the travel sub-phase."""


@dataclass
class NextJourney:
    """AI wants to proceed to the next journey."""


@dataclass
class ProposeAlliance:
    """AI proposes an alliance with another player."""
    target_idx: int


@dataclass
class RespondAlliance:
    """AI accepts or declines an incoming alliance proposal."""
    accept: bool


Action = Union[
    RollBuild, SetBuildStart, PlaceEdge, BuyFerry, EndTurn, DeclareEndBuild,
    RollStart, RollDest, JoinJourney, SelectRoute, CooperateWith,
    Advance, NextJourney, ProposeAlliance, RespondAlliance,
]


# ── AIPlayer ──────────────────────────────────────────────────────────── #

class AIPlayer:
    """
    Stateless AI decision engine for a single player slot.

    Usage:
      ai = AIPlayer(player_idx=1, profile=AIProfile())
      actions = ai.decide(game_state)
      # apply actions to game_state via MainWindow
    """

    def __init__(
        self,
        player_idx: int,
        profile: Optional[AIProfile] = None,
    ) -> None:
        self.player_idx = player_idx
        self.profile    = profile or AIProfile()
        self._rng       = random.Random(self.profile.seed)

        # Cached plan for the current build turn so we don't re-plan per step
        self._build_plan: Optional[BuildPlan] = None
        self._plan_step:  int = 0

    def reset_plan(self) -> None:
        """Clear cached build plan (call at start of each build turn)."""
        self._build_plan = None
        self._plan_step  = 0

    # ── Main entry point ─────────────────────────────────────────────── #

    def decide(self, game_state) -> list[Action]:
        """
        Return the next list of actions the AI wants to take.

        The caller should execute them in order, refreshing the game state
        between each action, then call decide() again if more actions are
        needed.  Returning a list (rather than a single action) lets the AI
        batch cheap decisions (e.g. roll + commit start node) while still
        letting the UI update between expensive ones (like PlaceEdge).
        """
        gs  = game_state
        idx = self.player_idx

        if gs.winner is not None:
            return []

        if gs.phase == "build":
            return self._decide_build(gs)
        elif gs.phase == "operate":
            return self._decide_operate(gs)
        return []

    # ── Build phase ───────────────────────────────────────────────────── #

    def _decide_build(self, gs) -> list[Action]:
        if gs.player_idx != self.player_idx:
            return []

        # 1. Roll if not yet rolled
        if not gs.build_rolled:
            self.reset_plan()
            return [RollBuild()]

        # 2. Set start node if not yet set
        if gs.build_last is None:
            start = choose_start_node(gs, self.player_idx, self.profile)
            if start is None:
                return [EndTurn()]
            return [SetBuildStart(start[0], start[1])]

        # 3. Build plan on first call after start is set
        if self._build_plan is None:
            self._build_plan = plan_build_turn(gs, self.player_idx, self.profile)
            self._plan_step  = 1  # index 0 is the start node

        plan = self._build_plan

        # 4. Check for early end-build declaration
        if should_declare_end_build_early(
            gs, self.player_idx, self.profile, plan.score
        ):
            return [DeclareEndBuild()]

        # 5. Execute next step of the plan
        if self._plan_step < len(plan.nodes):
            next_node = plan.nodes[self._plan_step]
            self._plan_step += 1
            return [PlaceEdge(next_node[0], next_node[1])]

        # 6. Plan exhausted — consider buying a ferry
        ferry_idx = best_ferry_to_buy(gs, self.player_idx, self.profile)
        if ferry_idx is not None:
            return [BuyFerry(ferry_idx)]

        # 7. End turn or declare end-build
        if should_declare_end_build(gs, self.player_idx, self.profile):
            return [DeclareEndBuild()]
        return [EndTurn()]

    # ── Operate phase ─────────────────────────────────────────────────── #

    def _decide_operate(self, gs) -> list[Action]:
        sub = gs.operate_sub
        idx = self.player_idx

        if sub == "roll_start":
            if gs.player_idx != idx:
                return []
            return [RollStart()]

        if sub == "roll_dest":
            if gs.player_idx != idx:
                return []
            return [RollDest()]

        if sub == "participate":
            j = gs.journey
            if j is None:
                return []
            # Respond if we're the target of a pending proposal
            if j.pending_alliance_from is not None and j.pending_alliance_to == idx:
                accept = decide_alliance_response(gs, idx, self.profile)
                return [RespondAlliance(accept=accept)]
            if gs.player_idx != idx:
                return []
            # Check whether to propose an alliance before deciding
            target = find_alliance_proposal_target(gs, idx, self.profile)
            if target is not None:
                return [ProposeAlliance(target_idx=target)]
            result = decide_participate(gs, idx, self.profile)
            return [JoinJourney(join=bool(result.chosen), decision=result)]

        if sub == "route_select":
            j = gs.journey
            if j is None:
                return []
            if j.route_select_idx >= len(j.participating):
                return []
            if j.participating[j.route_select_idx] != idx:
                return []
            result = decide_route(gs, idx, self.profile)
            chosen = result.chosen
            if isinstance(chosen, tuple) and chosen[0] == "cooperate":
                return [CooperateWith(partner_idx=chosen[1], decision=result)]
            option_idx = chosen if isinstance(chosen, int) else 0
            return [SelectRoute(option_idx=option_idx, decision=result)]

        if sub == "travel":
            j = gs.journey
            if j is None:
                return []
            remaining = [p for p in j.participating if p not in j.arrived_order]
            if not remaining:
                return [NextJourney()]
            return [Advance()]

        if sub == "post_journey":
            return [NextJourney()]

        return []

    # ── Deterministic dice (for testing / replay) ─────────────────────── #

    def roll_build_dice(self) -> tuple[int, int]:
        """Use seeded RNG if profile.seed is set, else true random."""
        if self.profile.seed is not None:
            return self._rng.randint(1, 6), self._rng.randint(1, 6)
        return roll_two()

    def roll_city_dice(self, grid) -> tuple[tuple, dict]:
        """Use seeded RNG if profile.seed is set, else true random."""
        if self.profile.seed is not None:
            d1 = self._rng.randint(1, 6)
            d2 = self._rng.randint(1, 6)
            from ..rules import city_by_number
            number = d1 * 10 + d2
            city = city_by_number(grid, number)
            if city is None and grid.cities:
                city = min(grid.cities, key=lambda c: abs(c["number"] - number))
            return (d1, d2), city
        return roll_city(grid)
