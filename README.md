# durenodes.com

Landing page for **DURE** (doo-reh) — a validator and public infrastructure operator.

DURE is named after 두레, a Korean village labor commons. Work together, keep the ledger,
settle by days worked. We run the same way: each chain's minimum commission, costs published
alongside fee income, and incident records we don't delete.

## Structure

| Path | |
|---|---|
| `index.html` | English (default, canonical) |
| `ko/index.html` | Korean |
| `robots.txt`, `sitemap.xml` | Search engine directives |
| `og.png` | Social share card (1200×630) |
| `favicon.png`, `icon-256.png` | Brand mark |
| `_style.css`, `_build.py` | **Sources.** Not served — see below |

## Editing

**Do not edit the HTML files directly. They are generated and will be overwritten.**

Copy is in `_build.py` (the `CONTENT` dict), styles are in `_style.css`. Both languages come
from the same source so they cannot drift apart.

```sh
python3 _build.py
```

This regenerates `index.html`, `ko/index.html`, `robots.txt` and `sitemap.xml`. No build step
runs at deploy time — the output is committed and Cloudflare Pages serves it as-is.

No JavaScript, no framework, no dependencies beyond Google Fonts.

## Language

English is the default and the canonical URL. Visitors from Korea are redirected to `/ko/`
by a Cloudflare rule; the switcher in the header overrides it either way. `hreflang` tags
tell search engines the two pages are translations of each other.

## Figures

Every number on this page comes from on-chain state and is meant to be verifiable.
**If a value here disagrees with the chain, the chain is right** — please open an issue.

Nothing is filled in with plausible-looking placeholder data. Where we don't have a figure
yet, the page says so.

---

함께 짓고, 낸 만큼 나눈다 · Shared work, settled fairly
