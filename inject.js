(() => {
  if (window.__tl_injector__ && window.__tl_injector__.scan) {
    window.__tl_injector__.scan();
    return;
  }

  const HOOK_URL = "http://localhost:5000/hook";
  const mark = "data-tl-hooked";

  function send(eventName, detail) {
    const payload = JSON.stringify({
      event: eventName,
      detail: detail || {},
      ts: Date.now(),
    });
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(HOOK_URL, payload);
        return;
      }
    } catch (e) {
      // ignore
    }
    try {
      fetch(HOOK_URL, {
        method: "POST",
        mode: "no-cors",
        headers: { "Content-Type": "application/json" },
        body: payload,
      });
    } catch (e) {
      // ignore
    }
  }

  function isApproveButton(el) {
    if (!el) return false;
    const txt = (el.innerText || el.textContent || "").trim().toLowerCase();
    if (!txt) return false;
    if (txt === "approve") return true;
    return txt.includes("approve");
  }

  function hookButton(btn) {
    if (btn.getAttribute(mark) === "1") return;
    btn.setAttribute(mark, "1");
    btn.addEventListener(
      "click",
      () => {
        send("approve_clicked", { text: (btn.innerText || "").trim() });
      },
      true
    );
  }

  function scan() {
    const buttons = Array.from(
      document.querySelectorAll(
        "button, [role='button'], input[type='button'], input[type='submit']"
      )
    );
    buttons.filter(isApproveButton).forEach(hookButton);
  }

  scan();

  const observer = new MutationObserver(() => scan());
  observer.observe(document.body, { childList: true, subtree: true });

  window.__tl_injector__ = { scan };
})();
