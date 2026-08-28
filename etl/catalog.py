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
    # Largest |scale| the UI may offer. Set it where the model itself has a boundary the
    # solver could not cross, so the slider cannot extrapolate past a point we know has
    # no solution. None = the UI default.
    max_scale: float | None = None
    max_scale_da: str | None = None  # why the cap is there, shown next to the slider
    explainer_da: str | None = None  # 2-3 plain-language sentences on the mechanism, for readers


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
             explainer_da="En varigt højere ECB-rente slår 1:1 igennem på alle danske renter. Dyrere lån rammer "
                          "først boligmarkedet — boligpriserne falder omkring 6 pct. — og dernæst forbrug og "
                          "investeringer, så BNP ligger 1–1,5 pct. lavere. Beskæftigelsen falder kun det første "
                          "år: lønnen tilpasser sig, og ledigheden vender tilbage til sit strukturelle niveau.",
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
             "er endogene og følger med.",
             explainer_da="Højere import- og konkurrentpriser gør dansk produktion relativt billigere, så eksport "
                          "og BNP løftes på kort sigt. Over nogle år stiger danske priser og lønninger tilsvarende "
                          "(ca. 1 pct.), og den reale effekt forsvinder: resultatet er et varigt højere prisniveau, "
                          "ikke en varig aktivitetsgevinst."),
    ShockRun("Importpris", "pM", "Importpriser (alle varegrupper)", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrument og størrelse som DREAMs standardstød \"Importpris\".",
             explainer_da="Dyrere import hæver forbrugerpriserne og forringer bytteforholdet: realindkomst og forbrug falder, og BNP ligger gradvist op til 0,4 pct. lavere."),
    ShockRun("Eksportkonkurrerende_priser", "pXUdl", "Udenlandske konkurrentpriser på eksportmarkederne",
             1.01, 0.0, "+1 pct.", 2030,
             "Samme instrument og størrelse som DREAMs standardstød \"Eksportkonkurrerende_priser\".",
             explainer_da="Højere udenlandske konkurrentpriser giver dansk eksport markedsandele: eksporten stiger knap 1 pct. og BNP ca. 0,3 pct., mens danske lønninger og priser trækkes op."),
    ShockRun("Bundskat", "tBund", "Bundskattesats", 1.0, 0.01, "+1 pct.-point", 2030, _DREAM_GDP_NORM,
             explainer_da="En højere bundskat tager af husholdningernes disponible indkomst: det private forbrug "
                          "falder godt 1 pct., og boligpriserne følger med ned. BNP ender knap 0,2 pct. lavere, mens "
                          "den offentlige saldo forbedres år for år. Beskæftigelsen påvirkes kun lidt, fordi "
                          "arbejdsudbuddet i MAKRO er strukturelt bestemt og kun reagerer svagt på skattesatsen."),
    ShockRun("AM_bidrag", "tAMbidrag", "Arbejdsmarkedsbidrag, sats", 1.0, 0.01, "+1 pct.-point", 2030, _DREAM_GDP_NORM,
             explainer_da="Et højere arbejdsmarkedsbidrag virker som bundskatten: lavere disponibel indkomst, forbruget falder knap 1 pct., og boligpriserne følger med. BNP ligger ca. 0,1 pct. lavere, saldoen forbedres."),
    ShockRun("Selskabsskat", "tSelskab", "Selskabsskattesats", 1.0, 0.01, "+1 pct.-point", 2030, _DREAM_GDP_NORM,
             explainer_da="Højere selskabsskat gør investeringer dyrere: investeringerne falder ca. 0,2 pct. og BNP knap 0,1 pct. på langt sigt, mens saldoen forbedres."),
    ShockRun("Ejendomsvaerdiskat", "tEjd", "Ejendomsværdiskat, implicit sats", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM,
             explainer_da="Højere ejendomsværdiskat sænker boligpriserne ca. 0,3 pct. og forbruget lidt; BNP-effekten er lille, saldoen forbedres."),
    ShockRun("Offentligt_forbrug", "qR(off,*),qE(off,*),hL(off,*),qI_s(!iTot,off,*)",
             "Offentlig sektors input: varekøb, energi, arbejdstimer og investeringer", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrumenter som DREAMs standardstød (den offentlige produktions eksogene input); "
             "DREAM normerer ændringen til 1 pct. af BNP, MAKROskop hæver alle input med 1 pct.",
             explainer_da="Mere offentligt forbrug løfter aktivitet og beskæftigelse det første år (BNP +0,1 pct.), "
                          "men effekten klinger hurtigt af: lønninger og priser stiger og fortrænger privat "
                          "aktivitet, så BNP-virkningen er omkring nul efter få år. Fordi udgiften ikke er "
                          "finansieret, vokser underskuddet på de offentlige finanser år for år."),
    ShockRun("Skattepligtig_indkomstoverforsel", "uvOvfSats(!boernyd|boligyd|iskatpl|groen|lumpsumovf,*)",
             "Satser for skattepligtige overførsler (ekskl. de ubeskattede ydelser)", 1.01, 0.0, "+1 pct.", 2030,
             "Samme afgrænsning som DREAMs standardstød (kun skattepligtige ydelser); DREAM normerer "
             "ændringen til 1 pct. af BNP, MAKROskop hæver satserne med 1 pct.",
             explainer_da="1 pct. højere skattepligtige overførsler løfter forbruget ca. 0,2 pct. og boligpriserne lidt; BNP-effekten er lille, og saldoen svækkes."),
    ShockRun("Eksportmarkedsvaekst", "uXMarked", "Eksportmarkedets størrelse", 1.01, 0.0, "+1 pct.", 2030,
             "DREAMs standardstød normerer ændringen til 1 pct. af BNP i eksport; MAKROskop hæver "
             "eksportmarkedet med 1 pct.",
             explainer_da="Et 1 pct. større eksportmarked løfter eksporten ca. 0,5 pct. og BNP ca. 0,1 pct.; beskæftigelsen stiger kun kortvarigt, og lønnen tager en del af gevinsten."),
    ShockRun("Befolkning", "nPop", "Befolkning, alle aldersgrupper", 1.01, 0.0, "+1 pct.", 2030,
             "Samme størrelse som DREAMs standardstød, men DREAM skalerer desuden offentligt forbrug og "
             "arbejdsstyrke med; MAKROskop ændrer kun befolkningen.",
             series_key="nPop",
             explainer_da="Flere mennesker giver flere beskæftigede (+1 pct.) og på sigt 1 pct. højere BNP. På kort sigt springer bolig- og andre investeringer op for at følge med den større befolkning."),
    # --- batch 3: the rest of DREAM's standard shocks (Analysis/Standard_shocks/standard_shocks.gms),
    # instruments translated 1:1 where the DREAM instrument is exogenous here; where DREAM swaps
    # endogeneity, the exogenous parameter behind it is moved instead (stated in dream_da).
    ShockRun("Offentlig_varekoeb", "qR(off,*)", "Offentligt varekøb (materialer)", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrument som DREAMs standardstød; DREAM normerer til 1 pct. af BNP, MAKROskop hæver varekøbet med 1 pct.",
             explainer_da="Mere offentligt varekøb giver et lille, kortvarigt løft i aktiviteten, som hurtigt fortrænges; saldoen svækkes, fordi udgiften ikke er finansieret."),
    ShockRun("Offentlig_Beskaeftigelse", "hL(off,*)", "Offentlige arbejdstimer", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrument som DREAMs standardstød; DREAM normerer til 1 pct. af BNP i lønsum, MAKROskop hæver timerne med 1 pct.",
             explainer_da="Flere offentlige arbejdstimer løfter beskæftigelsen det første år, men trækker derefter arbejdskraft fra den private sektor: eksport og investeringer falder, og BNP ender lidt lavere. Udgiften er ufinansieret, så saldoen svækkes."),
    ShockRun("Offentlige_investeringer", "qI_s(!iTot,off,*)", "Offentlige investeringer (maskiner og bygninger)", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrument som DREAMs standardstød; DREAM normerer til 1 pct. af BNP, MAKROskop hæver investeringerne med 1 pct.",
             explainer_da="Højere offentlige investeringer løfter de samlede investeringer ca. 0,15 pct. og BNP marginalt; saldoen svækkes, fordi udgiften ikke er finansieret."),
    ShockRun("Offentlig_loen", "qProd(off,*)", "Lønbestemmende produktivitet i den offentlige sektor", 1.01, 0.0, "+1 pct.", 2030,
             "DREAM hæver samme variabel (normeret til 1 pct. af BNP) og korrigerer desuden to aggregerede "
             "produktivitetsparametre; MAKROskop udelader korrektionen.",
             explainer_da="Højere offentlig løn smitter af på lønnen i hele økonomien: eksport og private investeringer taber konkurrenceevne, og BNP ender ca. 0,2 pct. lavere. Saldoen svækkes."),
    ShockRun("Ikke_skattepligtig_indkomstoverforsel", "uvOvfSats(boernyd|boligyd|iskatpl|groen|lumpsumovf,*)",
             "Satser for ikke-skattepligtige overførsler", 1.01, 0.0, "+1 pct.", 2030,
             "Samme afgrænsning som DREAMs standardstød (de ubeskattede ydelser); DREAM normerer til 1 pct. af BNP.",
             explainer_da="1 pct. højere ubeskattede ydelser er et lille beløb: forbruget stiger marginalt, saldoen svækkes tilsvarende, og beskæftigelsen er upåvirket."),
    ShockRun("Overforsel_privat", "vOffTilHhRest", "Øvrige offentlige overførsler til husholdninger", 1.0, 10.0, "+10 mia. kr. årligt", 2030,
             "Samme instrument som DREAMs standardstød (lump sum); DREAM giver 1 pct. af BNP, MAKROskop 10 mia. kr.",
             explainer_da="10 mia. kr. mere i overførsler går næsten fuldt ud i privat forbrug (+0,7 pct.) og boligpriser; BNP løftes ca. 0,1 pct., mens saldoen svækkes med det meste af beløbet."),
    ShockRun("Grundskyld", "tGrund", "Grundskyldspromille, alle brancher", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM,
             explainer_da="Højere grundskyld kapitaliseres i lavere bolig- og jordpriser (ca. −0,3 pct.), hvilket dæmper forbrug og investeringer lidt; saldoen forbedres."),
    ShockRun("Vaegtafgift", "utHhVaegt", "Vægtafgift, implicit sats", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM,
             explainer_da="Højere vægtafgift sænker forbruget marginalt (ca. −0,05 pct.); BNP-effekten er ubetydelig, og saldoen forbedres lidt."),
    ShockRun("Aktieskat", "tAktieTop", "Aktieindkomstskat, topsats", 1.0, 0.01, "+1 pct.-point", 2030,
             "DREAM ændrer både top- og lavsatsen normeret til 1 pct. af BNP; i denne konfiguration er kun topsatsen en variabel.",
             explainer_da="En højere topsats på aktieindkomst har næsten ingen realøkonomisk virkning i MAKRO; provenuet forbedrer saldoen marginalt, og forbruget falder først på langt sigt."),
    ShockRun("Moms", "tMoms_y,tMoms_m", "Momssatser (indenlandsk og importeret)", 1.0, 0.005, "+0,5 pct.-point", 2030,
             _DREAM_GDP_NORM + " Stødet er halveret i forhold til de øvrige satsstød: ved ca. 0,9 pct.-point rammer "
             "de 18-åriges ejerboligbeholdning omkring 2110 nul, og modellen har ingen håndtering af den grænse.",
             max_scale=1.5,
             max_scale_da="Opskaleringen stopper ved ×1,5 (+0,75 pct.-point): omkring +0,9 pct.-point rammer de "
                          "18-åriges ejerboligbeholdning nul ca. 2110, og der har modellen ingen løsning at "
                          "tilnærme sig imod. Nedad gælder grænsen ikke.",
             explainer_da="Højere moms hæver forbrugerpriserne og sænker realindkomsten: forbruget falder ca. 1,5 pct., boligpriserne ca. 1,5 pct. og BNP ca. 0,3 pct., mens saldoen forbedres markant."),
    ShockRun("Registreringsafgift", "tReg_y,tReg_m", "Registreringsafgift, implicitte satser", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM,
             explainer_da="Højere registreringsafgift rammer bilkøbet: forbrug og investeringer falder marginalt, og saldoen forbedres lidt."),
    ShockRun("Energiafgift", "tAfg_y(cEne,*,*),tAfg_m(cEne,*,*)", "Energiafgifter på privat forbrug", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM,
             explainer_da="Højere energiafgifter hæver forbrugerpriserne ca. 0,2 pct. og sænker forbruget tilsvarende; BNP-effekten er lille, saldoen forbedres."),
    ShockRun("Forbrugsafgift", "tAfg_y(cVar,*,*),tAfg_m(cVar,*,*)", "Øvrige afgifter på privat vareforbrug", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM,
             explainer_da="Højere vareafgifter hæver forbrugerpriserne ca. 0,15 pct. og sænker forbruget tilsvarende; BNP-effekten er lille, saldoen forbedres."),
    ShockRun("Afgift_erhverv", "tAfg_y(bol|byg|ene|fre|lan|off|soe|tje|udv,!off,*),tAfg_m(bol|byg|ene|fre|lan|off|soe|tje|udv,!off,*)",
             "Afgifter på private erhvervs materialeinput", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM,
             explainer_da="Dyrere materialeinput hæver virksomhedernes omkostninger marginalt: effekterne på BNP og forbrug er under 0,1 pct., og provenuet forbedrer saldoen."),
    ShockRun("Produktsubsidier", "rSub_y,rSub_m", "Produktsubsidiesatser", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM,
             explainer_da="Højere produktsubsidier sænker priserne marginalt; virkningerne på BNP og forbrug er under 0,1 pct., og saldoen svækkes."),
    ShockRun("Lontilskud", "rSubLoen(!tot,*)", "Løntilskudssatser", 1.10, 0.0, "+10 pct. af satsen", 2030, _DREAM_GDP_NORM,
             explainer_da="Højere løntilskudssatser er et lille beløb i MAKRO: virkningerne på forbrug, BNP og saldo er under 0,05 pct."),
    ShockRun("Produktionssubsidier", "rSubYRest(!tot,*)", "Øvrige produktionssubsidier, sats", 1.10, 0.0, "+10 pct. af satsen", 2030,
             "DREAM hæver subsidiebeløbet (1 pct. af BNP) og endogeniserer satsen; MAKROskop hæver satsen direkte.",
             explainer_da="Højere produktionssubsidier sænker virksomhedernes omkostninger: investeringer og forbrug stiger lidt (0,1–0,2 pct.), mens saldoen svækkes."),
    ShockRun("Arbejdsudbud_beskaeftigelse", "snLHh (uDeltag endogen)", "Strukturel beskæftigelse, alle aldre 15-100",
             1.01, 0.0, "+1 pct.", 2030,
             "Samme lukning som DREAMs standardstød: den strukturelle beskæftigelse hæves 1 pct. for hver alder, "
             "og husholdningernes deltagelsesparameter uDeltag frigives alder for alder, så den rammer målet. "
             "(uDeltag er en ulempeparameter — at hæve den direkte sænker deltagelsen.)",
             explainer_da="Når 1 pct. flere står til rådighed for arbejdsmarkedet, finder de gradvist job: "
                          "beskæftigelsen er 1 pct. højere efter få år, og BNP vokser med omkring 1 pct. på langt "
                          "sigt, efterhånden som virksomhedernes kapitalapparat følger med. Lønnen dæmpes i "
                          "starten, og de offentlige finanser forbedres, fordi flere betaler skat."),
    ShockRun("Arbejdsudbud_timer", "uh", "Timepræferenceparameter (strukturel arbejdstid = 1/uh)",
             1 / 1.01, 0.0, "+1 pct. strukturel arbejdstid", 2030,
             "Samme virkning som DREAMs standardstød: DREAM hæver den strukturelle arbejdstid shLHh 1 pct. og "
             "endogeniserer uh; i modellen er shLHh = 1/uh eksakt, så MAKROskop sætter uh til 1/1,01 gange "
             "grundforløbets værdi, hvilket giver præcis +1 pct. arbejdstid for alle aldre.",
             explainer_da="1 pct. længere arbejdstid pr. beskæftiget giver næsten samme BNP-løft som 1 pct. flere "
                          "beskæftigede — omkring 1 pct. på langt sigt — uden at antallet af beskæftigede ændrer "
                          "sig. Timelønnen presses lidt ned i begyndelsen, og den offentlige saldo forbedres."),
    ShockRun("ArbejdsProd", "qProdHh_t,qProdxDK", "Arbejdskraftproduktivitet (trend)", 1.01, 0.0, "+1 pct.", 2030,
             "Samme instrumenter og størrelse som DREAMs standardstød.",
             explainer_da="Højere produktivitet løfter BNP gradvist mod +1 pct.; reallønnen følger med, og eksporten vinder markedsandele. Beskæftigelsen er uændret, fordi arbejdsudbuddet er strukturelt bestemt."),
    ShockRun("VirkDisk", "rVirkDiskPrem(!spTot,*)", "Virksomhedernes risikopræmie (hurdle rate)", 1.0, 0.001, "+0,1 pct.-point", 2030,
             "Samme instrument og størrelse som DREAMs standardstød.",
             explainer_da="Et højere afkastkrav i virksomhederne sænker investeringerne ca. 0,25 pct. og dermed kapitalapparatet; BNP ender ca. 0,1 pct. lavere."),
    ShockRun("BoligRisiko", "rBoligPrem", "Risikopræmie i boligernes usercost", 1.0, 0.001, "+0,1 pct.-point", 2030,
             "Samme instrument og størrelse som DREAMs standardstød.",
             explainer_da="En højere risikopræmie hæver boligernes usercost: boligpriserne falder ca. 0,5 pct., forbrug og boliginvesteringer lidt; BNP-effekten er lille."),
    ShockRun("AktieAfkast", "rVirkDiskPrem(!spTot,*),rAktieDriftPrem", "Risikopræmie på virksomheder og aktieafkast", 1.0, 0.001, "+0,1 pct.-point", 2030,
             "Samme instrumenter og størrelse som DREAMs standardstød.",
             explainer_da="Et højere afkastkrav gør investeringer dyrere: investeringerne falder ca. 0,25 pct. og BNP knap 0,1 pct. på langt sigt."),
    ShockRun("RisikoPraemier", "rVirkDiskPrem(!spTot,*),rAktieDriftPrem,rBoligPrem", "Alle tre risikopræmier", 1.0, 0.001, "+0,1 pct.-point", 2030,
             "Samme instrumenter og størrelse som DREAMs standardstød.",
             explainer_da="Højere risikopræmier på både virksomheder og boliger gør investeringer og boliger dyrere: investeringerne falder ca. 0,4 pct., boligpriserne ca. 0,5 pct. og BNP ca. 0,1 pct."),
    ShockRun("Diskontering", "jfDisk_t", "Husholdningernes diskonteringsfaktor (justering)", 1.0, -0.001, "−0,001", 2030,
             "Samme instrument og størrelse som DREAMs standardstød.",
             explainer_da="Mere utålmodige husholdninger sparer mindre op: forbrug og boligpriser stiger på kort sigt, men effekten aftager og vender på langt sigt, når formuen er blevet mindre."),
    ShockRun("Loen", "rLoenNash", "Arbejdsgivernes forhandlingsvægt i lønforhandlingen (Nash)", 1.0, -0.01,
             "−1 pct.-point (lønmodtagerne står stærkere)", 2030,
             "Samme instrument og størrelse som DREAMs standardstød. rLoenNash er arbejdsgivernes vægt i "
             "Nash-forhandlingen, så et fald betyder stærkere lønmodtagere.",
             explainer_da="Når lønmodtagerne står stærkere i lønforhandlingen, stiger timelønnen (ca. +0,7 pct.), og beskæftigelsen falder lidt (ca. −0,15 pct.); den højere realindkomst løfter forbrug og BNP svagt, mens saldoen svækkes lidt."),
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
        "maxScale": run.max_scale,
        "maxScaleDa": run.max_scale_da,
        "explainerDa": run.explainer_da,
    }


def etl_gdx_symbols() -> set[str]:
    """GDX symbols the ETL reads for shock deviations — the minimum a compact export needs."""
    names = {sdef.gdx_name for sdef in SERIES}
    names |= {template[0] for template in SECTOR_SERIES_TEMPLATES}
    names.add("rHBI")
    return names
