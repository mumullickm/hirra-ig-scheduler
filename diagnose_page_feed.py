#!/usr/bin/env python3
"""
Read-only diagnostic, pass 3.

Pass 1: timeline is clean. 25+ posts, all EVERYONE, none hidden.
Pass 2: 67 feed stories = 47 added_photos + 20 added_video. /me/albums reports
        only Cover photos and Profile pictures, and the oldest photo story
        carries ?substory_index=... which is Facebook's marker for a story that
        is one slice of an aggregated parent story.

Hypothesis under test: every photo lands in one implicit uploads album, so
Facebook collapses them into a small number of "added N new photos" parent
stories. A visitor scrolling the Page sees those few parents, not 47 posts, and
a newly published photo is folded into an existing parent instead of appearing
as a new story. Reels sit on a separate tab and never enter the Posts list.

Checks: story text, parent_id, subattachment counts and album per photo post.
Writes nothing.
"""
import json, os, urllib.parse, urllib.request
from collections import Counter, defaultdict

GRAPH = "https://graph.facebook.com/v21.0"
TOKEN = os.environ["META_PAGE_TOKEN"]


def _get(path, params=None):
    p = dict(params or {})
    p["access_token"] = TOKEN
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(p)}"
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    fields = ("id,created_time,status_type,permalink_url,story,parent_id,"
              "attachments{type,title,url,subattachments}")
    rows, page = [], 0
    data = _get("me/feed", {"fields": fields, "limit": 50})
    while True:
        rows.extend(data.get("data", []))
        page += 1
        nxt = (data.get("paging") or {}).get("next")
        if not nxt or page > 6:
            break
        with urllib.request.urlopen(nxt, timeout=60) as r:
            data = json.loads(r.read().decode())

    photos = [r for r in rows if r.get("status_type") == "added_photos"]
    print(f"total stories {len(rows)}  photo stories {len(photos)}")

    print(f"\n{'='*70}\nAGGREGATION CHECK: photo stories\n{'='*70}")
    substory = 0
    subcounts = Counter()
    for r in photos[:20]:
        att = ((r.get("attachments") or {}).get("data") or [{}])[0]
        subs = ((att.get("subattachments") or {}).get("data") or [])
        pl = r.get("permalink_url") or ""
        has_sub = "substory_index" in pl
        substory += has_sub
        subcounts[len(subs)] += 1
        print(f"\n  {r.get('created_time')}  {r.get('id')}")
        print(f"    story         {(r.get('story') or '(none)')[:90]}")
        print(f"    parent_id     {r.get('parent_id')}")
        print(f"    att type      {att.get('type')}  title={str(att.get('title'))[:50]!r}")
        print(f"    subattach     {len(subs)}")
        print(f"    substory_idx  {has_sub}")

    for r in photos[20:]:
        att = ((r.get("attachments") or {}).get("data") or [{}])[0]
        subs = ((att.get("subattachments") or {}).get("data") or [])
        subcounts[len(subs)] += 1
        substory += "substory_index" in (r.get("permalink_url") or "")

    print(f"\n  photo stories carrying substory_index : {substory}/{len(photos)}")
    print(f"  subattachment count distribution      : {dict(subcounts)}")

    # Which album does each uploaded photo belong to? If they all share one
    # album, that is the aggregation bucket.
    print(f"\n{'='*70}\nALBUM OF EACH UPLOADED PHOTO\n{'='*70}")
    ph = _get("me/photos/uploaded", {"fields": "id,created_time,album{id,name,count}", "limit": 100})
    albums = Counter()
    for p in ph.get("data", []):
        a = p.get("album") or {}
        albums[f"{a.get('id')} {a.get('name')!r} count={a.get('count')}"] += 1
    print(f"  uploaded photos: {len(ph.get('data', []))}")
    for k, v in albums.items():
        print(f"    {v:3d} photos in album {k}")

    # Reels are a separate surface. Confirm how many and that they are not in
    # the same bucket as the photo stories.
    vids = [r for r in rows if r.get("status_type") == "added_video"]
    print(f"\n  video/reel stories: {len(vids)}")
    print(f"  reel permalinks all /reel/ form: "
          f"{all('/reel/' in (v.get('permalink_url') or '') for v in vids)}")


if __name__ == "__main__":
    main()
