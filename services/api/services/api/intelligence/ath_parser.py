"""ATH XML Parser — import/export formatu Norma PRO.

ATH = Audyt Techniczno-Historyczny / format XML Normy PRO.
Struktura:
  <Kosztorys>
    <Pozycja KodKat="KNR 2-02 0101-01" Opis="..." Jm="m2" Ilosc="100">
      <R Nazwa="Robocizna" Jm="r-g" Norma="0.24" Cena="52.09"/>
      <M Nazwa="Cegła" Jm="szt" Norma="50" Cena="2.5"/>
      <S Nazwa="Rusztowanie" Jm="m-g" Norma="0.05" Cena="35.0"/>
    </Pozycja>
  </Kosztorys>
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AthSkladnik:
    typ:       str        # R | M | S
    nazwa:     str
    jednostka: str
    norma:     float
    cena:      float


@dataclass
class AthPozycja:
    kst_code:  str
    opis:      str
    jednostka: str
    ilosc:     float
    skladniki: list[AthSkladnik] = field(default_factory=list)

    def r_jcena(self) -> float:
        """Suma cen robocizny [zł/jm pozycji]."""
        return sum(s.norma * s.cena for s in self.skladniki if s.typ == "R")

    def m_jcena(self) -> float:
        return sum(s.norma * s.cena for s in self.skladniki if s.typ == "M")

    def s_jcena(self) -> float:
        return sum(s.norma * s.cena for s in self.skladniki if s.typ == "S")


@dataclass
class AthKosztorys:
    nazwa:   str = ""
    wersja:  str = "2.0"
    pozycje: list[AthPozycja] = field(default_factory=list)


# ─── Parser ───────────────────────────────────────────────────────────────────

def parse_ath(content: bytes | str) -> AthKosztorys:
    """Parsuj ATH XML → AthKosztorys.

    Obsługuje:
    - Klasyczny format Norma PRO (Pozycja/R/M/S z atrybutami)
    - Wariant z elementami zagnieżdżonymi (Norma PRO 4.x)
    - Wariant uproszczony (tylko CenaJm bez składników)
    """
    if isinstance(content, str):
        content = content.encode("utf-8")

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise ValueError(f"Nieprawidłowy XML ATH: {e}")

    ath = AthKosztorys(
        nazwa=root.get("Nazwa", ""),
        wersja=root.get("wersja", "2.0"),
    )

    # Iteruj po elementach — szukaj Pozycja (lub ath:Pozycja, Pos, Item)
    for elem in root.iter():
        tag = _strip_ns(elem.tag)
        if tag.lower() not in ("pozycja", "pos", "item", "position", "ath_row"):
            continue

        kst  = elem.get("KodKat") or elem.get("Kod") or elem.get("kod") or ""
        opis = (elem.get("Opis") or elem.get("opis") or
                elem.findtext("Opis") or elem.findtext("Nazwa") or tag)
        jm   = elem.get("Jm") or elem.get("jm") or elem.findtext("Jm") or "szt"
        ilosc = _float(elem.get("Ilosc") or elem.get("ilosc") or
                        elem.findtext("Ilosc") or "1")

        pozycja = AthPozycja(kst_code=kst, opis=opis, jednostka=jm, ilosc=ilosc)

        # Składniki R/M/S jako child elements
        for child in elem:
            child_tag = _strip_ns(child.tag).upper()
            if child_tag in ("R", "M", "S"):
                s = AthSkladnik(
                    typ=child_tag,
                    nazwa=child.get("Nazwa") or child.get("nazwa") or child_tag,
                    jednostka=child.get("Jm") or child.get("jm") or "szt",
                    norma=_float(child.get("Norma") or child.get("norma") or "0"),
                    cena=_float(child.get("Cena") or child.get("cena") or
                                child.get("CenaNetto") or "0"),
                )
                pozycja.skladniki.append(s)

        # Fallback: jeśli brak składników, a jest CenaJm → jeden składnik M
        if not pozycja.skladniki:
            cena_jm = _float(elem.get("CenaJm") or elem.get("cena") or
                              elem.findtext("CenaJm") or "0")
            if cena_jm > 0:
                pozycja.skladniki.append(AthSkladnik(
                    typ="M", nazwa=opis, jednostka=jm, norma=1.0, cena=cena_jm,
                ))

        ath.pozycje.append(pozycja)

    return ath


# ─── Generator ────────────────────────────────────────────────────────────────

def generate_ath(
    pozycje: list[dict],
    nazwa: str = "Kosztorys Terra-OS",
) -> bytes:
    """Generuj ATH XML z listy dict pozycji.

    Każda pozycja: {kst_code, opis, jednostka, ilosc, skladniki: [{typ, nazwa, jednostka, norma, cena}]}
    lub uproszczona: {kst_code, opis, jednostka, ilosc, r_jcena, m_jcena, s_jcena}
    """
    root = ET.Element("Kosztorys")
    root.set("xmlns:ath", "http://norma.com.pl/ath/2.0")
    root.set("wersja", "2.0")
    root.set("Nazwa", nazwa)

    for poz in pozycje:
        pos_el = ET.SubElement(root, "Pozycja")
        pos_el.set("KodKat", str(poz.get("kst_code") or poz.get("opis", "")[:20]))
        pos_el.set("Opis",   str(poz.get("opis") or poz.get("description") or ""))
        pos_el.set("Jm",     str(poz.get("jednostka") or poz.get("unit") or "szt"))
        pos_el.set("Ilosc",  str(poz.get("ilosc") or poz.get("quantity") or 1))

        skladniki = poz.get("skladniki", [])
        if not skladniki:
            # Fallback z r/m/s_jcena
            for typ, key in [("R", "r_jcena"), ("M", "m_jcena"), ("S", "s_jcena")]:
                val = float(poz.get(key) or 0)
                if val > 0:
                    el = ET.SubElement(pos_el, typ)
                    el.set("Nazwa", {"R": "Robocizna", "M": "Materiały", "S": "Sprzęt"}[typ])
                    el.set("Jm", {"R": "r-g", "M": "jm", "S": "m-g"}[typ])
                    el.set("Norma", "1")
                    el.set("Cena", str(round(val, 4)))
        else:
            for sk in skladniki:
                el = ET.SubElement(pos_el, sk.get("typ", "M").upper())
                el.set("Nazwa",    str(sk.get("nazwa", "")))
                el.set("Jm",       str(sk.get("jednostka", "szt")))
                el.set("Norma",    str(sk.get("norma", 1)))
                el.set("Cena",     str(round(float(sk.get("cena", 0)), 4)))

    return ET.tostring(root, encoding="unicode", xml_declaration=False).encode("utf-8")


def ath_to_pozycje_dicts(ath: AthKosztorys) -> list[dict]:
    """Konwertuj AthKosztorys → lista dict gotowych do INSERT do kosztorys_pozycja."""
    result = []
    for i, poz in enumerate(ath.pozycje, start=1):
        # Rozłóż kod katalogowy: "KNR 2-02 0101-01" → katalog="KNR 2-02", nr="0101-01"
        parts = poz.kst_code.rsplit(" ", 1) if poz.kst_code else ["", ""]
        katalog = parts[0] if len(parts) > 1 else poz.kst_code
        nr = parts[1] if len(parts) > 1 else ""

        result.append({
            "lp":         i,
            "kst_code":   poz.kst_code,
            "katalog":    katalog,
            "pozycja_nr": nr,
            "opis":       poz.opis,
            "jednostka":  poz.jednostka,
            "ilosc":      poz.ilosc,
            "r_jcena":    round(poz.r_jcena(), 4),
            "m_jcena":    round(poz.m_jcena(), 4),
            "s_jcena":    round(poz.s_jcena(), 4),
            "skladniki":  [
                {
                    "typ": s.typ,
                    "nazwa": s.nazwa,
                    "jednostka": s.jednostka,
                    "norma": s.norma,
                    "cena_netto": s.cena,
                }
                for s in poz.skladniki
            ],
            "ath_pozycja_xml": ET.tostring(
                _build_pozycja_el(poz), encoding="unicode"
            ),
        })

    return result


def _build_pozycja_el(poz: AthPozycja) -> ET.Element:
    el = ET.Element("Pozycja")
    el.set("KodKat", poz.kst_code)
    el.set("Opis", poz.opis)
    el.set("Jm", poz.jednostka)
    el.set("Ilosc", str(poz.ilosc))
    for s in poz.skladniki:
        child = ET.SubElement(el, s.typ)
        child.set("Nazwa", s.nazwa)
        child.set("Jm", s.jednostka)
        child.set("Norma", str(s.norma))
        child.set("Cena", str(s.cena))
    return el


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _float(val: Any, default: float = 0.0) -> float:
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return default
