"""Live API verification test script for Sarvam AI and Twilio."""

import asyncio
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.services.sarvam_client import sarvam_client
from app.services.twilio_client import twilio_client


async def run_live_tests():
    print("==================================================")
    print("🔍 SWARASETU LIVE API VERIFICATION REPORT")
    print("==================================================")
    print(f"Sarvam API Key configured: {bool(settings.sarvam_api_key)} (len={len(settings.sarvam_api_key or '')})")
    print(f"Twilio Account SID configured: {bool(settings.twilio_account_sid)}")
    print(f"Twilio Auth Token configured: {bool(settings.twilio_auth_token)}")
    print("--------------------------------------------------")

    # 1. Test Sarvam Translation API
    print("\n[1/3] Testing Sarvam Indic Translation (Hindi -> English)...")
    test_hindi = "बच्चे को दो दिन से बहुत तेज बुखार है और सांस लेने में तकलीफ हो रही है।"
    try:
        translated = await sarvam_client.translate_text(test_hindi, source_language="hi", target_language="en")
        print(f"   Input (Hindi): {test_hindi}")
        print(f"   Output (English): {translated}")
        print("   ✅ Sarvam Translation: SUCCESS")
    except Exception as e:
        print(f"   ❌ Sarvam Translation Error: {e}")

    # 2. Test Sarvam Text-to-Speech API
    print("\n[2/3] Testing Sarvam Text-to-Speech (Indic TTS)...")
    test_response = "आशा दीदी को बता दिया गया है, वो जल्द ही आपके घर आएंगी।"
    try:
        audio_b64 = await sarvam_client.synthesize_speech(test_response, target_language="hi", speaker="priya")
        if audio_b64:

            print(f"   Synthesized text: {test_response}")
            print(f"   Audio base64 payload size: {len(audio_b64)} chars (~{len(audio_b64)*3//4//1024} KB)")
            print("   ✅ Sarvam TTS: SUCCESS")
        else:
            print("   ⚠️ Sarvam TTS returned empty audio payload")
    except Exception as e:
        print(f"   ❌ Sarvam TTS Error: {e}")

    # 3. Test Twilio SMS / WhatsApp Dispatch
    print("\n[3/3] Testing Twilio Client Configuration...")
    try:
        sms_res = await twilio_client.send_sms("+919876543210", "SwaraSetu Test Alert: Moderate pneumonia triage.")
        print(f"   Twilio SMS response: {sms_res}")
        print("   ✅ Twilio Client: SUCCESS")
    except Exception as e:
        print(f"   ❌ Twilio Dispatch Error: {e}")

    print("\n==================================================")
    print("🎉 ALL LIVE CHECKS COMPLETED")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_live_tests())
