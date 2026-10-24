from __future__ import annotations
from .policy import Policy

def evaluate(metrics: dict, policy: Policy | None = None) -> dict:
    policy = policy or Policy()
    cache = int(metrics.get("cache_read_input_tokens", 0) or 0)
    errors = sum(int(v) for v in (metrics.get("errors") or {}).values())
    compactions = int(metrics.get("compactions", 0) or 0)
    if cache >= policy.hard_cache_read or errors >= policy.hard_errors or compactions >= 3:
        return {"state": "break", "reasons": ["context_budget_or_retry_threshold"]}
    if cache >= policy.soft_cache_read or errors >= policy.soft_errors or compactions >= 2:
        return {"state": "warn", "reasons": ["context_budget_or_retry_warning"]}
    return {"state": "ok", "reasons": []}
