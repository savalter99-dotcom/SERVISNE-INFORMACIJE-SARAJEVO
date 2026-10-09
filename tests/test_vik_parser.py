"""Parser ViK stranice na SINTETIČKOM HTML-u (stvarna stranica nije bila dostupna
iz razvojnog okruženja). Kad stranica postane dostupna, ovdje treba dodati
snimljene stvarne stranice kao fixture."""
import unittest

from servisne.izvori import vik_sarajevo as vik

LISTA = """<html><body><nav><a href="/">Početna</a><a href="/objave">Objave</a></nav>
<div class="lista">
  <div class="objava"><a href="/objave/servisne_informacije/1234-prekid">Prekid u Dobrinji</a><span>13.10.2026 u 08:41</span></div>
  <div class="objava"><a href="https://www.viksa.ba/objave/servisne_informacije/1235-kvar">Kvar na Grbavici</a></div>
  <a href="/objave/servisne_informacije?str=2">Sljedeća</a>
</div><footer><a href="/kontakt">Kontakt</a></footer></body></html>"""

OBJAVA = """<html><body><header><h1>KJKP ViK</h1></header>
<div class="sadrzaj"><h1>Prekid u vodosnabdijevanju</h1><div class="datum">13.10.2026 u 08:41</div>
<div class="tekst"><p>Zbog otklanjanja kvara na vodovodnoj mreži, danas od 09:00 do 15:00 sati
bez vode će biti potrošači u ulicama: Zagrebačka i Grbavička.</p></div></div>
<footer>Sva prava zadržana. Vodovod i kanalizacija.</footer></body></html>"""

LISTA_BEZ_LINKOVA = """<html><body><div>
<div>13.10.2026 u 08:41</div><p>Zbog planiranih radova bez vode je naselje Dobrinja od 9 do 14 sati.</p>
<div>12.10.2026 u 10:00</div><p>Zbog kvara bez vode su potrošači u ulici Bolnička.</p>
</div></body></html>"""


class ParserViK(unittest.TestCase):
    def test_lista_nalazi_linkove_objava(self):
        linkovi, direktne = vik.parsiraj_listu(LISTA, vik.URL)
        self.assertEqual(linkovi, [
            "https://www.viksa.ba/objave/servisne_informacije/1234-prekid",
            "https://www.viksa.ba/objave/servisne_informacije/1235-kvar"])
        self.assertEqual(direktne, [])

    def test_objava(self):
        link = "https://www.viksa.ba/objave/servisne_informacije/1234-prekid"
        n = vik.parsiraj_objavu(OBJAVA, link)
        self.assertEqual(n.naslov, "Prekid u vodosnabdijevanju")
        self.assertEqual(n.objavljeno, "2026-10-13T08:41")
        self.assertEqual(n.ulice, ["Zagrebačka", "Grbavička"])
        self.assertEqual(n.naselja, ["Grbavica"])
        self.assertEqual(n.vrsta, "kvar")
        self.assertEqual((n.prekid_od, n.prekid_do), ("2026-10-13T09:00", "2026-10-13T15:00"))
        self.assertEqual(n.link, link)
        self.assertNotIn("Sva prava", n.tekst)
        self.assertFalse(n.primjer)

    def test_lista_bez_linkova(self):
        linkovi, direktne = vik.parsiraj_listu(LISTA_BEZ_LINKOVA, vik.URL)
        self.assertEqual(linkovi, [])
        self.assertEqual([n.objavljeno for n in direktne], ["2026-10-13T08:41", "2026-10-12T10:00"])
        self.assertTrue(direktne[0].cijelo_naselje)
        self.assertEqual(direktne[1].ulice, ["Bolnička"])


if __name__ == "__main__":
    unittest.main()
