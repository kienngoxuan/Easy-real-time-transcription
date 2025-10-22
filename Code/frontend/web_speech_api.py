import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
openai_api_input = st.session_state.get("_openai_key_input", "")

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

        widget_html = r"""
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8" />
          <style>
            body { font-family: Arial, Helvetica, sans-serif; margin: 8px; }
            .panel { border: 1px solid #ddd; padding: 8px; border-radius: 6px; }
            label { font-weight: 600; }
            select, button { margin: 6px 6px 6px 0; padding: 6px; }
            #transcript { white-space: pre-wrap; border: 1px solid #eee; padding: 8px; min-height: 120px; margin-top: 6px; background:#fafafa; }
            #status { font-size: 12px; color: #555; margin-top: 6px; }
          </style>
        </head>
        <body>
          <div class="panel">
            <label for="micSelect">Choose microphone</label><br/>
            <select id="micSelect"></select>
            <button id="startBtn">Start</button>
            <button id="stopBtn" disabled>Stop</button>
            <button id="downloadBtn">Download audio</button>
            <div id="status">Status: idle</div>
            <div id="transcript" role="region" aria-live="polite"></div>
          </div>

          <script>
            let mediaRecorder;
            let recordedChunks = [];
            let recognition;
            const micSelect = document.getElementById('micSelect');
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const downloadBtn = document.getElementById('downloadBtn');
            const transcriptDiv = document.getElementById('transcript');
            const statusDiv = document.getElementById('status');
            let savedTranscript = '';
            let isRecording = false;

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

            function setStatus(s) { statusDiv.textContent = 'Status: ' + s; }

            startBtn.addEventListener('click', async () => {
              startBtn.disabled = true;
              stopBtn.disabled = false;
              setStatus('requesting microphone...');
              const constraints = { audio: { deviceId: micSelect.value ? { exact: micSelect.value } : undefined } };
              try {
                const stream = await navigator.mediaDevices.getUserMedia(constraints);
                recordedChunks = [];
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data); };
                mediaRecorder.start();
                if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                  recognition = new SR();
                  recognition.continuous = true;
                  recognition.interimResults = true;
                  recognition.lang = 'en-US';
                  recognition.onresult = (evt) => {
                    let interim = '';
                    for (let i = evt.resultIndex; i < evt.results.length; ++i) {
                      const res = evt.results[i];
                      if (res.isFinal) savedTranscript += res[0].transcript + ' ';
                      else interim += res[0].transcript + ' ';
                    }
                    transcriptDiv.innerText = (savedTranscript + '\n' + interim).trim();
                    const t = (savedTranscript + '\n' + interim).trim();
                    const pyMsg = JSON.stringify({transcript: t});
                    window.parent.postMessage(pyMsg, "*");
                  };
                  recognition.start();
                  isRecording = true;
                  setStatus('recording + speech recognition active');
                } else {
                  setStatus('recording (speech recognition not supported)');
                }
              } catch (err) {
                setStatus('microphone unavailable');
                startBtn.disabled = false;
                stopBtn.disabled = true;
              }
            });

            stopBtn.addEventListener('click', () => {
              stopBtn.disabled = true;
              startBtn.disabled = false;
              isRecording = false;
              if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                mediaRecorder.onstop = () => {
                  const blob = new Blob(recordedChunks, { type: 'audio/webm' });
                  const url = URL.createObjectURL(blob);
                  downloadBtn.setAttribute('data-url', url);
                  setStatus('recording stopped');
                };
              }
              if (recognition) { try { recognition.stop(); } catch(e) {} recognition = null; }
            });

            downloadBtn.addEventListener('click', () => {
              const url = downloadBtn.getAttribute('data-url');
              if (!url) return;
              const a = document.createElement('a');
              a.href = url;
              a.download = 'recording.webm';
              a.click();
            });

            enumerateMicDevices();
            navigator.mediaDevices.ondevicechange = enumerateMicDevices;
          </script>
        </body>
        </html>
        """
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
