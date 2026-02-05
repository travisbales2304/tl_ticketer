from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

APP_ROOT = Path(__file__).resolve().parent
INJECT_JS_PATH = APP_ROOT / "inject.js"
LOCAL_CHROMEDRIVER = APP_ROOT / "chromedriver.exe"
TIME_SAVED_PATH = APP_ROOT / "time_saved.json"


def _load_config() -> dict:
    return {
        "THREATLOCKER_URL": os.getenv("THREATLOCKER_URL", "https://portal.threatlocker.com/"),
        "HEADLESS": os.getenv("HEADLESS", "false").lower() == "true",
        "USER_DATA_DIR": os.getenv("USER_DATA_DIR"),
        "PROFILE_DIR": os.getenv("PROFILE_DIR"),
        "CHROME_BINARY": os.getenv("CHROME_BINARY"),
        "CHROMEDRIVER_PATH": os.getenv("CHROMEDRIVER_PATH"),
        "INJECT_INTERVAL_SEC": int(os.getenv("INJECT_INTERVAL_SEC", "5")),
        "POLL_INTERVAL_SEC": float(os.getenv("POLL_INTERVAL_SEC", "0.5")),
        "MAX_EVENTS": int(os.getenv("MAX_EVENTS", "200")),
    }


def _build_options(cfg: dict) -> Options:
    options = Options()
    if cfg["HEADLESS"]:
        options.add_argument("--headless=new")
    if cfg["USER_DATA_DIR"]:
        options.add_argument(f"--user-data-dir={cfg['USER_DATA_DIR']}")
    if cfg["PROFILE_DIR"]:
        options.add_argument(f"--profile-directory={cfg['PROFILE_DIR']}")
    if cfg["CHROME_BINARY"]:
        options.binary_location = cfg["CHROME_BINARY"]
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--start-maximized")
    return options


def _resolve_chromedriver(cfg: dict) -> Optional[str]:
    if cfg["CHROMEDRIVER_PATH"]:
        return cfg["CHROMEDRIVER_PATH"]
    if LOCAL_CHROMEDRIVER.exists():
        return str(LOCAL_CHROMEDRIVER)
    return None


def _start_driver() -> webdriver.Chrome:
    cfg = _load_config()
    options = _build_options(cfg)
    chromedriver = _resolve_chromedriver(cfg)
    service = Service(chromedriver) if chromedriver else Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(cfg["THREATLOCKER_URL"])
    return driver


def _read_inject_js() -> str:
    return INJECT_JS_PATH.read_text(encoding="utf-8")


def _try_inject(driver: webdriver.Chrome) -> None:
    js = _read_inject_js()
    driver.execute_script(js)


def _poll_event(driver: webdriver.Chrome) -> Optional[Dict[str, Any]]:
    try:
        event = driver.execute_script("return window.__tl_last_event || null;")
        if isinstance(event, dict):
            return event
    except WebDriverException:
        return None
    return None


def _append_event(events: List[Dict[str, Any]], event: Dict[str, Any], max_events: int) -> None:
    events.append(event)
    if len(events) > max_events:
        del events[: len(events) - max_events]


def _load_time_saved() -> Dict[str, List[Dict[str, str]]]:
    if not TIME_SAVED_PATH.exists():
        return {}
    try:
        data = json.loads(TIME_SAVED_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {}


def _save_time_saved(data: Dict[str, List[Dict[str, str]]]) -> None:
    TIME_SAVED_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _record_time_saved(application_name: str) -> None:
    date_key = time.strftime("%Y-%m-%d")
    data = _load_time_saved()
    entry = {"2": application_name}
    bucket = data.get(date_key)
    if not isinstance(bucket, list):
        bucket = []
        data[date_key] = bucket
    bucket.append(entry)
    _save_time_saved(data)


def run() -> None:
    cfg = _load_config()
    driver = _start_driver()
    last_event_ts = 0
    last_inject = 0.0
    events: List[Dict[str, Any]] = []

    print("Chrome launched. Waiting for Approve clicks...")
    try:
        while True:
            now = time.time()
            if now - last_inject >= cfg["INJECT_INTERVAL_SEC"]:
                try:
                    _try_inject(driver)
                except WebDriverException:
                    pass
                last_inject = now

            event = _poll_event(driver)
            if event:
                ts = int(event.get("ts") or 0)
                if ts > last_event_ts:
                    last_event_ts = ts
                    _append_event(events, event, cfg["MAX_EVENTS"])
                    print(f"ThreatLocker event: {event}")
                    details = event.get("detail", {}).get("details")
                    if isinstance(details, list):
                        for item in details:
                            print(f"ThreatLocker detail: {item}")
                    app_name = str(event.get("detail", {}).get("applicationName") or "N/A")
                    _record_time_saved(app_name)

            time.sleep(cfg["POLL_INTERVAL_SEC"])
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        try:
            driver.quit()
        except WebDriverException:
            pass


if __name__ == "__main__":
    run()
