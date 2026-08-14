# Journey Gravity — absorbing Markov chain over real site journeys
**Version**: 2.6.0
**Author**: Caio Camargo + Claude
**Date Created**: 2026-08-12
**Last Updated**: 2026-08-12
**Purpose**: Model + visualization of where a website's pages pull their visitors — toward a booked meeting or toward leaving
**Status**: Active

---

## The idea

Take real page-by-page journeys of ICP leads across three properties (marketing site,
product dashboard, docs), fit an **absorbing Markov chain** over them, and ask each page a
question no per-page analytics view answers: *if a visitor is standing here, what is the
probability their story ends in a booked meeting?* We call that the page's **gravity**.

This is the first utilitarian exploration — the data is real work data, the math is the fun.

## Data and anonymization contract

- Source: `icp-journeys-full-pages.csv` (page-level journeys: 53 visitors, 245 sessions,
  1,199 pageviews, 2026-06-01 → 2026-07-20) joined with `icp-journeys-full.csv`
  (per-visitor outcome: Meeting Scheduled / Cancelled / Not Scheduled), both in a private
  workspace outside this repo (`JOURNEY_DATA_DIR` — see `build_data.py`).
  **Neither file is in this repo.**
- These CSVs are **point-in-time exports**; since 2026-08-12 the upstream source of truth
  is the company's Databricks lakehouse, and refreshes should be regenerated from there
  (the source→table mapping is documented in the private workspace, not here). The chart
  header always shows the window the current data actually covers.
- [`build_data.py`](build_data.py) reads them and injects an aggregate JSON into
  [`index.html`](index.html) between `/*DATA-START*/ … /*DATA-END*/` markers. The aggregate
  contains **page paths, transition counts, dwell sums, and fate-labeled counts only** — no
  emails, no identities. Dashboard agent URLs are collapsed to `…/agents/:agent`.
- The build script PII-scans were done at build time (regex for emails and `agent_…` ids —
  clean). Anything committed here is aggregate-only by construction.
- **Vendor and instrumentation names stay out of this repo.** Data sources are described by
  what they are ("identified-visitor exports", "the scheduler"), never by which product
  produces them — instrumentation detail is internal by the domain brief's rule, and naming
  a vendor also dates the work. Scrubbed repo-wide 2026-08-12 after one slipped in.

## The model

**States.** Every page is a transient state. Two absorbing states: `BOOKED` and `LOST`.
A virtual `START` state feeds session entry pages.

**Transitions.** Consecutive pageviews within a session are counted as transitions. What a
session's *last page* absorbs into is a modeling choice, and v1.3 exposes it as a toggle
(this was born from Caio spotting that v1.2 drew BOOKED edges from pages you cannot book on):

- **Visitor fate** (the original): every session end absorbs into the visitor's eventual
  outcome — `BOOKED` if they ever scheduled, `LOST` otherwise. All of a booked visitor's
  sessions end in `BOOKED`, even early exploratory ones. Answers *"is this page's visitor
  the booking kind?"*
- **Booking event** (default since v1.3, the strict semantics): booking mechanically happens
  only at the gate, so only gate session-ends by scheduled visitors absorb into `BOOKED`;
  every other session end — including a booked visitor's other sessions — is a neutral
  `EXIT`. Answers *"does this walk reach the form and book?"* In this mode the map shows a
  single green edge, gate → BOOKED, which is the truth of the mechanism.

`BOOKED` means **meeting scheduled**, nothing stronger — held-rate is not measured in the
source data. `Cancelled` visitors count as booked (the scheduling event happened); in the
current 53-visitor cohort this reclassification changes nothing (no `Cancelled` visitors
present), but the rule is in `build_data.py` for future refreshes.

**Smoothing.** Prior strength κ adds κ pseudo-transitions from every page to the absorbing
states, split by the global base rate. κ=0 trusts a 2-visit page's luck completely; large κ
shrinks everything to base. Default κ=2. The slider exists because with n=53 visitors the
interesting question is *which rankings survive shrinkage*.

**Quantities** (all solved by Jacobi iteration in the page, live under the κ slider):

- Gravity: `g = b + Q·g`, where `Q` is the transient transition matrix and `b` the direct
  probability of absorbing into `BOOKED`.
- Expected remaining pageviews: `t = 1 + Q·t`.
- Expected remaining time: `T = w + Q·T`, with `w` = mean dwell per visit (semi-Markov:
  each state has a holding time).

**Self-loops** (page reloads) are kept in the counts but the display hides them by default —
they provably don't change absorption probabilities, only expected times. The toggle's
tooltip states this; it's the kind of fact the model teaches for free.

## What it showed (κ=2, min 8 visits)

Base rate: **75.1%** session-weighted (81% visitor-level, 43/53 — booked visitors browse
more sessions, which drags the session-weighted base down). Model start-of-session
prediction: 74.5% — consistent with base, a sanity check that the chain is coherent.

**High gravity — the road to booked (~+6–8 pp over base):**

| Page | Gravity | Reading |
|---|---|---|
| `docs…/reliability/debug-call-disconnect` | 83% | Debugging a real call = already invested |
| `dashboard…/call-history` | 83% | Inspecting real calls — the product is in use |
| `dashboard…/knowledgeBase` | 81% | Building an actual agent |
| `dashboard…/live-monitoring` | 81% | Watching production traffic |
| `/enterprise-plan` | 80% | Self-qualifying on the marketing side |

**Low gravity — attention sinks (~−2–13 pp under base):**

| Page | Gravity | Reading |
|---|---|---|
| `dashboard…/billing` | 62% | Cost-checking without commitment |
| `dashboard…/` (root) | 63% | Landed in the product but going nowhere |
| `/` (homepage) | 71% | Lingering on marketing ≠ intent |
| `dashboard…/analytics` | 72% | — |
| `/pricing` | 73% | High-traffic, slightly below base |

The single sentence the picture earns: **depth of product engagement predicts booking far
better than marketing-page attention — and the billing page is where intent goes to die.**
Directionally unsurprising; the value is that it's now *quantified per page* with a model
whose knobs are visible, rather than a hunch.

### The denominator was the story all along (v2.2)

The Sankey's refinements came back to the graph via
[`docs/research/journey-viz-refinements.md`](https://github.com/caio-camargo/explorations/blob/main/docs/research/journey-viz-refinements.md).
The consequential one was **the inclusion rule**: event-mode gravity was being computed over
*all* 245 sessions, including 132 that never leave the product and 16 docs-only ones. Those
sessions cannot reach the form — counting them as non-bookings measures the wrong thing.

Restricted to the 97 sessions that touch the marketing site at least once, the base rate goes
from **16.7% → 42.3%**, and every page's gravity moves with it (the gate reads 69%, pricing
48%, homepage 44%). Same data, same model, honest denominator: the funnel is far less leaky
than the first reading suggested. Both denominators ship as a toggle with the exclusion counts
printed on the page — a denominator is a modeling decision and should be visible, not implied.

Three further transfers changed what the picture *claims*:

- **`→ APP` is now its own absorbing state.** Ending a session inside the product is not
  "lost" — it's a handoff. 15 of the 97 site-touching sessions end that way (155 of 245 in
  all-sessions scope, which is exactly why that denominator drowned everything). The model
  still counts them as non-bookings; the chart no longer calls them failures.
- **`START` became the origin channels.** An "every session begins" node carries zero
  information; self-reported origin carries some. chatgpt (26), other/unlisted (24),
  google (23), app dashboard (14), recommendation (10) — each with its own predicted
  P(booked), all within a few points of each other, and each tooltip carrying the
  under-attribution caveat.
- **Outcome nodes are sized by what they absorb**, with counts and shares printed beneath.
  Their radius is now the outcome distribution — previously they were fixed-size chrome.

### The two lenses disagree — and that's the finding (v1.3)

Switching to booking-event semantics **inverts the ranking**. Under event mode (base 16.7%
of sessions book): `/pricing` 38% and the homepage 34% lead, while the whole dashboard drops
to ~5–7% (call-history 5.0%, agent builder 5.8%). Under fate mode those same dashboard pages
are the top predictors.

Read together, they describe the company's actual product-led motion (corroborated by an
internal demand-gen readout, qualitatively): there is a **marketing lane** (homepage →
pricing → gate) where booking *happens*, and a **product lane** (build → run calls →
inspect) that shapes *who* books. Product sessions rarely end at the form — people book in a
separate, shorter, marketing-shaped session. Neither lens alone tells the truth; the toggle
is the insight.

### The funnel view ([sankey.html](sankey.html), v1.4 → v1.5)

The same aggregate, step-indexed: each Sankey column is one step into a session (consecutive
reloads collapsed), ribbons flow left to right, bookings leave as green stubs at the step
where they happen (event semantics — green exists only at the gate), everything else exits
or pools into "still browsing" past the last column.

**v1.5 best-practice pass** (per the research doc, applied by the parallel Sankey session):
the full-width terminal BOOKED/EXIT bands were replaced with **per-column stubs** — the
convention for drop-off funnels, and the fix for the arcs that were manufacturing crossings;
node ordering became gate-anchored to cut crossings further; the non-booking mass was
softened so the story flows stay loudest; a **table twin** closed the accessibility gap; and
the scale became gap-aware. (Both pages now cross-link — a "funnel"/"graph" button in the
header.)

**v2.3 — content groups, the confirmation page, and the handoff caveat** (Caio: exits to
the dashboard? and color-code the site pages). Three results:

- **Exits to the app are not observable in the all-traffic data** — a full scan found zero
  product-console pageviews (the identified-visitor tooling covers the marketing site
  only). Printed on the chart so EXIT isn't misread; the ICP funnel, which sees both
  properties, is the only measured handoff (its outcome node).
- **Content groups now carry color in both funnels**: core site (homepage/pricing/form)
  blue, blog & content yellow, landing pages violet, careers & other gray, docs aqua, app
  orange — with a legend, and the *stacking order equals the color order* because that
  adjacency sequence is what passed the palette validator (all-pairs cannot pass at six
  hues; a Sankey column is a stacked bar, so adjacent is the honest gate, plus direct
  labels everywhere as the secondary encoding). `site_group()` in `build_data.py` and
  `siteGroup()` in the page must stay in sync.
- **The census surfaced the form's confirmation page** — an *observed submission* signal
  the ends-on-form proxy was missing, and it was miscounting sessions that continued past
  the form as EXITs. All-traffic green is now "confirmed submission (confirmation page
  reached) or ends on the form": 556 of 22,804 sessions (2.4%), **179 of them confirmed
  submissions**. Which of the site's forms redirect there is worth confirming with the
  Retell-side session (the demo form reportedly lacks a visible acknowledgement, so the
  confirmation page may belong to a specific flow).

**v2.1 — the all-traffic funnel** ([sankey-all.html](sankey-all.html)). Same page code as
the ICP funnel — `build_data.py` byte-copies `sankey.html` and injects a different dataset;
`SK.mode` drives the wording, so the two can never drift. Data: identified-visitor
exports from the private intake (row-level deduped — the folder holds re-exports of the
same window in different byte order plus a week file inside a month file; 10,085 duplicate
rows dropped, and the 10k-row export cap is printed as a caveat). 22,804 identified
sessions across two windows; marketing site only (the limit of the identified-visitor
tooling); `Pages Viewed` order treated as chronological (59% of multi-page rows start at the homepage; sequences
read narratively). **Green here means "session's last page is the demo-request form" —
submission/booking is not observable at this scale**, and the page says so. Origins from
UTM tags (85% untagged/direct — the attribution hole, printed). The pair of funnels is the
finding: ICP leads convert ~39%; full identified traffic reaches the form 1.8% of the time
(411/22,804, still peaking at steps 2–3), with a 22,020-session EXIT wall of single-page
visits. Same site, same weeks — the difference between the two charts is what
"qualified" means.

### The warehouse gravity graph ([index-lakehouse.html](index-lakehouse.html), v2.6)

Caio asked whether the graph could refresh from the warehouse too — "same data inputs,
right?". Half right, and the half that isn't is the interesting part:

- **For the ICP data it was already rigged.** `build_data.py` has always injected one payload
  into *both* the graph and the funnel, so a refresh updates them together. Nothing to do.
- **The warehouse is not the same inputs.** It has richer *behaviour* (235k sessions vs 245)
  but no booking outcome and no visitor-level fate. So the twin graph redefines the absorbing
  state: **gravity = P(a walk reaches the demo-request form)**. The Visitor-fate toggle is
  removed rather than left as a fake choice, and the scope switch disappears because the
  source carries no product-side journeys.
- **Dwell had to be derived.** The platform populates its own engagement field on ~1% of
  pageviews, so per-page dwell is computed from gaps between consecutive pageviews, clamped at
  30 min (median 35 s/page — plausible). Without that the semi-Markov time quantity would have
  been silently meaningless.

What it says, and the reason it's worth having: with n=235k the ranking is **identical at
κ=2 and κ=20** — the shrinkage slider, which exists because n=53 was thin, has nothing left to
do. And the content verdict is blunt: `/enterprise-plan` 71%, `/thank-you-demo-call` 6.4%,
industry and feature pages 3.4–4.4% (2–3× base), while **blog posts sit at 0.0–0.1%** despite
being some of the highest-traffic pages on the site. The blog draws crowds that never walk
toward the form.

Model coherence checked: start-of-session gravity equals the base rate (1.52%) exactly, and
all gravities stay in [0, 1].

**v2.5 — the pseudo-outcome retired** (Caio: "10 end on 'still browsing', which isn't a
proper terminal node"). Correct, and it was a category error: BOOKED / EXIT / app dashboard
are *fates*, while "still browsing" only ever meant *we ran out of columns*. The fix keeps
both facts instead of trading one for the other — a journey longer than the chart is wide now
ends at its **real** outcome, drawn as a **dashed** ribbon whose tooltip says the middle isn't
drawn. Dashing earns its keep here (an incomplete path is exactly what a dash conventionally
means; the anti-pattern is dashing a *gridline*, where it signals nothing).

The correction moved real numbers, because those sessions had been silently withheld from
their outcomes: ICP **BOOKED 38 → 41, EXIT 36 → 41, app 13 → 15** — 10 sessions, a tenth of
that funnel, had been parked in a non-answer. Identified traffic redistributed 357; the
warehouse funnel 812, leaving its outcome column exactly two nodes. All three still conserve
exactly (97 / 22,804 / 235,218 at both ends), and the legend only claims the dashed
convention on pages that actually draw one.

### The warehouse funnel ([sankey-lakehouse.html](sankey-lakehouse.html), v2.4)

The third dataset, and the first sourced from the company's canonical warehouse rather than a
file export — built by [`build_data_lakehouse.py`](build_data_lakehouse.py), which reduces to
step transitions *inside* the warehouse and returns counts only (no identifier is ever read
or emitted). **225,466 marketing-site sessions, 2026-07-19 → 08-10.** Sample size stops
being the limiting factor: this is ~920× the ICP file's session count.

Its outcome is **"reached the form", not a booking** — and that is forced, not chosen: the
analytics platform records 32 submit events on the gate page against 4,709 sessions that
reached it, so submission and booking are unobservable at this grain. The honest response was
to rename the outcome, not to estimate the number. Booking outcomes stay in the ICP dataset.

What the scale reveals that neither smaller dataset could:

- **89.9% of sessions never see a second page** (202,697 of 225,466). The funnel is one wide
  step and then a cliff: 225,466 → 22,769 → 7,958 → 3,751 → 2,083 → 1,219.
- **1.54% reach the form.** The identified-visitor dataset reaches it at **2.4%**
  (556/22,804) — so reverse-IP identification skews **~1.6× more buyer-heavy** than real
  traffic. That's the selection bias of the identified subset, quantified rather than assumed.
- **Self-reported attribution is off by an order of magnitude, in a measurable direction.**
  ChatGPT is 1.7% of measured sessions (3,830) but 27% of ICP sessions self-report it. The
  internal brief predicted this direction; this is the size of it. Measured origins: direct /
  untagged 110,064 · google organic 89,980 · other referral 11,133 · google ads 8,932 ·
  chatgpt 3,830 · linkedin 1,527.

Two documented traps are honoured in the query rather than rediscovered: the marketing-site
host filter (the same property also collects the product and auth subdomains — **over 90% of
pageviews**, so an unfiltered chart is a product metric wearing a marketing label), and the
exclusion of `/careers` + `/about-us` (job-seeker traffic over-indexes on large companies).
Locale-prefixed paths normalise onto their canonical page so the funnel doesn't fragment
across ten locales.

**Window caveat, and why streaming didn't help.** The warehouse's raw-event history starts
when the export was first connected and **cannot be backfilled**, which is why this dataset
barely overlaps the ICP file's June–July window rather than extending it. Streaming export
was switched on at the source the same day this was built, and it made **no difference here**:
the managed connector consumes only whole-day tables, so both raw and gold still ended at
08-10 while the source had same-day data. Freshness gained at the source does not
automatically reach the warehouse — verify with `MAX(event_date)` rather than trusting a
green pipeline.

All three pages share one code path (the siblings are byte copies; `SK.mode` drives wording),
so a layout fix lands everywhere at once. Verified: origin and outcome columns both sum to
225,466, every intermediate column balances in=out, and no page node leaks into the outcome
column.

**v2.0 — the inclusion rule** (Caio: every user shown must have passed through at least one
www page). The funnel's population is now defined, not inherited: 97 marketing sessions;
132 pure-app and 16 docs-only sessions excluded (counted in the header). All 38 bookings
retained by construction — booking requires the gate, a www page. Docs pages stay as steps
inside qualifying journeys (which pages feed them, where they lead). Also: `/` renamed
**homepage**, "(other www)" → **"(other site pages)"** ("(other docs pages)" likewise).
The reframe this produced is the strongest single finding of the series: **BOOKED vs EXIT are
neck and neck — the marketing funnel converts ~42% of its true sessions** (41 vs 41 of 97
after v2.5 resolved the truncated journeys; it read 38 vs 36 while 10 sessions were still
parked in a non-outcome). The "leak" in every
earlier version was app traffic that was never the marketing funnel's to lose. A funnel's
denominator is a modeling decision, and it was hiding the conclusion.

**v1.9 — the app is an origin and an outcome, never a middle step** (Caio's structural
insight, checked against the data first). Bounce-back is the minority he suspected: of 245
sessions, 132 are pure-app, 71 never touch the app, 13 dive in and stay, and only 29 return
from app to marketing — but 19 of those simply *start* in the app, and 11 of the 29 end at
the gate (the product-lane booking path), so returns are preserved structurally rather than
spliced: leading app-runs become the **app dashboard origin** (151 sessions), trailing runs
the **app dashboard outcome** (153), pure-app sessions one direct origin→outcome ribbon,
and only 23 interior marketing→app→marketing hops are elided (counted on the chart). Side
effects that made the model better: BOOKED found a 38th session and "still browsing"
dropped 28→10 — most "long" journeys were only long inside the app; their marketing part is
short. EXIT shrank to 44: the marketing funnel leaks far less than the app-blind view
implied. The v1.7 expand-toggle retired (the restructure needs session sequences, so it
lives in `build_data.py`, not the page).

**v1.8 — origins replace the mute START bar** (Caio: "the big START bar gives us no
information"). Column 0 now splits sessions by the visitor's self-reported discovery
channel: google · 57, chatgpt · 38, recommendation · 11, other/unlisted · 139
(session-weighted; per-visitor it's 16/16/6/15). Directional only — `heard_about` is
self-reported and known to under-attribute (caveat printed on the chart and in tooltips).
What it shows immediately: google/chatgpt sessions feed the marketing lane, while the
other/unlisted mass is dominated by returning app sessions — the heavy product users are
exactly the ones attribution can't see. Also in v1.8: "dashboard app" renamed to
**app dashboard**; extra air below gate nodes after Caio mis-read the homepage→gate ribbon
(31 sessions, the biggest marketing transition) as a gate→gate self-flow — verified no
same-page step-transitions exist (reload-collapsing holds; only "(other …)" buckets
self-flow, which is different tail pages sharing a bucket).

**v1.7 — the app as one lane** (Caio: this is a marketing view; who enters and leaves the
dashboard matters, where they go inside it doesn't). All `dashboard.*` pages collapse into a
single "dashboard app" node per column — the app becomes one calm river along the bottom
(narrowing as sessions exit, feeding "still browsing"), marketing↔app crossovers stay
visible as strands between the lanes, and the marketing story owns the top half. A header
toggle expands the detail (51 nodes/155 ribbons collapsed ↔ 91/297 expanded; conservation
verified at 245 both ways). Audience framing beats completeness: the collapsed default is
the honest chart *for the question being asked*.

**v1.6 — terminal outcome column** (Caio: "shouldn't book aggregate into one band at the
end? The vertical aggregate height lets us compare that to other outcomes"). Correct, and
the research supports it: stubs answer *where* sessions end but fragment the totals; the
classic Sankey/alluvial answer to *how much ends where* is terminal nodes whose heights
compare directly. Now the last column is the outcome distribution — BOOKED·37,
still browsing·28, EXIT·180 stacked — while per-departure counts stay printed on each green
ribbon, keeping both answers (the hybrid is written up in the research doc §"Per-stage
stubs vs. terminal aggregation"). Unlike the rejected v1.4 band, outcomes are nodes in the
flow's grain: rightward ribbons, exit mass painted at the back, the green story on top.

What the step indexing adds that the graph can't show: **the modal booked session is two
steps long** — of 37 booking sessions, 16 book at step 2 and 9 more at step 3; it's
land → form → book, not a wander. Meanwhile the sessions that survive to step 6+ are almost
entirely dashboard sessions heading for "still browsing", not for the form. The funnel and
the two-lens finding agree: booking is a short marketing-lane errand, often by people whose
long sessions happened elsewhere.

Conservation checked programmatically: 245 sessions in; 37 booked + 180 exits +
28 still-browsing out; every column's inflow equals its outflow.

### The gate (domain datum from Caio, v1.2)

`/enterprise-plan` is not just another page — it hosts the demo-request form, so it is the
mechanical gate every booking passes through. The data agrees it's special:

- `/enterprise-plan → BOOKED` is the **largest single absorbing edge**: 41 of 184 booked
  session-ends (22.3%) happen there.
- When a session ends on it, it ends booked 41:8 (84%) — far above its 80% gravity.
- It is a destination, not a landing page: 74 of its 78 visits arrive from other pages
  (only 4 session entries).

The layout now encodes this: the gate is **pinned in the doorway** between the graph and
BOOKED (exempt from the fate force — its position states its role), drawn with a dashed
ring in BOOKED's green and a permanent GATE label. Domain gates live in a one-line
`GATES` set at the top of the script.

## Caveats — read before believing

1. **n = 53 visitors.** Everything above survives κ up to ~10, but this is a cohort sketch,
   not a measurement instrument. The κ slider is the honesty control.
2. **Fate labeling over-credits** (visitor-fate mode only). Every session of a booked
   visitor ends `BOOKED`, including sessions before they booked. The booking-event mode
   (v1.3) is the strict alternative; the remaining refinement — absorbing only the final
   pre-booking session — is an open thread.
3. **Correlation, not causation.** Call-history doesn't *make* people book; serious people
   visit call-history. Don't reroute the nav based on this alone.
4. **ICP-filtered cohort** — already qualified leads, hence the high fate-mode base. A
   general-traffic chain would look completely different (see the all-traffic funnel).
4b. **The denominator is a choice, and it dominates.** Event-mode gravity reads 16.7% base
   over all sessions and 42.3% over site-touching ones. Neither is wrong; quoting either
   without saying which is. The toggle and its exclusion counts are on the page for this
   reason.
4c. **Origin channels are self-reported** (asked at form fill) and under-attribute several
   real discovery paths — the origin split is a segmentation, not an attribution model.
5. Dwell is missing on ~30% of pageviews (treated as 0), so expected-time figures
   underestimate. Relatedly, very short bounce sessions are systematically
   under-represented by the session-matching pipeline that produced the source data.
6. **Some gate EXITs are technical, not motivational.** Known form/scheduler failure modes
   (no submit acknowledgement; the embedded scheduler failing to load for some visitors)
   mean a session ending at the gate without a booking may be a *broken* booking rather
   than lost intent. The gate's detail panel carries this warning.
7. **Right-edge truncation.** Outcome classification degrades near the export's end date,
   so late-window "not scheduled" visitors may simply be unclassified.
8. **`heard_about` is self-reported and incomplete** — a caveat waiting for the per-channel
   open thread: channel labels under-attribute several real discovery paths.

(Caveats 5–8 paraphrase an internal domain brief; precise figures live outside this repo.)

## How it's built

Single self-contained `index.html` (no deps, no build): hand-rolled force layout (O(n²)
repulsion, log-weighted springs, pinned START/BOOKED/LOST anchors), canvas renderer with
traffic particles along edges, the Markov solver re-runs live on κ changes.

**v1.1 legibility pass** (from looking at v1 and squinting):
- **Fate layout** (default on): each page is pulled vertically toward
  `y = lerp(LOST.y, BOOKED.y, gravity)` — height becomes the model's output, so the picture
  reads without hovering. Vertical center-gravity is nearly disabled while it's on (the two
  fought; the fate force must own the axis). ~300 physics ticks run synchronously at boot so
  the first paint is already a formed map.
- **Focus mode**: hovering/selecting dims everything outside the node's direct neighborhood;
  particles only travel lit edges.
- **Ghost tail**: pages under the "min visits (map)" threshold render as faint, edgeless,
  unlabeled dots — the long tail stays visible as texture without shouting.
- Contrast: sqrt easing on the diverging ramp (near-base differences register) and sqrt
  scaling on edge width/alpha (mid-traffic edges stop vanishing); canvas labels get a dark
  halo and greedy vertical decollision. Dark-mode
palette validated with the dataviz six-checks validator (categorical trio all-pairs pass on
`#0b0d12`; diverging blue↔red for gravity; status green/red reserved for the absorbing
states). Hover tooltips, click-to-inspect detail panel (outgoing distribution per page),
sortable full-data table for accessibility.

## Verification

- Model: no NaNs; all gravities in [0.50, 0.88]; κ→large shrinks toward base monotonically
  (checked `/changelog`: 78.8% at κ=2 → 76.5% at κ=20); start-of-session ≈ base.
- UI: detail panel, table sort, color-mode switches, legend swaps — exercised via scripted
  DOM checks in the embedded browser.
- Visual: verified from headless-Chrome screenshots (the preview pane wouldn't composite
  again); layout fixes (panel-aware anchors, label halos, stronger repulsion) came from
  actually looking, which numeric checks would never have caught.

**v2.2** — the refinement log applied (see "The denominator was the story all along").
Mechanically: `build_data.py` gained three additive keys — `edgesWww` (the same chain over
site-touching sessions only), `entryOrigins` (entries split by channel, per scope), and
`inclusion` (session counts + exclusion reasons); every visit read in the page routes
through a scope accessor so one toggle re-denominates the whole model. Verified: absorption
totals conserve to the session count in both scopes (41 + 41 + 15 = 97; 41 + 49 + 155 = 245),
origin entries sum to the scope's session count, and green edges still originate only at the
gate. Human labels landed too — `/` reads "homepage", dashboard paths read `app/…`, and the
folded nodes are "(other site/app/docs pages)".

**v1.5** — spacing pass on the graph, applying
[`docs/research/dataviz-sankey-best-practices.md`](https://github.com/caio-camargo/explorations/blob/main/docs/research/dataviz-sankey-best-practices.md)
Part 1 to the force layout (the research was produced for the Sankey; its general
principles transfer):

- **Fold minors into "Other"** (§2.2, the anti-spaghetti rule): pages below the threshold no
  longer float as ghost dots — they collapse into one dashed `(other www / dashboard / docs)`
  node per property that **carries their traffic with it**, so edge weight is conserved
  (verified: 1,199 in = 1,199 out). At the default threshold that's 67 pages folded into 3
  nodes; 117 pages → 56 visible marks, 442 → 341 drawn transitions. The slider unfolds them.
- **Rank-spaced fate axis**: height now encodes gravity *rank*, evenly spaced, instead of the
  raw value. The event-mode distribution is heavily skewed (a long low tail, a few leaders),
  so a linear axis piled two-thirds of the pages into one band — the ranking was invisible
  precisely where it mattered. Colour still carries the true value, so the pair reads as
  "order by height, magnitude by hue".
- **Pairwise collision resolution**: no two visible nodes may overlap, and nodes big enough to
  carry a label claim extra room. Verified 0 overlapping pairs after settling.
- Legend gained the "height = gravity rank · colour = gravity" caption and an `(other …)` key.

**v1.3.1** (design notes from Caio): the layout pre-settles ~1200 ticks and boots cold, so
the first paint is a still map instead of a settling scramble. Dragging became meaningful:
**dropping a node pins it** (small white pin dot; double-click releases one, re-layout
releases all) — the map is customizable. And the gate moved flush against BOOKED with an
x-clamp on free pages, so **nothing stands between the form and the meeting**.

**v1.4**: sibling page [`sankey.html`](sankey.html) — hand-rolled SVG Sankey over
step-indexed flows (`build_data.py` now emits `sankey.flows`/`sankey.ends` and injects into
every marker-bearing HTML in the folder). Top pages keep names; the tail folds into
"(other <prop>)" per property; ends use event semantics. Hover highlights a node's ribbons
(matched by column+id, not substring). Cross-linked with the graph page.

**v1.3**: absorption-semantics toggle (booking event vs visitor fate — see The model),
human page meanings on tooltips and the detail panel, mode-aware legends and ranked-list
framing, gate failure-mode warning. Display edges are rebuilt per mode, so the graph itself
tells the chosen story (event mode: one green edge).

## Open threads

- [ ] **Session-level credit assignment** — within visitor-fate mode, absorb only the last
      pre-booking session into `BOOKED`; earlier sessions end neutral. The middle ground
      between the two v1.3 lenses.
- [ ] **Edge-level fate coloring** — paint each transition by the fate mix of walks using it;
      would show *routes*, not just pages.
- [ ] **Per-channel chains** — `heard_about` is in the source data; a chatgpt-referred chain
      vs a google-search chain would answer whether channels shape journeys or just volume.
- [ ] **Betweenness on booked paths** — which pages are bridges rather than destinations.
- [ ] Re-run monthly as the journey exports refresh; the build script is one command.
