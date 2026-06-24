# HANDOFF.AI — EMS to Hospital Handoff

Transforms paramedic radio reports into structured hospital handoff data using AI.

**The flow:** Ambulance (paramedic) → HANDOFF.AI → Hospital ER

---

## How It Works

1. Paramedic speaks their radio report (live mic or paste text)
2. **Whisper** transcribes speech to text in real time
3. An **LLM** extracts structured data — vitals, history, interventions, allergies, code status
4. The hospital receives an actionable prep report **before the patient arrives**

---

## Dependencies

Install Python packages:

```bash
pip install openai flask flask-cors sounddevice numpy scipy
```

Install PortAudio (required by `sounddevice`):

```bash
# macOS
brew install portaudio

# Ubuntu / Debian
sudo apt install portaudio19-dev

# Windows — usually bundled automatically
```

---

## AI Provider — Groq (Recommended)

**Groq is the recommended provider.** It's free, cloud-hosted, fast, and requires no local setup.
The script defaults to Groq and will prompt for your API key.

1. Get a free API key at [console.groq.com](https://console.groq.com)
2. Set it as an environment variable (see below)
3. Run the script and press Enter at the provider prompt (defaults to Groq)

### Other Providers

| Provider | Notes |
|---|---|
| **Groq** ✅ (default) | Free tier, cloud, fast — recommended |
| **Ollama** | Local, fully offline, requires [install](https://ollama.ai/download) + `ollama pull llama3.2:1b` |
| **OpenRouter** | Cloud, some free models available at [openrouter.ai](https://openrouter.ai) |

---

## API Key Setup

Never hardcode your API key. Use an environment variable:

```bash
# macOS / Linux
export GROQ_API_KEY="gsk_your_key_here"

# Windows (Command Prompt)
set GROQ_API_KEY=gsk_your_key_here

# Windows (PowerShell)
$env:GROQ_API_KEY="gsk_your_key_here"
```

The script reads it automatically via `os.getenv("GROQ_API_KEY")`.

---

## Running the Script

```bash
python handoff.py
```

You'll see a provider menu — just press **Enter** to use Groq (the default).

### Menu Options

| Option | Description |
|---|---|
| 1 | STEMI demo — 67yo male, chest pain, cath lab activation |
| 2 | Trauma demo — 34yo female, MVC rollover |
| 3 | Sepsis demo — 82yo nursing home patient |
| 4 | Paste your own EMS report |
| **5** | **Live mic recording (speech-to-text mode)** |
| 6 | Exit |

---

## Speech-to-Text Mode (Option 5)

> Requires Groq provider.

1. Run the script and choose **option 1** (Groq) at the provider prompt
2. Choose **option 5** at the case menu
3. A browser window opens at `http://localhost:5000`
4. Click **Start Recording** and read your report aloud
5. Say **"Confirm report ready"** to stop automatically, or click Stop manually
6. The full audio is re-transcribed and processed into a structured handoff report

A sample script is shown in the browser UI to guide you.

---

## Output

Results are printed as a color-coded ER dashboard in the terminal and saved to:

```
handoff_report.json
```

The JSON contains ~20 structured fields including alert type, priority level, vitals, EMS interventions, patient history, allergies, code status, and time-critical hospital prep actions.
