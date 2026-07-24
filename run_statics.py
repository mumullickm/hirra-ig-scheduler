"""
Hirra STATICS auto-publisher (additive, IG feed + Facebook feed).

Posts the 60 Nano Banana statics 2/day from Jul 12 to both Instagram (feed image)
and Facebook (feed photo), using the same META_PAGE_TOKEN. Separate from run.py
(FLUX campaign) and run_reels.py. Self-healing.

Reads:  statics.json ([{static, iso}]), static_captions.json, config.json (staticBase, igUserId)
State:  posted_statics.json ({static: {"ig": id|false, "fb": id|false}}) committed by CI
Secret: META_PAGE_TOKEN (env)
"""
import datetime, json, os, time, urllib.error, urllib.parse, urllib.request

from caption_utils import retag

GRAPH = "https://graph.facebook.com/v21.0"
TOKEN = os.environ["META_PAGE_TOKEN"]
CFG = json.load(open("config.json"))
IG = CFG["igUserId"]
STATIC_BASE = CFG["staticBase"]
CAPS = json.load(open("static_captions.json"))


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


def image_url(sid): return f"{STATIC_BASE}/{sid}.jpg"
def caption_for(sid): return retag(CAPS[sid], sid)


def publish_ig_image(sid):
    cont = _post(f"{IG}/media", {"image_url": image_url(sid), "caption": caption_for(sid)})
    if "id" not in cont:
        return False, f"IG container error {cont.get('_error')}"
    cid = cont["id"]
    for _ in range(12):
        st = _get(cid, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            return False, "IG container ERROR"
        time.sleep(5)
    pub = _post(f"{IG}/media_publish", {"creation_id": cid})
    return ("id" in pub), (pub.get("id") or f"IG publish error {str(pub.get('_error'))[:160]}")


def publish_fb_photo(page_id, sid):
    r = _post(f"{page_id}/photos", {"url": image_url(sid), "message": caption_for(sid),
                                    "published": "true"})
    ok = r.get("id") or r.get("post_id")
    return bool(ok), (str(r.get("post_id") or r.get("id")) if ok else f"FB photo error {r.get('_error')}")


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sched = json.load(open("statics.json"))
    state = json.load(open("posted_statics.json")) if os.path.exists("posted_statics.json") else {}
    now = datetime.datetime.now(datetime.timezone.utc)
    page_id = _get("me").get("id")
    due = [s for s in sched
           if datetime.datetime.fromisoformat(s["iso"].replace("Z", "+00:00")) <= now
           and not (state.get(s["static"], {}).get("ig") and state.get(s["static"], {}).get("fb"))]
    if not due:
        print(f"[{stamp}] no statics due"); return
    for s in due:
        sid = s["static"]; st = state.setdefault(sid, {"ig": False, "fb": False})
        if not st["ig"]:
            ok, info = publish_ig_image(sid); st["ig"] = info if ok else False
            print(f"[{stamp}] IG static {sid}: {'published '+info if ok else info}")
        if not st["fb"]:
            ok, info = publish_fb_photo(page_id, sid); st["fb"] = info if ok else False
            print(f"[{stamp}] FB static {sid}: {'published '+info if ok else info}")
    json.dump(state, open("posted_statics.json", "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
