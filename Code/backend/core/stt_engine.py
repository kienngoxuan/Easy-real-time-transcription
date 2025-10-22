"""STT wrapper (safe import)
This module intentionally does NOT load the model at import time. Use
load_whisper_model() to load and cache a model object, and transcribe_file()
to run transcription.
"""
from typing import Any, Optional

_model: Optional[Any] = None

def load_whisper_model(name: str = "tiny") -> Any:
	"""Load and cache a Whisper model by name. Returns the model object."""
	global _model
	if _model is None:
		try:
			import whisper
			_model = whisper.load_model(name)
		except Exception:
			_model = None
			raise
	return _model

def transcribe_file(path: str) -> str:
	"""Transcribe a local audio file using the loaded model. Raises if model not loaded."""
	if _model is None:
		raise RuntimeError("model not loaded, call load_whisper_model() first")
	res = _model.transcribe(path)
	return res.get("text", "")
