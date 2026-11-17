# Launch-day Twitch forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/rikimaru04190820-ux/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/rikimaru04190820-ux/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A deterministic Python 3.13 standard-library program for make.fun's GTA VI Twitch viewer forecasting bounty.

Run `python main.py` with `MAKEFUN_INPUT_DIR` and `MAKEFUN_OUTPUT_DIR` set to local directories. Otherwise it uses `/input` and `/output`. Each input `*.in` produces a matching `*.out` containing 23 hours and five positive ordered viewer quantiles.

The model weights historical launch curves by their initial audience and observed pre-checkpoint trajectory. Rolling midnight, simultaneous global, mixed-platform and early-access launches receive different prior weights. It estimates quantiles from a smoothed mixture of relative launch curves. Missing observations are not filled with future data, the target-history comparable is excluded, and sparse inputs use broader uncertainty or the documented baseline fallback. No model calls, network access, third-party packages or randomness are needed.

Built from scratch in the current recorded Codex session. Local evaluation and limitations are in the preparation folder outside this submission directory. Official scoring has not run.

Competition: https://make.fun/bounty/gta6-twitch-ccu-forecast-01

Local leave-one-launch-out diagnostics across 37 historical comparables scored a mean log pinball loss of 0.516720 versus 0.929650 for the documented house baseline formula. This is retrospective shape-transfer evaluation, not an as-of backtest or an official score. The four public inputs passed format, ordering and byte-for-byte repeatability checks; their official answers were not included in the kit.
