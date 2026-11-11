# SotA Assistive HUD Overlay & Telemetry Companion (Refactored)

A modernized, high-performance assistive HUD overlay and telemetry companion for **Shroud of the Avatar** (specifically calibrated for Aeromancer builds and 2560×1440 displays), replacing fragile console rendering with a click-through transparent desktop overlay, asynchronous OpenCV/Tesseract processing, and an interactive web telemetry suite.

---

## User Review & Critical Decisions

> [!IMPORTANT]
> Based on your 20 development screenshots and confirmed preferences, the following architecture and design decisions are incorporated:
> - **Zero Terminal Crashes**: Resolves the `AttributeError: 'os.terminal_size' object has no attribute 'rows'` crash (terminal sizes use `.lines` and `.columns`) and eliminates `os.system('cls')` screen jitter by replacing the terminal with a native transparent HUD overlay.
> - **Exact Buff Icon Templates Matched**: Direct integration of the 6 extracted buff icons from your screenshots:
>   - `airs_embrace.png` (Air's Embrace – swirl over hands)
>   - `shield_of_air.png` (Shield of Air – radiant golden silhouette)
>   - `dash.png` (Dash – running golden athlete)
>   - `blessing_of_honor.png` (Devotional of Honor – flame altar)
>   - `blessing_of_sacrifice.png` (Devotional of Sacrifice – water bowl)
>   - `blessing_of_theurgy.png` (Devotional of Theurgy – winged chalice)
> - **In-Game Visual Grounding**: Calibrated to your live 2560×1440 gameplay screenshot:
>   - Character: **Hyperlight Drifter** (Adventurer Level 131, Pool ~128.2M, Dual-Spec 77 Air / 66 Focus)
>   - Left-edge Stats Panel: Real-time encumbrance warning (Weight 1,185.1 / 1,018.7) and Durability alerts (Weapon 43.6% < 50%, Armor 26.8%)
>   - TotA Meter / TotA Mater 1.0.0 integration: Adv XP tracking, DPS, and pool synchronization
>   - Active skill leak warning for `Draw Strength` (144) and `Shield of Air` (153) still set to `Training` despite being >131.
> - **Unobtrusive Compact HUD Badges**: Non-intrusive floating badges with subtle radial progress rings and clean numerical timers that automatically hide when nominal and glow gently when attention is required.
> - **Click-Through Windows Overlay**: Python overlay built with PySide6/PyQt6 (with Win32 `WS_EX_TRANSPARENT | WS_EX_LAYERED` click-through window styles) ensuring you can click right through the HUD into the game without losing focus or key inputs.

---

## 1. Overview & Core Concept

The existing tracker script provided essential math and telemetry, but suffered from three major limitations:
1. **Console Flaws & Crashing**: It relied on console clearing (`os.system('cls')`) which flickered violently, and failed under PyInstaller or Windows Terminal due to `shutil.get_terminal_size().rows`.
2. **Main Thread Blocking**: Screen grabbing (`ImageGrab.grab()`), OpenCV template matching, and Tesseract OCR were executed sequentially on the main thread, causing frame drops and input lag.
3. **Lack of In-Game Glanceability**: Requiring a second monitor or Alt-Tabbing to check terminal logs broke combat focus.

The refactored solution provides:
1. **A Modular Python Desktop Overlay Application** (`sota_overlay/`):
   - Transparent, click-through, always-on-top HUD window using hardware-accelerated rendering.
   - Dedicated background threads for non-blocking combat log tailing and adaptive OCR/template matching.
   - Smooth badge animations and gentle audio chimes (optional) when buffs drop or durability drops below 50%.
2. **An Interactive Web Studio Companion** (built into this app):
   - Live visualizer of the HUD overlay in full 2560×1440 resolution.
   - Live log simulator allowing you to test combat log scenarios, verify 1.0615/1.10 XP curves, and audit skill training states.
   - ROI calibration tool for custom screen layouts.
   - Full code export panel to copy or download the entire modular Python package ready for PyInstaller bundling.

---

## 2. User Experience & Visual Design

### Key User Flows
1. **In-Game Overlay View (Transparent HUD)**:
   - **Buff Watcher Strip**: Compact 36×36px icon badges for Air's Embrace, Shield of Air, Dash, and Devotionals. When active, displays a discrete ring timer; when a buff drops, it pulses amber and displays a 1-line guidance banner before fading to a subtle ghost state.
   - **Dual-Spec Progress Capsule**: Clean, unboxed text display showing `Air Spec: Lvl 77 (186,616 XP to 78)` and `Focus Spec: Lvl 66 (96,790 XP to 67)` with a compact `143 / 160` combined dual-cap bar.
   - **Smart Warning Badges (Dynamic Visibility)**:
     - *Overencumbered Badge*: Appears in amber/red when current weight > max weight (e.g., `1,185.1 / 1,018.7`). Completely hidden when unencumbered.
     - *Durability Warning Badge*: Appears when weapon or armor effectiveness is below 50% (e.g., `Weapon: 43.6% - Repair Soon!`). Hidden when gear is healthy.
     - *XP Leak Alert*: Flashes when chat log records XP gained towards skills already $\ge 131$ (e.g., Draw Strength at 144).
2. **Interactive Web Companion Studio**:
   - **Screen Calibrator**: Displays your actual 2560×1440 game screenshot with adjustable bounding boxes for `BUFF_BAR_ROI`, `STATS_PANEL_ROI`, and `TOTA_METER_ROI`.
   - **Log Telemetry & Parser Lab**: Real-time log inspector supporting drag-and-drop of `SotAChatLog_*.txt` files with automated midnight rollover testing.
   - **Python Source Hub**: Inspect and copy each modular script (`config.py`, `xp_math.py`, `ocr_worker.py`, `buff_engine.py`, `overlay_gui.py`, `main.py`).

### Visual Identity & Theme
- **Aesthetic Direction**: High-precision tactical gaming HUD with anti-slop design. No floating card sandwiches or garish pill badges.
- **Color Palette (60-30-10)**:
  - *Canvas (60%)*: Transparent / Deep Slate (`#0B0F19` with subtle blur)
  - *Structural Borders (30%)*: Hairline slate borders (`rgba(255,255,255,0.08)`)
  - *Semantic Accents (10%)*:
    - Air Spec Electric Cyan: `#38BDF8`
    - Focus Spec Arcane Violet: `#C084FC`
    - Nominal / Active Green: `#10B981`
    - Warning Amber: `#F59E0B`
    - Overencumbered / Leak Crimson: `#EF4444`
- **Typography**: Clean display sans (`Plus Jakarta Sans`) paired with monospace tabular numerals (`JetBrains Mono`, `tabular-nums`) for zero-jitter XP and rate readouts.

---

## 3. Key Product Decisions & Trade-Offs

### Decision 1: Threaded Pipeline vs. Monolithic Polling
- *Chosen Approach*: Decouple into three distinct workers:
  1. `LogWatcherThread`: Fast non-blocking line generator tailing the active chat log (polling every 100ms).
  2. `VisionWorkerThread`: Throttled background thread (running every 1.5–2s) capturing only small sub-ROIs rather than full 4K/1440p bitmaps to save CPU.
  3. `OverlayUIThread`: 60 FPS transparent Qt / Tkinter window that only receives state update events via a queue.
- *Why*: Eliminates the 2-second stuttering and terminal locks seen in the original script.

### Decision 2: Compact Unobtrusive Badges over Bulky Tables
- *Chosen Approach*: Floating micro-badges that remain 80% transparent until an alert fires (e.g. buff drops, durability <50%, or weight exceeded), at which point they glow cleanly with a compact label.
- *Why*: In SotA endgame combat, screen real estate is critical. Full tables block hostile targeting and ground telegraphs.

### Decision 3: Robust Log Rollover & Error Handling
- *Chosen Approach*: Implement a file descriptor watcher that checks for newly created `SotAChatLog_*.txt` files at midnight and cleanly switches handles without dropping state or throwing exceptions.

---

## 4. Technical Architecture & Data Strategy

```
┌────────────────────────────────────────────────────────────────────────┐
│               SotA Assistive In-Game Overlay Architecture              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   ┌───────────────────────┐          ┌─────────────────────────────┐   │
│   │   LogWatcherThread    │          │     VisionWorkerThread      │   │
│   │ ───────────────────── │          │ ─────────────────────────── │   │
│   │ • Non-blocking tail   │          │ • Throttled ROI grab        │   │
│   │ • Midnight rollover   │          │ • OpenCV template matching  │   │
│   │ • XP & leak regex     │          │ • Tesseract stats/meter OCR │   │
│   └──────────┬────────────┘          └──────────────┬──────────────┘   │
│              │                                      │                  │
│              ▼                                      ▼                  │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                 TelemetryState (Thread-Safe)                   │   │
│   │ • Air Spec: 77 -> 78 (XP & ETA)  • Banked Pool: ~128.2M        │   │
│   │ • Focus Spec: 66 -> 67 (XP & ETA)• Buff States & Timers        │   │
│   │ • Adv Lvl 131 -> 132 ETA         • Durability & Encumbrance    │   │
│   └──────────────────────────────┬─────────────────────────────────┘   │
│                                  │                                     │
│                                  ▼                                     │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │           Transparent In-Game HUD Overlay (PyQt6 / Web)        │   │
│   │ ────────────────────────────────────────────────────────────── │   │
│   │ • WS_EX_TRANSPARENT | WS_EX_LAYERED (Click-Through)            │   │
│   │ • Compact Buff Badges (Air's Embrace, Shield, Dash, Devotions) │   │
│   │ • Smart Warning Badges (Overencumbered, Low Durability <50%)   │   │
│   │ • Dual-Spec Cap Meter (143/160) & Pace Telemetry               │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### Modular Code Structure (for Desktop Package)
- `sota_overlay/`
  - `config.py`: Calibrated 2560×1440 ROIs, template match thresholds, baseline stats.
  - `xp_math.py`: Pre-100 / post-100 marginal XP formulas, dual-spec cap progress, ETAs.
  - `log_parser.py`: Zero-CPU tailer with daily rollover and XP leak detection.
  - `vision.py`: OpenCV multi-template matcher and PyTesseract OCR with fallback image pre-processing.
  - `overlay.py`: Hardware-accelerated transparent click-through window with compact badges.
  - `main.py`: Application coordinator with clean CLI options and crash-safe error reporting.
