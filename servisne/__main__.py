"""Prikupljanje: python -m servisne [--primjeri] [--stranica N]

Pokreće sve izvore, sprema u SQLite (data/najave.sqlite) i izvozi web/najave.json.
--primjeri: ako nijedan izvor nije dao stvarne najave, ubaci PRIMJERE (jasno označene).
"""
from __future__ import annotations

import argparse
import sys

from . import baza, primjeri
from .izvori import IZVORI, IzvorNedostupan


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m servisne", description=__doc__.splitlines()[0])
    ap.add_argument("--primjeri", action="store_true",
                    help="ubaci označene PRIMJERE ako stvarni podaci nisu dostupni")
    ap.add_argument("--stranica", type=int, default=2, help="koliko stranica liste čitati po izvoru")
    a = ap.parse_args(argv)

    c = baza.otvori()
    stanje, stvarnih = [], 0
    for izvor in IZVORI:
        print(f"→ {izvor.NAZIV}: {izvor.URL}")
        try:
            najave = izvor.prikupi(stranica_liste=a.stranica)
        except IzvorNedostupan as e:
            print(f"  ✗ NEDOSTUPNO: {e}")
            baza.zabiljezi(c, izvor.ID, "nedostupno", 0, str(e))
            stanje.append({"id": izvor.ID, "naziv": izvor.NAZIV, "url": izvor.URL,
                           "usluga": izvor.USLUGA, "status": "nedostupno", "poruka": str(e)})
            continue
        baza.sacuvaj(c, najave)
        stvarnih += len(najave)
        print(f"  ✓ pronađeno najava: {len(najave)}")
        baza.zabiljezi(c, izvor.ID, "ok", len(najave))
        stanje.append({"id": izvor.ID, "naziv": izvor.NAZIV, "url": izvor.URL,
                       "usluga": izvor.USLUGA, "status": "ok", "poruka": ""})

    if stvarnih:
        baza.obrisi_primjere(c)  # čim ima stvarnih podataka, primjeri nestaju
    elif a.primjeri:
        baza.obrisi_primjere(c)
        n = baza.sacuvaj(c, primjeri.napravi())
        print(f"  ! Stvarni podaci nedostupni — ubačeno {n} PRIMJERA (označeni kao PRIMJER).")

    podaci = baza.izvezi(c, stanje)
    ukupno = len(podaci["najave"])
    print(f"Izvezeno u {baza.JSON.relative_to(baza.KORIJEN)}: {ukupno} najava"
          f" (stvarnih iz ovog prikupljanja: {stvarnih})")
    return 0 if stvarnih else 2


if __name__ == "__main__":
    sys.exit(main())
