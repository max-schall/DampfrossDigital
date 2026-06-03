"""
AI scoring weights — the single place to tune bot behaviour.

All weights are positive; the decision services apply signs themselves
so the semantics are explicit at the call site.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AIProfile:
    # ── Build-phase weights ──────────────────────────────────────────── #

    # Bonus per newly connected city (stacks with the 6-unit cash bonus)
    city_connection_w: float = 12.0

    # Reward for proximity to unconnected cities: sum(1 / hex_distance)
    city_access_w: float = 2.0

    # Penalty per unit of crossing fees paid to other players
    fee_penalty_w: float = 2.0

    # Penalty per build point consumed (discourages expensive routes)
    cost_penalty_w: float = 0.3

    # Extra penalty for each foreign-network node the path passes through
    foreign_dep_w: float = 1.5

    # Penalty applied when the planned endpoint moves *away* from the
    # nearest unconnected city (overextension guard)
    overextend_w: float = 1.0

    # ── Race / route weights ─────────────────────────────────────────── #

    # Penalty per hop on a route (shorter = faster finish)
    hop_w: float = 0.4

    # Penalty per unit of travel fees on a route
    travel_fee_w: float = 2.0

    # Reward per percentage point of own-track share on a route
    own_track_w: float = 0.05

    # Prize expectations used in expected-value calculation
    prize_1st: float = 20.0
    prize_2nd: float = 10.0

    # Minimum expected value to decide to participate in a journey
    participate_ev_threshold: float = 0.0

    # ── Adaptive participation threshold ─────────────────────────────── #

    # Shift threshold by (gap * scale) so trailing players risk more
    threshold_gap_scale: float = 0.05
    # Max downward shift (trailing player becomes more willing)
    threshold_desperation_cap: float = 5.0
    # Max upward shift (leading player becomes more conservative)
    threshold_caution_cap: float = 3.0

    # ── Contention awareness ─────────────────────────────────────────── #

    # Urgency multiplier applied to city_connection_w when an opponent is ≤1 hex away
    contention_urgency_w: float = 1.5   # 1.0 = disabled

    # ── Balanced route option ────────────────────────────────────────── #

    # Dijkstra weights for the balanced third route
    balanced_route_hop_w: float = 0.5
    balanced_route_fee_w: float = 0.5

    # ── Two-step lookahead ───────────────────────────────────────────── #

    # Weight applied to the best lookahead continuation score; 0.0 = pure greedy
    build_lookahead_w: float = 0.5

    # ── Ferry-aware build planning ───────────────────────────────────── #

    # Bonus weight for building toward a ferry's near endpoint; 0.0 = disabled
    ferry_reach_w: float = 1.0
    # Only consider ferry endpoints within this many hex-distance units
    ferry_plan_horizon: int = 3

    # ── Alliance ─────────────────────────────────────────────────────── #

    # Minimum fee savings (units) to propose or accept an alliance
    alliance_min_fee_savings: int = 2

    # ── Misc ─────────────────────────────────────────────────────────── #

    # Optional RNG seed for deterministic tie-breaking (None = no seed)
    seed: Optional[int] = None
