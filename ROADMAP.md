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

## Queued

| # | Item | Notes |
|---|---|---|
| 1 | **Weekly AI commentary on the headline tiles** | Same pattern as the weekly usage-trends report: SQL computes every figure (including streaks and "N of the last M weeks" — never left to the model), the model writes a short narrative per tile plus a carryover note, and a human correction column feeds forward permanently. Output lands as a fourth section in the tile's expanded panel and as the Monday message. Needs: a `viz_commentary` table, one Edge Function on the Monday cron, the usage-trends context/carryover model reused. |
| 2 | **Signups on the home page** — done 2026-09-02 | Weekly self-serve signups with a business vs free-mail split, from the same Stripe feed the usage report uses. Next: usage minutes per week alongside it (same source family), and the cohort view from the usage report. |
| 3 | **Journey pages themed to match** | The Sankey/gravity pages are dark-only; the rest of the site is light. On a shared screen the switch is jarring and the dense dark ribbons read poorly. Either theme them to the site tokens or surface their tables (which carry the week-over-week content) above the chart. |
| 4 | **Retire or refresh the dated cohorts** | ICP funnel (Jun–Jul), ICP gravity (53 leads), identified accounts (Aug 4–10) are one-off snapshots. Move them to the nightly refresh or into an archive section. |
| 5 | **Unique tab titles on the journey pages** | Five pages share one title until their script overrides it. |
| 6 | **Enterprise bookings with recordings** | A count on the ICP bookings tile of how many of last week's booked enterprise leads have a watchable session recording — count only; the recordings themselves stay private. |

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
