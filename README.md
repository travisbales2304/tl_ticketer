# ThreatLocker Injector (Flask + Selenium)

This app launches a Chrome session via Selenium, injects JavaScript into the ThreatLocker UI, and listens for clicks on the **Approve** button. For now it logs events to the Flask server; we can wire this to ConnectWise later.

## How it works
- `/start` launches Chrome (via chromedriver) and opens ThreatLocker.
- A JS injector runs on an interval, attaching a click handler to any Approve button.
- When clicked, the page posts a payload to `http://localhost:5000/hook`.

## Setup
1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and set any needed values (especially `USER_DATA_DIR` if you want a persistent profile).

3. Start the Flask server:

```bash
python app.py
```

4. In another terminal, start the browser:

```bash
curl -X POST http://localhost:5000/start
```

## Notes
- If you want to use your normal Chrome profile, **close all Chrome windows first**, or use a dedicated profile folder via `USER_DATA_DIR`.
- The injector uses a MutationObserver so buttons added later are also hooked.
- This is intentionally minimal; we can improve selector specificity once you confirm what the Approve button looks like in your instance.
