/* ASHA Vaani – field app (no build step, works offline as a PWA) */
const API = "";            // same origin as the FastAPI server
const MAX_SECONDS = 28;    // Gnani Prisma REST accepts clips up to 30 s

const ASHAS = { ta: { id: "asha_ta_01", name: "செல்வி · கோவூர்" },
                hi: { id: "asha_hi_01", name: "कमला · रामपुर" } };

const I18N = {
  ta: {
    types: { ANC: "கர்ப்பம்", HBNC: "பிறந்த குழந்தை", IMMUNISATION: "தடுப்பூசி" },
    hintIdle: "பட்டனை அழுத்தி, வருகையை உங்கள் மொழியில் சொல்லுங்கள். மீண்டும் அழுத்தி நிறுத்துங்கள்.",
    hintRec: "பேசுங்கள்… முடிந்ததும் அழுத்துங்கள்",
    hintBusy: "புரிந்துகொள்கிறது…",
    hintFix: "திருத்தத்தைச் சொல்லுங்கள், அல்லது ‘சரி’ என்று சொல்லுங்கள்",
    yes: "சரி, சேமி", fix: "திருத்து", saved: "சேமிக்கப்பட்டது",
    heard: "கேட்டது", typedPh: "சோதனை: வருகையை டைப் செய்யவும்", send: "அனுப்பு",
    brief: "இன்றைய வருகைகள்", pending: "உறுதிசெய்ய காத்திருப்பவை", open: "திற",
    offline: "இணையம் இல்லை. பதிவுகள் சேமிக்கப்பட்டு, இணையம் வந்ததும் அனுப்பப்படும்.",
    queued: "இணையம் வந்ததும் அனுப்பப்படும்", unknownName: "பெயர் சொல்லப்படவில்லை",
    matched: "பதிவில் உள்ளவர்", ambiguous: "யார்? தேர்ந்தெடுக்கவும்:", newP: "புதிய பயனாளி",
    micDenied: "மைக் அனுமதி தேவை.", errorPrefix: "பிழை: ",
    fields: { gestation_months: "கர்ப்ப மாதம்", bp: "BP", hb: "Hb", weight_kg: "எடை (கிலோ)",
      ifa_tablets_given: "IFA மாத்திரை", calcium_tablets_given: "கால்சியம்", td_dose: "Td ஊசி",
      baby_age_days: "குழந்தை வயது (நாள்)", temperature_c: "வெப்பநிலை °C", breastfeeding_ok: "தாய்ப்பால்",
      cord_ok: "தொப்புள் கொடி", vaccines_given: "தடுப்பூசி", complaints: "பிரச்சனை", next_visit_date: "அடுத்த வருகை" },
    yesNo: ["சரி", "இல்லை"], notSaid: "சொல்லவில்லை",
    complaints: { headache: "தலைவலி", bleeding: "ரத்தப்போக்கு", "swelling of face": "முக வீக்கம்", fever: "காய்ச்சல்",
      "blurred vision": "கண் மங்கல்", "fast breathing": "வேகமான மூச்சு", "yellow skin": "மஞ்சள் நிறம்",
      convulsions: "வலிப்பு", "not feeding": "பால் குடிக்கவில்லை", "reduced fetal movement": "குழந்தை அசைவு குறைவு" },
  },
  hi: {
    types: { ANC: "गर्भावस्था", HBNC: "नवजात शिशु", IMMUNISATION: "टीकाकरण" },
    hintIdle: "बटन दबाएँ और विज़िट अपनी भाषा में बोलें। रोकने के लिए फिर दबाएँ।",
    hintRec: "बोलिए… पूरा होने पर दबाएँ",
    hintBusy: "समझ रहा है…",
    hintFix: "सुधार बोलें, या ‘हाँ’ कहें",
    yes: "हाँ, सेव करें", fix: "सुधारें", saved: "सेव हो गया",
    heard: "सुना गया", typedPh: "टेस्ट: विज़िट टाइप करें", send: "भेजें",
    brief: "आज की विज़िट", pending: "पुष्टि बाकी", open: "खोलें",
    offline: "इंटरनेट नहीं है। रिकॉर्डिंग सेव है, इंटरनेट आने पर भेज दी जाएगी।",
    queued: "इंटरनेट आने पर भेजी जाएगी", unknownName: "नाम नहीं बताया",
    matched: "रजिस्टर में दर्ज", ambiguous: "कौन? चुनें:", newP: "नई लाभार्थी",
    micDenied: "माइक की अनुमति चाहिए।", errorPrefix: "गड़बड़ी: ",
    fields: { gestation_months: "गर्भ का महीना", bp: "BP", hb: "Hb", weight_kg: "वज़न (किलो)",
      ifa_tablets_given: "IFA गोलियाँ", calcium_tablets_given: "कैल्शियम", td_dose: "Td टीका",
      baby_age_days: "शिशु की उम्र (दिन)", temperature_c: "तापमान °C", breastfeeding_ok: "स्तनपान",
      cord_ok: "नाल", vaccines_given: "टीके", complaints: "शिकायत", next_visit_date: "अगली विज़िट" },
    yesNo: ["ठीक", "नहीं"], notSaid: "नहीं बताया",
    complaints: { headache: "सिरदर्द", bleeding: "खून आना", "swelling of face": "चेहरे पर सूजन", fever: "बुखार",
      "blurred vision": "धुंधला दिखना", "fast breathing": "तेज़ साँस", "yellow skin": "पीलिया",
      convulsions: "दौरे", "not feeding": "दूध नहीं पी रहा", "reduced fetal movement": "बच्चे की हलचल कम" },
  },
};

const FIELDS_BY_TYPE = {
  ANC: ["gestation_months", "bp", "hb", "weight_kg", "ifa_tablets_given", "calcium_tablets_given", "td_dose", "complaints", "next_visit_date"],
  HBNC: ["baby_age_days", "weight_kg", "temperature_c", "breastfeeding_ok", "cord_ok", "complaints", "next_visit_date"],
  IMMUNISATION: ["vaccines_given", "complaints", "next_visit_date"],
};

const $ = (id) => document.getElementById(id);
const state = { lang: localStore("lang") || "ta", type: "ANC", mode: "new", current: null,
                recorder: null, chunks: [], timer: null, started: 0, health: null };
const t = () => I18N[state.lang];
const asha = () => ASHAS[state.lang];

function localStore(k, v) {
  try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch { return null; }
}

/* ---------------- offline queue (IndexedDB) ---------------- */
const idb = new Promise((res, rej) => {
  const r = indexedDB.open("asha-vaani", 1);
  r.onupgradeneeded = () => r.result.createObjectStore("queue", { keyPath: "ts" });
  r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
});
async function q(mode, fn) {
  const db = await idb;
  return new Promise((res, rej) => {
    const tx = db.transaction("queue", mode); const req = fn(tx.objectStore("queue"));
    tx.oncomplete = () => res(req && req.result); tx.onerror = () => rej(tx.error);
  });
}
const enqueue = (item) => q("readwrite", (s) => s.put(item));
const queued = () => q("readonly", (s) => s.getAll());
const dequeue = (ts) => q("readwrite", (s) => s.delete(ts));

async function flushQueue() {
  if (!navigator.onLine) return;
  for (const item of await queued()) {
    try {
      await postVisit(item.blob, item.type, item.lang, item.asha_id, null, true);
      await dequeue(item.ts);
    } catch { break; }
  }
  loadPending();
}

/* ---------------- rendering ---------------- */
function renderStatic() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll(".lang button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.lang === state.lang));
  document.querySelectorAll(".types button").forEach((b) => {
    b.textContent = t().types[b.dataset.type];
    b.setAttribute("aria-selected", b.dataset.type === state.type);
  });
  $("ashaName").textContent = asha().name;
  $("yesBtn").textContent = t().yes; $("fixBtn").textContent = t().fix;
  $("briefLabel").textContent = t().brief; $("pendingTitle").textContent = t().pending;
  $("typedInput").placeholder = t().typedPh; $("typedBtn").textContent = t().send;
  $("offlineBar").textContent = t().offline;
  setHint();
}

function setHint(key) {
  key = key || (state.mode === "reply" ? "hintFix" : "hintIdle");
  $("hint").textContent = t()[key];
}

function fmtValue(field, r) {
  if (field === "bp") {
    if (r.bp_systolic) return `${r.bp_systolic}/${r.bp_diastolic ?? "?"}`;
    return r.bp_status_spoken || null;
  }
  const v = r[field];
  if (v === null || v === undefined || (Array.isArray(v) && !v.length)) return null;
  if (typeof v === "boolean") return v ? t().yesNo[0] : t().yesNo[1];
  if (field === "complaints") return v.map((c) => t().complaints[c] || c).join(", ");
  if (Array.isArray(v)) return v.join(", ");
  if (field === "next_visit_date") {
    const d = new Date(v + "T00:00");
    return d.toLocaleDateString(state.lang === "ta" ? "ta-IN" : "hi-IN", { day: "numeric", month: "long" });
  }
  return String(v);
}

function renderEntry(data, saved = false) {
  const v = data.visit; state.current = v;
  const box = $("entry"); box.hidden = false; box.classList.toggle("saved", saved);
  const sp = v.patient_spoken || {};
  $("entryName").textContent = (data.match?.patient?.name) || sp.name || t().unknownName;

  // patient match
  const mb = $("matchBox"); mb.innerHTML = "";
  const m = data.match;
  if (m?.status === "matched") {
    mb.textContent = `${t().matched}: ${m.patient.husband_name} · ${m.patient.village}`;
  } else if (m?.status === "ambiguous") {
    mb.append(t().ambiguous);
    const row = document.createElement("div");
    m.candidates.forEach((c) => {
      const b = document.createElement("button");
      b.textContent = `${c.patient.name} (${c.patient.husband_name}, ${c.patient.village})`;
      b.onclick = async () => {
        await fetch(`${API}/api/visits/${v.id}/patient`, { method: "POST",
          headers: { "Content-Type": "application/json" }, body: JSON.stringify({ patient_id: c.patient.id }) });
        mb.textContent = `${t().matched}: ${c.patient.husband_name} · ${c.patient.village}`;
        $("entryName").textContent = c.patient.name;
      };
      row.append(b);
    });
    mb.append(row);
  } else if (m) {
    mb.textContent = t().newP;
  }

  // danger stamps
  const st = $("stamps"); st.innerHTML = "";
  (v.flags || []).forEach((f) => {
    const s = document.createElement("span");
    s.className = "stamp" + (f.severity === "medium" ? " medium" : "");
    const label = document.createTextNode(f.labels[state.lang]);
    const small = document.createElement("small");
    small.textContent = f.code === "danger_symptom" ? (t().complaints[f.detail] || f.detail) : f.detail;
    s.append(label, small);
    st.append(s);
  });

  // register lines; missing expected fields shown as dotted blanks
  const dl = $("lines"); dl.innerHTML = "";
  const missing = new Set(v.missing || []);
  FIELDS_BY_TYPE[v.visit_type].forEach((f) => {
    const val = fmtValue(f, v.record || {});
    if (val === null && !missing.has(f)) return;
    const row = document.createElement("div");
    if (val === null) row.className = "blank";
    row.innerHTML = `<dt></dt><dd></dd>`;
    row.querySelector("dt").textContent = t().fields[f];
    row.querySelector("dd").textContent = val ?? t().notSaid;
    dl.append(row);
  });

  $("heard").textContent = v.transcript ? `${t().heard}: “${v.transcript}”` : "";
  if (saved) $("heard").textContent = "✓ " + t().saved;
  if (data.readback_audio) play(data.readback_audio);
  $("playBtn").onclick = () => data.readback_audio && play(data.readback_audio);
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

function play(url) {
  const p = $("player"); p.src = API + url; p.play().catch(() => {});
}

/* ---------------- recording ---------------- */
async function startRecording() {
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } }); }
  catch { $("hint").textContent = t().micDenied; return; }
  const mime = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4"].find((m) => MediaRecorder.isTypeSupported(m)) || "";
  state.recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
  state.chunks = [];
  state.recorder.ondataavailable = (e) => e.data.size && state.chunks.push(e.data);
  state.recorder.onstop = () => {
    stream.getTracks().forEach((tr) => tr.stop());
    send(new Blob(state.chunks, { type: state.recorder.mimeType || "audio/webm" }));
  };
  state.recorder.start();
  state.started = Date.now();
  $("micBtn").classList.add("recording");
  setHint("hintRec");
  tick();
  state.timer = setInterval(tick, 200);
}

function tick() {
  const el = (Date.now() - state.started) / 1000;
  const left = Math.max(0, MAX_SECONDS - el);
  $("secs").textContent = Math.ceil(left);
  $("ringFg").style.strokeDashoffset = String(578 * (1 - el / MAX_SECONDS));
  if (left <= 0) stopRecording();
}

function stopRecording() {
  clearInterval(state.timer);
  $("micBtn").classList.remove("recording");
  $("secs").textContent = ""; $("ringFg").style.strokeDashoffset = "578";
  if (state.recorder?.state === "recording") state.recorder.stop();
}

/* ---------------- talking to the server ---------------- */
async function send(blob, typedText) {
  const busy = (on) => { $("micBtn").classList.toggle("busy", on); $("micBtn").disabled = on; if (on) setHint("hintBusy"); };
  if (!navigator.onLine && blob && state.mode === "new") {
    await enqueue({ ts: Date.now(), blob, type: state.type, lang: state.lang, asha_id: asha().id });
    $("hint").textContent = t().queued; loadPending(); return;
  }
  busy(true);
  try {
    if (state.mode === "reply" && state.current) {
      const fd = new FormData();
      if (blob) fd.append("audio", blob, "reply.webm");
      if (typedText) fd.append("mock_text", typedText);
      const data = await call(`/api/visits/${state.current.id}/reply`, fd);
      if (data.saved) { onSaved(data); } else { renderEntry(data); }
    } else {
      const data = await postVisit(blob, state.type, state.lang, asha().id, typedText);
      state.mode = "reply";
      renderEntry(data);
    }
  } catch (e) {
    $("hint").textContent = t().errorPrefix + e.message;
    busy(false); return;
  }
  busy(false); setHint();
}

async function postVisit(blob, type, lang, ashaId, typedText, silent = false) {
  const fd = new FormData();
  fd.append("visit_type", type); fd.append("lang", lang); fd.append("asha_id", ashaId);
  if (blob) fd.append("audio", blob, "visit.webm");
  if (typedText) fd.append("mock_text", typedText);
  return call("/api/visits", fd);
}

async function call(path, body) {
  const r = await fetch(API + path, { method: "POST", body });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
}

function onSaved(data) {
  renderEntry({ ...data, match: null }, true);
  state.mode = "new"; state.current = null; setHint(); loadPending();
}

async function loadPending() {
  const items = [];
  (await queued().catch(() => [])).filter((i) => i.asha_id === asha().id)
    .forEach((i) => items.push({ label: `${t().types[i.type]} · ${new Date(i.ts).toLocaleTimeString()}`, note: t().queued }));
  if (navigator.onLine) {
    try {
      const drafts = await (await fetch(`${API}/api/visits?status=draft&asha_id=${asha().id}`)).json();
      drafts.filter((d) => d.id !== state.current?.id).slice(0, 5).forEach((d) =>
        items.push({ label: `${t().types[d.visit_type]} · ${(d.patient_spoken || {}).name || "?"}`, visit: d }));
    } catch { /* offline */ }
  }
  const ul = $("pendingList"); ul.innerHTML = "";
  $("pending").hidden = !items.length;
  items.forEach((it) => {
    const li = document.createElement("li"); li.textContent = it.label;
    if (it.visit) {
      const b = document.createElement("button"); b.textContent = t().open;
      b.onclick = () => { state.mode = "reply"; renderEntry({ visit: it.visit }); setHint(); };
      li.append(b);
    } else { const s = document.createElement("span"); s.textContent = it.note; li.append(s); }
    ul.append(li);
  });
}

async function loadBriefing() {
  const list = $("briefList");
  try {
    const b = await (await fetch(`${API}/api/briefing?asha_id=${asha().id}&lang=${state.lang}`)).json();
    list.innerHTML = "";
    b.items.forEach((it) => {
      const li = document.createElement("li");
      li.textContent = [it.patient.name, it.detail, it.vax].filter(Boolean).join(" — ");
      if (it.kind === "flag") li.className = "flag";
      list.append(li);
    });
    list.hidden = !b.items.length;
    play(b.audio);
  } catch (e) { list.hidden = false; list.textContent = t().offline; }
}

/* ---------------- wiring ---------------- */
document.querySelectorAll(".lang button").forEach((b) => b.onclick = () => {
  state.lang = b.dataset.lang; localStore("lang", state.lang);
  state.mode = "new"; state.current = null; $("entry").hidden = true; $("briefList").hidden = true;
  renderStatic(); loadPending();
});
document.querySelectorAll(".types button").forEach((b) => b.onclick = () => {
  state.type = b.dataset.type; state.mode = "new"; state.current = null; $("entry").hidden = true; renderStatic();
});
$("micBtn").onclick = () => (state.recorder?.state === "recording" ? stopRecording() : startRecording());
$("yesBtn").onclick = async () => {
  if (!state.current) return;
  try { onSaved(await call(`/api/visits/${state.current.id}/confirm`, null)); }
  catch (e) { $("hint").textContent = t().errorPrefix + e.message; }
};
$("fixBtn").onclick = () => { state.mode = "reply"; setHint("hintFix"); startRecording(); };
$("briefBtn").onclick = loadBriefing;
$("typedForm").onsubmit = (e) => {
  e.preventDefault(); const v = $("typedInput").value.trim(); if (!v) return;
  $("typedInput").value = ""; send(null, v);
};
const setOnline = () => { $("offlineBar").hidden = navigator.onLine; if (navigator.onLine) flushQueue(); };
addEventListener("online", setOnline); addEventListener("offline", setOnline);

(async function init() {
  renderStatic(); setOnline(); loadPending();
  try {
    state.health = await (await fetch(`${API}/api/health`)).json();
    $("typedForm").hidden = !state.health.mock.stt;   // typing box only in test mode
  } catch { /* offline */ }
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
})();
