# Preregistration v2.0 amendment — pre-formal length calibration

Date: 2026-09-06

Status: **FROZEN BEFORE ANY FORMAL OBSERVATION**

## Reason

The six-request v1.0 smoke was retained unchanged. It passed 9 of 10 frozen checks: all six HTTP requests succeeded, all six deterministic answers passed, Thinking remained off, implicit cache hit on reuse, explicit cache creation and reuse were observed, and the cold control had zero cached tokens. The only failed check was the predeclared prompt-length bands.

Observed v1.0 smoke medians were:

- L1, 40 records: 3,163 prompt tokens
- L2, 125 records: 9,409 prompt tokens
- L3, 210 records: 15,654 prompt tokens

These smoke records are pilot/calibration data and are excluded from all formal estimates. The original failed gate, raw JSONL and hashes are preserved.

## Frozen calibration change

A linear fit to the three service-reported points gives approximately:

`prompt_tokens = 224.1 + 73.48 × record_count`

Before any formal request, record counts are therefore changed only for input-length calibration:

- L1: 24 records, target approximately 2,000 prompt tokens
- L2: 79 records, target approximately 6,000 prompt tokens
- L3: 133 records, target approximately 10,000 prompt tokens

The original token acceptance bands remain L1 1,200–3,200, L2 4,000–8,000 and L3 7,000–13,000. Formal records outside a band are retained and reported; they are not rerun.

## Unchanged elements

Research question, model, region, API, temperature, `max_tokens`, Thinking-off setting, cache strategies, nonce construction, output contract, deterministic scoring, two document repetitions, three chain positions, seed `20260906`, randomized 18-chain order, 54-observation cap, 90-second timeout, no-retry rule, raw-data retention and analysis metrics are unchanged.

The formal fixtures are regenerated deterministically from the frozen v2 record counts. No answer, score, cache result or latency from a formal request existed when this amendment was frozen.

