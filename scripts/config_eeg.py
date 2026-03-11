# -*- coding: utf-8 -*-
"""
EEG channel mapping: AURA ch1–ch8 → 10-20 positions.
Montage: F3, F4, Fz, Cz, Pz, P3, P4, Oz.
"""
from __future__ import annotations

# AURA channel index (0-based) -> 10-20 label
CHANNEL_TO_1020 = [
    "F3",   # ch1 -> index 0
    "F4",   # ch2
    "Fz",   # ch3
    "Cz",   # ch4
    "Pz",   # ch5
    "P3",   # ch6
    "P4",   # ch7
    "Oz",   # ch8
]

# Indices by position (for eeg_adaptive)
F3_IDX = 0
F4_IDX = 1
FZ_IDX = 2
CZ_IDX = 3
PZ_IDX = 4
P3_IDX = 5
P4_IDX = 6
OZ_IDX = 7

# Band definitions (Hz)
BAND_THETA = (4, 8)
BAND_ALPHA = (8, 13)
BAND_BETA = (13, 30)

# Acquisition
SAMPLE_RATE_HZ = 250
WINDOW_DURATION_S = 4.0
WINDOW_SAMPLES = int(SAMPLE_RATE_HZ * WINDOW_DURATION_S)
ADAPTIVE_UPDATE_INTERVAL_S = 2.0

# Bad channel value (AURA uses -375000 for disconnected)
BAD_CHANNEL_VALUE = -375_000
