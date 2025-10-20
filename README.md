
# Easy Real-Time Transcription

Lightweight prototype for real-time audio capture, transcription (Whisper), and summarization. This repository contains a Streamlit frontend (microphone widget + local speech recognition demo) and a Python backend scaffold (FastAPI) with a Whisper-based STT wrapper and placeholder summarization components.

This README is generated from the project files in the workspace and describes how to run and develop the project locally.

## Quick facts

- Language: Python
- Frontend: Streamlit (prototype: `Code/frontend/app.py`)
- Backend: FastAPI (scaffold: `Code/backend/main.py`, API under `Code/backend/api/`)
- STT: OpenAI/Whisper (wrapper at `Code/backend/core/stt_engine.py`)
- Docker files: `Code/docker/`

## Repository layout

- Code/
	- backend/
		- main.py                # FastAPI entrypoint (placeholder)
		- config.py
		- requirements.txt      # backend Python dependencies
		- api/
			- __init__.py
			- rest.py             # REST API endpoints (app-specific)
			- websocket.py        # WebSocket handling (receive audio stream from frontend)
		- core/
			- stt_engine.py       # Whisper wrapper (tiny model in example)
			- audio_processor.py
			- redis_queue.py
			- summarization_engine.py
			- summarization_worker.py
		- models/
			- load_whisper.py
			- load_summary_model.py
		- utils/
			- chunk_utils.py
			- logger.py
			- timer.py
	- frontend/
		- app.py                 # Streamlit demo with microphone widget + client-side Web Speech API
		- websocket_client.py
		- requirements.txt       # frontend dependencies
	- docker/
		- Dockerfile.backend
		- Dockerfile.frontend
		- docker-compose.yml

Other top-level files: `LICENSE`, `README.md`, and a `Roadmap/` directory with notes.

## What this project contains (short)

- A Streamlit-based frontend demo (`Code/frontend/app.py`) that embeds a browser widget to record audio, show live transcription (via the browser SpeechRecognition API where available), and download recorded audio.
- A backend scaffold with a Whisper-based STT wrapper in `Code/backend/core/stt_engine.py`. The example in that file shows loading the `tiny` Whisper model and transcribing a local WAV file.
- Docker and docker-compose files to containerize frontend and backend (experimental in this repo).

## Requirements

- Python 3.10+ recommended
- pip for package installation
- For Whisper model use: enough disk space to download model weights. For CPU-only systems, transcription will be slower. A CUDA-enabled GPU and torch with CUDA greatly speeds up Whisper.

## Backend — running locally

1. Create and activate a virtual environment (PowerShell example):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install backend dependencies:

```powershell
pip install -r Code/backend/requirements.txt
```

3. Start the FastAPI server (example using uvicorn). The project entrypoint is `Code/backend/main.py`.

```powershell
pip install uvicorn[standard]
uvicorn Code.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Notes:
- `Code/backend/api/websocket.py` is where the real-time audio WebSocket handling should be implemented. Right now the file contains a short comment describing its purpose.
- `Code/backend/core/stt_engine.py` contains a minimal example using Whisper's Python bindings. It currently loads the `tiny` model and transcribes a static file; adapt it to accept in-memory audio chunks or streamed audio for real-time use.

## Frontend — running locally (Streamlit)

The frontend demo is a Streamlit app that embeds a microphone widget and the Web Speech API for live client-side transcription.

1. (Optional) Create and activate a virtual environment for the frontend.
2. Install frontend dependencies:

```powershell
pip install -r Code/frontend/requirements.txt
```

3. Run the Streamlit app:

```powershell
streamlit run Code/frontend/app.py
```

Open the URL Streamlit prints (usually http://localhost:8501). The microphone widget uses the browser APIs; ensure the browser has microphone permissions.

Notes:
- The current frontend demo uses the browser's Web Speech API for quick transcription; this is a fallback for demos and does not send audio to the backend. To enable real-time server-side transcription, implement a WebSocket client (`Code/frontend/websocket_client.py`) to stream recorded audio to the backend WebSocket endpoint.

## Using Whisper locally (notes)

- `Code/backend/core/stt_engine.py` demonstrates how the project currently loads Whisper's `tiny` model:

	- Loading the model will download model weights the first time. Expect additional disk space and initial download time.
	- The tiny model is the fastest/smallest available but less accurate than larger models.

- For better performance in real-time scenarios, consider:
	- Using a GPU with torch + CUDA to speed transcription.
	- Using chunked audio buffers and incremental decoding instead of full-file transcribe.

## Docker (optional)

There are Dockerfiles for backend and frontend in `Code/docker/`. If you prefer to run the project with Docker Compose, build and run from the repository root:

```powershell
docker-compose -f Code/docker/docker-compose.yml up --build
```

Adjust the compose file and environment variables as needed.

## Development notes & next steps

- Real-time streaming: integrate `Code/frontend/websocket_client.py` with `Code/backend/api/websocket.py` so the browser streams short audio chunks to the server and the server pipes them to the Whisper STT engine for near-real-time transcription.
- Incremental transcription and low-latency summarization: implement chunked processing and partial transcript updates (rather than waiting for full-file transcribe).
- Summarization: `Code/backend/core/summarization_engine.py` and `Code/backend/core/summarization_worker.py` are placeholders for adding a short-form summarization model or using an API.
- Add tests and CI for reproducibility.

## Troubleshooting

- Microphone permission issues: ensure your browser allows microphone access for the Streamlit app origin. On Windows, check the system privacy settings if your browser can't access the microphone.
- Whisper OOM or slow transcription: either use a smaller model (tiny) or move to GPU. CPU transcription with larger models is very slow.
- Model download blocked: ensure internet access when loading the Whisper model for the first time.

## Contributing

Contributions welcome. Open an issue or send a PR with a clear description of the change.

## License

This repository includes a `LICENSE` file at the project root. Review it for license details.

## Acknowledgements

- Prototype inspired by OpenAI Whisper and browser Web Speech API demos.


