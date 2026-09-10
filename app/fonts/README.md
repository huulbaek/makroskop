# Fonts for the build-time share cards

Static TrueType instances of the site's web fonts, used only by the build-time card renderer
(`scripts/render-card.ts`, driven by `scripts/og-images.ts`) (resvg cannot instance variable
fonts). Regenerate with `bun fonts/fetch.ts`.

- Newsreader 500, 600, italic 500 — © Production Type, SIL Open Font License 1.1
- IBM Plex Sans 400, 500 and IBM Plex Mono 400 — © IBM Corp., SIL Open Font License 1.1

Licence text, one notice per family: `OFL-Newsreader.txt`, `OFL-IBMPlexSans.txt`,
`OFL-IBMPlexMono.txt`. The site itself loads the same families from Google Fonts.
