"""Izvlačenje ulica, naselja, općina, vrste i termina iz teksta najave."""
import unittest
from datetime import datetime

from servisne.izvlacenje import (izvuci_naselja, izvuci_ulice, izvuci_vrijeme,
                                 obogati, odredi_vrstu)

OBJAVA = datetime(2026, 10, 13, 8, 41)


class Ulice(unittest.TestCase):
    def test_popis_iza_dvotacke(self):
        t = "Bez vode će biti potrošači u ulicama: Urijan Dedina, Cicin Han, Stolačka i Zmaja od Bosne."
        self.assertEqual(izvuci_ulice(t), ["Urijan Dedina", "Cicin Han", "Stolačka", "Zmaja od Bosne"])

    def test_dio_ulice_i_kucni_brojevi(self):
        t = "Bez vode je dio ulice Zmaja od Bosne br. 10-24 i ulica Kranjčevićeva 5."
        self.assertEqual(izvuci_ulice(t), ["Zmaja od Bosne", "Kranjčevićeva"])

    def test_ulica_s_brojem_u_imenu(self):
        self.assertEqual(izvuci_ulice("u ulici 1. maja od 9 do 12 sati"), ["1. maja"])

    def test_skracenica_ul(self):
        self.assertEqual(izvuci_ulice("Radovi u ul. Bolnička, od 08:00 sati."), ["Bolnička"])

    def test_popis_staje_kod_termina(self):
        t = "u ulicama Zagrebačka i Grbavička od 08:00 do 14:00 sati zbog kvara"
        self.assertEqual(izvuci_ulice(t), ["Zagrebačka", "Grbavička"])

    def test_obicna_rijec_ulica_nije_ulica(self):
        self.assertEqual(izvuci_ulice("ulica će biti zatvorena za saobraćaj"), [])

    def test_samo_naselje_bez_ulice(self):
        self.assertEqual(izvuci_ulice("Bez vode je naselje Dobrinja."), [])


class Naselja(unittest.TestCase):
    def test_padezi(self):
        self.assertEqual(izvuci_naselja("bez vode su potrošači u Dobrinji"), ["Dobrinja"])
        self.assertEqual(izvuci_naselja("na Alipašinom Polju"), ["Alipašino Polje"])
        self.assertEqual(izvuci_naselja("u Hrasnom Brdu i na Vratniku"), ["Hrasno Brdo", "Vratnik"])

    def test_bez_kvacica(self):
        self.assertEqual(izvuci_naselja("u naselju Sokolovic Kolonija i na Kosevu"),
                         ["Sokolović Kolonija", "Koševo"])

    def test_duze_ime_ima_prednost(self):
        self.assertEqual(izvuci_naselja("Hrasno Brdo"), ["Hrasno Brdo"])

    def test_naselje_koje_nije_u_gazeteru(self):
        self.assertIn("Zlatište", izvuci_naselja("Bez vode je naselje Zlatište."))

    def test_samo_naselje_je_cijelo_naselje(self):
        r = obogati("Zbog radova bez vode će biti naselje Dobrinja.", OBJAVA)
        self.assertEqual(r["naselja"], ["Dobrinja"])
        self.assertEqual(r["ulice"], [])
        self.assertTrue(r["cijelo_naselje"])
        self.assertEqual(r["opcine"], ["Novi Grad"])

    def test_ulica_dodaje_naselje_iz_gazetera(self):
        r = obogati("Bez vode su ulice Bolnička i Bardakčije.", OBJAVA)
        self.assertEqual(r["naselja"], ["Koševo"])
        self.assertEqual(r["opcine"], ["Centar"])
        self.assertFalse(r["cijelo_naselje"])


class VrijemeIVrsta(unittest.TestCase):
    def test_datum_i_interval(self):
        self.assertEqual(izvuci_vrijeme("dana 14.10.2026. od 08:00 do 14:00 sati", OBJAVA),
                         ("2026-10-14T08:00", "2026-10-14T14:00"))

    def test_sati_bez_minuta_i_zarez(self):
        self.assertEqual(izvuci_vrijeme("sutra od 8 do 14 sati", OBJAVA),
                         ("2026-10-14T08:00", "2026-10-14T14:00"))
        self.assertEqual(izvuci_vrijeme("danas od 22,00 do 05,00 sati", OBJAVA),
                         ("2026-10-13T22:00", "2026-10-14T05:00"))

    def test_bez_kraja(self):
        self.assertEqual(izvuci_vrijeme("danas od 09:30 do završetka radova", OBJAVA),
                         ("2026-10-13T09:30", None))

    def test_vrste(self):
        self.assertEqual(odredi_vrstu("zbog otklanjanja kvara na mreži"), "kvar")
        self.assertEqual(odredi_vrstu("zbog planiranih radova na zamjeni cijevi"), "planirani radovi")
        self.assertEqual(odredi_vrstu("noćna redukcija vode"), "redukcija")
        self.assertEqual(odredi_vrstu("obavještenje potrošačima"), "ostalo")


if __name__ == "__main__":
    unittest.main()
