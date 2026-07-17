# Build-Your-Own-X Difficulty Ladder

Two self-contained, offline HTML pages that rank the projects from
[codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x)
from easiest to hardest:

- **`guide-ladder.html`** — every individual tutorial (~360 guides), grouped
  into difficulty tiers and filterable by tier, language, and category.
- **`category-ladder.html`** — the 30 top-level categories, grouped into
  Beginner / Intermediate / Advanced / Expert tiers.

Both are single files with all CSS, JS, and data inlined — no server, fonts, or
network needed. Open either directly in a browser (`file://`) and it works
offline, in your OS light/dark theme.

## Difficulty model

Difficulty is a judgment call, scored on three axes: prerequisite domain
knowledge, minimal-version scope, and how much step-by-step guidance exists.

- A guide **inherits its category's tier** — the dominant signal. A Regex-Engine
  guide is easier than an Operating-System guide whatever the language.
- **Language only nudges the order _within_ a tier**: lower-level languages
  (C, Rust, Assembly) sort a little harder than Python or JavaScript. It never
  moves a guide across a tier boundary.
- The **Unsorted** group is the repo's own "Uncategorized" bucket. Its guides
  span every level, so they are deliberately left un-ranked rather than forced
  into a tier.

The exact head-to-head order inside a tier is therefore approximate by design;
the tier boundaries are the trustworthy part.

## Regenerating

```sh
make build     # curl the README -> parse_guides.py -> build_pages.py
make clean     # remove the fetched README copy and guides.json
```

The pipeline:

1. `parse_guides.py` — parses a local copy of the upstream README
   (`byox-readme.md`) into `guides.json`, applying the difficulty model above.
2. `build_pages.py` — injects `guides.json` into `templates/guide.template.html`
   and wraps `templates/category.html`, writing the two standalone pages.

`byox-readme.md` and `guides.json` are derived artifacts and are gitignored; the
built `*-ladder.html` pages are committed as the runnable output.
