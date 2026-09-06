# 实验环境与冻结参数

| 项目 | 值 |
|---|---|
| 模型 | `qwen3.8-27b` |
| 平台 | 阿里云百炼 Model Studio |
| 地域 | 华北 2（北京） |
| API | OpenAI-compatible Chat Completions |
| Thinking | `enable_thinking=false` |
| temperature | `0` |
| max_tokens | `128` |
| 超时 | 90 秒/请求 |
| 自动重试 | 关闭 |
| 执行方式 | 串行；缓存链内 Q1→Q2→Q3 连续执行 |
| 执行顺序 | 18 条链按固定 seed 随机化，链内顺序不变 |
| seed | `20260906` |
| 长度档位 | 服务端实测中位 1,986 / 6,025.5 / 9,987.5 prompt tokens |
| 正式设计 | 3 策略 × 3 长度 × 2 合成文档 × 3 链位置 = 54 |
| Pilot/smoke | 6 次，单独保留，不进入正式估计 |
| 正式 API/transport error | 0 |
| 正式机器评分 | 54/54 通过 |
| 正式逻辑 Token | 325,327 |
| Pilot + 正式请求 | 60 次 |
| Pilot + 正式逻辑 Token | 381,926 |

三种策略：

- A `cold_control`：每个请求在前缀开头使用唯一等长 nonce，破坏可缓存公共前缀。它是冷请求基线，不是“关闭缓存”。
- B `implicit`：不设置 `cache_control`，链内公共前缀保持一致。
- C `explicit`：与 B 使用相同提示文本，仅在稳定文档块末端设置 `cache_control: {"type":"ephemeral"}`。

官方文档核查日期：2026-09-06。华北 2 公开原价为输入 3 元/百万 Token、输出 12 元/百万 Token、隐式缓存命中 0.6 元/百万 Token、显式创建 3.75 元/百万 Token、显式命中 0.3 元/百万 Token。文中费用为按 usage 字段和公开单价计算的估算，不冒充账单实扣。

来源：

- https://help.aliyun.com/zh/model-studio/qwen3-8-27b
- https://help.aliyun.com/zh/model-studio/context-cache

