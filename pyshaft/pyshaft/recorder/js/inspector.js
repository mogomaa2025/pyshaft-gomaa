/**
 * PyShaft Inspector — Element Inspection Script
 *
 * Injected into the browser page for inspect mode.
 * Highlights hovered elements, captures metadata on click.
 */
(function () {
  if (window.__pyshaft_inspector) {
    return;
  }

  let _overlay = null;
  let _tooltip = null;
  let _active = true;

  // -----------------------------------------------------------------------
  // Create overlay elements
  // -----------------------------------------------------------------------

  function createOverlay() {
    _overlay = document.createElement("div");
    _overlay.setAttribute("data-pyshaft-overlay", "true");
    _overlay.style.cssText = `
      position: fixed;
      pointer-events: none;
      z-index: 2147483646;
      border: 2px dashed #6C63FF;
      background: rgba(108, 99, 255, 0.08);
      border-radius: 4px;
      transition: all 0.1s ease;
      display: none;
    `;
    document.body.appendChild(_overlay);

    _tooltip = document.createElement("div");
    _tooltip.setAttribute("data-pyshaft-overlay", "true");
    _tooltip.style.cssText = `
      position: fixed;
      pointer-events: none;
      z-index: 2147483647;
      background: #1C2333;
      color: #E6EDF3;
      padding: 6px 10px;
      border-radius: 6px;
      font-family: 'Cascadia Code', 'JetBrains Mono', monospace;
      font-size: 11px;
      border: 1px solid #6C63FF;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
      display: none;
      max-width: 400px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    `;
    document.body.appendChild(_tooltip);
  }

  // -----------------------------------------------------------------------
  // Element metadata extraction
  // -----------------------------------------------------------------------

  function getElementMeta(el) {
    if (!el || !el.tagName) return null;

    const rect = el.getBoundingClientRect();

    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || "",
      class:  Array.from(el.classList || []),
      text: (el.innerText || "").trim().substring(0, 200),
      role: el.getAttribute("role") || _inferRole(el),
      "aria-label": el.getAttribute("aria-label") || "",
      placeholder: el.getAttribute("placeholder") || "",
      "data-testid":
        el.getAttribute("data-testid") ||
        el.getAttribute("data-test-id") ||
        el.getAttribute("data-qa") ||
        el.getAttribute("data-cy") || "",
      name: el.getAttribute("name") || "",
      type: el.getAttribute("type") || "",
      href: el.getAttribute("href") || "",
      value: el.value || "",
      title: el.getAttribute("title") || "",
      alt: el.getAttribute("alt") || "",
      checked: el.checked || false,
      disabled: el.disabled || false,
      rect: {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      },
      url: window.location.href,
      parentId: el.parentElement ? el.parentElement.id : "",
      parentTag: el.parentElement ? el.parentElement.tagName.toLowerCase() : "",
      isIframe: window !== window.top,
      frameId: window.name || window.location.href,
    };
  }

  function _inferRole(el) {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();
    const roleMap = {
      button: "button",
      a: "link",
      input: type === "checkbox" ? "checkbox" : type === "radio" ? "radio" : "textbox",
      textarea: "textbox",
      select: "combobox",
      img: "image",
      h1: "heading", h2: "heading", h3: "heading", h4: "heading", h5: "heading", h6: "heading",
      nav: "navigation",
      form: "form",
      dialog: "dialog",
      table: "table",
      li: "listitem",
      ul: "list",
      ol: "list",
    };
    return roleMap[tag] || tag;
  }

  function generateLocators(meta) {
    const locators = [];

    if (meta["data-testid"]) {
      locators.push({ type: "testid", value: meta["data-testid"], stability: "high", score: 100 });
    }
    if (meta.id) {
      locators.push({ type: "id", value: meta.id, stability: "high", score: 95 });
    }
    const inferredRole = meta.role;
    if (inferredRole && inferredRole !== meta.tag) {
      locators.push({ type: "role", value: inferredRole, stability: "high", score: 90 });
    }
    if (meta.placeholder) {
      locators.push({ type: "placeholder", value: meta.placeholder, stability: "medium", score: 80 });
    }
    if (meta["aria-label"]) {
      locators.push({ type: "label", value: meta["aria-label"], stability: "medium", score: 75 });
    }
    if (meta.text && meta.text.length <= 50) {
      locators.push({ type: "text", value: meta.text, modifier: "exact", stability: "medium", score: 70 });
    }
    if (meta.text && meta.text.length > 10) {
      locators.push({ type: "text", value: meta.text.substring(0, 30), modifier: "contain", stability: "low", score: 50 });
    }
    if (meta.name) {
      locators.push({ type: "attr", value: meta.name, stability: "medium", score: 65 });
      locators.push({ type: "css", value: `[name="${meta.name}"]`, stability: "medium", score: 63 });
    }
    if (meta.type) {
      locators.push({ type: "attr", value: "type", stability: "medium", score: 64 });
      locators.push({ type: "css", value: `[type="${meta.type}"]`, stability: "medium", score: 62 });
    }
    
    // Explicit tag
    locators.push({ type: "tag", value: meta.tag, stability: "low", score: 55 });

    let css = meta.tag;
    if (meta.id) css = "#" + meta.id;
    else if (meta.class.length > 0) css = meta.tag + "." + meta.class[0];
    if (meta.name) css += `[name="${meta.name}"]`;
    locators.push({ type: "css", value: css, stability: "low", score: 40 });

    return locators;
  }

  // -----------------------------------------------------------------------
  // Event handlers
  // -----------------------------------------------------------------------

  function onMouseMove(e) {
    if (!_active) return;
    if (e.target.closest && e.target.closest("[data-pyshaft-overlay]")) return;

    const el = e.target;
    const rect = el.getBoundingClientRect();

    // Position overlay
    _overlay.style.display = "block";
    _overlay.style.left = rect.left + "px";
    _overlay.style.top = rect.top + "px";
    _overlay.style.width = rect.width + "px";
    _overlay.style.height = rect.height + "px";

    // Tooltip content
    let desc = el.tagName.toLowerCase();
    if (el.id) desc += "#" + el.id;
    if (el.classList.length > 0) desc += "." + Array.from(el.classList).slice(0, 2).join(".");
    if (el.getAttribute("role")) desc += ` [${el.getAttribute("role")}]`;

    _tooltip.textContent = desc;
    _tooltip.style.display = "block";

    // Position tooltip above or below element
    let tooltipTop = rect.top - 30;
    if (tooltipTop < 5) tooltipTop = rect.bottom + 5;
    _tooltip.style.left = Math.max(5, rect.left) + "px";
    _tooltip.style.top = tooltipTop + "px";
  }

  function onMouseLeave(e) {
    if (_overlay) _overlay.style.display = "none";
    if (_tooltip) _tooltip.style.display = "none";
  }

  function onClickCapture(e) {
    if (!_active) return;
    if (e.target.closest && e.target.closest("[data-pyshaft-overlay]")) return;

    // Prevent the actual click in inspect mode
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();

    const meta = getElementMeta(e.target);
    if (!meta) return;

    const locators = generateLocators(meta);

    // Send inspect data back to Python
    console.log("__PYSHAFT_INSPECT__:" + JSON.stringify({
      element: meta,
      locators: locators,
    }));

    // Highlight selected element with solid border
    _overlay.style.border = "3px solid #00D9A3";
    _overlay.style.background = "rgba(0, 217, 163, 0.08)";
    setTimeout(() => {
      _overlay.style.border = "2px dashed #6C63FF";
      _overlay.style.background = "rgba(108, 99, 255, 0.08)";
    }, 1000);
  }

  // -----------------------------------------------------------------------
  // Init
  // -----------------------------------------------------------------------

  createOverlay();
  document.addEventListener("mousemove", onMouseMove, true);
  document.addEventListener("mouseleave", onMouseLeave, true);
  document.addEventListener("click", onClickCapture, true);

  window.__pyshaft_inspector = {
    stop: function () {
      _active = false;
      document.removeEventListener("mousemove", onMouseMove, true);
      document.removeEventListener("mouseleave", onMouseLeave, true);
      document.removeEventListener("click", onClickCapture, true);
      if (_overlay) _overlay.remove();
      if (_tooltip) _tooltip.remove();
      delete window.__pyshaft_inspector;
    },
  };
})();
