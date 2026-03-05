import os
import sys
import yaml
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, expect
from directives import run_step
from utils import safe_name, ensure_dir, copy_overwrite

ARTIFACTS_DIR = "qa/artifacts"
VIDEO_DIR = f"{ARTIFACTS_DIR}/videos"
TRACE_DIR = f"{ARTIFACTS_DIR}/traces"
DEFAULT_BASE_URL = os.getenv("BASE_URL", "http://frontend:5173")

def run_test(test_path: str, headed=False, base_url=None):
    """Run a YAML test using Playwright."""
    with open(test_path, "r") as f:
        test_data = yaml.safe_load(f)

    test_name = test_data.get("name", "Unnamed Test")
    base_url = base_url or test_data.get("base_url", DEFAULT_BASE_URL)
    steps = test_data.get("steps", [])

    print(f"Running test: {test_name}")
    ensure_dir(ARTIFACTS_DIR)
    ensure_dir(VIDEO_DIR)
    ensure_dir(TRACE_DIR)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(record_video_dir=VIDEO_DIR)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        try:
            for step_idx, step in enumerate(steps, 1):
                print(f"STEP {step_idx}: ", end="")
                run_step(page, base_url, step)
            
            print("TEST PASSED")
            success = True
        except Exception as e:
            print(f"TEST FAILED: {e}")
            screenshot_path = f"{ARTIFACTS_DIR}/failure_{safe_name(test_name)}_step_{step_idx}.png"
            page.screenshot(path=screenshot_path)
            trace_path = f"{ARTIFACTS_DIR}/trace_{safe_name(test_name)}_step_{step_idx}.zip"
            context.tracing.stop(path=trace_path)
            success = False
        finally:
            video_path = page.video.path() if page.video else None
            context.close()
            browser.close()

            if success and video_path:
                copy_overwrite(video_path, f"{ARTIFACTS_DIR}/last_pass.webm")
            
            # Optionally cleanup video dir if needed, but last_pass.webm is kept

    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run QA YAML tests.")
    parser.add_argument("test_path", help="Path to the YAML test file")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode")
    parser.add_argument("--base-url", help="Override the base URL for the test")
    args = parser.parse_args()

    success = run_test(args.test_path, headed=args.headed, base_url=args.base_url)
    sys.exit(0 if success else 1)
