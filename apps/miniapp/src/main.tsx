import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import "./styles.css";

/**
 * Fix for Telegram Desktop WebView stealing keyboard events.
 * The desktop client intercepts keydown/keyup at the native WebView level,
 * which breaks Shift (uppercase), Cyrillic input, and language switching.
 *
 * We use stopImmediatePropagation at the WINDOW level in the CAPTURE phase
 * to kill the event before Telegram's internal handlers see it.
 * We only do this when the active element is an input/textarea.
 */
const INTERCEPT_EVENTS = ["keydown", "keyup", "keypress"] as const;

function killTelegramKeyboardIntercept(e: Event) {
  const el = e.target as HTMLElement | null;
  if (!el) return;
  const tag = el.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || el.isContentEditable) {
    e.stopImmediatePropagation();
  }
}

for (const evt of INTERCEPT_EVENTS) {
  // window-level capture — fires before anything else in the page
  window.addEventListener(evt, killTelegramKeyboardIntercept, { capture: true });
  // document-level capture — belt-and-suspenders
  document.addEventListener(evt, killTelegramKeyboardIntercept, { capture: true });
}

/**
 * Patch all <input> and <textarea> elements to disable browser/WebView
 * autocomplete and spellcheck, which can interfere with typing in some
 * Telegram Desktop WebView versions.
 */
function patchInput(el: HTMLInputElement | HTMLTextAreaElement) {
  if (!el.dataset.tgPatched) {
    el.setAttribute("autocomplete", "off");
    el.setAttribute("autocorrect", "off");
    el.setAttribute("autocapitalize", "off");
    el.setAttribute("spellcheck", "false");
    el.dataset.tgPatched = "1";
  }
}

// Patch existing inputs
document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input, textarea").forEach(patchInput);

// Patch future inputs via MutationObserver
const mo = new MutationObserver((mutations) => {
  for (const m of mutations) {
    m.addedNodes.forEach((node) => {
      if (node instanceof HTMLElement) {
        if (node.tagName === "INPUT" || node.tagName === "TEXTAREA") {
          patchInput(node as HTMLInputElement);
        }
        node.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input, textarea").forEach(patchInput);
      }
    });
  }
});
mo.observe(document.body, { childList: true, subtree: true });

// Apply user theme preference
const savedTheme = localStorage.getItem("theme") || "system";
if (savedTheme === "dark") {
  document.documentElement.setAttribute("data-theme", "dark");
} else if (savedTheme === "light") {
  document.documentElement.setAttribute("data-theme", "light");
} else {
  document.documentElement.removeAttribute("data-theme");
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
