# retell-viz

Interactive visualizations of the Retell marketing-site funnel — anonymized
aggregate data only (counts and rates; no identities, no emails, no per-visitor
rows).

Live at **https://caio-camargo.github.io/retell-viz/**

| Page | What it is |
|---|---|
| [`index.html`](index.html) | Landing page |
| [`funnel-at-a-glance.html`](funnel-at-a-glance.html) | One-page funnel briefing (all-hands, Aug 14 2026) |
| [`journey/sankey-lakehouse.html`](journey/sankey-lakehouse.html) | Warehouse funnel, 235k sessions |
| [`journey/sankey-all.html`](journey/sankey-all.html) | Identified-traffic funnel, 22.8k sessions |
| [`journey/sankey.html`](journey/sankey.html) | ICP-lead funnel with booking outcomes |
| [`journey/index.html`](journey/index.html) | ICP journey gravity graph (absorbing Markov chain) |
| [`journey/index-lakehouse.html`](journey/index-lakehouse.html) | Warehouse gravity graph |

The journey pages were originally built in
[caio-camargo/explorations](https://github.com/caio-camargo/explorations) as the
`journey-markov` exploration and migrated here 2026-08-14. Their method notes live
in [`journey/NOTES.md`](journey/NOTES.md). The `journey/build_data_*.py` scripts
regenerate the embedded aggregates from private source data (never committed
here); they inject between `DATA-START`/`DATA-END` markers in each page.
