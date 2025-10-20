Front-end:
- Choosing micro/start/stop button
- Transcription area
- Summary area

Backend:
- Structure:
    - Audio input layer: mic
    - STT engine: Whisper/Vosk or Call api from server (have to use FastAPI)
    - Processing audio chunk (Queue || Sliding window)
    - Summariztion engine: LLM

Challenge (latency < 2s>):
    - Multi lang: OpenAI whisper
    - Whisper-tiny for real-time
    - WebSocket pipeline for recognizing chunk audio
    
Real-time summarization:
    - Fastest STT model (using GPU)
    - mini-window (3-5 sentences) -> put into model waiting queue then summary all (has to think)
    - incremental summarization ??

Suggested model:
    - Backend: Python (FastAPI, WebSocket)
    - Queue Layer: Redis Stream
    - Frontend: Streamlit
    - Model Serving: Hugging Face Transformers + TorchServe / OpenAI Realtime API


Optimization:
    - Optimize chunk size and catching