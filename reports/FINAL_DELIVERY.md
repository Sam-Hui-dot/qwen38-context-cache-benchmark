# Final delivery review

Completed: 2026-09-06

## Request accounting

- Pilot/smoke HTTP requests: 6
- Formal HTTP requests: 54
- Total HTTP requests: 60
- Automatic retries: 0
- Formal API/transport errors: 0
- Formal deterministic scoring passes: 54/54
- Pilot logical tokens: 56,599
- Formal logical tokens: 325,327
- Total logical tokens: 381,926

## Reproducibility

- V1.0 and V1.1 preregistration/freeze records retained.
- The failed v1 smoke length gate is retained; it was not rewritten as passing.
- V2.0 calibration amendment was frozen before any formal request.
- Formal random seed: 20260906.
- Formal execution order: 18 randomized chains, three contiguous requests per chain.
- Formal raw JSONL SHA-256: `1992f3e0d92a1d7d401f70d66a1fd4a916300fee5276231103a3375cf2c45e94`.
- V2.0 freeze-manifest SHA-256: `c080577e8be314fca589c9e68b6b3e5e9e4cb7575713346dec3c5f7b7053e41c`.
- Offline test suite: 41 passed.

## Main result and limitation

All six explicit-cache chains were internally clean with respect to API accounting. Their three-request normalized input cost was a median 51.4% lower than matched cold chains. Chain-total latency was a median 41.0% lower, though this latency figure is descriptive because explicit creation on doc1 may have benefited from prior implicit prewarming.

Two of six implicit-cache chains started with nonzero cached tokens after matching explicit chains had already executed. This is disclosed as possible condition-order carryover. No record was deleted or rerun. The four-chain clean implicit subset is labeled post-hoc sensitivity analysis, not the preregistered primary estimate.

## Cost estimate

Using the official prices checked on 2026-09-06 (ordinary input ¥3/M, output ¥12/M, implicit hit ¥0.6/M, explicit creation ¥3.75/M, explicit hit ¥0.3/M):

- Pilot estimated cost: ¥0.148837
- Formal estimated cost: ¥0.658472
- Total estimated cost: ¥0.807309

These are usage-based estimates, not invoice data; free quota and account promotions may change actual billing.

## Artifacts

- Four Chinese figures and plotting script.
- Full raw JSONL and CSV summary in the private project.
- Protocol audit and post-hoc sensitivity report.
- ModelScope article draft that explicitly discloses the carryover issue.
- Sanitized public release repository with results, source, tests, plans and manifests.
- Public-release security scan: zero blocking findings.

