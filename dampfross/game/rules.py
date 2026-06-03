"""
Dampfross game rules: build costs, travel costs, fees, routing.
"""
import math
import random
from collections import deque

from ..core.hex_grid import HexGrid, _NBRS_ODD, _NBRS_EVEN


# ── Dice ─────────────────────────────────────────────────────────────── #

def roll_d6() -> int:
    return random.randint(1, 6)

def roll_two() -> tuple[int, int]:
    return roll_d6(), roll_d6()


# ── Terrain helpers ──────────────────────────────────────────────────── #

def is_mountain(grid, r: int, c: int) -> bool:
    return bool(grid.is_mountainous is not None and grid.is_mountainous[r, c])


def neighbors_of(r: int, c: int) -> list:
    nbrs = _NBRS_ODD if r % 2 else _NBRS_EVEN
    return [(r + dr, c + dc) for dr, dc in nbrs]


def are_adjacent(r1: int, c1: int, r2: int, c2: int) -> bool:
    nbrs = _NBRS_ODD if r1 % 2 else _NBRS_EVEN
    return (r2 - r1, c2 - c1) in nbrs


# ── Build-phase costs ────────────────────────────────────────────────── #

def build_cost(grid, r1: int, c1: int, r2: int, c2: int) -> int:
    """
    Würfelpunkte needed to build one track segment from (r1,c1) to (r2,c2).

    Cost table:
      flat → flat          : 1
      flat ↔ mountain      : 3
      mountain → mountain  : 5
      river crossing       : +2 (additive on top of terrain cost)

    Examples: plain-river-plain = 3, plain-river-mountain = 5,
              mountain-river-mountain = 7
    """
    mtn1 = is_mountain(grid, r1, c1)
    mtn2 = is_mountain(grid, r2, c2)
    riv  = _edge_crosses_river(grid, r1, c1, r2, c2)

    if mtn1 and mtn2:
        base = 5
    elif mtn1 or mtn2:
        base = 3
    else:
        base = 1
    return base + (2 if riv else 0)


def _edge_crosses_river(grid, r1: int, c1: int, r2: int, c2: int) -> bool:
    """True when a river segment properly intersects the line between the two hex centers.
    Uses segment-segment intersection so a river running parallel to a hex edge
    (near but not crossing) does not trigger the extra cost."""
    if not grid.river_segs:
        return False
    ax, ay = HexGrid.hex_center(r1, c1, 1.0)
    bx, by = HexGrid.hex_center(r2, c2, 1.0)
    for seg in grid.river_segs:
        for i in range(len(seg) - 1):
            cx, cy = float(seg[i,   0]), float(seg[i,   1])
            dx, dy = float(seg[i+1, 0]), float(seg[i+1, 1])
            if math.isnan(cx) or math.isnan(dx):
                continue
            if _segs_intersect(ax, ay, bx, by, cx, cy, dx, dy):
                return True
    return False


def _segs_intersect(ax, ay, bx, by, cx, cy, dx, dy) -> bool:
    """True if segment AB and segment CD properly cross each other."""
    def _cross(ux, uy, vx, vy):
        return ux * vy - uy * vx

    abx, aby = bx - ax, by - ay
    cdx, cdy = dx - cx, dy - cy
    denom = _cross(abx, aby, cdx, cdy)
    if abs(denom) < 1e-10:
        return False   # parallel / collinear
    acx, acy = cx - ax, cy - ay
    t = _cross(acx, acy, cdx, cdy) / denom
    u = _cross(acx, acy, abx, aby) / denom
    return 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0


def crossing_fees(game_state, from_idx: int,
                  r1: int, c1: int, r2: int, c2: int) -> dict:
    """
    Return {player_idx: units} owed by player from_idx when building (r1,c1)→(r2,c2).

    Rules (Abb.3):
    - Connecting to OR crossing another player's line: 1 unit
    - Building in parallel in same hex (half-field): 2 units per half
    - Fees are NOT charged within a city hex.
    """
    grid = game_state.grid
    city_hexes = getattr(grid, "_city_hexes", None)
    if city_hexes is None:
        grid._city_hexes = {(c["row"], c["col"]) for c in grid.cities}
        city_hexes = grid._city_hexes
    edge = frozenset(((r1, c1), (r2, c2)))
    fees: dict[int, int] = {}
    for i, p in enumerate(game_state.players):
        if i == from_idx:
            continue
        amt = 0
        if edge in p.track_edges:
            # Exact overlap (parallel track in the same field): 1 unit
            # Full-parallel (4 units total) only applies if both halves overlap;
            # we simplify by charging 1 per crossing/overlap.
            amt += 1
        elif (r2, c2) not in city_hexes and (r2, c2) in p.track_nodes:
            # Connecting to their existing node: 1 unit
            amt += 1
        if amt:
            fees[i] = fees.get(i, 0) + amt
    return fees


def city_bonus(game_state, player_idx: int, city: dict) -> int:
    """6 units for the first player ever to connect this city."""
    n = city["number"]
    for i, p in enumerate(game_state.players):
        if n in p.connected_cities:
            return 0
    return 6


# ── Ferry helpers ────────────────────────────────────────────────────── #

def ferry_endpoints(ferry: dict):
    """Return ((r1,c1), (r2,c2)) endpoint hexes, or None if < 2 waypoints."""
    wps = ferry.get("waypoints", [])
    if len(wps) < 2:
        return None
    return (wps[0][0], wps[0][1]), (wps[-1][0], wps[-1][1])


def ferry_at_hex(grid, r: int, c: int) -> list:
    """Return indices of ferries whose start or end hex is (r, c)."""
    result = []
    for idx, ferry in enumerate(getattr(grid, "ferries", [])):
        ep = ferry_endpoints(ferry)
        if ep and (ep[0] == (r, c) or ep[1] == (r, c)):
            result.append(idx)
    return result


def ferry_owner_idx(game_state, ferry_idx: int):
    """Return player index that owns this ferry, or None if unbuilt."""
    for i, p in enumerate(game_state.players):
        if ferry_idx in p.owned_ferries:
            return i
    return None


def owned_ferry_accessible_endpoints(game_state, player_idx: int) -> set:
    """
    Return the set of (r,c) hexes that are endpoints of ANY ferry the player
    owns AND accessible for building — i.e., the player's track network
    already touches at least one of the two ferry endpoints.
    """
    cp = game_state.players[player_idx]
    if not cp.owned_ferries:
        return set()
    ferries = getattr(game_state.grid, "ferries", [])
    result: set = set()
    for fidx in cp.owned_ferries:
        if fidx >= len(ferries):
            continue
        ep = ferry_endpoints(ferries[fidx])
        if ep is None:
            continue
        f1, f2 = ep
        if cp.has_node(*f1) or cp.has_node(*f2):
            result.update({f1, f2})
    return result


def built_ferry_edges(game_state) -> set:
    """Return frozenset pairs for all built ferries."""
    result = set()
    for fidx, ferry in enumerate(getattr(game_state.grid, "ferries", [])):
        if ferry_owner_idx(game_state, fidx) is not None:
            ep = ferry_endpoints(ferry)
            if ep:
                result.add(frozenset(ep))
    return result


def city_at_hex(grid, r: int, c: int):
    """Return city dict if (r,c) is a city hex, else None."""
    cache = getattr(grid, "_city_lookup", None)
    if cache is None:
        grid._city_lookup = {(c["row"], c["col"]): c for c in grid.cities}
        cache = grid._city_lookup
    return cache.get((r, c))


def city_by_number(grid, number: int):
    for city in grid.cities:
        if city["number"] == number:
            return city
    return None


def check_all_cities_connected(game_state) -> bool:
    """True when every city hex is in at least one player's track network."""
    if not game_state.grid.cities:
        return False
    all_nodes: set = set()
    for p in game_state.players:
        all_nodes |= p.track_nodes
    return all(
        (c["row"], c["col"]) in all_nodes
        for c in game_state.grid.cities
    )


# ── Operate-phase routing ────────────────────────────────────────────── #

def roll_city(grid) -> tuple[tuple, dict]:
    """Roll two dice → city.  Returns ((red, white), city_dict)."""
    red, white = roll_two()
    number = red * 10 + white
    city = city_by_number(grid, number)
    if city is None and grid.cities:
        city = min(grid.cities, key=lambda c: abs(c["number"] - number))
    return (red, white), city


def find_route(game_state, start_rc: tuple, dest_rc: tuple) -> list | None:
    """
    BFS shortest path (in hexes) from start_rc to dest_rc using the combined
    track network of ALL players, including built ferry edges.
    Returns list[(r,c)] or None if unreachable.
    """
    adj: dict = {}
    for p in game_state.players:
        for edge in p.track_edges:
            a, b = tuple(edge)
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
    for fidx, ferry in enumerate(getattr(game_state.grid, "ferries", [])):
        if ferry_owner_idx(game_state, fidx) is not None:
            ep = ferry_endpoints(ferry)
            if ep:
                a, b = ep
                adj.setdefault(a, []).append(b)
                adj.setdefault(b, []).append(a)
    if start_rc not in adj:
        return None
    queue = deque([(start_rc, [start_rc])])
    visited = {start_rc}
    while queue:
        node, path = queue.popleft()
        if node == dest_rc:
            return path
        for nbr in adj.get(node, []):
            if nbr not in visited:
                visited.add(nbr)
                queue.append((nbr, path + [nbr]))
    return None


def find_route_cheapest(game_state, player_idx: int,
                        start_rc: tuple, dest_rc: tuple) -> list | None:
    """
    Dijkstra: finds a route minimising fees paid to *other* players.
    Edge cost = 0 for own track, 3 for foreign ferry, 1 for any other foreign segment.
    Returns list[(r,c)] or None.
    """
    import heapq
    adj: dict = {}
    own_edges = game_state.players[player_idx].track_edges

    for pidx, p in enumerate(game_state.players):
        fee = 0 if pidx == player_idx else 1
        for edge in p.track_edges:
            a, b = tuple(edge)
            adj.setdefault(a, []).append((b, fee))
            adj.setdefault(b, []).append((a, fee))

    for fidx, ferry in enumerate(getattr(game_state.grid, "ferries", [])):
        owner = ferry_owner_idx(game_state, fidx)
        if owner is not None:
            ep = ferry_endpoints(ferry)
            if ep:
                a, b = ep
                fee = 0 if owner == player_idx else 3
                adj.setdefault(a, []).append((b, fee))
                adj.setdefault(b, []).append((a, fee))

    if start_rc not in adj:
        return None

    counter = 0
    heap = [(0, counter, start_rc, [start_rc])]
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


def route_options_for(game_state, player_idx: int,
                      start_rc: tuple, dest_rc: tuple) -> list:
    """
    Return up to 3 distinct route options for a player:
      0. shortest (fewest hops, BFS)
      1. cheapest (minimum foreign-track fees, Dijkstra)
    Deduplicates so the player never sees the same route twice.
    """
    candidates = [
        find_route(game_state, start_rc, dest_rc),
        find_route_cheapest(game_state, player_idx, start_rc, dest_rc),
    ]
    seen: list = []
    for r in candidates:
        if r is not None and r not in seen:
            seen.append(r)
    return seen if seen else [[start_rc]]   # fallback: stay at start


def describe_route(game_state, player_idx: int, route: list) -> dict:
    """
    Return a display-ready summary for one route option::

        {"hops": 8, "fees": 2, "own_pct": 62}
    """
    if len(route) < 2:
        return {"hops": 0, "fees": 0, "own_pct": 0}
    own_edges = game_state.players[player_idx].track_edges
    own_ferry_edges: set = set()
    for fidx, ferry in enumerate(getattr(game_state.grid, "ferries", [])):
        if ferry_owner_idx(game_state, fidx) == player_idx:
            ep = ferry_endpoints(ferry)
            if ep:
                own_ferry_edges.add(frozenset(ep))
    total = len(route) - 1
    own_count = sum(
        1 for i in range(total)
        if frozenset((route[i], route[i + 1])) in own_edges
        or frozenset((route[i], route[i + 1])) in own_ferry_edges
    )
    fees = sum(route_fees(game_state, player_idx, route).values())
    own_pct = int(100 * own_count / total) if total else 0
    return {"hops": total, "fees": fees, "own_pct": own_pct}


def route_fees(game_state, player_idx: int, route: list) -> dict:
    """
    Credits owed per other player for traveling this route.
    - 1 unit per hex on another player's track (max 10 per player)
    - 3 units per ferry edge if player is not the ferry owner
    Allied players (via journey alliances) owe each other nothing.
    """
    j = getattr(game_state, "journey", None)
    allied_with: set[int] = set()
    if j is not None:
        for pair in j.alliances:
            if player_idx in pair:
                allied_with.update(p for p in pair if p != player_idx)

    fees: dict[int, int] = {}
    _bfe = built_ferry_edges(game_state)
    for i in range(len(route) - 1):
        edge = frozenset((route[i], route[i + 1]))
        if edge in _bfe:
            for fi, ferry in enumerate(getattr(game_state.grid, "ferries", [])):
                ep = ferry_endpoints(ferry)
                if ep and frozenset(ep) == edge:
                    owner = ferry_owner_idx(game_state, fi)
                    if owner is not None and owner != player_idx and owner not in allied_with:
                        fees[owner] = fees.get(owner, 0) + 3
                    break
            continue
        for ji, p in enumerate(game_state.players):
            if ji == player_idx or ji in allied_with:
                continue
            if edge in p.track_edges:
                fees[ji] = min(10, fees.get(ji, 0) + 1)
                break   # only pay the first owner per segment
    return fees


def advance_on_route(grid, route: list, pos: int, dice_total: int,
                     ferry_edges: set | None = None) -> int:
    """
    Move forward along route[pos:] spending dice_total points.
    Going UP a mountain costs 1 extra point; a ferry edge costs 5 points.
    ferry_edges: set of frozenset({(r,c),(r,c)}) for built ferries.
    Returns the new position index.
    """
    remaining = dice_total
    while pos + 1 < len(route) and remaining > 0:
        r_cur, c_cur = route[pos]
        r_nxt, c_nxt = route[pos + 1]
        edge = frozenset(((r_cur, c_cur), (r_nxt, c_nxt)))
        if ferry_edges and edge in ferry_edges:
            cost = 5
        else:
            going_up = (is_mountain(grid, r_nxt, c_nxt)
                        and not is_mountain(grid, r_cur, c_cur))
            cost = 2 if going_up else 1
        if remaining >= cost:
            remaining -= cost
            pos += 1
        else:
            break
    return pos
