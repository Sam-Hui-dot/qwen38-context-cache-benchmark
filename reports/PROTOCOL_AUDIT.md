# Formal protocol audit and post-hoc sensitivity analysis

- Raw JSONL SHA-256: `1992f3e0d92a1d7d401f70d66a1fd4a916300fee5276231103a3375cf2c45e94`
- Formal observations: 54
- API/transport errors: 0
- Deterministic scoring passes: 54/54
- Formal logical tokens: 325,327

## Confirmed protocol issue

Two implicit-cache chains began with non-zero `cached_tokens`. Both matching explicit-cache chains had already run within the same short formal run. Because B and C intentionally used byte-identical prompt text, the later implicit requests may have inherited cache state created by the earlier explicit condition. The design did not isolate cache namespaces or insert a TTL washout. This is condition-order contamination, not an API error.

| Implicit chain | First execution | First-request cached tokens | Prior explicit executions |
|---|---:|---:|---:|
| L2-d2 | 49 | 4,992 | 34–36 |
| L3-d2 | 52 | 8,320 | 4–6 |

No raw record is deleted or rescored. The preregistered all-row summary remains in `FORMAL_REPORT.md`. The following is explicitly post-hoc sensitivity analysis:

- Explicit cache: all six explicit chains were internally clean with respect to API-reported cache accounting (first request created cache, positions 2/3 hit). However, two explicit chains (L2-d1 and L3-d1) were preceded by byte-identical implicit chains, so their latency observations may have been affected by cross-condition prewarming. Median three-request-chain normalized input-cost saving versus cold control: 51.4% (supported by all six matched chains); median latency saving: 41.0% (should be interpreted descriptively rather than as an isolated causal estimate).
- Implicit cache clean subset: 4 of 6 chains (12 observations) began cold. Median normalized input-cost saving versus matched cold chains: 30.0%; median latency saving: 31.7%.
- The two contaminated implicit chains remain visible in the raw data but are not used for the clean-subset headline. This subset was not preregistered and must not be presented as the original primary estimate.

## Interpretation boundary

The 51.4% cost saving is supported by all six matched chains. The 41.0% latency saving is descriptive because cross-condition prewarming may have accelerated explicit creation on doc1. The implicit estimate is weaker because only four uncontaminated chains remain. The data do not establish that explicit and implicit cache stores are shared; they only show an order-aligned carryover pattern that requires a separately preregistered follow-up to identify causally.
