# build-your-own-x: ladder + builds + progress

A personal home for working through
[codecrafters-io/build-your-own-x](https://github.com/codecrafters-io/build-your-own-x).
Two halves live here:

- **`byox_ladder/`** — a difficulty-ladder generator + progress tracker. It
  ranks the ~360 guides easiest→hardest into offline HTML pages, and the `byox`
  CLI lets you mark guides done and note where you built each one. Progress is a
  [crdt_sync](https://github.com/kuhyx/utils) log, so it syncs across your
  machines (same layer diet_guard / screen-locker use).
- **`builds/`** — what you actually build, one folder per guide
  (e.g. `builds/tool-tutorial/` — the "Create a CLI tool in Javascript" guide).

## Track progress

```sh
byox status                                   # X / 359 done, per-tier breakdown
byox done "cli-tool" --note builds/tool-tutorial
byox sync                                      # push/pull across devices
byox build                                     # bake progress into the HTML dashboard
```

`byox done <guide>` resolves `<guide>` against the parsed guide list by URL,
url-slug, or title substring; an ambiguous token prints the candidates.

## Regenerate the ladder

```sh
cd byox_ladder
make build     # fetch upstream README -> parse -> build both pages (+ progress)
make clean     # remove the fetched README copy and guides.json
```

See `byox_ladder/README.md` for the difficulty model.

## Sync setup

Progress syncs through a private GitHub repo via crdt_sync. Create a
fine-grained PAT (contents read/write on the sync repo) and drop it at
`~/.config/byox_ladder/sync_token` (mode 600). Without it, `byox` still works
fully offline — sync just no-ops.

## Development

```sh
pip install -r requirements.txt
pre-commit install && pre-commit install --hook-type pre-push
python -m pytest byox_ladder/tests/ --cov=byox_ladder --cov-branch --cov-fail-under=100
```
