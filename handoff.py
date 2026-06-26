import json
import os
 
from openai import OpenAI
from typing import Optional
 
from prompt import EXTRACTION_PROMPT

# =============================================================================
# MAIN HANDOFF CLASS
# =============================================================================

class HandoffAI:
    """
    Transforms EMS radio reports into structured hospital handoff data.
    
    The Problem We Solve:
    - Paramedics give verbal reports that are hard to capture
    - Hospital staff miss critical info, have to ask repeat questions
    - Time-critical patients (STEMI, Stroke, Trauma) need instant prep
    
    Our Solution:
    - AI listens to paramedic's natural speech
    - Extracts structured data (vitals, history, interventions)
    - Sends actionable report to hospital BEFORE patient arrives
    """
    
    def __init__(self, api_key: Optional[str] = None, provider: str = "ollama"):
        """
        Initialize with your choice of FREE AI provider.
        
        Args:
            api_key: API key (not needed for Ollama)
            provider: "ollama" (local, free) | "groq" (cloud, free tier) | "openrouter" (cloud, some free models)
        """
        self.provider = provider
        
        if provider == "ollama":
            # Ollama runs locally - completely FREE!
            self.client = OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama"  # Ollama doesn't need a real key
            )
            # Use smaller 1B model as it uses less RAM and runs on all laptops
            self.model = "llama3.2:1b"
            
        elif provider == "groq":
            # Groq - FREE tier available at console.groq.com
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key or os.getenv("GROQ_API_KEY")
            )
            self.model = "llama-3.3-70b-versatile"  # Free on Groq
            
        elif provider == "openrouter":
            # OpenRouter - some free models available
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key or os.getenv("OPENROUTER_API_KEY")
            )
            self.model = "meta-llama/llama-3.2-3b-instruct:free"  # Free model
            
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'ollama', 'groq', or 'openrouter'")
    
    def process_ems_report(self, ems_report: str) -> dict:
        """
        Process a paramedic's verbal radio report and extract structured data.
        
        Args:
            ems_report: The raw text of what the paramedic said on the radio
            
        Returns:
            Structured handoff data for the hospital
        """
        print("\n[*] Processing EMS report...")
        print(f"    Using: {self.provider.upper()} — {self.model}")
        print("-" * 50)
 
        try:
            # Call AI to extract structured data (OpenAI-compatible API)
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": EXTRACTION_PROMPT.format(ems_report=ems_report),
                }],
            )

            # Parse the JSON response
            json_text = response.choices[0].message.content
            json_text = json_text.replace("```json", "").replace("```", "").strip()
            return json.loads(json_text)
 
        except Exception as e:
            self._print_connection_error(e)
            raise
 
    def _print_connection_error(self, e: Exception) -> None:
        """Print a provider-specific error message."""
        error_type = type(e).__name__
 
        if "Connection" in error_type or "ConnectError" in str(e):
            print("\n" + "=" * 60)
            print("[X] CONNECTION ERROR")
            print("=" * 60)
 
            if self.provider == "ollama":
                print("\n[!]  Ollama is not running or not installed.\n")
                print("Quick Fix Options:\n")
                print("Option 1: Install Ollama (Local - Free)")
                print("  1. Download from: https://ollama.ai/download")
                print("  2. Install it")
                print("  3. Run: ollama pull llama3.2")
                print("  4. Ollama should auto-start (or run: ollama serve)")
                print("  5. Re-run this script\n")

                print("Option 2: Use Groq Instead (Cloud - Free)")
                print("  1. Get API key from: https://console.groq.com")
                print("  2. Re-run this script")
                print("  3. Choose option 2 (Groq)")
                print("  4. Paste your API key\n")
 
            elif self.provider == "groq":
                print("\n[!]  Cannot connect to Groq API.\n")
                print("Possible issues:")
                print("  - Check your internet connection")
                print("  - Verify your API key is correct")
                print("  - Groq service might be down (check status.groq.com)\n")
 
            elif self.provider == "openrouter":
                print("\n[!]  Cannot connect to OpenRouter API.\n")
                print("Possible issues:")
                print("  - Check your internet connection")
                print("  - Verify your API key is correct")
                print("  - OpenRouter service might be down\n")
 
            print("=" * 60)
 
        elif "API" in error_type or "Auth" in error_type:
            print("\n[X] API Authentication Error")
            print("Your API key might be invalid or expired.")
            print(f"Provider: {self.provider}")
            print("\nGet a new API key:")
            if self.provider == "groq":
                print("  https://console.groq.com")
            elif self.provider == "openrouter":
                print("  https://openrouter.ai/keys")
 
        else:
            print(f"\n[X] Unexpected error: {error_type}")
            print(f"Details: {str(e)}")

    def transcribe_audio_chunk(self, filename):
        """Helper to transcribe a small chunk for keyword detection"""
        try:
            with open(filename, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=(filename, file.read()),
                    model="whisper-large-v3-turbo",  # UPDATED MODEL
                    response_format="json",
                    language="en",
                    temperature=0.0
                )
            return transcription.text.strip()
        except:
            return ""

    def transcribe_audio_final(self, filename):
        """Transcribe the full audio file"""
        print("\n[CLIPBOARD] Transcribing full report with Whisper...")
        try:
            with open(filename, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=(filename, file.read()),
                    model="whisper-large-v3-turbo", # UPDATED MODEL
                    prompt="The following is a paramedic radio report. Terminology: BP, HR, SpO2, STEMI, GCS, IV.",
                    response_format="json",
                    language="en"
                )
            return transcription.text
        except Exception as e:
            print(f"[X] Transcription failed: {e}")
            return None
        
    def display_hospital_view(self, data: dict):
        """
        Display what the hospital ER would see on their dashboard.
        This is the OUTPUT that makes us valuable.
        """
        alert_colors = {
            "RED": "\033[91m",      # Red
            "YELLOW": "\033[93m",   # Yellow  
            "GREEN": "\033[92m",    # Green
        }
        RESET = "\033[0m"
        BOLD = "\033[1m"
        
        color = alert_colors.get(data.get("alert_level", "GREEN"), "")
        
        print("\n" + "=" * 60)
        print(f"{BOLD}[HOSPITAL] HOSPITAL ER DASHBOARD - INCOMING PATIENT{RESET}")
        print("=" * 60)
        
        # Alert Banner
        print(f"\n{color}{BOLD}[!]  {data.get('alert_type', 'UNKNOWN')} ALERT - {data.get('alert_level', 'UNKNOWN')} PRIORITY{RESET}")
        print(f"{BOLD}ETA: {data.get('eta_minutes', '?')} MINUTES{RESET}")
        
        # One-liner summary
        summary = data.get("handoff_summary", {})
        print(f"\n \"{summary.get('one_liner', 'No summary available')}\"")
        
        # Patient Info
        patient = data.get("patient", {})
        print(f"\n{BOLD}PATIENT:{RESET}")
        print(f"  Age/Sex: {patient.get('age', '?')} {patient.get('age_unit', 'years')} {patient.get('sex', 'Unknown')}")
        print(f"  Chief Complaint: {data.get('chief_complaint', 'Unknown')}")
        print(f"  Mechanism/Onset: {data.get('mechanism_or_onset', 'Unknown')}")
        
        # Vital Signs
        vitals = data.get("vital_signs", {})
        print(f"\n{BOLD}VITAL SIGNS:{RESET}")
        if vitals.get("blood_pressure"):
            print(f"  BP: {vitals['blood_pressure']}")
        if vitals.get("heart_rate"):
            print(f"  HR: {vitals['heart_rate']}")
        if vitals.get("respiratory_rate"):
            print(f"  RR: {vitals['respiratory_rate']}")
        if vitals.get("spo2"):
            print(f"  SpO2: {vitals['spo2']}")
        if vitals.get("gcs"):
            print(f"  GCS: {vitals['gcs']}")
        if vitals.get("temperature"):
            print(f"  Temp: {vitals['temperature']}")
        if vitals.get("blood_glucose"):
            print(f"  BGL: {vitals['blood_glucose']}")
        
        # Assessment
        assessment = data.get("assessment_findings", {})
        print(f"\n{BOLD}ASSESSMENT:{RESET}")
        print(f"  LOC: {assessment.get('level_of_consciousness', 'Unknown')}")
        print(f"  Airway: {assessment.get('airway', 'Unknown')}")
        print(f"  Breathing: {assessment.get('breathing', 'Unknown')}")
        print(f"  Circulation: {assessment.get('circulation', 'Unknown')}")
        if assessment.get("other_findings"):
            print(f"  Other: {', '.join(assessment['other_findings'])}")
        
        # EMS Interventions
        interventions = data.get("ems_interventions", [])
        if interventions:
            print(f"\n{BOLD}EMS INTERVENTIONS:{RESET}")
            for i, item in enumerate(interventions, 1):
                print(f"  {i}. {item.get('intervention', '')} - {item.get('details', '')}")
                if item.get("response"):
                    print(f"     -> Response: {item['response']}")
        
        # History
        history = data.get("history", {})
        print(f"\n{BOLD}HISTORY:{RESET}")
        print(f"  PMH: {', '.join(history.get('past_medical', ['Unknown']))}")
        print(f"  Medications: {', '.join(history.get('medications', ['Unknown']))}")
        print(f"  Allergies: {', '.join(history.get('allergies', ['NKDA']))}")
        print(f"  Code Status: {history.get('code_status', 'Full Code')}")
        
        # Hospital Prep - THE KEY VALUE PROPOSITION
        hospital = data.get("hospital_recommendations", {})
        print(f"\n{color}{BOLD}[!] HOSPITAL PREPARATION:{RESET}")
        print(f"  Requested: {hospital.get('activation_requested', 'None specified')}")
        print(f"  Destination: {hospital.get('suggested_destination', 'General ED')}")
        if hospital.get("resources_to_prepare"):
            print(f"  Resources Needed:")
            for resource in hospital["resources_to_prepare"]:
                print(f"    * {resource}")
        if hospital.get("time_critical_actions"):
            print(f"  {BOLD}TIME-CRITICAL ACTIONS:{RESET}")
            for action in hospital["time_critical_actions"]:
                print(f"    [TIME]  {action}")
        
        # Key Concerns
        if summary.get("key_concerns"):
            print(f"\n{BOLD}[!] KEY CONCERNS:{RESET}")
            for concern in summary["key_concerns"]:
                print(f"  * {concern}")
        
        # Pending Needs
        if summary.get("pending_needs"):
            print(f"\n{BOLD}PENDING NEEDS ON ARRIVAL:{RESET}")
            for need in summary["pending_needs"]:
                print(f"  -> {need}")
        
        # Data Quality
        quality = data.get("data_quality", {})
        print(f"\n{BOLD}DATA QUALITY:{RESET} {quality.get('confidence', 'Unknown')}")
        if quality.get("missing_info"):
            print(f"  Missing: {', '.join(quality['missing_info'])}")
        
        print("\n" + "=" * 60)