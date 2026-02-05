(() => {
  if (window.__tl_injector__ && window.__tl_injector__.scan) {
    window.__tl_injector__.scan();
    return;
  }

  const mark = "data-tl-hooked";

  function recordEvent(eventName, detail) {
    window.__tl_last_event = {
      event: eventName,
      detail: detail || {},
      ts: Date.now(),
    };
  }

  function isApproveButton(el) {
    if (!el) return false;
    const txt = (el.innerText || el.textContent || "").trim().toLowerCase();
    if (!txt) return false;
    if (txt === "approve") return true;
    return txt.includes("approve");
  }

  function hookButton(btn, labelText) {
    if (btn.getAttribute(mark) === "1") return;
    btn.setAttribute(mark, "1");
    console.log("[TL] Hooked approve button:", labelText || (btn.innerText || "").trim());
    btn.addEventListener(
      "click",
      () => {
        console.log("[TL] Approve clicked:", labelText || (btn.innerText || "").trim());
        const texts = Array.from(
          document.querySelectorAll("p.text-600.break-word.select-all")
        )
          .map((el) => (el.innerText || el.textContent || "").trim())
          .filter((txt) => txt.length > 0);
        const allowedLabels = new Set([
          "Computer Group",
          "This Computer",
          "Entire Organization",
          "Permit Application",
          "Permit with Ringfencing",
          "Do not Elevate",
          "Elevate",
          "Silent Elevation",
        ]);
        const highlighted = Array.from(
          document.querySelectorAll(
            "div.p-ripple.p-element.p-button.p-component.ng-star-inserted.p-highlight"
          )
        )
          .map((el) => (el.getAttribute("aria-label") || "").trim())
          .filter((label) => allowedLabels.has(label));
        const slider = document.querySelector("div.mt-2.px-5");
        const sliderValue = slider
          ? (slider.querySelector("p.text-center.mb-2")?.innerText || "").trim()
          : "";
        recordEvent("approve_clicked", {
          text: (labelText || btn.innerText || "").trim(),
          details: texts,
          highlighted,
          expiration: sliderValue,
        });
      },
      true
    );
  }

  function findClickable(el) {
    if (!el) return null;
    if (el.tagName === "BUTTON") return el;
    if (el.getAttribute && el.getAttribute("role") === "button") return el;
    if (el.tagName === "INPUT" && (el.type === "button" || el.type === "submit")) return el;
    return el.closest
      ? el.closest("button, [role='button'], input[type='button'], input[type='submit']")
      : null;
  }

  function scan() {
    const candidates = Array.from(
      document.querySelectorAll(
        "button, [role='button'], input[type='button'], input[type='submit'], .p-button-label"
      )
    );
    candidates.forEach((el) => {
      if (!isApproveButton(el)) return;
      const labelText = (el.innerText || el.textContent || "").trim();
      const clickable = findClickable(el) || el;
      hookButton(clickable, labelText);
    });
  }

  scan();

  const observer = new MutationObserver(() => scan());
  observer.observe(document.body, { childList: true, subtree: true });

  window.__tl_injector__ = { scan };
})();
