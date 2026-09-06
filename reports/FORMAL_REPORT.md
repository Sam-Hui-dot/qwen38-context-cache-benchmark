# Qwen3.8-27B Context Cache Formal Report

- Observations: 54
- API/transport errors: 0
- Machine-scored successes: 54
- Total logical tokens: 325,327

## Strategy summary

| Strategy | N | Errors | Correct | Cache-hit obs | Prompt total | Cached total | Median latency ms | P95 latency ms | Equivalent input cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cold_control | 18 | 0 | 18 | 0 | 107,956 | 0 | 1,885.1 | 3,121.7 | 107,956.0 |
| implicit | 18 | 0 | 18 | 14 | 108,024 | 67,840 | 923.3 | 2,700.0 | 53,752.0 |
| explicit | 18 | 0 | 18 | 12 | 108,024 | 71,656 | 813.7 | 3,111.5 | 52,490.6 |

Equivalent input cost uses normalized multipliers: uncached=1.00, explicit creation=1.25, explicit hit=0.10, implicit hit=0.20. Output-token cost is excluded.

## Matched comparison against cold control

- implicit: matched pairs=18, median latency delta=-772.0 ms, median equivalent input-cost saving=59.4%.
- explicit: matched pairs=18, median latency delta=-1,060.4 ms, median equivalent input-cost saving=88.6%.

## Failures

No API, transport, parse, or machine-scoring failures.
