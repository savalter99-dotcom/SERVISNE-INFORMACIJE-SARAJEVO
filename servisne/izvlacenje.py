"""Izvlačenje strukturiranih podataka iz slobodnog teksta najave.

Zajedničko za sve izvore: ulice, naselja, općine, vrijeme prekida i vrsta.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from .normalizacija import korijen, normaliziraj

GAZETER = Path(__file__).resolve().parent.parent / "data" / "gazeter.json"


@lru_cache(maxsize=1)
def gazeter() -> dict:
    return json.loads(GAZETER.read_text(encoding="utf-8"))


def _korijeni_fraze(tekst: str) -> list[str]:
    return [korijen(r) for r in normaliziraj(tekst).split()]


def _sadrzi_frazu(tekst_korijeni: list[str], fraza: str) -> bool:
    f = _korijeni_fraze(fraza)
    n = len(f)
    return any(tekst_korijeni[i:i + n] == f for i in range(len(tekst_korijeni) - n + 1))


# ---------------------------------------------------------------- ulice

# Okidač nakon kojeg slijedi popis ulica: "u ulicama:", "ulica", "ul.", "dio ulice".
_OKIDAC_ULICE = re.compile(
    r"\b(?:ulic(?:ama|a|e|i|u)\b|ul\.)\s*:?\s*", re.IGNORECASE)

# Gdje popis ulica prestaje.
_KRAJ_POPISA = re.compile(
    r"(?:(?<!\d)\.\s|\.$|;|\n|\s[–-]\s|\(|\s(?:od|do|u)\s+\d|"
    r"\s(?:zbog|radi|u periodu|u vremenu|dana|danas|sutra|"
    r"kao i naselj|i naselj|te naselj|na podru[čc]ju|u naselj|naselj|bi[ćc]e|"
    r"bez vode|privremeno|mogu[ćc]e|o[čc]ekuje)\b)",
    re.IGNORECASE)

_RAZDJELNIK = re.compile(r"\s*,\s*|\s+i\s+|\s+te\s+|\s+kao i\s+", re.IGNORECASE)

_OCISTI_ULICU = [
    re.compile(r"^(?:u\s+)?(?:dijel(?:u|a)|dio)\s+(?:ulic\w*\s+)?", re.IGNORECASE),
    re.compile(r"^(?:ulic\w*|ul\.)\s*", re.IGNORECASE),
    re.compile(r"\s*(?:br\.?|broj(?:evi)?)\s*[\d\s/a-z,\-–]*$", re.IGNORECASE),
    re.compile(r"\s+\d+[a-z]?(?:\s*[-–]\s*\d+[a-z]?)?$", re.IGNORECASE),
    re.compile(r"\s+(?:neparni|parni)\s+brojevi.*$", re.IGNORECASE),
    re.compile(r"[\s:.,]+$"),
]


def _ocisti_ulicu(s: str) -> str:
    s = s.strip(" :,.\"'„“”")
    for r in _OCISTI_ULICU:
        s = r.sub("", s).strip()
    return s


def izvuci_ulice(tekst: str) -> list[str]:
    """Ulice navedene iza riječi "ulica/ulici/ulicama/ul." (redoslijed sačuvan)."""
    ulice: list[str] = []
    for m in _OKIDAC_ULICE.finditer(tekst):
        ostatak = tekst[m.end():]
        kraj = _KRAJ_POPISA.search(ostatak)
        popis = ostatak[: kraj.start()] if kraj else ostatak
        for dio in _RAZDJELNIK.split(popis):
            u = _ocisti_ulicu(dio)
            # Ulica mora počinjati velikim slovom ili brojem ("1. maja"),
            # inače je to obična riječ ("ulica će biti zatvorena").
            if not u or not (u[0].isupper() or u[0].isdigit()):
                continue
            if len(u) < 3 or len(u) > 60:
                continue
            if u not in ulice:
                ulice.append(u)
    return ulice


# ---------------------------------------------------------------- naselja

_OKIDAC_NASELJA = re.compile(
    r"\bnaselj(?:ima|e|a|u)\b\s*:?\s*", re.IGNORECASE)


def izvuci_naselja(tekst: str) -> list[str]:
    """Naselja iz gazetera (u bilo kojem padežu, sa ili bez kvačica) i iza riječi "naselje"."""
    kor = _korijeni_fraze(tekst)
    nadjena: list[str] = []
    # Duža imena prvo, da "Hrasno Brdo" ne proizvede i "Hrasno".
    sva = sorted({n for ns in gazeter()["opcine"].values() for n in ns},
                 key=lambda n: -len(n.split()))
    pokriveno: set[int] = set()
    for naselje in sva:
        f = _korijeni_fraze(naselje)
        n = len(f)
        for i in range(len(kor) - n + 1):
            if kor[i:i + n] == f and not pokriveno & set(range(i, i + n)):
                pokriveno |= set(range(i, i + n))
                if naselje not in nadjena:
                    nadjena.append(naselje)
    # Naselja kojih nema u gazeteru, ali stoje iza riječi "naselje".
    for m in _OKIDAC_NASELJA.finditer(tekst):
        ostatak = tekst[m.end():]
        kraj = _KRAJ_POPISA.search(ostatak)
        for dio in _RAZDJELNIK.split(ostatak[: kraj.start()] if kraj else ostatak):
            d = dio.strip(" :,.")
            if d and d[0].isupper() and 2 < len(d) <= 40 and len(d.split()) <= 3:
                if not any(_korijeni_fraze(d) == _korijeni_fraze(x) for x in nadjena):
                    nadjena.append(d)
    return nadjena


def opcine_za(naselja: list[str], tekst: str) -> list[str]:
    """Općine: izričito navedene u tekstu ili izvedene iz naselja."""
    kor = _korijeni_fraze(tekst)
    rez: list[str] = []
    for opcina, ns in gazeter()["opcine"].items():
        izricito = _sadrzi_frazu(kor, "općina " + opcina) or _sadrzi_frazu(kor, "općini " + opcina)
        if izricito or any(n in ns for n in naselja):
            rez.append(opcina)
    return rez


def naselja_za_ulicu(ulica: str) -> list[str]:
    """Naselja kojima ulica pripada prema gazeteru (prazno ako nije poznato)."""
    k = _korijeni_fraze(ulica)
    for u, ns in gazeter()["ulice"].items():
        if _korijeni_fraze(u) == k:
            return ns
    return []


# ---------------------------------------------------------------- vrsta

def odredi_vrstu(tekst: str) -> str:
    t = normaliziraj(tekst)
    if re.search(r"\bredukcij|\brestrikcij|\bnestasic", t):
        return "redukcija"
    if re.search(r"\bkvar|\bhavarij|\bpucanj|\bpuknu|\bintervenc|\bhitn", t):
        return "kvar"
    if re.search(r"\bplanira|\bradov|\bzamjen|\bprikljuc|\brekonstrukc|\bodrzavanj|\bispiranj", t):
        return "planirani radovi"
    return "ostalo"


# ---------------------------------------------------------------- vrijeme

_DATUM = re.compile(r"\b(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{4})?")
_INTERVAL = re.compile(
    r"\bod\s+(\d{1,2})(?:[:.,](\d{2}))?\s*(?:h|sati|časova|casova)?\s*"
    r"do\s+(\d{1,2})(?:[:.,](\d{2}))?\s*(?:h|sati|časova|casova)?",
    re.IGNORECASE)
_POCETAK = re.compile(
    r"\b(?:od|po[čc]ev(?:ši)? od|u)\s+(\d{1,2})[:.,](\d{2})\s*(?:h|sati|časova|casova)?",
    re.IGNORECASE)


def _datum_prekida(tekst: str, objavljeno: datetime | None) -> date | None:
    baza = (objavljeno or datetime.now()).date()
    t = normaliziraj(tekst)
    for m in _DATUM.finditer(tekst):
        d, mj, g = int(m.group(1)), int(m.group(2)), m.group(3)
        try:
            kandidat = date(int(g) if g else baza.year, mj, d)
        except ValueError:
            continue
        # Datum bez godine koji je "prošao" vjerovatno je u sljedećoj godini.
        if not g and kandidat < baza - timedelta(days=60):
            kandidat = kandidat.replace(year=kandidat.year + 1)
        return kandidat
    if re.search(r"\bprekosutra\b", t):
        return baza + timedelta(days=2)
    if re.search(r"\bsutra\b|\bsutrasnj", t):
        return baza + timedelta(days=1)
    if re.search(r"\bdanas\b|\bod jutros\b|\btrenutno\b|\bod \d", t) or objavljeno:
        return baza
    return None


def izvuci_vrijeme(tekst: str, objavljeno: datetime | None = None) -> tuple[str | None, str | None]:
    """(prekid_od, prekid_do) kao ISO stringovi; do = None ako kraj nije naveden."""
    dan = _datum_prekida(tekst, objavljeno)
    if dan is None:
        return None, None
    m = _INTERVAL.search(tekst)
    if m:
        h1, m1, h2, m2 = int(m.group(1)), int(m.group(2) or 0), int(m.group(3)), int(m.group(4) or 0)
        if h1 < 24 and h2 < 24 and m1 < 60 and m2 < 60:
            od = datetime.combine(dan, datetime.min.time()).replace(hour=h1, minute=m1)
            do = od.replace(hour=h2, minute=m2)
            if do <= od:
                do += timedelta(days=1)
            return od.isoformat(timespec="minutes"), do.isoformat(timespec="minutes")
    m = _POCETAK.search(tekst)
    if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
        od = datetime.combine(dan, datetime.min.time()).replace(
            hour=int(m.group(1)), minute=int(m.group(2)))
        return od.isoformat(timespec="minutes"), None
    # Samo dan, bez sata.
    return dan.isoformat(), None


# ---------------------------------------------------------------- sve zajedno

def obogati(tekst: str, objavljeno: datetime | None = None) -> dict:
    """Sva izvedena polja za Najava iz originalnog teksta."""
    ulice = izvuci_ulice(tekst)
    naselja = izvuci_naselja(tekst)
    cijelo = bool(naselja) and not ulice
    # Naselja poznatih ulica (gazeter) — da se najava nađe i po naselju.
    for u in ulice:
        for n in naselja_za_ulicu(u):
            if n not in naselja:
                naselja.append(n)
    od, do = izvuci_vrijeme(tekst, objavljeno)
    return {
        "ulice": ulice,
        "naselja": naselja,
        "opcine": opcine_za(naselja, tekst),
        "cijelo_naselje": cijelo,
        "vrsta": odredi_vrstu(tekst),
        "prekid_od": od,
        "prekid_do": do,
    }
