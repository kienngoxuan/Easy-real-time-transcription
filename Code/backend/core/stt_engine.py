#STT wrapper
import whisper
model = whisper.load_model("tiny")
result = model.transcribe("abjxc.wav")
print(result["text"])
