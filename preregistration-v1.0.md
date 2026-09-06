# Preregistration v1.0: Qwen3.8-27B context-cache benchmark

状态：**FROZEN v1.0 / NO LIVE OUTPUT OBSERVED BEFORE FREEZE**

本版本在任何真实 API 输出被观察前冻结。后续修订必须新增版本和理由，不覆盖本文件或原始 SHA-256。

## 1. 研究问题

在阿里云百炼华北 2（北京）的 OpenAI-compatible API 上，`qwen3.8-27b` 面对重复长公共前缀时：

1. 隐式缓存和显式缓存的真实命中 Token 有多少？
2. 命中能减少多少端到端响应延迟和折算输入成本？
3. 显式缓存的首次创建成本需要复用多少次才能摊平？
4. 缓存策略是否改变确定性任务的最终答案正确性？

## 2. 固定条件

- model: `qwen3.8-27b`
- enable_thinking: `false`
- temperature: `0`
- max_tokens: `128`（仅限制短答案输出，不限制输入长度）
- API: OpenAI-compatible Chat Completions
- 地域：华北 2（北京）
- 串行执行，不并发
- 自动重试：关闭
- 单个 observation：最多一个 HTTP 请求

## 3. 实验因素

### 缓存策略

- A / `cold_control`：不设置 `cache_control`，并在公共前缀最前部放置每次唯一、固定 32 位十六进制 payload 的语义无关 nonce。它是冷请求基线，不宣称关闭了隐式缓存。
- B / `implicit`：不设置 `cache_control`，同一链内保持公共前缀逐字节一致。
- C / `explicit`：提示文本与 B 逐字节一致，仅在稳定文档前缀末端添加 `{"cache_control":{"type":"ephemeral"}}`。显式缓存和隐式缓存不混为同一条件。

### 长度档位

- L1：约 2K prompt tokens
- L2：约 6K prompt tokens
- L3：约 10K prompt tokens

离线字符规模分别控制在约 5K–8K、16K–22K、28K–35K 字符；对应 Token 仍只是目标档位。真实分析以每次响应的 `usage.prompt_tokens` 为准。Smoke 前冻结可接受范围为：L1 1,200–3,200、L2 4,000–8,000、L3 7,000–13,000 prompt tokens。任一档超出范围则停止进入正式阶段，不根据答案表现调整文档。

### 独立文档与链内请求

- 每个长度档位生成 2 份不同 seed 的合成业务台账。
- 每份文档包含 3 个可确定验证的问题。
- 同一缓存链内顺序固定为 Q1 → Q2 → Q3，并在 5 分钟 TTL 内完成。
- 18 条链的顺序使用固定 seed 随机化；链内顺序不随机化。

正式 observation 数：`3 strategies × 3 lengths × 2 documents × 3 positions = 54`。

## 4. 数据与评分

文档完全合成，不含真实个人信息。记录格式固定，问题仅要求返回：

```json
{"answer":"<value>","evidence_id":"<record id>"}
```

评分器严格要求：

- 顶层恰好包含 `answer` 和 `evidence_id`；
- 两个字段均为字符串；
- 值与生成器保存的 gold 完全一致；
- Markdown fence、额外解释、错误 evidence 均判失败。

不使用 LLM judge。

## 5. 保存字段

每个 observation 保存：

- task/document/length/strategy/chain_position
- request SHA-256、stable-prefix SHA-256、nonce（仅实验随机标识，不含凭据）
- response_id、created、system_fingerprint、finish_reason
- prompt_tokens、cached_tokens、cache_creation_input_tokens
- completion_tokens、reasoning_tokens、total_tokens
- latency_ms、HTTP status、error_type、error_message
- final_answer、machine_success、grader_result

禁止保存 `.env`、API Key、Authorization Header、Workspace ID 值和完整请求 Header。

## 6. 主要指标

- 缓存命中率：`cached_tokens > 0` 的 observation 比例
- 缓存覆盖率：`cached_tokens / prompt_tokens`
- 延迟：平均值、中位数、P95；同时做相同文档/长度/位置的配对差异
- 逻辑输入 Token：API 返回的 `prompt_tokens`
- 折算输入成本：按照实验当日官方价格与缓存折扣单独计算，保留公式和价格快照日期
- 正确性：严格机器评分通过率
- 显式缓存回本点：首次创建溢价与后续命中节省额相抵所需复用次数

## 7. 失败、超时与排除

- HTTP 429、5xx、超时、网络或解析错误均作为原始失败记录，不补跑、不重试。
- 单请求超时固定为 90 秒，使三个请求的缓存链在最坏情况下仍不超过 5 分钟 TTL；超时不重发。
- 不因答案或图表不好而排除 observation。
- 只有在发送前检测到重复 observation ID 时拒绝运行，不消耗请求。

## 8. Smoke gate

最多 6 个真实请求，目标仅为确认：

1. 模型和接口可用；
2. Thinking 确实关闭；
3. 显式 `cache_control` 被接口接受；
4. `cached_tokens` 与 `cache_creation_input_tokens` 能安全取得；
5. 5 分钟 TTL 内第二次请求能观察到命中；
6. 原始保存和确定性评分正常。

固定 smoke 矩阵为：L1 隐式缓存连续 2 次、L2 显式缓存连续 2 次、L3 冷请求连续 2 次。它以恰好 6 次请求同时覆盖三个长度档和三种策略。Smoke 失败不自动增加第 7 个请求。人工 Review 后才决定是否冻结并执行 54 次正式实验。

## 9. 已知局限

- 隐式缓存无法关闭，冷请求基线依赖 nonce 破坏公共前缀；nonce 仍可能产生极小提示扰动。
- 两份独立文档适合工程实践文章，不足以支持广泛统计外推。
- 服务负载会影响延迟，随机链顺序只能缓解，不能完全消除。
- API usage 是服务端观测值；账单折扣需要与官方价格规则区分。
- 结论仅适用于测试时间、地域、模型版本和接口形态。
