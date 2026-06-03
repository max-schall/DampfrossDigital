"""
RaceDecisionService — handles the operate-phase decisions for an AI player.

Public API
----------
  decide_participate(game_state, player_idx, profile) → DecisionResult
    chosen: True (join) | False (skip)

  decide_route(game_state, player_idx, profile) → DecisionResult
    chosen: int (index into route_options) | ("cooperate", partner_idx)

  should_declare_end_build(game_state, player_idx, profile) → bool
"""
from __future__ import annotations
from typing import Union

from ..rules import (
    route_options_for,
    describe_route,
    route_fees,
    find_route,
    find_route_cheapest,
)
from .profile import AIProfile
from .explain import Candidate, DecisionResult
from .route_evaluator import route_score, race_expected_value, route_options_extended


def _adaptive_ev_threshold(game_state, player_idx: int, profile: AIProfile) -> float:
    """Shift the participation EV threshold based on the gap to the best opponent."""
    own = game_state.players[player_idx].money
    best_other = max(
        (p.money for i, p in enumerate(game_state.players) if i != player_idx),
        default=own,
    )
    gap = best_other - own          # positive = trailing, negative = leading
    shift = gap * profile.threshold_gap_scale
    shift = min(shift, profile.threshold_desperation_cap)
    shift = max(shift, -profile.threshold_caution_cap)
    return profile.participate_ev_threshold - shift


def decide_participate(
    game_state,
    player_idx: int,
    profile: AIProfile,
) -> DecisionResult:
    """
    Decide whether to join the current journey.

    Logic:
      1. Find the best route available to this player.
      2. Compute expected value of that route.
      3. Join if EV > profile.participate_ev_threshold.
      4. Also join if participating would let the player use their own track
         for free (own_pct == 100) and there is any prize at all.
    """
    j  = game_state.journey
    if j is None or j.dest_city is None:
        return DecisionResult(
            phase="participate", chosen=False, note="no active journey"
        )

    sc = (j.start_city["row"], j.start_city["col"])
    dc = (j.dest_city["row"],  j.dest_city["col"])

    routes = route_options_extended(game_state, player_idx, sc, dc, profile)
    if not routes:
        return DecisionResult(
            phase="participate", chosen=False, note="no reachable route"
        )

    # Hard guard: if even at baseline win probability (1/N each for 1st and 2nd)
    # the cheapest route yields zero or negative EV, joining can't pay off.
    min_fees = min(
        sum(route_fees(game_state, player_idx, r).values()) for r in routes
    )
    n_total = len(game_state.players)
    base_p = 1.0 / n_total
    best_case_ev = base_p * profile.prize_1st + base_p * profile.prize_2nd - min_fees
    if best_case_ev <= profile.participate_ev_threshold:
        return DecisionResult(
            phase="participate", chosen=False,
            note=(f"best-case EV {best_case_ev:.1f} ≤ threshold "
                  f"{profile.participate_ev_threshold} (fees={min_fees}, N={n_total})")
        )

    # Score each route
    n_competitors = len(game_state.players) - 1
    best_ev = float("-inf")
    best_route = None
    candidates = []
    labels = ("shortest", "cheapest", "opt-C", "opt-D")

    for i, route in enumerate(routes):
        ev = race_expected_value(route, game_state, player_idx, n_competitors, profile)
        sc_val, factors = route_score(route, game_state, player_idx, profile)
        factors["ev"] = ev
        info = describe_route(game_state, player_idx, route)
        lbl = labels[i] if i < len(labels) else f"route-{i}"
        candidates.append(Candidate(
            label=f"{lbl} [{info['hops']}h {info['fees']}f {info['own_pct']}%own]",
            action=i,
            score=ev,
            factors=factors,
        ))
        if ev > best_ev:
            best_ev = ev
            best_route = route

    effective_threshold = _adaptive_ev_threshold(game_state, player_idx, profile)
    join = best_ev > effective_threshold

    # Extra condition: if we own 100 % of the route, joining costs nothing
    if best_route is not None:
        info = describe_route(game_state, player_idx, best_route)
        if info["own_pct"] == 100 and info["fees"] == 0:
            join = True

    candidates.sort(key=lambda c: c.score, reverse=True)
    return DecisionResult(
        phase="participate",
        chosen=join,
        chosen_score=best_ev,
        candidates=candidates,
        note=f"best EV={best_ev:.1f} threshold={effective_threshold:.1f}",
    )


def decide_route(
    game_state,
    player_idx: int,
    profile: AIProfile,
) -> DecisionResult:
    """
    Choose the best route option or a cooperation partner.

    Returns DecisionResult where chosen is:
      int   — index into route_options[player_idx]
      ("cooperate", partner_idx)  — copy partner's route
    """
    j = game_state.journey
    if j is None:
        return DecisionResult(phase="route", chosen=0, note="no journey")

    opts = list(j.route_options.get(player_idx, []))
    if j.start_city and j.dest_city:
        sc_rc = (j.start_city["row"], j.start_city["col"])
        dc_rc = (j.dest_city["row"],  j.dest_city["col"])
        for r in route_options_extended(game_state, player_idx, sc_rc, dc_rc, profile):
            if r not in opts:
                opts.append(r)
        j.route_options[player_idx] = opts

    n_competitors = max(0, len(j.participating) - 1)

    # ── Score own routes ────────────────────────────────────────────── #
    from .route_evaluator import score_all_routes
    own_result = score_all_routes(opts, game_state, player_idx, profile, n_competitors)

    best_own_score = own_result.chosen_score
    best_own_idx   = own_result.chosen

    # ── Score cooperation options ────────────────────────────────────── #
    already_selected = [
        pp for pp in j.participating[:j.route_select_idx]
        if pp in j.routes
    ]

    coop_candidates: list[Candidate] = []
    for pp in already_selected:
        partner_route = j.routes[pp]
        sc, factors = route_score(partner_route, game_state, player_idx, profile)
        ev = race_expected_value(partner_route, game_state, player_idx,
                                 n_competitors, profile)
        factors["ev"] = ev
        info = describe_route(game_state, player_idx, partner_route)
        coop_candidates.append(Candidate(
            label=(f"cooperate with {game_state.players[pp].name} "
                   f"[{info['hops']}h {info['fees']}f {info['own_pct']}%own]"),
            action=("cooperate", pp),
            score=sc,
            factors=factors,
        ))

    # ── Pick overall best ────────────────────────────────────────────── #
    all_candidates = list(own_result.candidates) + coop_candidates
    all_candidates.sort(key=lambda c: c.score, reverse=True)

    if all_candidates:
        overall_best = all_candidates[0]
        return DecisionResult(
            phase="route",
            chosen=overall_best.action,
            chosen_score=overall_best.score,
            candidates=all_candidates,
            tiebreak=own_result.tiebreak,
        )

    return DecisionResult(phase="route", chosen=0, note="fallback to first route")


def find_alliance_proposal_target(
    game_state,
    player_idx: int,
    profile: AIProfile,
) -> int | None:
    """
    Return the index of a player worth proposing an alliance to, or None.

    Logic: find the player whose track would save us the most fees on the
    best available route, provided the savings meet a minimum threshold.
    Only considers players not already allied, not already declined, and
    not yet decided (so the proposal makes sense).
    """
    j = game_state.journey
    if j is None or j.dest_city is None:
        return None

    sc = (j.start_city["row"], j.start_city["col"])
    dc = (j.dest_city["row"],  j.dest_city["col"])

    already_allied = {
        p for pair in j.alliances for p in pair if player_idx in pair
    }

    best_target = None
    best_savings = 0

    for other_idx in range(len(game_state.players)):
        if other_idx == player_idx:
            continue
        if other_idx in already_allied:
            continue
        if (player_idx, other_idx) in j.declined_proposals:
            continue

        routes = route_options_for(game_state, player_idx, sc, dc)
        if not routes:
            continue
        savings = max(
            route_fees(game_state, player_idx, r).get(other_idx, 0)
            for r in routes
        )
        if savings > best_savings:
            best_savings = savings
            best_target = other_idx

    min_savings = getattr(profile, "alliance_min_fee_savings", 2)
    return best_target if best_savings >= min_savings else None


def decide_alliance_response(
    game_state,
    player_idx: int,
    profile: AIProfile,
) -> bool:
    """
    Decide whether to accept an incoming alliance proposal.

    Accept if the proposer's track would save us meaningful fees.
    """
    j = game_state.journey
    if j is None or j.pending_alliance_from is None or j.dest_city is None:
        return False

    proposer_idx = j.pending_alliance_from
    sc = (j.start_city["row"], j.start_city["col"])
    dc = (j.dest_city["row"],  j.dest_city["col"])

    routes = route_options_for(game_state, player_idx, sc, dc)
    if not routes:
        return False

    savings = max(
        route_fees(game_state, player_idx, r).get(proposer_idx, 0)
        for r in routes
    )
    min_savings = getattr(profile, "alliance_min_fee_savings", 1)
    return savings >= min_savings


def should_declare_end_build(
    game_state,
    player_idx: int,
    profile: AIProfile,
) -> bool:
    """
    Return True if the AI should declare end of build phase now.

    Conditions (all must hold):
    - All cities are connected (gs.cities_connected_since is not None)
    - The current player's build turn is complete (no points remaining
      OR no beneficial moves remain)
    - The AI has at most a marginal advantage from more building

    Note: the button is only shown by the UI when cities_connected_since
    is not None, so we only need to check the strategic condition.
    """
    gs = game_state
    if gs.cities_connected_since is None:
        return False
    if gs.build_pts_remaining > 0:
        return False   # still has points to spend — don't declare yet

    # All build points used and all cities connected → declare end
    return True


def should_declare_end_build_early(
    game_state,
    player_idx: int,
    profile: AIProfile,
    plan_score: float,
) -> bool:
    """
    Return True if it is strategically good to declare end of build
    even with points remaining, when all cities are connected.

    Used by the bot player to decide after a BuildPlan is computed but
    before executing it: if the plan has negative score and cities are
    already connected, ending early is better.
    """
    gs = game_state
    if gs.cities_connected_since is None:
        return False
    return plan_score <= 0
