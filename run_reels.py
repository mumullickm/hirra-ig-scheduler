"""
Hirra REELS auto-publisher (additive, IG + Facebook), cloud edition.

Separate from run.py (the image publisher) so the live FLUX image campaign is
untouched. Publishes any reel slot whose time has passed and isn't yet posted,
to BOTH Instagram Reels and Facebook Reels, using the same non-expiring
META_PAGE_TOKEN. Self-healing: a missed/late cron tick catches up next run.

Reads:  reels.json ([{reel, iso}]), reel_captions.json, config.json (videoBase, igUserId)
State:  posted_reels.json ({reel: {"ig": id|false, "fb": id|false}}) committed back by CI
Secret: META_PAGE_TOKEN (env)
"""
import datetime, json, os, time, urllib.error, urllib.parse, urllib.request

GRAPH = "https://graph.facebook.com/v21.0"
TOKEN = os.environ["META_PAGE_TOKEN"]
CFG = json.load(open("config.json"))
IG = CFG["igUserId"]
VIDEO_BASE = CFG["videoBase"]
CAPS = json.load(open("reel_captions.json"))
DL = ("\n\nGet Hirra, free: aykizintelligence.com/hirra/get"
      "\nحمّلي هِرّة مجانًا: aykizintelligence.com/hirra/get")


def _get(path, params=None):
    p = dict(params or {}); p["access_token"] = TOKEN
    return json.loads(urllib.request.urlopen(
        f"{GRAPH}/{path}?" + urllib.parse.urlencode(p), timeout=30).read())


def _post(path, params):
    p = dict(params); p["access_token"] = TOKEN
    req = urllib.request.Request(f"{GRAPH}/{path}",
                                 data=urllib.parse.urlencode(p).encode(), method="POST")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=180).read())
    except urllib.error.HTTPError as e:
        return {"_error": json.loads(e.read().decode()).get("error", {})}


def video_url(reel): return f"{VIDEO_BASE}/{reel}.mp4"
def caption_for(reel): return CAPS[reel] + DL


def publish_ig_reel(reel):
    cont = _post(f"{IG}/media", {"media_type": "REELS", "video_url": video_url(reel),
                                 "caption": caption_for(reel), "share_to_feed": "true"})
    if "id" not in cont:
        return False, f"IG container error {cont.get('_error')}"
    cid = cont["id"]
    for _ in range(40):                       # up to ~10 min for video processing
        st = _get(cid, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            return False, "IG container ERROR"
        time.sleep(15)
    pub = _post(f"{IG}/media_publish", {"creation_id": cid})
    return ("id" in pub), (pub.get("id") or f"IG publish error {str(pub.get('_error'))[:160]}")


def publish_fb_reel(page_id, reel):
    start = _post(f"{page_id}/video_reels", {"upload_phase": "start"})
    vid = start.get("video_id"); up = start.get("upload_url")
    if not (vid and up):
        return False, f"FB start error {start.get('_error')}"
    req = urllib.request.Request(up, data=b"", method="POST",
                                 headers={"Authorization": f"OAuth {TOKEN}",
                                          "file_url": video_url(reel)})
    try:
        urllib.request.urlopen(req, timeout=180).read()
    except urllib.error.HTTPError as e:
        return False, f"FB upload error {e.read()[:160].decode(errors='replace')}"
    fin = _post(f"{page_id}/video_reels", {"upload_phase": "finish", "video_id": vid,
                                           "video_state": "PUBLISHED",
                                           "description": caption_for(reel)})
    ok = fin.get("success") or fin.get("post_id") or fin.get("id")
    return bool(ok), (str(fin.get("post_id") or vid) if ok else f"FB finish error {fin.get('_error')}")


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    reels = json.load(open("reels.json"))
    state = json.load(open("posted_reels.json")) if os.path.exists("posted_reels.json") else {}
    now = datetime.datetime.now(datetime.timezone.utc)
    page_id = _get("me").get("id")
    due = [r for r in reels
           if datetime.datetime.fromisoformat(r["iso"].replace("Z", "+00:00")) <= now
           and not (state.get(r["reel"], {}).get("ig") and state.get(r["reel"], {}).get("fb"))]
    if not due:
        print(f"[{stamp}] no reels due"); return
    for r in due:
        reel = r["reel"]; st = state.setdefault(reel, {"ig": False, "fb": False})
        if not st["ig"]:
            ok, info = publish_ig_reel(reel); st["ig"] = info if ok else False
            print(f"[{stamp}] IG reel {reel}: {'published '+info if ok else info}")
        if not st["fb"]:
            ok, info = publish_fb_reel(page_id, reel); st["fb"] = info if ok else False
            print(f"[{stamp}] FB reel {reel}: {'published '+info if ok else info}")
    json.dump(state, open("posted_reels.json", "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
