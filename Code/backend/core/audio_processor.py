#Spliting chunks, audio processing, convert audio types
# backend/cores/audio_processor.py
import subprocess
import tempfile
import os
from pathlib import Path

def webm_bytes_to_wav_file(webm_bytes: bytes, out_wav_path: str, sample_rate: int = 16000):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as in_f:
        in_f.write(webm_bytes)
        in_f_path = in_f.name

    try:
        # ffmpeg -y -i input.webm -ac 1 -ar 16000 -f wav output.wav
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", in_f_path,
            "-ac", "1",
            "-ar", str(sample_rate),
            "-vn",
            out_wav_path
        ]
        subprocess.run(cmd, check=True)
    finally:
        try:
            os.remove(in_f_path)
        except Exception:
            pass

def combine_wavs(wav_paths, out_path):
    # build file list for ffmpeg
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as list_file:
        for p in wav_paths:
            list_file.write(f"file '{p}'\n")
        list_file_path = list_file.name

    try:
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", list_file_path,
            "-c", "copy", out_path
        ]
        subprocess.run(cmd, check=True)
    finally:
        try:
            os.remove(list_file_path)
        except Exception:
            pass
