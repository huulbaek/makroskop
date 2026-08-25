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
