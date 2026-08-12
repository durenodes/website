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

## Adding a network

Add one entry to `CHAINS` in `_build.py`. That entry builds the network card, the status row,
the hero counts and — if it carries a `keplr` link — the delegation card.

This used to take edits in four separate places, which is exactly why Cosmos Hub mainnet was
live for a day without appearing anywhere on the page. One place to add means one place to
forget, and there isn't one.

`cap` is the number of validators that actually take part in consensus: 100 on Celestia,
180 on the Cosmos Hub even though 200 are bonded. `RANK` is shown against that number, not
against the bonded count, because slipping past it is what costs rewards.

## Figures

Every number on this page comes from on-chain state and is meant to be verifiable.
**If a value here disagrees with the chain, the chain is right** — please open an issue.

Nothing is filled in with plausible-looking placeholder data. Where we don't have a figure
yet, the page says so. `_build.py` refuses to write any file if the on-chain read fails —
a skipped deploy is better than stale numbers presented as current.

## Incidents

`INCIDENTS` in `_build.py` — one card each, for outages where signing actually stopped.
Entries are appended, never removed.

That bar is the whole rule. A node is not down because a single signature was late, and a log
that records every blip stops being read. If a cause was never identified, the page says so
rather than guessing.

## Postmortems

`POSTMORTEMS` in `_build.py` builds `/incidents/<slug>/` and `/ko/incidents/<slug>/` from the
same shell as the landing page, and links itself from the matching incident card by date.

Keep internal hostnames, IP addresses and server paths out of these. The internal record lives
in the parent repository's `docs/incidents.md`; this is the public version of it.
