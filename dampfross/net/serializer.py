"""
Serialize / deserialize GameState to/from a JSON-compatible dict.

The grid (HexGrid) is NOT included — it is transmitted once as raw bytes
via MSG_MAP_DATA and passed into deserialize_state() as an argument.

Type mapping
  frozenset({(r1,c1),(r2,c2)})  →  [[r1,c1],[r2,c2]] (sorted)
  set[tuple]                    →  list of [r,c]
  set[int]                      →  list[int]
  dict{int→*}                   →  dict{str→*}  (JSON limitation)
  Optional[tuple]               →  Optional[list]
  winner: PlayerState           →  int (player index)
"""
from __future__ import annotations
from typing import Any


# ── edge helpers ─────────────────────────────────────────────────────────── #

def _edge_ser(edge) -> list:
    """frozenset of 2 tuples → sorted [[r,c],[r,c]]"""
    pts = sorted(edge)
    return [list(p) for p in pts]


def _edge_des(data: list):
    return frozenset({(data[0][0], data[0][1]), (data[1][0], data[1][1])})


# ── PlayerState ──────────────────────────────────────────────────────────── #

def _ser_player(p) -> dict:
    return {
        "name":            p.name,
        "color_hex":       p.color_hex,
        "money":           p.money,
        "is_bot":          p.is_bot,
        "track_edges":     [_edge_ser(e) for e in p.track_edges],
        "track_nodes":     [list(n) for n in p.track_nodes],
        "connected_cities": list(p.connected_cities),
        "owned_ferries":   list(p.owned_ferries),
    }


def _des_player(d: dict):
    from ..game.state import PlayerState
    p = PlayerState(
        name=d["name"],
        color_hex=d["color_hex"],
        money=d["money"],
        is_bot=d["is_bot"],
    )
    p.track_edges     = {_edge_des(e) for e in d["track_edges"]}
    p.track_nodes     = {(n[0], n[1]) for n in d["track_nodes"]}
    p.connected_cities = set(d["connected_cities"])
    if "owned_ferries" in d:
        p.owned_ferries = list(d["owned_ferries"])
    elif d.get("owned_ferry") is not None:
        p.owned_ferries = [d["owned_ferry"]]
    else:
        p.owned_ferries = []
    return p


# ── JourneyState ─────────────────────────────────────────────────────────── #

def _ser_journey(j) -> dict:
    return {
        "start_city":      j.start_city,
        "dest_city":       j.dest_city,
        "participating":   j.participating,
        "decided":         list(j.decided),
        "routes":          {
            str(k): [list(n) for n in route]
            for k, route in j.routes.items()
        },
        "positions":       {str(k): v for k, v in j.positions.items()},
        "arrived_order":   j.arrived_order,
        "fees_owed":       {
            str(k): {str(kk): vv for kk, vv in v.items()}
            for k, v in j.fees_owed.items()
        },
        "route_select_idx": j.route_select_idx,
        "route_options":   {
            str(k): [[list(n) for n in route] for route in routes]
            for k, routes in j.route_options.items()
        },
        "cooperations":    {str(k): v for k, v in j.cooperations.items()},
        "pending_alliance_from": j.pending_alliance_from,
        "pending_alliance_to":   j.pending_alliance_to,
        "alliances":       [sorted(pair) for pair in j.alliances],
        "declined_proposals": [list(pair) for pair in j.declined_proposals],
    }


def _des_journey(d: dict):
    from ..game.state import JourneyState
    j = JourneyState(start_city=d["start_city"])
    j.dest_city       = d["dest_city"]
    j.participating   = d["participating"]
    j.decided         = set(d["decided"])
    j.routes          = {int(k): [(n[0], n[1]) for n in route]
                         for k, route in d["routes"].items()}
    j.positions       = {int(k): v for k, v in d["positions"].items()}
    j.arrived_order   = d["arrived_order"]
    j.fees_owed       = {int(k): {int(kk): vv for kk, vv in v.items()}
                         for k, v in d["fees_owed"].items()}
    j.route_select_idx = d["route_select_idx"]
    j.route_options   = {
        int(k): [[(n[0], n[1]) for n in route] for route in routes]
        for k, routes in d["route_options"].items()
    }
    j.cooperations    = {int(k): v for k, v in d["cooperations"].items()}
    j.pending_alliance_from = d.get("pending_alliance_from")
    j.pending_alliance_to   = d.get("pending_alliance_to")
    j.alliances       = [frozenset(pair) for pair in d.get("alliances", [])]
    j.declined_proposals = {
        tuple(pair) for pair in d.get("declined_proposals", [])
    }
    return j


# ── pending_log ──────────────────────────────────────────────────────────── #

def _ser_log_entry(e: dict) -> dict:
    return {
        "edge":               _edge_ser(e["edge"]),
        "cost":               e["cost"],
        "fees":               {str(k): v for k, v in e["fees"].items()},
        "bonuses":            [list(b) for b in e["bonuses"]],
        "cities_connected_was": e["cities_connected_was"],
        "build_last_was":     list(e["build_last_was"]) if e["build_last_was"] else None,
    }


def _des_log_entry(d: dict) -> dict:
    return {
        "edge":               _edge_des(d["edge"]),
        "cost":               d["cost"],
        "fees":               {int(k): v for k, v in d["fees"].items()},
        "bonuses":            [tuple(b) for b in d["bonuses"]],
        "cities_connected_was": d["cities_connected_was"],
        "build_last_was":     tuple(d["build_last_was"]) if d["build_last_was"] else None,
    }


# ── GameState ─────────────────────────────────────────────────────────────── #

def serialize_state(gs) -> dict:
    """Convert a GameState to a JSON-serializable dict (grid excluded)."""
    winner_idx = None
    if gs.winner is not None:
        try:
            winner_idx = next(i for i, p in enumerate(gs.players) if p is gs.winner)
        except StopIteration:
            pass

    return {
        "players":               [_ser_player(p) for p in gs.players],
        "win_target":            gs.win_target,
        "phase":                 gs.phase,
        "round_number":          gs.round_number,
        "player_idx":            gs.player_idx,
        "build_rolled":          gs.build_rolled,
        "build_pts_total":       gs.build_pts_total,
        "build_pts_used":        gs.build_pts_used,
        "build_last":            list(gs.build_last) if gs.build_last else None,
        "build_fees_accum":      {str(k): v for k, v in gs.build_fees_accum.items()},
        "cities_connected_since": gs.cities_connected_since,
        "turns_after_connected": gs.turns_after_connected,
        "pending_log":           [_ser_log_entry(e) for e in gs.pending_log],
        "last_roll":             list(gs.last_roll) if gs.last_roll else None,
        "operate_sub":           gs.operate_sub,
        "journey":               _ser_journey(gs.journey) if gs.journey else None,
        "journey_number":        gs.journey_number,
        "winner_idx":            winner_idx,
        "shared_roll":           gs.shared_roll,
        "shared_roll_total":     gs.shared_roll_total,
        "round_start_player":    gs.round_start_player,
        "score_history":         [{str(k): v for k, v in snap.items()}
                                  for snap in gs.score_history],
        "build_money":           {str(k): v for k, v in gs.build_money.items()},
    }


def deserialize_state(data: dict, grid) -> Any:
    """Reconstruct a GameState from a serialized dict, using the supplied grid."""
    from ..game.state import GameState
    players = [_des_player(p) for p in data["players"]]
    gs = GameState(players=players, grid=grid, win_target=data["win_target"])
    gs.phase                 = data["phase"]
    gs.round_number          = data["round_number"]
    gs.player_idx            = data["player_idx"]
    gs.build_rolled          = data["build_rolled"]
    gs.build_pts_total       = data["build_pts_total"]
    gs.build_pts_used        = data["build_pts_used"]
    gs.build_last            = tuple(data["build_last"]) if data["build_last"] else None
    gs.build_fees_accum      = {int(k): v for k, v in data["build_fees_accum"].items()}
    gs.cities_connected_since = data["cities_connected_since"]
    gs.turns_after_connected  = data["turns_after_connected"]
    gs.pending_log            = [_des_log_entry(e) for e in data["pending_log"]]
    lr = data.get("last_roll")
    gs.last_roll              = tuple(lr) if lr else None
    gs.operate_sub            = data["operate_sub"]
    gs.journey                = _des_journey(data["journey"]) if data["journey"] else None
    gs.journey_number         = data["journey_number"]
    wi = data.get("winner_idx")
    gs.winner                 = players[wi] if wi is not None else None
    gs.shared_roll            = data.get("shared_roll", False)
    gs.shared_roll_total      = data.get("shared_roll_total", 0)
    gs.round_start_player     = data.get("round_start_player", 0)
    gs.score_history          = [{int(k): v for k, v in snap.items()}
                                 for snap in data.get("score_history", [])]
    gs.build_money            = {int(k): v for k, v in data.get("build_money", {}).items()}
    return gs
