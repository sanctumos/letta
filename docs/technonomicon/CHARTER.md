# Project Technonomicon — Charter

**Canonical Tasks copy:** [Doc #672](https://tasks.decisionsciencecorp.com/admin/doc.php?id=672) (Project Technonomicon)

**Purpose.** Hard-fork Letta, permanently, into Sanctum OS proper. The fork lives in `technonomicon-lore/letta` until it reaches its own stable, ideal "Sanctum" version; until then we build off the 0.16.4 base we already run in production.

**Status of the base (as of 2026-07-07).** The upstream `letta-ai/letta` API server we self-host is **officially legacy and unsupported** — stated directly by Letta's Cameron Pfiffer on our issue #3399: *"fully deprecated… no longer supported."* Active upstream development has moved to the "Letta Agent" repo and an "App Server" self-hosting path, which *is* the cloud-oriented conversation-model architecture we reject. **There is no supported forward path on the base that preserves what Sanctum is.** Forking is therefore not a preference; it is the only continuity path.

**Scope.**

- We **own the API surface** our middleware (Broca, and all Sanctum services) depends on. Upstream's deprecation of it has no authority over us because we no longer track upstream for that surface.
- We **stay agent-continuous**: one agent = one continuous stream, one integrated memory, one self. We do not adopt conversations-as-first-class objects. See `AGENT_CONTINUOUS.md`.
- We **move memory from Postgres to plain markdown on disk** — **no git** for the memory substrate (decision lock 2026-07-08). Durability: append-only raw archives, atomic shadow-and-swap writes, periodic snapshots. Recall: metadata-first (tags/aliases + grep), not vector-primary. Vectors deferred optional.
- We **keep the `llm_api` provider seam upstream-shaped** so improvements remain cherry-pickable.

**Non-goals.** Multi-tenant throughput, shared-context/prompt-caching economics, billing-shaped thread multiplexing — these are upstream's revenue model, not our operating principle.

**Point of no return.** Upstream's deprecation of the direct agent-messaging API (#9120), now confirmed by the maintainer as the whole server's status, is the trigger. From here Letta is a **parts supplier (quarry)**, not a base to merge.

**Definition of "done" for the fork.** A self-owned Sanctum runtime whose agent API contract is stable and documented by us, whose memory substrate is plain markdown with metadata-first recall, that runs the Vernal family agent-continuous, and that can still absorb upstream provider/model work by cherry-pick — at which point it stops being "the Letta fork" and is simply **Sanctum**.
