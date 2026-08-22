"""Curated catalogs for the MAKRO explorer.

Variable selection and labels are ported from DREAM's own plotting pipeline
(`Analysis/Templates/variables_to_plot.py` and
`Analysis/Standard_shocks/shocks_to_plot.py` in the MAKRO repo), so the
explorer shows the same headline series DREAM uses in their standard reports.

Conventions:
- `selector` picks a slice of a GDX variable, e.g. ("qBVT", ("tot",)) reads
  qBVT[tot,t]. An empty tuple means the variable is indexed by t only.
- `trend` names the growth/inflation adjustment factor used to convert
  MAKRO's detrended model units into actual levels: "fvt" for values,
  "fqt" for quantities, "fpt" for prices, None for counts and rates.
- `dev_mode` controls how shock deviations from baseline are displayed:
  "pct" = percent deviation (DREAM's "pq"), "pp" = percentage-point
  deviation x100 (DREAM's "pm").
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SeriesDef:
    key: str
    gdx_name: str
    selector: tuple[str, ...]
    label_da: str
    label_en: str
    group: str
    unit_da: str
    trend: str | None
    dev_mode: str


SERIES: list[SeriesDef] = [
    # --- Nationalregnskab ---
    SeriesDef("qBNP", "qBNP", (), "BNP (realt)", "GDP (real)", "Nationalregnskab", "mia. 2020-kr.", "fqt", "pct"),
    SeriesDef("vBNP", "vBNP", (), "BNP (nominelt)", "GDP (nominal)", "Nationalregnskab", "mia. kr.", "fvt", "pct"),
    SeriesDef("qC", "qC", ("cTot",), "Privat forbrug", "Private consumption", "Nationalregnskab", "mia. 2020-kr.", "fqt", "pct"),
    SeriesDef("qG", "qG", ("gTot",), "Offentligt forbrug", "Government consumption", "Nationalregnskab", "mia. 2020-kr.", "fqt", "pct"),
    SeriesDef("qI", "qI", ("iTot",), "Investeringer i alt", "Total investments", "Nationalregnskab", "mia. 2020-kr.", "fqt", "pct"),
    SeriesDef("qIbErhverv", "qIbErhverv", (), "Erhvervsbyggeri", "Commercial building investments", "Nationalregnskab", "mia. 2020-kr.", "fqt", "pct"),
    SeriesDef("qX", "qXy", ("xTot",), "Eksport", "Exports", "Nationalregnskab", "mia. 2020-kr.", "fqt", "pct"),
    SeriesDef("qM", "qM", ("tot",), "Import", "Imports", "Nationalregnskab", "mia. 2020-kr.", "fqt", "pct"),
    SeriesDef("qBVT", "qBVT", ("tot",), "Bruttoværditilvækst (BVT)", "Gross value added", "Nationalregnskab", "mia. 2020-kr.", "fqt", "pct"),

    # --- Arbejdsmarked ---
    SeriesDef("nL", "nL", ("tot",), "Beskæftigelse", "Employment", "Arbejdsmarked", "1.000 personer", None, "pct"),
    SeriesDef("nLsp", "nL", ("spTot",), "Privat beskæftigelse", "Private employment", "Arbejdsmarked", "1.000 personer", None, "pct"),
    SeriesDef("nLoff", "nL", ("off",), "Offentlig beskæftigelse", "Public employment", "Arbejdsmarked", "1.000 personer", None, "pct"),
    SeriesDef("snL", "snL", ("tot",), "Strukturel beskæftigelse", "Structural employment", "Arbejdsmarked", "1.000 personer", None, "pct"),
    SeriesDef("nBruttoLedig", "nBruttoLedig", (), "Bruttoledighed", "Gross unemployment", "Arbejdsmarked", "1.000 personer", None, "pct"),
    SeriesDef("nBruttoArbsty", "nBruttoArbsty", (), "Arbejdsstyrke (brutto)", "Labor force (gross)", "Arbejdsmarked", "1.000 personer", None, "pct"),
    SeriesDef("nPop", "nPop", ("tot",), "Befolkning", "Population", "Arbejdsmarked", "1.000 personer", None, "pct"),

    # --- Priser og løn ---
    SeriesDef("pC", "pC", ("cTot",), "Forbrugerpriser", "Consumer prices", "Priser og løn", "indeks (2020=1)", "fpt", "pct"),
    SeriesDef("pBVT", "pBVT", ("tot",), "BVT-deflator", "GVA deflator", "Priser og løn", "indeks (2020=1)", "fpt", "pct"),
    SeriesDef("pBolig", "pBolig", (), "Boligpriser", "House prices", "Priser og løn", "indeks (2020=1)", "fpt", "pct"),
    SeriesDef("vhW", "vhW_DA", (), "Timeløn (DA-området)", "Hourly wages (DA)", "Priser og løn", "kr. pr. time", "fvt", "pct"),

    # --- Offentlige finanser ---
    SeriesDef("vSaldo", "vSaldo", (), "Offentlig saldo", "Public balance", "Offentlige finanser", "mia. kr.", "fvt", "gdp_pp"),
    SeriesDef("vPrimSaldo", "vPrimSaldo", (), "Primær saldo", "Primary balance", "Offentlige finanser", "mia. kr.", "fvt", "gdp_pp"),
    SeriesDef("vOff13Net", "vOff13Net", (), "Offentlig nettoformue", "Public net financial worth", "Offentlige finanser", "mia. kr.", "fvt", "gdp_pp"),
    SeriesDef("tLukning", "tLukning", (), "Beregningsteknisk lukkeskat", "Fiscal closure tax rate", "Offentlige finanser", "pct.-sats", None, "pp"),

    # --- Renter mv. ---
    SeriesDef("rRenteObl", "rRente", ("Obl",), "Obligationsrente", "Bond interest rate", "Renter", "pct.", None, "pp"),
    SeriesDef("rRenteECB", "rRenteECB", (), "ECB-rente", "ECB policy rate", "Renter", "pct.", None, "pp"),
    SeriesDef("pOlie", "pOlie", (), "Oliepris", "Oil price", "Renter", "indeks", "fpt", "pct"),
]

SECTOR_SERIES_TEMPLATES = [
    ("qBVT", "BVT", "Gross value added", "mia. 2020-kr.", "fqt"),
    ("nL", "Beskæftigelse", "Employment", "1.000 personer", None),
]

SECTORS = ["tje", "fre", "byg", "lan", "soe", "bol", "ene", "udv", "off"]

# Ratio series computed in the ETL from the extracted series above.
# (key, numerator_key, denominator_key, label_da, label_en, group, unit)
RATIOS = [
    ("ledighedsgrad", "nBruttoLedig", "nBruttoArbsty", "Bruttoledighedsgrad", "Unemployment rate", "Arbejdsmarked", "pct. af arbejdsstyrken"),
    ("saldo2bnp", "vSaldo", "vBNP", "Offentlig saldo, andel af BNP", "Public balance, share of GDP", "Offentlige finanser", "pct. af BNP"),
    ("primsaldo2bnp", "vPrimSaldo", "vBNP", "Primær saldo, andel af BNP", "Primary balance, share of GDP", "Offentlige finanser", "pct. af BNP"),
    ("nettoformue2bnp", "vOff13Net", "vBNP", "Offentlig nettoformue, andel af BNP", "Public net worth, share of GDP", "Offentlige finanser", "pct. af BNP"),
]


# Display scaling applied to baseline levels (not deviations): rates -> pct., wages -> kr.
DISPLAY_SCALE = {"rRenteObl": 100, "rRenteECB": 100, "tLukning": 100, "vhW": 1000}


@dataclass(frozen=True)
class ShockDef:
    name: str  # gdx file stem used by Analysis/Standard_shocks
    label_da: str
    label_en: str
    group: str


SHOCKS: list[ShockDef] = [
    ShockDef("Offentligt_forbrug", "Offentligt forbrug", "Government consumption", "Offentlige udgifter"),
    ShockDef("Offentlig_varekoeb", "Offentlige varekøb", "Government purchases", "Offentlige udgifter"),
    ShockDef("Offentlig_Beskaeftigelse", "Offentlig beskæftigelse", "Government employment", "Offentlige udgifter"),
    ShockDef("Offentlig_loen", "Offentlig løn", "Government wages", "Offentlige udgifter"),
    ShockDef("Offentlige_investeringer", "Offentlige investeringer", "Public investments", "Offentlige udgifter"),
    ShockDef("Skattepligtig_indkomstoverforsel", "Skattepligtige overførsler", "Taxable transfers", "Offentlige udgifter"),
    ShockDef("Ikke_skattepligtig_indkomstoverforsel", "Ikke-skattepligtige overførsler", "Non-taxable transfers", "Offentlige udgifter"),
    ShockDef("Overforsel_privat", "Øvrige overførsler til husholdninger", "Other transfers to households", "Offentlige udgifter"),
    ShockDef("Bundskat", "Bundskat", "Income tax (bundskat)", "Skatter og afgifter"),
    ShockDef("AM_bidrag", "AM-bidrag", "Labor market contribution", "Skatter og afgifter"),
    ShockDef("Grundskyld", "Grundskyld", "Land tax", "Skatter og afgifter"),
    ShockDef("Ejendomsvaerdiskat", "Ejendomsværdiskat", "Property value tax", "Skatter og afgifter"),
    ShockDef("Vaegtafgift", "Vægtafgift", "Vehicle excise duty", "Skatter og afgifter"),
    ShockDef("Selskabsskat", "Selskabsskat", "Corporate income tax", "Skatter og afgifter"),
    ShockDef("Aktieskat", "Aktieskat", "Dividend/capital gains tax", "Skatter og afgifter"),
    ShockDef("Moms", "Moms", "VAT", "Skatter og afgifter"),
    ShockDef("Registreringsafgift", "Registreringsafgift", "Vehicle registration tax", "Skatter og afgifter"),
    ShockDef("Energiafgift", "Energiafgift", "Household energy taxes", "Skatter og afgifter"),
    ShockDef("Forbrugsafgift", "Øvrige forbrugsafgifter", "Other consumption taxes", "Skatter og afgifter"),
    ShockDef("Afgift_erhverv", "Afgifter på erhvervs materialeinput", "Duties on intermediate goods", "Skatter og afgifter"),
    ShockDef("Produktsubsidier", "Produktsubsidier", "Product subsidies", "Subsidier"),
    ShockDef("Lontilskud", "Løntilskud", "Wage subsidies", "Subsidier"),
    ShockDef("Produktionssubsidier", "Produktionssubsidier", "Production subsidies", "Subsidier"),
    ShockDef("Eksportmarkedsvaekst", "Eksportmarkedsvækst", "Export market growth", "Udland"),
    ShockDef("Importpris", "Importpriser", "Import prices", "Udland"),
    ShockDef("Eksportkonkurrerende_priser", "Eksportkonkurrerende priser", "Export-competing prices", "Udland"),
    ShockDef("Oliepris", "Oliepris", "Oil price", "Udland"),
    ShockDef("Udenlandske_priser", "Udenlandske priser", "Foreign prices", "Udland"),
    ShockDef("Rente", "Rente (ECB)", "Interest rate (ECB)", "Udland"),
    ShockDef("Arbejdsudbud_beskaeftigelse", "Arbejdsudbud (beskæftigelse)", "Labor supply (employment)", "Udbud og struktur"),
    ShockDef("Arbejdsudbud - timer", "Arbejdsudbud (timer)", "Labor supply (hours)", "Udbud og struktur"),
    ShockDef("Befolkning", "Befolkning", "Population", "Udbud og struktur"),
    ShockDef("KapitalProd", "Kapitalproduktivitet", "Capital productivity", "Udbud og struktur"),
    ShockDef("ArbejdsProd", "Arbejdskraftproduktivitet", "Labor productivity", "Udbud og struktur"),
    ShockDef("VirkDisk", "Virksomhedernes hurdle rates", "Firm hurdle rates", "Risikopræmier"),
    ShockDef("BoligRisiko", "Risikopræmie på bolig", "Housing risk premium", "Risikopræmier"),
    ShockDef("AktieAfkast", "Hurdle rates og aktieafkast", "Hurdle rates and equity returns", "Risikopræmier"),
    ShockDef("RisikoPraemier", "Alle risikopræmier", "All risk premia", "Risikopræmier"),
    ShockDef("Diskontering", "Husholdningernes diskontering", "Household discounting", "Præferencer"),
    ShockDef("Loen", "Lønmodtagernes forhandlingsstyrke", "Wage bargaining power", "Præferencer"),
]

VARIATIONS = [
    ("_blip", "1-årigt stød", "One-year blip"),
    ("_midl", "Midlertidigt (AR-profil)", "Transitory (AR profile)"),
    ("_perm", "Permanent, finansieret", "Permanent, financed"),
    ("_ufin", "Permanent, ufinansieret", "Permanent, unfinanced"),
]
