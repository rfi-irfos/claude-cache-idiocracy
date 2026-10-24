from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Policy:
    max_tools: int = 10
    max_subagents: int = 3
    max_spawn_depth: int = 1
    soft_cache_read: int = 100_000_000
    hard_cache_read: int = 250_000_000
    soft_errors: int = 20
    hard_errors: int = 50
    error_window_seconds: int = 900
    max_result_chars: int = 40_000

    def environment(self) -> dict[str, str]:
        return {
            "CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY": str(self.max_tools),
            "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": str(self.max_subagents),
            "CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS": str(self.max_subagents),
            "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": str(self.max_spawn_depth),
        }

    @classmethod
    def from_env(cls) -> "Policy":
        def integer(name, default):
            try:
                return max(1, int(os.environ.get(name, default)))
            except ValueError:
                return default
        return cls(
            max_tools=integer("HACHE_MAX_TOOLS", 10),
            max_subagents=integer("HACHE_MAX_SUBAGENTS", 3),
        )
