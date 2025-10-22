#Loading and cache Whisper functions
# backend/models/load_whisper.py
from faster_whisper import WhisperModel
import os

_model = None

def get_model(model_size: str = "tiny.en", device: str = "cpu", compute_type: str = "int8"):
    global _model
    if _model is None:
        # path or model size
        _model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model
