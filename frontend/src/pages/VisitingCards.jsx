import { useRef, useState } from "react";
import api from "../api";
import { apiError } from "../lib/useFetch.js";
import { PageHeader, Field, Spinner } from "../components/ui.jsx";

// ── Image preprocessing ────────────────────────────────────────────────────────
async function loadImage(file) {
  return new Promise((res, rej) => {
    const i = new Image();
    i.onload = () => res(i);
    i.onerror = rej;
    i.src = URL.createObjectURL(file);
  });
}

// Find the card in the photo automatically, so far-away shots scan without
// manual cropping. Primary signal: EDGE DENSITY — printed text is busy while
// tables/covers are smooth, and this works for dark cards too. Fallback:
// Otsu-bright region (classic white card on dark table).
function detectCard(img) {
  const iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
  const W = 320;
  const H = Math.max(1, Math.round((ih / iw) * W));
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const ctx = c.getContext("2d");
  ctx.drawImage(img, 0, 0, W, H);
  const d = ctx.getImageData(0, 0, W, H).data;

  const luma = new Uint8Array(W * H);
  const hist = new Array(256).fill(0);
  for (let i = 0, p = 0; p < d.length; p += 4, i++) {
    const g = Math.round(0.299 * d[p] + 0.587 * d[p + 1] + 0.114 * d[p + 2]);
    luma[i] = g; hist[g]++;
  }

  // moving-average smoothing bridges the gaps between text lines
  const smooth = (a, r = 5) => a.map((_, i) => {
    let s = 0, n = 0;
    for (let j = Math.max(0, i - r); j <= Math.min(a.length - 1, i + r); j++) { s += a[j]; n++; }
    return s / n;
  });
  // largest contiguous run above a threshold
  const run = (counts, min) => {
    let bs = -1, be = -1, s = -1;
    for (let i = 0; i <= counts.length; i++) {
      const on = i < counts.length && counts[i] > min;
      if (on && s === -1) s = i;
      if (!on && s !== -1) {
        if (be - bs < i - s) { bs = s; be = i; }
        s = -1;
      }
    }
    return bs === -1 ? null : [bs, be];
  };
  const box = (rows, cols) => {
    if (!rows || !cols) return null;
    const sx = cols[0] / W, sw = (cols[1] - cols[0]) / W;
    const sy = rows[0] / H, sh = (rows[1] - rows[0]) / H;
    if (sw * sh < 0.03 || sw * sh > 0.92) return null;   // sliver or full frame
    const pad = 0.05;
    return {
      x: Math.max(0, sx - pad), y: Math.max(0, sy - pad),
      w: Math.min(1 - Math.max(0, sx - pad), sw + 2 * pad),
      h: Math.min(1 - Math.max(0, sy - pad), sh + 2 * pad),
    };
  };

  // 1) Edge-density detection
  const rowE = new Array(H).fill(0), colE = new Array(W).fill(0);
  for (let y = 0; y < H - 1; y++)
    for (let x = 0; x < W - 1; x++) {
      const i = y * W + x;
      const e = Math.abs(luma[i] - luma[i + 1]) + Math.abs(luma[i] - luma[i + W]);
      if (e > 26) { rowE[y]++; colE[x]++; }
    }
  const rowsE = run(smooth(rowE), 0.045 * W);
  const colsE = run(smooth(colE), 0.045 * H);
  const edgeBox = box(rowsE, colsE);
  if (edgeBox) return edgeBox;

  // 2) Otsu-bright fallback
  const total = W * H;
  let sumAll = 0;
  for (let t = 0; t < 256; t++) sumAll += t * hist[t];
  let sumB = 0, wB = 0, best = 0, thr = 127;
  for (let t = 0; t < 256; t++) {
    wB += hist[t];
    if (!wB) continue;
    const wF = total - wB;
    if (!wF) break;
    sumB += t * hist[t];
    const mB = sumB / wB, mF = (sumAll - sumB) / wF;
    const between = wB * wF * (mB - mF) * (mB - mF);
    if (between > best) { best = between; thr = t; }
  }
  const rowB = new Array(H).fill(0), colB = new Array(W).fill(0);
  let brightTotal = 0;
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++)
      if (luma[y * W + x] > thr) { rowB[y]++; colB[x]++; brightTotal++; }
  if (brightTotal / total > 0.8) return null;
  return box(run(smooth(rowB), 0.25 * W), run(smooth(colB), 0.25 * H));
}

// Second-pass refine: crop to the first detection, detect again inside it,
// and compose — tightens boxes that grabbed background on the first pass.
function refineRegion(img, r1) {
  if (!r1) return null;
  const iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
  const c = document.createElement("canvas");
  const rw = r1.w * iw, rh = r1.h * ih;
  const scale = Math.min(1, 700 / rw);
  c.width = Math.max(1, Math.round(rw * scale));
  c.height = Math.max(1, Math.round(rh * scale));
  c.getContext("2d").drawImage(img, r1.x * iw, r1.y * ih, rw, rh, 0, 0, c.width, c.height);
  const r2 = detectCard(c);
  if (!r2 || r2.w * r2.h > 0.85) return r1;
  return { x: r1.x + r2.x * r1.w, y: r1.y + r2.y * r1.h, w: r2.w * r1.w, h: r2.h * r1.h };
}

// Colour crop of the detected card (optionally rotated upright) for the preview.
function colorCrop(img, region, rot = 0) {
  const iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
  const rx = region ? region.x * iw : 0, ry = region ? region.y * ih : 0;
  const rw = region ? region.w * iw : iw, rh = region ? region.h * ih : ih;
  const scale = Math.min(1, 1000 / Math.max(rw, rh));
  const w0 = Math.round(rw * scale), h0 = Math.round(rh * scale);
  const c = document.createElement("canvas");
  if (rot === 90 || rot === 270) { c.width = h0; c.height = w0; } else { c.width = w0; c.height = h0; }
  const ctx = c.getContext("2d");
  ctx.save();
  if (rot === 90) { ctx.translate(c.width, 0); ctx.rotate(Math.PI / 2); }
  else if (rot === 270) { ctx.translate(0, c.height); ctx.rotate(-Math.PI / 2); }
  ctx.drawImage(img, rx, ry, rw, rh, 0, 0, w0, h0);
  ctx.restore();
  return c.toDataURL("image/jpeg", 0.85);
}

// Upscale + grayscale + contrast (big OCR accuracy win). `region` optionally
// crops to the detected card first (fractions of the full image), and `rot`
// (0/90/270) turns a sideways card upright before OCR.
function preprocess(img, region, rot = 0) {
  const rx = region ? region.x * img.naturalWidth : 0;
  const ry = region ? region.y * img.naturalHeight : 0;
  const rw = region ? region.w * img.naturalWidth : img.naturalWidth;
  const rh = region ? region.h * img.naturalHeight : img.naturalHeight;
  const scale = Math.max(1, 1600 / Math.max(rw, rh));
  const w0 = Math.round(rw * scale), h0 = Math.round(rh * scale);
  const c = document.createElement("canvas");
  if (rot === 90 || rot === 270) { c.width = h0; c.height = w0; }
  else { c.width = w0; c.height = h0; }
  const ctx = c.getContext("2d");
  ctx.imageSmoothingQuality = "high";
  ctx.save();
  if (rot === 90) { ctx.translate(c.width, 0); ctx.rotate(Math.PI / 2); }
  else if (rot === 270) { ctx.translate(0, c.height); ctx.rotate(-Math.PI / 2); }
  ctx.drawImage(img, rx, ry, rw, rh, 0, 0, w0, h0);
  ctx.restore();
  const im = ctx.getImageData(0, 0, c.width, c.height);
  const d = im.data;
  for (let p = 0; p < d.length; p += 4) {
    // grayscale + mild contrast stretch around midpoint
    let g = 0.299 * d[p] + 0.587 * d[p + 1] + 0.114 * d[p + 2];
    g = Math.max(0, Math.min(255, (g - 128) * 1.35 + 128));
    d[p] = d[p + 1] = d[p + 2] = g;
  }
  ctx.putImageData(im, 0, 0);
  return c;
}

// ── Parsing helpers ────────────────────────────────────────────────────────────
const BUSINESS_WORDS = [
  "textile", "textiles", "creation", "creations", "fashion", "fashions", "garment",
  "garments", "saree", "sarees", "suits", "salwar", "kameez", "collection",
  "collections", "selection", "selections", "matching", "centre", "center",
  "house", "palace", "traders", "trading", "agency", "agencies", "industries",
  "emporium", "store", "stores", "mart", "boutique", "silk", "mills", "sons",
  "brothers", "enterprise", "enterprises", "apparel", "apparels", "cloth",
  "fab", "fabrics", "designer", "dresses", "nx", "impex", "exports", "syndicate",
  "company", "corporate", "corporation", "pvt", "ltd", "llp", "inc", "& co",
];
const PERSON_WORDS = ["prop", "proprietor", "partner", "director", "manager", "mr.", "mrs.",
  "ms.", "contact person", "job", "position", "designation", "ceo", "founder",
  "executive", "officer", "your name"];
// "SPECIALIST STOCKISTS OF: MANDAP CLOTH" — describes the business, isn't its name.
const TAGLINE_WORDS = ["specialist", "stockist", "stockists", "dealer", "dealers", "deals in",
  "mfg", "mfrs", "manufacturer", "manufacturers", "wholesale", "wholesaler",
  "retailer", "supplier", "suppliers", "all types", "exclusive", "since "];
const ADDRESS_WORDS = ["shop", "no.", "floor", "road", "rd", "street", "st.", "market", "bazar",
  "bazaar", "nagar", "chowk", "near", "opp", "behind", "plot", "gala", "building", "bldg",
  "complex", "tower", "mall", "lane", "gali", "cross", "main", "sector", "phase", "pin",
  "dist", "city", "station", "add.", "address"];

const hasAny = (line, words) => {
  const lower = " " + line.toLowerCase() + " ";
  return words.some((w) => lower.includes(w));
};

const EMAIL_RE = /[\w.+-]+@[\w-]+\.[\w.\-]+/g;
const URL_RE = /(?:www\.|https?:\/\/)\S+|\b\S+\.(?:com|in|net|org|co\.in|co)\b/gi;
const PHONE_RUN_RE = /\+?\d[\d\s\-()./]{5,}\d/g;                 // 7+ digits with separators
const LABEL_RE = /\b(?:mob(?:ile)?|ph(?:one)?|tel|fax|e-?mail|web(?:site)?|gst(?:in)?|whatsapp|contact|call)\b\s*(?:no\.?|number)?\s*[.:\-]?\s*/gi;

// Strip emails / urls / phone runs / "Mob:"-style labels off a line, keep the rest.
// Cards often OCR two columns into one line, so we salvage the text part
// instead of throwing the whole line away.
function cleanLine(l) {
  return l
    .replace(EMAIL_RE, " ").replace(URL_RE, " ")
    // remove phone-length digit runs, but keep short ones (pincodes, shop nos.)
    .replace(PHONE_RUN_RE, (m) => (m.replace(/[^\d]/g, "").length >= 8 ? " " : m))
    .replace(LABEL_RE, " ")
    .replace(/[|_=©®™£€§]+/g, " ")
    .replace(/\s+/g, " ")
    .replace(/^[\s,.;:\-\/]+|[\s,.;:\-\/]+$/g, "");
}

// Meaningful text = at least 3 letters after cleaning (drops OCR noise like "\ py").
const letterCount = (l) => (l.match(/[a-zA-Z]/g) || []).length;

// OCR often misreads digits as lookalike letters (O→0, S→5, B→8, l→1...).
// On lines that already carry several real digits, map them back.
const DIGIT_LOOKALIKE = { O: "0", o: "0", D: "0", Q: "0", I: "1", l: "1", "|": "1",
  "!": "1", i: "1", Z: "2", z: "2", S: "5", s: "5", G: "6", B: "8", g: "9" };

function _phoneDigits(line) {
  const real = (line.match(/\d/g) || []).length;
  const src = real >= 6
    ? line.split("").map((ch) => DIGIT_LOOKALIKE[ch] ?? ch).join("")
    : line;
  return src.replace(/[^\d]/g, "");
}

// Prefer Indian 10-digit mobiles; fall back to any 8-13 digit run (foreign formats).
function extractPhones(rawText) {
  const indian = [];
  for (let run of rawText.split("\n").map(_phoneDigits)) {
    // strip country / trunk prefix ("+91 98765 43210", "098765 43210")
    if (run.length === 12 && run.startsWith("91")) run = run.slice(2);
    if (run.length === 11 && run.startsWith("0")) run = run.slice(1);
    for (let i = 0; i + 10 <= run.length; i++) {
      const chunk = run.slice(i, i + 10);
      if (/^[6-9]/.test(chunk) && !indian.includes(chunk)) { indian.push(chunk); break; }
    }
  }
  if (indian.length) return indian;
  const generic = [];
  for (const m of rawText.match(PHONE_RUN_RE) || []) {
    const digits = m.replace(/[^\d]/g, "");
    if (digits.length >= 8 && digits.length <= 13 && !generic.includes(digits)) generic.push(digits);
  }
  return generic;
}

// If a line is "BIG CAPS NAME followed by lowercase junk" (merged columns),
// keep just the leading ALL-CAPS chunk as the name.
function capsPrefix(l) {
  const m = l.match(/^[A-Z][A-Z0-9&.,'\-\s]*[A-Z0-9]/);
  if (m && letterCount(m[0]) >= 4 && m[0].length < l.length) return m[0].trim().replace(/[,.\-]+$/, "");
  return l;
}

// Merged columns often glue address text after the company name — cut the name
// off at the first address-ish word ("address", "shop", "road", ...).
function truncateAtAddress(l) {
  const words = l.split(" ");
  for (let i = 1; i < words.length; i++) {
    if (hasAny(words[i], ADDRESS_WORDS)) return words.slice(0, i).join(" ");
  }
  return l;
}

// Bold letter-spaced logos OCR as "co M PA NY NAM E" — if most tokens are tiny,
// glue them back together into one word.
function fixSpacedCaps(l) {
  const tokens = l.split(" ").filter(Boolean);
  const tiny = tokens.filter((t) => t.length <= 3).length;
  if (tokens.length >= 4 && tiny >= tokens.length - 1) return tokens.join("").toUpperCase();
  return l;
}

function parseCard(text) {
  const rawLines = text.split("\n").map((l) => l.replace(/\s+/g, " ").trim()).filter(Boolean);
  const phones = extractPhones(text);

  // Clean every line (strip emails/urls/phones/labels) and drop noise lines.
  const lines = rawLines.map(cleanLine).filter((l) => letterCount(l) >= 3);

  const isPersonLine = (l) => hasAny(l, PERSON_WORDS) || /\b[A-Z]\.(\s|$)/.test(l);
  const isTagline = (l) => hasAny(l, TAGLINE_WORDS);

  // Shop/company name: score cleaned lines (top of card, business words, ALL-CAPS,
  // sitting right above a tagline). Taglines and person lines score low.
  let name = "", best = -99;
  lines.slice(0, 8).forEach((l, idx) => {
    let score = 4 - idx;                                     // higher on the card = better
    if (hasAny(l, BUSINESS_WORDS)) score += 6;               // "Textiles", "Selection", "Company"...
    const letters = l.replace(/[^a-zA-Z]/g, "");
    if (letters.length >= 4 && letters === letters.toUpperCase()) score += 3;  // ALL CAPS
    if (lines[idx + 1] && isTagline(lines[idx + 1])) score += 5;  // name sits above its tagline
    if (isTagline(l)) score -= 8;                            // "SPECIALIST STOCKISTS OF ..."
    if (lines[idx - 1] && (isTagline(lines[idx - 1]) || /\bof\s*:?\s*$/i.test(lines[idx - 1])))
      score -= 6;                                            // "... OF:" continuation ("MANDAP CLOTH")
    if (isPersonLine(l)) score -= 6;                         // "Prop. ...", "Mukesh K. Shahani"
    if (hasAny(l, ADDRESS_WORDS)) score -= 3;                // address lines aren't names
    if (score > best) { best = score; name = l; }
  });
  const nameLine = name;   // the raw cleaned line the name came from
  name = fixSpacedCaps(truncateAtAddress(capsPrefix(name)));
  // OCR picks up stray marks at the card edges as lone letters ("f RESHMA
  // SELECTION j") — trim single-character tokens off both ends.
  const toks = name.split(" ").filter(Boolean);
  while (toks.length > 1 && toks[0].replace(/[^A-Za-z0-9]/g, "").length <= 1 && toks[0] !== "&") toks.shift();
  while (toks.length > 1 && toks[toks.length - 1].replace(/[^A-Za-z0-9]/g, "").length <= 1 && toks[toks.length - 1] !== "&") toks.pop();
  name = toks.join(" ");

  // Address: only lines with a real address signal — an address word, a pincode,
  // or digits + comma. (Keeps OCR garbage and stray card text out.)
  const addrLines = lines.filter((l) =>
    l !== nameLine && !isPersonLine(l) && !isTagline(l) &&
    (hasAny(l, ADDRESS_WORDS) || /\b\d{6}\b/.test(l) || (/\d/.test(l) && l.includes(","))));
  const address = addrLines
    .join(", ")
    .replace(/\s*,\s*,+/g, ",").replace(/\s+/g, " ")
    .replace(/^[,\s]+|[,\s]+$/g, "");

  const fmtPhone = (p) => (p.length === 10 ? p : p);
  return {
    name: name.replace(/\s+/g, " ").trim(),
    phone: phones.slice(0, 2).map(fmtPhone).join(" / "),
    address,
  };
}

export default function VisitingCards() {
  const fileRef = useRef(null);
  const [imgUrl, setImgUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [rawText, setRawText] = useState("");
  const [form, setForm] = useState({ name: "", phone: "", address: "" });
  const [err, setErr] = useState(""); const [saved, setSaved] = useState([]);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setErr(""); setScanning(true); setRawText(""); setProgress(0);
    setForm({ name: "", phone: "", address: "" });
    setImgUrl(URL.createObjectURL(file));
    try {
      const img = await loadImage(file);
      const Tesseract = await import("tesseract.js");
      const ocr = async (canvas) => {
        const { data } = await Tesseract.recognize(canvas, "eng", {
          logger: (m) => { if (m.status === "recognizing text") setProgress(Math.round(m.progress * 100)); },
        });
        return { text: data.text, conf: data.confidence || 0 };
      };
      // Quality = Tesseract's own confidence + bonuses for real signals.
      // Upside-down text scores low confidence even when it produces
      // plausible-looking junk, so this reliably picks the right rotation.
      const quality = (r) =>
        r.conf +
        (/[\w.+-]+@[\w-]+\.[\w.\-]+/.test(r.text) ? 15 : 0) +
        (extractPhones(r.text).length ? 10 : 0);

      // Auto-find the card, then refine once inside the crop to shed background.
      const region = refineRegion(img, detectCard(img));
      if (region) setImgUrl(colorCrop(img, region, 0));

      const portrait = region && region.h * img.naturalHeight > region.w * img.naturalWidth;
      // Sideways cards: try BOTH 90 and 270 and let confidence decide — never
      // trust just one direction.
      const rots = region ? (portrait ? [90, 270] : [0]) : [0];
      let best = null, bestRot = 0;
      for (const rot of rots) {
        setProgress(0);
        const r = await ocr(preprocess(img, region, rot));
        r.q = quality(r);
        if (!best || r.q > best.q) { best = r; bestRot = rot; }
      }
      // Low confidence? Try the remaining rotation(s).
      if (region && best.conf < 55) {
        for (const rot of (portrait ? [0] : [90, 270])) {
          setProgress(0);
          const r = await ocr(preprocess(img, region, rot));
          r.q = quality(r);
          if (r.q > best.q) { best = r; bestRot = rot; }
        }
      }
      // Still nearly nothing? Fall back to the full photo.
      if (letterCount(best.text) < 12) {
        setProgress(0);
        const r = await ocr(preprocess(img, null, 0));
        r.q = quality(r);
        if (r.q > best.q) { best = r; bestRot = 0; }
      }
      // Show the upright, tightened card as the final preview.
      if (region) setImgUrl(colorCrop(img, region, bestRot));

      const text = best.text;
      setRawText(text);
      const parsed = parseCard(text);
      setForm(parsed);
      if (!parsed.name && !parsed.phone) setErr("Couldn't read much from this photo — try a closer, straighter shot with good light, or type the details in.");
    } catch (e) {
      setErr("Could not read the card — fill the details in manually.");
    } finally {
      setScanning(false);
    }
  };

  const save = async () => {
    if (!form.name.trim()) return setErr("Enter the shop / company name");
    setBusy(true); setErr("");
    try {
      const { data } = await api.post("/api/customers", {
        name: form.name.trim(), phone: form.phone.trim(),
        address: form.address.trim(), email: "", gst_number: "" });
      setSaved([{ ...form, id: data.id }, ...saved]);
      setForm({ name: "", phone: "", address: "" });
      setRawText(""); setImgUrl("");
      if (fileRef.current) fileRef.current.value = "";
    } catch (e) { setErr(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader title="Visiting Cards" subtitle="Scan a visiting card — shop name, contact & address are picked out automatically for review" />

      <div className="card grid grid-cols-1 gap-5 p-5 lg:grid-cols-2">
        <div>
          <input ref={fileRef} type="file" accept="image/*" capture="environment"
                 onChange={onFile} className="hidden" id="card-input" />
          <label htmlFor="card-input"
                 className="btn-primary inline-flex cursor-pointer items-center gap-2">
            📷 Scan Visiting Card
          </label>

          {imgUrl && (
            <img src={imgUrl} alt="card" className="mt-4 max-h-64 rounded-xl border border-separator object-contain" />
          )}
          {scanning && (
            <div className="mt-3">
              <div className="flex items-center gap-2 text-sm text-muted"><Spinner /> Reading card… {progress > 0 && `${progress}%`}</div>
              <div className="mt-2 h-2 w-full rounded-full bg-surface2">
                <div className="h-2 rounded-full bg-accent transition-all" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}
          {rawText && (
            <details className="mt-3 text-xs text-muted">
              <summary className="cursor-pointer">Raw scanned text</summary>
              <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-surface2 p-2">{rawText}</pre>
            </details>
          )}
        </div>

        <div>
          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Review &amp; Save</div>
          <div className="space-y-3">
            <Field label="Shop / Company Name" required>
              <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Rajesh Textiles" />
            </Field>
            <Field label="Contact Number">
              <input className="input" inputMode="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="10-digit mobile" />
            </Field>
            <Field label="Address">
              <textarea className="input" rows={3} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} placeholder="Shop, street, area, city" />
            </Field>
          </div>
          {err && <div className="mt-3 rounded-lg bg-dangerSoft px-3 py-2 text-sm text-danger">{err}</div>}
          <button className="btn-success mt-4 w-full" onClick={save} disabled={busy || scanning}>
            {busy ? <Spinner /> : "Save Lead as Customer"}
          </button>
        </div>
      </div>

      {saved.length > 0 && (
        <div className="mt-5">
          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-muted">Captured this session ({saved.length})</div>
          <div className="space-y-1">
            {saved.map((s) => (
              <div key={s.id} className="rounded-lg bg-surface2 px-3 py-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-ink">{s.name}</span>
                  <span className="text-ink2">{s.phone}</span>
                </div>
                {s.address && <div className="mt-0.5 text-xs text-muted">{s.address}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
