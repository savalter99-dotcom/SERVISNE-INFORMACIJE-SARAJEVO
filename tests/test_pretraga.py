"""Pretraga sa i bez kvačica, velika/mala slova, padeži, "cijelo naselje".

Isti slučajevi se provjeravaju i za JavaScript verziju (web/app.js) preko Node-a.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from servisne.normalizacija import normaliziraj, odgovara
from servisne.pretraga import pretrazi

APP_JS = Path(__file__).resolve().parent.parent / "web" / "app.js"


def najava(naslov, naselja=(), ulice=(), tekst=""):
    return {"naslov": naslov, "naselja": list(naselja), "ulice": list(ulice),
            "cijelo_naselje": bool(naselja) and not ulice, "tekst": tekst or naslov}


NAJAVE = [
    najava("A", naselja=["Dobrinja"]),
    najava("B", naselja=["Grbavica"], ulice=["Zagrebačka", "Zmaja od Bosne"]),
    najava("C", naselja=["Koševo"], ulice=["Bolnička"]),
    najava("D", naselja=["Hrasno Brdo"]),
    najava("E", tekst="Kvar na cjevovodu kod Đulagine kafane"),
]
ULICE_NASELJA = {"Trg solidarnosti": ["Dobrinja"], "Bolnička": ["Koševo"]}

# (upit, očekivani naslovi s razlogom)
SLUCAJEVI = [
    ("Dobrinja", {"A": "cijelo naselje"}),
    ("dobrinja", {"A": "cijelo naselje"}),
    ("DOBRINJA", {"A": "cijelo naselje"}),
    ("u Dobrinji", {"A": "cijelo naselje"}),
    ("dobrinji", {"A": "cijelo naselje"}),
    ("Trg solidarnosti", {"A": "cijelo naselje"}),   # ulica u naselju koje je cijelo bez vode
    ("trg solidarnosti 12", {}),                     # broj nije u nazivu ulice
    ("Zagrebačka", {"B": "ulica"}),
    ("zagrebacka", {"B": "ulica"}),
    ("u Zagrebačkoj ulici", {"B": "ulica"}),
    ("zmaja od bosne", {"B": "ulica"}),
    ("Kosevo", {"C": "naselje"}),
    ("na Koševu", {"C": "naselje"}),
    ("bolnicka", {"C": "ulica"}),
    ("hrasnom brdu", {"D": "cijelo naselje"}),
    ("dulagin", {"E": "tekst"}),
    ("đulagine", {"E": "tekst"}),
    ("djulagine", {"E": "tekst"}),
    ("Otoka", {}),
]


class Normalizacija(unittest.TestCase):
    def test_kvacice(self):
        self.assertEqual(normaliziraj("ČĆŠŽĐ čćšžđ"), "ccszd ccszd")
        self.assertEqual(normaliziraj("  Alipašino   Polje! "), "alipasino polje")

    def test_odgovara(self):
        self.assertTrue(odgovara("u Dobrinji", "Dobrinja"))
        self.assertTrue(odgovara("dobr", "Dobrinja"))       # djelimično kucanje
        self.assertFalse(odgovara("Dobrinja", "Grbavica"))
        self.assertFalse(odgovara("u", "Dobrinja"))         # samo stop-riječ


class PretragaPython(unittest.TestCase):
    def test_slucajevi(self):
        for upit, ocekivano in SLUCAJEVI:
            with self.subTest(upit=upit):
                rez = {n["naslov"]: r for n, r in pretrazi(NAJAVE, upit, ULICE_NASELJA)}
                self.assertEqual(rez, ocekivano)

    def test_prazan_upit_vraca_sve(self):
        self.assertEqual(len(pretrazi(NAJAVE, "  ")), len(NAJAVE))


@unittest.skipUnless(shutil.which("node"), "Node nije instaliran")
class PretragaJavaScript(unittest.TestCase):
    def test_isti_rezultati_kao_python(self):
        skripta = f"""
        const a = require({json.dumps(str(APP_JS))});
        const najave = {json.dumps(NAJAVE)};
        const un = {json.dumps(ULICE_NASELJA)};
        const upiti = {json.dumps([u for u, _ in SLUCAJEVI])};
        const rez = upiti.map(u => Object.fromEntries(a.pretrazi(najave, u, un).map(x => [x.najava.naslov, x.razlog])));
        console.log(JSON.stringify({{rez, norm: a.normaliziraj("ČĆŠŽĐ čćšžđ")}}));
        """
        izlaz = json.loads(subprocess.run(["node", "-e", skripta], capture_output=True,
                                          text=True, check=True).stdout)
        self.assertEqual(izlaz["norm"], "ccszd ccszd")
        for (upit, ocekivano), dobijeno in zip(SLUCAJEVI, izlaz["rez"]):
            with self.subTest(upit=upit):
                self.assertEqual(dobijeno, ocekivano)


if __name__ == "__main__":
    unittest.main()
