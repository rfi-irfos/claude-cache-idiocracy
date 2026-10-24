# Upstream research and attribution

The implementation is an independent RFI-IRFOS integration inspired by:

- `Bande-a-Bonnot/Boucle-framework/tools/read-once`: read deduplication and diff fallback.
- `hacknitive/claude-context-size-guard`: context threshold enforcement.
- `JanBancerewicz/claude-cache-guard`: local usage guard and handover model.
- `rtk-ai/rtk`: shell-output filtering, retained as a separate dependency.
- `cnighswonger/claude-code-cache-fix`: per-session hard budget/circuit-breaker pattern.
- Claude Code prompt-caching documentation: cache TTL, model/tool-definition
  invalidation, and cache-hit observability.

The upstream projects are not copied into runtime state. Their licenses and exact
commits must be recorded before vendoring any source. Anthropic issue reports are
kept as research references only.

The design consequence is deliberate: the local wrapper owns the hard stop and
offline transcript replacement, while Claude Code's native settings own cache
TTL and concurrency. A Read hook cannot rewrite a tool response, so RTK-style
output compaction must remain a command wrapper/dependency rather than being
pretended to be a PostToolUse transform.
