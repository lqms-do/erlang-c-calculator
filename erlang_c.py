"""
erlang_c.py — Erlang C staffing engine for contact centers.

Part of the LQMS Erlang C Calculator (https://github.com/lqms-do/erlang-c-calculator).
No external dependencies: works with the Python standard library only.

Model assumptions (classic Erlang C / M/M/N queue):
  * Random (Poisson) call arrivals within the interval
  * Exponentially distributed handle times
  * Callers wait indefinitely (no abandonment) and no blocking
  * Steady state within the interval

Typical use:
    >>> from erlang_c import required_agents
    >>> r = required_agents(calls=100, aht=180, interval=1800,
    ...                     target_sl=0.80, threshold=20, shrinkage=0.30)
    >>> r["agents"], r["scheduled_fte"]
    (14, 20)
"""

from __future__ import annotations

import math
from typing import Optional


# --------------------------------------------------------------------------- #
# Core formulas
# --------------------------------------------------------------------------- #
def traffic_intensity(calls: float, aht: float, interval: float = 1800) -> float:
    """Offered load in Erlangs: A = calls x AHT / interval (AHT and interval in seconds)."""
    if calls < 0 or aht <= 0 or interval <= 0:
        raise ValueError("calls must be >= 0; aht and interval must be > 0")
    return calls * aht / interval


def erlang_b(agents: int, traffic: float) -> float:
    """Erlang B blocking probability, computed with the numerically stable recursion."""
    if agents < 0:
        raise ValueError("agents must be >= 0")
    b = 1.0
    for n in range(1, agents + 1):
        b = traffic * b / (n + traffic * b)
    return b


def erlang_c(agents: int, traffic: float) -> float:
    """Probability that a call has to wait (Pw). Returns 1.0 when agents <= traffic."""
    if agents <= traffic:
        return 1.0
    b = erlang_b(agents, traffic)
    return agents * b / (agents - traffic * (1 - b))


def service_level(agents: int, traffic: float, aht: float, threshold: float) -> float:
    """Share of calls answered within `threshold` seconds."""
    if agents <= traffic:
        return 0.0
    pw = erlang_c(agents, traffic)
    return max(0.0, 1.0 - pw * math.exp(-(agents - traffic) * threshold / aht))


def asa(agents: int, traffic: float, aht: float) -> float:
    """Average Speed of Answer in seconds (infinite when understaffed)."""
    if agents <= traffic:
        return math.inf
    return erlang_c(agents, traffic) * aht / (agents - traffic)


def occupancy(agents: int, traffic: float) -> float:
    """Agent occupancy = traffic / agents (capped at 1.0)."""
    if agents <= 0:
        return 1.0
    return min(1.0, traffic / agents)


# --------------------------------------------------------------------------- #
# Staffing solver
# --------------------------------------------------------------------------- #
def interval_metrics(agents: int, calls: float, aht: float, interval: float = 1800,
                     threshold: float = 20) -> dict:
    """All KPIs for a given number of agents on the phones."""
    a = traffic_intensity(calls, aht, interval)
    return {
        "agents": agents,
        "traffic_erlangs": a,
        "prob_wait": erlang_c(agents, a),
        "service_level": service_level(agents, a, aht, threshold),
        "asa_seconds": asa(agents, a, aht),
        "occupancy": occupancy(agents, a),
    }


def required_agents(calls: float, aht: float, interval: float = 1800,
                    target_sl: float = 0.80, threshold: float = 20,
                    max_occupancy: Optional[float] = None,
                    target_asa: Optional[float] = None,
                    shrinkage: float = 0.0,
                    max_agents: int = 10_000) -> dict:
    """
    Minimum agents on the phones meeting every target given, plus scheduled FTE.

    Args:
        calls:          calls offered in the interval
        aht:            average handle time, seconds
        interval:       interval length, seconds (1800 = 30 min)
        target_sl:      service-level goal as a fraction (0.80 = 80%)
        threshold:      service-level answer threshold, seconds (20 -> 80/20)
        max_occupancy:  optional occupancy cap as a fraction (0.85 = 85%)
        target_asa:     optional ASA goal, seconds
        shrinkage:      fraction of paid time unavailable (0.30 = 30%)
    """
    if not 0 <= shrinkage < 1:
        raise ValueError("shrinkage must be between 0 and 1")
    if not 0 < target_sl < 1:
        raise ValueError("target_sl must be between 0 and 1")

    a = traffic_intensity(calls, aht, interval)
    if a == 0:
        n = 0
    else:
        n = max(1, math.floor(a) + 1)
        while n <= max_agents:
            ok = service_level(n, a, aht, threshold) >= target_sl
            if max_occupancy is not None:
                ok = ok and occupancy(n, a) <= max_occupancy
            if target_asa is not None:
                ok = ok and asa(n, a, aht) <= target_asa
            if ok:
                break
            n += 1
        else:
            raise RuntimeError("No staffing level found within max_agents")

    result = interval_metrics(n, calls, aht, interval, threshold) if n else {
        "agents": 0, "traffic_erlangs": 0.0, "prob_wait": 0.0,
        "service_level": 1.0, "asa_seconds": 0.0, "occupancy": 0.0,
    }
    result["scheduled_fte"] = math.ceil(n / (1 - shrinkage)) if n else 0
    return result


def staffing_table(calls: float, aht: float, interval: float = 1800,
                   threshold: float = 20, extra: int = 8) -> list[dict]:
    """KPIs for every staffing level from the minimum stable N up to N + extra."""
    a = traffic_intensity(calls, aht, interval)
    start = max(1, math.floor(a) + 1)
    return [interval_metrics(n, calls, aht, interval, threshold)
            for n in range(start, start + extra + 1)]


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #
def _main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="LQMS Erlang C staffing calculator")
    p.add_argument("--calls", type=float, required=True, help="calls offered in the interval")
    p.add_argument("--aht", type=float, required=True, help="average handle time (seconds)")
    p.add_argument("--interval", type=float, default=1800, help="interval length (seconds)")
    p.add_argument("--sl", type=float, default=80, help="service-level target (%%)")
    p.add_argument("--threshold", type=float, default=20, help="answer threshold (seconds)")
    p.add_argument("--max-occ", type=float, default=None, help="maximum occupancy (%%)")
    p.add_argument("--asa", type=float, default=None, help="ASA target (seconds)")
    p.add_argument("--shrinkage", type=float, default=0, help="shrinkage (%%)")
    args = p.parse_args()

    r = required_agents(
        calls=args.calls, aht=args.aht, interval=args.interval,
        target_sl=args.sl / 100, threshold=args.threshold,
        max_occupancy=None if args.max_occ is None else args.max_occ / 100,
        target_asa=args.asa, shrinkage=args.shrinkage / 100,
    )
    print(f"Traffic intensity : {r['traffic_erlangs']:.2f} Erlangs")
    print(f"Agents required   : {r['agents']}")
    print(f"Scheduled FTE     : {r['scheduled_fte']}  (shrinkage {args.shrinkage:.0f}%)")
    print(f"Service level     : {r['service_level']:.1%} in {args.threshold:.0f}s")
    print(f"ASA               : {r['asa_seconds']:.1f} s")
    print(f"Occupancy         : {r['occupancy']:.1%}")
    print(f"Probability wait  : {r['prob_wait']:.1%}")


if __name__ == "__main__":
    _main()
