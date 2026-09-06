# Official API documentation check

Checked: 2026-09-06, before any live request.

Primary sources:

- Qwen3.8-27B model page: https://help.aliyun.com/zh/model-studio/qwen3-8-27b
- Model Studio context-cache documentation: https://help.aliyun.com/zh/model-studio/context-cache
- Explicit-cache best practices: https://help.aliyun.com/zh/model-studio/explicit-cache-guide

Frozen interface assumptions for the smoke gate:

- `qwen3.8-27b` supports context caching in China (Beijing).
- Implicit caching is automatic and cannot be disabled; a minimum shared prefix does not guarantee a hit.
- Explicit caching uses a `cache_control: {"type":"ephemeral"}` marker in message content.
- Explicit and implicit cache modes must not be conflated.
- Explicit-cache TTL is five minutes and a hit refreshes the TTL.
- Cache creation and hit usage can be observed through `cache_creation_input_tokens` and `cached_tokens` in usage details.
- Documented normalized input-price multipliers are: explicit creation 125%, explicit hit 10%, implicit hit 20% for this Alibaba Cloud-deployed model category. The experiment will retain the raw usage fields and label cost calculations as normalized estimates rather than invoice data.

The live smoke must verify actual interface acceptance and returned field shape. If the interface contradicts these assumptions, formal execution is blocked; the runner does not silently reinterpret missing fields as evidence of a hit.

