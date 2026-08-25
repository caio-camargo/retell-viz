#!/usr/bin/env python3
"""Paid-ads journey funnel — the warehouse funnel restricted to paid sessions.

Same reduction as build_data_lakehouse.py, over the subset of sessions that
ARRIVED FROM A PAID AD: any pageview in the session carries a Google click id
(gclid), an ad campaign id (gad_campaign_id), or utm_medium in
cpc/ppc/paid/paid_social. This capture is URL-based, so it largely escaped the
CookieYes consent disruption — measured on paid pageviews, session ids were
0% null through 2026-08-11, 2-5% to 08-18, then 10-21% from 08-19, so the most
recent days undercount somewhat.

Origins are the AD CAMPAIGN (top N by sessions, the rest folded into "other
campaigns"). Channel-level origins were pointless here — Google Ads is 99.4% of
paid traffic, so the origin column was one node. 98.4% of Google-ads sessions
carry `gad_campaign_id`, and Ads-reported clicks reconcile ~1:1 with sessions
(verified 2026-08-25), so spend per campaign rides along in the payload and
shows up in each origin's tooltip.

Writes sankey-ads.html as a byte copy of sankey.html (mode "ads" drives the
wording), so all funnel variants stay on one code path.
"""
import collections
import json
import sys

from build_data_lakehouse import (sql, EVENTS, SITE_HOST, GATE, MAXSTEP, TOPN,
                                  LOCALES, DROP_PAGES, WAREHOUSE, HERE, CATALOG)

# Spark inlines CTEs, so a CTE referenced N times runs N times. The paid-session
# aggregate scans the whole events table — materialize it once into a scratch
# table instead of paying that scan on every reference (the CTE version ran >10
# minutes; this shape runs in ~2).
SCRATCH = f"{CATALOG}.caio_scratch"
PAID_TBL = f"{SCRATCH}.ads_paid_sessions"

# The form's post-submit confirmation page. It is NOT a journey step — it only
# exists after the visitor has already submitted — so it never appears as a
# node: each session's path is truncated at its first confirmation view, and
# the session ends as a confirmed submission (green) on its last real page.
# Post-submission browsing is likewise not drawn.
CONFIRM = "/thank-you-demo-call"

# Session-level paid membership + channel. gclid/gad_campaign_id are
# Google-only signals; UTM decides the rest.
TOPCAMP = 8   # named campaigns on the origin axis; the tail folds into one node

# Campaign labels are long ("ScalixAI | Non-Branded | Use Cases | 27 July 2026")
# and the node axis is narrow, so strip the account prefix and the launch-date
# suffix — what distinguishes them is the middle.
# NB: the pipe needs a DOUBLE backslash — Spark unescapes the string literal
# first, so '\|' reaches the regex engine as a bare alternation whose empty-left
# branch matches every space (it silently turned "Comp - Poly AI" into
# "Comp-PolyAI"). '\|' is what makes it a literal pipe.
NAME_CLEAN = (r"regexp_replace(regexp_replace(regexp_replace(ch.name, "
              r"'^ScalixAI \\| ', ''), ' \\| [0-9]{1,2} [A-Za-z]{3,9} [0-9]{4}$', ''), "
              r"' \\| [A-Za-z]{3,9} [0-9]{4}$', '')")

# Session-level paid membership + which campaign brought it.
# gclid/gad_campaign_id are Google-only signals; UTM decides the rest.
PAID_SQL = f"""
WITH base AS (
  SELECT concat(user_pseudo_id, '|', CAST(ga_session_id AS STRING)) AS sk,
         MAX(CASE WHEN gad_campaign_id <> '' THEN gad_campaign_id END) AS cid,
         MAX(CASE WHEN gclid IS NOT NULL AND gclid <> '' THEN 1 ELSE 0 END) AS g,
         MAX(CASE WHEN lower(coalesce(param_medium, '')) IN
                       ('cpc','ppc','paid','paid_social')
                   AND lower(coalesce(param_source, '')) LIKE '%linkedin%'
                  THEN 1 ELSE 0 END) AS li,
         MAX(CASE WHEN lower(coalesce(param_medium, '')) IN
                       ('cpc','ppc','paid','paid_social')
                  THEN 1 ELSE 0 END) AS anypaid
  FROM {EVENTS}
  WHERE device_web_hostname = '{SITE_HOST}' AND ga_session_id IS NOT NULL
  GROUP BY 1
  HAVING g = 1 OR anypaid = 1
),
-- campaign_history is an SCD table: dedupe to one row per id BEFORE joining,
-- or every downstream sum multiplies by the number of history rows
ch AS (
  SELECT id, name FROM (
    SELECT id, name, ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) rn
    FROM workspace.google_ads.campaign_history
  ) x WHERE rn = 1
),
lab AS (
  SELECT b.sk, b.g, b.li,
         CASE WHEN b.cid IS NULL THEN NULL
              ELSE COALESCE({NAME_CLEAN}, concat('campaign ', b.cid)) END AS nm
  FROM base b LEFT JOIN ch ON ch.id = CAST(b.cid AS BIGINT)
),
rk AS (
  SELECT nm, ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) AS rn
  FROM lab WHERE nm IS NOT NULL GROUP BY nm
)
SELECT l.sk,
       CASE WHEN l.nm IS NOT NULL AND r.rn <= {TOPCAMP} THEN l.nm
            WHEN l.nm IS NOT NULL THEN 'other campaigns'
            WHEN l.li = 1 THEN 'linkedin ads'
            WHEN l.g = 1 THEN 'google ads (untagged)'
            ELSE 'other paid' END AS origin
FROM lab l LEFT JOIN rk r ON r.nm = l.nm
"""

# Spend/clicks per campaign label, over the same window the funnel covers.
def camp_stats_sql(first_day, last_day):
    return f"""
WITH ch AS (
  SELECT id, name FROM (
    SELECT id, name, ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) rn
    FROM workspace.google_ads.campaign_history
  ) x WHERE rn = 1
)
SELECT COALESCE({NAME_CLEAN}, concat('campaign ', CAST(s.id AS STRING))) AS label,
       CAST(ROUND(SUM(s.cost_micros)/1e6, 0) AS STRING) AS spend,
       CAST(SUM(s.clicks) AS STRING) AS clicks
FROM workspace.google_ads.campaign_stats s
LEFT JOIN ch ON ch.id = s.id
WHERE s.date BETWEEN '{first_day}' AND '{last_day}'
GROUP BY 1 HAVING SUM(s.cost_micros) > 0
"""

# form_only=True restricts the whole funnel to sessions that touch the gate at
# any step — the flows are re-aggregated over that subset (an aggregate funnel
# cannot be filtered after the fact; the counts don't carry per-session fate).
def funnel_sql(form_only=False):
    reach_filter = f"""
reachers AS (SELECT DISTINCT sk FROM dedup0 WHERE path = '{GATE}'
             UNION SELECT sk FROM ty),
dedup AS (SELECT d.* FROM dedup0 d JOIN reachers r ON r.sk = d.sk),
""" if form_only else "dedup AS (SELECT * FROM dedup0),"
    return f"""
WITH paid AS (SELECT * FROM {PAID_TBL}),
pv AS (
  SELECT b.sk, b.event_ts,
         CASE WHEN p = '' OR p IS NULL THEN '/' ELSE p END AS path
  FROM (
    SELECT concat(user_pseudo_id, '|', CAST(ga_session_id AS STRING)) AS sk,
           event_ts,
           CASE WHEN length(lp) > 1 AND endswith(lp, '/')
                THEN left(lp, length(lp) - 1) ELSE lp END AS p
    FROM (
      SELECT user_pseudo_id, ga_session_id, event_ts,
             regexp_replace(page_path, '^/({LOCALES})(/|$)', '/') AS lp
      FROM {EVENTS}
      WHERE device_web_hostname = '{SITE_HOST}'
        AND event_name = 'page_view'
        AND ga_session_id IS NOT NULL
        AND page_path IS NOT NULL
    ) a
  ) b JOIN paid ON paid.sk = b.sk
),
kept AS (
  SELECT * FROM pv WHERE path NOT IN ({",".join(f"'{p}'" for p in DROP_PAGES)})
),
ty AS (
  SELECT sk, MIN(event_ts) AS ty_ts FROM kept
  WHERE path = '{CONFIRM}' GROUP BY sk
),
pre AS (
  SELECT k.sk, k.path, k.event_ts
  FROM kept k LEFT JOIN ty ON ty.sk = k.sk
  WHERE (ty.ty_ts IS NULL OR k.event_ts < ty.ty_ts) AND k.path <> '{CONFIRM}'
),
dedup0 AS (
  SELECT sk, path, event_ts FROM (
    SELECT sk, path, event_ts,
           LAG(path) OVER (PARTITION BY sk ORDER BY event_ts) AS prev
    FROM pre
  ) w WHERE prev IS NULL OR prev <> path
),
{reach_filter}
stepped AS (
  SELECT sk, path,
         ROW_NUMBER() OVER (PARTITION BY sk ORDER BY event_ts) AS step,
         COUNT(*) OVER (PARTITION BY sk) AS steps_total
  FROM dedup
),
topn AS (
  SELECT path FROM (
    SELECT path, ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) AS rn
    FROM dedup GROUP BY path
  ) t WHERE rn <= {TOPN}
),
labeled AS (
  SELECT s.sk, s.step, s.steps_total,
         CASE WHEN s.path = '/' THEN 'homepage'
              WHEN s.path = '{GATE}' THEN '{GATE}'
              WHEN s.path IN (SELECT path FROM topn) THEN s.path
              ELSE '(other site pages)' END AS node,
         s.path AS raw_path
  FROM stepped s
)
SELECT 'origin' AS kind, 0 AS c, x.origin AS a, l.node AS b, COUNT(*) AS n
  FROM labeled l JOIN paid x ON x.sk = l.sk
  WHERE l.step = 1 GROUP BY 1,2,3,4
UNION ALL
SELECT 'flow', a.step, a.node, b.node, COUNT(*)
  FROM labeled a JOIN labeled b ON a.sk = b.sk AND b.step = a.step + 1
  WHERE a.step < {MAXSTEP} GROUP BY 1,2,3,4
UNION ALL
SELECT CASE WHEN t.sk IS NOT NULL
            THEN 'end_gate_trunc' ELSE 'end_exit_trunc' END,
       {MAXSTEP}, at_edge.node, '', COUNT(*)
  FROM labeled at_edge
  JOIN labeled last ON last.sk = at_edge.sk AND last.step = last.steps_total
  LEFT JOIN ty t ON t.sk = at_edge.sk
  WHERE at_edge.step = {MAXSTEP} AND at_edge.steps_total > {MAXSTEP}
  GROUP BY 1,2,3,4
UNION ALL
SELECT CASE WHEN t.sk IS NOT NULL
            THEN 'end_gate' ELSE 'end_exit' END,
       l.step, l.node, '', COUNT(*)
  FROM labeled l LEFT JOIN ty t ON t.sk = l.sk
  WHERE l.step = l.steps_total AND l.steps_total <= {MAXSTEP}
  GROUP BY 1,2,3,4
UNION ALL
SELECT 'excl', 0, 'confirmation-only', '', COUNT(*)
  FROM ty t WHERE NOT EXISTS (SELECT 1 FROM dedup0 d WHERE d.sk = t.sk)
UNION ALL
SELECT 'touch', 0, 'form-touched', '', COUNT(*) FROM (
  SELECT DISTINCT sk FROM dedup0 WHERE path = '{GATE}'
  UNION SELECT t.sk FROM ty t
   WHERE EXISTS (SELECT 1 FROM dedup0 d WHERE d.sk = t.sk)
) u
"""


META_SQL = f"""
WITH paid AS (SELECT * FROM {PAID_TBL})
SELECT CAST(MIN(e.event_date) AS STRING), CAST(MAX(e.event_date) AS STRING),
       COUNT(DISTINCT concat(e.user_pseudo_id, '|', CAST(e.ga_session_id AS STRING))),
       COUNT(*)
FROM {EVENTS} e
JOIN paid ON paid.sk = concat(e.user_pseudo_id, '|', CAST(e.ga_session_id AS STRING))
WHERE e.device_web_hostname = '{SITE_HOST}' AND e.event_name = 'page_view'
  AND e.ga_session_id IS NOT NULL
"""


def main():
    if not WAREHOUSE:
        sys.exit("Set LAKEHOUSE_WAREHOUSE_ID to your SQL warehouse id first "
                 "(not committed: this repo is public).")
    sql(f"CREATE SCHEMA IF NOT EXISTS {SCRATCH}")
    sql(f"CREATE OR REPLACE TABLE {PAID_TBL} AS {PAID_SQL}")
    first_day, last_day, paid_sessions, pageviews = sql(META_SQL)[0]
    # spend rides along so each origin's tooltip can answer "what did this cost?"
    camp = {r[0]: {"spend": int(float(r[1])), "clicks": int(r[2])}
            for r in sql(camp_stats_sql(first_day, last_day))}
    print(f"campaign spend rows: {len(camp)} "
          f"(total ${sum(c['spend'] for c in camp.values()):,})")

    for form_only, dest in ((False, "sankey-ads.html"),
                            (True, "sankey-ads-form.html")):
        rows = sql(funnel_sql(form_only))

        flows, ends, trunc = (collections.Counter(), collections.Counter(),
                              collections.Counter())
        confirm_only = form_touched = 0
        for kind, c, a, b, n in rows:
            c, n = int(c), int(n)
            if kind == "excl":
                confirm_only = n
            elif kind == "touch":
                form_touched = n
            elif kind in ("origin", "flow"):
                flows[(c, a, b)] += n
            elif kind == "end_gate":
                ends[(c, a, "booked")] += n
            elif kind == "end_gate_trunc":
                trunc[(c, a, "booked")] += n
            elif kind == "end_exit_trunc":
                trunc[(c, a, "exit")] += n
            else:
                ends[(c, a, "exit")] += n

        included = sum(n for (c, _a, _b), n in flows.items() if c == 0)
        ended = sum(ends.values()) + sum(trunc.values())
        if included != ended:
            sys.exit(f"conservation FAILED ({dest}): {included} in vs {ended} out")
        reached = sum(n for (_c, _a, e), n in
                      list(ends.items()) + list(trunc.items()) if e == "booked")

        out = {
            "meta": {
                "source": "Warehouse web-analytics sessions arriving from paid ads"
                          + (", form-reaching subset" if form_only else "")
                          + ", marketing site only (aggregate; no identifiers read"
                            " or emitted)",
                "date_range": [first_day, last_day],
                "sessions": included,
                "pageviews": int(pageviews),
            },
            "sankey": {
                "maxstep": MAXSTEP,
                "mode": "ads",
                **({"formOnly": True} if form_only else {}),
                "formTouched": form_touched,
                "campaigns": camp,
                "origins": sorted({a for (c, a, _b) in flows if c == 0}),
                "included": included,
                "excluded": ({"sessions entering on the confirmation page "
                              "(no pre-submission step)": confirm_only}
                             if confirm_only else {}),
                "appHopsElided": 0,
                "reachedForm": reached,
                "flows": [{"c": c, "from": a, "to": b, "n": n}
                          for (c, a, b), n in sorted(flows.items())],
                "ends": [{"c": c, "from": a, "end": e, "n": n}
                         for (c, a, e), n in sorted(ends.items())]
                      + [{"c": c, "from": a, "end": e, "n": n, "t": 1}
                         for (c, a, e), n in sorted(trunc.items())],
            },
        }

        js = json.dumps(out, separators=(",", ":"))
        if "--stdout" in sys.argv:
            print(js)
            continue

        s, e = "/*DATA-START*/", "/*DATA-END*/"
        dst = HERE / dest
        html = (HERE / "sankey.html").read_text(encoding="utf-8")
        i, j = html.index(s) + len(s), html.index(e)
        dst.write_text(html[:i] + js + html[j:], encoding="utf-8")
        label = "form-reaching paid" if form_only else "paid"
        print(f"wrote {dest}: {included:,} {label} sessions, "
              f"{form_touched:,} reach the form, {reached:,} submit "
              f"({reached / included * 100:.2f}%), "
              f"{first_day} -> {last_day}, {len(out['sankey']['flows'])} flows")


if __name__ == "__main__":
    main()
