"""
RouteEvaluator — scores routes and provides pathfinding cost models.

Exposes:
  route_score(route, game_state, player_idx, profile)  → float
  race_expected_value(route, game_state, player_idx, n_competitors, profile) → float
  cheapest_path(game_state, player_idx, start, dest)  → list[(r,c)] | None
  own_track_path(game_state, player_idx, start, dest) → list[(r,c)] | None
"""
from __future__ import annotations
import heapq
from typing import Optional

from ..rules import (
    describe_route,
    find_route,
    find_route_cheapest,
    route_fees,
    route_options_for,
    built_ferry_edges,
    ferry_owner_idx,
    ferry_endpoints,
)
from .profile import AIProfile
from .explain import Candidate, DecisionResult


def route_score(
    route: list,
    game_state,
    player_idx: int,
    profile: AIProfile,
) -> tuple[float, dict]:
    """
    Score a single route option.  Returns (score, factors).

    Higher is better.  Factors dict contains each component's contribution
    so callers can build a Candidate with full explainability.
    """
    if not route or len(route) < 2:
        return -1000.0, {"error": -1000.0}

    info = describe_route(game_state, player_idx, route)
    hops     = info["hops"]
    fees     = info["fees"]
    own_pct  = info["own_pct"]

    hop_penalty    = -hops      * profile.hop_w
    fee_penalty    = -fees      * profile.travel_fee_w
    own_reward     =  own_pct   * profile.own_track_w

    score = hop_penalty + fee_penalty + own_reward
    factors = {
        "hops":     hop_penalty,
        "fees":     fee_penalty,
        "own_pct":  own_reward,
    }
    return score, factors


def race_expected_value(
    route: list,
    game_state,
    player_idx: int,
    n_competitors: int,
    profile: AIProfile,
) -> float:
    """
    Expected monetary value of participating with this route.

    EV = p(1st) * prize_1st + p(2nd) * prize_2nd - fees

    Win probability drops with route length (longer route → slower → harder to
    win).  For 2-competitor races the outcomes are binary (1st or 2nd), so
    p(2nd) = 1 − p(1st).  For larger fields p(2nd) is bounded by 1/N.
    """
    if not route or len(route) < 2:
        return -999.0

    info = describe_route(game_state, player_idx, route)
    hops = max(1, info["hops"])
    fees = info["fees"]

    total_participants = n_competitors + 1
    base_p = 1.0 / total_participants

    # Length penalty: each hop past 8 reduces win probability by 3 %
    length_penalty = max(0.0, (hops - 8) * 0.03)
    p1 = max(0.05, base_p - length_penalty)

    # In a 2-player race you always finish either 1st or 2nd
    if n_competitors == 1:
        p2 = 1.0 - p1
    else:
        p2 = max(0.0, min(base_p, 1.0 - p1))

    ev = p1 * profile.prize_1st + p2 * profile.prize_2nd - fees
    return ev


def score_all_routes(
    routes: list[list],
    game_state,
    player_idx: int,
    profile: AIProfile,
    n_competitors: int = 0,
) -> DecisionResult:
    """
    Evaluate all route options and return a DecisionResult for route selection.
    """
    if not routes:
        return DecisionResult(
            phase="route", chosen=None, note="no routes available"
        )

    candidates = []
    labels = ("Route A (shortest)", "Route B (cheapest)", "Route C", "Route D")
    for i, route in enumerate(routes):
        sc, factors = route_score(route, game_state, player_idx, profile)
        ev = race_expected_value(route, game_state, player_idx, n_competitors, profile)
        factors["ev"] = ev
        factors["route_score"] = sc
        label = labels[i] if i < len(labels) else f"Route {i}"
        info = describe_route(game_state, player_idx, route)
        candidates.append(Candidate(
            label=f"{label} [{info['hops']}h {info['fees']}f {info['own_pct']}%own]",
            action=i,
            score=ev,   # rank routes by expected monetary value
            factors=factors,
        ))

    candidates.sort(key=lambda c: c.score, reverse=True)
    best = candidates[0]

    tiebreak = ""
    if len(candidates) >= 2 and abs(candidates[0].score - candidates[1].score) < 0.01:
        tiebreak = "tie broken by route index (prefer shorter/first)"

    return DecisionResult(
        phase="route",
        chosen=best.action,
        chosen_score=best.score,
        candidates=candidates,
        tiebreak=tiebreak,
    )


def find_route_balanced(
    game_state,
    player_idx: int,
    start_rc: tuple,
    dest_rc: tuple,
    hop_w: float = 0.5,
    fee_w: float = 0.5,
) -> list | None:
    """
    Dijkstra over the combined track network with edge cost = hop_w + fee_w * fee.
    Own edges: hop_w.  Foreign edges: hop_w + fee_w * fee_amount.
    Returns None if no path exists.
    """
    adj: dict = {}
    own_edges = game_state.players[player_idx].track_edges

    for pidx, p in enumerate(game_state.players):
        raw_fee = 0 if pidx == player_idx else 1
        for edge in p.track_edges:
            a, b = tuple(edge)
            cost = hop_w + fee_w * raw_fee
            adj.setdefault(a, []).append((b, cost))
            adj.setdefault(b, []).append((a, cost))

    for fidx, ferry in enumerate(getattr(game_state.grid, "ferries", [])):
        owner = ferry_owner_idx(game_state, fidx)
        if owner is not None:
            ep = ferry_endpoints(ferry)
            if ep:
                a, b = ep
                raw_fee = 0 if owner == player_idx else 3
                cost = hop_w + fee_w * raw_fee
                adj.setdefault(a, []).append((b, cost))
                adj.setdefault(b, []).append((a, cost))

    if start_rc not in adj:
        return None

    counter = 0
    heap = [(0.0, counter, start_rc, [start_rc])]
    visited: dict = {}
    while heap:
        cost, _, node, path = heapq.heappop(heap)
        if node in visited:
            continue
        visited[node] = cost
        if node == dest_rc:
            return path
        for nbr, edge_cost in adj.get(node, []):
            if nbr not in visited:
                counter += 1
                heapq.heappush(heap, (cost + edge_cost, counter, nbr, path + [nbr]))
    return None


def route_options_extended(
    game_state,
    player_idx: int,
    start_rc: tuple,
    dest_rc: tuple,
    profile: AIProfile,
) -> list[list]:
    """
    Returns [shortest, cheapest, balanced], deduplicated (2 or 3 routes).
    Falls back to base options if balanced duplicates an existing route.
    """
    base = route_options_for(game_state, player_idx, start_rc, dest_rc)
    balanced = find_route_balanced(
        game_state, player_idx, start_rc, dest_rc,
        profile.balanced_route_hop_w,
        profile.balanced_route_fee_w,
    )
    if balanced is not None and balanced not in base:
        base = list(base) + [balanced]
    return base


def own_path_cost(
    game_state,
    player_idx: int,
    start: tuple,
    dest: tuple,
) -> float:
    """
    Dijkstra cost where own track = 0, foreign track = 1, foreign ferry = 3.
    Returns the minimum cost, or infinity if no path exists.
    """
    route = find_route_cheapest(game_state, player_idx, start, dest)
    if route is None:
        return float("inf")
    fees_dict = route_fees(game_state, player_idx, route)
    return float(sum(fees_dict.values()))
