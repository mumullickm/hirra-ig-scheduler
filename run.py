"""
Hirra Instagram auto-publisher, cloud edition (GitHub Actions cron).

IG's Content Publishing API has no native scheduling, so this runs on a GH
Actions schedule (see .github/workflows/publish.yml) and publishes any slot
whose time has passed and isn't yet posted. Fully machine-independent: no Mac,
no launchd. Mirrors mumullickm/wasilah-ig-scheduler.

FB is handled separately by native Graph API scheduling (posts already live on
Facebook's servers), so this repo is IG-only.

Reads:  schedule.json (piece + iso slots), captions.json, config.json
State:  posted.json (list of published piece numbers) -- committed back by CI
Secret: META_PAGE_TOKEN (non-expiring Hirra Page token) from the env
"""
import datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"
TOKEN = os.environ["META_PAGE_TOKEN"]
CFG = json.load(open("config.json"))
IG = CFG["igUserId"]
IMG_BASE = CFG["imgBase"]
CAPTIONS = json.load(open("captions.json"))


def _get(path, params=None):
    p = dict(params or {}); p["access_token"] = TOKEN
    return json.loads(urllib.request.urlopen(
        f"{GRAPH}/{path}?" + urllib.parse.urlencode(p), timeout=30).read())


def _post(path, params):
    p = dict(params); p["access_token"] = TOKEN
    req = urllib.request.Request(f"{GRAPH}/{path}",
                                 data=urllib.parse.urlencode(p).encode(), method="POST")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=120).read())
    except urllib.error.HTTPError as e:
        return {"_error": json.loads(e.read().decode()).get("error", {})}


def caption_for(no):
    c = CAPTIONS[str(no)]
    return retag(c["en"] + "\n\n" + c["ar"] + "\n\n" + c["tags"], str(no))


def img_for(no):
    return f"{IMG_BASE}/piece-{int(no):02d}.jpg"


def publish_ig(no):
    cont = _post(f"{IG}/media", {"image_url": img_for(no), "caption": caption_for(no)})
    if "id" not in cont:
        return False, f"container error {cont.get('_error')}"
    cid = cont["id"]
    # Images are usually ready immediately; poll briefly to be safe.
    for _ in range(12):
        st = _get(cid, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            return False, "container ERROR"
        time.sleep(5)
    pub = _post(f"{IG}/media_publish", {"creation_id": cid})
    if "id" in pub:
        return True, pub["id"]
    return False, f"publish error {str(pub.get('_error'))[:160]}"


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sched = json.load(open("schedule.json"))
    posted = set(str(x) for x in json.load(open("posted.json")))
    now = datetime.datetime.now(datetime.timezone.utc)
    due = [s for s in sched
           if datetime.datetime.fromisoformat(s["iso"].replace("Z", "+00:00")) <= now
           and str(s["piece"]) not in posted]
    if not due:
        print(f"[{stamp}] nothing due ({len(posted)} posted)"); return
    for s in due:
        ok, info = publish_ig(s["piece"])
        print(f"[{stamp}] IG piece {s['piece']} ({s['iso']}): "
              f"{'published ' + info if ok else info}")
        if ok:
            posted.add(str(s["piece"]))
    json.dump(sorted(posted, key=int), open("posted.json", "w"), indent=2)


if __name__ == "__main__":
    main()
