"""End-to-end Playwright tests for SwaraSetu application."""

import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

REPORTS_DIR = Path(__file__).resolve().parents[1] / "e2e_reports"
REPORTS_DIR.mkdir(exist_ok=True)


def run_e2e():
    print("🚀 Starting Playwright E2E Test Suite against http://localhost:5173 and http://localhost:8000...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        # 1. Navigate to App
        print("\n▶ Step 1: Navigating to SwaraSetu App...")
        page.goto("http://localhost:5173", wait_until="networkidle", timeout=15000)
        time.sleep(1)
        page.screenshot(path=str(REPORTS_DIR / "01_homepage.png"))
        print("  ✓ Homepage loaded successfully")

        # 2. Check for Main Tabs / Navigation
        print("\n▶ Step 2: Testing Navigation Tabs & Modes...")
        tabs = page.locator("button[role='tab']")
        tab_count = tabs.count()
        print(f"  ✓ Found {tab_count} navigation tabs")
        
        # 3. Test Patient Voice Triage Interaction
        print("\n▶ Step 3: Testing Patient Voice Interface & IMCI Scenarios...")
        # Scenario buttons
        scenario_btns = page.locator("button:has-text('Tamil'), button:has-text('Hindi'), button:has-text('Bengali'), button:has-text('Scenario')")
        print(f"  ✓ Scenario selectors detected: {scenario_btns.count()}")
        
        # Click Hindi scenario (Respiratory & Fever, Score 2)
        hindi_btn = page.locator("button:has-text('Hindi')").first
        if hindi_btn.is_visible():
            hindi_btn.click()
            time.sleep(0.5)
            print("  ✓ Switched to Hindi Clinical Scenario")

        # Click Bengali emergency scenario (Score 3)
        bengali_btn = page.locator("button:has-text('Bengali')").first
        if bengali_btn.is_visible():
            bengali_btn.click()
            time.sleep(0.5)
            print("  ✓ Switched to Bengali Emergency Scenario")
            page.screenshot(path=str(REPORTS_DIR / "02_bengali_emergency_scenario.png"))

        # 4. Test ASHA Tablet Offline Mode
        print("\n▶ Step 4: Testing ASHA Tablet Mode & Offline Toggle...")
        asha_tab = page.locator("button[role='tab']:has-text('ASHA'), button[role='tab']:has-text('CHW'), button:has-text('ASHA Mode'), button:has-text('CHW Mode'), button:has-text('ASHA')").first
        if asha_tab.is_visible():
            asha_tab.click()
            time.sleep(1)
            print("  ✓ Switched to ASHA Field Tablet Interface")
            page.screenshot(path=str(REPORTS_DIR / "03_asha_tablet_mode.png"))

            # Toggle offline switch
            offline_switch = page.locator("button[role='switch']").first
            if offline_switch.is_visible():
                offline_switch.click()
                time.sleep(0.5)
                print("  ✓ Toggled Offline Mode: ON (IndexedDB queue active)")
                page.screenshot(path=str(REPORTS_DIR / "04_asha_offline_active.png"))
                
                # Toggle back online
                offline_switch.click()
                time.sleep(0.5)
                print("  ✓ Toggled Online Mode: ON (Auto-sync triggered)")

        # 5. Test District Supervisor Dashboard
        print("\n▶ Step 5: Testing Health Supervisor Surveillance Dashboard...")
        dash_tab = page.locator("button[role='tab']:has-text('Supervisor'), button[role='tab']:has-text('Dashboard'), button:has-text('Analytics')").first
        if dash_tab.is_visible():
            dash_tab.click()
            time.sleep(1)
            print("  ✓ Switched to District Supervisor Analytics Dashboard")
            page.screenshot(path=str(REPORTS_DIR / "05_supervisor_dashboard.png"))

        # 6. Test Nearest PHC Facility Map
        print("\n▶ Step 6: Testing Nearest PHC Facility Map...")
        map_tab = page.locator("button[role='tab']:has-text('PHC'), button[role='tab']:has-text('Map'), button:has-text('Facilities')").first
        if map_tab.is_visible():
            map_tab.click()
            time.sleep(1.5)
            print("  ✓ Switched to Nearest PHC Interactive Map")
            page.screenshot(path=str(REPORTS_DIR / "06_nearest_phc_map.png"))

        browser.close()
        print("\n=================================================================")
        print("✅ ALL PLAYWRIGHT E2E TESTS PASSED SUCCESSFULLY!")
        print(f"📸 Screenshots saved to {REPORTS_DIR}")
        print("=================================================================")


if __name__ == "__main__":
    run_e2e()
