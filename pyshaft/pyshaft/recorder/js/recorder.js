/**
 * PyShaft Recorder — Event Capture Script
 *
 * Injected into the browser page to capture user interactions.
 * Events are sent back to Python via console.log("__PYSHAFT_EVENT__:" + JSON)
 */
(function () {
  if (window.__pyshaft_recorder) {
    window.__pyshaft_recorder.resume();
    return;
  }

  const DEBOUNCE_MS = 300;
  let _paused = false;
  let _lastTypeEvent = null;
  let _typeTimer = null;

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  function getElementMeta(el) {
    if (!el || !el.tagName) return null;

    const rect = el.getBoundingClientRect();
    const styles = window.getComputedStyle(el);

    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || "",
      class: Array.from(el.classList || []),
      text: (el.innerText || "").trim().substring(0, 200),
      role: el.getAttribute("role") || el.tagName.toLowerCase(),
      "aria-label": el.getAttribute("aria-label") || "",
      placeholder: el.getAttribute("placeholder") || "",
      "data-testid":
        el.getAttribute("data-testid") ||
        el.getAttribute("data-test-id") ||
        el.getAttribute("data-qa") ||
        el.getAttribute("data-cy") ||
        "",
      name: el.getAttribute("name") || "",
      type: el.getAttribute("type") || "",
      href: el.getAttribute("href") || "",
      value: el.value || "",
      title: el.getAttribute("title") || "",
      alt: el.getAttribute("alt") || "",
      src: el.getAttribute("src") || "",
      checked: el.checked || false,
      disabled: el.disabled || false,
      visible: styles.display !== "none" && styles.visibility !== "hidden",
      rect: {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
      url: window.location.href,
      // Parent info for inside() hints
      parentId: el.parentElement ? el.parentElement.id : "",
      parentTag: el.parentElement ? el.parentElement.tagName.toLowerCase() : "",
      parentRole: el.parentElement
        ? el.parentElement.getAttribute("role") || ""
        : "",
      isIframe: window !== window.top,
      frameId: window.name || window.location.href,
    };
  }

  function generateLocators(meta) {
    const locators = [];

    // data-testid (most stable)
    if (meta["data-testid"]) {
      locators.push({
        type: "testid",
        value: meta["data-testid"],
        stability: "high",
        score: 100,
      });
    }

    // ID
    if (meta.id) {
      locators.push({
        type: "id",
        value: meta.id,
        stability: "high",
        score: 95,
      });
    }

    // Role (ARIA or inferred)
    if (meta.role && meta.role !== meta.tag) {
      locators.push({
        type: "role",
        value: meta.role,
        stability: "high",
        score: 90,
      });
    }

    // Placeholder
    if (meta.placeholder) {
      locators.push({
        type: "placeholder",
        value: meta.placeholder,
        stability: "medium",
        score: 80,
      });
    }

    // aria-label
    if (meta["aria-label"]) {
      locators.push({
        type: "label",
        value: meta["aria-label"],
        stability: "medium",
        score: 75,
      });
    }

    // Text (exact)
    if (meta.text && meta.text.length <= 50) {
      locators.push({
        type: "text",
        value: meta.text,
        modifier: "exact",
        stability: "medium",
        score: 70,
      });
    }

    // Text (contain) for longer text
    if (meta.text && meta.text.length > 10) {
      const shortText = meta.text.substring(0, 30);
      locators.push({
        type: "text",
        value: shortText,
        modifier: "contain",
        stability: "low",
        score: 50,
      });
    }

    // Name attribute
    if (meta.name) {
      locators.push({
        type: "attr",
        value: meta.name,
        stability: "medium",
        score: 65,
      });
    }

    // CSS selector (generated)
    let cssSelector = meta.tag;
    if (meta.id) cssSelector = "#" + meta.id;
    else if (meta.class.length > 0) cssSelector = meta.tag + "." + meta.class[0];
    locators.push({
      type: "css",
      value: cssSelector,
      stability: "low",
      score: 40,
    });

    return locators;
  }

  function sendEvent(type, el, extras) {
    if (_paused) return;

    const meta = getElementMeta(el);
    if (!meta) return;

    const locators = generateLocators(meta);

    const event = {
      type: type,
      timestamp: Date.now(),
      element: meta,
      locators: locators,
      ...extras,
    };

    console.log("__PYSHAFT_EVENT__:" + JSON.stringify(event));

    // Brief green flash on the element
    flashElement(el);
  }

  function flashElement(el) {
    const orig = el.style.outline;
    const origTransition = el.style.transition;
    el.style.transition = "outline 0.15s ease";
    el.style.outline = "2px solid #00D9A3";
    setTimeout(() => {
      el.style.outline = orig;
      el.style.transition = origTransition;
    }, 300);
  }

  // -----------------------------------------------------------------------
  // Event Listeners
  // -----------------------------------------------------------------------

  function onClickCapture(e) {
    if (_paused) return;
    // Ignore our own UI overlays
    if (e.target.closest && e.target.closest("[data-pyshaft-overlay]")) return;

    sendEvent("click", e.target, {
      button: e.button,
      ctrlKey: e.ctrlKey,
      shiftKey: e.shiftKey,
    });
  }

  function onDblClickCapture(e) {
    if (_paused) return;
    if (e.target.closest && e.target.closest("[data-pyshaft-overlay]")) return;
    sendEvent("double_click", e.target, {});
  }

  function onContextMenuCapture(e) {
    if (_paused) return;
    if (e.target.closest && e.target.closest("[data-pyshaft-overlay]")) return;
    sendEvent("right_click", e.target, {});
  }

  function onInputCapture(e) {
    if (_paused) return;
    if (e.target.closest && e.target.closest("[data-pyshaft-overlay]")) return;

    // Debounce typing events
    clearTimeout(_typeTimer);
    _lastTypeEvent = e;

    _typeTimer = setTimeout(() => {
      if (_lastTypeEvent) {
        sendEvent("type", _lastTypeEvent.target, {
          value: _lastTypeEvent.target.value || "",
        });
        _lastTypeEvent = null;
      }
    }, DEBOUNCE_MS);
  }

  function onChangeCapture(e) {
    if (_paused) return;
    if (e.target.closest && e.target.closest("[data-pyshaft-overlay]")) return;

    const tag = e.target.tagName.toLowerCase();
    const type = (e.target.getAttribute("type") || "").toLowerCase();

    if (tag === "select") {
      sendEvent("select", e.target, {
        selectedOption:
          e.target.options[e.target.selectedIndex]?.text || e.target.value,
        selectedValue: e.target.value,
      });
    } else if (type === "checkbox") {
      sendEvent(e.target.checked ? "check" : "uncheck", e.target, {});
    } else if (type === "radio") {
      sendEvent("check", e.target, { value: e.target.value });
    }
  }

  function onSubmitCapture(e) {
    if (_paused) return;
    sendEvent("submit", e.target, {});
  }

  function onScrollCapture(e) {
    if (_paused) return;
    // Only track scrolls on the main window, debounced
    // Skip for now to reduce noise — scrolls are less common in tests
  }

  // -----------------------------------------------------------------------
  // Attach listeners
  // -----------------------------------------------------------------------

  document.addEventListener("click", onClickCapture, true);
  document.addEventListener("dblclick", onDblClickCapture, true);
  document.addEventListener("contextmenu", onContextMenuCapture, true);
  document.addEventListener("input", onInputCapture, true);
  document.addEventListener("change", onChangeCapture, true);
  document.addEventListener("submit", onSubmitCapture, true);

  // -----------------------------------------------------------------------
  // Public API
  // -----------------------------------------------------------------------

  window.__pyshaft_recorder = {
    pause: function () {
      _paused = true;
    },
    resume: function () {
      _paused = false;
    },
    stop: function () {
      _paused = true;
      document.removeEventListener("click", onClickCapture, true);
      document.removeEventListener("dblclick", onDblClickCapture, true);
      document.removeEventListener("contextmenu", onContextMenuCapture, true);
      document.removeEventListener("input", onInputCapture, true);
      document.removeEventListener("change", onChangeCapture, true);
      document.removeEventListener("submit", onSubmitCapture, true);
      delete window.__pyshaft_recorder;
    },
  };

  console.log("__PYSHAFT_EVENT__:" + JSON.stringify({
    type: "recorder_ready",
    url: window.location.href,
    timestamp: Date.now()
  }));
})();
