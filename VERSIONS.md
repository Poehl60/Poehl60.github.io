# Publishing record

What the public repo contains, and how it differs from this working copy.
Current version: **v25**. One file per role — read order is `beginner` → `order_truth` → `INDEX.md`.

---

## Current kit

| File | Bytes | Lines |
|------|-------|-------|
| `coherence_framework_v25_beginner.txt` | 28,939 | 446 |
| `coherence_framework_v25_order_truth.txt` | 40,298 | 534 |
| `coherence_framework_v25_theory.txt` | 816,374 | 15,676 |
| `coherence_framework_v25_disorder_forms.txt` | 84,470 | 1,207 |
| `coherence_framework_v25_order_forms.txt` | 39,510 | 528 |
| `coherence_framework_v25_applied.txt` | 397,325 | 6,847 |
| `coherence_framework_v25_applied_science.txt` | 254,590 | 4,000 |
| `coherence_framework_v25_applied_s6.txt` | 858,941 | 13,305 |
| `coherence_framework_v25_cases_real.txt` | 2,338,239 | 36,672 |
| `coherence_framework_v25_cases_fiction.txt` | 949,907 | 17,507 |
| `coherence_framework_v25_cases.txt` | 1,309 | 29 |
| `coherence_framework_v25_sophist.txt` | 25,858 | 329 |
| `coherence_framework_v25_transmission.txt` | 12,395 | 239 |
| `cf_grep.txt` | 29,339 | — |
| **Total** | **5,877,494** | |

Real case anchors: **459**. Fiction case anchors: **408**.

---

## Published snapshot vs. this copy

`main` was last written **2026-08-29**. Everything since then exists only locally. Measured 2026-11-06:

| File | Public `main` | Local | Delta |
|------|--------------|-------|-------|
| `cases_real.txt` | 815,622 | 2,338,239 | +1,522,617 |
| `applied_s6.txt` | 556,380 | 858,941 | +302,561 |
| `applied_science.txt` | 135,644 | 254,590 | +118,946 |
| `applied.txt` | 311,506 | 397,325 | +85,819 |
| `theory.txt` | 737,071 | 816,374 | +79,303 |
| `disorder_forms.txt` | 54,008 | 84,470 | +30,462 |
| `beginner.txt` | 17,900 | 28,939 | +11,039 |
| `cf_grep.txt` | 23,730 | 29,339 | +5,609 |
| `order_forms.txt` | 41,309 | 39,510 | −1,799 |
| `order_truth.txt` | 48,632 | 40,298 | −8,334 |
| `sophist.txt` | *absent* | 25,858 | added |

Two of these move the wrong way: `order_forms` and `order_truth` are **smaller** locally. Local v25 is treated as canonical, so publishing replaces the public copy with the local one. `publish.sh` refuses this by default and requires `--overwrite-newer` to proceed, so the loss is never silent.

⚠️ `order_truth.txt` is the one to check by hand before publishing — the public copy is 8 KB larger, so it may contain work that never came back local.

---

## Not published

Excluded from every publish and from the website build:

| Path | Why |
|------|-----|
| `Personal/**` | live loop, hold queue, long-term queue, persona, survival file, source inbox, ABSTRACT |
| `technical/**` | logs, temp, snapshots, scripts |
| `.cursor/**` | agent rules, hooks, skills |
| `docs/**` | generated in CI on every push from the `.txt` kit |

`PUBLISH_MANIFEST.txt` is the allowlist. `technical/publish.sh` refuses the paths above even if the manifest is edited to include them.

---

## Publishing

```bash
./technical/publish.sh --plan                    # what would publish; touches nothing
./technical/publish.sh --bootstrap --yes "msg"   # first push: init repo, fetch, push
./technical/publish.sh --yes "msg"               # subsequent updates
```

Manual only. Nothing here runs on a timer, hook, or loop.

### One-time setup

Auth is stored **once**, outside this repo. After that the script pushes without prompting and no secret passes through any agent.

Option A — `gh` CLI, stores in the system keyring:

```bash
sudo pacman -S github-cli
gh auth login          # GitHub.com -> HTTPS -> login with browser
```

Option B — fine-grained token. Create at
<https://github.com/settings/personal-access-tokens/new> with:

| Field | Value |
|---|---|
| Resource owner | `Poehl60` |
| Repository access | Only select repositories → `Poehl60/Framework` |
| Contents | Read and write |
| Workflows | Read and write — required for `.github/workflows/pages.yml` |
| Everything else | No access |

Then store it once:

```bash
git config --global credential.helper store
git push   # prompts once; the token is saved to ~/.git-credentials (chmod 600)
```

Also required once: `git config --global user.email` and `user.name`, or the commit fails at the end.

### Guards

The script stops rather than guess:

- **Remote larger than local** → refuses; needs `--overwrite-newer`. This is the `order_truth.txt` case.
- **Forbidden path staged** → refuses outright, even if the manifest is edited to include it.
- **No git identity** → refuses before staging.
- **Nothing changed** → exits clean.

Files outside the manifest are **not** deleted by a publish — `git add -A -- <allowlist>` only touches allowlisted paths. Removing a public file needs an explicit `git rm`.

### First push expectations

1. `order_truth.txt` is 8 KB larger on GitHub than locally. The script stops here. Decide which copy is canonical before passing `--overwrite-newer`.
2. `cursor_usage_guide.txt` and `coherence_framework_v25_personal_political.txt` exist on GitHub but not locally. They stay published and untouched unless explicitly removed.

Website: `.github/workflows/pages.yml` builds `docs/` from the kit on every push to `main` and deploys it to Pages. Enable once in **Settings → Pages → Source: GitHub Actions**.

License: CC0. Fork, mirror, and republish without permission.

---

*File sizes and anchor counts measured 2026-11-06. Re-run after any publish.*
