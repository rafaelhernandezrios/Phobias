#!/usr/bin/env python3
"""
Simulador de AURA para pruebas sin casco real.

Publica un stream LSL con nombre "AURA" y 8 canales (F3, F4, Fz, Cz, Pz, P3, P4, Oz)
con datos sintéticos a 250 Hz, para que `aura_recorder.py` y `aura_test.py`
puedan conectarse sin necesidad del dispositivo físico.
"""

import math
import random
import socket
import os
import sys
import time
from datetime import datetime

try:
    from pylsl import StreamInfo, StreamOutlet, local_clock
except ImportError:
    print("Error: pylsl no está instalado. Ejecuta: pip install pylsl")
    sys.exit(1)


STREAM_NAME = "AURA"
STREAM_TYPE = "EEG"
CHANNEL_COUNT = 8  # F3, F4, Fz, Cz, Pz, P3, P4, Oz
SAMPLE_RATE_HZ = 250  # coincide con config_eeg.SAMPLE_RATE_HZ
CHANNEL_LABELS = ["F3", "F4", "Fz", "Cz", "Pz", "P3", "P4", "Oz"]


def create_stream(stream_name: str, source_id: str) -> StreamOutlet:
    info = StreamInfo(
        stream_name,
        STREAM_TYPE,
        CHANNEL_COUNT,
        SAMPLE_RATE_HZ,
        "float32",
        source_id,
    )

    # Añadir metadatos mínimos (no es estrictamente necesario para que el recorder funcione)
    chns = info.desc().append_child("channels")
    for label in CHANNEL_LABELS:
        ch = chns.append_child("channel")
        ch.append_child_value("label", label)
        ch.append_child_value("unit", "uV")
        ch.append_child_value("type", "EEG")

    outlet = StreamOutlet(info)
    return outlet


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="AURA LSL simulator (8ch @ 250Hz)")
    parser.add_argument("--name", default=STREAM_NAME, help="LSL stream name (default: AURA)")
    parser.add_argument(
        "--source-id",
        default=None,
        help="LSL source_id (helps avoid ambiguity when multiple streams have same name)",
    )
    args = parser.parse_args()

    stream_name = args.name

    host = socket.gethostname()
    pid = os.getpid()
    source_id = args.source_id or f"AURA_SIMULATOR_{host}_{pid}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    print("=== AURA Simulator (LSL) ===")
    print(f"Publicando stream LSL con nombre '{stream_name}' ({CHANNEL_COUNT} canales, {SAMPLE_RATE_HZ} Hz)")
    print(f"source_id: {source_id}")
    print("Canales:", ", ".join(CHANNEL_LABELS))
    print("Usa este simulador junto con aura_recorder.py y la app de experimento.")
    print("Para detenerlo, presiona Ctrl+C.\n")

    outlet = create_stream(stream_name, source_id)

    start_time = local_clock()
    phase = 0.0
    noise_level = 5.0  # microvoltios aproximados

    try:
        while True:
            now = local_clock()
            t = now - start_time

            # Señales sintéticas diferentes por canal (seno/cos con distintas fases)
            base_freq = 10.0  # ~10 Hz banda alfa
            sample = []
            for i in range(CHANNEL_COUNT):
                ch_phase = phase + i * 0.5
                value = 20.0 * math.sin(2 * math.pi * base_freq * t + ch_phase)
                value += random.gauss(0.0, noise_level)
                sample.append(float(value))

            outlet.push_sample(sample)

            # Avanzar fase y dormir para aproximar 250 Hz
            phase += 0.01
            time.sleep(1.0 / SAMPLE_RATE_HZ)
    except KeyboardInterrupt:
        print("\nSimulador detenido por el usuario.")


if __name__ == "__main__":
    main()

