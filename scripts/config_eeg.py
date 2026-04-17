# -*- coding: utf-8 -*-
"""
EEG channel mapping: AURA ch1–ch8 → 10-20-like positions for `eeg_adaptive.py`.

Default use case (front-only device):
  - Stream order is: `ch1=F1, ch2=Fp1, ch3=Fz, ch4=Fp2, ch5=F2, ch6–ch8=disconnected`.
  - This keeps the EEG pipeline running even if posterior electrodes are not connected.
"""
from __future__ import annotations

# AURA channel index (0-based) -> electrode label used for metrics.
# NOTE: ch6–ch8 are disconnected on your device, so metrics that rely on posterior
# sites will become NaN and be ignored by the adaptive index.
CHANNEL_TO_1020 = [
    "F1",   # ch1 -> index 0
    "Fp1",  # ch2 -> index 1
    "Fz",   # ch3 -> index 2
    "Fp2",  # ch4 -> index 3
    "F2",   # ch5 -> index 4
    "OFF6", # ch6 -> index 5 (disconnected)
    "OFF7", # ch7 -> index 6 (disconnected)
    "OFF8", # ch8 -> index 7 (disconnected)
]

# Indices by position (for eeg_adaptive)
F3_IDX = 0  # use F1 as the "left" frontal site (FAA)
F4_IDX = 4  # use F2 as the "right" frontal site (FAA)
FZ_IDX = 2  # theta uses Fz

# Beta/Alpha ratio uses Fz and an "other frontal reference".
# For your device you selected: average(F1, F2)
BETA_ALPHA_OTHER_IDXS = [F3_IDX, F4_IDX]

# Kept for backward-compatibility with older code paths.
CZ_IDX = BETA_ALPHA_OTHER_IDXS[0]

# Posterior alpha (ideal 10–20): Pz, P3, P4, Oz — often NaN with 5-channel / front-only streams.
PZ_IDX = 5
P3_IDX = 6
P4_IDX = 7
OZ_IDX = 5

# When posterior sites are missing, `eeg_adaptive` averages alpha over these frontal indices instead
# (same 5 slots as ch1–ch5: F1, Fp1, Fz, Fp2, F2).
FRONTAL_ALPHA_FALLBACK_IDXS = [0, 1, 2, 3, 4]

# Band definitions (Hz)
BAND_THETA = (4, 8)
BAND_ALPHA = (8, 13)
BAND_BETA = (13, 30)

# Acquisition
SAMPLE_RATE_HZ = 250
WINDOW_DURATION_S = 4.0
WINDOW_SAMPLES = int(SAMPLE_RATE_HZ * WINDOW_DURATION_S)
ADAPTIVE_UPDATE_INTERVAL_S = 2.0

# Fear-index adaptation: rolling mean (~FEAR_ADAPT_AGGREGATE_S), stress threshold = μ + (pct/100)*max(σ,0.05), dwell
FEAR_ADAPT_AGGREGATE_S = 30.0
FEAR_ADAPT_AGGREGATE_MIN_TICKS = 10
FEAR_ADAPT_BASELINE_SAMPLES = 8
# Timed baseline phase (seconds): GUI sends baseline_calibration_seconds; 0 = legacy sample-count only
FEAR_BASELINE_CALIBRATION_DEFAULT_S = 45.0
FEAR_BASELINE_MIN_SAMPLES = 3
FEAR_ADAPT_STRESS_PCT = 15.0
FEAR_ADAPT_DWELL_S = 8.0

# Bad channel value (AURA uses -375000 for disconnected)
BAD_CHANNEL_VALUE = -375_000
