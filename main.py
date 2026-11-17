"""Deterministic launch-curve analog forecast; Python 3.13 standard library."""
import json
import math
import os
from datetime import datetime
from pathlib import Path
from statistics import median

LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
Z = (-1.645, -0.674, 0.0, 0.674, 1.645)


def instant(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def hourly(rows, start, cutoff=None):
    """Use observed buckets only: never fill a missing hour with a future point."""
    groups = {}
    for row in rows or []:
        at = instant(row.get("from") or row["at"])
        value = row.get("viewers")
        if value is None or (cutoff is not None and at >= cutoff):
            continue
        index = math.floor((at - start) / 3600)
        groups.setdefault(index, []).append(max(1.0, float(value)))
    return {index: sum(values) / len(values) for index, values in groups.items()}


def regime(text, platforms=""):
    text = text.lower().split("research note:")[0]
    # Negated early access and a mere preload must not imply an early launch.
    clean = text.replace("no early access", "").replace("no early-access", "")
    if "early access" in clean or "early-access" in clean:
        return "early"
    rolling = "midnight local" in text or "rolling" in text
    global_time = "simultaneous" in text or "single global" in text
    if rolling and global_time and "pc" in platforms.lower():
        return "mixed"
    if rolling:
        return "rolling"
    if global_time:
        return "global"
    return "unknown"


def feature(curve, anchor, lo, hi):
    values = [math.log(curve[t] / anchor) for t in range(lo, hi) if t in curve]
    return median(values) if values else None


def analogs(case):
    start = instant(case["day_start"])
    cutoff = min(instant(case["checkpoint"]), start + 3600)
    known = max(1.0, float(case["known"][0]["viewers"]))
    history = hourly(case.get("history_hourly"), start, cutoff)
    if not history:
        history = hourly(case.get("history"), start, cutoff)
    history[0] = known
    target_regime = regime(str(case.get("notes", "")))
    windows = ((-3, 0), (-8, -3), (-16, -8), (-24, -16))
    target_features = [feature(history, known, lo, hi) for lo, hi in windows]
    candidates = []
    for comp in case.get("comparables") or []:
        if "target-history" in str(comp.get("unlock", "")).lower():
            continue
        if comp.get("name") == case.get("game", {}).get("name"):
            continue
        curve = hourly(comp.get("hourly"), instant(comp["day_start"]))
        anchor = curve.get(0)
        if anchor is None or anchor < 10:
            continue
        kind = regime(str(comp.get("unlock", "")), str(comp.get("platforms", "")))
        if kind == target_regime:
            prior = 1.0
        elif "early" in (kind, target_regime):
            prior = 0.07
        elif {kind, target_regime} == {"rolling", "global"}:
            prior = 0.08
        elif kind == "mixed":
            prior = 0.45
        else:
            prior = 0.35
        platforms = str(comp.get("platforms", "")).lower()
        if target_regime == "rolling" and "pc" not in platforms:
            prior *= 1.7
        errors = []
        for observed, (lo, hi) in zip(target_features, windows):
            other = feature(curve, anchor, lo, hi)
            if observed is not None and other is not None:
                errors.append(min(9.0, (observed - other) ** 2))
        distance = sum(errors) / len(errors) if errors else 0.5
        # Missing analog history is missing evidence, not a good trajectory match.
        # With no target history, all analogs keep the same neutral coverage.
        observed_windows = sum(value is not None for value in target_features)
        overlap = (len(errors) + 1) / (observed_windows + 1)
        # Relative trajectories matter most; scale is a weak secondary signal.
        size = min(9.0, math.log(anchor / known) ** 2)
        weight = prior * overlap * math.exp(-distance / 1.4 - 0.10 * size)
        candidates.append((curve, anchor, weight))
    return known, candidates, sum(x is not None for x in target_features)


def mixture_quantile(components, tau):
    total = sum(weight for _, _, weight in components)
    lo = min(mu - 9 * sigma for mu, sigma, _ in components)
    hi = max(mu + 9 * sigma for mu, sigma, _ in components)
    for _ in range(55):
        mid = (lo + hi) / 2
        cdf = sum(weight * 0.5 * (1 + math.erf((mid - mu) / (sigma * math.sqrt(2))))
                  for mu, sigma, weight in components) / total
        if cdf < tau:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def predict(case):
    known, candidates, features = analogs(case)
    hours = []
    for hour in range(2, 25):
        index = hour - 1
        available = [(curve[index], anchor, weight) for curve, anchor, weight in candidates
                     if index in curve and weight > 0]
        total = sum(weight for _, _, weight in available)
        if not available or total < 1e-12:
            q = [known * math.exp(z * 0.15 * math.sqrt(index)) for z in Z]
        else:
            effective = total ** 2 / sum(weight ** 2 for _, _, weight in available)
            # Kernel smoothing prevents an empirical tail collapsing to one analog.
            sigma = 0.12 + 0.035 * math.sqrt(index) + 0.16 / math.sqrt(effective)
            sigma += 0.035 * (4 - features)
            components = [(math.log(value / anchor), sigma, weight / total)
                          for value, anchor, weight in available]
            # A small wide fallback protects sparse or mismatched history.
            fallback = 0.04 + 0.04 * (4 - features) + 0.12 / max(1.0, effective)
            components.append((0.0, max(0.3, 0.15 * math.sqrt(index)), fallback))
            q = [known * math.exp(mixture_quantile(components, tau)) for tau in LEVELS]
        q = [round(min(1e9, max(0.01, value)), 4) for value in q]
        hours.append({"hour": hour, "q": q})
    return {"hours": hours}


def main():
    inputs = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    outputs = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    outputs.mkdir(parents=True, exist_ok=True)
    for path in sorted(inputs.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        result = predict(case)
        (outputs / (path.stem + ".out")).write_text(
            json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n",
            encoding="utf-8")


if __name__ == "__main__":
    main()
