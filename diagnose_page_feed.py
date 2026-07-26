#!/usr/bin/env python3
"""
Read-only diagnostic, pass 2.

Pass 1 established the timeline is clean: 25 posts, all EVERYONE, none hidden,
feed == published_posts. So the gap is not permissions.

The remaining anomaly is the permalink actor. Photo posts resolve to
facebook.com/122109204921394425/posts/... while the Page is 1225532260636387.
Reels resolve to facebook.com/reel/<id>. If the photo posts are attributed to a
different profile object than the one a visitor lands on, that alone explains a
visitor seeing only the handful of stories that ARE attributed to the Page.

Also counts posts by type and by resolved actor. Writes nothing.
"""
import json, os, urllib.parse, urllib.request
from collections import Counter

GRAPH = "https://graph.facebook.com/v21.0"
TOKEN = os.environ["META_PAGE_TOKEN"]


def _get(path, params=None):
    p = dict(params or {})
    p["access_token"] = TOKEN
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(p)}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def try_get(label, path, params=None):
    print(f"\n--- {label}  ({path}) ---")
    try:
        d = _get(path, params)
        print(json.dumps(d, indent=2, ensure_ascii=False)[:2500])
        return d
    except Exception as e:
        body = e.read().decode()[:500] if hasattr(e, "read") else ""
        print(f"  ERROR {e} {body}")
        return None


def main():
    # 1. What is the mystery actor in the photo permalinks?
    try_get("mystery actor", "122109204921394425",
            {"fields": "id,name,link,category,username"})

    # 2. What does the Page think its own profile / username is?
    try_get("page identity", "me",
            {"fields": "id,name,username,link,category,about,"
                       "has_transitioned_to_new_page_experience,"
                       "new_like_count,fan_count,followers_count,"
                       "is_published,is_webhooks_subscribed,talking_about_count"})

    # 3. Walk the FULL feed, not just page 1, and bucket it.
    print(f"\n{'='*70}\nFULL FEED WALK\n{'='*70}")
    fields = "id,created_time,status_type,permalink_url,is_hidden,is_published"
    rows, url_params, page = [], {"fields": fields, "limit": 100}, 0
    data = _get("me/feed", url_params)
    while True:
        rows.extend(data.get("data", []))
        page += 1
        nxt = (data.get("paging") or {}).get("next")
        if not nxt or page > 10:
            break
        with urllib.request.urlopen(nxt, timeout=60) as r:
            data = json.loads(r.read().decode())

    print(f"  total feed stories: {len(rows)}")
    print(f"  by status_type: {Counter(r.get('status_type') for r in rows)}")

    actors = Counter()
    for r in rows:
        pl = r.get("permalink_url") or ""
        seg = pl.replace("https://www.facebook.com/", "").split("/")
        actors[seg[0] if seg else "?"] += 1
    print(f"  by permalink actor: {dict(actors)}")

    print(f"\n  oldest story: {rows[-1].get('created_time')}  {rows[-1].get('permalink_url')}")
    print(f"  newest story: {rows[0].get('created_time')}  {rows[0].get('permalink_url')}")

    # 4. The visitor-facing surfaces the mobile app actually renders.
    for label, edge in [("posts edge", "me/posts"),
                        ("photos uploaded", "me/photos/uploaded"),
                        ("albums", "me/albums"),
                        ("video reels", "me/video_reels")]:
        try:
            d = _get(edge, {"fields": "id,name,count,created_time", "limit": 100})
            n = len(d.get("data", []))
            print(f"\n  {label:18s} -> {n} items")
            if edge == "me/albums":
                for a in d.get("data", []):
                    print(f"      album {a.get('id')} {a.get('name')!r} count={a.get('count')}")
        except Exception as e:
            print(f"\n  {label:18s} -> ERROR {e}")


if __name__ == "__main__":
    main()
