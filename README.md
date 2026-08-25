# MAKROskop

En offentligt-vendt udforsker af [MAKRO](https://github.com/DREAM-DK/MAKRO) – den
makroøkonomiske model, DREAM-gruppen udvikler til Finansministeriet m.fl. – med en
**licensfri løser**, så nye scenarier kan beregnes uden GAMS/CONOPT.

Tre sider: **Grundforløb** (modellens baseline), **Scenarier** (stød som afvigelser fra
grundforløbet) og **Validering** (den frie løser krydstjekket mod GAMS/IPOPT og kørt i fuld
skala: 2.197.277 ligninger over hele horisonten).

```
etl/    Python (uv): GDX → JSON til web-appen, samt freesolver.py (den frie løser)
app/    SvelteKit (bun): statisk web-app, adapter-static
cloud/  Køreplan for fuld-horisont-løsninger på en lejet 64 GB-maskine
```

## Arkitektur

Ingen GAMS-licens kræves – hverken for at vise eller beregne:

1. `Model/Gdx/baseline.gdx` og `Model/deep_dynamic_calibration.zip` fra MAKRO-repoet læses
   med den pip-installerbare `gamsapi[transfer]` + `gamspy_base` (ingen GAMS-installation).
2. `etl/extract.py` afdetrender med modellens `fvt/fqt/fpt`-faktorer, beregner nøgle-ratioer og
   skriver `app/static/data/*.json`. Stød-scenarier i `etl/shock_gdx/*.gdx` bliver til
   `app/static/data/shocks/<Navn><variant>.json` som afvigelser fra referencen.
3. `etl/freesolver.py` parser modellens udfoldede ligningssystem fra zip'en og løser stød med
   Newtons metode (ikke-monoton linjesøgning, adaptiv stød-kontinuation, checkpoints). Lineære
   systemer: verificeret kæde Pardiso → UMFPACK → SuperLU med rækkeekvilibrering og iterativ
   forbedring. Kommandoer: `parse`, `check`, `jacobian`, `newton`, `oracle`, `solve-export`,
   `export-baseline`.
4. Web-appen er 100 % statisk og kan hostes hvor som helst.

### Scenarier

Et 10-års udsnit (~200.000 ligninger) kan løses på en 16 GB-bærbar. Hele horisonten
(2,2 mio. ligninger) kræver ~64 GB og køres på en lejet maskine – se `cloud/README.md`.
Stød-afvigelser måles **altid** mod `etl/shock_gdx/_reference.gdx` (zip'ens kalibreringspunkt),
som `extract.py` foretrækker automatisk, når filen findes.

Filnavne følger stød-kataloget i `etl/catalog.py`: `<Navn><variant>.gdx`, fx `Rente_ufin.gdx`
(`_ufin` = permanent, ufinansieret). Uden rigtige stød-data viser appen et tydeligt mærket
syntetisk demo-scenarie (`--demo`-flaget).

## Kørsel

```bash
# ETL (kræver uv)
cd etl
uv run python extract.py             # --makro-root peger på MAKRO-repoet; --demo for syntetisk stød

# Fri løser: parse + residual-check + et lille stød på et 10-års udsnit
uv run python freesolver.py parse
uv run python freesolver.py check
uv run python freesolver.py newton --from-year 2120 --perturb 1e-4

# App (kræver bun)
cd ../app
bun install
bun run dev                          # eller: bun run build && bun run preview
```

## Deploy (Dokploy)

Live på **https://makroskop.nodalit.com** — en Dokploy-Application på nodalit-serveren, bygget
fra dette GitHub-repo med `Dockerfile` i roden (bun bygger `app/`, nginx serverer `app/build`).
Et `git push` til `main` er hele deployet; data-JSON'en ligger i repoet, så ingen ETL kører i
byggeriet.

1. Dokploy → Create Application → source: dette repo, branch `main`, build type **Dockerfile**
   (Dockerfile path `Dockerfile`, build context `.`).
2. Domain `makroskop.nodalit.com`, HTTPS via Traefik/Let's Encrypt, container port **80**.
   DNS: A-record → serverens IP, *uden* Cloudflare-proxy (Let's Encrypt HTTP-udfordring).
3. Health check path `/`. Valgfrit build arg `APP_COMMIT=<sha>` stempler commit i footeren.
4. Deploy. Nye scenarier: kør `extract.py`, commit JSON'en, push.

Lokal test af imaget: `docker build -t makroskop . && docker run --rm -p 8089:80 makroskop`.

Footeren stempler modelversion + MAKRO-commit (fra ETL'en) og MAKROskop-commit + byggedato
(injiceret af Vite ved build).

## Datakatalog

Variabeludvalg, danske/engelske labels og enheder er porteret fra DREAMs egen plot-pipeline
(`Analysis/Templates/variables_to_plot.py` og `Analysis/Standard_shocks/shocks_to_plot.py`)
og vedligeholdes i `etl/catalog.py`. Stødkataloget (40 standardstød) samme sted.

## Vigtige forbehold

- Grundforløbet er stiliseret og egner sig kun til marginale eksperimenter – ikke som prognose
  (jf. MAKROs README).
- Frie løser-scenarier er afvigelser fra modellens kalibreringsforløb, ikke DREAMs officielle
  grundforløb; tallene bør ikke citeres som Finansministeriets.
- Valideringssiden dokumenterer, hvad der er efterprøvet, og hvad der ikke er.
- MAKROskop er en uafhængig prototype, ikke et produkt fra DREAM eller Finansministeriet.
