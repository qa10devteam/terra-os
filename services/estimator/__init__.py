"""M3 — Estimator: two-variant cost estimation engine.

Variant A (doc): Wk = Σ(Lj × Cj) — simplified calc per Rozp. MRiT 20.12.2021
Variant B (owner): Cj = Σ(n×c) + Kpj + Zj — detailed RMS from rate_card

ALL computation is deterministic, local, never sent to cloud.
Owner rate_card data NEVER leaves the local system.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

logger = logging.getLogger(__name__)

# Rounding policy: 2 decimal places, ROUND_HALF_UP (consistent with Polish accounting)
_ROUND = Decimal("0.01")


def _r(v: Decimal) -> Decimal:
    """Round to 2 decimal places per Polish accounting convention."""
    return v.quantize(_ROUND, rounding=ROUND_HALF_UP)


# ──────────────────────────────────────────────────────────────── #
# Data models
# ──────────────────────────────────────────────────────────────── #

@dataclass
class RateCard:
    """Owner's rate card — RMS rates + overhead + profit.

    This data NEVER leaves the local system. Assert in tests.
    """
    robocizna_zl_rg: Decimal = Decimal("35.00")  # stawka robocizny [zł/r-g]
    kp_pct: Decimal = Decimal("12.0")            # koszty pośrednie % od (R+S)
    zysk_pct: Decimal = Decimal("8.0")           # zysk % od (R+S+Kp)
    kz_pct: Decimal = Decimal("7.0")             # koszty zakupu % od M
    calibration_coeff: Decimal = Decimal("1.00") # multiplier from learning loop

    # Equipment rates [zł/m-g]
    sprzet_rates: dict[str, Decimal] = field(default_factory=lambda: {
        "koparka_0.6": Decimal("180.00"),
        "koparka_0.4": Decimal("150.00"),
        "spycharka_75kW": Decimal("160.00"),
        "walec_8t": Decimal("140.00"),
        "samochod_10t": Decimal("120.00"),
        "zagęszczarka": Decimal("45.00"),
    })


@dataclass
class MarketPriceBase:
    """Market price base (SEKOCENBUD BRZ equivalent) for Variant A.

    Maps KNR codes → unit prices (Cj) from published data.
    """
    prices: dict[str, Decimal] = field(default_factory=lambda: {
        # KNR 2-01 — roboty ziemne
        "KNR 2-01 0211-03": Decimal("22.50"),  # Wykop kop. 0.4m³ kat.III transp 1km [zł/m³]
        "KNR 2-01 0307-02": Decimal("18.00"),  # Nasyp z gruntu kat.II zagęszcz. [zł/m³]
        "KNR 2-01 0510-01": Decimal("28.00"),  # Transport urobku do 5km [zł/m³]
        "KNR 2-01 0405-04": Decimal("6.50"),   # Zagęszczenie walcem 8t [zł/m²]
        "KNR 2-01 0804-01": Decimal("15.00"),  # Humusowanie skarp [zł/m²]
        # KNR 2-31 — roboty drogowe
        "KNR 2-31 0108-01": Decimal("45.00"),  # Podbudowa kruszywo 20cm [zł/m²]
        "KNR 2-31 0403-02": Decimal("55.00"),  # Nawierzchnia AC16W 5cm [zł/m²]
    })

    # Fallback: if KNR not found, use unit-based defaults
    unit_defaults: dict[str, Decimal] = field(default_factory=lambda: {
        "m3": Decimal("25.00"),
        "m2": Decimal("20.00"),
        "mb": Decimal("30.00"),
        "t": Decimal("50.00"),
        "szt": Decimal("100.00"),
    })

    def get_price(self, knr_code: str | None, unit: str) -> Decimal:
        """Get unit price for a KNR code or fallback to unit default."""
        if knr_code:
            normalized = knr_code.strip()
            if normalized in self.prices:
                return self.prices[normalized]
        return self.unit_defaults.get(unit, Decimal("20.00"))


@dataclass
class KNRNorm:
    """Nakłady rzeczowe from KNR catalog for a single position."""
    robocizna_rg: Decimal = Decimal("0.35")     # r-g / j.m.
    material_zl: Decimal = Decimal("5.00")      # zł / j.m. (materiały bezpośrednie)
    sprzet_mg: Decimal = Decimal("0.12")        # m-g / j.m.
    sprzet_type: str = "koparka_0.6"


# Default KNR norms for earthworks
_DEFAULT_NORMS: dict[str, KNRNorm] = {
    "KNR 2-01 0211-03": KNRNorm(robocizna_rg=Decimal("0.18"), material_zl=Decimal("0.50"), sprzet_mg=Decimal("0.015"), sprzet_type="koparka_0.6"),
    "KNR 2-01 0307-02": KNRNorm(robocizna_rg=Decimal("0.25"), material_zl=Decimal("2.00"), sprzet_mg=Decimal("0.012"), sprzet_type="spycharka_75kW"),
    "KNR 2-01 0510-01": KNRNorm(robocizna_rg=Decimal("0.05"), material_zl=Decimal("0.00"), sprzet_mg=Decimal("0.020"), sprzet_type="samochod_10t"),
    "KNR 2-01 0405-04": KNRNorm(robocizna_rg=Decimal("0.02"), material_zl=Decimal("0.00"), sprzet_mg=Decimal("0.006"), sprzet_type="walec_8t"),
    "KNR 2-01 0804-01": KNRNorm(robocizna_rg=Decimal("0.15"), material_zl=Decimal("3.50"), sprzet_mg=Decimal("0.008"), sprzet_type="spycharka_75kW"),
    "KNR 2-31 0108-01": KNRNorm(robocizna_rg=Decimal("0.10"), material_zl=Decimal("28.00"), sprzet_mg=Decimal("0.010"), sprzet_type="walec_8t"),
    "KNR 2-31 0403-02": KNRNorm(robocizna_rg=Decimal("0.08"), material_zl=Decimal("35.00"), sprzet_mg=Decimal("0.012"), sprzet_type="walec_8t"),
}


# ──────────────────────────────────────────────────────────────── #
# Estimate line
# ──────────────────────────────────────────────────────────────── #

@dataclass
class EstimateLine:
    """Single line in an estimate."""
    position_no: str
    description: str
    unit: str
    quantity: Decimal
    unit_price: Decimal = Decimal("0")
    labor_pln: Decimal = Decimal("0")
    material_pln: Decimal = Decimal("0")
    equipment_pln: Decimal = Decimal("0")
    line_total_pln: Decimal = Decimal("0")
    knr_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_no": self.position_no,
            "description": self.description,
            "unit": self.unit,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "labor_pln": str(self.labor_pln),
            "material_pln": str(self.material_pln),
            "equipment_pln": str(self.equipment_pln),
            "line_total_pln": str(self.line_total_pln),
            "knr_code": self.knr_code,
        }


@dataclass
class Estimate:
    """Complete estimate (one variant)."""
    variant: str  # "A" or "B"
    lines: list[EstimateLine] = field(default_factory=list)
    total_net_pln: Decimal = Decimal("0")
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": self.variant,
            "lines": [l.to_dict() for l in self.lines],
            "total_net_pln": str(self.total_net_pln),
            "params": self.params,
        }


@dataclass
class CompareResult:
    """Comparison between Variant A and B."""
    doc_total: Decimal
    owner_total: Decimal
    delta_pln: Decimal
    margin_headroom_pct: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_total": str(self.doc_total),
            "owner_total": str(self.owner_total),
            "delta_pln": str(self.delta_pln),
            "margin_headroom_pct": str(self.margin_headroom_pct),
        }


# ──────────────────────────────────────────────────────────────── #
# Variant A: Wk = Σ(Lj × Cj) — market price base
# ──────────────────────────────────────────────────────────────── #

def compute_variant_a(
    przedmiar_items: list[dict[str, Any]],
    *,
    price_base: MarketPriceBase | None = None,
) -> Estimate:
    """Variant A (doc): simplified calc Wk = Σ(Lj × Cj).

    Uses SEKOCENBUD-like market prices mapped from KNR codes.
    """
    pb = price_base or MarketPriceBase()
    lines: list[EstimateLine] = []

    for item in przedmiar_items:
        qty = Decimal(str(item.get("quantity", 0)))
        knr = item.get("knr_code")
        unit = item.get("unit", "m3")
        cj = pb.get_price(knr, unit)
        line_total = _r(qty * cj)

        lines.append(EstimateLine(
            position_no=item.get("position_no", ""),
            description=item.get("description", ""),
            unit=unit,
            quantity=qty,
            unit_price=cj,
            line_total_pln=line_total,
            knr_code=knr,
        ))

    total = sum((l.line_total_pln for l in lines), Decimal("0"))

    return Estimate(
        variant="A",
        lines=lines,
        total_net_pln=_r(total),
        params={"method": "Wk=Σ(Lj×Cj)", "price_base": "SEKOCENBUD BRZ Q3/2025"},
    )


# ──────────────────────────────────────────────────────────────── #
# Variant B: Cj = Σ(n×c) + Kpj + Zj — owner rate card
# ──────────────────────────────────────────────────────────────── #

def compute_variant_b(
    przedmiar_items: list[dict[str, Any]],
    *,
    rate_card: RateCard | None = None,
) -> Estimate:
    """Variant B (owner): detailed calc Cj = Σ(n×c) + Kpj + Zj.

    Uses owner's rate_card (RMS rates + overhead + profit).
    ALL computation is local and deterministic.
    """
    rc = rate_card or RateCard()
    lines: list[EstimateLine] = []

    for item in przedmiar_items:
        qty = Decimal(str(item.get("quantity", 0)))
        knr = item.get("knr_code")
        unit = item.get("unit", "m3")

        # Get KNR norms
        norm = _DEFAULT_NORMS.get(knr.strip() if knr else "", KNRNorm())

        # Koszty bezpośrednie na jednostkę
        r_unit = _r(norm.robocizna_rg * rc.robocizna_zl_rg)  # R na j.m.
        m_unit = norm.material_zl                              # M na j.m.
        sprzet_rate = rc.sprzet_rates.get(norm.sprzet_type, Decimal("150.00"))
        s_unit = _r(norm.sprzet_mg * sprzet_rate)             # S na j.m.

        # KB na j.m. = R + M + S
        kb_unit = r_unit + m_unit + s_unit

        # Koszty pośrednie: Kp = Wkp% × (R + S) / 100
        kp_unit = _r((r_unit + s_unit) * rc.kp_pct / Decimal("100"))

        # Zysk: Z = WZ% × (R + S + Kp) / 100
        z_unit = _r((r_unit + s_unit + kp_unit) * rc.zysk_pct / Decimal("100"))

        # Koszty zakupu: Kz = WKz% × M / 100
        kz_unit = _r(m_unit * rc.kz_pct / Decimal("100"))

        # Cj = KB + Kp + Z + Kz
        cj = kb_unit + kp_unit + z_unit + kz_unit

        # Apply calibration coefficient
        cj_calibrated = _r(cj * rc.calibration_coeff)

        # Line total
        line_total = _r(qty * cj_calibrated)
        labor_total = _r(qty * r_unit)
        material_total = _r(qty * (m_unit + kz_unit))
        equipment_total = _r(qty * s_unit)

        lines.append(EstimateLine(
            position_no=item.get("position_no", ""),
            description=item.get("description", ""),
            unit=unit,
            quantity=qty,
            unit_price=cj_calibrated,
            labor_pln=labor_total,
            material_pln=material_total,
            equipment_pln=equipment_total,
            line_total_pln=line_total,
            knr_code=knr,
        ))

    total = sum((l.line_total_pln for l in lines), Decimal("0"))

    return Estimate(
        variant="B",
        lines=lines,
        total_net_pln=_r(total),
        params={
            "method": "Cj=Σ(n×c)+Kp+Z",
            "robocizna_zl_rg": str(rc.robocizna_zl_rg),
            "kp_pct": str(rc.kp_pct),
            "zysk_pct": str(rc.zysk_pct),
            "calibration_coeff": str(rc.calibration_coeff),
        },
    )


# ──────────────────────────────────────────────────────────────── #
# Compare
# ──────────────────────────────────────────────────────────────── #

def compare_estimates(a: Estimate, b: Estimate) -> CompareResult:
    """Compare Variant A (doc) and B (owner).

    margin_headroom_pct = (A_total - B_total) / A_total × 100
    Positive = owner cheaper than market → profit margin.
    """
    delta = _r(a.total_net_pln - b.total_net_pln)
    if a.total_net_pln > 0:
        headroom = _r(delta * Decimal("100") / a.total_net_pln)
    else:
        headroom = Decimal("0.00")

    return CompareResult(
        doc_total=a.total_net_pln,
        owner_total=b.total_net_pln,
        delta_pln=delta,
        margin_headroom_pct=headroom,
    )


# ──────────────────────────────────────────────────────────────── #
# Sum reconciliation (acceptance test utility)
# ──────────────────────────────────────────────────────────────── #

def verify_sum_reconciliation(estimate: Estimate) -> bool:
    """Verify that sum of line_totals == total_net_pln exactly. Zero tolerance."""
    sum_lines = sum((l.line_total_pln for l in estimate.lines), Decimal("0"))
    return sum_lines == estimate.total_net_pln
