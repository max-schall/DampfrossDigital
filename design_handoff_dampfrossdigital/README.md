# Handoff: Dampfrossdigital — Design System

## Overview
**Dampfrossdigital** is a digital adaptation of the *Dampfross* board game: players build railway networks on a hex map (Network phase), then race trains across that network (Race phase). This bundle is the **design system** for the application — visual identity, components, map rendering primitives, and eight sample game screens including a map editor.

The aesthetic is a **modern transit-map / cartography** treatment: schematic hex tiles, restrained terrain glyphs, eight bold "line colors" for players, warm paper neutrals.

---

## About the Design Files
The files in this bundle are **design references created in HTML/React/CSS** — prototypes that show the intended look-and-feel and behavior. They are **not production code** to ship directly.

Your task is to **recreate these designs in the target codebase's existing environment** (React, Vue, SwiftUI, Godot, web canvas, native, etc.) using its established patterns and libraries. If no environment exists yet, choose the most appropriate stack for a real-time multiplayer board game (e.g., React + Konva/PixiJS/SVG for the map; or a game engine if going native) and implement against that.

The HTML prototypes are **the source of truth** for visual specification. The included `.jsx` files run inline-compiled via Babel-standalone purely so the design canvas can render — your implementation should use your own component framework.

---

## Fidelity
**High-fidelity (hifi).** Pixel-perfect mockups with final colors, typography, spacing, and interactions. Recreate them pixel-perfectly using your codebase's existing libraries and patterns. All design tokens are spelled out in `tokens.css` — port them to your styling system (CSS variables, Tailwind theme, Tamagui, design-token JSON, etc.).

---

## Files In This Bundle
| File | What's in it |
|------|-------------|
| `Design System.html` | Entry point — opens the design canvas with all artboards |
| `tokens.css` | **The design tokens.** Colors (incl. player lines), terrain palette, type stack, radii, shadows, motion. Theme switches for light/dark/sepia. |
| `ds.css` | Component CSS — buttons, panels, badges, player cards, HUD, hex/track styles, etc. |
| `foundations.jsx` | Brand cover, color palette artboards, type scale artboards (Variation A + B) |
| `map-system.jsx` | **Hex geometry helpers** (`axialToPx`, `hexCorners`, `hexPath`), terrain glyphs, `HexTile`, `CityNode`, `River`, `Track`, `TrainSVG` components |
| `components.jsx` | Buttons, badges, chips, segmented controls, toggles, inputs, panels, dialogs, toasts, player cards, HUD, dice, overlays |
| `screens.jsx` | The eight sample screens (Title, Map view, Network turn, Race, Scoreboard, Round results, Settings, Map editor) |
| `design-canvas.jsx` | Pan-zoom canvas wrapper — **delete in your implementation**, exists only for presentation |
| `tweaks-panel.jsx` | Theme switcher — **delete in your implementation** |

> **Tip:** read `tokens.css` first, then `ds.css`, then jump straight to `screens.jsx` for the screen layouts. The `.jsx` files are plain React with no JSX preprocessing tricks — copy patterns directly.

---

## Design Tokens

### Colors — Variation A (default)
```
--paper      #f4f2ec    Page background, map canvas
--surface    #ffffff    Cards, panels, dialogs
--surface-2  #fbfaf6    Secondary surfaces, side rails
--sunk       #ece9e1    Pressed state, segmented track
--ink        #14171c    Primary text, primary buttons
--ink-1      #2a2e36    Strong UI text
--ink-2      #5a5f6a    Secondary text
--ink-3      #8a8f99    Tertiary / metadata
--ink-4      #b9bcc3    Disabled, dividers darker
--rule       #e2dfd7    Borders
--rule-soft  #ecead3    Soft inner dividers (e.g. table rows)
```

### Player Line Colors (S1–S8)
The game supports up to **8 players**. Each player is identified by one of these "transit line" hues — they appear on tracks, train tokens, avatars, player cards, and HUD accents. They are deliberately distinct in hue *and* luminance for color-vision accessibility.

| ID | Hex | CSS var | Suggested name |
|----|-----|---------|----------------|
| S1 | `#e23b3b` | `--p1` | Krapotkin Red |
| S2 | `#1f6fd9` | `--p2` | Nordpol Blue |
| S3 | `#1f7a4a` | `--p3` | Vossberg Green |
| S4 | `#e8a915` | `--p4` | Lichtenau Yellow |
| S5 | `#e76018` | `--p5` | Sandhafen Orange |
| S6 | `#7a4dd0` | `--p6` | Aschberg Violet |
| S7 | `#0a9aa1` | `--p7` | Kupferstadt Teal |
| S8 | `#d3398a` | `--p8` | Marienburg Pink |

Each color also has a `--pN-tint` (e.g. `--p1-tint: #fcdede`) used for soft backgrounds, halos, ghost tracks, and badge fills.

### Terrain Colors
```
--terrain-plain      #faf8f2    cost 1 to build
--terrain-forest     #d9e7d1    cost 2
--terrain-mountain   #d8cebd    cost 3
--terrain-water      #cee0ed    impassable
--terrain-desert     #ecd6a8    cost 2
--terrain-swamp      #c9c8b1    cost 2
--river              #5ea4d6    river stroke
--coast              #b9d2e3    river underglow / coast band
```

### Semantic
```
--success #1f7a4a   --warn #e8a915   --danger #e23b3b   --info #1f6fd9
```

### Themes
The system supports **three themes** via `[data-theme="..."]` on `<body>`:
- `light` (default) — warm paper, dark ink
- `dark` — slate background, lifted player colors
- `sepia` — vintage atlas, ochre paper, deeper green-blue water

Each theme overrides the same CSS variables. Implementation: set `data-theme` on the document root and store the preference in user prefs.

### Typography
**Variation A (default)** — `Geist` + `Geist Mono`. Variation B is `DM Sans` + `IBM Plex Mono` (alternate; pick one).

```
Display    64 / 65   600   −2.5%    Hero titles, results winner
H1         40 / 43   600   −2.0%    Page titles, round header
H2         28 / 32   600   −1.5%    Section headers
H3         20 / 25   600   −1.0%    Card titles
Body       15 / 23   400    0%      Default text
Small      13 / 19   500    0%      Hints, secondary
Caption    11 / 15   500    +6%     ALL-CAPS LABELS (mono)
Numeric    var       500   tabular  Scores, timers, coordinates
```

**Mono is functional, not decorative.** Use it for: numbers, station codes (e.g. `MBG · capital`), coordinates (`q 14 · r −6`), timer values, eyebrow/caption labels, build IDs. Body copy must NOT use mono.

`font-variant-numeric: tabular-nums` is mandatory wherever numbers tick (scores, timers, distances).

### Spacing & Radius
```
--r-1     4px    Inputs, small chips
--r-2     8px    Buttons (rect), inputs, swatches
--r-3    12px    Panels, cards
--r-4    16px    Dialogs
--r-pill 999px   Pills, HUD, chips
```

No explicit spacing token scale was needed — author with multiples of 4 (4 / 8 / 10 / 14 / 16 / 20 / 24 / 32 / 40 / 56). Default screen padding: `40px 48px` desktop, `24px 16px` mobile.

### Shadows
```
--sh-0   subtle 1px paper-lift     (cards on paper)
--sh-1   0 1px 2px + 0 1px 1px     (resting cards)
--sh-2   0 4px 16px + 0 1px 2px    (popovers, hovered cards)
--sh-3   0 16px 40px + 0 2px 4px   (dialogs, focused HUD)
```

### Motion
```
--dur-snap   120ms ease-out          Button press, toggle flip
--dur-base   220ms ease-out          Hover, panel reveal
--dur-glide  420ms ease-in-out       Camera pan, focus shift
--dur-train  900ms ease-in-out       Train traversal per hex
```

---

## Screens / Views

There are **8 screens** in the system, all designed at **1280 × 800** desktop reference (Map editor at 1440 × 900). All are **responsive**; the layouts collapse from 3-column to 2-column to single-column at tablet/mobile breakpoints.

### 01 · Title / Main Menu (`TitleScreen`)
**Purpose:** Entry point. New game, resume, join, tutorial.

**Layout:** 2-column. Left = branding column (paper bg, brand mark, hero headline "Lay the lines. Race the rails.", primary CTAs, online friends footer). Right = animated map preview with floating "Last 3 games" card.

**Components:** Logo (32px), display title (92px / -.04em), 2 primary buttons (`dr-btn--lg`: "New game" + "Resume Sunday at Tilman's"), 3 ghost buttons (Join by code, Tutorial, Rules), online-friends pill, recent-games card (240px).

### 02 · Map View (mid-game observing) (`MapViewScreen`)
**Purpose:** Watching another player's turn. See full board state.

**Layout:** Header (56px) + 3-column body (260px left players list, 1fr map, 280px right inspector).
- **Header:** Logo · "Round 4 / 9 · Network phase" badge · session name · view segmented (Map/Standings/Log) · settings cog
- **Left rail:** Player cards (one active, others idle), "Race objectives" section with overlay cards
- **Map:** Full hex map with tracks, cities, river. Bottom HUD pill shows active player. Top-right zoom controls.
- **Right inspector:** Hovered tile info ("Aschberg ridge · mountain · Build cost: 3 coins"), recent action log

### 03 · Network-Building Turn (`BuildTurnScreen`)
**Purpose:** Player is laying track. The "active" gameplay screen.

**Layout:** Header + 2-column body (1fr map, 320px right rail).
- **Map:** Same hex map. Two floating overlays — top-left "Lay 2 more segments" prompt with progress bar (3/5), and a hovered-edge cost preview at the cursor.
- **Right rail:** Checklist-style turn flow (Roll engine → Choose start edge → Lay segments → End turn) with completion states, "Available actions" buttons, player line statistics (segments laid, cities reached, net pts).

### 04 · Race Phase (`RaceScreen`)
**Purpose:** Heat racing — trains traverse the route, dice roll per turn.

**Layout:** Header + 2-column body (320px left standings, 1fr race map).
- **Left:** Heat header ("Marienburg → Sandhafen"), live standings (Leading/Chasing/Derailed badges), heat board (3 heats with winners).
- **Race map:** A horizontal-flow stripe of hex tiles with the race route. Players' colored trails behind their trains. Mile markers. Top ribbon ("HEAT 2 · 18 hex · 3 mountain"). Bottom HUD with 2 dice + "Advance train" button.

### 05 · Scoreboard (`ScoreboardScreen`)
**Purpose:** Full standings, sortable, with trend sparklines.

**Layout:** Header + 2-column body (1fr table, 360px sidebar).
- **Table:** Rank · Player (avatar + line) · Network pts · Race pts · 6-round trend sparkline · Total. Leader colored.
- **Sidebar:** "Hannah is leading" feature card + round insights bullets.

### 06 · End-of-Round Results (`ResultsScreen`)
**Purpose:** Recap. Round winner spotlight + highlights + timeline.

**Layout:** Hero band (top, surface bg, big avatar + display title) + body in 2 columns.
- **Hero:** 96px avatar, "★ Round winner" eyebrow, "Hannah · Vossberg Green" display title, point delta.
- **Body left:** "Round highlights" 2×2 grid (Longest network / Most heats won / Most efficient / Boldest move), then "Round timeline" with vertical timeline component.
- **Body right:** "Round totals" panel (sortable list with deltas), "Next round preview" card.

### 07 · Settings (`SettingsScreen`)
**Purpose:** Preferences. Theme, gameplay, controls, audio, accessibility, account.

**Layout:** 2-column. Left nav (240px) + main content.
- **Theme:** 3 theme cards (Paper / Slate / Atlas) — clickable, show 3 player-color dots + theme preview.
- **Behavior:** Toggle rows (snap, confirm) + animation speed segmented control.
- **Layout density:** Compact / Comfortable / Roomy segmented.
- **Footer:** Reset to defaults + Save.

### 08 · Map Editor (`MapEditorScreen`) — 1440 × 900
**Purpose:** Author custom maps. Paint terrain, place cities, draw tracks/rivers, validate.

**Layout:** Top toolbar (48px) + 3-column body (220px palette / 1fr canvas / 280px inspector) + status bar (32px).
- **Top bar:** Logo · map name · modified status · centered tool palette (select, brush, erase, fill, track, city, river, measure) · undo/redo · Preview/Export/Save.
- **Left panel:** Terrain palette (2×3 grid of hex thumbnails with build cost), brush size (1/7/19 hex), opacity slider, symbols grid (Capital/City/Town/Port/Bridge/Tunnel).
- **Canvas:** Full hex grid. Selected tile shows ink-colored ring + dashed paper inner stroke + 6 corner handles. A "brush ghost" hex shows where the next paint would go. Marquee selection rectangle with tile-count label.
- **Floating overlays:** Top-left layer chip (Terrain/Tracks/Symbols/Labels), top-right zoom controls + grid toggle + minimap (140px wide).
- **Bottom-center pill:** Active tool · current terrain · cursor coords.
- **Right inspector:** Map properties (name/author/players/dimensions/seed), selection panel (hex preview + properties: race delay, elevation, bridge/tunnel allowed toggles), layer list with visibility toggles, validation auto-check (reachability, isolated tiles, race symmetry, player start fairness).
- **Status bar:** Tile/city/river counts, zoom %, autosave timestamp, validation status, version.

---

## Key Components

### Hex Tile (`HexTile`)
Flat-top hex (60° increments). Inputs: `cx, cy, r, type, selected, ghost`.
- Terrain types: `plain | forest | mountain | water | desert | swamp | city`
- Renders: filled hex path + terrain glyph (subtle, see `HexGlyph`) + selection ring (dashed ink) when selected
- Stroke: 0.6px `--rule` resting, 1.5px `--ink` selected

### Track (`Track`)
Connects two or more hex centers. Inputs: `points: [[x,y], ...], player: 1-8, ghost: bool, casing: bool`.
- **Casing:** paper-colored outer stroke at `--track-width + 2*--track-stroke` (default 11px), keeps colored line legible across terrain — this is the metro-map trick.
- **Line:** `--track-width` (7px) colored stroke, round caps and joins.
- **Ghost:** dashed `3 7`, 0.7 opacity — for previewed/planned tracks.

### Train Token (`TrainSVG` / `.dr-train`)
SVG version: rounded body (`var(--pN)`), nose (triangle), 2 white windows, 3 wheels, paper outline casing. 32×18 nominal. Rotates to follow track direction.

### City Node (`CityNode`)
Inputs: `cx, cy, name, code, size: s|m|l, label: left|right`.
- Halo (paper) + double-stroked circle. Large = capital (filled inner dot). Label: 11px Geist 600 with 3px paper stroke (paint-order). Sub-label: 8px mono.

### Player Card (`.dr-player` / `PlayerCard`)
Identifies a player. Inputs: `p (1-8), name, state: active|idle|out|winner, hand, score, coins, trains`.
- Grid: 44px avatar (circle, player color, initials) · name + metadata · score + status
- States: active → soft player-color background + matching border. Winner → ring `0 0 0 2px var(--pN) inset`. Out → 0.45 opacity.
- Always has a left edge stripe (4px) in player color.

### Buttons
- `.dr-btn` (default ink-filled pill, 14px Geist 600, 10×16 padding)
- `.dr-btn--secondary` (surface + 1px rule border)
- `.dr-btn--ghost` (transparent, sunk hover)
- `.dr-btn--danger / --success` (semantic colors)
- `.dr-btn--lg` (14×24, 16px) for hero CTAs
- `.dr-btn--sm` (7×12, 12px) for inline actions

### Badges (`.dr-badge`)
Pill, 10px mono uppercase. Variants: default (sunk), `--solid` (ink), `--success / --warn / --danger` (tint backgrounds with matching color text). Optional 6px dot inline.

### Engine Die (`.dr-die`)
46×46, 10px radius, surface bg, sh-2. Pip layout via 3×3 grid (`Die` component maps values 1-6 to grid positions).

### HUD (`.dr-hud`)
Bottom-centered floating pill, ink-92% bg, paper text. Slots: player swatch · player name · divider · phase status · divider · action buttons.

---

## Interactions & Behavior

### Network phase (build turn)
1. Active player rolls engine die → engine value determines max placements (e.g. 1 → 1 segment, 6 → 6 segments).
2. Player clicks adjacent hex edges to extend their network.
3. Hover an edge → cost preview popover shows terrain cost + Build/Cancel.
4. Click confirms; segment animates in (220ms, ease-out, with casing first then color).
5. "End turn" or auto-end when placements exhausted.

### Race phase
1. Trains start at heat origin city.
2. Each player's turn: roll → move N hex along their network toward destination.
3. Train sprite slides along the track (`--dur-train` per hex).
4. Derailment events (mountain crit-fail) flash the train and skip turn.

### Map editor
- **Paint:** click/drag fills hexes with current terrain. Brush sizes 1/7/19 fill ring radii.
- **Fill:** flood-fill same-terrain region.
- **Select:** marquee → multi-select tiles for batch operations.
- **Track / River / City tools:** click hex centers / edges to place that element.
- **Validation:** runs continuously; surfaces in right inspector + status bar dot.
- **Undo/redo:** infinite, per-action.

### Theme switching
Set `data-theme` on `<body>` or `<html>`. All tokens cascade. Persist to localStorage.

### Accessibility
- All 8 player colors pass WCAG AA for 24×24+ shapes against `--paper` and against each other (distinct hue + luminance).
- Reduced-motion: respect `prefers-reduced-motion`; disable train traversal animation, replace with snap.
- Tabular nums everywhere numbers tick → screen readers read numbers consistently.
- Player cards include text state ("PLAYING", "WINNER", "ELIMINATED") in addition to color/opacity.

---

## State Management Needs

Minimum state for a game session:
- `mapId`, `seed`, `players[]` (id, name, color 1-8, score, coins, trainsRemaining, eliminated)
- `currentPlayerId`, `round`, `phase: 'network' | 'race' | 'results'`
- `tracks[]: { ownerPlayerId, edges: [hexA, hexB] }`
- `trains[]: { playerId, position, headingTo, derailed }`
- `heats[]: { from, to, distance, winner }`
- `objectives[]: { type, target, progress }`
- `log[]: { t, playerId, kind, payload }` (for the recent-action panel)

For the editor:
- `map: { width, height, tiles: terrain[][], cities[], rivers[], symbols[] }`
- `selection`, `tool`, `brushSize`, `currentTerrain`, `layerVisibility`, `history` (undo/redo stack)

---

## Implementation Notes

1. **Map rendering** — these designs use SVG, which is fine up to ~2000 tiles. For larger maps or smoother pan/zoom, render to Canvas or WebGL (PixiJS, react-konva).
2. **Track strokes** — render in two passes (casing first, color second) so colored lines visually cross over terrain. Same for rivers (coast underglow + river stroke).
3. **Hex math** — see `axialToPx`, `hexCorners`, `hexPath` in `map-system.jsx`. Flat-top orientation. Axial coordinates `(q, r)`.
4. **Player color via CSS** — every player-themed element uses `style={{'--c': 'var(--pN)'}}` so child styles can reference a single variable. Replicate this with your styling system (Tailwind arbitrary properties, styled-components props, etc.).
5. **No icon library used** — all icons are tiny inline SVGs (12–14px, 1.4 stroke). Replace with your icon library, but keep the visual weight.

---

## Open Items / Decisions Left

- **Real city names** — the design uses placeholder city + line names (Aschberg, Marienburg, Lichtenau, etc.). Replace with your canonical map regions.
- **Heat structure** — the design assumes 3 heats per round; confirm with game design.
- **Engine die** — design assumes a standard d6; if there's a custom die face (e.g. "lightning"), extend the `Die` component.
- **Sound design** — explicitly out of scope for this design system; needs separate audio direction.
- **Localization** — all copy is English placeholder; wrap in i18n on implementation.

---

## Assets
No external image assets are used. All visuals are CSS + inline SVG (icons, hex glyphs, trains, dice, logo). Fonts are loaded from Google Fonts (Geist, Geist Mono, DM Sans, IBM Plex Mono).
