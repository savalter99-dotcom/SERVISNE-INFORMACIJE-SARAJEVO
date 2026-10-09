# Servisne informacije Sarajevo

Najave prekida i radova (voda, a kasnije struja, plin, grijanje) na jednom mjestu,
s pretragom po naselju i ulici. **Korak 1:** jedan izvor — ViK Sarajevo
(<https://www.viksa.ba/objave/servisne_informacije>).

## Pokretanje u 5 koraka

1. **Pripremi Python 3.12** (nema vanjskih biblioteka, sve je iz standardne biblioteke):
   ```bash
   python3.12 --version
   ```
2. **Pokreni testove** (izvlačenje ulica/naselja, pretraga bez kvačica i padeži; JS verzija pretrage se provjerava preko Node-a ako je instaliran):
   ```bash
   python3.12 -m unittest discover -s tests -t .
   ```
3. **Prikupi najave** — čita zvaničnu stranicu (poštuje robots.txt, 3 s razmaka između zahtjeva), sprema u `data/najave.sqlite` i izvozi `web/najave.json`:
   ```bash
   python3.12 -m servisne            # samo stvarni podaci
   python3.12 -m servisne --primjeri # ako izvor nije dostupan, ubaci jasno označene PRIMJERE
   ```
   Izlazni kod 0 = ima stvarnih najava, 2 = nijedan izvor nije bio dostupan.
4. **Pokreni stranicu:**
   ```bash
   cd web && python3.12 -m http.server 8000
   ```
   i otvori <http://localhost:8000>.
5. **Osvježavaj redovno** — npr. cron svakih 30 minuta:
   ```
   */30 * * * * cd /putanja/do/projekta && python3.12 -m servisne
   ```
   Čim stigne stvarni podatak, PRIMJERI se automatski brišu.

## Struktura

```
servisne/
  izvori/            jedan modul po izvoru, isti izlazni format (Najava)
    vik_sarajevo.py  ViK Sarajevo
    zajednicko.py    pristojno preuzimanje (robots.txt, razmak), čitanje HTML-a
  model.py           Najava: izvor, datum objave, prekid od–do, vrsta, općine, naselja, ulice, tekst, link
  izvlacenje.py      ulice, naselja, općine, termin i vrsta iz slobodnog teksta
  normalizacija.py   bez kvačica, mala slova, padeži (ista logika u web/app.js)
  pretraga.py        referentna pretraga (ista logika u web/app.js)
  baza.py            SQLite + izvoz u najave.json
data/gazeter.json    naselja po općinama + poznate ulice → naselje (dopunjava se)
web/                 statična stranica (HTML/CSS/JS bez frameworka)
tests/
```

**Novi izvor** (Elektrodistribucija, Sarajevogas, Toplane): napravi `servisne/izvori/<ime>.py`
s `ID`, `NAZIV`, `USLUGA`, `URL` i `prikupi() -> list[Najava]`, i dodaj ga u `IZVORI`
u `servisne/izvori/__init__.py`.

**Pretraga:** "Dobrinja", "dobrinja", "u Dobrinji" i "DOBRINJI" daju isto; "Kosevo" nalazi
"Koševo"; Đ se može kucati kao đ, dj ili d. Ako najava navodi samo naselje, prikazuje se i
onome ko traži ulicu u tom naselju (oznaka "cijelo naselje") — veza ulica → naselje dolazi
iz `data/gazeter.json` i iz najava koje navode i ulicu i naselje.

**Napomena:** Mjerodavni su isključivo zvanični izvori. Parser ViK stranice napisan je bez
pristupa stvarnoj stranici (bila je blokirana iz razvojnog okruženja) i testiran na
sintetičkom HTML-u — pri prvom stvarnom pokretanju provjeri rezultat i po potrebi ga prilagodi.
