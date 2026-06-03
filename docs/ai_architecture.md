# Dampfross AI Architecture

Offline, rule-based AI player for Dampfross.
No LLMs, no internet access, no cloud dependencies.

---

## Module layout

```
dampfross/game/ai/
    __init__.py          — public re-exports (AIPlayer, AIProfile)
    profile.py           — AIProfile: all scoring weights in one place
    explain.py           — DecisionResult, Candidate: structured traces
    route_evaluator.py   — route_score(), race_expected_value(), score_all_routes()
    build_decision.py    — plan_build_turn(), choose_start_node(), ferry_score()
    race_decision.py     — decide_participate(), decide_route(), should_declare_end_build()
    bot_player.py        — AIPlayer: orchestrator; produces Action values
```

The AI never imports PyQt. All decisions are pure functions of `GameState`.

---

## Decision phases

### 1. Build phase

**Entry:** `AIPlayer._decide_build(game_state)`

1. **Roll dice** — `RollBuild` action, no animation dialog.
2. **Choose start node** — `choose_start_node()` picks the node in
   `track_nodes` with the highest `city_access_score` toward unconnected cities.
   Round 1: the starting city is assigned automatically by the roll result.
3. **Plan build sequence** — `plan_build_turn()` runs a greedy Dijkstra-based
   search. At each step it enumerates all endpoints reachable within remaining
   build points, scores each candidate path with `buildScore()`, picks the
   best, commits that step to the simulation, and repeats.
4. **Execute plan** — one `PlaceEdge` action per node in the plan.
5. **Buy ferry** — if `best_ferry_to_buy()` returns a positive-score ferry,
   emit a `BuyFerry` action.
6. **End turn** — `EndTurn` normally; `DeclareEndBuild` if all cities are
   connected and no further builds are beneficial.

### 2. Race / operate phase

**Entry:** `AIPlayer._decide_operate(game_state)`

Operates by sub-state:

| Sub-state | AI action |
|---|---|
| `roll_start` | `RollStart` |
| `roll_dest` | `RollDest` |
| `participate` | `decide_participate()` → `JoinJourney(join=True/False)` |
| `route_select` | `decide_route()` → `SelectRoute(idx)` or `CooperateWith(partner)` |
| `travel` | `Advance` until all arrived |
| `post_journey` | `NextJourney` |

---

## Heuristics and scoring

### buildScore(path, state) → (score, factors)

```
score = city_reward
      + city_access_score
      - fee_penalty
      - cost_penalty
      - foreign_dependency_penalty
      - overextension_penalty
```

| Factor | Weight | Description |
|---|---|---|
| `city_connection_w` | 12.0 | Per newly connected city (stacks with 6-unit cash bonus) |
| `city_access_w` | 2.0 | `weight × Σ(1 / hex_distance)` to unconnected cities from endpoint |
| `fee_penalty_w` | 2.0 | Per unit of crossing fees paid |
| `cost_penalty_w` | 0.3 | Per build point consumed |
| `foreign_dep_w` | 1.5 | Per foreign-network node passed through |
| `overextend_w` | 1.0 | If endpoint is farther from nearest unconnected city than start |

### routeScore(route, state) → (score, factors)

```
score = - hops × hop_w
        - fees × travel_fee_w
        + own_pct × own_track_w
```

| Weight | Default | Description |
|---|---|---|
| `hop_w` | 0.4 | Shorter routes preferred |
| `travel_fee_w` | 2.0 | Fees reduce net profit |
| `own_track_w` | 0.05 | Prefer routes on own track |

### raceExpectedValue(route, state) → float

```
EV = p1 × prize_1st + p2 × prize_2nd - fees
```

`p1 = max(0.05, 1/n_participants - length_penalty)`
where `length_penalty = max(0, (hops - 10) × 0.02)`.

The AI participates if `EV > participate_ev_threshold` (default −2.0),
or unconditionally if `own_pct == 100` and `fees == 0`.

---

## Scoring weights and profiles

All weights live in `AIProfile` (`dampfross/game/ai/profile.py`).
To create a more aggressive build profile:

```python
from dampfross.game.ai.profile import AIProfile
from dampfross.game.ai.bot_player import AIPlayer

aggressive = AIProfile(
    city_connection_w=20.0,   # value cities more
    overextend_w=0.2,         # less worried about overextension
    participate_ev_threshold=-5.0,  # join more races
)
ai = AIPlayer(player_idx=1, profile=aggressive)
```

---

## Explainability

Every public decision method returns a `DecisionResult`:

```python
@dataclass
class DecisionResult:
    phase: str           # "build" | "participate" | "route" | "cooperate"
    chosen: Any          # the selected action
    chosen_score: float
    candidates: list[Candidate]   # all options considered
    tiebreak: str        # reason if scores were equal
    note: str            # free-form context
```

Each `Candidate` carries `label`, `action`, `score`, and `factors` (a dict
of named score contributions).

`str(result)` prints a human-readable trace with the top 5 candidates.

The `JoinJourney`, `SelectRoute`, and `CooperateWith` action dataclasses each
carry the `DecisionResult` that produced them, so callers (including tests)
can inspect reasoning without re-running the AI.

---

## UI integration

The `GameSetupScreen` now has a "Bot" checkbox per player row.
`player_configs()` returns `{"name": …, "color": …, "is_bot": bool}`.

`MainWindow._start_game()` creates an `AIPlayer` for every bot slot.
After every `_game_refresh_ui()`, if the current player is a bot and the
game is in an actionable state, `QTimer.singleShot(120ms, _run_ai_step)` is
scheduled. The 120 ms delay lets the UI repaint before the bot acts, so the
board visually updates between moves.

`_run_ai_step()` calls `ai.decide(gs)` and dispatches each returned action
through `_apply_ai_action()`, which mirrors the existing UI handler methods
without any dialog boxes.

---

## How to run tests

```bash
# From the project root:
python -m pytest tests/ -v

# One module at a time:
python -m pytest tests/test_build_ai.py -v
python -m pytest tests/test_route_eval.py -v
python -m pytest tests/test_race_ai.py -v
python -m pytest tests/test_ai_player.py -v
```

No PyQt is required for the tests; they only import `dampfross.core` and
`dampfross.game`.

---

## Known limitations

1. **Build planning is greedy, not globally optimal.** The AI commits one
   segment at a time and does not backtrack. This can miss multi-step plans
   that temporarily sacrifice score to reach a high-value destination.

2. **Race EV model is a rough approximation.** Win probabilities are estimated
   from participant count and route length only. The AI does not model
   competitors' routes, speeds, or likely arrival order.

3. **No opponent modelling.** The AI treats opponents as passive. It does not
   anticipate blocking moves or race for contested city connections.

4. **No post-race reinvestment phase.** Dampfross does not have an explicit
   reinvestment sub-phase; the AI's build-phase heuristics (city access,
   foreign-track penalty) implicitly capture this goal.

5. **Ferry evaluation is shallow.** The AI buys a ferry only when its network
   already touches an endpoint and the other side is near unconnected cities.
   It does not plan ahead to extend its network to a ferry endpoint.

6. **No multi-player coordination.** Cooperation decisions are purely
   self-interested (compare own EV vs partner's route EV for *self*).

---

## Likely future improvements

- **Beam search or MCTS for build planning** — evaluate full turn sequences
  rather than committing greedily.
- **Opponent network modelling** — track how close competitors are to each
  city to better predict race competition.
- **Adaptive profiles** — switch between conservative and aggressive profiles
  based on the current score gap.
- **Difficulty levels** — expose a `difficulty` parameter in `AIProfile` that
  scales weights (e.g. `easy` makes the AI occasionally choose suboptimally).
- **Ferry planning** — extend the build planner to include "plan to reach a
  ferry endpoint in future turns" as a build goal.
