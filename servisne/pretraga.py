"""Pretraga najava po ulici ili naselju (referentna implementacija; web/app.js radi isto)."""
from __future__ import annotations

from .normalizacija import normaliziraj, odgovara, tokeni


def pretrazi(najave: list[dict], upit: str, ulice_naselja: dict[str, list[str]] | None = None
             ) -> list[tuple[dict, str]]:
    """Vraća (najava, razlog) — razlog: "ulica", "naselje", "cijelo naselje" ili "tekst"."""
    if not tokeni(upit):
        return [(n, "") for n in najave]
    # Naselja u kojima je ulica koju korisnik traži (npr. "Trg solidarnosti" -> Dobrinja).
    naselja_ulice = {ns for u, lista in (ulice_naselja or {}).items()
                     if odgovara(upit, u) for ns in lista}
    rez = []
    for n in najave:
        if any(odgovara(upit, u) for u in n["ulice"]):
            rez.append((n, "ulica"))
        elif any(odgovara(upit, x) for x in n["naselja"]):
            rez.append((n, "cijelo naselje" if n["cijelo_naselje"] else "naselje"))
        elif n["cijelo_naselje"] and naselja_ulice & set(n["naselja"]):
            rez.append((n, "cijelo naselje"))
        elif _u_tekstu(upit, n["tekst"]):
            rez.append((n, "tekst"))
    return rez


def _u_tekstu(upit: str, tekst: str) -> bool:
    t = tokeni(tekst, bez_stop=False)
    return all(any(x == u or x.startswith(u) for x in t) for u in tokeni(upit)) \
        and len(normaliziraj(upit)) >= 3
