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
- **Alpha suppression:** alpha power (8–13 Hz) at Pz, P3, P4, Oz; less alpha = more engagement → uses `-z(alpha_posterior)`.
- **FAA:** frontal alpha asymmetry (F4−F3)/(F4+F3) in alpha → affective modulator.

Default weights: `w1 = w2 = w3 = w4 = 0.25`. Baseline is estimated from the first windows of the experiment (see `scripts/eeg_adaptive.py`).

---

## Level Adaptation Rules

| Transition | Condition |
|------------|-----------|
| **Level 1 → 2** | `level_suggestion === "up"`: moderate frontal theta, low posterior alpha, index in middle range. Applied after **hysteresis** (2 consecutive suggestions) and **cooldown** (45 s since last change). |
| **Hold (2)** | Index in middle zone; clear physiological response without escalation. |
| **Level 2 or 3 → down** | `level_suggestion === "down"`: high theta/beta-alpha (index above threshold). Applied after hysteresis (2 suggestions) and cooldown (20 s). Also when **High distress** is pressed. |

Server thresholds (in `eeg_adaptive.suggest_level`):  
- Up (1→2): `threshold_low < fear_index < threshold_high` (e.g. −0.3 and 0.8).  
- Down: `fear_index >= threshold_high`.

---

## Technical Flow

1. **aura_recorder.py** reads LSL, keeps a buffer of the last 4 s (1000 samples at 250 Hz).
2. Every 2 s it computes the index with `eeg_adaptive` (bands, baseline, z-scores) and `level_suggestion` ("up" / "hold" / "down").
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
| `scripts/eeg_adaptive.py` | Filters, band powers, FAA, baseline, composite index, `suggest_level()`. |
| `scripts/aura_recorder.py` | Buffer, `adaptive_state` via WebSocket; `manual_level` → `force_level`; optional `--lsl` (VRPhobia_State outlet, VRPhobia_ManualLevel inlet). |
| `scripts/adaptive_monitor_gui.py` | PC GUI: real-time state + Level 1/2/3 buttons via WebSocket. |
| `experiment.html` | Receives `adaptive_state` and `force_level`, level logic, High distress button. |
