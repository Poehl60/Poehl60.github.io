#!/usr/bin/env python3
"""
Build a static HTML site from the Coherence Framework kit into ./docs.

Why: the kit is *.txt — a search engine sees ~15 crawlable URLs, not the
thousands of topics and cases inside them. This turns each kit topic and each
[CASE:...] anchor into a real page with a title, headings, canonical URL,
description, and sitemap entry.

Usage:  python3 scripts/build_site.py
Output: docs/  (static, .nojekyll, no build step needed on GitHub)

NOT published: Personal/, technical/, logs/. The analyst policy file IS published —
it is declared position, labeled as such (analyst 2026-11-06).
"""

import html
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
# Works whether this file sits in scripts/ (local) or at the repo root (a
# one-time GitHub web upload always lands at root).
ROOT = _HERE if os.path.basename(_HERE) != "scripts" else os.path.dirname(_HERE)
OUT = os.path.join(ROOT, "docs")

SITE_NAME = "Coherence Framework"

# URL prefix for the deployed site [analyst 2026-11-06].
#   ""            -> https://poehl60.github.io/            (user site repo, root property)
#   "/Framework"  -> https://poehl60.github.io/Framework/  (project repo, subpath property)
# Every URL in the build derives from this one constant: canonicals, sitemap,
# robots, og:image, breadcrumbs, internal links, and the site-search payload.
# A root site is the correct target because Google only reads robots.txt at the
# host root, and Search Console only offers the robots.txt report for root-level
# properties — a subpath property reports "could not be read" for a valid sitemap.
# Override per-build with SITE_BASE (e.g. SITE_BASE=/Framework python3 ...).
BASE = os.environ.get("SITE_BASE", "")
ORIGIN = os.environ.get("SITE_ORIGIN", "https://poehl60.github.io")

# Google Search Console ownership proof [analyst 2026-11-06].
# Emitted as a <meta> tag on every page, so verification survives rebuilds.
# It is a public identifier, not a secret. Set to "" to drop it.
GOOGLE_VERIFY = "5DBmhSs7USDDh5AoE4rybj9K0il1noBed9oylSnOzrI"

# Bing Webmaster Tools ownership proof. Same public-identifier logic as above.
# Paste the content="" value from Bing's "HTML meta tag" verification option.
# Empty means no tag is emitted — Bing can still verify via an XML file it drops
# at the site root (BingSiteAuth.xml) or via importing from Search Console.
BING_VERIFY = ""

# IndexNow key [protocol: indexnow.org]. Proves the site is yours when Bing,
# Yandex, Naver, Seznam, or DuckDuckGo are pinged that URLs changed.
#
# Leave empty to disable. To enable: put a key of 8-128 chars (a-z, A-Z, 0-9,
# and dashes only) in here. The build then publishes it at
# https://poehl60.github.io/<key>.txt, which is the whole verification step —
# there is no account, no dashboard, no OAuth.
#
# WHY IT HAS TO BE GENERATED HERE: docs/ is gitignored and rebuilt from scratch
# by CI on every push, so a key file uploaded by hand would vanish on the next
# deploy. Writing it from a constant in the builder makes it survive rebuilds.
# The key is public by design — it lives at a public URL. It is not a secret.
INDEXNOW_KEY = "7fc482195566ca3aa117113934b6b733"

# Fallback lastmod when the source file's history is unknown.
# Why this matters: mtime is NOT a publication date. A fresh `git clone` or a
# GitHub Actions checkout stamps every file with "now", so an mtime-derived
# lastmod tells a crawler "all 1851 pages changed today" on every single build.
# Google discounts a lastmod it can prove is untrustworthy, which slows recrawl.
# Order of preference per source file:
#   1. `git log -1 --format=%cs` — the actual last commit date (CI has history).
#   2. Filesystem mtime — only when not in a git repo (local scratch build).
#   3. This constant — last resort.
LASTMOD_FALLBACK = "2026-11-06"

# Canonical public home of the source. Linked from every page footer so the
# site and the repo point at each other (helps discovery both directions).
REPO_URL = "https://github.com/Poehl60/Framework"

# Favicon: inline SVG, so there is no favicon.ico 404 and no extra file.
FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' fill='%230f1115'/%3E"
    "%3Ctext x='16' y='23' font-size='20' font-family='monospace' "
    "fill='%237fb2ff' text-anchor='middle'%3E~%3C/text%3E"
    "%3C/svg%3E"
)

# Social share card. Must be an absolute URL to a real image; leave "" to omit.
OG_IMAGE = f"{ORIGIN}{BASE}/og.png"

EXCLUDE_REASON = "analyst_policy is bias-labeled personal political position, not kit reading"

# Private-lane redaction is OFF by design.
# The kit .txt files are published verbatim (they are in PUBLISH_MANIFEST.txt), and
# they name Personal/ paths in navigation notes. Redacting the HTML while shipping
# the same paths in the .txt is theatre, and the substitution mangles sentences
# ("archive `Personal/...`" -> "archive `local lane`"). Off = pages match source.
SITE_REDACT = False

# file stem -> (nav label, short slug dir, description)
#
# PLAIN TITLES [analyst 2026-11-07]: several kit topics are titled in framework
# internal shorthand -- "Form -- Democracy-fake", "T9 in Politics", "L4 Mimicry".
# Those titles are correct as internal vocabulary and are NOT rewritten: the kit
# body, the .txt source, the slug, and the on-page internal label all keep the
# original term. Only the <title>, the <h1>, and the search listing use a plain
# form, because those are the three surfaces a searcher or a crawler reads.
# Key = the topic title the parser produces, uppercased. Value = plain form.
# Add rows here rather than renaming topics at source.
PLAIN_TITLES = {
    # ---- disorder / order form pages
    "FORM -- DEMOCRACY-FAKE":
        "Why voting feels pointless — fake democracy",
    "FORM -- FAKE-SPECTRUM-CRAZY-FILTER":
        "Why both parties look the same — fake spectrum",
    "FORM -- CHARITY-LEGITIMACY-EXPORT":
        "When charity laundering buys legitimacy",
    "FORM -- CORP-GOD-METRIC":
        "When the company only serves the number",
    "FORM -- CREDENTIAL-EXPERTISE-FAKE":
        "Fake credentials and borrowed expertise",
    "FORM -- COUNTER-HYPERSTITION-PRAXIS":
        "Countering a made-up belief with action",
    "FORM -- DISTRIBUTED-CORRECTION-PATH":
        "How correction works without a central authority",
    "FORM -- EMPIRE-NODE":
        "Empire as a network of nodes",
    "FORM -- FARM-CLEAN-REMEDIATION":
        "Cleanup that only looks like remediation",
    "FORM -- HONEST-NON-DEMO":
        "Non-democratic systems that still self-correct",
    "FORM -- HYPERSTITION-DEFEAT-NARRATIVE":
        "How a defeat narrative protects the belief",
    "FORM -- KINGDOM-ILLUSION-GOD":
        "The kingdom built on an illusion",
    "FORM -- KINGDOM-RECIPROCAL-GOD":
        "Reciprocal order — the kingdom that gives back",
    "FORM -- LEGACY-MORAL-MONOCULTURE":
        "Moral monoculture inherited from the past",
    "FORM -- LIBERALISM-PARTIAL-STATE-RELIGION":
        "Liberalism as a partial state religion",
    "FORM -- OIL-SUBSTRATE-LOCK":
        "Oil dependency as a locked substrate",
    "FORM -- OPEN-RECORD-FALSIFICATION-CULTURE":
        "Open records that let a culture falsify itself",
    "FORM -- PROPORTIONAL-LIABILITY":
        "Proportional liability instead of blame-all",
    "FORM -- PUNDIT-VISIBILITY-CURSE":
        "Why pundits get worse as they get famous",
    "FORM -- RECIPROCAL-EXCHANGE":
        "Reciprocal exchange — real give and take",
    "FORM -- BB":
        "Appetite with a job description — the core extraction form",
    "FORM TAGS":
        "Tags used to label disorder and order forms",
    "FORM -- SHIELD PULL":
        "Pulling the shield — protection used as leverage",
    "FORM -- SOVEREIGN-AS-ORDER":
        "The sovereign as the source of order",
    "FORM -- STATE RELIGION":
        "State religion and enforced belief",
    "FORM -- TEAM-JERSEY-ORDER-COSTUME":
        "Team jersey order — costume instead of substance",
    "FORM -- TOTALITARIAN":
        "Totalitarian control — how it actually runs",
    "FORM -- WELFARE-FLOOR-IN-KIND":
        "Welfare paid in kind instead of cash",
    "FORM -- AEC-RATIFICATION-CHAIN":
        "How ratification chains manufacture consent",
    "FORM CATALOG":
        "Catalog of disorder and order forms",
    "BB-FUNCTION":
        "Appetite with a job description — the core extraction pattern",

    # ---- level / capacity codes
    "T9 IN POLITICS":
        "Why government never fixes anything",
    "T9 SOFT EXPOSURE METHODS":
        "How to name a limit without being destroyed",
    "T3 CALIBRATION":
        "Calibrating an unsure read",
    "L4 MIMICRY":
        "Institutions that only pretend to self-correct",
    "L4.5 CIVILIZATIONAL TRANSMISSION THRESHOLD":
        "Can a method survive past one generation",
    "L3.5 CONTACT TYPE MUST MATCH INSTRUMENT FRICTION AXIS":
        "Why the right help only works from the right angle",
    "C1 STARVED RECOVERY REQUIRES L3.5 CONTACT":
        "Why starving systems cannot recover alone",
    "PRE-RESTORATION C1 AUDIT PROCEDURE":
        "How to check a system before trying to fix it",
    "HONEST LIMITS T1-T9":
        "The nine honest limits on what a read can resolve",
    "SCIENCE T4 READ":
        "How to read a science news story",
    "SR/SP SUBSTRATE READ":
        "Reading the substrate a system runs on",
    "CAG + MI CORRECTION STACK":
        "The correction stack — capacity plus mechanism",
    "SUB-NATIONAL LEGITIMACY PRESERVATION + T9 COUNTER":
        "How local legitimacy survives central decay",

    # ---- pathos lane (sophist). These pages had zero search routes before
    # 2026-11-07 and titles built from internal register language. Plain titles
    # below; the pathos term stays visible as the pill.
    "CERTAINTY-CHASE FALL":
        "Why facts rarely change minds — the certainty chase",
    "CORRECTION WITHOUT CLINGING":
        "How to correct someone without humiliating them",
    "PEACE AS NON-RESISTANCE":
        "Why people resist being helped — non-resistance",
    "EMBODIED PRAXIS PATHOS":
        "Emotional labour and practice — feeling as work",
    "OFFICE AS BURDEN":
        "Why power feels like a burden, not a reward",
    "AMBIGUITY-CENTER AND FREEDOM":
        "Why freedom feels like anxiety",
    "MANIFEST-SALIENCE ASYMMETRY":
        "Why people believe made-up things",
    "FILE REGISTER AND FIREWALL":
        "Why being certain feels good — register and firewall",
    "LOGOS EXPORT":
        "What makes an argument persuasive",
    "DECOY PROGRESS AND STUPID VERSION":
        "Fake progress and the stupid version of an idea",
    "MORAL CUBE":
        "The moral cube — mapping a dispute",
    "DIVINE REGISTER DESK LADDER":
        "The divine register — how sacred language gets used",
    "ONTOLOGY-BRACKETED PHENOMENOLOGY VALUE":
        "Value without metaphysics — bracketing what exists",
    "EPISTEMIC BAND PATHOS ORIENT":
        "How sure can you be — the epistemic bands",

    # ---- project shorthand (AEC = applied extraction case series)
    "AEC FUNDAMENTALS AND SCALE APPLICATION":
        "Extraction cases — fundamentals and how it scales",
    "AEC DEMOCRACY VALUES AND INSTRUMENT LADDER":
        "Democracy values versus the instrument ladder",
    "AEC ANALYST STEELMAN NOTES":
        "Steelman notes on extraction cases",
    "AEC THREE-LEG NORMAL UNDERSTANDING":
        "The three-leg model of normal understanding",
    "BI/MI CO-FAILURE PATTERN":
        "When two correction routes fail together",
    "MI YOUTH LEMONADE STAND HB 6007":
        "Michigan lemonade stand law HB 6007",
}

KIT = [
    ("coherence_framework_v25_beginner", "Beginner", "read/beginner",
     "Vocabulary and kit map. Start here with no prior framework terms."),
    ("coherence_framework_v25_order_truth", "Order / Truth / Disorder", "read/order-truth",
     "The three bands: productive order, truth layers, and disorder forms."),
    ("coherence_framework_v25_theory", "Theory", "theory",
     "Foundation and procedure: coherence capacities, extraction, correction."),
    ("coherence_framework_v25_disorder_forms", "Disorder forms", "read/disorder-forms",
     "Library of disorder forms — named failure shapes to match against."),
    ("coherence_framework_v25_order_forms", "Order forms", "read/order-forms",
     "Library of order forms — named generative shapes."),
    ("coherence_framework_v25_applied", "Applied / glossary", "applied",
     "Politics, science, and full glossary applied readings."),
    ("coherence_framework_v25_applied_science", "Applied science", "read/applied-science",
     "Science and philosophy source tiers and replication readings."),
    ("coherence_framework_v25_applied_s6", "Section Six", "read/s6",
     "Politics in Action readings."),
    ("coherence_framework_v25_cases", "Case hub", "read/case-hub",
     "Redirect hub for the case libraries."),
    ("coherence_framework_v25_cases_real", "Real cases", "cases",
     "Real-world cases: people, events, institutions, history, science."),
    ("coherence_framework_v25_cases_fiction", "Fiction cases", "fiction",
     "Fiction cases: books, film, games, myth read through the same method."),
    ("coherence_framework_v25_sophist", "Sophist / pathos", "read/sophist",
     "Pathos mechanics and SUPPORT lane."),
    ("coherence_framework_v25_transmission", "Transmission", "read/transmission",
     "Deposit and optional paste protocol."),
    ("coherence_framework_v25_analyst_policy", "Analyst policy", "read/analyst-policy",
     "Declared analyst positions on all topics — bias-labeled, not framework finding."),
    ("cf_grep", "Line maps", "read/cf-grep",
     "Grep recipes and per-file line maps."),
]

# ---------------------------------------------------------------- parsing

SEP = re.compile(r"^-{8,}\s*$")
BANNER = re.compile(r"^={8,}")
CASE = re.compile(r"^\[CASE:([A-Za-z0-9_]+)\]\s*(.*)$")
CASE_ANY = re.compile(r"\[CASE:([A-Za-z0-9_]+)\]")
BRACKET_TAIL = re.compile(r"\s*\[.*$")
PIPE_TAIL = re.compile(r"\s*\|.*$")

ACRONYMS = {
    "us", "uk", "eu", "un", "ai", "ml", "ceo", "cfo", "cto", "fbi", "cia",
    "doj", "irs", "hud", "acs", "cdc", "fda", "epa", "ftc", "sec", "nato",
    "imf", "who", "wto", "gdp", "ce", "bce", "ad", "blm", "aipac", "adl",
    "mlk", "nra", "nyt", "bbc", "cnn", "pbs", "rcmp", "nyc", "la", "ca",
    "fl", "tx", "wv", "mi", "il", "nhs", "hk", "prc", "ccp", "ussr", "gdr",
    "icd", "ptsd", "rct", "crt", "pnas", "jama", "nejm", "llc", "inc",
    "mrna", "covid", "hiv", "sars", "tls", "ssl", "ca", "edny", "cbi",
    "lvt", "vat", "esg", "dei", "woke", "kkk", "irb", "phd", "lsi",
}


def clean_title(raw: str) -> str:
    t = raw.rstrip()
    t = BRACKET_TAIL.sub("", t)
    t = PIPE_TAIL.sub("", t)
    t = t.replace("**", "")
    t = t.strip().rstrip("-–—:, ").strip()
    return t


def is_continuation(line: str) -> bool:
    """True for wrapped tail-ends of a previous sentence, not a real heading."""
    s = line.strip()
    if not s:
        return True
    if s.startswith((">", "]", ")", ",", ";", ":", "-", "*", "|", "and ", "AND ")):
        return True
    if s.endswith("]"):
        return True
    letters = [c for c in s if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.62:
        return True
    return False


def title_from_id(name: str) -> str:
    words = []
    for w in name.split("_"):
        if not w:
            continue
        if w.isdigit():
            words.append(w)
            continue
        lw = w.lower()
        if lw in ACRONYMS:
            words.append(w.upper())
        elif any(c.isdigit() for c in w) and w.isupper():
            words.append(w)
        else:
            words.append(w[:1].upper() + w[1:].lower())
    out = " ".join(words)
    return out


def slugify(text: str, fallback: str = "item") -> str:
    s = text.lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    # Truncate BEFORE the final strip: slicing at 80 can land on a hyphen and
    # leave a trailing "-" in the slug, which 404s because the file on disk is
    # named without it [found 2026-11-06: 3 sitemap URLs ended mid-word].
    s = (s or fallback)[:80].strip("-")
    return s or fallback


PRIVATE_PATH = re.compile(
    r"(?:Personal|technical)/[A-Za-z0-9_.\-/]*")


def redact(text: str) -> str:
    """The public site should not list private-lane filenames. The kit names
    Personal/ and technical/ homes in navigation notes; show a neutral label
    instead of the internal layout. Flip SITE_REDACT to False to publish them."""
    if not SITE_REDACT:
        return text
    out = PRIVATE_PATH.sub("local lane", text)
    return out


def plain(body_lines):
    """Join body lines into one whitespace-collapsed string."""
    txt = " ".join(l.strip() for l in body_lines if l.strip())
    txt = re.sub(r"\*\*", "", txt)
    return re.sub(r"\s{2,}", " ", txt).strip()


def excerpt(body_lines, limit=155):
    txt = plain(body_lines)
    txt = re.sub(r"^\[[A-Z_]+:[^\]]*\]\s*", "", txt)
    txt = redact(txt)
    if len(txt) <= limit:
        return txt
    cut = txt[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:. ") + "…"


def parse_topics(lines):
    """Return [(title, body_lines)] using the kit grammar: a title block at
    column 0 may wrap across consecutive lines, then a dash rule, then body.
    Body stops at the next title block."""
    n = len(lines)
    blocks = []  # (start_idx, rule_idx, title)
    for i in range(1, n):
        if not SEP.match(lines[i].rstrip()) or BANNER.match(lines[i]):
            continue
        j = i - 1
        parts = []
        while j >= 0:
            ln = lines[j]
            if not ln or ln.startswith(" "):
                break
            if SEP.match(ln.rstrip()) or BANNER.match(ln) or CASE.match(ln):
                break
            parts.append(ln)
            j -= 1
        if not parts:
            # Wrapped-title case [added 2026-11-06]: the title block is a
            # column-0 heading whose continuation is one-space indented, the
            # same indent the body uses. 102 topics across five files had NO
            # page because the loop above stopped at that indented line.
            # Accept only when a col0 ALL-CAPS heading sits directly above.
            if j >= 0 and lines[j].startswith(" ") and lines[j].strip():
                k = j
                while k >= 0 and lines[k].startswith(" ") and lines[k].strip():
                    k -= 1
                if k >= 0 and lines[k].strip() and not SEP.match(lines[k].rstrip()) \
                        and not BANNER.match(lines[k]) and not CASE.match(lines[k]):
                    head = lines[k].strip()
                    # Caps test on the heading proper, before any [tag] tail.
                    stem = re.split(r"\s+\[", head)[0].strip()
                    letters = [c for c in stem if c.isalpha()]
                    if len(letters) >= 4 and \
                            sum(c.isupper() for c in letters) / len(letters) >= 0.85:
                        parts = [ln.strip() for ln in reversed(lines[k:i])
                                 if ln.strip()]
                        j = k - 1
            if not parts:
                # Blank-line-split title [added 2026-11-07]: analyst_policy has a
                # wrapped heading with an empty line inside it, so the scan above
                # stopped at the blank and captured only the tail ("]"). Scan up
                # past blanks to the column-0 heading that actually has letters.
                # Without this a page is published titled "]" at /topic-142.html.
                if j >= 0 and not lines[j].strip():
                    k = j
                    while k >= 0 and not lines[k].strip():
                        k -= 1
                    if k >= 0 and lines[k].strip() and not lines[k].startswith(" ") \
                            and not SEP.match(lines[k].rstrip()) \
                            and not BANNER.match(lines[k]) and not CASE.match(lines[k]):
                        parts = [lines[k].strip()]
                        j = k - 1
            if not parts:
                continue
        start = j + 1
        parts.reverse()
        title = " ".join(p.strip() for p in parts)
        blocks.append((start, i, title))

    out = []
    for idx, (start, rule, title) in enumerate(blocks):
        end = blocks[idx + 1][0] if idx + 1 < len(blocks) else n
        body = lines[rule + 1:end]
        # strip trailing banners / case anchors that belong to the next unit
        while body and (BANNER.match(body[-1]) or CASE.match(body[-1])):
            body.pop()
        out.append((title, body))
    return out


def trim_body(body):
    """Drop leading/trailing banners and SOURCE anchors so a case page never
    opens or closes on ==== / [SOURCE:] noise leaked from the previous case."""
    out = list(body)
    while out and (not out[-1].strip() or BANNER.match(out[-1])
                   or out[-1].lstrip().startswith("[SOURCE:")
                   or SEP.match(out[-1].rstrip())):
        out.pop()
    while out and (not out[0].strip()
                   or BANNER.match(out[0])
                   or out[0].lstrip().startswith("[SOURCE:")):
        out.pop(0)
    return out


def is_case_start(lines, i):
    """A [CASE:ID] line starts a case only when it is not a cross-reference.

    Some kit lines put an anchor at column 0 while merely *citing* a case:
    `[CASE:A] + [CASE:B] ... -> [SOURCE:X]` or `LIVE CASES: ...; [CASE:C].`
    Those must not split the case they sit inside.
    """
    m = CASE.match(lines[i])
    if not m:
        return False
    rest = m.group(2).strip()
    if "[CASE:" in rest or "[REF:" in rest:
        return False
    if rest.startswith(("+", ",", ";", "->", "and ")):
        return False
    if rest.endswith((".", ",", ";")):
        return False
    j = i - 1
    while j >= 0 and not lines[j].strip():
        j -= 1
    if j >= 0:
        prev = lines[j].strip()
        if not BANNER.match(lines[j]) and not set(prev) <= set("="):
            if prev.endswith((";", ":", ",")):
                return False
    return True


def parse_cases(lines):
    """Return [(case_id, body_lines)] split on genuine case starts. Duplicate
    ids keep the longest body, so a citation stub cannot win over the case."""
    out, cur, buf = [], None, []
    for i, line in enumerate(lines):
        if is_case_start(lines, i):
            if cur:
                out.append((cur, trim_body(buf)))
            cur, buf = CASE.match(line).group(1), []
        elif cur is not None:
            buf.append(line)
    if cur:
        out.append((cur, trim_body(buf)))

    seen, uniq = set(), []
    best = {}
    for cid, body in out:
        if len(body) > len(best.get(cid, [])):
            best[cid] = body
    for cid, _ in out:
        if cid in seen or cid not in best:
            continue
        seen.add(cid)
        uniq.append((cid, best[cid]))
    return uniq


def smart_case_title(t: str) -> str:
    """Title-case shouting headings while keeping acronyms and IDs intact."""
    if not t or not t.isupper():
        return t
    head, sep, tail = t.partition(":")
    if sep and len(head.split()) <= 4:
        out = [head.capitalize() + ":"]
        rest = tail.strip().split()
    else:
        out, rest = [], t.split()
    small = {"a", "an", "the", "of", "in", "on", "for", "vs", "and", "to",
             "at", "by", "from", "with", "as", "or", "per", "into"}
    for i, w in enumerate(rest):
        core = re.sub(r"[^A-Za-z0-9]", "", w)
        if core and core.lower() in ACRONYMS:
            out.append(w)
        elif any(c.isdigit() for c in w):
            out.append(w)
        elif i and w.lower() in small:
            out.append(w.lower())
        elif len(w) <= 3 and w.isupper():
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)


META_LINE = re.compile(r"^\s*(Type|Arc|Source|Source tier|Note|See|Grep|Primary_Q|PRIMARY_Q)\b")


STOP_START = ("AND ", "OR ", "BUT ", "WHAT ", "WHY ", "HOW ", "LANES,",
              "INSTRUMENTS ", "PRIVACY ", "SPLIT ", "SELF-INSERT ",
              "PUBLISHER,", "MAGNITUDE ")


def looks_broken(t: str) -> bool:
    """A prose title is broken when it starts mid-sentence or is a wrap tail."""
    if not t:
        return True
    if t[0] in "+,;)]":
        return True
    if t.startswith(STOP_START):
        return True
    if t.endswith(("->", ";", ":", ",", "—", "/", "&")):
        return True
    if t.count("(") != t.count(")") or t.count('"') % 2:
        return True
    first = t.split()[0].lower().strip("—-,")
    if first in {"and", "or", "but", "what", "why", "how", "when", "who",
                 "which", "that", "then", "it", "this", "these", "those"}:
        return True
    return False


def case_heading(case_id, body):
    """The heading is the whole first prose paragraph — titles wrap, so line
    one alone is usually a fragment. Bracketed metadata blocks ([PRIMARY_Q: ...])
    can also wrap, so skip to the closing bracket before reading prose."""
    n = len(body)
    i = 0
    while i < n:
        line = body[i]
        s = line.strip()
        if not s or s.startswith("*") or META_LINE.match(line):
            i += 1
            continue
        if s.startswith("["):
            # skip a possibly multi-line bracket block
            while i < n and body[i].strip() and not body[i].rstrip().endswith("]"):
                i += 1
            i += 1
            continue
        block = []
        while i < n:
            ln = body[i]
            if not ln.strip() or META_LINE.match(ln) or ln.strip().startswith("["):
                break
            block.append(ln.strip())
            i += 1
        joined = " ".join(block)
        if not joined:
            continue
        t = smart_case_title(clean_title(joined).replace(" -- ", " — "))
        if len(t) > 110:
            t = t[:110].rsplit(" ", 1)[0].rstrip(",;:/&-–— ")
        if len(t) >= 3 and not looks_broken(t):
            return t
    return title_from_id(case_id)


# ---------------------------------------------------------------- html

CSS = """
:root{--bg:#0f1115;--fg:#e6e8ee;--dim:#9aa3b2;--line:#242a36;--acc:#7fb2ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
 font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
header{border-bottom:1px solid var(--line);padding:14px 20px;position:sticky;top:0;
 background:rgba(15,17,21,.94);backdrop-filter:blur(8px);z-index:5}
header nav{max-width:900px;margin:0 auto;display:flex;flex-wrap:wrap;gap:14px;
 font-size:14px;align-items:center}
header .brand{font-weight:700;letter-spacing:.2px;margin-right:auto}
main{max-width:900px;margin:0 auto;padding:28px 20px 80px}
h1{font-size:26px;line-height:1.28;margin:0 0 6px}
h2{font-size:19px;margin:34px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.crumb{font-size:13px;color:var(--dim);margin-bottom:14px}
.meta{font-size:13px;color:var(--dim);margin-bottom:22px}
pre.kit{background:#141822;border:1px solid var(--line);border-radius:8px;padding:16px;
 white-space:pre-wrap;word-wrap:break-word;overflow-wrap:anywhere;font-size:13.5px;
 line-height:1.55;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
 margin:0 0 22px;color:#d7dbe4}
ul.list{list-style:none;padding:0;margin:0}
ul.list li{padding:9px 0;border-bottom:1px solid var(--line)}
ul.list li .k{font-size:12px;color:var(--dim);display:block}
footer{border-top:1px solid var(--line);color:var(--dim);font-size:13px;
 padding:22px 20px;text-align:center}
input.filter{width:100%;padding:11px 13px;border-radius:8px;border:1px solid var(--line);
 background:#141822;color:var(--fg);font-size:15px;margin-bottom:18px}
.pill{display:inline-block;font-size:11px;text-transform:uppercase;letter-spacing:.6px;
 border:1px solid var(--line);border-radius:99px;padding:2px 9px;color:var(--dim);margin-right:6px}
table{border-collapse:collapse;width:100%;font-size:14px;margin:0 0 20px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px}
""".strip()


SHORT_FILE = {
    "applied": "read/applied.html",
    "theory": "read/theory.html",
    "order_truth": "read/order-truth.html",
    "disorder_forms": "read/disorder-forms.html",
    "order_forms": "read/order-forms.html",
    "applied_s6": "read/applied-s6.html",
    "applied_science": "read/applied-science.html",
    "beginner": "read/beginner.html",
    "sophist": "read/sophist.html",
    "cases_real": "cases/index.html",
    "cases_fiction": "fiction/index.html",
}


TOPIC_PAGES: dict[str, str] = {}   # uppercase topic title -> page path


def resolve_topic_page(topic: str):
    """Map an INDEX/cross-ref topic phrase to its SPECIFIC topic page.

    Added 2026-11-06: rows used to always land on the whole-file page, so a
    search phrase like 'why rent keeps rising' opened 6,846 lines of `applied`
    instead of the HOUSING TENURE topic. Try, in order: exact title, title with
    trailing [..] sub-point refs stripped, then a unique prefix match.
    """
    t = topic.strip().strip(";,.").upper()
    if not t:
        return None
    if t in TOPIC_PAGES:
        return TOPIC_PAGES[t]
    # Drop sub-point selectors: 'STRUCTURE COUPLING [1][6]' -> 'STRUCTURE COUPLING'
    base = re.sub(r"(\s*\[[^\]]*\])+\s*$", "", t).strip()
    if base and base in TOPIC_PAGES:
        return TOPIC_PAGES[base]
    for cand in (t, base):
        if not cand or len(cand) < 8:
            continue
        pref = [p for k, p in TOPIC_PAGES.items() if k.startswith(cand)]
        if len(set(pref)) == 1:
            return pref[0]
    return None


def route_kit_refs(text: str) -> str:
    """text must already be HTML-escaped. Links `applied` TOPIC cross-refs and
    exact ALL-CAPS topic titles to their pages."""
    def repl(m):
        name, topic = m.group(1), m.group(2).strip()
        specific = resolve_topic_page(topic)
        if specific:
            return f'<a href="{href(specific)}">{name} — {topic}</a>'
        target = SHORT_FILE.get(name)
        if name == "analyst_policy":
            target = "read/analyst-policy.html"
            label = f"analyst policy — {topic}" if topic else "analyst policy"
            return f'<a href="{href(target)}">{label}</a>'
        label = f"{name} — {topic}" if topic else name
        if not target:
            return label
        return f'<a href="{href(target)}">{label}</a>'
    out = re.sub(r"`([a-z0-9_]+)`\s*([A-Z][A-Z0-9 /&:.\-]*[A-Z0-9])", repl, text)

    # single exact topic title -> its page
    stripped = out.strip().strip(";,")
    page_path = TOPIC_PAGES.get(stripped.upper())
    if page_path and "<a " not in out:
        return f'<a href="{href(page_path)}">{stripped}</a>'
    return out.replace("`", "")


def file_page(stem: str) -> str:
    """Stable human URL for a full-file reading page."""
    short = stem.replace("coherence_framework_v25_", "").replace("coherence_framework_", "")
    return f"read/{slugify(short, 'file')}.html"


def href(path: str) -> str:
    """Absolute-path URL for a site-relative path, honoring BASE.

    BASE="" is the root deploy; BASE="/Framework" is the subpath deploy.
    Empty path -> site root ("/" or "/Framework/")."""
    if not path:
        return f"{BASE}/"
    return f"{BASE}/{path}"


def page(path, title, desc, body, crumb="", jsonld=None, noindex=False):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    # Directory index pages are served at both "/dir/" and "/dir/index.html".
    # Point the canonical at the directory form so the pair does not compete as
    # duplicate URLs [fixed 2026-11-06 alongside the homepage].
    if path == "index.html":
        canonical = f"{ORIGIN}{href('')}"
    elif path.endswith("/index.html"):
        canonical = f"{ORIGIN}{href(path[:-len('/index.html')] + '/')}"
    else:
        canonical = f"{ORIGIN}{href(path)}"
    robots = ('<meta name="robots" content="noindex,follow">' if noindex
              else '<meta name="robots" content="index,follow">')
    ld = ""
    if jsonld:
        ld = ('<script type="application/ld+json">'
              + json.dumps(jsonld, ensure_ascii=False) + "</script>")
    # Bing verification tag, emitted only when BING_VERIFY is filled in. Kept on
    # a single line with no stray whitespace so it is copy-exact for the crawler.
    bing = (f'<meta name="msvalidate.01" content="{BING_VERIFY}" />\n'
            if BING_VERIFY else "")
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="google-site-verification" content="{GOOGLE_VERIFY}" />
{bing}<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
{robots}
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:image" content="{OG_IMAGE}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{html.escape(title)}">
<meta name="twitter:description" content="{html.escape(desc)}">
<link rel="icon" href="{FAVICON}">
<style>{CSS}</style>
{ld}
</head>
<body>
<header><nav>
<span class="brand"><a href="{href('')}">{SITE_NAME}</a></span>
<a href="{href('read/beginner.html')}">Start</a>
<a href="{href('problems/index.html')}">Problems</a>
<a href="{href('cases/index.html')}">Real cases</a>
<a href="{href('fiction/index.html')}">Fiction</a>
<a href="{href('topics/index.html')}">All topics</a>
<a href="{href('search.html')}">Search</a>
<a href="{href('versions.html')}">Versions</a>
</nav></header>
<main>
{crumb}
{body}
</main>
<footer>
<a href="{href('')}">{SITE_NAME}</a> — gift / forkable, CC0. Method travels; brand does not.
<br>
<a href="{REPO_URL}" rel="noopener">Source &amp; .txt kit on GitHub</a>
 · <a href="{REPO_URL}#readme" rel="noopener">README</a>
 · <a href="{REPO_URL}/blob/main/INDEX.md" rel="noopener">INDEX.md</a>
 · <a href="{href('versions.html')}">What is published</a>
</footer>
</body>
</html>
"""
    with open(full, "w", encoding="utf-8") as f:
        f.write(doc)


def source_lastmod(filename):
    """Real publication date for a source file, not filesystem mtime.

    See LASTMOD_FALLBACK for why mtime is unusable: a fresh checkout makes every
    file look modified today, and a sitemap that says "everything changed today"
    on every build trains the crawler to ignore lastmod entirely.

    `git log -1 --format=%cs -- <file>` returns the committer date of the last
    commit touching that file, which is what a reader would call "when this
    content last changed". CI checks out with full history by default, so this
    works there; a local build outside git falls back to mtime.
    """
    src = os.path.join(ROOT, filename)
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", src],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", out):
            return out
    except (OSError, subprocess.SubprocessError):
        pass
    if os.path.isfile(src):
        return datetime.fromtimestamp(
            os.path.getmtime(src), timezone.utc).date().isoformat()
    return LASTMOD_FALLBACK


def parse_problem_clusters(md_lines):
    """Parse INDEX.md '## Problem index by topic' into [(cluster name, [(phrase, target)])].

    Extracted from main() 2026-11-07 so the cluster map is available BEFORE case
    and topic pages are written. Cross-links from those pages back into the
    problem clusters are what make the clusters crawlable: each problem page had
    one real inbound link (the index), which is how a URL stays discovered but
    uncrawled for weeks.
    """
    start = None
    for i, l in enumerate(md_lines):
        if l.startswith("## Problem index by topic"):
            start = i
            break
    if not start:
        return []
    clusters, cur, rows = [], None, []
    for l in md_lines[start + 1:]:
        if l.startswith("## "):
            break
        m = re.match(r"^### (.+)$", l)
        if m:
            if cur:
                clusters.append((cur, rows))
            cur, rows = m.group(1).strip(), []
        elif cur and l.startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", l):
            cells = [c.strip() for c in l.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0].lower() not in ("search phrases",):
                rows.append((cells[0], cells[1]))
    if cur:
        clusters.append((cur, rows))
    return clusters


def index_for_problem(clusters, token):
    """Cluster slug that a case/topic token belongs to, or None.

    Matches against the ROUTING column (where the phrase lands), not the phrase
    column: the routing column names the kit home, which is what a case page or
    topic page can be identified by.
    """
    tok = token.lower()
    for name, rows in clusters:
        for _phrase, target in rows:
            if tok in target.lower():
                return slugify(name)
    return None


def crumb_html(parts):
    bits = []
    for label, path in parts:
        if path:
            bits.append(f'<a href="{href(path)}">{html.escape(label)}</a>')
        else:
            bits.append(html.escape(label))
    return '<div class="crumb">' + " / ".join(bits) + "</div>"


# ---------------------------------------------------------------- build

def reset_out():
    if os.path.isdir(OUT):
        for attempt in range(3):
            try:
                shutil.rmtree(OUT)
                break
            except OSError:
                time.sleep(0.4 * (attempt + 1))
        if os.path.isdir(OUT):
            shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT, exist_ok=True)


def main():
    reset_out()
    # copy the social card into the built site so og:image resolves
    og_src = os.path.join(ROOT, "og.png")
    if os.path.isfile(og_src):
        shutil.copy2(og_src, os.path.join(OUT, "og.png"))

    sitemap = []          # (path, lastmod)
    search_idx = []       # (title, path, kind)
    problems_nav = []

    # Parse INDEX.md clusters up front so case and topic pages can link back
    # into them. Previously the parse happened after those pages were already
    # written, so every problem cluster had exactly one inbound internal link.
    clusters = []
    index_path = os.path.join(ROOT, "INDEX.md")
    if os.path.isfile(index_path):
        with open(index_path, encoding="utf-8") as f:
            clusters = parse_problem_clusters(f.read().splitlines())
    cluster_slug = {name: slugify(name) for name, _ in clusters}
    cluster_title = {name: name for name, _ in clusters}
    slug_title = {slugify(name): name for name, _ in clusters}

    # Lastmod for the generated/navigation pages below, which have no kit source
    # of their own. Derived from INDEX.md, the file those pages are built from,
    # so their date moves only when their actual input moves.
    index_lastmod = source_lastmod("INDEX.md")

    all_topics = []       # (file label, dir, slug, title, path, desc)
    all_cases = []        # (kind, slug, title, path, desc, case_id)

    for stem, label, subdir, flabel in KIT:
        src = os.path.join(ROOT, stem + ".txt")
        if not os.path.isfile(src):
            print(f"  skip (missing): {stem}.txt")
            continue
        with open(src, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        mtime = source_lastmod(stem + ".txt")

        if subdir in ("cases", "fiction"):
            kind = "real case" if subdir == "cases" else "fiction case"
            entries = parse_cases(lines)
            used = set()
            items = []
            for cid, body in entries:
                if cid in ("BY_QUALITY",):
                    continue
                title = case_heading(cid, body)
                base_slug = slugify(title, cid.lower())
                slug = base_slug
                if slug in used:
                    slug = f"{base_slug}-{cid.lower()[:24]}"
                used.add(slug)
                p = f"{subdir}/{slug}.html"
                desc = excerpt(body, 300)
                if not desc:
                    desc = f"{title} — read through the Coherence Framework."
                text = "\n".join(body).strip("\n")
                jsonld = {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": title,
                    "description": desc[:300],
                    "url": f"{ORIGIN}{href(p)}",
                    "isPartOf": {"@type": "WebSite", "name": SITE_NAME,
                                 "url": f"{ORIGIN}{href('')}"},
                    "license": "https://creativecommons.org/publicdomain/zero/1.0/",
                }
                # Cross-link into the problem cluster this case appears in, so the
                # cluster is reachable from every page that mentions it instead of
                # only from /problems/index.html. One link per cluster, deduped.
                back = []
                seen_cl = set()
                for cid in CASE_ANY.findall(text):
                    cl = index_for_problem(clusters, cid)
                    if cl and cl not in seen_cl:
                        seen_cl.add(cl)
                        back.append(cl)
                    if len(back) >= 2:
                        break
                back_html = "".join(
                    f' · <a href="{href("problems/" + cl + ".html")}">'
                    f'{html.escape(slug_title.get(cl, cl))}</a>'
                    for cl in back
                )
                body_html = (
                    f'<h1>{html.escape(title)}</h1>'
                    f'<div class="meta"><span class="pill">{kind}</span>'
                    f'CASE ID <code>{html.escape(cid)}</code></div>'
                    f'<pre class="kit">{html.escape(redact(text))}</pre>'
                    f'<p><a href="{href(subdir + "/index.html")}">All {kind}s</a> · '
                    f'<a href="{href("read/beginner.html")}">Start here</a>'
                    + f'{back_html}'
                    + f'</p>'
                )
                crumb = crumb_html([("Home", ""),
                                    (kind + "s", subdir + "/index.html"),
                                    (title[:60], None)])
                page(p, f"{title} — {SITE_NAME}", desc, body_html, crumb, jsonld)
                sitemap.append((p, mtime))
                search_idx.append((title, p, kind))
                all_cases.append((subdir, slug, title, p, desc, cid))
                items.append((title, p, desc, cid))

            # index page for the library
            li = "".join(
                f'<li data-s="{html.escape((t + " " + c).lower())}">'
                f'<a href="{href(p_)}">{html.escape(t)}</a>'
                f'<span class="k">{html.escape(d[:120])}</span></li>'
                for t, p_, d, c in sorted(items, key=lambda x: x[0].lower())
            )
            idx_body = (
                f'<h1>{html.escape(label)}</h1>'
                f'<div class="meta">{len(items)} cases · '
                f'<a href="{href("read/beginner.html")}">how to read a case</a></div>'
                f'<input class="filter" placeholder="Filter by name, person, event…">'
                f'<ul class="list">{li}</ul>'
                "<script>const f=document.querySelector('.filter');"
                "f.addEventListener('input',()=>{const q=f.value.toLowerCase();"
                "document.querySelectorAll('ul.list li').forEach(li=>{"
                "li.style.display=li.dataset.s.includes(q)?'':'none'})});</script>"
            )
            page(f"{subdir}/index.html", f"{label} — {SITE_NAME}",
                 f"All {len(items)} {label.lower()} in the Coherence Framework, "
                 f"searchable by name.",
                 idx_body, crumb_html([("Home", ""), (label, None)]))
            sitemap.append((f"{subdir}/index.html", mtime))
            search_idx.append((label, f"{subdir}/index.html", "library"))
            continue

        # ---- topic-based files
        topics = parse_topics(lines)
        used = set()
        items = []
        for i, (raw_title, body) in enumerate(topics):
            title = smart_case_title(clean_title(raw_title)) or f"{label} {i+1}"
            # A title with no letters is not a title. Seen in analyst_policy: a
            # wrapped heading split by a BLANK line, whose tail was a lone "]"
            # directly above the dash rule -> page called "]" at /topic-142.html.
            # Scan up past blank and punctuation-only lines for the real column-0
            # heading. Stop at an indented line (that is body, not title) and at
            # any rule/banner/case anchor. A bare "]" is unsearchable and the
            # slug "topic-142" tells a crawler nothing either.
            if sum(c.isalpha() for c in title) < 3:
                first = next((ln.strip().lstrip("*# ").strip()
                              for ln in body if ln.strip()), "")
                if sum(c.isalpha() for c in first) >= 3:
                    title = first[:90]
                else:
                    title = f"{label} {i+1}"
            # Guard against a title that is only the surviving TAIL of a heading
            # split by a blank line: "... [analyst chat -- \n\n bias-labeled]".
            # The kit source has been repaired for the three cases found, but the
            # shape can recur, and a title starting lowercase with a dangling "]"
            # is unsalvageable in search. Strip the dead bracket and capitalise.
            if title.count("]") > title.count("["):
                title = title.replace("]", "").strip()
                if title and title[0].islower():
                    title = title[0].upper() + title[1:]
            base = slugify(title, f"topic-{i+1}")
            slug = base
            if slug in used:
                slug = f"{base}-{i+1}"
            used.add(slug)
            p = f"{subdir}/{slug}.html"
            # Internal title (title) drives the slug and stays as the kit wrote it.
            # Display title (shown) is the plain-language form where one exists.
            # Keeping them separate is the whole point: the URL and the kit
            # vocabulary do not change, only what a searcher reads.
            shown = PLAIN_TITLES.get(title.upper(), title)
            desc = excerpt(body, 300) or f"{shown} — {flabel}"
            text = "\n".join(body).strip("\n")
            jsonld = {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": shown,
                "description": desc[:300],
                "url": f"{ORIGIN}{href(p)}",
                "isPartOf": {"@type": "WebSite", "name": SITE_NAME,
                             "url": f"{ORIGIN}{href('')}"},
                "license": "https://creativecommons.org/publicdomain/zero/1.0/",
            }
            # The internal term is kept visible as a small label so the page still
            # teaches the kit's own name for the thing. Nothing is hidden from the
            # reader; the plain title is an addition, not a substitution.
            internal = ("" if shown == title else
                        f'<span class="pill">{html.escape(title)}</span>')
            # Cross-link into a problem cluster when this topic is a routing
            # target in INDEX.md. Same reason as case pages: without this the
            # cluster is reachable only from /problems/index.html.
            tcl = index_for_problem(clusters, title)
            tback = (f' · <a href="{href("problems/" + tcl + ".html")}">'
                     f'{html.escape(slug_title.get(tcl, tcl))}</a>' if tcl else "")
            body_html = (
                f'<h1>{html.escape(shown)}</h1>'
                f'<div class="meta">{internal}<span class="pill">{html.escape(label)}</span>'
                f'<a href="{href(file_page(stem))}">full file</a></div>'
                f'<pre class="kit">{html.escape(redact(text))}</pre>'
                f'<p><a href="{href(subdir + "/index.html")}">More {html.escape(label)}</a> · '
                f'<a href="{href("read/beginner.html")}">Start here</a>'
                + tback
                + f'</p>'
            )
            crumb = crumb_html([("Home", ""), (label, f"{subdir}/index.html"),
                                (shown[:60], None)])
            page(p, f"{shown} — {SITE_NAME}", desc, body_html, crumb, jsonld)
            sitemap.append((p, mtime))
            search_idx.append((shown, p, label.lower()))
            # Search/listing shows the plain form; the kit term is searchable too
            # via the existing site search payload (both are indexed below).
            all_topics.append((label, subdir, slug, shown, p, desc))
            TOPIC_PAGES.setdefault(title.upper(), p)
            if shown != title:
                TOPIC_PAGES.setdefault(shown.upper(), p)
            items.append((shown, p, desc))

        # Files with no parsed topics (case hub redirect, grep line maps) would
        # emit two empty pages: /dir/index.html and /dir.html, both showing a
        # "0 entries" list. Skip them rather than publishing thin duplicates
        # that compete with each other for the same query [2026-11-07].
        if not items:
            continue

        li = "".join(
            f'<li data-s="{html.escape(t.lower())}">'
            f'<a href="{href(p_)}">{html.escape(t)}</a>'
            f'<span class="k">{html.escape(d[:120])}</span></li>'
            for t, p_, d in items
        )
        idx_body = (
            f'<h1>{html.escape(label)}</h1>'
            f'<div class="meta">{len(items)} topics · {html.escape(flabel)}</div>'
            f'<input class="filter" placeholder="Filter topics…">'
            f'<ul class="list">{li}</ul>'
            "<script>const f=document.querySelector('.filter');"
            "f.addEventListener('input',()=>{const q=f.value.toLowerCase();"
            "document.querySelectorAll('ul.list li').forEach(li=>{"
            "li.style.display=li.dataset.s.includes(q)?'':'none'})});</script>"
        )
        page(f"{subdir}/index.html", f"{label} — {SITE_NAME}",
             f"{flabel} Indexed by topic, {len(items)} entries.",
             idx_body, crumb_html([("Home", ""), (label, None)]))
        sitemap.append((f"{subdir}/index.html", mtime))
        search_idx.append((label, f"{subdir}/index.html", "library"))

        # full-file reading page: ordered topic list
        fli = "".join(
            f'<li><a href="{href(p_)}">{html.escape(t)}</a>'
            f'<span class="k">{html.escape(d[:140])}</span></li>'
            for t, p_, d in items
        )
        page(file_page(stem), f"{label} — full contents — {SITE_NAME}",
             f"{flabel} All {len(items)} topics in reading order.",
             f'<h1>{html.escape(label)}</h1>'
             f'<div class="meta">{html.escape(flabel)} · {len(items)} topics</div>'
             f'<ul class="list">{fli}</ul>',
             crumb_html([("Home", ""), (label, None)]))
        sitemap.append((file_page(stem), mtime))
        search_idx.append((f"{label} — full contents", file_page(stem), "file"))

    # ---- problems (from INDEX.md clusters)
    # `clusters` was parsed at the top of main() so case and topic pages could
    # already cross-link into them.
    case_lookup = {c[5]: c[3] for c in all_cases if c[0] == "cases"}
    case_title = {c[5]: c[2] for c in all_cases if c[0] == "cases"}

    for name, rows in clusters:
        slug = slugify(name)
        problems_nav.append((name, f"problems/{slug}.html", len(rows)))
        body_rows = []
        for phrase, target in rows:
            links = []
            for cid in CASE_ANY.findall(target):
                if cid in case_lookup:
                    links.append((case_title.get(cid, title_from_id(cid)),
                                  case_lookup[cid]))
                else:
                    links.append((title_from_id(cid), None))
            cleaned = CASE_ANY.sub("", target).replace("``", "").strip(" ;,·—-")
            body_rows.append((phrase, links, cleaned))
        trs = []
        for phrase, links, cleaned in body_rows:
            tgt = " · ".join(
                (f'<a href="{href(p_)}">{html.escape(t)}</a>' if p_ else html.escape(t))
                for t, p_ in links
            )
            if cleaned:
                cleaned_html = route_kit_refs(html.escape(cleaned))
                tgt = (tgt + " — " if tgt else "") + cleaned_html
            trs.append(
                f"<tr><td>{html.escape(phrase)}</td><td>{tgt}</td></tr>"
            )
        body = (
            f'<h1>{html.escape(name)}</h1>'
            f'<div class="meta">Search phrases that route into the framework · '
            f'{len(body_rows)} entries · '
            f'<a href="{href("problems/index.html")}">all problem clusters</a></div>'
            f'<table><thead><tr><th>What someone searches</th>'
            f'<th>Where it lands</th></tr></thead><tbody>{"".join(trs)}</tbody></table>'
        )
        page(f"problems/{slug}.html", f"{name} — {SITE_NAME}",
             f"Coherence Framework readings for {name.lower()}: "
             f"{', '.join(p for p, _, _ in body_rows[:4])}.",
             body, crumb_html([("Home", ""), ("Problems", "problems/index.html"),
                               (name, None)]))
        sitemap.append((f"problems/{slug}.html", index_lastmod))

    pli = "".join(
        f'<li><a href="{href(p_)}">{html.escape(n)}</a>'
        f'<span class="k">{c} search phrases</span></li>'
        for n, p_, c in problems_nav
    )
    page("problems/index.html", f"Problems — {SITE_NAME}",
         "Start from the problem you are trying to name, not from framework vocabulary.",
         f'<h1>Start from the problem</h1>'
         f'<div class="meta">People search problems, names, and events — '
         f'not "Coherence Framework." Each cluster maps the phrasings someone '
         f'actually types to a reading.</div><ul class="list">{pli}</ul>',
         crumb_html([("Home", ""), ("Problems", None)]))
    sitemap.append(("problems/index.html", index_lastmod))
    search_idx.append(("Problems", "problems/index.html", "index"))

    # ---- all-topics index
    # Full-file reading pages get their inbound link here. Previously the only
    # link to a file page came from one of its own topic pages, so files with no
    # topics (cf_grep, the case hub) were orphaned: in the sitemap, unlinked, and
    # therefore barely crawlable. /topics/ is linked from the nav on every page,
    # so this makes every file page reachable in one hop from anywhere.
    #
    # Case libraries are the exception: they have no topics, so they never emit a
    # file_page() and file_page("..._cases_real") -> read/cases-real.html does not
    # exist. Their real landing page is the per-library index built in the KIT
    # loop. Link that instead of a 404 [bug found 2026-11-07].
    _flinks = []
    for _stem, _label, _subdir, _flabel in KIT:
        if not os.path.isfile(os.path.join(ROOT, _stem + ".txt")):
            continue
        if _subdir in ("cases", "fiction"):
            _flinks.append(
                f'<li><a href="{href(_subdir + "/index.html")}">'
                f'{html.escape(_label)}</a>'
                f'<span class="k">all cases · searchable by name</span></li>')
        else:
            # Only link a full-file page that the build actually produced. Files
            # with no parsed topics are skipped above and have no such page.
            if not os.path.isfile(os.path.join(OUT, file_page(_stem))):
                continue
            _flinks.append(
                f'<li><a href="{href(file_page(_stem))}">{html.escape(_label)}</a>'
                f'<span class="k">full file · every topic in reading order</span></li>')
    file_links = "".join(_flinks)
    tli = "".join(
        f'<li data-s="{html.escape((t + " " + lab).lower())}">'
        f'<a href="{href(p_)}">{html.escape(t)}</a>'
        f'<span class="k">{html.escape(lab)} — {html.escape(d[:110])}</span></li>'
        for lab, sd, sl, t, p_, d in sorted(all_topics, key=lambda x: x[3].lower())
    )
    page("topics/index.html", f"All topics — {SITE_NAME}",
         f"Every topic in the kit, {len(all_topics)} entries, one page each.",
         f'<h1>All topics</h1>'
         f'<div class="meta">{len(all_topics)} topic pages · '
         f'{len(all_cases)} case pages</div>'
         f'<input class="filter" placeholder="Filter {len(all_topics)} topics…">'
         f'<ul class="list">{tli}</ul>'
         f'<h2>Full files</h2>'
         f'<div class="meta">Each kit .txt as one readable page.</div>'
         f'<ul class="list">{file_links}</ul>'
         "<script>const f=document.querySelector('.filter');"
         "f.addEventListener('input',()=>{const q=f.value.toLowerCase();"
         "document.querySelectorAll('ul.list li').forEach(li=>{"
         "li.style.display=li.dataset.s.includes(q)?'':'none'})});</script>",
         crumb_html([("Home", ""), ("All topics", None)]))
    sitemap.append(("topics/index.html", index_lastmod))
    search_idx.append(("All topics", "topics/index.html", "index"))

    # ---- site search
    payload = json.dumps([[t, p_, k] for t, p_, k in search_idx], ensure_ascii=False)
    page("search.html", f"Search — {SITE_NAME}",
         "Search every topic and case in the Coherence Framework.",
         f'<h1>Search</h1>'
         f'<div class="meta">{len(search_idx)} pages</div>'
         f'<input class="filter" id="q" placeholder="Type a topic, person, event…">'
         f'<ul class="list" id="r"></ul>'
         f"<script>const D={payload};const q=document.getElementById('q');"
         "const r=document.getElementById('r');"
         "function draw(){const s=q.value.toLowerCase().trim();"
         "const hits=s?D.filter(x=>x[0].toLowerCase().includes(s)).slice(0,80):D.slice(0,60);"
         "r.innerHTML=hits.map(x=>`<li><a href=\"" + BASE + "/${x[1]}\">${x[0]}</a>"
         "<span class=\"k\">${x[2]}</span></li>`).join('');}q.addEventListener('input',draw);draw();"
         "</script>",
         crumb_html([("Home", ""), ("Search", None)]), noindex=True)
    # noindex pages are deliberately NOT sitemapped — a sitemap entry for a
    # noindex URL is a contradiction Search Console reports as an error.

    # ---- VERSIONS.md -> versions.html
    vers_body = "<h1>Versions</h1>"
    vmd = os.path.join(ROOT, "VERSIONS.md")
    if os.path.isfile(vmd):
        with open(vmd, encoding="utf-8") as f:
            raw = f.read()
        # tiny markdown subset: headings, tables, links, bold, code, fences
        out, in_table, table_rows = [], False, []
        fence, fence_lines = False, []

        def inline(s):
            s = html.escape(s)
            s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
            s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
            s = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<em>\1</em>", s)
            s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
            # link kit filenames to their live site pages
            s = re.sub(
                r"(?<![\w/`>])((?:coherence_framework_v25_[a-z0-9_]+|cf_grep)\.txt)",
                r'<a href="' + BASE + r'/read/\1">\1</a>', s)
            return redact(s)

        for line in raw.splitlines():
            if line.startswith("```"):
                fence = not fence
                continue
            if fence:
                fence_lines.append(line)
                continue
            if fence_lines:
                out.append('<pre class="kit">'
                           + html.escape(redact("\n".join(fence_lines)))
                           + "</pre>")
                fence_lines = []
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if re.match(r"^[\s\-:|]+$", line.strip().strip("|")):
                    continue
                table_rows.append(cells)
                in_table = True
                continue
            if in_table:
                head = table_rows[0]
                bodyr = table_rows[1:]
                t = "<table><thead><tr>" + "".join(
                    f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                t += "".join(
                    "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>"
                    for row in bodyr) + "</tbody></table>"
                out.append(t)
                in_table, table_rows = False, []
            if line.startswith("# "):
                continue  # h1 already emitted
            if re.match(r"^-{3,}$", line.strip()):
                continue  # horizontal rule
            if line.startswith("### "):
                out.append(f"<h3>{inline(line[4:])}</h3>")
            elif line.startswith("## "):
                out.append(f"<h2>{inline(line[3:])}</h2>")
            elif line.startswith("- "):
                out.append(f"<p>· {inline(line[2:])}</p>")
            elif re.match(r"^\d+\.\s", line):
                out.append(f"<p>{inline(line)}</p>")
            elif line.strip():
                out.append(f"<p>{inline(line)}</p>")
        if in_table and table_rows:
            head, bodyr = table_rows[0], table_rows[1:]
            t = "<table><thead><tr>" + "".join(
                f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row)
                         + "</tr>" for row in bodyr) + "</tbody></table>"
            out.append(t)
        vers_body += (
            '<div class="meta">What the public repo contains and how it differs '
            'from this working copy. Manual publish only.</div>'
            + "".join(out))
        page("versions.html", f"Versions — {SITE_NAME}",
             "What the published Coherence Framework contains, how it differs "
             "from the current working copy, and what is never published.",
             vers_body, crumb_html([("Home", ""), ("Versions", None)]))
        sitemap.append(("versions.html", source_lastmod("VERSIONS.md")))
        search_idx.append(("Versions", "versions.html", "index"))

    # ---- home
    stats = (
        f"{len(all_topics)} topic pages · {len(all_cases)} case pages · "
        f"{len(problems_nav)} problem clusters"
    )
    home = f"""
<h1>Coherence Framework</h1>
<div class="meta">A reading system for <strong>true vs false coherence</strong> — whether a
person, institution, or design generates more than it consumes, or consumes while
looking like it generates.</div>
<p>Not a political party, cult, or vibes checklist. Gift / forkable — use, remix, and fork
without permission.</p>
<h2>Start here</h2>
<ul class="list">
<li><a href="{href('read/beginner.html')}">Beginner — vocabulary and kit map</a>
<span class="k">No prior framework terms assumed.</span></li>
<li><a href="{href('read/order-truth.html')}">Order / Truth / Disorder</a>
<span class="k">The three bands that everything else depends on.</span></li>
<li><a href="{href('problems/index.html')}">Start from the problem</a>
<span class="k">Search phrases someone actually types, mapped to a reading.</span></li>
</ul>
<h2>Browse</h2>
<ul class="list">
<li><a href="{href('cases/index.html')}">Real cases</a><span class="k">People, events, institutions, history, science.</span></li>
<li><a href="{href('fiction/index.html')}">Fiction cases</a><span class="k">Books, film, games, myth.</span></li>
<li><a href="{href('topics/index.html')}">All topics</a><span class="k">{stats}</span></li>
<li><a href="{href('search.html')}">Search</a><span class="k">Every page.</span></li>
<li><a href="{href('versions.html')}">Versions</a><span class="k">What is published, and what never is.</span></li>
</ul>
<h2>What this is for</h2>
<p>It scores <strong>capacities</strong> [can it correct? is the meter honest?] and names
<strong>extraction mechanisms</strong> [tricks that make prey help consume itself].
The test is output, not stated values: does the thing generate more than it consumes,
and can it be corrected by evidence?</p>
"""
    page("index.html", f"{SITE_NAME} — true vs false coherence",
         "A reading system for true vs false coherence: does a person, institution, "
         "or design generate more than it consumes, or consume while looking like it "
         "generates? Problem-indexed case library, CC0.",
         home)
    sitemap.append(("", index_lastmod))
    search_idx.append(("Home", "index.html", "index"))

    # ---- 404, robots, sitemap, .nojekyll
    # Legacy-path rescue. The site moved from the project path /Framework/ to the
    # user-site root when the repo was renamed Framework -> poehl60.github.io.
    # Every old /Framework/... URL now hard-404s, and the repo README still links
    # to /Framework/ , so real readers land here. There is no server on GitHub
    # Pages, so the only redirect available is client-side: map the known old
    # prefix onto the matching root path and replace the history entry so the
    # 404 URL does not linger in the back button.
    # This runs on the 404 page only; it costs nothing on a normal page load.
    legacy_redirect = f"""
<script>
(function () {{
  var p = location.pathname, old = '/framework';
  var lp = p.toLowerCase();
  if (lp === old || lp.indexOf(old + '/') === 0) {{
    var rest = p.slice(old.length) || '/';
    var q = location.search + location.hash;
    location.replace('{ORIGIN}' + rest + q);
  }}
}})();
</script>"""
    page("404.html", f"Not found — {SITE_NAME}",
         "Page not found.",
         f'<h1>Not found</h1><p>That page does not exist. '
         f'<a href="{href("search.html")}">Search</a> or '
         f'<a href="{href("")}">start over</a>.</p>'
         + legacy_redirect,
         noindex=True)

    with open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n\n"
                f"Sitemap: {ORIGIN}{href('sitemap.xml')}\n")
    with open(os.path.join(OUT, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")

    lines_xml = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    seen = set()
    seen_locs = []        # (absolute url, lastmod) — input for the IndexNow manifest
    for p, lm in sitemap:
        if p in seen:
            continue
        seen.add(p)
        # Directory index pages are canonically the directory form (see page()).
        # Emitting "/dir/index.html" here while the page canonicals to "/dir/"
        # is a contradiction Search Console reports as an error.
        # Guard the "/" so a file legitimately named "...-index.html" (a slug
        # that ends in the word "index") is not mangled into a trailing hyphen
        # with no matching file on disk [bug found 2026-11-06: 3 dead URLs].
        loc = p
        if p == "index.html":
            loc = ""
        elif p.endswith("/index.html"):
            loc = p[:-len("index.html")]
        lines_xml.append(
            f"<url><loc>{ORIGIN}{href(loc)}</loc>"
            f"<lastmod>{lm}</lastmod></url>")
        seen_locs.append((f"{ORIGIN}{href(loc)}", lm))
    lines_xml.append("</urlset>")
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines_xml))

    # ---- IndexNow key file
    # Must sit at the site root and must contain nothing but the key. Bing and
    # the other IndexNow engines fetch this once to prove the submitter controls
    # the host. Written by the build because docs/ is gitignored and regenerated,
    # so a hand-uploaded copy would 404 after the next deploy.
    if INDEXNOW_KEY:
        if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", INDEXNOW_KEY):
            raise SystemExit(
                f"INDEXNOW_KEY is malformed: {INDEXNOW_KEY!r}. "
                "IndexNow requires 8-128 chars of a-z, A-Z, 0-9, and dashes.")
        with open(os.path.join(OUT, f"{INDEXNOW_KEY}.txt"), "w",
                  encoding="utf-8") as f:
            f.write(INDEXNOW_KEY)

    # ---- lastmod manifest for incremental IndexNow pings
    # One line per URL: "<lastmod> <url>". The deploy workflow downloads the
    # previous deployment's copy, diffs it against this one, and pings IndexNow
    # with only the URLs whose date actually moved. Without this the workflow
    # would either ping all 1851 URLs on every push (wasteful, and IndexNow's own
    # guidance is to send only changed URLs) or ping nothing (no benefit).
    # Underscore prefix keeps it out of the sitemap and off the 404 path.
    with open(os.path.join(OUT, "_indexnow.txt"), "w", encoding="utf-8") as f:
        for url, lm in sorted(seen_locs, key=lambda x: x[1]):
            f.write(f"{lm} {url}\n")

    n_files = sum(len(fs) for _, _, fs in os.walk(OUT))
    print(f"built {n_files} files into docs/")
    print(f"  topic pages: {len(all_topics)}")
    print(f"  case pages:  {len(all_cases)}")
    print(f"  problems:    {len(problems_nav)}")
    print(f"  sitemap urls:{len(seen)}")


if __name__ == "__main__":
    main()
