#!/usr/bin/env python3
"""
Read-only diagnostic: what does the Hirra Page timeline actually contain?

Answers one question. Posts are confirmed public by permalink, yet a visitor on
the Facebook mobile app sees only a handful of stories on the Page. Public by
permalink and present on the timeline are two different things. A post can be
`privacy: EVERYONE` and still be absent from the Page feed if it is hidden from
the timeline, unpublished, or restricted by country or age.

Prints, per post: id, created_time, is_published, is_hidden, is_expired,
privacy, targeting restrictions, and permalink. Writes nothing, changes nothing.
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


def dump(label, edge, fields, limit=25):
    print(f"\n{'='*70}\n{label}  (GET /me/{edge})\n{'='*70}")
    try:
        data = _get(f"me/{edge}", {"fields": fields, "limit": limit})
    except Exception as e:
        body = ""
        if hasattr(e, "read"):
            body = e.read().decode()[:600]
        print(f"  ERROR: {e} {body}")
        return []
    rows = data.get("data", [])
    print(f"  count returned: {len(rows)}")
    for p in rows:
        print(f"\n  id           {p.get('id')}")
        print(f"  created      {p.get('created_time')}")
        print(f"  is_published {p.get('is_published')}")
        print(f"  is_hidden    {p.get('is_hidden')}")
        print(f"  is_expired   {p.get('is_expired')}")
        print(f"  status_type  {p.get('status_type')}")
        priv = p.get("privacy") or {}
        print(f"  privacy      value={priv.get('value')!r} desc={priv.get('description')!r} "
              f"allow={priv.get('allow')!r} deny={priv.get('deny')!r}")
        if p.get("targeting"):
            print(f"  targeting    {json.dumps(p['targeting'])}")
        if p.get("feed_targeting"):
            print(f"  feed_target  {json.dumps(p['feed_targeting'])}")
        print(f"  permalink    {p.get('permalink_url')}")
        msg = (p.get("message") or "").replace("\n", " ")[:70]
        print(f"  message      {msg}")
    return rows


def main():
    me = _get("me", {"fields": "id,name,is_published,link,"
                               "country_page_likes,is_permanently_closed,"
                               "verification_status,fan_count,followers_count"})
    print("PAGE")
    print(json.dumps(me, indent=2, ensure_ascii=False))

    # Page-level gates that hide every story from a given viewer.
    for edge, fields in [
        ("restrictions", "age,alcohol,country,type"),
        ("settings", "setting,value"),
    ]:
        try:
            print(f"\n--- /me/{edge} ---")
            print(json.dumps(_get(f"me/{edge}", {"fields": fields}), indent=2)[:3000])
        except Exception as e:
            print(f"  (unavailable: {e})")

    fields = ("id,created_time,is_published,is_hidden,is_expired,status_type,"
              "permalink_url,message,privacy,targeting,feed_targeting")

    # published_posts = what the admin sees. feed = what a visitor's Page feed is
    # built from. A gap between these two is the bug.
    pub = dump("PUBLISHED POSTS (admin view)", "published_posts", fields)
    feed = dump("FEED (visitor-facing timeline)", "feed", fields)

    print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
    print(f"  published_posts returned : {len(pub)}")
    print(f"  feed returned            : {len(feed)}")
    hidden = [p['id'] for p in pub if p.get('is_hidden')]
    unpub = [p['id'] for p in pub if p.get('is_published') is False]
    nonpublic = [(p['id'], (p.get('privacy') or {}).get('value'))
                 for p in pub if (p.get('privacy') or {}).get('value') not in ("EVERYONE", "", None)]
    print(f"  hidden from timeline     : {len(hidden)} {hidden[:10]}")
    print(f"  is_published false       : {len(unpub)} {unpub[:10]}")
    print(f"  privacy not EVERYONE     : {len(nonpublic)} {nonpublic[:10]}")


if __name__ == "__main__":
    main()
