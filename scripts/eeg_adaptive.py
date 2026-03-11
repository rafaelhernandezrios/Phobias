# -*- coding: utf-8 -*-
"""
Fear/Engagement index from EEG band powers.
Input: windows of (n_samples, 8) in order F3, F4, Fz, Cz, Pz, P3, P4, Oz.
"""
from __future__ import annotations

import numpy as np

try:
    from scipy.signal import butter, filtfilt
except ImportError:
    butter = filtfilt = None

from config_eeg import (
    BAND_ALPHA,
    BAND_BETA,
    BAND_THETA,
    BAD_CHANNEL_VALUE,
    CZ_IDX,
    F3_IDX,
    F4_IDX,
    FZ_IDX,
    OZ_IDX,
    P3_IDX,
    P4_IDX,
    PZ_IDX,
    SAMPLE_RATE_HZ,
)


def _bandpass(data: np.ndarray, low: float, high: float, fs: float) -> np.ndarray:
    if butter is None or filtfilt is None:
        return data
    nyq = fs / 2
    low = max(0.5, min(low, nyq - 0.5))
    high = min(high, nyq - 0.5)
    if low >= high:
        return data
    b, a = butter(4, [low / nyq, high / nyq], btype="band")
    out = np.zeros_like(data)
    for ch in range(data.shape[1]):
        x = np.asarray(data[:, ch], dtype=np.float64)
        if np.any(np.isnan(x)):
            out[:, ch] = np.nan
            continue
        out[:, ch] = filtfilt(b, a, x)
    return out


def _power(channel_signal: np.ndarray) -> float:
    x = np.asarray(channel_signal, dtype=np.float64)
    x = x[~np.isnan(x)]
    if len(x) < 10:
        return np.nan
    return float(np.mean(x ** 2))


def _safe_mean_power(data: np.ndarray, ch_indices: list[int], band: tuple[float, float]) -> float:
    fs = SAMPLE_RATE_HZ
    banded = _bandpass(data, band[0], band[1], fs)
    powers = []
    for i in ch_indices:
        p = _power(banded[:, i])
        if not np.isnan(p):
            powers.append(p)
    return float(np.mean(powers)) if powers else np.nan


def _replace_bad_channels(data: np.ndarray) -> np.ndarray:
    out = np.array(data, dtype=np.float64, copy=True)
    out[out <= BAD_CHANNEL_VALUE * 1.1] = np.nan
    return out


def compute_theta_fz(data: np.ndarray) -> float:
    data = _replace_bad_channels(data)
    return _safe_mean_power(data, [FZ_IDX], BAND_THETA)


def compute_beta_alpha_ratio_fz_cz(data: np.ndarray) -> float:
    data = _replace_bad_channels(data)
    beta = _safe_mean_power(data, [FZ_IDX, CZ_IDX], BAND_BETA)
    alpha = _safe_mean_power(data, [FZ_IDX, CZ_IDX], BAND_ALPHA)
    if np.isnan(beta) or np.isnan(alpha) or alpha < 1e-20:
        return np.nan
    return float(beta / alpha)


def compute_alpha_suppression_posterior(data: np.ndarray) -> float:
    """Mean alpha power over Pz, P3, P4, Oz. 'Suppression' = we use raw power; higher engagement -> lower alpha."""
    data = _replace_bad_channels(data)
    return _safe_mean_power(data, [PZ_IDX, P3_IDX, P4_IDX, OZ_IDX], BAND_ALPHA)


def compute_faa(data: np.ndarray) -> float:
    """Frontal alpha asymmetry: (alpha_F4 - alpha_F3) / (alpha_F4 + alpha_F3)."""
    data = _replace_bad_channels(data)
    a3 = _safe_mean_power(data, [F3_IDX], BAND_ALPHA)
    a4 = _safe_mean_power(data, [F4_IDX], BAND_ALPHA)
    if np.isnan(a3) or np.isnan(a4) or (a3 + a4) < 1e-20:
        return np.nan
    return float((a4 - a3) / (a4 + a3))


class BaselineStats:
    """Collects first N windows to compute mean/std for z-scoring."""
    MAX_SAMPLES = 20

    def __init__(self) -> None:
        self.theta_fz_mean: float = 0.0
        self.theta_fz_std: float = 1.0
        self.beta_alpha_mean: float = 0.0
        self.beta_alpha_std: float = 1.0
        self.alpha_post_mean: float = 0.0
        self.alpha_post_std: float = 1.0
        self.faa_mean: float = 0.0
        self.faa_std: float = 1.0
        self._theta: list[float] = []
        self._ba: list[float] = []
        self._ap: list[float] = []
        self._faa: list[float] = []
        self._finalized = False

    def update(self, theta_fz: float, beta_alpha: float, alpha_post: float, faa: float) -> None:
        if self._finalized or (np.isnan(theta_fz) and np.isnan(beta_alpha) and np.isnan(alpha_post) and np.isnan(faa)):
            return
        if not np.isnan(theta_fz):
            self._theta.append(theta_fz)
        if not np.isnan(beta_alpha):
            self._ba.append(beta_alpha)
        if not np.isnan(alpha_post):
            self._ap.append(alpha_post)
        if not np.isnan(faa):
            self._faa.append(faa)
        total = len(self._theta) + len(self._ba) + len(self._ap) + len(self._faa)
        if total >= self.MAX_SAMPLES * 2:
            self._finalize()

    def _finalize(self) -> None:
        if self._finalized:
            return
        if len(self._theta) >= 3:
            self.theta_fz_mean = float(np.mean(self._theta))
            self.theta_fz_std = max(1e-10, float(np.std(self._theta)))
        if len(self._ba) >= 3:
            self.beta_alpha_mean = float(np.mean(self._ba))
            self.beta_alpha_std = max(1e-10, float(np.std(self._ba)))
        if len(self._ap) >= 3:
            self.alpha_post_mean = float(np.mean(self._ap))
            self.alpha_post_std = max(1e-10, float(np.std(self._ap)))
        if len(self._faa) >= 3:
            self.faa_mean = float(np.mean(self._faa))
            self.faa_std = max(1e-10, float(np.std(self._faa)))
        self._finalized = True

    def z_score(self, theta_fz: float, beta_alpha: float, alpha_post: float, faa: float) -> tuple[float, float, float, float]:
        z_theta = (theta_fz - self.theta_fz_mean) / self.theta_fz_std if not np.isnan(theta_fz) else 0.0
        z_ba = (beta_alpha - self.beta_alpha_mean) / self.beta_alpha_std if not np.isnan(beta_alpha) else 0.0
        z_ap = (alpha_post - self.alpha_post_mean) / self.alpha_post_std if not np.isnan(alpha_post) else 0.0
        z_faa = (faa - self.faa_mean) / self.faa_std if not np.isnan(faa) else 0.0
        return z_theta, z_ba, z_ap, z_faa


# Weights for composite index (w1..w4)
WEIGHT_THETA = 0.25
WEIGHT_BETA_ALPHA = 0.25
WEIGHT_ALPHA_SUPPRESSION = 0.25
WEIGHT_FAA = 0.25


def compute_fear_engagement_index(
    data: np.ndarray,
    baseline: BaselineStats,
) -> tuple[float, dict]:
    """
    data: (n_samples, 8) in order F3, F4, Fz, Cz, Pz, P3, P4, Oz.
    Returns (fear_index, metrics_dict).
    """
    theta_fz = compute_theta_fz(data)
    beta_alpha = compute_beta_alpha_ratio_fz_cz(data)
    alpha_post = compute_alpha_suppression_posterior(data)
    faa = compute_faa(data)

    z_theta, z_ba, z_ap, z_faa = baseline.z_score(theta_fz, beta_alpha, alpha_post, faa)

    # Alpha suppression: lower alpha = more engagement; we want positive z when alpha is LOW.
    # So we use -z_ap so that "less alpha" -> positive contribution to fear/engagement.
    z_alpha_suppression = -z_ap

    fear_index = (
        WEIGHT_THETA * z_theta
        + WEIGHT_BETA_ALPHA * z_ba
        + WEIGHT_ALPHA_SUPPRESSION * z_alpha_suppression
        + WEIGHT_FAA * z_faa
    )

    metrics = {
        "theta_fz": float(theta_fz) if not np.isnan(theta_fz) else None,
        "beta_alpha_fz_cz": float(beta_alpha) if not np.isnan(beta_alpha) else None,
        "alpha_posterior": float(alpha_post) if not np.isnan(alpha_post) else None,
        "faa": float(faa) if not np.isnan(faa) else None,
        "z_theta": z_theta,
        "z_beta_alpha": z_ba,
        "z_alpha_suppression": z_alpha_suppression,
        "z_faa": z_faa,
    }
    return float(fear_index), metrics


def suggest_level(
    fear_index: float,
    current_level: int,
    *,
    threshold_low: float = -0.3,
    threshold_high: float = 0.8,
) -> str:
    """
    Returns "up", "hold", or "down".
    - up: level 1 -> 2 when index in moderate range (above threshold_low, below threshold_high).
    - down: level 2 or 3 -> lower when index too high (above threshold_high) or user reported distress.
    - hold: otherwise.
    """
    if current_level == 1:
        if threshold_low < fear_index < threshold_high:
            return "up"
        return "hold"
    if current_level >= 2:
        if fear_index >= threshold_high:
            return "down"
        return "hold"
    return "hold"
