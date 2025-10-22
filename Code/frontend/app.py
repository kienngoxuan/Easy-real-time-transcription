import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
openai_api_input = st.session_state.get("_openai_key_input", "")
BACKEND_WS_URL = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/ws/transcribe")

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

st.set_page_config(page_title="⌛ Realtime AI App — Frontend (without backend)", layout="wide")

st.title("⌛Realtime AI Frontend — Streamlit (without Backend)")
st.markdown(
    """
1. Allow microphone permission in the embedded widget below.
2. Select your microphone, press **Start**. The widget shows live transcription and *Download audio*.
3. When recording stops, the transcription will appear automatically below.
"""
)

with st.container():
    left, right = st.columns([1.1, 1])

    with left:
        st.subheader("🎙️ Microphone Control & Recording")
        st.markdown("This widget uses the browser Web Speech API (speech-to-text).")

        widget_html = """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8" />
          <style>
            body {{ font-family: Arial, Helvetica, sans-serif; margin: 8px; }}
            .panel {{ border: 1px solid #ddd; padding: 8px; border-radius: 6px; }}
            label {{ font-weight: 600; }}
            select, button {{ margin: 6px 6px 6px 0; padding: 6px; }}
            #transcript {{ white-space: pre-wrap; border: 1px solid #eee; padding: 8px; min-height: 120px; margin-top: 6px; background:#fafafa; }}
            #status {{ font-size: 12px; color: #555; margin-top: 6px; }}
          </style>
        </head>
        <body>
          <div class="panel">
            <label for="micSelect">Choose microphone</label><br/>
            <select id="micSelect"></select>
            <button id="startBtn">Start</button>
            <button id="stopBtn" disabled>Stop</button>
            <button id="downloadBtn">Download audio</button>
            <button id="copyBtn">Copy transcript</button>
            <div id="status">Status: idle</div>
            <div id="transcript" role="region" aria-live="polite"></div>
          </div>

          <script>
            // Backend WS URL provided by Streamlit
            const BACKEND_WS_URL = "__BACKEND_WS_URL__";
            let mediaRecorder;
            let recordedChunks = [];
            let ws = null;
            const micSelect = document.getElementById('micSelect');
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const downloadBtn = document.getElementById('downloadBtn');
            const copyBtn = document.getElementById('copyBtn');
            const transcriptDiv = document.getElementById('transcript');
            const statusDiv = document.getElementById('status');
            let sessionId = 'sess-' + Math.random().toString(36).slice(2,9);

            function setStatus(s) { statusDiv.textContent = 'Status: ' + s; }

            function ensureWS() {
              if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return ws;
              const url = BACKEND_WS_URL + '?session_id=' + encodeURIComponent(sessionId);
              ws = new WebSocket(url);
              ws.binaryType = 'arraybuffer';
              ws.onopen = () => { console.log('WS open', url); setStatus('connected to backend'); };
              ws.onmessage = (evt) => {
                try {
                  const d = JSON.parse(evt.data);
                  if (d.type === 'partial' || d.type === 'final') {
                    transcriptDiv.innerText = d.text;
                  } else if (d.type === 'info' || d.type === 'ack') {
                    // ignore/optional
                  } else if (d.type === 'error') {
                    console.error(d.error);
                  }
                } catch (e) { console.error('ws parse error', e); }
              };
              ws.onclose = () => { setStatus('websocket closed'); };
              ws.onerror = (e) => { console.error('ws err', e); };
              return ws;
            }

            async function enumerateMicDevices() {
              try {
                const devices = await navigator.mediaDevices.enumerateDevices();
                const mics = devices.filter(d => d.kind === 'audioinput');
                micSelect.innerHTML = '';
                mics.forEach(m => {
                  const opt = document.createElement('option');
                  opt.value = m.deviceId;
                  opt.textContent = m.label || `Microphone ${micSelect.length+1}`;
                  micSelect.appendChild(opt);
                });
              } catch (e) {
                micSelect.innerHTML = '<option value="">(permission required / unavailable)</option>';
              }
            }

            startBtn.addEventListener('click', async () => {
              startBtn.disabled = true; stopBtn.disabled = false; setStatus('requesting microphone...');
              const constraints = { audio: { deviceId: micSelect.value ? { exact: micSelect.value } : undefined } };
              try {
                const stream = await navigator.mediaDevices.getUserMedia(constraints);
                recordedChunks = [];
                // send chunks periodically while recording (timeslice)
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = async (e) => {
                  if (e.data && e.data.size > 0) {
                    // send chunk immediately to backend WS
                    try {
                      ensureWS();
                      if (ws.readyState === WebSocket.OPEN) {
                        const ab = await e.data.arrayBuffer();
                        ws.send(ab);
                      }
                    } catch (err) { console.error('send chunk err', err); }
                    recordedChunks.push(e.data);
                  }
                };
                mediaRecorder.start(1000); // emit dataavailable every 1s
                ensureWS();
                setStatus('recording');
              } catch (err) {
                setStatus('microphone unavailable'); startBtn.disabled = false; stopBtn.disabled = true;
              }
            });

            stopBtn.addEventListener('click', async () => {
              stopBtn.disabled = true; startBtn.disabled = false; setStatus('stopping');
              if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
              }
              // after stop, send full blob and ask server to flush to finalize
              setTimeout(async () => {
                try {
                  ensureWS();
                  const blob = new Blob(recordedChunks, { type: 'audio/webm' });
                  const ab = await blob.arrayBuffer();
                  if (ws.readyState === WebSocket.OPEN) ws.send(ab);
                  if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ command: 'flush' }));
                  // create download url
                  const url = URL.createObjectURL(blob);
                  downloadBtn.setAttribute('data-url', url);
                  setStatus('recording stopped');
                } catch (e) { console.error('final send err', e); setStatus('error sending audio'); }
              }, 300);
            });

            downloadBtn.addEventListener('click', () => {
              const url = downloadBtn.getAttribute('data-url'); if (!url) return; const a = document.createElement('a'); a.href = url; a.download = 'recording.webm'; a.click();
            });

            copyBtn.addEventListener('click', async () => {
              const text = transcriptDiv.innerText || '';
              try { await navigator.clipboard.writeText(text); alert('Transcript copied to clipboard — paste into the Streamlit summary box.'); }
              catch (e) { alert('Failed to copy: ' + e); }
            });

            enumerateMicDevices(); navigator.mediaDevices.ondevicechange = enumerateMicDevices;
          </script>
        </body>
        </html>
        """.replace("__BACKEND_WS_URL__", BACKEND_WS_URL)
        transcript_placeholder = st.empty()
        transcript_input = transcript_placeholder.text_area(label="Transcription (auto-filled)", value="", height=180, key="transcript_input")
        st.components.v1.html(widget_html, height=420)
        transcript_data = st.experimental_get_query_params().get("transcript", [""])[0]

    with right:
        st.subheader("🗃️ Summary from transcription")
        if not OPENAI_API_KEY:
            api_key_input = st.text_input("OpenAI API key (or set OPENAI_API_KEY in .env)", type="password", key="_openai_key_input")
            if api_key_input:
                client = OpenAI(api_key=api_key_input)
        if st.button("Generate Summary", use_container_width=True):
            transcript_val = st.session_state.get("transcript_input", "")
            if client is None:
                st.error("No OpenAI API key provided. Set OPENAI_API_KEY in .env or enter it above.")
            elif not transcript_val.strip():
                st.warning("Transcription is empty.")
            else:
                with st.spinner("Generating summary"):
                    try:
                        resp = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": "You are a concise summarization assistant."},
                                {"role": "user", "content": "Summarize the following transcription into a short, clear summary. Keep important points and speaker actions. Return a single-paragraph summary."},
                                {"role": "user", "content": transcript_val}
                            ],
                            max_tokens=500,
                            temperature=0.2
                        )
                        summary = resp.choices[0].message.content.strip()
                        st.session_state["summary_display_area"] = summary
                    except Exception as e:
                        st.error(f"Error calling OpenAI API: {e}")
        summary_value = st.session_state.get("summary_display", "Summary display area")
        st.text_area(label="", value=summary_value, height=280, disabled=True, key="summary_display_area")

st.markdown("---")
st.caption("Frontend simplified: live transcription auto-filled and summarized by gpt-4o.")
