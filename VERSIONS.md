# What is published

The public repo holds the full reading corpus. This page records what is in it, what is
deliberately left out, and how the website is generated.

Current version: **v25**. One file per role. Read order is `beginner` → `order_truth` →
`INDEX.md` for the problem you have.

Website: <https://poehl60.github.io/Framework/>

---

## The kit

| File | Bytes | Lines |
|------|-------|-------|
| `coherence_framework_v25_beginner.txt` | 28,939 | 445 |
| `coherence_framework_v25_order_truth.txt` | 40,298 | 533 |
| `coherence_framework_v25_theory.txt` | 816,374 | 15,675 |
| `coherence_framework_v25_disorder_forms.txt` | 84,470 | 1,206 |
| `coherence_framework_v25_order_forms.txt` | 39,510 | 527 |
| `coherence_framework_v25_applied.txt` | 397,325 | 6,846 |
| `coherence_framework_v25_applied_science.txt` | 254,590 | 3,999 |
| `coherence_framework_v25_applied_s6.txt` | 858,941 | 13,304 |
| `coherence_framework_v25_cases_real.txt` | 2,338,239 | 36,671 |
| `coherence_framework_v25_cases_fiction.txt` | 949,907 | 17,506 |
| `coherence_framework_v25_cases.txt` | 1,309 | 28 |
| `coherence_framework_v25_sophist.txt` | 25,858 | 328 |
| `coherence_framework_v25_transmission.txt` | 12,395 | 238 |
| `coherence_framework_v25_analyst_policy.txt` | 972,349 | 14,945 |
| `cf_grep.txt` | 29,339 | 424 |
| **Total** | **6,849,843** | |

Case library: **455** real cases, **407** fiction cases.

### About the analyst policy file

`coherence_framework_v25_analyst_policy.txt` is **not** framework finding. It is the
author's own declared positions — bias-labeled, with a `PERSONAL BIAS WARNING` on every
topic that carries one. It is published on purpose: the framework treats stated position
as the honest form, and undisclosed preference is not policy.

Read the kit without it if you want the method alone. Read it if you want to know where
the author stands and hold them to it.

---

## What is not published

| Path | Why |
|------|-----|
| `Personal/**` | working files — session state, queues, notes |
| `technical/**` | scripts, logs, local archives |
| `.cursor/**` | editor and agent configuration |
| `docs/**` | generated HTML, rebuilt by CI — never committed |

The site is built from the `.txt` files. Nothing generated is stored in the repo.

---

## How the website works

`.github/workflows/pages.yml` runs on every push to `main`. It:

1. finds `build_site.py` (repo root or `scripts/`)
2. runs it, generating `docs/`
3. uploads `docs/` and deploys to GitHub Pages

`build_site.py` turns each kit topic and each `[CASE:...]` anchor into its own page with a
title, description, canonical URL, and JSON-LD, plus a problem index, search, sitemap, and
`robots.txt`. Output is ~1,750 pages.

To build locally:

```bash
python3 build_site.py
```

Python 3.11 or later, no dependencies. Output goes to `docs/`.

### Changing the published set

Edit the `.txt` files and push. Only files present in the repo are published — there is no
allowlist to maintain. Anything you do not want public should not be in the repo.

---

## License

CC0. Fork, mirror, and republish any part of this without permission.

---

*Sizes and counts measured 2026-11-06 against the local working copy.*
