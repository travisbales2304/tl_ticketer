# ThreatLocker Injector (Selenium)

This app launches a Chrome session via Selenium, injects JavaScript into the ThreatLocker UI, and prints details when the **Approve** button is clicked.

## How it works
- Starts Chrome (via chromedriver) and opens ThreatLocker.
- A JS injector runs on an interval, attaching a click handler to any Approve button.
- When clicked, it captures all `p.text-600.break-word.select-all` text and prints it.

## Setup
1. Install dependencies (global or user site):

```bash
python -m pip install --user -r requirements.txt
```

2. Copy `.env.example` to `.env` and set any needed values (especially `USER_DATA_DIR` if you want a persistent profile).

3. Run:

```bash
python app.py
```

## Notes
- If you want to use your normal Chrome profile, **close all Chrome windows first**, or use a dedicated profile folder via `USER_DATA_DIR`.
- To avoid Selenium Manager (and `cmd.exe`/`reg.exe`), put `chromedriver.exe` in this folder or set `CHROMEDRIVER_PATH` in `.env`.
- The injector uses a MutationObserver so buttons added later are also hooked.
