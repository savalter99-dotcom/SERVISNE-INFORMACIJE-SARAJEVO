"""SQLite pohrana najava i izvoz u najave.json."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .izvlacenje import gazeter
from .model import Najava

KORIJEN = Path(__file__).resolve().parent.parent
BAZA = KORIJEN / "data" / "najave.sqlite"
JSON = KORIJEN / "web" / "najave.json"

_SHEMA = """
CREATE TABLE IF NOT EXISTS najave (
    id TEXT PRIMARY KEY,
    izvor TEXT NOT NULL,
    usluga TEXT NOT NULL,
    naslov TEXT,
    tekst TEXT NOT NULL,
    link TEXT NOT NULL,
    objavljeno TEXT,
    prekid_od TEXT,
    prekid_do TEXT,
    vrsta TEXT,
    opcine TEXT,      -- JSON lista
    naselja TEXT,     -- JSON lista
    ulice TEXT,       -- JSON lista
    cijelo_naselje INTEGER,
    primjer INTEGER,
    prikupljeno TEXT
);
CREATE TABLE IF NOT EXISTS prikupljanja (
    vrijeme TEXT, izvor TEXT, status TEXT, broj INTEGER, poruka TEXT
);
"""
_LISTE = ("opcine", "naselja", "ulice")


def otvori(putanja: Path = BAZA) -> sqlite3.Connection:
    putanja.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(putanja)
    c.row_factory = sqlite3.Row
    c.executescript(_SHEMA)
    return c


def sacuvaj(c: sqlite3.Connection, najave: list[Najava]) -> int:
    sada = datetime.now().isoformat(timespec="seconds")
    for n in najave:
        d = n.u_rjecnik()
        for k in _LISTE:
            d[k] = json.dumps(d[k], ensure_ascii=False)
        d["prikupljeno"] = sada
        kolone = ", ".join(d)
        c.execute(f"INSERT OR REPLACE INTO najave ({kolone}) VALUES ({', '.join(':' + k for k in d)})", d)
    c.commit()
    return len(najave)


def obrisi_primjere(c: sqlite3.Connection) -> None:
    c.execute("DELETE FROM najave WHERE primjer = 1")
    c.commit()


def zabiljezi(c: sqlite3.Connection, izvor: str, status: str, broj: int, poruka: str = "") -> None:
    c.execute("INSERT INTO prikupljanja VALUES (?, ?, ?, ?, ?)",
              (datetime.now().isoformat(timespec="seconds"), izvor, status, broj, poruka))
    c.commit()


def sve(c: sqlite3.Connection) -> list[dict]:
    redovi = c.execute(
        "SELECT * FROM najave ORDER BY COALESCE(prekid_od, objavljeno) DESC").fetchall()
    rez = []
    for r in redovi:
        d = dict(r)
        for k in _LISTE:
            d[k] = json.loads(d[k] or "[]")
        d["cijelo_naselje"] = bool(d["cijelo_naselje"])
        d["primjer"] = bool(d["primjer"])
        rez.append(d)
    return rez


def ulice_naselja(najave: list[dict]) -> dict[str, list[str]]:
    """Gazeter ulica + ono što se nauči iz najava koje navode jedno naselje i ulice."""
    mapa = {u: list(ns) for u, ns in gazeter()["ulice"].items()}
    for n in najave:
        if len(n["naselja"]) == 1:
            for u in n["ulice"]:
                lista = mapa.setdefault(u, [])
                if n["naselja"][0] not in lista:
                    lista.append(n["naselja"][0])
    return mapa


def izvezi(c: sqlite3.Connection, izvori: list[dict], putanja: Path = JSON) -> dict:
    najave = sve(c)
    podaci = {
        "osvjezeno": datetime.now().isoformat(timespec="minutes"),
        "sadrzi_primjere": any(n["primjer"] for n in najave),
        "izvori": izvori,
        "ulice_naselja": ulice_naselja(najave),
        "najave": najave,
    }
    putanja.parent.mkdir(parents=True, exist_ok=True)
    putanja.write_text(json.dumps(podaci, ensure_ascii=False, indent=1), encoding="utf-8")
    return podaci
