"""Izvori najava. Svaki izvor je jedan modul s:

    ID: str             kratki identifikator ("vik")
    NAZIV: str          ime za prikaz ("ViK Sarajevo")
    USLUGA: str         voda / struja / plin / grijanje
    URL: str            zvanična stranica s najavama
    def prikupi(**opcije) -> list[Najava]   # baca IzvorNedostupan ako ne može

Novi izvor (Elektrodistribucija, Sarajevogas, Toplane): dodaj modul i upiši ga u IZVORI.
"""
from . import vik_sarajevo
from .zajednicko import IzvorNedostupan

IZVORI = [vik_sarajevo]

__all__ = ["IZVORI", "IzvorNedostupan"]
