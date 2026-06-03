"""
BuildDecisionService — plans a full build turn for an AI player.

Public API
----------
  choose_start_node(game_state, player_idx, profile) → (r,c) | None
  plan_build_turn(game_state, player_idx, profile)   → BuildPlan
  ferry_score(game_state, player_idx, profile)       → float

A BuildPlan is a list of (r,c) nodes to visit in order (the first entry
is the chosen start node; each subsequent entry is the next segment to lay).
The caller is responsible for executing each step.
"""
from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from typing import Optional

from ...core.hex_grid import HexGrid
from ..rules import (
    build_cost,
    crossing_fees,
    city_bonus,
    city_at_hex,
    neighbors_of,
    are_adjacent,
    ferry_endpoints,
    ferry_owner_idx,
    owned_ferry_accessible_endpoints,
)
from .profile import AIProfile
from .explain import Candidate, DecisionResult


# ── Data types ────────────────────────────────────────────────────────── #

@dataclass
class BuildPlan:
    """The AI's intended sequence of hex visits for the build turn."""
    nodes: list[tuple]           # [(r,c), …]  including the start node
    total_cost: int              # build points consumed
    total_fees: int              # crossing fees paid
    score: float
    decision: DecisionResult


# ── Internal helpers ──────────────────────────────────────────────────── #

def _unconnected_cities(game_state, player_idx: int) -> list[dict]:
    """Cities not yet in this player's connected_cities set."""
    cp = game_state.players[player_idx]
    return [
        c for c in game_state.grid.cities
        if c["number"] not in cp.connected_cities
    ]


def _city_access_score(
    grid,
    rc: tuple,
    target_cities: list[dict],
    weight: float,
) -> float:
    """
    Reward proximity to unconnected cities: weight * sum(1 / dist).
    Distance is in cube-coordinate hops.
    """
    if not target_cities:
        return 0.0
    total = 0.0
    r, c = rc
    for city in target_cities:
        d = HexGrid.hex_distance(r, c, city["row"], city["col"])
        total += 1.0 / max(1, d)
    return weight * total


def _nearest_unconnected_distance(grid, rc: tuple, target_cities: list[dict]) -> int:
    """Hex distance to the nearest unconnected city, or a large number."""
    if not target_cities:
        return 999
    r, c = rc
    return min(
        HexGrid.hex_distance(r, c, city["row"], city["col"])
        for city in target_cities
    )


def _foreign_nodes(game_state, player_idx: int, path: list[tuple]) -> int:
    """Count how many nodes in path belong exclusively to foreign players."""
    foreign: set = set()
    for i, p in enumerate(game_state.players):
        if i != player_idx:
            foreign |= p.track_nodes
    own = game_state.players[player_idx].track_nodes
    return sum(1 for rc in path if rc in foreign and rc not in own)


def _opponent_min_distance_to_city(game_state, player_idx: int, city: dict) -> int:
    """Hex distance from the nearest opponent track node to the given city."""
    city_rc = (city["row"], city["col"])
    distances = [
        HexGrid.hex_distance(*node, *city_rc)
        for i, p in enumerate(game_state.players)
        if i != player_idx
        for node in p.track_nodes
    ]
    return min(distances, default=999)


def _build_score(
    game_state,
    player_idx: int,
    path: list[tuple],       # from start_node to new endpoint (inclusive)
    profile: AIProfile,
    simulated_connected: set,  # set of city numbers already connected during this sim
) -> tuple[float, dict, int, int]:
    """
    Score a candidate build path (a sequence of nodes to visit).

    Returns (score, factors, total_build_cost, total_fees).
    """
    grid = game_state.grid
    cp   = game_state.players[player_idx]

    if len(path) < 2:
        return 0.0, {}, 0, 0

    total_cost = 0
    total_fees = 0
    city_reward = 0.0
    newly_connected: set = set()

    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        total_cost += build_cost(grid, r1, c1, r2, c2)
        fees_dict = crossing_fees(game_state, player_idx, r1, c1, r2, c2)
        total_fees += sum(fees_dict.values())

        for rc in [(r1, c1), (r2, c2)]:
            city = city_at_hex(grid, *rc)
            if city and city["number"] not in cp.connected_cities \
                    and city["number"] not in simulated_connected \
                    and city["number"] not in newly_connected:
                bonus = city_bonus(game_state, player_idx, city)
                opp_d = _opponent_min_distance_to_city(game_state, player_idx, city)
                if opp_d <= 1:
                    urgency = profile.contention_urgency_w
                elif opp_d <= 2:
                    urgency = 1.0 + (profile.contention_urgency_w - 1.0) * 0.5
                else:
                    urgency = 1.0
                city_reward += (profile.city_connection_w + bonus) * urgency
                newly_connected.add(city["number"])

    endpoint = path[-1]
    unconnected = _unconnected_cities(game_state, player_idx)
    unconnected = [c for c in unconnected if c["number"] not in newly_connected
                   and c["number"] not in simulated_connected]

    access   = _city_access_score(grid, endpoint, unconnected, profile.city_access_w)
    fee_pen  = -total_fees  * profile.fee_penalty_w
    cost_pen = -total_cost  * profile.cost_penalty_w
    fdep_pen = -_foreign_nodes(game_state, player_idx, path) * profile.foreign_dep_w

    # Overextension: penalise if endpoint is farther from nearest unconnected city
    # than the start node was.
    start_dist = _nearest_unconnected_distance(grid, path[0], unconnected)
    end_dist   = _nearest_unconnected_distance(grid, endpoint, unconnected)
    overext    = -max(0, end_dist - start_dist) * profile.overextend_w

    score = city_reward + access + fee_pen + cost_pen + fdep_pen + overext
    factors = {
        "city_reward": city_reward,
        "city_access": access,
        "fee_penalty": fee_pen,
        "cost_penalty": cost_pen,
        "foreign_dep": fdep_pen,
        "overextend":  overext,
    }
    return score, factors, total_cost, total_fees


# ── Lookahead and ferry helpers ───────────────────────────────────────── #

def _two_step_lookahead_score(
    game_state,
    player_idx: int,
    path1: list[tuple],
    pts_after: int,
    profile: AIProfile,
    sim_connected: set,
) -> float:
    """Score the best step-2 continuation reachable from path1's endpoint."""
    if profile.build_lookahead_w <= 0.0 or pts_after <= 0:
        return 0.0
    endpoint1 = path1[-1]
    new_sim = sim_connected | {
        city["number"]
        for rc in path1
        for city in [city_at_hex(game_state.grid, *rc)]
        if city and city["number"] not in sim_connected
    }
    step2_eps = _reachable_endpoints(game_state, player_idx, endpoint1, pts_after)
    best = 0.0
    for ep2, path2 in step2_eps.items():
        sc2, _, _, _ = _build_score(
            game_state, player_idx, path1[-1:] + path2[1:], profile, new_sim
        )
        if sc2 > best:
            best = sc2
    return best


def _ferry_reachable_extensions(
    game_state,
    player_idx: int,
    current_pos: tuple,
    pts_remaining: int,
    profile: AIProfile,
) -> list[tuple[tuple, tuple, float]]:
    """
    Return (near_ep, far_ep, access_score) for unowned ferries where:
    - near_ep is within ferry_plan_horizon hex distance of current_pos
    - near_ep is reachable within pts_remaining build points
    - far_ep provides positive city access score
    """
    grid = game_state.grid
    cp = game_state.players[player_idx]
    ferries = getattr(grid, "ferries", [])

    max_f = getattr(game_state.grid, "max_ferries_per_player", 1)
    if len(cp.owned_ferries) >= max_f or cp.money < 6:
        return []

    unconnected = _unconnected_cities(game_state, player_idx)
    if not unconnected:
        return []

    reachable = _reachable_endpoints(game_state, player_idx, current_pos, pts_remaining)
    reachable_set = set(reachable.keys()) | {current_pos}

    results = []
    cr, cc = current_pos
    for fidx, ferry in enumerate(ferries):
        if ferry_owner_idx(game_state, fidx) is not None:
            continue
        ep = ferry_endpoints(ferry)
        if ep is None:
            continue
        f1, f2 = ep

        if f1 in reachable_set:
            near_ep, far_ep = f1, f2
        elif f2 in reachable_set:
            near_ep, far_ep = f2, f1
        else:
            continue

        if near_ep == current_pos:
            continue  # already at the ferry; handled by buy-ferry logic

        access_sc = _city_access_score(grid, far_ep, unconnected, profile.city_access_w)
        if access_sc > 0:
            results.append((near_ep, far_ep, access_sc))

    return results


# ── Reachable search ─────────────────────────────────────────────────── #

def _reachable_endpoints(
    game_state,
    player_idx: int,
    start: tuple,
    pts_remaining: int,
) -> dict[tuple, list[tuple]]:
    """
    Dijkstra over the hex grid respecting build_cost and remaining build points.
    Returns {endpoint: best_path_to_endpoint} for all reachable endpoints
    (excluding start itself).

    Also seeds from ferry-accessible far endpoints (cost 0) so the planner
    can extend a network from the other side of an owned ferry without
    requiring a track segment across water.
    """
    grid = game_state.grid

    # Ferry far endpoints reachable at zero cost (owned ferry's other side)
    cp = game_state.players[player_idx]
    ferry_eps = owned_ferry_accessible_endpoints(game_state, player_idx)
    far_seeds = ferry_eps - cp.track_nodes   # not yet in network — new territory

    counter = 0
    heap = [(0, counter, start)]
    settled: set[tuple] = set()
    dist: dict[tuple, int] = {start: 0}
    parent: dict[tuple, tuple | None] = {start: None}

    # Seed far ferry endpoints with cost 0 so they show up as reachable
    for ep in far_seeds:
        if ep != start and grid.is_valid(*ep) and grid.is_land(*ep):
            dist[ep] = 0
            parent[ep] = None   # treat as a separate "root"
            counter += 1
            heapq.heappush(heap, (0, counter, ep))

    while heap:
        cost, _, node = heapq.heappop(heap)
        if node in settled:
            continue
        settled.add(node)

        r, c = node
        for nr, nc in neighbors_of(r, c):
            if not grid.is_valid(nr, nc) or not grid.is_land(nr, nc):
                continue
            edge_cost = build_cost(grid, r, c, nr, nc)
            new_cost  = cost + edge_cost
            if new_cost > pts_remaining:
                continue
            nbr = (nr, nc)
            if nbr not in settled and new_cost < dist.get(nbr, pts_remaining + 1):
                dist[nbr] = new_cost
                parent[nbr] = node
                counter += 1
                heapq.heappush(heap, (new_cost, counter, nbr))

    def _reconstruct(node):
        path = []
        while node is not None:
            path.append(node)
            node = parent[node]
        path.reverse()
        # If the path starts with a far-seed node (parent=None, not == start),
        # the reconstructed path begins at that far endpoint — valid start.
        return path

    return {node: _reconstruct(node) for node in settled if node != start}


# ── Public API ────────────────────────────────────────────────────────── #

def choose_start_node(
    game_state,
    player_idx: int,
    profile: AIProfile,
) -> Optional[tuple]:
    """
    Choose which node to start building from this turn.

    Candidates are own track_nodes PLUS any ferry-accessible far endpoints
    (hexes reachable through an owned ferry whose near side is already in the
    network but the far side has not yet been built upon).
    """
    cp = game_state.players[player_idx]
    if not cp.track_nodes:
        return None

    # Far ferry endpoints the player may legally start building from
    ferry_eps = owned_ferry_accessible_endpoints(game_state, player_idx)
    extra_starts = ferry_eps - cp.track_nodes   # far endpoints not yet in network

    unconnected = _unconnected_cities(game_state, player_idx)
    if not unconnected:
        # All cities connected — prefer nodes with most edges (central hubs)
        best = max(cp.track_nodes, key=lambda rc: len([
            e for e in cp.track_edges if rc in e
        ]))
        return best

    all_candidates = list(cp.track_nodes) + list(extra_starts)
    best_node = max(
        all_candidates,
        key=lambda rc: _city_access_score(
            game_state.grid, rc, unconnected, 1.0
        ),
    )
    return best_node


def plan_build_turn(
    game_state,
    player_idx: int,
    profile: AIProfile,
) -> BuildPlan:
    """
    Plan the full sequence of edges to lay this turn.

    Strategy: greedy multi-step beam search.
    At each step, enumerate all endpoints reachable with *remaining* build
    points, score them, pick the best, commit that step, and repeat until
    no more useful moves or no build points left.

    Returns a BuildPlan (may have only the start node if nothing is worth
    building).
    """
    from copy import deepcopy

    gs = game_state
    cp = gs.players[player_idx]
    grid = gs.grid

    start = gs.build_last
    if start is None:
        return BuildPlan(nodes=[], total_cost=0, total_fees=0, score=0.0,
                         decision=DecisionResult(phase="build", chosen=None,
                                                  note="no start node"))

    pts_remaining = gs.build_pts_remaining
    plan_nodes = [start]
    plan_nodes_set: set = {start}  # O(1) membership check
    plan_cost  = 0
    plan_fees  = 0
    plan_score = 0.0
    all_candidates: list[Candidate] = []

    # Track which cities we've connected during this simulated turn
    sim_connected: set = set(cp.connected_cities)

    # intended_edges: existing + newly planned edges (used to detect new edges)
    # this_turn_edges: only edges planned in THIS turn (used to detect backtracks)
    intended_edges: set  = set(cp.track_edges)
    this_turn_edges: set = set()
    current_pos = start

    for _step in range(20):   # hard cap on steps per turn
        if pts_remaining <= 0:
            break

        endpoints = _reachable_endpoints(gs, player_idx, current_pos, pts_remaining)
        if not endpoints:
            break

        step_candidates = []
        for endpoint, path in endpoints.items():
            # Skip endpoints already in the player's network or plan — they
            # form a pointless loop and waste build points.
            if endpoint in cp.track_nodes or endpoint in plan_nodes_set:
                continue

            # Skip if the only path back is through already-owned/planned edges
            new_edges_in_path = [
                frozenset((path[i], path[i + 1]))
                for i in range(len(path) - 1)
                if frozenset((path[i], path[i + 1])) not in intended_edges
            ]
            if not new_edges_in_path:
                continue

            # Skip paths that start by traversing a this-turn planned edge.
            # Executing such a path would try to re-place an edge that was just
            # planned, silently fail, and leave the bot stuck.
            if len(path) >= 2 and frozenset((path[0], path[1])) in this_turn_edges:
                continue

            # Score the full plan so far + this extension
            sc, factors, ec, ef = _build_score(
                gs, player_idx, plan_nodes[-1:] + path[1:],
                profile, sim_connected
            )
            if sc <= 0 and not any(c["number"] not in sim_connected
                                   for c in gs.grid.cities):
                # No positive-value extension
                continue

            step_candidates.append(Candidate(
                label=f"→{endpoint}",
                action=(endpoint, path),
                score=sc,
                factors=factors,
            ))

        # Ferry-aware candidates: build toward a ferry near endpoint
        if profile.ferry_reach_w > 0.0:
            for near_ep, far_ep, access_sc in _ferry_reachable_extensions(
                    gs, player_idx, current_pos, pts_remaining, profile):
                near_path = endpoints.get(near_ep)
                if near_path is None:
                    continue
                sc, factors, ec, ef = _build_score(
                    gs, player_idx, near_path, profile, sim_connected
                )
                ferry_bonus = profile.ferry_reach_w * access_sc
                step_candidates.append(Candidate(
                    label=f"→ferry_near{near_ep}→far{far_ep}",
                    action=(near_ep, near_path),
                    score=sc + ferry_bonus,
                    factors={**factors, "ferry_reach": ferry_bonus},
                ))

        if not step_candidates:
            break

        # Two-step lookahead: rescore candidates by adding best continuation value
        # Pre-sort and cap so we don't run N full Dijkstras for every candidate.
        _LOOKAHEAD_BEAM = 8
        if profile.build_lookahead_w > 0.0 and len(step_candidates) > _LOOKAHEAD_BEAM:
            step_candidates.sort(key=lambda c: c.score, reverse=True)
            step_candidates = step_candidates[:_LOOKAHEAD_BEAM]

        if profile.build_lookahead_w > 0.0:
            rescored = []
            for cand in step_candidates:
                ep, path = cand.action
                step_cost = sum(
                    build_cost(grid, path[i][0], path[i][1],
                               path[i + 1][0], path[i + 1][1])
                    for i in range(len(path) - 1)
                    if frozenset((path[i], path[i + 1])) not in cp.track_edges
                )
                extra = _two_step_lookahead_score(
                    gs, player_idx, path, pts_remaining - step_cost,
                    profile, sim_connected,
                )
                rescored.append(Candidate(
                    label=cand.label,
                    action=cand.action,
                    score=cand.score + profile.build_lookahead_w * extra,
                    factors={**cand.factors, "lookahead": extra},
                ))
            step_candidates = rescored

        step_candidates.sort(key=lambda c: c.score, reverse=True)
        best = step_candidates[0]

        if best.score <= 0 and plan_cost > 0:
            break

        best_endpoint, best_path = best.action
        # Only charge build points for edges that aren't already built.
        # Existing edges are traversed for free; only new edges cost points.
        step_cost = sum(
            build_cost(grid, best_path[i][0], best_path[i][1],
                       best_path[i + 1][0], best_path[i + 1][1])
            for i in range(len(best_path) - 1)
            if frozenset((best_path[i], best_path[i + 1])) not in cp.track_edges
        )
        step_fees = sum(
            sum(crossing_fees(gs, player_idx,
                              best_path[i][0], best_path[i][1],
                              best_path[i + 1][0], best_path[i + 1][1]).values())
            for i in range(len(best_path) - 1)
            if frozenset((best_path[i], best_path[i + 1])) not in cp.track_edges
        )

        # Update simulation state
        for i in range(len(best_path) - 1):
            edge = frozenset((best_path[i], best_path[i + 1]))
            intended_edges.add(edge)
            if edge not in cp.track_edges:
                this_turn_edges.add(edge)
            for rc in [best_path[i], best_path[i + 1]]:
                city = city_at_hex(grid, *rc)
                if city:
                    sim_connected.add(city["number"])

        plan_nodes  += best_path[1:]
        plan_nodes_set.update(best_path[1:])
        plan_cost   += step_cost
        plan_fees   += step_fees
        plan_score  += best.score
        pts_remaining -= step_cost
        current_pos   = best_endpoint
        all_candidates.extend(step_candidates[:3])

        # Stop if we've connected all remaining cities
        remaining_unconnected = _unconnected_cities(gs, player_idx)
        remaining_unconnected = [c for c in remaining_unconnected
                                 if c["number"] not in sim_connected]
        if not remaining_unconnected:
            break

    decision = DecisionResult(
        phase="build",
        chosen=plan_nodes,
        chosen_score=plan_score,
        candidates=all_candidates[:10],
        note=f"plan: {len(plan_nodes)-1} segments, cost={plan_cost}, fees={plan_fees}",
    )
    return BuildPlan(
        nodes=plan_nodes,
        total_cost=plan_cost,
        total_fees=plan_fees,
        score=plan_score,
        decision=decision,
    )


def ferry_score(
    game_state,
    player_idx: int,
    profile: AIProfile,
) -> float:
    """
    Return a score for buying the most valuable available ferry.

    A ferry is valuable if:
    - It is unowned
    - The player's network touches one of its endpoints
    - The other endpoint is near unconnected cities

    Returns the score of the best available ferry, or -inf if none.
    """
    grid = game_state.grid
    cp   = game_state.players[player_idx]
    ferries = getattr(grid, "ferries", [])

    max_f = getattr(game_state.grid, "max_ferries_per_player", 1)
    if len(cp.owned_ferries) >= max_f or cp.money < 6:
        return float("-inf")

    unconnected = _unconnected_cities(game_state, player_idx)
    best = float("-inf")

    for fidx, ferry in enumerate(ferries):
        if ferry_owner_idx(game_state, fidx) is not None:
            continue
        ep = ferry_endpoints(ferry)
        if ep is None:
            continue
        f1, f2 = ep
        if cp.has_node(*f1):
            reachable_side = f2
        elif cp.has_node(*f2):
            reachable_side = f1
        else:
            continue

        sc = _city_access_score(
            grid, reachable_side, unconnected, profile.city_access_w
        )

        best = max(best, sc)

    return best


def best_ferry_to_buy(
    game_state,
    player_idx: int,
    profile: AIProfile,
) -> Optional[int]:
    """Return the index of the best ferry to buy, or None."""
    grid = game_state.grid
    cp   = game_state.players[player_idx]
    ferries = getattr(grid, "ferries", [])

    max_f = getattr(game_state.grid, "max_ferries_per_player", 1)
    if len(cp.owned_ferries) >= max_f or cp.money < 6:
        return None

    # build_last is the player's current build position; on round 1 before any
    # edges are built, track_nodes is empty but the player IS at build_last.
    current_pos = game_state.build_last

    unconnected = _unconnected_cities(game_state, player_idx)
    best_score = float("-inf")
    best_idx   = None

    for fidx, ferry in enumerate(ferries):
        if ferry_owner_idx(game_state, fidx) is not None:
            continue
        ep = ferry_endpoints(ferry)
        if ep is None:
            continue
        f1, f2 = ep
        at_f1 = cp.has_node(*f1) or current_pos == f1
        at_f2 = cp.has_node(*f2) or current_pos == f2
        if at_f1:
            reachable_side = f2
        elif at_f2:
            reachable_side = f1
        else:
            continue

        sc = _city_access_score(
            grid, reachable_side, unconnected, profile.city_access_w
        )

        if sc > best_score:
            best_score = sc
            best_idx   = fidx

    return best_idx if best_score > 0 else None
