# Letta base version pin (Technonomicon fork)

**Verified:** 2026-07-09 (Otto — GitHub + moya prod read-only)

## Summary

| Item | Value |
|------|-------|
| **Upstream last release** | `letta-ai/letta` tag **`0.16.4`** → commit `65dbd7fd89b965c0fd52295dc1dd9bdd01a93fa9` |
| **Fork `main`** | Same commit as upstream `0.16.4` (exact match) |
| **Fork `venice-openai-proxy`** | `0.16.4` + Venice OpenAI-compatible provider patch (7 commits on top of `main`) |
| **Prod branch (moya)** | `venice-openai-proxy` @ `54e8ccdda` |
| **Prod install path (moya)** | `/home/rizzn/letta` |
| **Package version** | `pyproject.toml` → `0.16.4` |
| **Upstream server status** | Legacy — maintainer confirmed deprecated / unsupported (issue #3399) |

## Branches

### `main`

- Points at upstream **`0.16.4`** release commit (`65dbd7fd`).
- No Sanctum-specific code beyond owning the fork namespace.
- Use for cherry-picks from upstream maintenance and documentation that applies to all branches.

### `venice-openai-proxy`

Commits ahead of `main` (Venice integration only):

```
54e8ccdd Use async BYOK lookup in request_embeddings.
d9edb755 Pass actor into OpenAIEmbedder for BYOK embedding auth.
1e9f9d0a Align embedding auth with chat: BYOK first, then Venice env.
cf4a0755 Fix Venice embedding auth: prefer VENICE_API_KEY for venice.ai endpoints.
657ee523 test: add multimodal unit tests and live Venice integration tests
bd7c4fbf fix: Venice streaming think-tag extraction and tool compatibility
03e78db6 test: add 28 Venice unit tests covering all proxy integration code
2b95cc53 feat: Venice AI support via OpenAI-compatible proxy
```

Prod runs this branch. Future Letta patches (e.g. MCP resync fix #6) land here first, then may merge to `main` when appropriate.

## Production (moya / rizzn-223)

```
$ cd /home/rizzn/letta && git branch -v
* venice-openai-proxy  54e8ccdda  Use async BYOK lookup in request_embeddings.
```

Letta HTTP API: `127.0.0.1:8284` (Broca and bridges depend on this surface — see task #1495).

## Policy

- **Brotli (HTTP2Shell / CVE-2026-111497):** `pyproject.toml` requires **`brotli>=1.2.1`**. Do not revert to `>=1.1.0` — 1.0.3–1.2.0 are RCE. Existing installs: `uv lock --upgrade-package brotli` then restart Letta so the old `.so` is not left mapped.
- **Do not** track `letta-ai/letta` `main` post-deprecation for server architecture.
- **Do** cherry-pick provider/model fixes at the `llm_api` seam when safe.
- **Issue filing:** `technonomicon-lore/letta` (see Tasks doc #680).

**Tasks:** [#1492](https://tasks.decisionsciencecorp.com/admin/view.php?id=1492) · research card [#1538](https://tasks.decisionsciencecorp.com/admin/view.php?id=1538)
