# PROMPT FOR CLAUDE CODE

Copy and paste the following into your Claude Code session, *after* you've placed this folder somewhere in your project.

---

## The prompt

> I have a complete design system in `design_handoff_dampfrossdigital/`. Read `README.md` in that folder for the full spec, then read **every other file in that folder** (HTML, CSS, JSX) to see the actual design implementation.
>
> **The HTML/CSS/JSX files are the source of truth for layout, components, and screens — not just the color tokens.** I want you to recreate the entire design in this codebase, not just port the colors.
>
> **Open `design_handoff_dampfrossdigital/Design System.html` in your browser first** (or have me describe what you see). All 8 screens and the component library are visible in there. Match what's on screen.
>
> Plan your work in this order — do not start coding until you've read everything and proposed a plan:
>
> 1. **Tokens.** Port `tokens.css` to this codebase's styling system. Preserve every CSS variable name; map them 1:1 to whatever theme system this codebase uses (Tailwind theme config, CSS-in-JS theme object, design-token JSON, SwiftUI Color extension, etc.).
> 2. **Primitives.** Port `ds.css` component classes to reusable components in this codebase's framework. Match class names where idiomatic.
> 3. **Map primitives.** Port `map-system.jsx` — the `HexTile`, `Track`, `CityNode`, `River`, `TrainSVG` components and the hex math helpers (`axialToPx`, `hexCorners`, `hexPath`). These are foundational; every screen uses them.
> 4. **Components.** Port `components.jsx` — buttons, badges, chips, panels, dialogs, player cards, HUD, dice, overlays. Each becomes a real component in our codebase.
> 5. **Screens, one at a time.** For each of the 8 screens in `screens.jsx`, build a real page/route in this codebase that matches the design pixel-for-pixel:
>    - `TitleScreen` → `/` (main menu)
>    - `MapViewScreen` → `/game/:id` (map view mid-game)
>    - `BuildTurnScreen` → `/game/:id/build` (active network turn)
>    - `RaceScreen` → `/game/:id/race` (race phase)
>    - `ScoreboardScreen` → `/game/:id/standings`
>    - `ResultsScreen` → `/game/:id/round/:n/results`
>    - `SettingsScreen` → `/settings`
>    - `MapEditorScreen` → `/editor` (map editor — 1440×900 reference size)
> 6. **Theme switching.** Implement light/dark/sepia by setting `data-theme` on the document root. Persist preference.
>
> Constraints:
> - **Do not skip the layout work.** Tokens alone are not a design system. Every screen has a specific 2- or 3-column composition with specific padding, panel chrome, and component placement. Reproduce these.
> - **Use the codebase's existing UI library** (if any) but match the visual treatment from the design — don't lift default Material/Ant/Tailwind UI patterns.
> - **Inline SVGs** for icons, hex glyphs, trains, dice — no icon library substitutions.
> - **Wire up real state** where the design shows it (active player, turn progress, score totals). Use mock data initially if the backend isn't ready; the design files show the shape.
> - **Mobile.** Screens were designed at desktop reference size. Collapse 3-column → 2-column → 1-column responsively.
>
> Before you write code, please give me your plan: which files you'll create, which existing files you'll modify, and your proposed file/folder structure.

---

## Tips for working with Claude Code

- **Watch out for it skipping screens.** It will be tempted to do 1–2 screens then declare victory. Push back: "Now do the next screen." There are 8.
- **Show it the rendered HTML.** Run a local server (`python3 -m http.server 8000 --directory design_handoff_dampfrossdigital`) and tell Claude Code what URL you can see. Or paste screenshots into the chat.
- **Re-read files as needed.** If Claude Code's output drifts from the design, point it back to the specific JSX file for that component/screen.
- **Component naming.** All component class names start with `dr-` (Dampfross). Keep the prefix in your port for traceability.
- **Hex math.** Don't let Claude Code reinvent hex coordinate math — the helpers in `map-system.jsx` are correct (flat-top axial). Use them verbatim.

## What's in this folder

| File | Purpose |
|------|---------|
| `README.md` | Full spec — tokens, screens, components, behavior, accessibility |
| `PROMPT.md` | This file |
| `Design System.html` | **Open this in a browser** to see the actual design — 8 screens + component library + foundations on a zoomable canvas |
| `tokens.css` | Design tokens (colors, type, radii, shadows, motion) |
| `ds.css` | Component CSS classes |
| `foundations.jsx` | Brand cover, colors artboards, type artboards |
| `map-system.jsx` | Hex math + map primitives (HexTile, Track, CityNode, River, TrainSVG) |
| `components.jsx` | UI kit (buttons, panels, dialogs, player cards, HUD, dice) |
| `screens.jsx` | **All 8 sample screens** — TitleScreen, MapViewScreen, BuildTurnScreen, RaceScreen, ScoreboardScreen, ResultsScreen, SettingsScreen, MapEditorScreen |
| `design-canvas.jsx` | Pan-zoom canvas wrapper for the demo — **delete in production** |
| `tweaks-panel.jsx` | Theme switcher for the demo — **delete in production** |
