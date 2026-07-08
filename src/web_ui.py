import time
import threading
import webbrowser
 
import numpy as np
import scipy.io.wavfile as wav
import sounddevice as sd
from flask import Flask, jsonify
from flask_cors import CORS
from typing import Optional

# ---------------------------------------------------------------------------
# HTML served to the browser
# ---------------------------------------------------------------------------

_INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EMS Handoff - Live Mode</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #121212; color: #e0e0e0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; overflow: hidden; transition: background-color 0.5s; }
        .container { background-color: #1e1e1e; padding: 2rem; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.5); width: 80%; max-width: 800px; text-align: center; border: 1px solid #333; position: relative; z-index: 10; }
        h1 { color: #fff; margin-bottom: 0.5rem; font-weight: 300; letter-spacing: 1px; }
        .status-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; font-weight: bold; margin-bottom: 1.5rem; text-transform: uppercase; letter-spacing: 1px; }
        .status-ready { background-color: #333; color: #aaa; }
        .status-recording { background-color: #cf222e; color: white; animation: pulse 1.5s infinite; }
        .status-confirmed { background-color: #238636; color: white; }
        
        .script-box { background-color: #252525; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #58a6ff; text-align: left; margin-bottom: 1.5rem; font-size: 1.1rem; line-height: 1.6; color: #fff; box-shadow: inset 0 2px 4px rgba(0,0,0,0.2); }
        .transcript-box { background-color: #0d1117; padding: 1.5rem; border-radius: 8px; border: 1px solid #30363d; height: 150px; overflow-y: auto; text-align: left; font-family: 'Consolas', monospace; color: #8b949e; margin-bottom: 2rem; transition: all 0.3s; }
        .transcript-box.active { border-color: #58a6ff; color: #c9d1d9; }
        .transcript-box .new-text { color: #fff; font-weight: bold; }
        
        .controls { display: flex; gap: 1rem; justify-content: center; }
        button { padding: 0.8rem 2rem; border: none; border-radius: 6px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn-record { background-color: #238636; color: white; }
        .btn-record:hover { background-color: #2ea043; transform: translateY(-2px); }
        .btn-stop { background-color: #da3633; color: white; }
        .btn-stop:hover { background-color: #f85149; }
        
        .instruction { color: #8b949e; font-size: 0.9rem; margin-top: 1rem; }
        .magic-word { color: #58a6ff; font-weight: bold; }

        /* Flash Animation for Confirmation */
        @keyframes flashRed {
            0% { background-color: #121212; }
            50% { background-color: #8a1c1c; }
            100% { background-color: #121212; }
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(207, 34, 46, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(207, 34, 46, 0); }
            100% { box-shadow: 0 0 0 0 rgba(207, 34, 46, 0); }
        }
        
        .flashing { animation: flashRed 2s ease-in-out infinite; }
        .confirmed-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(35, 134, 54, 0.95); display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 100; opacity: 0; pointer-events: none; transition: opacity 0.5s; }
        .confirmed-overlay.show { opacity: 1; pointer-events: auto; }
        .confirmed-text { color: white; font-size: 3rem; font-weight: bold; margin-bottom: 1rem; text-shadow: 0 4px 8px rgba(0,0,0,0.3); }
    </style>
</head>
<body>
    <div id="flash-layer"></div>
    <div class="confirmed-overlay" id="confirmOverlay">
        <div class="confirmed-text">REPORT CONFIRMED</div>
        <div style="color: #fff; font-size: 1.2rem;">Generating Handoff...</div>
    </div>

    <div class="container">
        <h1>EMS HANDOFF AI</h1>
        <div id="status-badge" class="status-badge status-ready">Ready</div>
        
        <div class="script-box">
            <strong>📄 READ THIS SCRIPT:</strong><br><br>
            "Medic 21 to General Hospital.<br>
            We are inbound with a 45-year-old male found down.<br>
            GCS is 14. History of Seizures.<br>
            Vitals: BP 140 over 90, Heart Rate 110, SpO2 98%.<br>
            We have established an IV and given 5mg Versed.<br>
            ETA is 5 minutes."
        </div>
        
        <div class="transcript-box active" id="transcript">
            (Transcript will appear here...)
        </div>
        
        <div class="controls">
            <button id="btnAction" class="btn-record" onclick="toggleRecording()">START RECORDING</button>
        </div>
        
        <p class="instruction">
            Say <span class="magic-word">"CONFIRM REPORT READY"</span> to send automatically.
        </p>
    </div>

    <script>
        let isRecording = false;
        let pollInterval;

        async function toggleRecording() {
            const btn = document.getElementById('btnAction');
            const status = document.getElementById('status-badge');
            
            if (!isRecording) {
                // Start
                await fetch('/start_recording');
                isRecording = true;
                btn.textContent = "STOP RECORDING";
                btn.className = "btn-stop";
                status.textContent = "🔴 RECORDING";
                status.className = "status-badge status-recording";
                startPolling();
            } else {
                // Stop manually
                await fetch('/stop_recording');
                isRecording = false;
                btn.textContent = "START RECORDING";
                btn.className = "btn-record";
                status.textContent = "Ready";
                status.className = "status-badge status-ready";
                stopPolling();
            }
        }

        function startPolling() {
            pollInterval = setInterval(async () => {
                const response = await fetch('/get_state');
                const data = await response.json();
                
                // Update transcript
                const textBox = document.getElementById('transcript');
                if(data.transcript) {
                    textBox.innerText = data.transcript;
                    textBox.scrollTop = textBox.scrollHeight;
                }
                
                // Check status
                if (data.status === 'confirmed') {
                    stopPolling();
                    document.body.className = "flashing"; // Red flash on body if needed, or overlay
                    document.getElementById('confirmOverlay').className = "confirmed-overlay show";
                    setTimeout(() => {
                        window.close(); // Optional: close window after delay
                    }, 3000);
                }
            }, 1000);
        }

        function stopPolling() {
            clearInterval(pollInterval);
        }
    </script>
</body>
</html>
"""

def start_web_ui(transcribe_chunk_fn):
    """Start the Flask server for the Web GUI."""
    app = Flask(__name__)
    CORS(app)
    
    # Shared state
    web_state = {
        "is_recording": False,
        "transcript": "",
        "status": "ready", # ready, recording, confirmed
        "final_file": None
    }

    def _recording_worker():
        """Background thread to handle audio recording loop."""
        threshold_text = "confirm report"
        sample_rate = 16000
        chunk_duration = 3.0
        
        full_audio_data = np.array([], dtype=np.float32)
        
        try:
            while web_state["is_recording"]:
                # Record chunk
                chunk = sd.rec(int(chunk_duration * sample_rate), samplerate=sample_rate, channels=1)
                sd.wait()
                
                # Append
                chunk_flat = chunk.flatten()
                full_audio_data = np.concatenate((full_audio_data, chunk_flat))
                
                # Check keyword
                check_duration = 6.0
                samples_to_check = int(check_duration * sample_rate)
                if len(full_audio_data) > samples_to_check:
                    check_data = full_audio_data[-samples_to_check:]
                else:
                    check_data = full_audio_data
                
                wav.write("output/temp_check.wav", sample_rate, check_data)
                
                # Transcribe
                new_text = transcribe_chunk_fn("output/temp_check.wav")
                
                if new_text:
                    # Append to transcript for UI (simplistic)
                    # Ideally we wouldn't just append, but for demo this shows activity
                    if len(web_state["transcript"]) == 0:
                            web_state["transcript"] = new_text
                    elif len(new_text) > 3: # Avoid noise
                            web_state["transcript"] += f" {new_text}"
                    
                    # Check keyword
                    if threshold_text.lower() in new_text.lower() or "ready to send" in new_text.lower():
                        web_state["status"] = "confirmed"
                        web_state["is_recording"] = False
                        break
                        
            # Save final
            final_filename = "output/final_recording.wav"
            wav.write(final_filename, sample_rate, full_audio_data)
            web_state["final_file"] = final_filename
            print("[REC] Recording finished.")
            
        except Exception as e:
            print(f"[REC] Error: {e}")
            web_state["is_recording"] = False
    
    @app.route("/")
    def index():
        return _INDEX_HTML

    @app.route("/start_recording")
    def start_recording():
        if not web_state["is_recording"]:
            web_state["is_recording"] = True
            web_state["status"] = "recording"
            web_state["transcript"] = ""
            # Start recording thread
            threading.Thread(target=_recording_worker).start()
        return jsonify({"status": "started"})

    @app.route("/stop_recording")
    def stop_recording():
        web_state["is_recording"] = False
        web_state["status"] = "ready"
        return jsonify({"status": "stopped"})

    @app.route("/get_state")
    def get_state():
        return jsonify(web_state)
        
    # Run Flask in a separate thread
    print("[WEB] Starting local content server...")
    threading.Thread(target=lambda: app.run(port=5000, use_reloader=False), daemon=True).start()
    
    # Open Browser
    time.sleep(1)
    webbrowser.open("http://localhost:5000")
    
    # Block main thread until we have a file or user exits
    print("[WEB] Waiting for recording from Web UI...")
    try:
        while True:
            if web_state["status"] == "confirmed" and web_state["final_file"]:
                return web_state["final_file"]
            time.sleep(0.5)
    except KeyboardInterrupt:
        return None
