#!/usr/bin/env python3
"""
Read-only diagnostic, pass 4.

Passes 1 to 3 ruled out every visibility explanation:
  - all 64 stories are is_published true, is_hidden false, privacy EVERYONE
  - feed == published_posts, so nothing is filtered out of the visitor timeline
  - no aggregation: 44 photo stories are standalone, 0 subattachments, no parent
  - no page-level age, country or publish restriction

So the Page is not hiding anything. What is left is delivery: Facebook is
choosing not to put these posts in front of the 17 followers. This pass pulls
per-post reach to confirm that, and checks follower vs fan split.

Writes nothing.
"""
import json, os, urllib.parse, urllib.request

GRAPH = "https://graph.facebook.com/v21.0"
TOKEN = os.environ["META_PAGE_TOKEN"]


def _get(path, params=None):
    p = dict(params or {})
    p["access_token"] = TOKEN
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(p)}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def err(e):
    if hasattr(e, "read"):
        try:
            return json.loads(e.read().decode())["error"]["message"][:300]
        except Exception:
            return str(e)
    return str(e)


def main():
    print("FOLLOWERS VS FANS")
    try:
        d = _get("me", {"fields": "fan_count,followers_count,talking_about_count,"
                                  "were_here_count,rating_count"})
        print(json.dumps(d, indent=2))
    except Exception as e:
        print(f"  ERROR {err(e)}")

    print("\nRECENT POSTS + REACH")
    posts = _get("me/feed", {"fields": "id,created_time,status_type,permalink_url",
                             "limit": 12}).get("data", [])
    for p in posts:
        pid = p["id"]
        line = f"\n  {p['created_time']}  {p['status_type']:14s} {pid}"
        print(line)
        for metric in ("post_impressions_unique", "post_impressions",
                       "post_impressions_fan_unique", "post_engaged_users"):
            try:
                ins = _get(f"{pid}/insights", {"metric": metric})
                vals = ins.get("data", [])
                v = vals[0]["values"][0]["value"] if vals else "(empty)"
                print(f"      {metric:30s} {v}")
            except Exception as e:
                print(f"      {metric:30s} ERROR {err(e)}")
                break

    print("\nPAGE-LEVEL REACH, last 28 days")
    for metric in ("page_impressions_unique", "page_posts_impressions_unique",
                   "page_fans", "page_follows"):
        try:
            d = _get("me/insights", {"metric": metric, "period": "day"})
            rows = d.get("data", [])
            if not rows:
                print(f"  {metric:32s} (empty)")
                continue
            vals = rows[0].get("values", [])[-5:]
            print(f"  {metric:32s} {[(v.get('end_time','')[:10], v.get('value')) for v in vals]}")
        except Exception as e:
            print(f"  {metric:32s} ERROR {err(e)}")


if __name__ == "__main__":
    main()
