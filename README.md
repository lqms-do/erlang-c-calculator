# Erlang C Staffing Calculator

**By [LQMS – Lazala Quality Management Solution](https://lqms.com.do)** · *BPO for BPOs*

This calculator works out how many agents a contact center needs on the phones in each interval to meet its **service level, ASA and occupancy** targets. It also converts that number into **scheduled FTE** after shrinkage.

### ▶ [Open the live calculator](https://lqms-do.github.io/erlang-c-calculator/)

No installation is needed. It runs in any browser.

---

## What it calculates

| Output | Meaning |
|---|---|
| **Traffic intensity (Erlangs)** | Workload in the interval: `calls × AHT ÷ interval` |
| **Agents on phones** | The minimum agents that meet every target you set |
| **Scheduled FTE** | Agents ÷ (1 − shrinkage), rounded up |
| **Service level** | % of calls answered within the threshold (e.g. 80/20) |
| **ASA** | Average speed of answer, in seconds |
| **Occupancy** | % of logged-in time agents spend handling calls |
| **Probability of wait** | Erlang C probability that a caller has to queue |

The **staffing sensitivity table** shows how each additional agent changes service level, ASA and occupancy. Use it to discuss cost against service with operations and finance.

---

## Validation

The engine was cross-checked against the open-source [`pyworkforce`](https://github.com/rodrigo-arenas/pyworkforce) library and gives identical results:

| Scenario: 100 calls / 30 min, AHT 180 s, 80/20, max occupancy 85%, shrinkage 30% | Result |
|---|---|
| Traffic intensity | 10.00 Erlangs |
| Agents required | **14** |
| Scheduled FTE | **20** |
| Service level achieved | 88.8% |
| ASA | 7.8 s |
| Occupancy | 71.4% |
| Probability of wait | 17.4% |

---

## Use it in Python

`erlang_c.py` uses only the Python standard library. There is nothing to install.

```python
from erlang_c import required_agents, staffing_table

r = required_agents(calls=100, aht=180, interval=1800,
                    target_sl=0.80, threshold=20,
                    max_occupancy=0.85, shrinkage=0.30)
print(r["agents"], r["scheduled_fte"])   # 14 20
```

From the command line:

```bash
python erlang_c.py --calls 100 --aht 180 --sl 80 --threshold 20 --max-occ 85 --shrinkage 30
```

Run the tests:

```bash
python -m unittest test_erlang_c.py
```

---

## Model assumptions and limits

Erlang C is the industry-standard starting point for interval staffing. It relies on these simplifying assumptions:

- Calls arrive at random (Poisson) and handle times are exponentially distributed.
- **No abandonment**: every caller waits until answered. With high abandonment, Erlang C *overstates* the staff needed. Consider Erlang A in that case.
- Each interval is in steady state, with no carry-over of queued calls.
- Agents are fully interchangeable, with a single skill.

Treat the output as the **minimum staffing floor**. Validate it against your forecast accuracy, schedule adherence and real-time performance.

---

## Files

| File | Purpose |
|---|---|
| `index.html` | Browser calculator, published with GitHub Pages |
| `erlang_c.py` | Python engine and command-line tool |
| `test_erlang_c.py` | Unit tests |

---

## Need more than a calculator?

LQMS helps contact centers and BPOs with **workforce management, quality assurance, COPC and ISO 9001 readiness, and Lean Six Sigma**.

📧 [alazala@lqms.com.do](mailto:alazala@lqms.com.do) · 🌐 [lqms.com.do](https://lqms.com.do)

---

MIT License © 2026 LQMS – Lazala Quality Management Solution
