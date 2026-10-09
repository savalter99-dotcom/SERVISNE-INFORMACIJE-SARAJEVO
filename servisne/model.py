"""Zajednički izlazni format svih izvora."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field

VRSTE = ("planirani radovi", "kvar", "redukcija", "ostalo")


@dataclass
class Najava:
    izvor: str                      # npr. "ViK Sarajevo"
    usluga: str                     # voda / struja / plin / grijanje
    naslov: str
    tekst: str                      # originalni tekst najave
    link: str                       # link na originalnu objavu
    objavljeno: str | None = None   # ISO datum i vrijeme objave
    prekid_od: str | None = None    # ISO datum/vrijeme početka prekida
    prekid_do: str | None = None    # ISO datum/vrijeme kraja (None = do završetka radova)
    vrsta: str = "ostalo"           # jedna od VRSTE
    opcine: list[str] = field(default_factory=list)
    naselja: list[str] = field(default_factory=list)
    ulice: list[str] = field(default_factory=list)
    cijelo_naselje: bool = False    # najava navodi naselje bez ulica
    primjer: bool = False           # True = izmišljeni PRIMJER, ne stvarni podatak

    @property
    def id(self) -> str:
        kljuc = f"{self.izvor}|{self.link}|{self.naslov}|{self.objavljeno}"
        return hashlib.sha1(kljuc.encode("utf-8")).hexdigest()[:16]

    def u_rjecnik(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        return d
