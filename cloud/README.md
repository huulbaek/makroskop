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
