"""
Caption post-processing shared by run.py / run_statics.py / run_reels.py.

Added 2026-07-24 after the reach audit (Hirra-Social-Reach-Audit-2026-07-24.md),
which found two caption-level problems across all 45 published posts:

  1. Every post carried the same appended download link. On Instagram captions are
     not clickable, so it bought nothing; on Facebook an outbound link in the post
     body depresses reach. The link now lives in the bios instead.
  2. Every static caption carried an identical 14-hashtag block and every reel an
     identical 6-tag block. An unchanging tag set across 128 posts is a duplicate
     content signal on both platforms.

retag() strips whatever tags the stored caption already has and appends a rotated
set, chosen deterministically from the post id so a republish is byte-identical.
"""
import hashlib
import re

# Two anchors always present so the topic stays legible, then a rotating tail.
CORE = ["#cathealth", "#catcare"]

POOL_EN = [
    "#cats", "#catsofinstagram", "#catlovers", "#petcare", "#catmom",
    "#catlife", "#petparents", "#felinehealth", "#catwellness", "#catowner",
    "#kittens", "#seniorcats", "#catsofig", "#pethealth", "#catparents",
]

POOL_AR = ["#قطط", "#صحة_القطط", "#رعاية_القطط", "#قطط_الخليج"]

TAG_RE = re.compile(r"(?:^|\s)#[^\s#]+")


def strip_tags(text):
    """Remove hashtags and any now-empty trailing lines."""
    out = TAG_RE.sub(" ", text)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in out.split("\n")]
    collapsed = []
    for ln in lines:
        if not ln and collapsed and not collapsed[-1]:
            continue          # never leave a double blank where a tag block was
        collapsed.append(ln)
    while collapsed and not collapsed[-1]:
        collapsed.pop()
    return "\n".join(collapsed).strip()


def pick(seed, pool, n):
    """Deterministic rotation: same seed always yields the same set."""
    h = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16)
    chosen, avail = [], list(pool)
    for _ in range(min(n, len(avail))):
        h, i = divmod(h, len(avail))
        chosen.append(avail.pop(i))
    return chosen


def retag(caption, post_id, n_en=5, n_ar=2):
    """Strip stored tags, append a rotated set. No download link is added."""
    body = strip_tags(caption)
    tags = CORE + pick(post_id, POOL_EN, n_en) + pick(post_id + "|ar", POOL_AR, n_ar)
    return body + "\n\n" + " ".join(tags)
