"""KJKP "Vodovod i kanalizacija" d.o.o. Sarajevo — servisne informacije.

Zvanična stranica: https://www.viksa.ba/objave/servisne_informacije
(lista objava, stranice se listaju parametrom ?str=N; svaka objava ima
datum i vrijeme objave u obliku "13.10.2021 u 08:41").

Struktura HTML-a nije bila provjerena uživo (stranica je bila blokirana iz
razvojnog okruženja), zato je parser namjerno tolerantan:
  1. na listi traži linkove na pojedinačne objave (/objave/...);
  2. ako ih nađe, otvara svaku i uzima naslov, datum i tekst;
  3. ako ih ne nađe, dijeli tekst same liste po datumima objave.
Ako ništa od toga ne uspije, baca IzvorNedostupan s jasnom porukom.
"""
from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlsplit

from ..izvlacenje import obogati
from ..model import Najava
from .zajednicko import IzvorNedostupan, Preuzimac, procitaj

ID = "vik"
NAZIV = "ViK Sarajevo"
USLUGA = "voda"
URL = "https://www.viksa.ba/objave/servisne_informacije"

_DATUM_OBJAVE = re.compile(
    r"(\d{1,2})\.(\d{1,2})\.(\d{4})\.?\s*(?:u|,)?\s*(\d{1,2})[:.](\d{2})")
_KLJUCNE = re.compile(
    r"vod[aeu]\b|vode\b|vodosnabd|vodovod|kanaliz|ulic|naselj|kvar|radov|potroša",
    re.IGNORECASE)


def _datum(tekst: str) -> datetime | None:
    m = _DATUM_OBJAVE.search(tekst)
    if not m:
        return None
    d, mj, g, h, mi = map(int, m.groups())
    try:
        return datetime(g, mj, d, h, mi)
    except ValueError:
        return None


def _je_objava(href: str) -> bool:
    put = urlsplit(href).path.rstrip("/")
    lista = urlsplit(URL).path.rstrip("/")
    return (urlsplit(href).netloc.endswith("viksa.ba")
            and put.startswith("/objave/") and put != lista
            and not put.endswith("/objave"))


def _napravi(naslov: str, tekst: str, link: str, objavljeno: datetime | None) -> Najava:
    izvedeno = obogati(f"{naslov}. {tekst}", objavljeno)
    return Najava(
        izvor=NAZIV, usluga=USLUGA, naslov=naslov or "Servisna informacija",
        tekst=tekst, link=link,
        objavljeno=objavljeno.isoformat(timespec="minutes") if objavljeno else None,
        **izvedeno)


def parsiraj_objavu(html: str, link: str) -> Najava | None:
    """Jedna pojedinačna objava."""
    s = procitaj(html, link)
    naslov = s.naslovi[0] if s.naslovi else ""
    objavljeno = None
    dijelovi: list[str] = []
    for b in s.blokovi:
        if objavljeno is None and (d := _datum(b)) and len(b) < 60:
            objavljeno = d
            continue
        if b != naslov and _KLJUCNE.search(b) and b not in dijelovi:
            dijelovi.append(b)
    # Blokovi se ugnježđuju (div > p); zadrži samo najdužu verziju istog teksta.
    dijelovi = [b for b in dijelovi if not any(b != o and b in o for o in dijelovi)]
    tekst = "\n".join(dijelovi).strip()
    if not tekst:
        return None
    return _napravi(naslov, tekst, link, objavljeno or _datum(" ".join(s.blokovi)))


def parsiraj_listu(html: str, url: str) -> tuple[list[str], list[Najava]]:
    """Vraća (linkovi na objave, najave pročitane direktno s liste)."""
    s = procitaj(html, url)
    linkovi: list[str] = []
    for href, _ in s.linkovi:
        href = href.split("#")[0]
        if _je_objava(href) and href not in linkovi:
            linkovi.append(href)
    if linkovi:
        return linkovi, []
    # Rezerva: lista bez zasebnih stranica — svaka objava počinje datumom.
    najave: list[Najava] = []
    tekuci: list[str] = []
    datum: datetime | None = None
    for b in s.blokovi + ["01.01.1900 u 00:00"]:
        d = _datum(b)
        if d and len(b) < 60:
            if datum and tekuci:
                tekst = "\n".join(tekuci)
                if _KLJUCNE.search(tekst):
                    najave.append(_napravi(tekuci[0][:120], tekst, url, datum))
            datum, tekuci = d, []
        elif datum:
            tekuci.append(b)
    return [], najave


def prikupi(stranica_liste: int = 2, max_objava: int = 40,
            preuzimac: Preuzimac | None = None) -> list[Najava]:
    p = preuzimac or Preuzimac()
    najave: list[Najava] = []
    linkovi: list[str] = []
    for n in range(1, stranica_liste + 1):
        url = URL if n == 1 else f"{URL}?str={n}"
        l, direktne = parsiraj_listu(p.get(url), url)
        linkovi += [x for x in l if x not in linkovi]
        najave += direktne
    for link in linkovi[:max_objava]:
        try:
            if (n := parsiraj_objavu(p.get(link), link)):
                najave.append(n)
        except IzvorNedostupan:
            continue  # jedna nedostupna objava ne ruši cijeli izvor
    if not najave:
        raise IzvorNedostupan(
            f"{URL}: stranica je učitana, ali nijedna najava nije prepoznata — "
            "vjerovatno je promijenjena struktura stranice, parser treba prilagoditi")
    return najave
