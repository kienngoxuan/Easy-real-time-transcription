import streamlit as st

st.set_page_config(page_title="⌛ Realtime AI App — Frontend (without backend)", layout="wide")

st.title("⌛Realtime AI Frontend — Streamlit (without Backend)")
st.markdown(
    """
1. Allow microphone permission in the embedded widget below.
2. Select your microphone, press **Start**. The widget shows live transcription and *Download audio*.
3. The idle live transcription with idle generate summary.
"""
)

# Layout: mic widget on the left, live transcription on the right
with st.container():
    left, right = st.columns([1.1, 1])

    # ===== LEFT COLUMN: MIC WIDGET =====
    with left:
        st.subheader("🎙️ Microphone Control & Recording")
        st.markdown(
            "This widget uses the browser Web Speech API (speech-to-text). If the browser does not support speech recognition, use the record controls and download audio for offline processing."
        )

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
                console.warn('enumerateDevices error', e);
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
                    let final = '';
                    for (let i = evt.resultIndex; i < evt.results.length; ++i) {
                      const res = evt.results[i];
                      if (res.isFinal) final += res[0].transcript + ' ';
                      else interim += res[0].transcript + ' ';
                    }
                    transcriptDiv.innerText = (final + '\n' + interim).trim();
                  };
                  recognition.onerror = e => console.error('recognition error', e);
                  recognition.onend = () => setStatus('recognition ended');
                  recognition.start();
                  setStatus('recording + speech recognition active');
                } else {
                  setStatus('recording (speech recognition not supported in this browser)');
                }

              } catch (err) {
                console.error(err);
                setStatus('microphone permission denied or unavailable');
                startBtn.disabled = false;
                stopBtn.disabled = true;
              }
            });

            stopBtn.addEventListener('click', () => {
              stopBtn.disabled = true;
              startBtn.disabled = false;
              if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                mediaRecorder.onstop = () => {
                  const blob = new Blob(recordedChunks, { type: 'audio/webm' });
                  const url = URL.createObjectURL(blob);
                  downloadBtn.setAttribute('data-url', url);
                  downloadBtn.setAttribute('data-name', 'recording.webm');
                  setStatus('recording stopped - audio ready for download');
                };
              }
              if (recognition) {
                try { recognition.stop(); } catch(e) {}
                recognition = null;
              }
              setStatus('stopped');
            });

            downloadBtn.addEventListener('click', () => {
              const url = downloadBtn.getAttribute('data-url');
              const name = downloadBtn.getAttribute('data-name') || 'recording.webm';
              if (!url) { setStatus('no audio recorded yet'); return; }
              const a = document.createElement('a');
              a.href = url;
              a.download = name;
              a.click();
              setStatus('audio download started (local file)');
            });

            enumerateMicDevices();
            navigator.mediaDevices.ondevicechange = enumerateMicDevices;
          </script>
        </body>
        </html>
        """

        st.components.v1.html(widget_html, height=380)

    # ===== RIGHT COLUMN: TRANSCRIPTION + SUMMARY BUTTON =====
    with right:
        st.subheader("📝 Live Transcription")
        st.text_area(
            label="",
            value="Status: idle",
            height=320,
            disabled=True,
            key="transcription_display"
        )

        # Generate Summary button placed below transcription
        if st.button("Generate Summary", use_container_width=True):
            st.info("Generate Summary button pressed — summarization logic is currently disabled in this frontend build.")

st.markdown("---")
st.caption("Frontend simplified: live transcription displayed on the right, ready for backend integration.")
