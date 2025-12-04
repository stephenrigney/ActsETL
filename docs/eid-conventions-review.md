# ActsETL eId Conventions Review (Akoma Ntoso)

Date: 2025-12-04

Scope: Review eId usage for definition sections against [Akoma Ntoso Naming Convention (Section 5)](https://docs.oasis-open.org/legaldocml/akn-nc/v1.0/akn-nc-v1.0.html) and project patterns.

Summary
- eId must be unique, stable, and contain no whitespace; UTF-8 letters/digits/underscore permitted.
- Prefer hierarchical concatenation of meaningful context prefixes with clear separators.
- Use full element name or hcontainer/@name for `name`, other than where structural markers (eg, `subsec`, `para`, `chp`) are mandated by Akoma Ntoso Naming Convention.
- An eId snippet for an element is composed by a combination of a `name` reflecting the element tag/@name and a `number` reflecting the <num> value (if present) or the ordinal of the element in series of like named siblings (if <num> is not present).
- The pattern for an eId snippet is `name`_`number`.
- Part, schedule and section level eIds consist solely of the eId for the element if they they are not inserted elements (an inserted element being an element enclosed in a <mod> structure).
- Other elements are prefixed by their eId of their parent container or context.
- Inserted elements are prefixed by the eId of their mod element parent.
- Double underscores between context prefixes to demarcate boundaries clearly.
- Structural markers first, normalized term slugs second.


Patterns
- Part: `part_1`
- Chapter: `part_1__chp_1`
- Section: `sec_1`
- Schedule: `schedule_1`
- Subsection: `sec_1__subsec_1`
- Paragraph (lettered): `sec_1__subsec_1__para_a`
- Definitions list container: `sec_1__subsec_1__definitions`
- Definition item: `sec_1__subsec_1__def__act_of_1967`
- Nested list under a definition: `sec_1__subsec_1__definition__specified_animal__list`

Slug Rules
- Lower-case; spaces → `_`; strip punctuation; ASCII-only if possible.
- Use underscore `_` only within slugs; avoid hyphens.
- Deterministic slugs derived from the defined term for readability, not raw text.

Rationale
- Double underscores reflect context boundaries in line with AN Section 5 guidance.
- Structural semantics (`subsect`, `para`, `definition`) ensure clarity and stability.
- Readable slugs assist cross-reference without coupling to natural-language text.

Recommendations
- Adopt the double-underscore scheme project-wide for hierarchical eIds.
- Ensure every addressable unit (definition items, nested points) has an `eId`.
- Keep real numbering in `<num>` only where published (e.g., `(a)…(h)`); never use empty `<num>` as anchors.
