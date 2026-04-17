# EEG Adaptive Levels — Fear/Engagement Index

System for adapting exposure level (1–3) based on real-time EEG signal.

---

## 10–20 Montage (8 Electrodes)

Recommended configuration for AURA (ch1–ch8):

| AURA channel | 10–20 position | Use |
|--------------|----------------|-----|
| ch1          | F3             | Frontal alpha asymmetry (FAA) |
| ch2          | F4             | Frontal alpha asymmetry (FAA) |
| ch3          | Fz             | Frontal theta, beta/alpha |
| ch4          | Cz             | Beta/alpha (support) |
| ch5          | Pz             | Posterior alpha / suppression |
| ch6          | P3             | Posterior alpha |
| ch7          | P4             | Posterior alpha |
| ch8          | Oz             | Posterior alpha / visual attention |

**Functional blocks:**
- **Frontal (F3, F4, Fz):** emotional regulation, anxiety, FAA.
- **Midline (Fz, Cz, Pz):** stable state tracking.
- **Posterior (Pz, P3, P4, Oz):** visual attention and perceptual load in VR.

---

## Fear/Engagement Index

Composite index (z-scores over baseline):

```
Fear/Engagement = w1·z(θ_Fz) + w2·z(β/α)_Fz,Cz + w3·z(AlphaSuppression) + w4·z(FAA)
```

- **θ Fz:** theta power (4–8 Hz) at Fz → vigilance, cognitive control, anxiety.
- **β/α Fz,Cz:** beta/alpha ratio at Fz and Cz → activation/arousal.
- **Alpha suppression:** alpha power (8–13 Hz) at Pz, P3, P4, Oz; less alpha = more engagement → uses `-z(alpha_posterior)`. **5-channel mode:** posterior columns are missing → code uses **mean frontal alpha** (`FRONTAL_ALPHA_FALLBACK_IDXS`: F1, Fp1, Fz, Fp2, F2) as proxy so all four weights still apply.
- **FAA:** frontal alpha asymmetry (F4−F3)/(F4+F3) in alpha → affective modulator.

Default weights: `w1 = w2 = w3 = w4 = 0.25`. Baseline is estimated from the first windows of the experiment (see `scripts/eeg_adaptive.py`).

---

## Level Adaptation Rules

Adaptation uses the **same Fear/Engagement composite index**. **Level suggestions** use one **stress threshold** derived from the calibration mean and **dwell time** above/below that line (see `eeg_adaptive.tick_dwell_and_suggest`).

### Timed baseline (recommended)

GUI sends **`baseline_calibration_seconds`** (e.g. **45**) in `controller_start`. **0** disables this and uses the legacy rule below.

| Step | What happens |
|------|----------------|
| **Calibration phase** | While **elapsed &lt; baseline_calibration_seconds**, only **collect** instantaneous `fear_index` into the calibration buffer. **`level_suggestion`** is always **hold**; payload **`adaptive_phase`: `"calibration"`**, **`baseline_remaining_s`**. No rolling aggregate or dwell yet. |
| **End of calibration** | Compute `μ_ref`, `σ_ref` from **all** samples collected in that window. Clear dwell counters and the rolling ring. If **current level is 0**, the server sets **level 1** and broadcasts **`force_level`**. |
| **Adaptation phase** | Rolling **`agg`**, stress line; **dwell only for "down"** (sustained stress). **"up"** when `agg < threshold` every tick (calm); VR applies hysteresis/cooldown. Payload **`adaptive_phase`: `"adaptation"`**. |

### Legacy ( `baseline_calibration_seconds` = 0 )

| Step | What happens |
|------|----------------|
| **Calibration** | First **`FEAR_ADAPT_BASELINE_SAMPLES`** (8) updates store `fear_index`; then `μ_ref`, `σ_ref`. No timed phase; level is **not** auto-advanced. |
| **Stress threshold** | `fear_stress_threshold(μ_ref, σ_ref)` = **`μ_ref + (FEAR_ADAPT_STRESS_PCT/100)·max(σ_ref, 0.05)`** — additive above the calibration mean in σ units (works for negative μ; multiplicative `μ·(1+pct)` was wrong for signed indices). |
| **Aggregate** | Rolling mean of `fear_index` over the last ~`FEAR_ADAPT_AGGREGATE_S` (30 s), requiring at least `FEAR_ADAPT_AGGREGATE_MIN_TICKS` samples in the buffer (`agg`). |
| **Dwell** | **`agg ≥ threshold`:** add time to **dwell_above**; when it reaches **`FEAR_ADAPT_DWELL_S`** (default 8 s) → **down**. **`agg < threshold`:** emit **up** each tick (no calm dwell); reset **dwell_above**. |

| Transition | Condition |
|------------|-----------|
| **Level down** | `level_suggestion === "down"` after `agg` stayed **≥ stress threshold** for **FEAR_ADAPT_DWELL_S** (and level &gt; 0). VR may still throttle. |
| **Level up** | `level_suggestion === "up"` whenever **`agg < threshold`** (and level &lt; 5). Browser/VR uses **2× consecutive "up"** + **cooldown** before changing level. |
| **Hold** | `agg ≥ threshold` but dwell not long enough yet for **down**, or missing calibration/**agg**, or level at boundary. |

Constants: `scripts/config_eeg.py` (`FEAR_ADAPT_STRESS_PCT`, `FEAR_ADAPT_DWELL_S`, aggregate settings). Payload: `fear_index_aggregate`, `fear_ref_mean`, `fear_ref_std`, `fear_stress_threshold`, `dwell_above_s`, `dwell_below_s`.

The helper `suggest_level(fear, level)` in `eeg_adaptive.py` is a **legacy** fixed z-band test only (`−0.3` … `0.8` on a global scale); the recorder uses **dwell + % threshold** above.

---

## Technical Flow

1. **aura_recorder.py** reads LSL, keeps a buffer of the last 4 s (1000 samples at 250 Hz).
2. Every 2 s it computes the index with `eeg_adaptive` (bands, baseline, z-scores), updates fear-index calibration if needed, pushes into the rolling aggregate, and computes `level_suggestion` ("up" / "hold" / "down").
3. Sends to all clients via WebSocket: `{ type: "adaptive_state", fear_index, level_suggestion, current_level, metrics }`.
4. **experiment.html** receives the message, updates the HUD (index) and applies a level change only if hysteresis and cooldown are satisfied.
5. The **High distress** button lowers the level immediately and notifies the server with `level_change`.

---

## PC Monitor and Manual Control

- **Graphical interface (PC):** run `python scripts/adaptive_monitor_gui.py` to see the adaptive state (fear index, suggestion, metrics) in real time and change the level manually with the Level 1/2/3 buttons (sends `manual_level` via WebSocket to the recorder, which forwards `force_level` to the browser).
  - If the experiment uses HTTPS: `python scripts/adaptive_monitor_gui.py --wss`
  - Options: `--host`, `--port`, `--wss`
- **LSL (optional):** with `python scripts/aura_recorder.py --wss --lsl`:
  - The recorder publishes state to the LSL stream **VRPhobia_State** (channels: fear_index, current_level) so other apps (e.g. LabRecorder) can record it.
  - The recorder listens to the **VRPhobia_ManualLevel** stream: if another app sends samples with value 1, 2, or 3, the level in VR is updated (same as with the GUI buttons).

---

## Files

| File | Content |
|------|---------|
| `scripts/config_eeg.py` | ch1–ch8 to 10–20 mapping, constants (bands, window, interval). |
| `scripts/eeg_adaptive.py` | Filters, band powers, FAA, baseline, composite index, `fear_stress_threshold()`, `tick_dwell_and_suggest()`, legacy `suggest_level()`. |
| `scripts/aura_recorder.py` | Buffer, `adaptive_state` via WebSocket; `manual_level` → `force_level`; optional `--lsl` (VRPhobia_State outlet, VRPhobia_ManualLevel inlet). |
| `scripts/adaptive_monitor_gui.py` | PC GUI: real-time state + Level 1/2/3 buttons via WebSocket. |
| `experiment.html` | Receives `adaptive_state` and `force_level`, level logic, High distress button. |
