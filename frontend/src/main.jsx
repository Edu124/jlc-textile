import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { AuthProvider } from "./auth.jsx";
import { initOfflineSync } from "./lib/offline.js";
import "./index.css";

// Offline support: cache pages/data for viewing without internet (service
// worker, production build only) and auto-sync any queued offline entries.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
    // Warm the card-scanner engines (OpenCV + OCR chunks) in the background a
    // few seconds after start-up, so the service worker has them cached and
    // scanning works offline even if the page was never opened online.
    setTimeout(() => {
      if (!navigator.onLine) return;
      import("@techstark/opencv-js").catch(() => {});
      import("tesseract.js").catch(() => {});
    }, 6000);
  });
}
initOfflineSync();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);
