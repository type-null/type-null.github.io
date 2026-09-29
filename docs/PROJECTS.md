# Companion websites and project articles

Each app stays in its own repository and has its own GitHub Pages address. The blog adds an introduction, a local screenshot and an optional live preview. Readers can use the app inside the article or open its complete, independent interface in a new tab. The circular GitHub button opens its source repository.

GitHub Pages supports separate project sites alongside the main blog, including public repositories on GitHub Free. See [GitHub's Pages overview](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

## Add a live project preview

Copy [the project starter](../examples/project.md), write an introduction, and save a screenshot as `cover.png` beside `index.md`. A **1000 × 480** image matches the news artwork proportions. Use `template: article` to keep the homepage cover without repeating it above the project preview. Add this front matter:

```yaml
embeds:
  - type: project
    title: PTCG calendar
    image: cover.png
    repository: https://github.com/type-null/PTCG-calendar
    url: https://type-null.github.io/PTCG-calendar/
    interactive: true
```

Put `[[embed:1]]` on its own line in the body. Set `interactive: false` or omit it for a screenshot link only. Before a website exists, omit both `url` and `interactive`; the screenshot will open GitHub instead.

On the hosted blog, a live preview loads when it comes into view. When opening the blog through `file://`, it initially shows only the local screenshot and makes no automatic project request; **Use in this article** loads the online app when requested. **Open website** always opens the same app address separately. Without JavaScript, the screenshot, website and GitHub links still work in new tabs.

The screenshot stays visible until the app confirms that it is ready. An unavailable site or a hosted 404 therefore keeps the saved preview and offers **Try again** after the timeout. These apps implement the small `type-null:embed-ping` / `type-null:embed-ready` message exchange. A future app needs the same readiness response for its live preview; an ordinary website link does not.

## Publish and update independently

| Project repository | Pages destination | Build command in that repository |
| --- | --- | --- |
| [PTCG-calendar](https://github.com/type-null/PTCG-calendar) | `https://type-null.github.io/PTCG-calendar/` | `python3 export_site.py` |
| [PTCG-database](https://github.com/type-null/PTCG-database) | `https://type-null.github.io/PTCG-database/` | `python3 code/buildSite.py` |
| [Squirrel Tracker](https://github.com/type-null/Website-central-park-squirrel-tracker) | `https://type-null.github.io/Website-central-park-squirrel-tracker/` | `python3 scripts/build_site.py` |

In each repository, select **Settings → Pages → Build and deployment → Source → GitHub Actions**. Push to its configured `main` or `master` branch: its workflow builds and checks `site/`, then publishes that folder. Wait for a successful deployment and verify the address; configuration alone does not establish that a website is live.

Later source changes follow the same automatic build and deployment. The URL stays stable, so the blog's preview and full-page link use the new version without an app-copying step or a blog rebuild. Refresh the screenshot and article text manually when useful, update the article's `updated` date, and rebuild the blog.

The calendar build uses its saved event edition and current template; fetching newer events is separate. The database build uses its committed **48-card edition** and current viewer; changing that selection is a deliberate `code/exportSite.py` operation. The squirrel website presents the archived 2018 census. Rebuilding an interface does not refresh the underlying research data.

Each repository owns its source, local data and generated `site/` files. Do not use symbolic links into another checkout as a deployment shortcut: Pages artifacts must contain the actual files and exclude symbolic and hard links. See [GitHub's artifact requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages#configuring-the-upload-pages-artifact-action).

## Offline use and research sites

The blog's writing, screenshots and interface work offline. Live previews, project websites and GitHub need internet. For an offline app, download that project's complete `site/` folder and open its `index.html` with its assets alongside it. The original local calculators and games still use [local website embeds](WRITING.md#put-a-calculator-or-game-inside-a-post).

A research presentation can have its own design and shareable address in the same way. The [Florida introduction](../content/notes/florida-power-systems/index.md) is reserved for future study and website links; it contains no research results yet. The old `florida/map.html` address links to that introduction.
