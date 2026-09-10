# MAKROskop – web-app

SvelteKit (Svelte 5, runes) + `adapter-static`. Læser de JSON-filer, `../etl/extract.py`
skriver til `static/data/`. Se repo-roden's README for arkitektur, ETL og deploy.

```bash
bun install
bun run dev        # udvikling
bun run check      # svelte-check
bun run build      # statisk site i build/
bun run preview
```

## Delingskort (share cards)

Hvert løst scenarie i hver tilladt skala har sin egen prerenderede side,
`/scenarier/<Stød><variant>/<skala>/` (fx `/scenarier/Rente_ufin/0.5/`), med egen titel,
beskrivelse og `og:image`. Teksten kommer fra `src/lib/card.ts`, billedet fra
`src/lib/card-svg.ts` + `scripts/og-images.ts` (resvg, kører som en del af `bun run build`
og skriver til `build/og/`, som aldrig committes). Skrifterne i `fonts/` er statiske
TTF-instanser (OFL) — `bun fonts/fetch.ts` henter dem igen. `bun run verify:build` tjekker
sider, tags og billeder efter et build.
