#Entry point run FastAPI
import os
import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse
import redis.asyncio as aioredis
from dotenv import load_dotenv

from models.load_whisper import get_model
from core.audio_processor import webm_bytes_to_wav_file

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MODEL_SIZE = os.getenv("MODEL_SIZE", "tiny.en")
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE", "int8")

# transcription config
CHUNK_SECONDS = float(os.getenv("CHUNK_SECONDS", "6.0"))  # sliding buffer window to transcribe
MIN_AUDIO_BYTES_FOR_TRANSCRIBE = int(os.getenv("MIN_AUDIO_BYTES_FOR_TRANSCRIBE", "1000"))

app = FastAPI(title="Realtime Transcription Backend")


# NOTE: Do NOT perform heavy I/O or model loading at import time.
# Initialize Redis and the Whisper model during FastAPI startup so uvicorn can finish import
# and accept connections even if model loading is slow or fails.


@app.on_event("startup")
async def startup_event():
    print("Starting FastAPI app...")
    # initialize redis client
    try:
        app.state.redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        print("Redis client initialized.")
    except Exception as e:
        app.state.redis = None
        print("Redis init error:", e)

    # load Whisper/faster-whisper model in a thread to avoid blocking the event loop
    try:
        print("Loading faster-whisper model:", MODEL_SIZE)
        # get_model is CPU-bound / may block; run it in a thread
        model_obj = await asyncio.to_thread(get_model, MODEL_SIZE, DEVICE, COMPUTE_TYPE)
        app.state.model = model_obj
        print("Model loaded.")
    except Exception as e:
        app.state.model = None
        print("Model load error:", e)


@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down FastAPI app...")
    try:
        redis_client = getattr(app.state, "redis", None)
        if redis_client is not None:
            await redis_client.close()
    except Exception:
        pass


@app.get("/")
async def root():
    """Simple health endpoint to verify the server is up."""
    model_status = "loaded" if getattr(app.state, "model", None) is not None else "not_loaded"
    redis_status = "connected" if getattr(app.state, "redis", None) is not None else "not_connected"
    return {"status": "ok", "model": model_status, "redis": redis_status}

# In-memory store per-session: buffer of wav file paths (rotating)
SESSION_BUFFERS = {}  # session_id -> list of WAV temp file paths

async def publish_transcript(session_id: str, transcript_text: str):
    key = f"transcript:{session_id}"
    redis_client = getattr(app.state, "redis", None)
    if redis_client is None:
        # Redis not available; skip persisting
        return
    await redis_client.set(key, transcript_text)
    payload = json.dumps({"session_id": session_id, "transcript": transcript_text, "ts": int(time.time())})
    await redis_client.publish("transcripts", payload)


@app.websocket("/ws/transcribe")
async def websocket_transcribe(ws: WebSocket, session_id: Optional[str] = Query(None)):
    """
    WebSocket endpoint to receive binary audio chunks (webm/opus) from browser and return incremental transcripts.
    Query param: session_id (string) — must be provided by the client to identify session.
    Protocol (client -> server):
      - Binary frames: webm/opus blob bytes (recorded chunks)
      - Text frames: JSON command messages like {"command":"flush"} or {"command":"end"}
    Server -> client:
      - JSON text messages: {"type":"partial","text":"..."} or {"type":"final","text":"...","full_text":"..."}
    """
    if session_id is None:
        await ws.close(code=4001)
        return

    await ws.accept()
    print(f"WS accepted session_id={session_id}")

    # buffer list
    SESSION_BUFFERS.setdefault(session_id, [])

    # each session keeps a running full transcript
    session_full_text = ""
    try:
        while True:
            msg = await ws.receive()
            # handle disconnect
            if "type" in msg and msg["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(code=1000)

            if msg["type"] == "websocket.receive" and "bytes" in msg:
                webm_bytes = msg["bytes"]
                # Convert to wav file
                tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                tmp_wav_path = tmp_wav.name
                tmp_wav.close()
                try:
                    webm_bytes_to_wav_file(webm_bytes, tmp_wav_path, sample_rate=16000)
                except Exception as e:
                    # failed decode
                    await ws.send_text(json.dumps({"type":"error","error": f"ffmpeg error: {e}"}))
                    continue

                # keep buffer; rotate older files to maintain ~CHUNK_SECONDS of audio
                SESSION_BUFFERS[session_id].append(tmp_wav_path)

                # compute total covered seconds ~ we don't have exact durations easily here, but faster-whisper will accept the file
                # For simplicity, trigger transcription whenever we have >1 file (or small bytes)
                # Optionally compute sizes:
                total_bytes = sum(Path(p).stat().st_size for p in SESSION_BUFFERS[session_id] if Path(p).exists())
                if total_bytes < MIN_AUDIO_BYTES_FOR_TRANSCRIBE:
                    # wait for more bytes
                    await ws.send_text(json.dumps({"type":"ack","msg":"chunk_received","buffer_files": len(SESSION_BUFFERS[session_id])}))
                    continue

                # Merge all buffered wav files into a single temp wav for transcription
                merged_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                merged_tmp_path = merged_tmp.name
                merged_tmp.close()
                try:
                    # Use ffmpeg concat approach to join
                    from core.audio_processor import combine_wavs
                    combine_wavs(SESSION_BUFFERS[session_id], merged_tmp_path)

                    # Transcribe merged file with faster-whisper
                    model_obj = getattr(app.state, "model", None)
                    if model_obj is None:
                        await ws.send_text(json.dumps({"type":"error","error": "model not loaded"}))
                        continue
                    # We use model.transcribe(merged_tmp_path, language='en', beam_size=5) to get text
                    # Note: faster-whisper returns segments generator/list
                    segments, info = model_obj.transcribe(merged_tmp_path, beam_size=5, language="en", vad_filter=False)
                    # Collect segments text
                    partial_text = " ".join([seg.text.strip() for seg in segments]).strip()

                    # compute diff vs session_full_text to send incremental updates
                    if partial_text and (not session_full_text or partial_text != session_full_text):
                        # choose to send partial or final depending on silence / command — here we treat it as partial and also update full
                        session_full_text = partial_text
                        await ws.send_text(json.dumps({"type":"partial","text": partial_text}))
                        # persist to redis and publish
                        await publish_transcript(session_id, session_full_text)

                    # rotate buffer: keep only latest few files to bound disk usage
                    # remove older files if we have >8 files
                    while len(SESSION_BUFFERS[session_id]) > 8:
                        old = SESSION_BUFFERS[session_id].pop(0)
                        try:
                            Path(old).unlink()
                        except Exception:
                            pass

                except Exception as e:
                    await ws.send_text(json.dumps({"type":"error","error": f"transcription error: {e}"}))
                finally:
                    # remove merged tmp
                    try:
                        Path(merged_tmp_path).unlink()
                    except Exception:
                        pass

            elif msg["type"] == "websocket.receive" and "text" in msg:
                text = msg["text"]
                try:
                    payload = json.loads(text)
                except Exception:
                    payload = {"command": "unknown", "raw": text}

                cmd = payload.get("command", "").lower()
                if cmd == "flush":
                    # client requests to finalize current buffer into a final transcript
                    # do one final transcription pass
                    paths = SESSION_BUFFERS.get(session_id, [])
                    if not paths:
                        await ws.send_text(json.dumps({"type":"final","text": "", "full_text": session_full_text}))
                        continue

                    merged_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                    merged_tmp_path = merged_tmp.name
                    merged_tmp.close()
                    try:
                        from core.audio_processor import combine_wavs
                        combine_wavs(paths, merged_tmp_path)
                        model_obj = getattr(app.state, "model", None)
                        if model_obj is None:
                            await ws.send_text(json.dumps({"type":"error","error": "model not loaded"}))
                            continue
                        segments, info = model_obj.transcribe(merged_tmp_path, beam_size=5, language="en", vad_filter=False)
                        final_text = " ".join([seg.text.strip() for seg in segments]).strip()
                        session_full_text = final_text or session_full_text
                        await ws.send_text(json.dumps({"type":"final","text": final_text, "full_text": session_full_text}))
                        await publish_transcript(session_id, session_full_text)
                        # clear buffer
                        for p in list(SESSION_BUFFERS.get(session_id, [])):
                            try:
                                Path(p).unlink()
                            except Exception:
                                pass
                        SESSION_BUFFERS[session_id] = []
                    except Exception as e:
                        await ws.send_text(json.dumps({"type":"error","error": f"flush error: {e}"}))
                    finally:
                        try:
                            Path(merged_tmp_path).unlink()
                        except Exception:
                            pass

                elif cmd == "end":
                    # client signals end-of-session; send final and close
                    await ws.send_text(json.dumps({"type":"info","msg":"ending session"}))
                    await ws.close()
                    break

                else:
                    await ws.send_text(json.dumps({"type":"info","msg":"unknown command","payload":payload}))

    except WebSocketDisconnect:
        print(f"Websocket disconnected for session_id={session_id}")
    except Exception as e:
        print("WS error:", e)
    finally:
        # cleanup
        for p in SESSION_BUFFERS.get(session_id, []):
            try:
                Path(p).unlink()
            except Exception:
                pass
        SESSION_BUFFERS.pop(session_id, None)
        try:
            await ws.close()
        except Exception:
            pass
        print(f"Cleaned up session {session_id}")
