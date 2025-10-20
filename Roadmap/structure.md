realtime\_ai\_app/

│

├── backend/

│   ├── main.py                     # FastAPI entry point

│   ├── config.py                   # Global config: Redis URL, model path, constants

│   ├── requirements.txt            # Dependency list

│   │

│   ├── api/

│   │   ├── init.py

│   │   ├── websocket\_routes.py     # WebSocket logic (receive audio stream from frontend)

│   │   └── rest\_routes.py          # REST endpoints (if you need testing, logs, etc.)

│   │

│   ├── core/

│   │   ├── audio\_processor.py      # Chunk splitting, audio signal processing, format conversion

│   │   ├── stt\_engine.py           # Whisper/Vosk wrapper (Speech-to-Text)

│   │   ├── summarization\_engine.py # Summarization model (LLM, T5, etc.)

│   │   ├── redis\_queue.py          # Redis Stream handling (push/pull chunk)

│   │   └── summarization\_worker.py # Worker running in parallel for summarization

│   │

│   ├── utils/

│   │   ├── logger.py               # Standard logging (FastAPI + model)

│   │   ├── timer.py                # Measure latency for each step (STT, summary)

│   │   └── chunk\_utils.py          # Split and merge text/audio windows

│   │

│   └── models/

│       ├── load\_whisper.py         # Function to load and cache Whisper

│       ├── load\_summary\_model.py   # Function to load and cache LLM

│       └── init.py

│

├── frontend/

│   ├── app.py                      # Streamlit frontend

│   ├── components/                 # UI components: buttons, live area, summary box

│   ├── websocket\_client.py         # WebSocket connection to FastAPI backend

│   └── requirements.txt

│

├── docker/

│   ├── Dockerfile.backend

│   ├── Dockerfile.frontend

│   └── docker-compose.yml

│

└── README.md                       # Project description, how to run

