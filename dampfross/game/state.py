"""
Core game-state data classes for Dampfross.
All game logic lives in rules.py; these are pure data containers.
"""
from dataclasses import dataclass, field
from typing import Optional, Any
import random

PLAYER_COLORS = [
    ("#e23b3b", "Rot"),
    ("#1f6fd9", "Blau"),
    ("#1f7a4a", "Grün"),
    ("#e8a915", "Gelb"),
    ("#e76018", "Orange"),
    ("#7a4dd0", "Lila"),
    ("#0a9aa1", "Türkis"),
    ("#d3398a", "Magenta"),
]

# Win targets per player count (Einheiten)
WIN_TARGETS = {2: 250, 3: 250, 4: 225, 5: 200, 6: 200}


@dataclass
class PlayerState:
    name: str
    color_hex: str
    money: int = 20
    is_bot: bool = False

    # Track network: frozenset({(r1,c1),(r2,c2)}) per edge
    track_edges: set = field(default_factory=set)
    # All nodes (hex centers) that are part of this player's network
    track_nodes: set = field(default_factory=set)
    # City numbers connected to this player's network at least once
    connected_cities: set = field(default_factory=set)
    # Indices into grid.ferries that this player owns
    owned_ferries: list = field(default_factory=list)

    def add_edge(self, r1: int, c1: int, r2: int, c2: int) -> None:
        self.track_edges.add(frozenset(((r1, c1), (r2, c2))))
        self.track_nodes.update(((r1, c1), (r2, c2)))

    def has_edge(self, r1: int, c1: int, r2: int, c2: int) -> bool:
        return frozenset(((r1, c1), (r2, c2))) in self.track_edges

    def has_node(self, r: int, c: int) -> bool:
        return (r, c) in self.track_nodes


@dataclass
class JourneyState:
    start_city: dict
    dest_city: Optional[dict] = None
    # Player indices who decided to participate
    participating: list = field(default_factory=list)
    # Player indices who have finished their participation decision
    decided: set = field(default_factory=set)
    # routes[player_idx] = list of (r,c) from start to dest
    routes: dict = field(default_factory=dict)
    # Current position index along route for each player
    positions: dict = field(default_factory=dict)
    # Arrival order (player indices)
    arrived_order: list = field(default_factory=list)
    # Pre-computed travel fees: fees_owed[player_idx][other_idx] = units
    fees_owed: dict = field(default_factory=dict)

    # ── Route selection phase ────────────────────────────────────────── #
    # Index into `participating` for whose turn it is to pick a route
    route_select_idx: int = 0
    # route_options[player_idx] = [route_A, route_B, ...] (list of (r,c) lists)
    route_options: dict = field(default_factory=dict)
    # cooperations[follower_idx] = leader_idx  (follower adopts leader's route)
    cooperations: dict = field(default_factory=dict)

    # ── Alliance phase ───────────────────────────────────────────────── #
    # Player idx currently proposing an alliance (waiting for target's response)
    pending_alliance_from: Optional[int] = None
    # Player idx who must accept or decline the pending proposal
    pending_alliance_to: Optional[int] = None
    # Accepted alliances: list of frozenset({pidx_a, pidx_b})
    alliances: list = field(default_factory=list)
    # (proposer_idx, target_idx) pairs that were declined this journey
    declined_proposals: set = field(default_factory=set)


@dataclass
class GameState:
    players: list        # list[PlayerState]
    grid: Any            # HexGrid
    win_target: int

    phase: str = "build"     # "build" | "operate"
    round_number: int = 1
    player_idx: int = 0

    # ── Build phase ─────────────────────────────────────────────────── #
    build_rolled: bool = False
    build_pts_total: int = 0
    build_pts_used: int = 0
    # Last placed node this turn (None = must start from a city)
    build_last: Optional[tuple] = None
    # Fees accumulated this turn: {player_idx: units owed by current player}
    build_fees_accum: dict = field(default_factory=dict)
    # Round number when all cities were first all connected (None = not yet)
    cities_connected_since: Optional[int] = None
    # Individual turns taken after all cities connected
    turns_after_connected: int = 0
    # Log of edges placed this turn — each entry is a dict:
    #   {edge, cost, fees, bonuses, cities_connected_was, build_last_was}
    # Cleared on turn end; used for undo and dotted-pending rendering.
    pending_log: list = field(default_factory=list)
    # Most recent dice roll (d1, d2); used to drive the animation on remote clients.
    last_roll: Optional[tuple] = None

    # ── Operate phase ────────────────────────────────────────────────── #
    # Sub-states: roll_start | roll_dest | participate | travel | post_journey
    operate_sub: str = "roll_start"
    journey: Optional[JourneyState] = None
    journey_number: int = 0   # total journeys completed

    winner: Optional[Any] = None    # PlayerState

    # ── Score history ────────────────────────────────────────────────── #
    # Snapshot of each player's money after each build round and operate journey.
    # score_history[i] = {pidx: money_at_snapshot_i}
    score_history: list = field(default_factory=list)
    # Parallel human-readable labels: "B1", "B2" … for build rounds,
    # "J1", "J2" … for journeys.  Always same length as score_history.
    score_history_labels: list = field(default_factory=list)
    # Money snapshot at the moment build phase ends (to split build vs race).
    # Empty dict means build phase hasn't ended yet.
    build_money: dict = field(default_factory=dict)

    # ── Game options ─────────────────────────────────────────────────── #
    # Shared-roll: one player rolls per round; everyone gets that many pts.
    # Round 1 is exempt (individual rolls determine starting cities).
    shared_roll: bool = False
    shared_roll_total: int = 0    # 0 = no shared roll yet this round
    round_start_player: int = 0   # player_idx who starts the current round

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.player_idx]

    @property
    def build_pts_remaining(self) -> int:
        return max(0, self.build_pts_total - self.build_pts_used)

    def advance_player(self) -> None:
        """Advance to the next player; increment round_number when wrapping.

        With shared_roll the round start rotates each round, so the roller
        always goes first and the round ends when we cycle back to them.
        """
        n = len(self.players)
        next_idx = (self.player_idx + 1) % n
        if next_idx == self.round_start_player:
            # Full round completed
            self.round_number += 1
            if self.shared_roll:
                self.round_start_player = (self.round_start_player + 1) % n
                self.shared_roll_total = 0
                self.player_idx = self.round_start_player
            else:
                self.player_idx = next_idx   # = 0 for normal fixed-start rounds
        else:
            self.player_idx = next_idx
