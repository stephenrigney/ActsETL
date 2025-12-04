# Akoma Ntoso Element Hierarchy for Irish Acts

This document provides a concise summary of the hierarchy of elements used in Irish Acts marked up according to the Akoma Ntoso XML schema (version 3.0).

## Document Overview

Irish Acts in Akoma Ntoso format use the namespace `http://docs.oasis-open.org/legaldocml/ns/akn/3.0` and validate against the `akomantoso30.xsd` schema.

---

## Element Hierarchy Summary

### Root Structure

| Element | Attributes | Description |
|---------|------------|-------------|
| `akomaNtoso` | `xmlns`, `xmlns:xsi`, `xsi:schemaLocation` | Root element containing the legislative document |
| `act` | `name` (e.g., "ActOfTheOireachtas") | Container for the entire act |

### Metadata Section (`meta`)

| Element | Parent | Attributes | Description |
|---------|--------|------------|-------------|
| `meta` | `act` | — | Container for all metadata |
| `identification` | `meta` | `source` (e.g., "#source") | Document identification block |
| `FRBRWork` | `identification` | — | Work-level FRBR identification |
| `FRBRExpression` | `identification` | — | Expression-level FRBR identification |
| `FRBRManifestation` | `identification` | — | Manifestation-level FRBR identification |
| `FRBRthis` | `FRBRWork`, `FRBRExpression`, `FRBRManifestation` | `value`, `showAs` | URI for this specific resource |
| `FRBRuri` | `FRBRWork`, `FRBRExpression`, `FRBRManifestation` | `value` | Base URI for the resource |
| `FRBRdate` | `FRBRWork`, `FRBRExpression`, `FRBRManifestation` | `date`, `name` (e.g., "enacted", "transformed") | Relevant date |
| `FRBRauthor` | `FRBRWork`, `FRBRExpression`, `FRBRManifestation` | `href` | Reference to the author |
| `FRBRcountry` | `FRBRWork` | `value` (e.g., "ie") | Country code |
| `FRBRnumber` | `FRBRWork` | `value` | Act number |
| `FRBRname` | `FRBRWork` | `value` | Short title of the act |
| `FRBRauthoritative` | `FRBRExpression` | `value` (boolean) | Whether authoritative |
| `FRBRlanguage` | `FRBRExpression` | `language` (e.g., "eng") | Language code |
| `FRBRformat` | `FRBRManifestation` | `value` (e.g., "application/akn+xml") | MIME type |
| `analysis` | `meta` | `source` | Container for analysis metadata |
| `references` | `meta` | `source` | Container for reference definitions |
| `TLCOrganization` | `references` | `eId`, `href`, `showAs` | Referenced organization |

### Front Matter

| Element | Parent | Attributes | Description |
|---------|--------|------------|-------------|
| `coverPage` | `act` | — | Cover/title page content |
| `preface` | `act` | — | Preamble and enacting formula |
| `p` | `coverPage`, `preface`, various | `class` | Paragraph element |
| `img` | `p` | `src` | Image (e.g., harp emblem) |
| `docNumber` | `p` | — | Act number display |
| `shortTitle` | `p` | — | Short title of the act |
| `longTitle` | `preface` | — | Long title container |
| `docDate` | `p` | `date` | Date of enactment |
| `formula` | `preface` | `name` (e.g., "EnactingText") | Enacting formula |

### Body Structure (Hierarchical Divisions)

| Element | Parent | Attributes | Description |
|---------|--------|------------|-------------|
| `body` | `act` | — | Main content container |
| `part` | `body` | `eId` (e.g., "part_1") | Part division |
| `chapter` | `part` | `eId` | Chapter division within a part |
| `section` | `body`, `part`, `chapter` | `eId` (e.g., "sect_1") | Section - primary unit of law |
| `subsection` | `section` | `eId` (e.g., "sect_1_subsect_1") | Subsection within a section |
| `paragraph` | `subsection`, `section` | `eId` | Lettered paragraph (a), (b), etc. |
| `subparagraph` | `paragraph` | `eId` | Roman numeral subparagraph (i), (ii) |
| `clause` | `subparagraph` | `eId` | Clause within subparagraph |
| `subclause` | `clause` | `eId` | Sub-clause |

### Content Elements within Divisions

| Element | Parent | Attributes | Description |
|---------|--------|------------|-------------|
| `num` | `part`, `chapter`, `section`, `subsection`, `paragraph`, etc. | — | Numbering element |
| `heading` | `part`, `chapter`, `section` | — | Heading text |
| `content` | `subsection`, `paragraph`, etc. | — | Container for paragraph content |
| `intro` | `section`, `subsection` | — | Introductory text before list items |
| `wrapUp` | `section`, `subsection` | — | Concluding text after list items |

### Inline Elements

| Element | Parent | Attributes | Description |
|---------|--------|------------|-------------|
| `b` | various | — | Bold text |
| `i` | various | — | Italic text |
| `p` | `content`, `heading`, etc. | `class` | Paragraph |

### Tables

| Element | Parent | Attributes | Description |
|---------|--------|------------|-------------|
| `table` | `content`, `quotedStructure` | `width`, `class`, `xmlns:x` | Table container |
| `colgroup` | `table` | — | Column group |
| `col` | `colgroup` | `width` | Column definition |
| `tr` | `table` | — | Table row |
| `td` | `tr` | `colspan`, `rowspan`, `valign` | Table cell |

### Amendment Structures

| Element | Parent | Attributes | Description |
|---------|--------|------------|-------------|
| `mod` | `p` | `eId` | Modification container |
| `quotedStructure` | `mod` | `eId`, `startQuote`, `endQuote` | Quoted amendment text structure |
| `quotedText` | `mod` | — | Inline quoted text in amendments |

### Back Matter

| Element | Parent | Attributes | Description |
|---------|--------|------------|-------------|
| `schedule` | `backmatter` | `eId` | Schedule/appendix |
| `title` | `schedule` | — | Schedule title |

---

## Schematic Element Hierarchy

```
akomaNtoso
└── act [@name]
    ├── meta
    │   ├── identification [@source]
    │   │   ├── FRBRWork
    │   │   │   ├── FRBRthis [@value, @showAs]
    │   │   │   ├── FRBRuri [@value]
    │   │   │   ├── FRBRdate [@date, @name]
    │   │   │   ├── FRBRauthor [@href]
    │   │   │   ├── FRBRcountry [@value]
    │   │   │   ├── FRBRnumber [@value]
    │   │   │   └── FRBRname [@value]
    │   │   ├── FRBRExpression
    │   │   │   ├── FRBRthis [@value]
    │   │   │   ├── FRBRuri [@value]
    │   │   │   ├── FRBRdate [@date, @name]
    │   │   │   ├── FRBRauthor [@href]
    │   │   │   ├── FRBRauthoritative [@value]
    │   │   │   └── FRBRlanguage [@language]
    │   │   └── FRBRManifestation
    │   │       ├── FRBRthis [@value]
    │   │       ├── FRBRuri [@value]
    │   │       ├── FRBRdate [@date, @name]
    │   │       ├── FRBRauthor [@href]
    │   │       └── FRBRformat [@value]
    │   ├── analysis [@source]
    │   └── references [@source]
    │       └── TLCOrganization [@eId, @href, @showAs]
    │
    ├── coverPage
    │   └── p [@class]
    │       ├── img [@src]
    │       ├── docNumber
    │       │   └── i
    │       └── shortTitle
    │
    ├── preface
    │   ├── p [@class]
    │   │   ├── img [@src]
    │   │   ├── docNumber
    │   │   └── shortTitle
    │   ├── longTitle
    │   │   └── p
    │   ├── p [@class="DateOfEnactment"]
    │   │   └── docDate [@date]
    │   └── formula [@name]
    │       └── p
    │
    ├── body
    │   ├── part [@eId]
    │   │   ├── num
    │   │   ├── heading
    │   │   │   └── b
    │   │   ├── chapter [@eId]
    │   │   │   ├── num
    │   │   │   ├── heading
    │   │   │   └── section [@eId]
    │   │   │       └── ...
    │   │   └── section [@eId]
    │   │       └── ...
    │   └── section [@eId]
    │       ├── num
    │       │   └── b
    │       ├── heading
    │       │   └── b
    │       ├── intro
    │       │   └── p
    │       ├── subsection [@eId]
    │       │   ├── num
    │       │   ├── intro
    │       │   │   └── p
    │       │   ├── content
    │       │   │   └── p
    │       │   │       ├── (text)
    │       │   │       ├── i
    │       │   │       └── b
    │       │   └── paragraph [@eId]
    │       │       ├── num
    │       │       ├── content
    │       │       │   └── p
    │       │       └── subparagraph [@eId]
    │       │           ├── num
    │       │           ├── content
    │       │           │   └── p
    │       │           └── clause [@eId]
    │       │               ├── num
    │       │               └── content
    │       │                   └── p
    │       └── wrapUp
    │           └── p
    │
    └── backmatter (optional)
        └── schedule [@eId]
            ├── title
            │   └── p
            └── (content elements)
```

---

## eId Naming Conventions

The `eId` attribute provides unique identifiers for addressable elements using hierarchical concatenation:

| Element Type | Pattern | Example |
|--------------|---------|---------|
| Part | `part_{number}` | `part_1` |
| Chapter | `chap_{number}` | `chap_1` |
| Section | `sect_{number}` | `sect_1`, `sect_118` |
| Subsection | `sect_{n}_subsect_{m}` | `sect_1_subsect_1` |
| Paragraph | `sect_{n}_subsect_{m}_para_{letter}` | `sect_1_subsect_1_para_a` |
| Subparagraph | `...para_{l}_subpara_{roman}` | `sect_1_subsect_1_para_a_subpara_i` |

---

## Common Attribute Values

### `class` Attribute (on `p` elements)
Used to preserve layout information from source:
- `"harp"` - Harp emblem paragraph
- `"Number"` - Act number paragraph
- `"shortTitle"` - Short title paragraph  
- `"DateOfEnactment"` - Date of enactment paragraph

### `name` Attribute
- On `act`: `"ActOfTheOireachtas"`
- On `formula`: `"EnactingText"`
- On `hcontainer`: `"definitions"`, `"definitionTerm"`

### `date` Attribute Format
ISO 8601 format: `YYYY-MM-DD` (e.g., `2024-01-01`)

### URI Patterns (`value` attribute on FRBR elements)
Follows ELI (European Legislation Identifier) structure:
- Work: `/eli/ie/oireachtas/{year}/act/{number}`
- Expression: `/eli/ie/oireachtas/{year}/act/{number}/enacted/en`
- Manifestation: `/eli/ie/oireachtas/{year}/act/{number}/enacted/en/akn`

---

## Notes

1. **Namespace**: All elements must be in the Akoma Ntoso 3.0 namespace.
2. **Validation**: Documents validate against `akomantoso30.xsd`.
3. **Hierarchy Levels**: The structural hierarchy from outermost to innermost is:
   `part → chapter → section → subsection → paragraph → subparagraph → clause → subclause`
4. **Content Containers**: Use `content` element to wrap `p` elements in leaf divisions.
5. **Amendments**: Modifications use `mod` with `quotedStructure` for block amendments or `quotedText` for inline changes.
