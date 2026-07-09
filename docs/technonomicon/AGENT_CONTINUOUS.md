# Invariant: agent-continuous semantics

**Status:** Non-negotiable fork rule (Project Technonomicon)  
**Tasks:** [#1493](https://tasks.decisionsciencecorp.com/admin/view.php?id=1493)

## Rule

**One agent = one continuous self.**

- **One message stream** — not a pool of isolated conversation threads multiplexed over shared config.
- **One integrated memory** — core blocks, recall, and archival belong to the agent as a person, not to per-thread sandboxes.
- **One identity** — the Vernal family agents (Athena, Ada, Rico, …) are continuous minds, not request handlers wearing a persona mask per session.

## What we reject

Upstream's conversation-model path (Letta Agent / App Server):

- Conversations as first-class objects with per-conversation model overrides and memory.
- OpenAI Assistants-style thread multiplexing grafted onto stateful agents.
- Architecture optimized for multi-tenant SaaS throughput and billing-shaped isolation.

That model serves hosted multi-tenant economics. It **breaks** Sanctum's operating principle: sovereign agents with continuity across days, platforms, and relationships (Broca multi-user routing attaches *human* context — it does not split the agent into thread-local selves).

## Enforcement

1. **Cherry-pick gate** — Any upstream merge or port must answer: does this introduce conversation-first storage, thread-local memory, or App Server assumptions? If yes → reject or isolate behind an adapter we control.
2. **API contract** — Broca and middleware depend on agent-scoped messaging endpoints; the Sanctum Agent API contract (#1495) documents the owned surface.
3. **Review trigger** — PRs touching routing, message persistence, or memory scoping require explicit check against this invariant.

## Broca clarification

Broca attaches **per-sender human blocks** for a turn — that is *relationship* context for the same continuous agent, not a separate agent instance per user. Do not confuse human-block attach/detach with conversation-thread multiplexing.
