import { useEffect, useRef, useState } from "react";

// Global PDF preview: openPdf() dispatches a "jlc-pdf" event with a blob URL
// and this host (mounted once in Layout) shows it in a popup with
// Print / Download. Inside the Android app the share sheet is used instead
// (its WebView can't render PDFs).
export default function PdfPreviewHost() {
  const [doc, setDoc] = useState(null);
  const frameRef = useRef(null);

  useEffect(() => {
    const handler = (e) => setDoc(e.detail);
    window.addEventListener("jlc-pdf", handler);
    return () => window.removeEventListener("jlc-pdf", handler);
  }, []);

  if (!doc) return null;

  const close = () => { URL.revokeObjectURL(doc.url); setDoc(null); };
  const print = () => {
    try { frameRef.current?.contentWindow?.print(); }
    catch { window.open(doc.url, "_blank"); }
  };
  const download = () => {
    const a = document.createElement("a");
    a.href = doc.url; a.download = doc.filename;
    document.body.appendChild(a); a.click(); a.remove();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-3" onClick={close}>
      <div className="flex h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-surface shadow-2xl"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-separator px-4 py-2.5">
          <div className="truncate text-sm font-semibold text-ink">{doc.filename}</div>
          <div className="flex gap-2">
            <button className="btn-ghost" onClick={download}>⬇ Download</button>
            <button className="btn-primary" onClick={print}>🖨 Print</button>
            <button className="btn-ghost" onClick={close}>✕</button>
          </div>
        </div>
        <iframe ref={frameRef} title="pdf-preview" src={doc.url} className="w-full flex-1 bg-white" />
      </div>
    </div>
  );
}
