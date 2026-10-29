# AGENTS.md

Notes for people and coding agents working on this fork of libsigrokdecode.

## What this fork is

`nemanjan00/libsigrokdecode` `master` is **stock upstream libsigrokdecode plus
topic branches merged on top**. Nothing upstream is rewritten. Every addition
comes in as a merge, so each source can be followed in `git log --graph`.

| Source | What it adds | How it got here |
|---|---|---|
| [sigrokproject/libsigrokdecode](https://github.com/sigrokproject/libsigrokdecode) `master` | upstream | merged |
| branch `saleae-hla` | decoder `saleae_hla`: runs Saleae Logic 2 High Level Analyzer extensions unchanged on top of `uart`, `i2c` or `spi` | merged |

It's maintained the same way as the companion libsigrok fork,
[nemanjan00/libsigrok](https://github.com/nemanjan00/libsigrok).

## Remotes

```sh
git remote add origin https://github.com/sigrokproject/libsigrokdecode.git
git remote add fork   git@github.com-libsigrokdecode:nemanjan00/libsigrokdecode.git   # push here (deploy key)
```

`fork` uses the per-project deploy key `~/.ssh/libsigrokdecode_deploy` through
the SSH alias `github.com-libsigrokdecode`.

## Branches: kept upstreamable

Every feature lives on a **topic branch based on upstream `master`**, so it
can be sent upstream as is. `master` is only where the branches are combined.

- Branch from `origin/master`, not from this fork's `master`:
  `git checkout -b <topic> origin/master`.
- Only upstreamable changes go on a topic branch: decoder code and its docs.
  Fork-only files such as this `AGENTS.md` and `README.md` stay on `master`.
- Commit to the topic branch first, push it, then merge it into `master` with
  `--no-ff` and push `master`. Both must always carry the same decoder
  changes.
- To refresh a topic branch for upstreaming, rebase it on the latest
  `origin/master` (topic branches may be force-pushed; `master` never).
- Current topic branches: `saleae-hla`.

## Syncing master

Merge; never rebase or force-push `master`:

```sh
git fetch origin
git checkout master                      # tracks fork/master
git merge origin/master
git push fork master
```

`master` replaces upstream's plain-text `README` with `README.md`. If an
upstream merge conflicts on `README` (modify/delete), keep it deleted and
carry anything worth having into `README.md`.

## AUR package

`libsigrokdecode-nemanjan00-git` builds this repo's `master` and replaces
`libsigrokdecode`/`libsigrokdecode-git`. Its packaging repo is
`ssh://aur@aur.archlinux.org/libsigrokdecode-nemanjan00-git.git` (AUR
account key `~/.ssh/aur_deploy`). It's the companion of
`libsigrok-nemanjan00-git`.

## Commit conventions

- Use the sigrok subject style: `<decoder>: <imperative summary>`, e.g.
  `saleae_hla: Add a decoder that runs Saleae Logic 2 HLA extensions`.
- No AI attribution in commits (no `Co-Authored-By` or "Generated with" lines).

## saleae_hla

The decoder re-implements the `saleae` Python package that Logic 2 gives HLA
extensions, from Saleae's public documentation. Logic 2's own copy has no open
license, so none of it is used. Usage and the supported API are in the
decoder's docstring (`decoders/saleae_hla/__init__.py`).

```sh
sigrok-cli -i cap.sr -P "uart:rx=0:baudrate=115200,saleae_hla:extension=<extension dir>:settings=packet_timeout=0.01" -A saleae_hla
```

- **Don't load untrusted extensions.** An extension is arbitrary Python that
  runs with the user's privileges, the same as in Logic 2. Some extensions ship
  pickled data files, which can also run code when loaded.
- **sigrok-cli 0.7.2** (as packaged by some distributions) is built against an
  older libsigrok and fails every decoder with a `g_variant_get_type`
  assertion. Use a sigrok-cli built from git.
