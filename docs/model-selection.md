# Model Selection — Meeting-to-Workflow Builder (Capstone AI)

**Author:** Shoshana Zimmerman
**Module:** M1 — LLM Fundamentals, L3 Model Comparison
**Project:** Reads Fathom meeting transcripts and auto-deploys Make scenarios, MailerLite lists, and WordPress plugins/webhooks
**Status:** Based on Experiments 1–4 comparing `claude-haiku-4-5`, `mistral-small-latest`, and `gemini-3.5-flash-lite`, with escalation to `claude-sonnet-5` / `claude-opus-4-8` where evidence supports it

---

## 1. AI Capabilities in This Capstone

1. **Extraction** — parse Fathom transcript into structured workflow definitions (triggers, actions, conditions, platform references)
2. **Build planning** — dependency ordering, conflict detection, platform sequencing into an executable build plan
3. **Payload generation** — exact API payloads, Make automation JSON, and WordPress plugin/webhook code per build step
4. **Error recovery** — classify API failure type and generate a targeted fix
5. **Verification summary** — plain-language report of what was built/reused/succeeded/needs attention

**Volume:** ~2 requests/day (≈40 builds/month across 3 clients, with headroom).

---

## 2. Task-to-Model Mapping

### Extraction
- **Model:** `claude-sonnet-5`
- **Rationale:** Experiment 2 showed all three cheap-tier models (`claude-haiku-4-5`, `mistral-small-latest`, `gemini-3.5-flash-lite`) solve *simple, explicit* schema extraction reliably (flat 6-key JSON, 5/5 valid across all three). But Fathom transcripts require inferring implicit intent from conversational language ("let's have Sarah follow up" implies a trigger + action + assignee never stated explicitly) — a different failure mode, closer to Experiment 1, where all three cheap-tier models confidently produced wrong output whenever a task required inference rather than direct lookup. Since an extraction error here silently seeds every downstream step with a wrong platform reference or missing trigger, escalating to Sonnet reduces that inference risk.
- **Cost per request:** ~2500 tokens in / 800 out * Sonnet pricing ≈ $0.02–0.03
- **Cheaper model good enough?** No — none of the three cheap-tier models tested (including Haiku) showed reliable inference on ambiguous/implicit content in Experiment 1; the risk isn't JSON validity, which all three handled fine.

### Build Planning
- **Model:** `claude-opus-4-8`
- **Rationale:** Directly supported by Experiment 3. All three cheap-tier providers were most likely to drop state or miscount across sub-steps on the multi-entity room-scheduling task — this is the sharpest cross-provider performance gap observed in the whole suite. Build planning is a harder version of the same problem (a MailerLite segment referenced before it exists is the structural equivalent of double-booking a room). Since this step runs once per build, Opus's cost is proportionally small relative to the cost of a cascading failure it prevents.
- **Cost per request:** ~3000 tokens in / 1500 out * Opus pricing ≈ $0.15–0.25
- **Cheaper model good enough?** No — Experiment 3 is the strongest evidence in this suite for escalating past cheap tier on any provider, and this step's low frequency (once per build) makes the premium cost justified.

### Payload Generation (API payloads, Make automation JSON, WP plugin/webhook code)
- **Model:** `claude-sonnet-5`
- **Rationale:** No experiment directly tested code/config generation — flagged explicitly as the least-evidenced tier choice in this document. The closest analog is Experiment 2, where `gemini-3.5-flash-lite` was actually the fastest and joint-most-reliable cheap-tier model on flat structured JSON, and `mistral-small-latest` matched it on validity — but that test used a flat 6-key schema, not deeply nested, platform-specific structures like a Make scenario graph or WP plugin PHP. The reasoning gap in Experiment 3 is also relevant, since a Make scenario, MailerLite reference, and WP webhook config must stay internally consistent with each other and with build_planning's decisions. Sonnet is chosen as the tier where retrieved API/plugin schema constrains output enough that Opus shouldn't be strictly necessary, while none of the three cheap-tier models were tested at this complexity level, so defaulting to a proven-stronger tier reduces execution risk on code that runs against live client systems.
- **Cost per request:** ~1800 tokens in (incl. retrieved schema/API docs) / 900 out ≈ $0.02–0.025
- **Cheaper model good enough?** Not tested directly. Top candidate for a dedicated follow-up experiment before M6 — specifically testing whether `gemini-3.5-flash-lite` (strongest cheap-tier performer in Experiments 2 and 4) can handle nested API/plugin code generation, since its Experiment 2 and 4 results are the best cheap-tier evidence available and it's worth checking before assuming Sonnet is required.

### Error Recovery
- **Model:** `gemini-3.5-flash-lite`
- **Rationale:** This is fundamentally a classification + small-correction task, the same shape as Experiment 2's structured extraction — the API error message already narrows the problem space substantially. All three cheap-tier providers solved that class of task perfectly in Experiment 2 (5/5 valid, all fields present), but `gemini-3.5-flash-lite` was the fastest of the three, and this step runs multiple times per build, so latency and cost compound. Right-sizing to the fastest validated cheap-tier model directly follows the Experiment 2 production implication.
- **Cost per request:** ~500 tokens in / 200 out * Flash-Lite pricing ≈ $0.0001–0.0002
- **Cheaper model good enough?** Yes — the strongest-evidenced choice in this document; Experiment 2 validated this exact task shape across all three providers, and Gemini's latency edge makes it the best fit for a high-frequency step.

### Verification Summary
- **Model:** `gemini-3.5-flash-lite`
- **Rationale:** Experiment 4 directly supports this: `gemini-3.5-flash-lite` hit the exact word-count target, had the fastest latency of the three, and produced the strongest audience-specific framing — outperforming `claude-haiku-4-5` and `mistral-small-latest` on both quality and speed for short constrained writing. Verification summaries are pure formatting/summarization from an already-structured build log — no reasoning or inference required, exactly matching the task shape where Gemini's cheap tier won outright rather than merely tying.
- **Cost per request:** ~1000 tokens in / 300 out * Flash-Lite pricing ≈ $0.0001–0.0002
- **Cheaper model good enough?** Yes — Experiment 4 showed this model beating, not just matching, the other two on this exact task shape.

---

## 3. Cascade Routing Opportunity

**Default:** `gemini-3.5-flash-lite` for error recovery and verification summary — Experiments 2 and 4 showed this specific model as the strongest cheap-tier performer for both format/classification tasks and short constrained generation, with the best latency of the three.

**Escalation trigger — error recovery:** If the same error type recurs 3+ times within a single build after Flash-Lite fixes are applied (signaling classification-based correction isn't resolving root cause), escalate that specific error to `claude-sonnet-5` for a deeper diagnostic pass. This mirrors Experiment 1's lesson that cheap-tier models across all three providers can fail in the *same* way on tasks outside their competence — repeated failure is a better signal than assumed competence.

**Escalation trigger — extraction → payload generation boundary:** If payload_generation (Sonnet) produces a platform reference that doesn't resolve against what build_planning (Opus) expects, treat this as an extraction-quality signal, not just a payload bug — log it for prompt/schema tightening at the extraction step, since Experiment 1 showed tier/provider upgrades alone don't reliably fix inference-shaped errors at the source.

**Escalation trigger — payload generation:** Given this is the least-evidenced tier assignment in the document, add a mandatory pre-deployment validation step (schema/lint check against the target platform's API, or a WP plugin syntax check) before any generated code reaches build_planning's execution stage. If validation fails, escalate the specific failing payload from Sonnet to Opus for regeneration — zero-tolerance, not frequency-based, because the artifact is executable code hitting live client infrastructure.

**No cascade — build planning:** Always `claude-opus-4-8`, run once per build. Experiment 3 is the strongest single piece of evidence in this suite, and this step's low per-build frequency means the premium cost doesn't scale with build complexity the way a per-payload or per-error cost would.

---

## 4. Summary Rationale

Model choice here is driven by which specific model, among the three actually tested (`claude-haiku-4-5`, `mistral-small-latest`, `gemini-3.5-flash-lite`), performed best for each task shape — not a fixed provider preference. `gemini-3.5-flash-lite` wins the two highest-frequency, cheap-tier-appropriate tasks (error recovery, verification summary) because Experiments 2 and 4 showed it outright beating its cheap-tier peers on both latency and quality for classification and short-form generation. Build planning escalates to `claude-opus-4-8` because Experiment 3 is the clearest evidence in this suite that tier differences matter most when models must track many interacting constraints without dropping state, and this step's low frequency makes the premium cost proportionate. Extraction and payload generation both escalate to `claude-sonnet-5` as a deliberate middle ground: extraction resembles both the format-adherence success case (Exp. 2) and the inference-risk failure case (Exp. 1) observed across all three cheap-tier models, while payload generation extends Experiment 2's format task into a structural complexity and execution-risk level that wasn't directly tested by any provider — flagged as the highest-priority gap in this document and backstopped by a zero-tolerance validation-before-deployment rule rather than relying on tier choice alone.

---

*Note: build planning and error recovery escalation triggers are designed but not yet empirically validated against real build failures. Payload generation's tier assignment is the least evidenced in this document — a dedicated follow-up experiment testing `gemini-3.5-flash-lite` specifically (strongest cheap-tier performer in Exp. 2 and 4) on nested API/plugin code generation should run before M6's eval harness treats this cascade as production-ready.*