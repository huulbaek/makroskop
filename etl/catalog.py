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
    ShockDef("Arbejdsudbud_timer", "Arbejdsudbud (timer)", "Labor supply (hours)", "Udbud og struktur"),
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


@dataclass(frozen=True)
class ShockRun:
    """How MAKROskop's free solver actually implements a catalog shock.

    Mirrors the `solve-export` calls in cloud/run.sh and cloud/run_batch2.sh: the
    exogenous `instrument` is set to `level * factor + delta` in every year of the
    shock window and the model is re-solved. `dream_da` states how this differs
    from DREAM's own standard shock of the same name (Analysis/Standard_shocks).
    """
    shock: str            # catalog name (ShockDef.name)
    instrument: str       # exogenous model variable
    instrument_da: str    # the model's own label for it
    factor: float
    delta: float
    change_da: str        # the change in words, e.g. "+1 pct.-point"
    first_year: int
    dream_da: str
    series_key: str | None = None  # SERIES key of the instrument, if it is a catalog series
    linearity_da: str | None = None  # measured nonlinearity (nonlinearity.py), if known


_DREAM_GDP_NORM = (
    "DREAMs standardstød af samme navn normerer i stedet ændringen til 1 pct. af BNP i provenu "
    "(og sænker satsen); MAKROskop ændrer selve satsen med et fast beløb. Størrelserne er derfor "
    "ikke direkte sammenlignelige."
)

SHOCK_RUNS: list[ShockRun] = [
    ShockRun("Rente", "rRenteECB", "ECB-renten", 1.0, 0.01, "+1 pct.-point (100 basispoint)", 2030,
             "Samme instrument, størrelse og stødår (2030) som DREAMs standardstød \"Rente\" "
             "(rRenteECB + 0,01). "
             "Alle danske renter i MAKRO er bygget oven på ECB-renten (obligations-, bank- og "
             "virksomhedernes afkastkrav), så gennemslaget er 1:1; udenlandske priser er uændrede, "
             "så det er reelt en permanent højere realrente.",
             series_key="rRenteECB",
             linearity_da="Målt på et 10-års udsnit: ved 64 pct. af stødet afviger modellen 1,1 pct. "
                          "(median) fra lineær skalering; BNP 0,8 pct., beskæftigelse 0,9 pct., "
                          "boligpriser 1,8 pct., enkelte branche-serier op til 6 pct. af effekten."),
    ShockRun("Oliepris", "pOlieBrent", "Prisnotering på råolie, Brent", 1.10, 0.0, "+10 pct.", 2030,
             "Samme instrument og størrelse som DREAMs standardstød. I kalibrerings-konfigurationen "
             "driver Brent-prisen kun oliepris-indekset pOlie, mens de import- og energipriser, det "
             "skulle slå igennem på, er faste datainput — så stødet bider næsten ikke. Brug "
             "\"Udenlandske priser\" eller \"Importpriser\" for et prisstød, der virker.",
             series_key="pOlie"),
    ShockRun("Udenlandske_priser", "pM, pXUdl", "Importpriser (alle varegrupper) og eksportkonkurrerende priser",
             1.01, 0.0, "+1 pct.", 2030,
             "Samme bundt og størrelse som DREAMs standardstød \"Udenlandske_priser\": alle eksogene "
             "importpriser pM[s] og udenlandske konkurrentpriser pXUdl[x] hæves 1 pct.; aggregaterne "
             "er endogene og følger med."),
    ShockRun("Importpris", "pM", "Importpriser (alle varegrupper)", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrument og størrelse som DREAMs standardstød \"Importpris\"."),
    ShockRun("Eksportkonkurrerende_priser", "pXUdl", "Udenlandske konkurrentpriser på eksportmarkederne",
             1.01, 0.0, "+1 pct.", 2030,
             "Samme instrument og størrelse som DREAMs standardstød \"Eksportkonkurrerende_priser\"."),
    ShockRun("Bundskat", "tBund", "Bundskattesats", 1.0, 0.01, "+1 pct.-point", 2030, _DREAM_GDP_NORM),
    ShockRun("AM_bidrag", "tAMbidrag", "Arbejdsmarkedsbidrag, sats", 1.0, 0.01, "+1 pct.-point", 2030, _DREAM_GDP_NORM),
    ShockRun("Selskabsskat", "tSelskab", "Selskabsskattesats", 1.0, 0.01, "+1 pct.-point", 2030, _DREAM_GDP_NORM),
    ShockRun("Ejendomsvaerdiskat", "tEjd", "Ejendomsværdiskat, implicit sats", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM),
    ShockRun("Offentligt_forbrug", "qR(off,*),qE(off,*),hL(off,*),qI_s(!iTot,off,*)",
             "Offentlig sektors input: varekøb, energi, arbejdstimer og investeringer", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrumenter som DREAMs standardstød (den offentlige produktions eksogene input); "
             "DREAM normerer ændringen til 1 pct. af BNP, MAKROskop hæver alle input med 1 pct."),
    ShockRun("Skattepligtig_indkomstoverforsel", "uvOvfSats(!boernyd|boligyd|iskatpl|groen|lumpsumovf,*)",
             "Satser for skattepligtige overførsler (ekskl. de ubeskattede ydelser)", 1.01, 0.0, "+1 pct.", 2030,
             "Samme afgrænsning som DREAMs standardstød (kun skattepligtige ydelser); DREAM normerer "
             "ændringen til 1 pct. af BNP, MAKROskop hæver satserne med 1 pct."),
    ShockRun("Eksportmarkedsvaekst", "uXMarked", "Eksportmarkedets størrelse", 1.01, 0.0, "+1 pct.", 2030,
             "DREAMs standardstød normerer ændringen til 1 pct. af BNP i eksport; MAKROskop hæver "
             "eksportmarkedet med 1 pct."),
    ShockRun("Befolkning", "nPop", "Befolkning, alle aldersgrupper", 1.01, 0.0, "+1 pct.", 2030,
             "Samme størrelse som DREAMs standardstød, men DREAM skalerer desuden offentligt forbrug og "
             "arbejdsstyrke med; MAKROskop ændrer kun befolkningen.",
             series_key="nPop"),
    # --- batch 3: the rest of DREAM's standard shocks (Analysis/Standard_shocks/standard_shocks.gms),
    # instruments translated 1:1 where the DREAM instrument is exogenous here; where DREAM swaps
    # endogeneity, the exogenous parameter behind it is moved instead (stated in dream_da).
    ShockRun("Offentlig_varekoeb", "qR(off,*)", "Offentligt varekøb (materialer)", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrument som DREAMs standardstød; DREAM normerer til 1 pct. af BNP, MAKROskop hæver varekøbet med 1 pct."),
    ShockRun("Offentlig_Beskaeftigelse", "hL(off,*)", "Offentlige arbejdstimer", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrument som DREAMs standardstød; DREAM normerer til 1 pct. af BNP i lønsum, MAKROskop hæver timerne med 1 pct."),
    ShockRun("Offentlige_investeringer", "qI_s(!iTot,off,*)", "Offentlige investeringer (maskiner og bygninger)", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrument som DREAMs standardstød; DREAM normerer til 1 pct. af BNP, MAKROskop hæver investeringerne med 1 pct."),
    ShockRun("Offentlig_loen", "qProd(off,*)", "Lønbestemmende produktivitet i den offentlige sektor", 1.01, 0.0, "+1 pct.", 2030,
             "DREAM hæver samme variabel (normeret til 1 pct. af BNP) og korrigerer desuden to aggregerede "
             "produktivitetsparametre; MAKROskop udelader korrektionen."),
    ShockRun("Ikke_skattepligtig_indkomstoverforsel", "uvOvfSats(boernyd|boligyd|iskatpl|groen|lumpsumovf,*)",
             "Satser for ikke-skattepligtige overførsler", 1.01, 0.0, "+1 pct.", 2030,
             "Samme afgrænsning som DREAMs standardstød (de ubeskattede ydelser); DREAM normerer til 1 pct. af BNP."),
    ShockRun("Overforsel_privat", "vOffTilHhRest", "Øvrige offentlige overførsler til husholdninger", 1.0, 10.0, "+10 mia. kr. årligt", 2030,
             "Samme instrument som DREAMs standardstød (lump sum); DREAM giver 1 pct. af BNP, MAKROskop 10 mia. kr."),
    ShockRun("Grundskyld", "tGrund", "Grundskyldspromille, alle brancher", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM),
    ShockRun("Vaegtafgift", "utHhVaegt", "Vægtafgift, implicit sats", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM),
    ShockRun("Aktieskat", "tAktieTop", "Aktieindkomstskat, topsats", 1.0, 0.01, "+1 pct.-point", 2030,
             "DREAM ændrer både top- og lavsatsen normeret til 1 pct. af BNP; i denne konfiguration er kun topsatsen en variabel."),
    ShockRun("Moms", "tMoms_y,tMoms_m", "Momssatser (indenlandsk og importeret)", 1.0, 0.005, "+0,5 pct.-point", 2030,
             _DREAM_GDP_NORM + " Stødet er halveret i forhold til de øvrige satsstød: ved ca. 0,9 pct.-point rammer "
             "de 18-åriges ejerboligbeholdning omkring 2110 nul, og modellen har ingen håndtering af den grænse."),
    ShockRun("Registreringsafgift", "tReg_y,tReg_m", "Registreringsafgift, implicitte satser", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM),
    ShockRun("Energiafgift", "tAfg_y(cEne,*,*),tAfg_m(cEne,*,*)", "Energiafgifter på privat forbrug", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM),
    ShockRun("Forbrugsafgift", "tAfg_y(cVar,*,*),tAfg_m(cVar,*,*)", "Øvrige afgifter på privat vareforbrug", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM),
    ShockRun("Afgift_erhverv", "tAfg_y(bol|byg|ene|fre|lan|off|soe|tje|udv,!off,*),tAfg_m(bol|byg|ene|fre|lan|off|soe|tje|udv,!off,*)",
             "Afgifter på private erhvervs materialeinput", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM),
    ShockRun("Produktsubsidier", "rSub_y,rSub_m", "Produktsubsidiesatser", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM),
    ShockRun("Lontilskud", "rSubLoen(!tot,*)", "Løntilskudssatser", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM),
    ShockRun("Produktionssubsidier", "rSubYRest(!tot,*)", "Øvrige produktionssubsidier, sats", 1.10, 0.0, "+10 pct. af satsen", 2030,
             "DREAM hæver subsidiebeløbet (1 pct. af BNP) og endogeniserer satsen; MAKROskop hæver satsen direkte."),
    ShockRun("Arbejdsudbud_beskaeftigelse", "uDeltag", "Erhvervsdeltagelse, alle aldre", 1.01, 0.0, "+1 pct.", 2030,
             "DREAM hæver den strukturelle beskæftigelse med 1 pct. og endogeniserer deltagelsesparameteren; "
             "MAKROskop hæver deltagelsesparameteren direkte med 1 pct."),
    ShockRun("Arbejdsudbud_timer", "uh", "Arbejdstid pr. beskæftiget, alle aldre", 1.01, 0.0, "+1 pct.", 2030,
             "DREAM hæver de strukturelle timer med 1 pct. og endogeniserer timeparameteren; "
             "MAKROskop hæver timeparameteren direkte med 1 pct."),
    ShockRun("ArbejdsProd", "qProdHh_t,qProdxDK", "Arbejdskraftproduktivitet (trend)", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrumenter og størrelse som DREAMs standardstød."),
    ShockRun("VirkDisk", "rVirkDiskPrem(!spTot,*)", "Virksomhedernes risikopræmie (hurdle rate)", 1.0, 0.001, "+0,1 pct.-point", 2030,
             "Samme instrument og størrelse som DREAMs standardstød."),
    ShockRun("BoligRisiko", "rBoligPrem", "Risikopræmie i boligernes usercost", 1.0, 0.001, "+0,1 pct.-point", 2030,
             "Samme instrument og størrelse som DREAMs standardstød."),
    ShockRun("AktieAfkast", "rVirkDiskPrem(!spTot,*),rAktieDriftPrem", "Risikopræmie på virksomheder og aktieafkast", 1.0, 0.001, "+0,1 pct.-point", 2030,
             "Samme instrumenter og størrelse som DREAMs standardstød."),
    ShockRun("RisikoPraemier", "rVirkDiskPrem(!spTot,*),rAktieDriftPrem,rBoligPrem", "Alle tre risikopræmier", 1.0, 0.001, "+0,1 pct.-point", 2030,
             "Samme instrumenter og størrelse som DREAMs standardstød."),
    ShockRun("Diskontering", "jfDisk_t", "Husholdningernes diskonteringsfaktor (justering)", 1.0, -0.001, "−0,001", 2030,
             "Samme instrument og størrelse som DREAMs standardstød."),
    ShockRun("Loen", "rLoenNash", "Lønmodtagernes forhandlingsstyrke", 1.0, -0.01, "−1 pct.-point", 2030,
             "Samme instrument og størrelse som DREAMs standardstød."),
]

_UNFINANCED = (
    "Ufinansieret: ingen skattesats reagerer. Virkningen på de offentlige finanser akkumulerer "
    "derfor over tid og er ikke et holdbart forløb."
)
_UNFINANCED_TEMP = (
    "Ufinansieret: ingen skattesats reagerer. (DREAMs tilsvarende variant er finansieret via "
    "den beregningstekniske lukkeskat — det kan den frie løser ikke endnu.)"
)

# Profiles follow Analysis/Standard_shocks/standard_shocks.gms: dt = år siden stødåret.
VARIATION_DEFINITIONS: dict[str, dict[str, str]] = {
    "_blip": {"profile_da": "Ét år: stødet gælder kun i stødåret (DREAMs blip_profile).",
              "closure_da": _UNFINANCED_TEMP},
    "_midl": {"profile_da": "Midlertidigt: fuldt stød i stødåret, derefter 0,9 pr. år "
                            "(100, 90, 81, 73 pct. … — DREAMs AR_profile, Finansministeriets "
                            "multiplikator-standard).",
              "closure_da": _UNFINANCED_TEMP},
    "_perm": {"profile_da": "Permanent: stødet gælder alle år fra stødåret og horisonten ud.",
              "closure_da": "Finansieret: den beregningstekniske lukkeskat justeres, så de offentlige "
                            "finanser forbliver holdbare."},
    "_ufin": {"profile_da": "Permanent: stødet gælder alle år fra stødåret og horisonten ud.",
              "closure_da": _UNFINANCED},
}

# solve-export --shock-profile value that produces each variation.
VARIATION_PROFILES: dict[str, str] = {"_blip": "blip", "_midl": "ar", "_perm": "permanent", "_ufin": "permanent"}


def shock_definition(shock_name: str, suffix: str, last_year: int) -> dict | None:
    """Definition block written into a scenario JSON, or None if the run is not catalogued."""
    run = next((r for r in SHOCK_RUNS if r.shock == shock_name), None)
    variation = VARIATION_DEFINITIONS.get(suffix)
    if run is None or variation is None:
        return None
    return {
        "instrument": run.instrument,
        "instrumentDa": run.instrument_da,
        "changeDa": run.change_da,
        "factor": run.factor,
        "delta": run.delta,
        "firstYear": run.first_year,
        "lastYear": last_year,
        "profileDa": variation["profile_da"],
        "closureDa": variation["closure_da"],
        "dreamDa": run.dream_da,
        "seriesKey": run.series_key,
        "solver": "MAKROskops frie løser (Newton, fuld horisont)",
        "linearityDa": run.linearity_da or "Lineariteten er ikke målt for dette stød endnu.",
    }


def etl_gdx_symbols() -> set[str]:
    """GDX symbols the ETL reads for shock deviations — the minimum a compact export needs."""
    names = {sdef.gdx_name for sdef in SERIES}
    names |= {template[0] for template in SECTOR_SERIES_TEMPLATES}
    names.add("rHBI")
    return names
