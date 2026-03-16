import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import "./styles.css";

// Fix for Telegram Desktop on Windows/Linux stealing keyboard events 
// (like Shift for uppercase or language switching) when an input is focused.
const stopPropagation = (e: KeyboardEvent) => {
  const target = e.target as HTMLElement;
  if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable) {
    e.stopPropagation();
  }
};

document.addEventListener("keydown", stopPropagation, { capture: true });
document.addEventListener("keyup", stopPropagation, { capture: true });
document.addEventListener("keypress", stopPropagation, { capture: true });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
