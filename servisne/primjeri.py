"""Izmišljeni PRIMJERI za prikaz stranice kad zvanični izvor nije dostupan."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from .izvlacenje import obogati
from .izvori import vik_sarajevo
from .model import Najava

PRIMJERI = Path(__file__).resolve().parent.parent / "data" / "primjeri.json"


def napravi(danas: date | None = None) -> list[Najava]:
    danas = danas or date.today()
    zamjene = {f"{{D{i}}}": (danas + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(8)}
    najave = []
    for p in json.loads(PRIMJERI.read_text(encoding="utf-8"))["primjeri"]:
        tekst = p["tekst"]
        for k, v in zamjene.items():
            tekst = tekst.replace(k, v)
        h, m = map(int, p["objava_sat"].split(":"))
        objavljeno = datetime.combine(danas + timedelta(days=p["objava_dana"]), datetime.min.time()).replace(hour=h, minute=m)
        najave.append(Najava(
            izvor=f"PRIMJER — {vik_sarajevo.NAZIV}", usluga=vik_sarajevo.USLUGA,
            naslov="PRIMJER: " + p["naslov"],
            tekst="PRIMJER (izmišljen tekst, nije stvarna najava). " + tekst,
            link=vik_sarajevo.URL,
            objavljeno=objavljeno.isoformat(timespec="minutes"),
            primjer=True, **obogati(tekst, objavljeno)))
    return najave
