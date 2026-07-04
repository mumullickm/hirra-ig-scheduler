# hirra-ig-scheduler

Cloud auto-publisher for Hirra's Instagram (`@hirra.cat`). Private, machine-independent.

Instagram's Content Publishing API has **no native scheduling**, so a GitHub
Actions cron fires twice daily and publishes any post whose slot has passed and
isn't yet posted. Facebook is handled separately by native Graph API scheduling
(posts live on Facebook's servers), so this repo is **IG-only**.

Mirrors `mumullickm/wasilah-ig-scheduler`.

## Files
- `run.py` — self-contained (stdlib only), publishes due IG slots, updates `posted.json`.
- `schedule.json` — `[{piece, iso}]` slots (2/day, from the Hirra Social pipeline).
- `captions.json` — EN/AR/tags per piece (copied from the pipeline).
- `config.json` — non-secret IG user id + hosted image base.
- `posted.json` — state; the workflow commits it back each run with `[skip ci]`.
- `.github/workflows/publish.yml` — cron `0 6 * * *` + `30 16 * * *` UTC (10:00 + 20:30 Dubai), plus `workflow_dispatch`.

## Secret
`META_PAGE_TOKEN` — the non-expiring Hirra **Page** token (`expires_at=0`,
scope `instagram_content_publish`). Never printed.

## Change the schedule / captions
Edit `schedule.json` / `captions.json` in the Hirra Social pipeline, copy them
here, commit, push. Images must be publicly hosted first
(`mumullickm.github.io/hirra-campaign/outputs/campaign/piece-NN.jpg`).

## Check runs
`gh run list -R mumullickm/hirra-ig-scheduler`
