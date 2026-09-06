from __future__ import annotations

MODEL = "qwen3.8-27b"
TEMPERATURE = 0
MAX_TOKENS = 128
ENABLE_THINKING = False

LENGTH_LEVELS = {
    # Deterministic record counts chosen from offline character-size calibration.
    # The API-reported prompt_tokens value remains authoritative.
    "L1": 24,
    "L2": 79,
    "L3": 133,
}

TARGET_PROMPT_TOKEN_BANDS = {
    "L1": (1_200, 3_200),
    "L2": (4_000, 8_000),
    "L3": (7_000, 13_000),
}

NONCE_HEX_LENGTH = 32
STABLE_NONCE_HEX = "0" * NONCE_HEX_LENGTH

STRATEGIES = ("cold_control", "implicit", "explicit")
DOCUMENT_REPETITIONS = (1, 2)
CHAIN_POSITIONS = (1, 2, 3)

SYSTEM_CONTRACT = (
    "你是业务台账检索器。只依据给定台账回答问题。"
    "输出必须是单行 JSON，且顶层恰好包含 answer 与 evidence_id 两个字符串字段。"
    "不得输出 Markdown 或解释。"
)
