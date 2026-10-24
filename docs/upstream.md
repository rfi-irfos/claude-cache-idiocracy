# Upstream research and attribution

The implementation is an independent RFI-IRFOS integration inspired by:

- `Bande-a-Bonnot/Boucle-framework/tools/read-once`: read deduplication and diff fallback.
- `hacknitive/claude-context-size-guard`: context threshold enforcement.
- `JanBancerewicz/claude-cache-guard`: local usage guard and handover model.
- `rtk-ai/rtk`: shell-output filtering, retained as a separate dependency.

The upstream projects are not copied into runtime state. Their licenses and exact
commits must be recorded before vendoring any source. Anthropic issue reports are
kept as research references only.
