# Cloud-kørsel: fuld horisont på en lejet maskine

Formål: løse MAKRO-stød over hele 100-års-horisonten med den frie løser og hente
resultaterne hjem til MAKROskop. Alt herunder er testet lokalt undtagen selve
fuldskala-løsningen (kræver ~64 GB RAM).

## Maskine

- **Hetzner Cloud CCX43** (16 AMD-kerner, 64 GB) eller **CCX53** (128 GB, anbefalet
  første gang) — Ubuntu 24.04. AWS-alternativ: `r6i.4xlarge` spot i eu-north-1.
- Vælg x86 (ikke ARM): MKL Pardiso-backenden er x86-only og er den store speedup.

## Køreplan

```bash
# 1. Lokalt: pak bundtet (~190 MB) og send det op
cloud/pack.sh
scp makroskop-cloud.tar.gz root@<box>:

# 2. På boksen: udpak, installér, verificér parseren (~5 min)
ssh root@<box>
tar xzf makroskop-cloud.tar.gz && cd makroskop-cloud
bash cloud/setup.sh        # slutter med residual-check: max |res| ~1e-9

# 3. Kør planen (fuld-horisont test + reference + to scenarier)
bash cloud/run.sh 2>&1 | tee run.log

# 4. Lokalt: hent resultaterne og indlæs dem i MAKROskop
scp 'root@<box>:makroskop-cloud/etl/shock_gdx/*.gdx' etl/shock_gdx/
cd etl && uv run python extract.py
cd ../app && bun run build
```

Sluk maskinen, når `run.log` er i hus — timeprisen løber, til den slettes.

## Hvad run.sh gør

1. **Fuld-horisont Newton-test** (2.197.277 ligninger, forstyrret start): måler
   hukommelse og tid pr. iteration og beviser, at fuld skala virker på boksen.
2. **`_reference.gdx`**: den uforstyrrede løsning. Stød-afvigelser måles mod den
   (kalibreringspunktet afviger 0,3–9 pct. fra baseline.gdx, så dette er obligatorisk).
3. **`Rente_perm.gdx`**: ECB-renten +100 bp permanent fra 2030 (kontinuationsløseren).
4. **`Oliepris_perm.gdx`**: Brent +10 pct. permanent fra 2030.

Flere stød: kopiér et `solve-export`-kald i `run.sh` og skift `--shock-name`
(dict-navn), `--shock-years`, `--shock-factor`/`--shock-delta` og `--out`
(filnavnet skal matche stød-kataloget i `catalog.py`: `<Navn><variant>.gdx`).

## Ny MAKRO-version: grundforløb og scenarier skifter samlet

DREAM udgiver nye versioner 2–4 gange om året (fx 2025-December, 2026-Maj, 2026-June);
zip'en og `baseline.gdx` ændres sammen, og ligninger/kalibrering kan være ændret. Alle
scenarier er afvigelser fra *den* versions referenceforløb, så de skal genløses, når
grundforløbet skifter. Regel: **opdatér aldrig `~/vserver/MAKRO` uden at genløse** —
og publicér grundforløb + scenarier i ét push.

1. **Lokalt:** `git -C ~/vserver/MAKRO pull` (den uberørte klon). Notér README-titlen og
   `git rev-parse --short HEAD`. Kør `cloud/pack.sh` — bundtet indeholder den nye zip og
   baseline.
2. **På boksen:** udpak i en *ny* mappe (ikke oven i den gamle: `etl/cache/` og
   `system.npz` hører til den gamle version). `bash cloud/setup.sh` skal slutte med
   max |res| ~1e-9 — ellers har parseren mødt nye konstruktioner; stop her.
3. **Ny reference:** `uv run python freesolver.py export-baseline --out shock_gdx/_reference.gdx`.
   Filen stemples med modellens fingerprint (sha256 af `raw.gms`), som `extract.py`
   sammenholder med zip'en i MAKRO-klonen.
4. **Genløs alle scenarier:** `shock_gdx/` skal være tom for gamle filer — `run_batch2.sh`
   springer eksisterende `.gdx` over. Kør `cloud/run.sh`-scenarierne og
   `cloud/run_batch2.sh` (gerne med `--export-stages`, se nedenfor). Budget: 2–3 timer pr.
   stød på en 16-kerners boks, dvs. omkring et døgn for ti stød; prisen er boksens timepris.
5. **Hjem:** `scp` alle `shock_gdx/*.gdx`, `cd etl && uv run python extract.py`. Outputtet
   må hverken indeholde `WARNING: ... solved on a different model` eller `assuming ...`
   (ustemplet fil). `meta.json` og hvert scenaries `modelVersion` skal have samme
   fingerprint — ellers viser appen en versionsadvarsel.
6. **Validering:** opdatér tallene i `app/static/data/validation.json` fra `run.log`
   (fuld-horisont-genfinding), eller lad dem stå med tydelig versionsangivelse.
7. **Én commit** med data-JSON (+ validering), `git push` → Dokploy bygger og deployer.
   Footeren viser den nye modelversion.

Kræver *ikke* genløsning: UI-ændringer, katalog-labels, ændringer i `extract.py`
(sekunder fra de eksisterende GDX-filer), nye stød (kun det nye løses).

### Kontinuationstrin som gratis data

`solve-export --export-stages` skriver hvert konvergeret kontinuationstrin (1 %, 3,5 %,
9,75 %, … af stødet) som en kompakt `<navn>_sNNN.gdx` (NNN = andel i promille, kun de
serier ETL'en bruger). `uv run python nonlinearity.py <navn>` sammenligner trinnene med
den endelige løsning og rapporterer, hvor langt modellen er fra lineær — grundlaget for
at skalere et løst scenarie i appen (fx +50 bp som halvdelen af +100 bp).

## Fejlsøgning

- `pypardiso unavailable`: kør videre — SuperLU virker, bare langsommere.
- Newton stopper med "line search failed with fresh Jacobian": gør stødet mindre
  eller start kontinuationen finere (sænk `step = 0.01` i `solve_shock`).
- Hukommelse: `watch -n5 free -g` i en anden terminal. CCX53 (128 GB) fjerner risikoen.

## Forbehold

Scenarierne er afvigelser fra **kalibreringsforløbet** (zip'ens løsningspunkt), ikke
DREAMs officielle grundforløb — fint til marginale eksperimenter, og MAKROskop viser
kun afvigelser. En konfigurationsren baseline-zip (via licenseret CONVERT) er en
senere forbedring.
