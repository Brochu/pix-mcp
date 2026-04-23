# pix-mcp

An MCP server (plus companion skill) that lets an LLM agent drive
[Microsoft PIX](https://devblogs.microsoft.com/pix/) to automate graphics
profiling and optimization workflows.

The agent takes captures, inspects them, and surfaces findings — starting
with capture-taking and replay, eventually covering deeper analysis of
graphics captures.

## Architecture

Three layers, each matching a different PIX surface:

1. **`pixtool` wrapper.** Exposes what the existing `pixtool` CLI already
   does: taking GPU/timing captures, replaying, listing counters, trimming
   recapture regions.
2. **GPU capture analysis via the PIX API.** For targeted questions
   about a specific draw/dispatch: events, timing, resources, pipeline
   state, shaders.

A skill file teaches the LLM when to reach for each tool. Rule of thumb:
triage with timing captures (SQL-queryable), escalate to graphics captures
when a specific event needs investigation.

## First target use case: shader-hash-per-pass diffing

Across two versions of the same game, for each PIX-instrumented pass,
record the set of shader hashes used. Flag passes whose name stayed the
same but whose shader hashes changed — a precise regression signal.

Why this first:

- Uses only already-exposed API surface (events, program state, PSO).
- No hardware counters required.
- Possibly works without `StartAnalysis` at all

Shader hashes come straight from the DXBC/DXIL container's `HASH` part
(flags + 128-bit digest written at compile time by DXC/FXC). Parsing the
container is ~50 lines; no crypto needed.
