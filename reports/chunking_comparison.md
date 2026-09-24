# Chunking Strategy Comparison

**Document:** [`data/documents/ad-infinitum-roadmap.md`](../data/documents/ad-infinitum-roadmap.md) (8,450 chars, 12 headings across a phased rollout + numbered issue list)
**Chosen because:** it's the most structurally rich document in the corpus — nested `##`/`###` sections, numbered lists, and a specific numeric requirement (a 150-unit order minimum with a stated exception) that a bad split can silently corrupt.
**Parameters:** `chunk_size=500`, `overlap=100` for both strategies, via [`Chunker`](../src/capstone_ai/rag/chunker.py).

## Summary (fixed vs. recursive, pre-fix numbers — see Step 7 for the recursive fix and Step 10 for semantic)

| Metric | Fixed | Recursive |
|---|---|---|
| Total chunks | 21 | 27 |
| Avg chunk size (chars) | 498 | 312 |
| Min chunk size (chars) | 450 | 17 |
| Max chunk size (chars) | 500 | 498 |

`chunk_size` behaves as a ceiling for both, but only `chunk_fixed` treats it as a *target* — it packs every chunk to (near) 500 chars regardless of content. `chunk_recursive` stops at the nearest separator under the ceiling, so its average lands at 62% of the requested size. More, smaller chunks isn't free: it means more embedding calls and more retrieval noise for the same document.

## Bad Chunk Boundaries

### Fixed: mid-word split through the exact requirement that matters

Fixed-size chunking has no awareness of word or sentence boundaries — it cuts at raw character offset 500, landing inside a word:

**Chunk 4 (end):**
> `...tiered/quantity pricing with a 150-unit minim`

**Chunk 5 (start):**
> `ase imprint is 1 color...) → tiered/quantity pricing with a 150-unit minimum (special case: ordering 2 different designs allows 75 units each)...`

The word `minimum` is torn across the boundary (`minim` | `um`). This is cosmetic on its own — the 100-char overlap happens to duplicate the full sentence into chunk 5, so the 150-unit-minimum-with-75-unit-exception detail survives intact *in this instance*. But that's luck, not design: it depends entirely on where the sentence happened to fall relative to the fixed 500-char boundary. A slightly longer preceding sentence would have split the requirement itself across two chunks with no shared context, silently dropping either the minimum or its exception from whichever chunk gets retrieved.

### Recursive: heading isolated from its own content

Recursive chunking respects word/sentence boundaries but has no concept of "this heading belongs with the paragraph beneath it." Because a heading is followed by `\n\n`, the splitter's top-priority separator, short headings frequently end up alone:

**Chunk 5 (entire chunk, 17 chars):**
> `## Phased Rollout`

**Chunk 10 (entire chunk, 31 chars):**
> `## Key Functional Issues to Fix`

**Chunk 22 (entire chunk, 29 chars):**
> `## Commercial Terms Discussed`

Each of these is retrieved (or not) as a standalone unit carrying zero information — a chunk that says only "Key Functional Issues to Fix" with none of the five issues listed underneath it. In a retrieval system, this chunk can rank as a false-positive match (the query term appears in it) while contributing nothing useful to the generation prompt, and worse, it wastes a slot in top-k that a substantive chunk could have filled.

## Takeaway (pre-fix)

Neither strategy was safe by default for this corpus:

- **Fixed** risks splitting a specific numeric requirement across chunks with no guarantee the overlap window happens to reunite it — the 150-unit/75-unit case worked out here by coincidence.
- **Recursive** risks stripping content of its heading context by isolating short headings into their own near-empty chunks.

## Step 7: Fixing the recursive heading-isolation failure

I picked the recursive failure to fix rather than the fixed-strategy one, because it's a systematic pattern, not a coincidence — every short markdown heading in the corpus is at risk, not just the one instance that happened to land on a 500-char boundary.

**Original text around the boundary** (from `ad-infinitum-roadmap.md`):

```
...four sentences of Phase-3 discussion, end of prior section.

## Key Functional Issues to Fix

1. **Checkout totals don't calculate correctly.** Example from the call: a $0.33/unit add-on...
```

**Which strategy produced the bad split:** `chunk_recursive`. `RecursiveCharacterTextSplitter` tries `"\n\n"` first, and a short heading followed by a blank line is frequently short enough to become its own complete chunk before the splitter ever reaches the numbered list beneath it — producing:

- Chunk 10: `"## Key Functional Issues to Fix"` (31 chars, zero content)
- Chunk 11: the five numbered issues, with no heading indicating what they're a list *of*

This isn't cosmetic: a query about "checkout totals" would retrieve chunk 11's content fine, but a broader query matching only the heading text retrieves 31 characters of pure noise, wasting a top-k slot.

**How I fixed it:** added `Chunker._merge_bare_headings`, a post-processing pass in `chunk_recursive` that detects a chunk whose entire stripped content is a markdown heading (`#{1,6}\s+\S.*`, matched with `re.fullmatch`) and folds it into the *next* chunk, joined by the same `\n\n` the splitter had stripped. I chose a post-merge over a parameter/separator change because I tested that first — reordering or dropping `\n\n` from `separators` (tried `['\n\n\n', '\n\n', '. ', ' ', '']`) did **not** stop the isolation; the heading is short enough to stand alone as a valid chunk under almost any separator ordering, so the fix has to happen after splitting, not during it.

**Result on the same document:** bare-heading chunks dropped from 3 to 0, total chunk count 27 → 22 (merges reduce count, they don't just relabel). Verified with a corpus-wide sweep: 4 of 5 documents now have zero heading-isolation chunks. The fifth (`Daven for me and volumes of joy roadmap-meeting-notes.md`) still has two 2-line chunks — `"---\n\n## Volumes of Joy"` and `"---\n\n## Open questions"` — because that document uses a `---` horizontal-rule divider immediately before each heading, so the chunk isn't a *bare* heading match and the merge correctly leaves it alone. That's a known gap: the fix targets the pattern I found, not every short-chunk shape, and a `---`-prefixed heading is a second pattern this pass doesn't yet cover.

Offsets were re-verified after the merge (`text[start:end] == chunk.text` for every chunk, including merged ones) since the merge logic recomputes `end_char` and a bug there would silently corrupt every downstream page/citation mapping.

## Takeaway (through Step 7)

A markdown-aware post-process (merge bare headings forward) closes recursive's main failure mode without reintroducing fixed's mid-word risk, at the cost of not yet handling every heading-adjacent divider pattern in the corpus. That's the next case worth testing before treating recursive as production-safe.

---

## Step 10: Three-way comparison (fixed vs. recursive vs. semantic)

Same document, `data/documents/ad-infinitum-roadmap.md`, run through all three strategies via [`Chunker`](../src/capstone_ai/rag/chunker.py). Recursive numbers below are **post-fix** (§Step 7's bare-heading merge applied). Semantic uses `threshold=0.55`, the corpus-measured default (see `Chunker.similarity_distribution`, documented in the chunker's `DEFAULT_SEMANTIC_THRESHOLD` comment) rather than a borrowed tutorial value.

### Summary

| Metric | Fixed | Recursive | Semantic |
|---|---|---|---|
| Total chunks | 21 | 22 | 13 |
| Avg chunk size (chars) | 498 | 384 | 649 |
| Min chunk size (chars) | 450 | 138 | **2** |
| Max chunk size (chars) | 500 | 534 | 2,708 |

Semantic is the outlier on every axis, and for a specific reason: it doesn't control size at all. Fixed and recursive both take a `chunk_size` ceiling as an input; semantic takes a *similarity threshold* and lets chunk size fall out of however many consecutive sentences stay above it. The result is the widest size spread of the three strategies — one chunk of 2,708 chars (a long uninterrupted stretch of related sentences about the business background) sitting next to a 2-char chunk.

### Bad boundary: semantic mis-splits a numbered list as if it were sentence punctuation

**Original text** (source, uninterrupted):

```
...(dated 5-color art — needs re-pricing before production).
3. Staff send the customer a PDF proof of the imprint; customer must sign off before...
```

**Which strategy produced the bad split:** `chunk_semantic`, but the root cause sits one layer earlier, in `Chunker._split_sentences`. The sentence-boundary regex (`(?<=[.!?])\s+(?=[A-Z0-9"'])`) treats any `.` followed by whitespace and a capital letter or digit as a sentence end. A numbered list item like `"3. Staff send..."` matches that pattern exactly — the `.` after `production)` ends a real sentence, and the very next token, `"3."`, gets read as *starting* a new sentence, which promptly ends after two characters because it's immediately followed by another capital-starting word. This is the exact abbreviation/decimal failure mode flagged in the code comment above `_SENTENCE_BOUNDARY` — numbered lists are a case that comment didn't call out but belongs to the same family.

**Resulting chunks:**

- Chunk 7: `"3."` (2 chars, zero information)
- Chunk 9: `"4."` (2 chars, zero information)
- Chunk 11: `"5."` (2 chars, zero information)

Each of these three list markers was embedded and chunked as if it were a complete, meaningful sentence, standing alone with no relationship recorded to the list item it introduces. This is a worse failure than recursive's heading-isolation bug: a heading chunk at least contains a real word a query might match; `"3."` is retrieval noise with no possible signal value, and it consumed an embedding call to produce.

**Not fixed here** — flagged as the next thing to fix, the same way heading-isolation was flagged and then fixed in Step 7. The likely fix is the same *shape* of solution: a post-processing merge pass, this time folding a sentence whose entire content is a bare list-item number (`^\d+\.$`) into the sentence that follows it, mirroring `_merge_bare_headings`. A regex-only fix at the splitting stage (e.g., requiring more than one digit-or-letter after the terminal punctuation before splitting) was not attempted here and is a reasonable alternative worth comparing.

### Takeaway (all three strategies)

No strategy is safe unmodified against this corpus:

- **Fixed** — mid-word splits, only "saved" by overlap coincidentally reuniting content (§ above).
- **Recursive** — heading isolation, now fixed via post-merge (Step 7), with one known unfixed variant (`---`-prefixed headings).
- **Semantic** — numbered-list items misread as standalone sentences, not yet fixed, and arguably the most damaging of the three because the resulting chunk (`"3."`) carries no retrievable signal at all, unlike a mis-split word or an isolated-but-legible heading.

Each strategy's failure mode traces back to a different layer treating structure it didn't understand as if it were the structure it expects: fixed ignores structure entirely, recursive's separator hierarchy doesn't know a heading is bound to its body, and semantic's sentence splitter doesn't know a numbered list marker isn't a sentence. Structural fixes compound — every fix applied so far has been a targeted post-process for the specific pattern found, not a general parser, which means new document shapes in the corpus should be expected to surface new unhandled patterns rather than assuming these fixes generalize.
