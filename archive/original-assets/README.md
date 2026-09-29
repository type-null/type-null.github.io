# Original materials retained locally

These files came with the original website. They were not referenced by the generated site, current Markdown posts, timeline data, active stylesheets, or runtime scripts when the repository was reorganized on September 29, 2026.

They remain here for future posts and historical reference. No unique artwork was discarded. Keeping them outside `assets/` prevents the builder from copying unused files into every published site.

- **252 files, 164,399,576 bytes** are retained here.
- `manifest.json` records each original path, archive path, byte count, and SHA-256 hash.
- `assets/images/card/` contains unused pack variants, English and Pocket logos, app logos, and mechanic artwork.
- `assets/css/`, `assets/fonts/`, and the remaining images retain the superseded original presentation files.
- The **186 original images used by the timeline remain in the active `assets/` tree**. The résumé information and portrait remain intact in their source locations.

The archived stylesheets are historical source files, not a second working website. Some of their original remote or missing dependencies already did not work in the old repository.

## Reuse a material

Copy the image you want into your new post folder, alongside `index.md`, then reference its filename in Markdown or the post's `cover` field. See [the posting guide](../../docs/WRITING.md).

For example, from the repository root:

```sh
cp 'archive/original-assets/assets/images/card/set-logo-en/SV/Pokemon_TCG_Scarlet_Violet_Logo.png' \
   'content/card/my-new-post/set-logo.png'
```

To restore the entire original asset collection to its old paths without overwriting existing files:

```sh
cp -R -n archive/original-assets/assets/. assets/
```

Restoring all assets makes future build output larger again. The archive remains untouched, so a restore is reversible.

## Verify preservation

```sh
python3 scripts/check-archive.py
```

This checks every archived file against its saved size and SHA-256 hash and confirms that every timeline record still has its original image locally. Keep this directory and its manifest together when backing up the repository.

The historical timeline audit (`scripts/import-timeline.py --audit`) also resolves original image and stylesheet paths from this archive, preserving its measured baseline after reorganization.
