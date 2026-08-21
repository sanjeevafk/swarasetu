"""Automated Playwright Video Recorder for SwaraSetu End-to-End Walkthrough."""

import os
import shutil
import subprocess
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

VIDEO_RAW_DIR = Path("/tmp/swarasetu_raw_video")
OUTPUT_VIDEO_PATH = Path("/home/sanjeev/Downloads/swarasetu/videos/swarasetu_e2e_walkthrough.mp4")
OUTPUT_VIDEO_PATH.parent.mkdir(parents=True, exist_ok=True)
if VIDEO_RAW_DIR.exists():
    shutil.rmtree(VIDEO_RAW_DIR)
VIDEO_RAW_DIR.mkdir(parents=True, exist_ok=True)


def inject_overlay_helpers(page):
    """Inject styling and DOM helper functions for title cards and callouts."""
    page.evaluate("""() => {
        if (document.getElementById('swara-overlay-root')) return;

        const overlayRoot = document.createElement('div');
        overlayRoot.id = 'swara-overlay-root';
        overlayRoot.style.position = 'fixed';
        overlayRoot.style.zIndex = '99999';
        overlayRoot.style.pointerEvents = 'none';
        overlayRoot.style.fontFamily = '"Outfit", "Plus Jakarta Sans", system-ui, sans-serif';
        document.body.appendChild(overlayRoot);

        window.showTitleCard = (title, subtitle, badge, durationMs) => {
            const card = document.createElement('div');
            card.className = 'swara-title-card';
            card.style.position = 'fixed';
            card.style.inset = '0';
            card.style.background = 'radial-gradient(circle at center, #0f172a 0%, #030712 100%)';
            card.style.display = 'flex';
            card.style.flexDirection = 'column';
            card.style.alignItems = 'center';
            card.style.justifyContent = 'center';
            card.style.color = '#ffffff';
            card.style.textAlign = 'center';
            card.style.padding = '40px';
            card.style.zIndex = '100000';
            card.style.transition = 'opacity 0.6s ease-in-out';
            card.style.opacity = '0';

            card.innerHTML = `
                <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #34d399; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; padding: 6px 18px; border-radius: 9999px; margin-bottom: 24px; display: inline-flex; align-items: center; gap: 8px;">
                    <span style="width: 8px; height: 8px; background: #10b981; border-radius: 50%; display: inline-block;"></span>
                    ${badge || 'SWARASETU DEMO'}
                </div>
                <h1 style="font-size: 46px; font-weight: 900; line-height: 1.15; margin: 0 0 16px 0; background: linear-gradient(135deg, #ffffff 0%, #a7f3d0 50%, #34d399 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 10px 30px rgba(16,185,129,0.2);">
                    ${title}
                </h1>
                <p style="font-size: 19px; color: #cbd5e1; max-width: 760px; margin: 0 0 28px 0; line-height: 1.6; font-weight: 400;">
                    ${subtitle}
                </p>
                <div style="width: 140px; height: 4px; background: linear-gradient(90deg, #10b981, #f59e0b); border-radius: 2px;"></div>
            `;

            document.getElementById('swara-overlay-root').appendChild(card);
            setTimeout(() => { card.style.opacity = '1'; }, 50);

            setTimeout(() => {
                card.style.opacity = '0';
                setTimeout(() => card.remove(), 600);
            }, durationMs - 600);
        };

        window.showCallout = (text, durationMs) => {
            const pill = document.createElement('div');
            pill.style.position = 'fixed';
            pill.style.bottom = '24px';
            pill.style.left = '50%';
            pill.style.transform = 'translateX(-50%) translateY(20px)';
            pill.style.background = 'rgba(15, 23, 42, 0.94)';
            pill.style.backdropFilter = 'blur(12px)';
            pill.style.border = '1px solid rgba(52, 211, 153, 0.5)';
            pill.style.color = '#ffffff';
            pill.style.padding = '12px 28px';
            pill.style.borderRadius = '9999px';
            pill.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.5), 0 0 20px rgba(16, 185, 129, 0.2)';
            pill.style.fontSize = '14px';
            pill.style.fontWeight = '600';
            pill.style.letterSpacing = '0.3px';
            pill.style.zIndex = '99999';
            pill.style.transition = 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
            pill.style.opacity = '0';
            pill.style.display = 'flex';
            pill.style.alignItems = 'center';
            pill.style.gap = '10px';
            pill.innerHTML = `<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#10b981; animation:pulse 1.5s infinite;"></span> ${text}`;

            document.getElementById('swara-overlay-root').appendChild(pill);
            setTimeout(() => {
                pill.style.opacity = '1';
                pill.style.transform = 'translateX(-50%) translateY(0)';
            }, 50);

            setTimeout(() => {
                pill.style.opacity = '0';
                pill.style.transform = 'translateX(-50%) translateY(20px)';
                setTimeout(() => pill.remove(), 400);
            }, durationMs - 400);
        };
    }""")


def display_title(page, title, subtitle, badge="SWARASETU", duration=4.0):
    page.evaluate(f"window.showTitleCard('{title}', '{subtitle}', '{badge}', {int(duration * 1000)})")
    time.sleep(duration)


def display_callout(page, text, duration=3.0):
    escaped_text = text.replace("'", "\\'")
    page.evaluate(f"window.showCallout('{escaped_text}', {int(duration * 1000)})")
    time.sleep(duration)


def record_walkthrough():
    print("=================================================================")
    print("🎬 RECORDING SWARASETU END-TO-END PRODUCT WALKTHROUGH VIDEO")
    print("=================================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=str(VIDEO_RAW_DIR),
            record_video_size={"width": 1280, "height": 800},
        )
        page = context.new_page()

        # Load App
        print("▶ Loading Application...")
        page.goto("http://localhost:5173", wait_until="networkidle")
        time.sleep(1.5)
        inject_overlay_helpers(page)

        # -------------------------------------------------------------
        # SCENE 0: INTRO TITLE CARD
        # -------------------------------------------------------------
        print("▶ Scene 0: Introduction Title Card...")
        display_title(
            page,
            title="SwaraSetu (स्वर सेतु)",
            subtitle="Your voice, your village, your first doctor.<br><br>End-to-End Walkthrough: Patient Triage · ASHA Offline Tablet · District Surveillance",
            badge="SMART INDIA HACKATHON 2026",
            duration=4.5,
        )

        # -------------------------------------------------------------
        # SCENE 1: PATIENT EXPERIENCE
        # -------------------------------------------------------------
        print("▶ Scene 1: Patient Experience...")
        display_title(
            page,
            title="Section 1: The Patient Experience",
            subtitle="Zero-barrier, voice-first clinical triage across native Indic languages (Hindi, Tamil, Bengali).",
            badge="SECTION 1: PATIENT",
            duration=3.5,
        )

        display_callout(page, "1.1 Landing Portal: Designed for rural citizens on 2G WhatsApp, IVRS, and Web.", duration=3.0)
        time.sleep(1)

        # Hover over core capability cards
        page.hover("text=Offline-First")
        time.sleep(0.6)
        page.hover("text=Voice AI")
        time.sleep(0.6)
        page.hover("text=IMCI Protocol")
        time.sleep(0.6)

        # Click As Patient
        display_callout(page, "1.2 Entering Patient Voice Portal...", duration=2.5)
        patient_btn = page.locator("button:has-text('As Patient')")
        patient_btn.hover()
        time.sleep(0.5)
        patient_btn.click()
        time.sleep(1.5)

        # 1.2 Voice Intake (Hindi Scenario - Score 2 / Yellow)
        display_callout(page, "1.3 Simulating Patient Voice Note intake in Hindi (Fever & Cough)...", duration=3.5)
        mic_btn = page.locator("button:has(svg.lucide-mic)").first
        mic_btn.hover()
        time.sleep(0.5)
        mic_btn.click()
        time.sleep(5.5)

        display_callout(page, "1.4 IMCI Decision Tree evaluates symptoms -> Score 2 (ASHA Worker Dispatched within 24h).", duration=4.0)
        time.sleep(2)

        # 1.3 Custom Text Entry (Acute Emergency - Score 3 / Red)
        display_callout(page, "1.5 Testing Live Custom Text: Patient reports acute chest pain & vomiting blood...", duration=3.5)
        chat_input = page.locator("input[placeholder*='Type symptoms']")
        chat_input.click()
        time.sleep(0.5)
        
        # Type deliberately
        query = "Patient has severe chest pain and vomiting blood"
        for char in query:
            chat_input.type(char, delay=35)
        time.sleep(0.6)

        send_btn = page.locator("button:has(svg.lucide-send)").first
        send_btn.hover()
        time.sleep(0.4)
        send_btn.click()
        time.sleep(2.5)

        display_callout(page, "1.6 Live IMCI Evaluation -> Score 3 (Immediate Red Emergency Referral).", duration=3.5)
        time.sleep(1.5)

        # 1.4 Spatial Health Facility Navigation (Nearest PHC)
        display_callout(page, "1.7 Patient clicks 'Find Nearest PHC' to locate closest emergency care facility...", duration=3.5)
        find_phc_btn = page.locator("button:has-text('Find Nearest PHC'), button:has-text('Nearest PHC')").first
        if find_phc_btn.is_visible():
            find_phc_btn.hover()
            time.sleep(0.5)
            find_phc_btn.click()
            time.sleep(3.0)

            display_callout(page, "📍 Interactive GIS routing calculates Haversine distance (~4.2 km) with Doctor Availability.", duration=3.5)
            time.sleep(2)

            close_btn = page.locator(".absolute.top-4.right-4 button, button:has(svg.lucide-x)").first
            if close_btn.is_visible():
                close_btn.click(force=True)
                time.sleep(1.5)

        # 1.5 Quick Suggestion Chip Testing (Mild Fever / Self Care)
        display_callout(page, "1.8 Testing 1-click Quick Suggestion Chip: Mild Fever (1 day)...", duration=3.5)
        fever_chip = page.locator("button:has-text('Mild Fever')").first
        if fever_chip.is_visible():
            fever_chip.hover()
            time.sleep(0.5)
            fever_chip.click(force=True)
            time.sleep(2.5)
            display_callout(page, "🟢 Result: Score 1 (Self-Care & Home Monitoring Guidance).", duration=3.0)
            time.sleep(1.5)

        # -------------------------------------------------------------
        # SCENE 2: ASHA WORKER (WORKER) EXPERIENCE
        # -------------------------------------------------------------
        print("▶ Scene 2: ASHA Worker Experience...")
        display_title(
            page,
            title="Section 2: The ASHA Worker Experience",
            subtitle="Frontline field tablet application operating 100% offline with on-device IMCI logic & background sync.",
            badge="SECTION 2: WORKER",
            duration=3.5,
        )

        display_callout(page, "2.1 ASHA Worker opens frontline tablet: Views pending village home-visit roster.", duration=3.5)
        asha_tab = page.locator("button[role='tab']:has-text('ASHA Tablet')")
        asha_tab.hover()
        time.sleep(0.5)
        asha_tab.click(force=True)
        time.sleep(2.5)

        # 2.2 Offline Mode Activation
        display_callout(page, "2.2 ASHA worker enters media-dark rural village with 0% cellular signal...", duration=3.5)
        offline_switch = page.locator("button[role='switch']").first
        offline_switch.hover()
        time.sleep(0.5)
        offline_switch.click(force=True)
        time.sleep(2.0)

        display_callout(page, "📴 Offline Mode Active: Triage runs 100% on-device CPU, queueing cases in IndexedDB.", duration=4.0)
        time.sleep(2)

        # 2.3 On-Device Edge Triage
        display_callout(page, "2.3 Performing on-device field assessment for village patient without internet...", duration=3.5)
        cough_chip = page.locator("button:has-text('Cough & Breathing')").first
        if cough_chip.is_visible():
            cough_chip.hover()
            time.sleep(0.5)
            cough_chip.click(force=True)
            time.sleep(3.0)

        display_callout(page, "⚡ On-Device IMCI Engine confirms Score 2 & saves case to local IndexedDB queue.", duration=3.5)
        time.sleep(2)

        # 2.4 Reconnection & Auto-Sync
        display_callout(page, "2.4 ASHA Worker returns to connectivity: System triggers automatic background sync...", duration=3.5)
        offline_switch.click(force=True)
        time.sleep(3.0)
        display_callout(page, "✅ Background Sync Complete: All offline cases flushed to central district database.", duration=3.5)
        time.sleep(1.5)

        # -------------------------------------------------------------
        # SCENE 3: OFFICIAL / ADMIN (SUPERVISOR) EXPERIENCE
        # -------------------------------------------------------------
        print("▶ Scene 3: Supervisor & Admin Experience...")
        display_title(
            page,
            title="Section 3: The Official & Admin Experience",
            subtitle="District-level health surveillance, epidemiological outbreak monitoring, and ABDM facility coordination.",
            badge="SECTION 3: OFFICIAL / ADMIN",
            duration=3.5,
        )

        display_callout(page, "3.1 District Chief Medical Officer opens Health Surveillance Dashboard.", duration=3.5)
        supervisor_tab = page.locator("button[role='tab']:has-text('Supervisor')")
        supervisor_tab.hover()
        time.sleep(0.5)
        supervisor_tab.click(force=True)
        time.sleep(2.5)

        # 3.2 District Volume & Outbreaks
        display_callout(page, "3.2 Real-time triage volume by district (Sitamarhi, Sheohar, Muzaffarpur, Darbhanga)...", duration=3.5)
        page.hover("text=Regional Overview")
        time.sleep(2)

        # 3.3 Disease Distribution & Escalation Trend
        display_callout(page, "3.3 Syndromic breakdown: Monitoring Fever (45%), Respiratory (30%), Diarrhoea (15%) spikes.", duration=4.0)
        time.sleep(2.5)

        # 3.4 Reviewing Recent Cases & Emergency Logs
        display_callout(page, "3.4 Auditing live cases, emergency red flags, and ASHA field assignments...", duration=3.5)
        page.hover("text=Recent Cases")
        time.sleep(3)

        # -------------------------------------------------------------
        # SCENE 4: CONCLUSION
        # -------------------------------------------------------------
        print("▶ Scene 4: Conclusion...")
        display_title(
            page,
            title="SwaraSetu: The Zero-Barrier Voice Bridge",
            subtitle="✓ Patient: Native Indic Voice & Text Triage (0% Literacy Barrier)<br>✓ Worker: 100% Offline Tablet with On-Device IMCI & Auto-Sync<br>✓ Admin: Real-Time Epidemiological Surveillance & ABDM GIS Routing",
            badge="WALKTHROUGH COMPLETE",
            duration=5.0,
        )

        time.sleep(1)
        context.close()
        browser.close()

    print("\n▶ Processing recorded video with ffmpeg...")
    raw_videos = list(VIDEO_RAW_DIR.glob("*.webm"))
    if not raw_videos:
        print("❌ Error: No raw video found!")
        return

    raw_video = raw_videos[0]
    print(f"  Raw video file: {raw_video}")

    # Convert to web-optimized MP4 with H.264 video codec and high compatibility
    cmd = [
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(OUTPUT_VIDEO_PATH),
    ]
    subprocess.run(cmd, check=True)

    # Also keep a copy in brain artifacts directory for direct embedding
    artifact_dir = Path("/home/sanjeev/.gemini/antigravity-cli/brain/25070af2-df49-4926-b59b-d639bf4ec397")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(OUTPUT_VIDEO_PATH, artifact_dir / "swarasetu_e2e_walkthrough.mp4")

    print("\n=================================================================")
    print(f"✅ VIDEO RECORDING COMPLETE & OPTIMIZED!")
    print(f"🎥 Output MP4: {OUTPUT_VIDEO_PATH}")
    print(f"📁 File size: {OUTPUT_VIDEO_PATH.stat().st_size / (1024 * 1024):.2f} MB")
    print("=================================================================")


if __name__ == "__main__":
    record_walkthrough()
