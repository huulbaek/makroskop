# MAKROskop

En prototype på en offentligt-vendt udforsker af [MAKRO](https://github.com/DREAM-DK/MAKRO) –
den makroøkonomiske model, DREAM-gruppen udvikler til Finansministeriet m.fl.

To dele:

```
etl/   Python: læser MAKROs GDX-filer og skriver JSON til web-appen
app/   SvelteKit: statisk web-app (grundforløb + scenarie-værksted)
```

## Arkitektur

Ingen GAMS-licens kræves for at **vise** noget som helst – kun for at **beregne** nye scenarier:

1. `Model/Gdx/baseline.gdx` (følger med MAKRO-repoet via git-lfs) læses med den
   pip-installerbare `gamsapi[transfer]` + `gamspy_base` (ingen GAMS-installation nødvendig).
2. `etl/extract.py` afdetrender med modellens `fvt/fqt/fpt`-faktorer (så beløb bliver
   faktiske mia. kr.), beregner nøgle-ratioer og skriver `app/static/data/*.json`.
3. Web-appen er 100 % statisk (adapter-static) og kan hostes hvor som helst.

### Scenarier (stød)

Løste stød fra MAKROs `Analysis/Standard_shocks`-pipeline (kræver GAMS + CONOPT4, minutter
pr. stød fra det medfølgende savepoint) lægges som GDX-filer i `etl/shock_gdx/` med navne som
`Bundskat_ufin.gdx`. Kør `extract.py` igen, og scenariet dukker op i appen som afvigelser fra
grundforløbet. Uden rigtige stød-data viser appen et tydeligt mærket syntetisk demo-scenarie
(`--demo`-flaget).

## Kørsel

```bash
# ETL (kræver uv)
cd etl
uv run python extract.py --demo    # --makro-root peger på MAKRO-repoet

# App (kræver bun)
cd ../app
bun install
bun run dev        # eller: bun run build && bun run preview
```

## Datakatalog

Variabeludvalg, danske/engelske labels og enheder er porteret fra DREAMs egen plot-pipeline
(`Analysis/Templates/variables_to_plot.py` og `Analysis/Standard_shocks/shocks_to_plot.py`)
og vedligeholdes i `etl/catalog.py`. Stødkataloget (40 standardstød) samme sted.

## Vigtige forbehold

- Grundforløbet er stiliseret og egner sig kun til marginale eksperimenter – ikke som prognose
  (jf. MAKROs README).
- Stød-kurver er afvigelser fra grundforløbet, normeret (typisk 1 pct. af BNP / 1 pct.-point).
- Modelversion + commit stemples i footeren; ETL'en læser den fra MAKRO-repoets README og git.
