"""Pomoćne stvari zajedničke svim izvorima: pristojno preuzimanje i čitanje HTML-a."""
from __future__ import annotations

import socket
import ssl
import time
import urllib.error
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

USER_AGENT = "ServisneInformacijeSarajevo/0.1 (javne najave; jedan zahtjev svakih nekoliko sekundi)"
RAZMAK_SEKUNDI = 3.0
TIMEOUT = 20


class IzvorNedostupan(Exception):
    """Izvor se ne može pročitati (mreža, blokada, promijenjena stranica...)."""


class Preuzimac:
    """HTTP GET s poštovanjem robots.txt i razmakom između zahtjeva."""

    def __init__(self, razmak: float = RAZMAK_SEKUNDI):
        self.razmak = razmak
        self._zadnji = 0.0
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def _dozvoljeno(self, url: str) -> bool:
        dijelovi = urlsplit(url)
        baza = f"{dijelovi.scheme}://{dijelovi.netloc}"
        if baza not in self._robots:
            rp = urllib.robotparser.RobotFileParser(baza + "/robots.txt")
            try:
                rp.parse(self._get(baza + "/robots.txt").splitlines())
            except IzvorNedostupan:
                rp = None  # nema robots.txt ili nije dostupan -> nema zabrana
            self._robots[baza] = rp
        rp = self._robots[baza]
        return rp is None or rp.can_fetch(USER_AGENT, url)

    def _get(self, url: str) -> str:
        cekaj = self.razmak - (time.monotonic() - self._zadnji)
        if cekaj > 0:
            time.sleep(cekaj)
        self._zadnji = time.monotonic()
        zahtjev = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT, "Accept-Language": "bs,hr,sr;q=0.9"})
        try:
            with urllib.request.urlopen(zahtjev, timeout=TIMEOUT) as odg:
                kodiranje = odg.headers.get_content_charset() or "utf-8"
                return odg.read().decode(kodiranje, errors="replace")
        except urllib.error.HTTPError as e:
            raise IzvorNedostupan(f"{url}: server je vratio HTTP {e.code}") from e
        except urllib.error.URLError as e:
            razlog = e.reason
            if isinstance(razlog, socket.gaierror):
                poruka = "naziv domene se ne može razriješiti (DNS) — mreža je blokirana ili domena ne postoji"
            elif isinstance(razlog, ssl.SSLError):
                poruka = f"TLS greška: {razlog}"
            elif "403" in str(razlog) or "Tunnel" in str(razlog):
                poruka = f"proxy/mrežna politika odbija vezu ({razlog})"
            else:
                poruka = str(razlog)
            raise IzvorNedostupan(f"{url}: {poruka}") from e
        except (TimeoutError, socket.timeout) as e:
            raise IzvorNedostupan(f"{url}: isteklo vrijeme čekanja ({TIMEOUT} s)") from e
        except OSError as e:
            raise IzvorNedostupan(f"{url}: {e}") from e

    def get(self, url: str) -> str:
        if not self._dozvoljeno(url):
            raise IzvorNedostupan(f"{url}: robots.txt ne dozvoljava preuzimanje")
        return self._get(url)


class TekstHTML(HTMLParser):
    """Iz HTML-a vadi linkove, naslove (h1-h3) i blokove teksta, bez menija i skripti."""

    _PRESKOCI = {"script", "style", "noscript", "nav", "header", "footer", "form", "svg"}
    _BLOK = {"p", "div", "li", "h1", "h2", "h3", "h4", "article", "section", "br", "tr", "td", "span"}

    def __init__(self, baza: str = ""):
        super().__init__(convert_charrefs=True)
        self.baza = baza
        self.linkovi: list[tuple[str, str]] = []  # (apsolutni href, tekst)
        self.naslovi: list[str] = []
        self.blokovi: list[str] = []
        self._preskoci = 0
        self._link: list | None = None
        self._naslov: list[str] | None = None
        self._tekuci: list[str] = []

    def _zatvori_blok(self):
        t = " ".join("".join(self._tekuci).split())
        if t:
            self.blokovi.append(t)
        self._tekuci = []

    def handle_starttag(self, tag, attrs):
        if tag in self._PRESKOCI:
            self._preskoci += 1
            return
        if self._preskoci:
            return
        if tag in self._BLOK and tag != "span":
            self._zatvori_blok()
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._link = [urljoin(self.baza, href), []]
        if tag in ("h1", "h2", "h3"):
            self._naslov = []

    def handle_endtag(self, tag):
        if tag in self._PRESKOCI:
            self._preskoci = max(0, self._preskoci - 1)
            return
        if self._preskoci:
            return
        if tag == "a" and self._link:
            self.linkovi.append((self._link[0], " ".join("".join(self._link[1]).split())))
            self._link = None
        if tag in ("h1", "h2", "h3") and self._naslov is not None:
            n = " ".join("".join(self._naslov).split())
            if n:
                self.naslovi.append(n)
            self._naslov = None
        if tag in self._BLOK and tag != "span":
            self._zatvori_blok()

    def handle_data(self, data):
        if self._preskoci:
            return
        self._tekuci.append(data)
        if self._link is not None:
            self._link[1].append(data)
        if self._naslov is not None:
            self._naslov.append(data)

    def close(self):
        super().close()
        self._zatvori_blok()


def procitaj(html: str, baza: str = "") -> TekstHTML:
    p = TekstHTML(baza)
    p.feed(html)
    p.close()
    return p
