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
    const tagStr = `<span style="color:#6C63FF; font-weight:bold">${el.tagName.toLowerCase()}</span>`;
    const dimStr = `<span style="color:#8B949E; margin-left:8px">${Math.round(rect.width)} × ${Math.round(rect.height)}</span>`;
    
    let details = "";
    if (el.id) details += `<div style="color:#E3B341">#${el.id}</div>`;
    if (el.classList.length > 0) details += `<div style="color:#79C0FF">.${Array.from(el.classList).slice(0, 2).join(".")}</div>`;
    if (el.getAttribute("role")) details += `<div style="color:#8B949E; font-size:10px; text-transform:uppercase">[${el.getAttribute("role")}]</div>`;

    _tooltip.innerHTML = `<div style="display:flex; flex-direction:column; gap:2px">${tagStr}${dimStr}${details}</div>`;
    _tooltip.style.display = "block";

    // Position tooltip above or below element
    let tooltipTop = rect.top - _tooltip.offsetHeight - 8;
    if (tooltipTop < 5) tooltipTop = rect.bottom + 8;
    _tooltip.style.left = Math.max(8, rect.left) + "px";
    _tooltip.style.top = tooltipTop + "px";
  }

  function onMouseLeave(e) {
    if (_overlay) _overlay.style.display = "none";
    if (_tooltip) _tooltip.style.display = "none";
  }

  function getAriaTree(root) {
    const roles_to_ignore = ['presentation', 'none', 'generic'];
    
    function isVisible(el) {
        if (!el) return false;
        if (el.getAttribute('aria-hidden') === 'true') return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    }

    function getRole(el) {
        const explicitRole = el.getAttribute('role');
        if (explicitRole) return explicitRole;
        
        const tag = el.tagName.toLowerCase();
        const type = el.getAttribute('type');
        
        if (tag === 'button') return 'button';
        if (tag === 'input') {
            if (['button', 'submit', 'reset'].includes(type)) return 'button';
            if (type === 'checkbox') return 'checkbox';
            if (type === 'radio') return 'radio';
            if (type === 'image') return 'button';
            return 'textbox';
        }
        if (tag === 'textarea') return 'textbox';
        if (tag === 'select') return 'combobox';
        if (tag === 'a' && el.getAttribute('href')) return 'link';
        if (/^h[1-6]$/.test(tag)) return 'heading';
        if (tag === 'table') return 'table';
        if (tag === 'ul' || tag === 'ol') return 'list';
        if (tag === 'li') return 'listitem';
        if (tag === 'form') return 'form';
        if (tag === 'nav') return 'navigation';
        if (tag === 'header') return 'banner';
        if (tag === 'footer') return 'contentinfo';
        if (tag === 'main') return 'main';
        if (tag === 'aside') return 'complementary';
        if (tag === 'section' && (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby'))) return 'region';
        
        return null;
    }

    function getName(el, role) {
        // 1. aria-label
        let name = el.getAttribute('aria-label');
        if (name) return name.trim();
        
        // 2. aria-labelledby
        const labelId = el.getAttribute('aria-labelledby');
        if (labelId) {
            const labelEl = document.getElementById(labelId);
            if (labelEl) return labelEl.innerText.trim();
        }

        // 3. label for (inputs)
        if (el.id) {
            const label = document.querySelector(`label[for="${el.id}"]`);
            if (label) return label.innerText.trim();
        }

        // 4. placeholder
        const placeholder = el.getAttribute('placeholder');
        if (placeholder) return placeholder.trim();
        
        // 5. title
        const title = el.getAttribute('title');
        if (title) return title.trim();

        // 6. alt (images)
        const alt = el.getAttribute('alt');
        if (alt) return alt.trim();

        // 7. inner text for specific roles
        const textRoles = ['button', 'link', 'heading', 'listitem', 'menuitem', 'tab', 'option'];
        if (textRoles.includes(role)) {
            // Only get direct text or flattened child text
            return el.innerText.trim().replace(/\s+/g, ' ');
        }
        
        return '';
    }

    function buildNode(el) {
        if (!isVisible(el)) return null;

        const role = getRole(el);
        const name = role ? getName(el, role) : '';
        
        const children = [];
        for (const child of el.children) {
            const node = buildNode(child);
            if (node) {
                if (Array.isArray(node)) children.push(...node);
                else children.push(node);
            }
        }

        if (!role || roles_to_ignore.includes(role)) {
            // Container node — flatten if possible
            return children.length > 0 ? children : null;
        }

        const node = { role };
        if (name) node.name = name;
        
        if (role === 'heading') {
            const levelMatch = el.tagName.match(/H(\d)/i);
            if (levelMatch) node.level = parseInt(levelMatch[1], 10);
        }
        
        if (children.length > 0) node.children = children;
        return node;
    }

    const tree = buildNode(root);
    return Array.isArray(tree) ? tree[0] : tree;
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
    
    // Add aria tree
    meta.aria_tree = getAriaTree(e.target);

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
