"""
Performance watcher for Hirra reels and statics.

Added 2026-07-24. The reach audit had to be done by hand because nothing was
recording performance over time; this closes that. It runs daily in CI, pulls
per-post insights from the Graph API for everything in the posted state files,
and appends a row per post per day to metrics.csv.

The point is the trend, not the snapshot. The number that decides whether the
9:16 rebuild worked is ig_reels_avg_watch_time: the old 4:5 cuts averaged
~1 second on a 16 second reel. If that climbs, the format was the problem and
reach should start compounding. If it stays flat, the hook copy is next.

Reads:  posted_reels.json, posted_statics.json, posted.json
Writes: metrics.csv (append-only, one row per post per collection day)
Secret: META_PAGE_TOKEN (env)

Usage: python3 collect_insights.py
"""
import csv
import datetime
import json
import os
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"
TOKEN = os.environ["META_PAGE_TOKEN"]
OUT = "metrics.csv"

# Reels expose watch-time metrics; feed images do not. Asking for a metric the
# media type does not support fails the whole call, so the sets are separate.
IG_REEL = ["reach", "likes", "comments", "shares", "saved", "views",
           "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]
IG_IMAGE = ["reach", "likes", "comments", "saved", "views"]
FB_POST = ["post_impressions_unique", "post_video_avg_time_watched",
           "post_video_view_time", "post_reactions_by_type_total"]

FIELDS = ["collected_at", "platform", "kind", "post_key", "media_id", "metric", "value"]


def _get(path, params=None):
    p = dict(params or {})
    p["access_token"] = TOKEN
    url = f"{GRAPH}/{path}?" + urllib.parse.urlencode(p)
    try:
        return json.loads(urllib.request.urlopen(url, timeout=30).read())
    except urllib.error.HTTPError as e:
        try:
            return {"_error": json.loads(e.read().decode()).get("error", {})}
        except Exception:
            return {"_error": {"message": f"HTTP {e.code}"}}
    except Exception as e:
        return {"_error": {"message": str(e)[:120]}}


_errs = []


def insights(media_id, metrics):
    """Return {metric: value}. Drops unsupported metrics rather than failing."""
    r = _get(f"{media_id}/insights", {"metric": ",".join(metrics)})
    if "_error" in r:
        _errs.append(f"{media_id} batch: {r['_error'].get('message','')[:150]}")
        # retry one metric at a time so one unsupported name does not lose the rest
        out = {}
        for m in metrics:
            one = _get(f"{media_id}/insights", {"metric": m})
            if "_error" in one:
                _errs.append(f"{media_id} {m}: {one['_error'].get('message','')[:150]}")
                continue
            for row in one.get("data", []) or []:
                vals = row.get("values") or [{}]
                out[row["name"]] = vals[0].get("value")
        return out
    out = {}
    for row in r.get("data", []) or []:
        vals = row.get("values") or [{}]
        out[row["name"]] = vals[0].get("value")
    return out


def load(path):
    return json.load(open(path)) if os.path.exists(path) else {}


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []

    for key, st in load("posted_reels.json").items():
        if st.get("ig"):
            for m, v in insights(st["ig"], IG_REEL).items():
                rows.append([now, "ig", "reel", key, st["ig"], m, v])
        if st.get("fb"):
            for m, v in insights(st["fb"], FB_POST).items():
                rows.append([now, "fb", "reel", key, st["fb"], m, v])

    for name, statefile in (("static", "posted_statics.json"), ("campaign", "posted.json")):
        state = load(statefile)
        if isinstance(state, list):
            continue                      # run.py keeps a bare id list, no media ids
        for key, st in state.items():
            if st.get("ig"):
                for m, v in insights(st["ig"], IG_IMAGE).items():
                    rows.append([now, "ig", name, key, st["ig"], m, v])
            if st.get("fb"):
                for m, v in insights(st["fb"], FB_POST).items():
                    rows.append([now, "fb", name, key, st["fb"], m, v])

    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        w.writerows(rows)

    # A short digest in the CI log, so a glance at the run tells the story.
    watch = [r for r in rows if r[5] == "ig_reels_avg_watch_time"]
    reach = [r for r in rows if r[5] == "reach" and r[1] == "ig"]
    print(f"[{now}] wrote {len(rows)} metric rows for "
          f"{len({r[3] for r in rows})} posts")
    if _errs:
        # Never fail silently: an empty metrics.csv looks identical to a healthy
        # run with nothing to report, and that is how the reach problem went
        # unnoticed for a fortnight in the first place.
        print(f"  {len(_errs)} API errors, first few:")
        for e in _errs[:6]:
            print("   ", e)
    if watch:
        vals = [r[6] for r in watch if isinstance(r[6], (int, float))]
        if vals:
            print(f"  IG reels avg watch time: mean {sum(vals)/len(vals)/1000:.1f}s "
                  f"over {len(vals)} reels (was ~1.0s on the 4:5 cuts)")
    if reach:
        vals = [r[6] for r in reach if isinstance(r[6], (int, float))]
        if vals:
            print(f"  IG reach: total {sum(vals)}, best {max(vals)}, over {len(vals)} posts")


if __name__ == "__main__":
    main()
