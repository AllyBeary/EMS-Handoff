#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HANDOFF.AI - Option A: EMS to Hospital Handoff Demo
====================================================
Transforms paramedic radio reports into structured hospital handoff data.

This is the CORRECT flow:
  AMBULANCE (Paramedic) --> HANDOFF.AI --> HOSPITAL ER
  
NOT 911 dispatch, but the actual paramedic transporting the patient.
"""

import json
import os
import sys
 
from dotenv import load_dotenv
from typing import Optional

from handoff import HandoffAI
from samples import SAMPLE_STEMI, SAMPLE_TRAUMA, SAMPLE_SEPSIS
from web_ui import start_web_ui

load_dotenv()

# =============================================================================
# DEMO / TESTING
# =============================================================================

def _fix_windows_encoding() -> None:
    """Window UTF-8 fix"""
    if sys.platform == "win32":
        try:
            import codecs
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
        except Exception:
            pass

def _select_provider() -> tuple[str, Optional[str]]:
    """Return (provider, api_key). api_key may be None (read from env)."""
    # Choose your FREE provider
    print("\nSelect AI Provider:\n")
    print("  1. Groq (Cloud - FAST & FREE) [Recommended]")
    print("  2. Ollama (Local - requires install)")
    print("  3. OpenRouter (Cloud)\n")
 
    provider_choice = input("Enter choice (1-3, default=1): ").strip() or "1"
 
    if provider_choice == "1":
        api_key = os.getenv("GROQ_API_KEY")
        print("\n[OK] Using Groq cloud API (Key loaded)")
        return "groq", api_key
 
    if provider_choice == "2":
        print("\n[OK] Using Ollama (local). Make sure Ollama is running: 'ollama serve'")
        return "ollama", None
 
    if provider_choice == "3":
        api_key = input("Paste your OpenRouter API key: ").strip() or None
        print("\n[OK] Using OpenRouter API")
        return "openrouter", api_key
 
    print("\n[OK] Defaulting to Ollama (local)")
    return "ollama", None
 
def _select_case(handoff: HandoffAI, provider: str) -> Optional[str]:
    """Return the EMS report text, or None if the user chose to exit."""
    print("Select a sample case to process:\n")
    print("  1. STEMI (Heart Attack) - 67yo male, chest pain, cath lab activation")
    print("  2. TRAUMA (MVC) - 34yo female, rollover crash, trauma activation")
    print("  3. SEPSIS (Medical) - 82yo female, nursing home, altered mental status")
    print("  4. Enter your own EMS report")
    print("  5. [NEW] Record Live Audio (Microphone)")
    print("  6. Exit\n")
 
    sample_choice = input("Enter choice (1-6): ").strip()
 
    if sample_choice == "1":
        print("\n[RADIO] Loading STEMI case...")
        return SAMPLE_STEMI
 
    if sample_choice == "2":
        print("\n[RADIO] Loading TRAUMA case...")
        return SAMPLE_TRAUMA
 
    if sample_choice == "3":
        print("\n[RADIO] Loading SEPSIS case...")
        return SAMPLE_SEPSIS
 
    if sample_choice == "4":
        print("\nPaste the EMS radio report (press Enter twice when done):")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        return "\n".join(lines)
 
    if sample_choice == "5":
        if provider != "groq":
            print("\n[!] Error: Live audio requires Groq provider. Please restart and choose Option 1.")
            return
 
        # Launch Web GUI
        filename = start_web_ui(transcribe_chunk_fn=handoff.transcribe_audio_chunk)
        
        if not filename:
            print("\n[!] No recording captured.")
            return None
 
        ems_report = handoff.transcribe_audio_final(filename)
        if ems_report:
            print("\n" + "=" * 60)
            print("[RADIO] FULL TRANSCRIBED REPORT:")
            print("=" * 60)
            print(ems_report)
        return ems_report
 
    if sample_choice == "6":
        print("Goodbye!")
        return None
 
    print("[!] Invalid choice — running STEMI demo.")
    return SAMPLE_STEMI

def run_demo() -> None:
    _fix_windows_encoding()
 
    print("""
        ===============================================================
                            HANDOFF.AI                              
                Option A: EMS -> Hospital Handoff Demo               
        ===============================================================
        This transforms what paramedics SAY into structured data     
        that hospitals can ACT ON before the patient arrives.        
                                                                    
        Now using FREE AI providers!                              
        ===============================================================
    """)
 
    provider, api_key = _select_provider()
 
    try:
        handoff = HandoffAI(api_key=api_key, provider=provider)
    except Exception as e:
        print(f"\n[X] Error initializing AI provider: {e}")
        print("\nTroubleshooting:")
        print("  - For Ollama: Install from https://ollama.ai and run 'ollama pull llama3.2:1b'")
        print("  - For Groq: Get free API key from https://console.groq.com")
        print("  - For OpenRouter: Get API key from https://openrouter.ai")
        return
 
    ems_report = _select_case(handoff, provider)
    if not ems_report:
        return
 
    print("\n" + "=" * 60)
    print("[RADIO] EMS RADIO REPORT (INPUT):")
    print("=" * 60)
    print(ems_report)
 
    try:
        handoff_data = handoff.process_ems_report(ems_report)

        # Display hospital view
        handoff.display_hospital_view(handoff_data)
 
        # Save JSON to current directory
        output_file = "handoff_report.json"
        with open(output_file, "w") as f:
            json.dump(handoff_data, f, indent=2)
        print(f"\n[SAVE] Full JSON saved to: {output_file}")
        print("\n[OK] Demo completed successfully!")
 
    except KeyboardInterrupt:
        print("\n\n[!] Demo cancelled by user.")
        return 
    except Exception:
        # Error details already printed by process_ems_report
        print("\n[!] Demo failed. See error details above.")
        return 

if __name__ == "__main__":
    run_demo()