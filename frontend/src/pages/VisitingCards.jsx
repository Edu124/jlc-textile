import { useRef, useState } from "react";
import api from "../api";
import { apiError } from "../lib/useFetch.js";
import { PageHeader, Field, Spinner } from "../components/ui.jsx";

// ── Image preprocessing: upscale + grayscale + contrast (big OCR accuracy win) ──
async function preprocess(file) {
  const img = await new Promise((res, rej) => {
    const i = new Image();
    i.onload = () => res(i);
    i.onerror = rej;
    i.src = URL.createObjectURL(file);
  });
  const targetW = Math.max(img.naturalWidth, 1400);   // upscale small photos
  const scale = targetW / img.naturalWidth;
  const c = document.createElement("canvas");
  c.width = Math.round(img.naturalWidth * scale);
  c.height = Math.round(img.naturalHeight * scale);
  const ctx = c.getContext("2d");
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(img, 0, 0, c.width, c.height);
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

// Prefer Indian 10-digit mobiles; fall back to any 8-13 digit run (foreign formats).
function extractPhones(rawText) {
  const indian = [];
  const digitsAll = rawText.replace(/[^\d\n]/g, "\n").split("\n").filter(Boolean);
  for (const run of rawText.split("\n").map((l) => l.replace(/[^\d]/g, ""))) {
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
      const canvas = await preprocess(file);
      const Tesseract = await import("tesseract.js");
      const { data } = await Tesseract.recognize(canvas, "eng", {
        logger: (m) => { if (m.status === "recognizing text") setProgress(Math.round(m.progress * 100)); },
      });
      setRawText(data.text);
      const parsed = parseCard(data.text);
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
