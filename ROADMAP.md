# Roadmap & notes

Working notes for this site: what each view is for, what's queued, and the caveats a
reader should know. The audience for the site is a busy reader who needs the picture at a
glance, cares most about week-over-week movement, and often sees it on a shared screen.

## Design rules

- **Glance first.** The home page leads with last complete week vs the week before. Anything
  that needs reading goes below the fold or behind a click.
- **Week over week, always complete weeks.** Mon–Sun, never the current partial week.
- **Every number is computed, never narrated.** Where AI commentary is added, the model
  receives finished tables and writes prose only — it never derives a figure or a streak.
- **Aggregate only.** Counts and rates. No identities, emails, domains, or per-visitor rows.
  The private per-lead material lives elsewhere.
- **Live or dated.** Every view says whether it refreshes nightly or is a dated snapshot.
- **Screenshare-safe.** Large type, no hover-only information for the headline layer, light
  theme for the top-level pages, presentation mode on the home page (`?present`).

## Queued (triaged 2026-09-02)

Two standing decisions: revenue figures are allowed on the site for now (the URL is
unlisted; proper access controls are queued below), and aggregate objection / competitor
trends from sales calls are in scope — never verbatims, never per-rep.

| # | Item | Notes | Size |
|---|---|---|---|
| 1 | **Three more headline tiles**: new paid accounts (pairs with signups), ICP accounts seen on the site (count), visitors from AI assistants | Paid accounts need a billing fetch worker alongside the signups one; ICP accounts is a count over the identified-visitor feed; AI-assistant visitors come from the warehouse origin classification already used by the funnel. | S–M |
| 2 | **Pipeline health section** on the home | All computed already: per-source freshness, metric anomaly verdicts, form-leak count, attribution capture rates (UTM %, client-id %), feed liveness, payload build stamps. One row per source, green/amber/red, last run. | S |
| 3 | **Usage cohorts page + weekly AI commentary** — one build | Cohort counts and minute totals per week (no customer names), plus the commentary pattern from the weekly usage report: SQL computes every figure including streaks, the model writes prose and a carryover note, a human-correction column feeds forward. Commentary renders as a fourth section in each tile's panel and as the Monday message. | M |
| 4 | **Ads full-funnel on nightly refresh** | Spend → session → form → routed → booked per campaign (ad clicks reconcile with sessions ~1:1). Replaces the dated paid-ads snapshot. LinkedIn ads data is stale upstream since June. | M |
| 5 | **Organic ICP demand page** | Search-console pages and queries ranked by the ICP leads they produce — demand quality, not rankings (rankings stay with the SEO owner's weekly report). | M |
| 6 | **Sales-call objection & competitor trends** | Aggregate per week and segment from the structured call analysis: top objections, competitors named, feature gaps, stage-vs-reality. Counts and shares only. | M |
| 7 | **Access controls** | Move from an unlisted URL to real access control (sign-in in front of the static site or a gated host) before widening the audience. Until then no per-person data of any kind, and revenue stays coarse. | M |
| 8 | **Enterprise bookings with recordings** | Count on the ICP bookings tile of last week's booked enterprise leads with a watchable recording. | S |
| 9 | **Chili routed-but-not-booked + calendar abandonment** | Weekly count and rate on the enterprise-leads page. | S |
| 10 | **Meeting → deal movement** | Weekly counts from the meeting↔deal link (deals exist from Feb 2026; amounts on ~2%, so counts only). | M |
| 11 | **Community page** | Discourse themes and health week over week; the data currently lives in a spreadsheet base, so the cost is a payload path. | M |
| 12 | **Journey pages themed to match; dated cohorts refreshed or archived; unique tab titles** | Screenshare consistency; see the review notes. | S |
| 13 | **Visitor → signup / booking ratio, 12 months** | Monthly index (no shared key between the three sources — an index, not a funnel). | S |
| — | Done 2026-09-02 | Signups tile; expandable tiles; presentation mode; this roadmap. | — |

## Caveats that travel with the numbers

- **Sessions undercount since Aug 12, 2026.** A consent-banner change drops the session id on
  a growing share of pageviews (~20% by the week of Aug 17). Session counts read low; lead
  metrics are unaffected. Treat session week-over-week as directional.
- **Form reach is not conversion.** Reaching `/enterprise-plan` is observable for every
  session; submitting and booking are only observable on the lead metrics.
- **ICP** = matched routing rule for the enterprise team, or the CRM classifier (company
  match / enterprise tier) where the rule is not observable — the rule is only recorded for
  leads that booked.
- **Journeys** are observable from Jul 19, 2026 and roughly one in five in-coverage leads
  shows none (corporate machines block tracking).
- **Signups** are Stripe customer creations; the business/free-mail split is by email
  domain against a fixed free-mail list.

## Changelog

- 2026-09-02 — Home page rebuilt around week-over-week headline tiles (sessions, form
  reach, leads routed, ICP leads, ICP bookings, signups), expandable to their weekly data,
  source breakdowns and notes; presentation mode; question-grouped links with live/snapshot
  badges; week-over-week anchor on the all-traffic funnel; this file.
- 2026-09-01 — ICP lead journeys page (live daily); dashboard layer on the all-traffic
  funnel (windows, audiences, leak tables, week-over-week by source).
- 2026-08-14 — Journey pages migrated in; funnel-at-a-glance briefing.
