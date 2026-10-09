"""Normalizacija teksta za pretragu: bez kvačica, mala slova, osnovni padeži.

Ista logika je preslikana u web/app.js (funkcije normaliziraj/korijen) —
kad mijenjaš jedno, promijeni i drugo (testovi provjeravaju oba).
"""
from __future__ import annotations

import re
import unicodedata

# Đ se piše kao "đ", "dj" ili samo "d" — sve svodimo na "d" (Đulagina = Djulagina = Dulagina).
_ZAMJENE = str.maketrans({"đ": "d", "Đ": "d", "ð": "d"})

# Riječi koje ne nose značenje u upitu ("u Dobrinji", "ulica Zagrebačka").
STOP_RIJECI = frozenset(
    "u na ul ulica ulici ulice ulicu ulicama naselje naselju naselja kod iz za "
    "i te dio dijelu dijela oko prema br broj bb".split()
)

# Padežni nastavci, najduži prvi. Korijen mora ostati dug bar 3 slova
# (Brdu/Brdo -> brd), da kratka imena ne nestanu.
_NASTAVCI = ("ama", "ima", "oga", "omu", "om", "em", "oj", "ih", "im", "og",
             "a", "e", "i", "u", "o")
_MIN_KORIJEN = 3


def normaliziraj(tekst: str) -> str:
    """Mala slova, bez dijakritika (č->c, ć->c, š->s, ž->z, đ/dj->d), sređeni razmaci."""
    t = (tekst or "").translate(_ZAMJENE)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(z for z in t if not unicodedata.combining(z))
    t = t.lower().replace("dj", "d")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()


def korijen(rijec: str) -> str:
    """Vrlo jednostavno skidanje padežnog nastavka (Dobrinji -> dobrinj)."""
    for n in _NASTAVCI:
        if rijec.endswith(n) and len(rijec) - len(n) >= _MIN_KORIJEN:
            return rijec[: -len(n)]
    return rijec


def tokeni(tekst: str, bez_stop: bool = True) -> list[str]:
    """Normalizirani korijeni riječi."""
    rijeci = normaliziraj(tekst).split()
    if bez_stop:
        rijeci = [r for r in rijeci if r not in STOP_RIJECI]
    return [korijen(r) for r in rijeci]


def odgovara(upit: str, naziv: str) -> bool:
    """Da li upit odgovara nazivu ulice/naselja (sve riječi upita se nalaze u nazivu).

    Riječ upita odgovara riječi naziva ako su im korijeni jednaki ili ako je
    korijen upita početak korijena naziva (djelimično kucanje: "dobr" -> Dobrinja).
    """
    u = tokeni(upit)
    if not u:
        return False
    n = tokeni(naziv, bez_stop=False)
    return all(any(nt == ut or nt.startswith(ut) for nt in n) for ut in u)
