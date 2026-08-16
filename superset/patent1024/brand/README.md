# Patent 1024 brand assets

The "Claim Tree" identity. A claim set is a tree — one independent claim
branching into dependents — and a binary tree ten levels deep has exactly
1024 leaves. The mark is that tree.

Every shipped asset is generated from the single geometry definition in
`geometry.py`, so the lockup, the favicon and the spinner cannot drift apart.
Edit the geometry or the colour ramp there, never the output files.

## Regenerating

From the repository root:

```bash
pip install pillow fonttools brotli uharfbuzz numpy   # dev-only, not runtime deps
python superset/patent1024/brand/generate.py
```

Output is written to `superset-frontend/src/assets/images/` (the source of
truth, which webpack copies to `superset/static/assets/images/`) and mirrored
straight into `superset/static/assets/images/` so a running instance picks the
new assets up without a rebuild.

The wordmark is set in Inter SemiBold and IBM Plex Mono Medium and converted to
outlines, so no font ships with the logo and it renders identically everywhere.
Both faces are already frontend dependencies (`@fontsource/inter`,
`@fontsource/ibm-plex-mono`) and both are SIL Open Font License 1.1, which
permits embedding their outlines. They are located by family name, so a webpack
rehash does not break this script — but the frontend must have been built, or
its `node_modules` installed, for them to be found.

## What gets written

| File | Used by |
| --- | --- |
| `patent-1024.svg` | site header, auth pages, `APP_ICON` |
| `patent-1024-inverse.svg` | dark grounds |
| `patent-1024-mark.svg`, `-mark-inverse.svg` | square mark, avatars |
| `patent-1024.png` | schema.org `publisher.logo` (Google needs a raster) |
| `patent-1024-email.png` | password-reset email (clients strip CSS filters) |
| `p4-favicon.ico`, `p4-favicon.png`, `p4-apple-touch-icon.png` | `FAVICONS` |
| `patent-1024-og.png`, `blog-og.png`, `blog-patent-trends-og.png` | `og:image` |
| `patent-1024-loading.gif` | `brandSpinnerUrl` |

## Three drawings, not one

The mark is reduced as it shrinks, which is why it survives a 16px tab:

- **full** (1-2-4-8) at 40px and up — all four generations, navy stepping to cyan
- **compact** (1-2-4) from 24 to 40px — outer generation dropped, strokes thickened
- **mini** (1-2) below 24px — just the fork

`p4-favicon.ico` is assembled by hand so each entry carries its own drawing
rather than a downscale of the largest.

## Not touched

`favicon.png` and `loading.gif` in `superset-frontend/src/assets/images/` are
unmodified upstream Superset files. The Patent 1024 equivalents sit alongside
them under distinct names and are wired up through config, keeping upstream
merges mechanical.
