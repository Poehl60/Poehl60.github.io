# Coherence Framework v25

A reading system for **true vs false coherence** — whether a person, institution, or design generates more than it consumes, or consumes while looking like it generates.

**Not** a political party, cult, or vibes checklist. **Gift / forkable** — use, remix, and fork without permission.

**[Read it as a website →](https://poehl60.github.io/Framework/)** — every topic and case on its own page, searchable.

## Start here

1. [`coherence_framework_v25_beginner.txt`](coherence_framework_v25_beginner.txt) — vocabulary and kit map
2. [`coherence_framework_v25_order_truth.txt`](coherence_framework_v25_order_truth.txt) — Order / Truth / Disorder
3. [`INDEX.md`](INDEX.md) — **search by problem** (rent, epistemology, both parties, replication crisis, support vs system, etc.)

**Philosophy / no-metaphor lane:** [`INDEX.md` → Philosophy, epistemology, support vs system](INDEX.md#philosophy-epistemology-support-vs-system) → `order_truth` **STRUCTURE COUPLING AND TRUTH LAYERS**.

## Find a topic

Open **[INDEX.md](INDEX.md)** — maps search phrases to cases and kit topics. People search problems, not "Coherence Framework."

## Current version

This is **v25**. [`VERSIONS.md`](VERSIONS.md) records what is in the repo, what is deliberately left out, and how the website is generated.

## Reading the site

The `.txt` files are the source of truth. The site is generated from them by
`build_site.py` and deployed by GitHub Actions on every push to `main` — one page per
topic and per case, with a problem index, search, sitemap, and JSON-LD. Nothing generated
is committed.

To build locally:

```bash
python3 build_site.py
```

Outputs ~1,750 pages into `docs/`. Python 3.11 or later, no dependencies.

## Kit files

| File | What |
|------|------|
| `coherence_framework_v25_beginner.txt` | Onboarding |
| `coherence_framework_v25_order_truth.txt` | Order / Truth / Disorder bands |
| `coherence_framework_v25_disorder_forms.txt` | Disorder form library |
| `coherence_framework_v25_order_forms.txt` | Order form library |
| `coherence_framework_v25_theory.txt` | Foundation + procedure |
| `coherence_framework_v25_applied.txt` | Politics, science, glossary |
| `coherence_framework_v25_applied_science.txt` | Science + philosophy source tiers |
| `coherence_framework_v25_applied_s6.txt` | Politics in Action readings |
| `coherence_framework_v25_cases_real.txt` | Real-world case library — 455 cases |
| `coherence_framework_v25_cases_fiction.txt` | Fiction case library — 407 cases |
| `coherence_framework_v25_sophist.txt` | Pathos mechanics + SUPPORT lane |
| `coherence_framework_v25_transmission.txt` | Deposit + optional paste protocol |
| `coherence_framework_v25_analyst_policy.txt` | Analyst policy — declared positions, bias-labeled [not framework finding] |
| `cf_grep.txt` | Line maps + grep recipes |

## Publishing

Everything here is published as-is. The website is generated from the `.txt` files by
`build_site.py` on every push — nothing generated is committed. See
[`VERSIONS.md`](VERSIONS.md) for what is in the repo and what is left out.

## License

Framework kit is **not copyright-locked** [gift / Silent Alternative]. Fork freely. Method travels; brand without correctable axis does not.
