"""One-shot: upload the paid ad cuts to the Facebook Page as UNPUBLISHED (dark)
videos so they can be used as ad creatives, without appearing on the timeline.
Prints the returned video IDs. Secret: META_PAGE_TOKEN (env).
"""
import json, os, urllib.error, urllib.parse, urllib.request

GRAPH = "https://graph.facebook.com/v21.0"
TOKEN = os.environ["META_PAGE_TOKEN"]
BASE = "https://mumullickm.github.io/hirra-calendar/assets/ads"

VIDEOS = [
    ("hirra-ad-en.mp4", "Hirra ad EN"),
    ("hirra-ad-ar.mp4", "Hirra ad AR"),
]


def post(path, params):
    p = dict(params)
    p["access_token"] = TOKEN
    req = urllib.request.Request(
        f"{GRAPH}/{path}", data=urllib.parse.urlencode(p).encode(), method="POST")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=180).read())
    except urllib.error.HTTPError as e:
        return {"_error": json.loads(e.read().decode()).get("error", {})}


for fname, title in VIDEOS:
    r = post("me/videos", {
        "file_url": f"{BASE}/{fname}",
        "title": title,
        "description": title,
        "published": "false",
    })
    print(f"{fname}: {json.dumps(r)}")
