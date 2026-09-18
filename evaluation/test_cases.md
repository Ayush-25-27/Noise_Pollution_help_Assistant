# Evaluation test cases

| Location | dB | Zone | Time | Duration | Expect exceeds? | Expect source mentions |
|---|---|---|---|---|---|---|
| Any residential street | 50 | residential | day | sustained | No (limit 55) | traffic |
| Any residential street | 50 | residential | night | sustained | Yes (limit 45) | generator/machinery |
| Near a school | 60 | silence | day | sustained | Yes (limit 50) | construction/industrial |
| Near a hospital | 42 | silence | night | brief | Yes (limit 40) | event/loudspeaker (if db≥85) or unclear pattern |
| Market street | 70 | commercial | day | sustained | Yes (limit 65) | traffic or construction |
| Factory zone | 80 | industrial | day | sustained | Yes (limit 75) | construction/industrial |
| (omit db/time/duration) | — | residential | — | — | uses sample_data fallback | data_source = "sample_data (no reading logged yet)" |

Run with:
```bash
curl -s -X POST http://localhost:8000/api/report \
  -H "Content-Type: application/json" \
  -d '{"location":"Near Lotus Public School, Sector 12","zone":"silence","db":78,"time_of_day":"night","duration":"sustained"}' | python3 -m json.tool
```

## What to check for the Responsible AI section

- **Fairness**: the tool should never flag a reading as a violation without stating the actual applicable limit for that zone/time — no blanket "loud = bad" judgment.
- **Transparency**: `limit`, `over_by`, and `regulation_passages` should always be present so the exceedance claim is checkable.
- **Ethics**: confirm no response text names or implies a specific individual/household — only location-level and pattern-level framing.
- **Privacy**: confirm the schema never asks for or stores a name, phone number, or precise home address — only a general location string.
