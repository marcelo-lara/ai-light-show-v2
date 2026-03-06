import os
import sys
import yaml
import argparse
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, expect
from directives import run_step
from utils import safe_name, ensure_dir, copy_overwrite, rotate_artifacts

ARTIFACTS_DIR = "qa/artifacts"
VIDEO_DIR = f"{ARTIFACTS_DIR}/videos"
TRACE_DIR = f"{ARTIFACTS_DIR}/traces"
LAST_RUN_LOG = f"{ARTIFACTS_DIR}/last_run.log"
DEFAULT_BASE_URL = os.getenv("BASE_URL", "http://frontend:5173")

def run_test(test_path: str, headed=False, base_url=None):
    """Run a YAML test using Playwright."""
    with open(test_path, "r") as f:
        test_data = yaml.safe_load(f)

    test_name = test_data.get("name", "Unnamed Test")
    base_url = base_url or test_data.get("base_url", DEFAULT_BASE_URL)
    steps = test_data.get("steps", [])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_slug = safe_name(test_name)

    print(f"Running test: {test_name}")
    ensure_dir(ARTIFACTS_DIR)
    ensure_dir(VIDEO_DIR)
    ensure_dir(TRACE_DIR)

    summary = {
        "test_name": test_name,
        "timestamp": timestamp,
        "base_url": base_url,
        "steps_total": len(steps),
        "steps_completed": 0,
        "status": "IN_PROGRESS",
        "error": None,
        "artifacts": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(record_video_dir=VIDEO_DIR)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        try:
            for step_idx, step in enumerate(steps, 1):
                print(f"STEP {step_idx}: ", end="")
                run_step(page, base_url, step)
                summary["steps_completed"] = step_idx
            
            print("TEST PASSED")
            summary["status"] = "PASSED"
            success = True
        except Exception as e:
            print(f"TEST FAILED: {e}")
            summary["status"] = "FAILED"
            summary["error"] = str(e)
            
            screenshot_path = f"{ARTIFACTS_DIR}/{timestamp}_{test_slug}_fail_step_{step_idx}.png"
            page.screenshot(path=screenshot_path)
            summary["artifacts"]["screenshot"] = screenshot_path
            
            trace_path = f"{ARTIFACTS_DIR}/{timestamp}_{test_slug}_trace_step_{step_idx}.zip"
            context.tracing.stop(path=trace_path)
            summary["artifacts"]["trace"] = trace_path
            
            rotate_artifacts(ARTIFACTS_DIR, "*_fail_*.png", 5)
            rotate_artifacts(ARTIFACTS_DIR, "*_trace_*.zip", 5)
            success = False
        finally:
            video_path = page.video.path() if page.video else None
            context.close()
            browser.close()

            if success and video_path:
                pass_video = f"{ARTIFACTS_DIR}/{timestamp}_{test_slug}_pass.webm"
                copy_overwrite(video_path, pass_video)
                copy_overwrite(video_path, f"{ARTIFACTS_DIR}/last_pass.webm")
                summary["artifacts"]["video"] = pass_video
                rotate_artifacts(ARTIFACTS_DIR, "*_pass.webm", 5)
            
            with open(LAST_RUN_LOG, "w") as f:
                json.dump(summary, f, indent=2)

    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run QA YAML tests.")
    parser.add_argument("test_path", help="Path to the YAML test file")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode")
    parser.add_argument("--base-url", help="Override the base URL for the test")
    args = parser.parse_args()

    success = run_test(args.test_path, headed=args.headed, base_url=args.base_url)
    sys.exit(0 if success else 1)
