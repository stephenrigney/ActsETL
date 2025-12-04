# Definitions Section Modeling (Akoma Ntoso 3.0)

Purpose
- Model statutory definition sections with addressable term anchors and consistent hierarchy.
- Audience: XML-savvy architects new to Akoma Ntoso; ActsETL maintainers planning refactors.
- Goals: XSD validity, stable eIds, clear placement rules, predictable references.

Document Envelope
- Container: `akomaNtoso/act` as the root legal document.
- Meta: `meta.identification` with `source="#source"`; FRBR blocks describe work/expression/manifestation.
- Body: `body` holds structural content (sections, subsections, containers).

Section Pattern
- Section: `section eId="sect_{num}"` with heading and number.
- Subdivision:
  - Intro: `subsection > intro > p` for the opening sentence (e.g., “In this Part—”).
  - Definitions group: `subsection > hcontainer name="definitions"` as the container for all terms.
  - Term entries: Repeated `hcontainer name="definitionTerm"` for each term:
    - Content: `content > p` containing the headword in `<def refersTo="#term-{slug}">Term</def>` followed by the definition text.
    - Optional list: `blockList` under `content` for lettered sub-elements where the definition enumerates categories.

Identifiers (eId)
- Strategy: Hierarchical, double-underscore separators between contexts.
  - Section: `sect_{number}`
  - Subsection: `sect_{number}__subsect_{index}`
  - Definitions group: `sect_{number}__subsect_{index}__definitions`
  - Term: `sect_{number}__subsect_{index}__def__{slug}`
  - Nested list: suffix `__list` and lettered items `__para_{a|b|...}`.
- Slugs: Lowercase, underscore-separated tokens derived from the term headword; stable across conversions.

References
- Term anchors: `<def refersTo="#term-{slug}">…</def>` enable consistent cross-referencing.
- Internal refs: `<ref href="#{target_eId}">…</ref>` to other subdivisions (sections, subsections, paragraphs).
- External refs: `<ref href="URL" refersTo="#act">…</ref>` for cited legislation.

Validation
- Schema: `akomantoso30.xsd` governs allowed elements and placement.
- Placement rules:
  - Use `intro` for the first paragraph of a subdivision.
  - Keep `hcontainer` as a direct child of the subdivision; do not place `hcontainer` inside `content`.
  - Use `content` within term `hcontainer` to carry `p` and optional `blockList`.

ActsETL Refactoring Prompt
- Data modeling:
  - Provision model for definitions: `Definition(term_text, slug, body_text, list_items: Optional[List[LetteredItem]])`.
  - Detect lettered lists `(a)…(h)` bound to a specific definition.
- Builders:
  - `build_definitions_hcontainer(subsection_eid, definitions) -> etree._Element`.
  - `build_definition_term(defn) -> etree._Element` emitting `hcontainer[name="definitionTerm"]` with `content`.
  - `build_lettered_blocklist(items) -> etree._Element` when present.
- eId generation:
  - `sect_eid = f"sect_{section_num}"`, `subsect_eid = f"{sect_eid}__subsect_{index}"`.
  - `def_eid = f"{subsect_eid}__def__{slug}"`, with child eIds for lists.
- Referencing:
  - Populate `def@refersTo` for anchors; resolve intra-document `ref@href` via `section_hierarchy` mapping.
- Tests:
  - Fixtures covering plain definitions and definitions with nested lists.
  - Assertions for element placement, eIds, `def@refersTo`, and XSD validity.

Motivation: Lists vs Hcontainers
- Block lists:
  - Use when the definition contains enumerated sub-clauses that are lettered and semantically ordered.
  - Pros: Native list semantics; clear markers with `<num>`; straightforward rendering and citation at item-level.
  - Cons: Item anchors live under the term but items themselves are not standalone semantic containers; headword scoping is implicit.
- Hcontainers:
  - Use to model each definition term as its own addressable container (`definitionTerm`) scoped under a definitions group.
  - Pros: Strong, stable anchors for each term; clean separation of term headword and body; easier future enrichment (notes, properties) per term; fits hierarchical traversal and TOC building.
  - Cons: Adds one more structural layer; requires care not to place `hcontainer` inside `content` for subdivision-level grouping.
- Pattern chosen:
  - Group-level `hcontainer name="definitions"` for the section’s definitions set.
  - Term-level `hcontainer name="definitionTerm"` for each headword’s content.
  - Inside the term, use `blockList` only when the body enumerates lettered elements; avoid lists for simple prose.
- Rationale:
  - Balances clear semantic scoping (hcontainers) with appropriate use of list semantics (blockList) where the law enumerates discrete, citable elements.
  - Keeps XSD compliance clean by placing containers at the correct hierarchy level while preserving intro and content roles.
  - Provides stable anchors and predictable eId schemes for cross-referencing and amendment tracking, aligning with ActsETL’s pipeline.
