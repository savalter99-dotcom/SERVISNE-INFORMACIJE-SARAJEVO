/* Servisne informacije Sarajevo — pretraga i prikaz najava iz najave.json.
 * Normalizacija i pretraga su ista logika kao servisne/normalizacija.py i
 * servisne/pretraga.py (testovi provjeravaju da se slažu). */
"use strict";

// ------------------------------------------------------------ normalizacija

const STOP_RIJECI = new Set(("u na ul ulica ulici ulice ulicu ulicama naselje naselju naselja kod iz za " +
  "i te dio dijelu dijela oko prema br broj bb").split(" "));
const NASTAVCI = ["ama", "ima", "oga", "omu", "om", "em", "oj", "ih", "im", "og",
  "a", "e", "i", "u", "o"];
const MIN_KORIJEN = 3;

function normaliziraj(tekst) {
  return (tekst || "")
    .replace(/[đĐð]/g, "d")
    .normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/dj/g, "d")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function korijen(r) {
  for (const n of NASTAVCI) {
    if (r.endsWith(n) && r.length - n.length >= MIN_KORIJEN) return r.slice(0, -n.length);
  }
  return r;
}

function tokeni(tekst, bezStop = true) {
  let r = normaliziraj(tekst).split(" ").filter(Boolean);
  if (bezStop) r = r.filter(x => !STOP_RIJECI.has(x));
  return r.map(korijen);
}

function odgovara(upit, naziv) {
  const u = tokeni(upit);
  if (!u.length) return false;
  const n = tokeni(naziv, false);
  return u.every(ut => n.some(nt => nt === ut || nt.startsWith(ut)));
}

function uTekstu(upit, tekst) {
  const t = tokeni(tekst, false);
  return normaliziraj(upit).length >= 3 &&
    tokeni(upit).every(u => t.some(x => x === u || x.startsWith(u)));
}

/** Vraća [{najava, razlog}] — razlog: "ulica", "naselje", "cijelo naselje", "tekst" ili "". */
function pretrazi(najave, upit, uliceNaselja = {}) {
  if (!tokeni(upit).length) return najave.map(n => ({ najava: n, razlog: "" }));
  const naseljaUlice = new Set();
  for (const [u, lista] of Object.entries(uliceNaselja)) {
    if (odgovara(upit, u)) lista.forEach(x => naseljaUlice.add(x));
  }
  const rez = [];
  for (const n of najave) {
    let razlog = null;
    if (n.ulice.some(u => odgovara(upit, u))) razlog = "ulica";
    else if (n.naselja.some(x => odgovara(upit, x))) razlog = n.cijelo_naselje ? "cijelo naselje" : "naselje";
    else if (n.cijelo_naselje && n.naselja.some(x => naseljaUlice.has(x))) razlog = "cijelo naselje";
    else if (uTekstu(upit, n.tekst)) razlog = "tekst";
    if (razlog) rez.push({ najava: n, razlog });
  }
  return rez;
}

// ------------------------------------------------------------ vrijeme

function pocetakDana(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; }
function dodajDane(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }

/** [početak, kraj) prekida; bez kraja = do kraja dana početka. */
function interval(n) {
  const od = n.prekid_od ? new Date(n.prekid_od) : (n.objavljeno ? new Date(n.objavljeno) : null);
  if (!od) return null;
  const kraj = n.prekid_do ? new Date(n.prekid_do) : dodajDane(pocetakDana(od), 1);
  return [od, kraj];
}

function uPeriodu(n, filter, sada = new Date()) {
  if (filter === "sve") return true;
  const iv = interval(n);
  if (!iv) return false;
  const danas = pocetakDana(sada);
  let od, kraj;
  if (filter === "danas") { od = danas; kraj = dodajDane(danas, 1); }
  else if (filter === "sutra") { od = dodajDane(danas, 1); kraj = dodajDane(danas, 2); }
  else { // ova sedmica: od ponedjeljka do nedjelje
    const pon = dodajDane(danas, -((danas.getDay() + 6) % 7));
    od = pon; kraj = dodajDane(pon, 7);
  }
  return iv[0] < kraj && iv[1] > od;
}

const DANI = ["nedjelja", "ponedjeljak", "utorak", "srijeda", "četvrtak", "petak", "subota"];
const dvije = x => String(x).padStart(2, "0");
const datumTxt = d => `${DANI[d.getDay()]}, ${d.getDate()}. ${d.getMonth() + 1}. ${d.getFullYear()}.`;
const satTxt = d => `${dvije(d.getHours())}:${dvije(d.getMinutes())}`;
const imaSat = iso => /T\d\d:\d\d/.test(iso || "");

function vrijemePrekida(n) {
  if (!n.prekid_od) return "Termin nije naveden u najavi";
  const od = new Date(n.prekid_od);
  let t = datumTxt(od);
  if (imaSat(n.prekid_od)) t += ` od ${satTxt(od)}`;
  if (n.prekid_do) {
    const doo = new Date(n.prekid_do);
    t += pocetakDana(doo).getTime() === pocetakDana(od).getTime()
      ? ` do ${satTxt(doo)}` : ` do ${datumTxt(doo)} ${satTxt(doo)}`;
  } else {
    t += " — do završetka radova";
  }
  return t;
}

// ------------------------------------------------------------ prikaz

const IKONE = { voda: "💧", struja: "⚡", plin: "🔥", grijanje: "♨️" };

function el(tag, attrs = {}, ...djeca) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else e.setAttribute(k, v);
  }
  for (const d of djeca) if (d != null) e.append(d);
  return e;
}

function kartica({ najava: n, razlog }, sada) {
  const iv = interval(n);
  const zavrseno = iv && iv[1] < sada;
  const traje = iv && iv[0] <= sada && iv[1] > sada;
  const vrstaKlasa = "vrsta-" + n.vrsta.replace(/\s+/g, "-");

  const oznake = el("div", { class: "oznake" },
    el("span", { class: `oznaka ${vrstaKlasa}` }, n.vrsta),
    traje ? el("span", { class: "oznaka u-toku" }, "u toku") : null,
    zavrseno ? el("span", { class: "oznaka zavrseno" }, "završeno") : null,
    n.primjer ? el("span", { class: "oznaka primjer" }, "PRIMJER") : null);

  const mjesta = el("dl", { class: "mjesta" });
  const red = (naziv, vrijednost) => { if (vrijednost) mjesta.append(el("dt", {}, naziv), el("dd", {}, vrijednost)); };
  red("Općina", n.opcine.join(", "));
  if (n.naselja.length) {
    const dd = document.createDocumentFragment();
    dd.append(n.naselja.join(", "));
    if (n.cijelo_naselje) dd.append(" ", el("span", { class: "cijelo" }, "cijelo naselje"));
    red("Naselje", dd);
  }
  red("Ulice", n.ulice.join(", "));

  const pogodak = razlog === "cijelo naselje"
    ? el("p", { class: "pogodak" }, "Najava navodi samo naselje — odnosi se na cijelo naselje, uključujući ulicu koju tražite.")
    : razlog === "tekst" ? el("p", { class: "pogodak" }, "Pojam je pronađen u tekstu najave.") : null;

  return el("article", { class: "kartica" + (zavrseno ? " prosla" : "") + (n.primjer ? " je-primjer" : "") },
    el("div", { class: "kartica-glava" },
      el("span", { class: "usluga", title: n.usluga }, IKONE[n.usluga] || "ℹ️"),
      el("div", {}, el("h2", {}, n.naslov), el("p", { class: "izvor" }, n.izvor))),
    oznake,
    el("p", { class: "termin" }, vrijemePrekida(n)),
    mjesta,
    pogodak,
    el("details", {},
      el("summary", {}, "Originalni tekst"),
      el("p", { class: "original" }, n.tekst)),
    el("p", { class: "dno-kartice" },
      n.objavljeno ? el("span", {}, `Objavljeno: ${datumTxt(new Date(n.objavljeno))} ${imaSat(n.objavljeno) ? satTxt(new Date(n.objavljeno)) : ""}`) : null,
      el("a", { href: n.link, target: "_blank", rel: "noopener" }, "Originalna objava ↗")));
}

function poredaj(lista, sada) {
  // Prvo aktuelne i buduće (najranije prve), pa završene (najnovije prve).
  const kljuc = x => interval(x.najava) || [new Date(0), new Date(0)];
  return lista.sort((a, b) => {
    const [ao, ak] = kljuc(a), [bo, bk] = kljuc(b);
    const ap = ak < sada, bp = bk < sada;
    if (ap !== bp) return ap ? 1 : -1;
    return ap ? bo - ao : ao - bo;
  });
}

function pokreni() {
  const stanje = { upit: "", period: "sve", vrsta: "sve", podaci: null };
  const $ = s => document.querySelector(s);

  const iscrtaj = () => {
    const sada = new Date();
    const p = stanje.podaci;
    let lista = pretrazi(p.najave, stanje.upit, p.ulice_naselja)
      .filter(x => uPeriodu(x.najava, stanje.period, sada))
      .filter(x => stanje.vrsta === "sve" || x.najava.vrsta === stanje.vrsta);
    lista = poredaj(lista, sada);
    const kont = $("#najave");
    kont.replaceChildren(...lista.map(x => kartica(x, sada)));
    $("#broj").textContent = lista.length === 1 ? "1 najava" :
      `${lista.length} ${lista.length % 10 >= 2 && lista.length % 10 <= 4 && (lista.length % 100 < 12 || lista.length % 100 > 14) ? "najave" : "najava"}`;
    $("#prazno").hidden = lista.length > 0;
  };

  $("#pretraga").addEventListener("input", e => { stanje.upit = e.target.value; iscrtaj(); });
  for (const grupa of ["period", "vrsta"]) {
    document.querySelectorAll(`[data-${grupa}]`).forEach(b => b.addEventListener("click", () => {
      stanje[grupa] = b.dataset[grupa];
      document.querySelectorAll(`[data-${grupa}]`).forEach(x => x.setAttribute("aria-pressed", String(x === b)));
      iscrtaj();
    }));
  }

  fetch("najave.json", { cache: "no-store" })
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(p => {
      stanje.podaci = p;
      $("#primjer-upozorenje").hidden = !p.sadrzi_primjere;
      const nedostupni = p.izvori.filter(i => i.status !== "ok");
      $("#izvori-greska").hidden = !nedostupni.length;
      $("#izvori-greska").textContent = nedostupni.length
        ? "Trenutno nedostupan izvor: " + nedostupni.map(i => i.naziv).join(", ") + "." : "";
      const o = new Date(p.osvjezeno);
      $("#osvjezeno").textContent = `${datumTxt(o)} u ${satTxt(o)}`;
      $("#izvori").replaceChildren(...p.izvori.map(i =>
        el("li", {}, el("a", { href: i.url, target: "_blank", rel: "noopener" }, i.naziv),
          ` (${i.usluga}) — ${i.status === "ok" ? "dostupan" : "nedostupan pri zadnjem osvježavanju"}`)));
      iscrtaj();
    })
    .catch(() => { $("#prazno").hidden = false; $("#prazno").textContent = "Najave se ne mogu učitati (najave.json)."; });
}

if (typeof module !== "undefined") {
  module.exports = { normaliziraj, korijen, tokeni, odgovara, pretrazi, uPeriodu };
} else {
  document.addEventListener("DOMContentLoaded", pokreni);
}
