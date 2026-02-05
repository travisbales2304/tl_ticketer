from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

APP_ROOT = Path(__file__).resolve().parent
INJECT_JS_PATH = APP_ROOT / "inject.js"

app = Flask(__name__)

_driver_lock = threading.Lock()
_driver: Optional[webdriver.Chrome] = None
_injector_thread: Optional[threading.Thread] = None
_stop_injector = threading.Event()
_last_event_ts: int = 0


def _load_config() -> dict:
    return {
        "THREATLOCKER_URL": os.getenv("THREATLOCKER_URL", "https://portal.threatlocker.com/"),
        "HEADLESS": os.getenv("HEADLESS", "false").lower() == "true",
        "USER_DATA_DIR": os.getenv("USER_DATA_DIR"),
        "PROFILE_DIR": os.getenv("PROFILE_DIR"),
        "CHROME_BINARY": os.getenv("CHROME_BINARY"),
        "CHROMEDRIVER_PATH": os.getenv("CHROMEDRIVER_PATH"),
        "INJECT_INTERVAL_SEC": int(os.getenv("INJECT_INTERVAL_SEC", "5")),
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


def _start_driver() -> webdriver.Chrome:
    cfg = _load_config()
    options = _build_options(cfg)
    service = Service(cfg["CHROMEDRIVER_PATH"]) if cfg["CHROMEDRIVER_PATH"] else Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(cfg["THREATLOCKER_URL"])
    return driver


def _read_inject_js() -> str:
    return INJECT_JS_PATH.read_text(encoding="utf-8")


def _try_inject(driver: webdriver.Chrome) -> None:
    js = _read_inject_js()
    driver.execute_script(js)


def _injector_loop() -> None:
    cfg = _load_config()
    interval = cfg["INJECT_INTERVAL_SEC"]
    global _last_event_ts
    while not _stop_injector.is_set():
        with _driver_lock:
            driver = _driver
        if driver is None:
            time.sleep(0.5)
            continue
        try:
            _try_inject(driver)
            event = driver.execute_script("return window.__tl_last_event || null;")
            if event and isinstance(event, dict):
                ts = int(event.get("ts") or 0)
                if ts > _last_event_ts:
                    _last_event_ts = ts
                    app.logger.info("ThreatLocker event: %s", event)
                    print(f"ThreatLocker event: {event}")
                    details = event.get("detail", {}).get("details")
                    if isinstance(details, list):
                        for item in details:
                            app.logger.info("ThreatLocker detail: %s", item)
                            print(f"ThreatLocker detail: {item}")
        except WebDriverException:
            pass
        time.sleep(interval)


def _ensure_injector_thread() -> None:
    global _injector_thread
    if _injector_thread and _injector_thread.is_alive():
        return
    _stop_injector.clear()
    _injector_thread = threading.Thread(target=_injector_loop, daemon=True)
    _injector_thread.start()


@app.route("/start", methods=["POST"])
def start():
    global _driver
    with _driver_lock:
        if _driver is not None:
            return jsonify({"status": "already_running"})
        _driver = _start_driver()
    _ensure_injector_thread()
    return jsonify({"status": "started"})


@app.route("/stop", methods=["POST"])
def stop():
    global _driver
    with _driver_lock:
        driver = _driver
        _driver = None
    _stop_injector.set()
    if driver is not None:
        try:
            driver.quit()
        except WebDriverException:
            pass
    return jsonify({"status": "stopped"})


@app.route("/status", methods=["GET"])
def status():
    with _driver_lock:
        running = _driver is not None
    return jsonify({"running": running})


@app.route("/hook", methods=["POST"])
def hook():
    raw = request.get_data(as_text=True) or ""
    payload = None
    if raw:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw}
    app.logger.info("ThreatLocker event: %s", payload)
    return ("", 204)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "start":
            with _driver_lock:
                if _driver is None:
                    _driver = _start_driver()
            _ensure_injector_thread()
            print("Started Selenium session.")
        elif cmd == "stop":
            with _driver_lock:
                driver = _driver
                _driver = None
            _stop_injector.set()
            if driver is not None:
                try:
                    driver.quit()
                except WebDriverException:
                    pass
            print("Stopped Selenium session.")
        else:
            print("Unknown command. Use: python app.py start|stop")
    else:
        app.run(host="127.0.0.1", port=5000, debug=True)
