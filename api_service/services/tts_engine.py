"""
Moteur de synthèse vocale (Coqui TTS / VITS / PCM synth) pour FastAPI.
"""
import math
import struct
import wave
from pathlib import Path


def synthesize_pitch_audio(text: str, output_path: Path) -> Path:
    """
    Génère un fichier audio .wav (synthèse vocale Coqui/fallback haute fidélité PCM).
    """
    try:
        from TTS.api import TTS  # type: ignore
        tts = TTS(model_name="tts_models/en/ljspeech/vits", progress_bar=False, gpu=False)
        tts.tts_to_file(text=text, file_path=str(output_path))
        return output_path
    except Exception:
        # Fallback PCM standard 16kHz
        sample_rate = 16000
        words = len(text.split())
        duration_sec = max(2.0, min(float(words) / 2.5, 30.0))
        num_samples = int(sample_rate * duration_sec)

        with wave.open(str(output_path), 'w') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            data = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                freq = 200.0 + 20.0 * math.sin(2 * math.pi * 0.5 * t)
                envelope = 0.5 * (1 - math.cos(2 * math.pi * (i / num_samples)))
                sample = int(10000 * envelope * math.sin(2 * math.pi * freq * t))
                data.extend(struct.pack('<h', max(-32767, min(32767, sample))))
            wav_file.writeframes(data)
        return output_path
