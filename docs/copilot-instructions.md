# ActsETL AI Coding Agent Instructions

## Project Overview
ActsETL transforms Irish legislative XML from eISB format (electronic Irish Statute Book) into Akoma Ntoso (LegalDocML) format. The system parses hierarchical legal documents, extracts amendment metadata, and validates against Akoma Ntoso 3.0 schema.

**Key directories:**
- `actsetl/parsers/` - Core parsing logic (eISB → intermediate structures)
- `actsetl/akn/` - Akoma Ntoso document construction and utilities
- `data/eisb/` - Input XML files in eISB format
- `data/akn/` - Output XML files in Akoma Ntoso format
- `actsetl/resources/xslt/` - XSLT transforms for character encoding and HTML conversion

## Architecture & Data Flow

### Three-Stage Pipeline
1. **Preprocessing** (`transform_xml` in `eisb_structure.py`): XSLT converts eISB special character tags (`<odq/>`, `<afada/>`, etc.) to UTF-8
2. **Parsing** (`parse_body` → `parse_section` → `parse_*`): Builds intermediate `Provision` dataclass objects with layout metadata (margin, hanging indent, alignment from CSS class strings)
3. **Assembly** (`section_hierarchy` + `akn_skeleton`): Constructs nested Akoma Ntoso hierarchy with proper eId generation and amendment tracking

### Amendment State Machine
`AmendmentParser` (in `eisb_provisions.py`) is a critical stateful parser with three states:
- **IDLE**: Scanning for amendment instructions
- **PARSING_INSTRUCTION**: Instruction detected, awaiting quoted content marker
- **CONSUMING_CONTENT**: Buffering provisions until quote terminator

Returns tuples: `("CONSUMED"|"COMPLETED_BLOCK"|"COMPLETED_INLINE"|"IDLE", data)`

### Hierarchical Structure Building
`section_hierarchy()` uses a **stack-based algorithm** to nest provisions:
- Maintains `(level_index, element)` tuples representing current ancestry path
- Pops stack until finding parent with strictly lower level (higher in hierarchy)
- Special handling for `INLINE_CONTAINER_TAGS` (mod_block, tblock, table) - appended to nearest ancestor's `<content>`

**Level ordering** (lowest index = outermost):
```python
LEVELS = ("part", "chapter", "section", "subsection", 
          "paragraph", "subparagraph", "clause", "subclause")
```

## Data Structures

### Core Types
```python
# Intermediate provision representation (preserves layout metadata)
@dataclass Provision:
    tag, eid, ins, hang, margin, align, xml, text, idx

# Amendment metadata for activeModifications block
AmendmentMetadata = namedtuple(
    "type source_eId destination_uri position old_text new_text"
)

# Act metadata extracted from eISB
ActMeta = namedtuple(
    "number year date_enacted status short_title long_title"
)
```

## Development Workflows

### Running the Parser
```bash
# Install in editable mode
python -m pip install -e .

# Basic conversion
actsetl data/eisb/act_6_2025.eisb.xml

# With options
actsetl data/eisb/act_43_2024.eisb.xml \
  --output data/akn/output.akn.xml \
  --notes notes.yaml \
  --loglevel DEBUG \
  --no-validate  # Skip XSD validation
```

### Testing
```bash
pytest tests/  # All tests
pytest tests/parsers/test_eisb_structure.py::TestTransformXml  # Specific test class
```

Tests use `tests/test_data/` with paired `eisb_input/*.eisb.xml` and `akn_expected_output/*.akn.xml` files.

### Debugging
VS Code configurations in `.vscode/launch.json`:
- "Python: ActsETL (Local - launch)" - F5 to debug with predefined args
- "Python: ActsETL (Attach - debugpy)" - Attach to running process on port 5678

Example attach workflow:
```bash
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client \
  -m actsetl.cli tests/test_data/eisb_input/part_and_1_section.eisb.xml \
  --loglevel INFO
```

## Project-Specific Patterns

### eId Generation
eIds use hierarchical concatenation with underscore separators:
```python
# Parent: "sec_3", Child: "subsec_1" → "sec_3__subsec_1"
_generate_child_eid(parent_eid, child_eid)
```
Missing parent eIds logged but child used as-is (fallback for robustness).

### Regex Pattern Library
`RegexPatternLibrary` (in `patterns.py`) centralizes all legal text parsing patterns:
- Amendment instructions: `amendment_substitution`, `amendment_insertion_*`
- Provision markers: `subsection_pattern` (e.g., `"(1)"`), `paragraph_pattern` (e.g., `"(a)"`)
- Handles curly quotes (`""''`) in both pattern definitions and captured text

**Pattern matching order matters** - more specific patterns checked first (e.g., inline substitution before general substitution).

### Layout-Based Provision Detection
eISB encodes structure in CSS class attributes: `"<hang> <margin> 0 <align> ..."` 
```python
# Thresholds determine provision type from margin values
INSERTED_SECTION_THRESHOLD = 8
PARAGRAPH_MARGIN_THRESHOLD = 14
SUBPARAGRAPH_MARGIN_THRESHOLD = 17
```

### Post-Processing Steps
After main parse, several fixup passes occur:
1. `fix_headings()` - Identifies centered text in `<p>` tags within `<quotedStructure>`, converts to `<heading>`
2. `build_active_modifications()` - Generates `<activeModifications>` block from collected `AmendmentMetadata`
3. `pop_styles()` - Removes style attributes if `--styles` flag used (for cleaner output)

### Validation Strategy
`akn_write()` validates against `akomantoso30.xsd` by:
1. Adding namespace to all elements: `{http://docs.oasis-open.org/legaldocml/ns/akn/3.0}`
2. Running `xsd.assertValid(akn)`
3. On failure, writes to `*.invalid_akn.xml` instead, logs each error with XPath

## Known Limitations (TODOs in codebase)
- Textual modifications track amendments but don't yet transform inline text content
- Table of Contents generation incomplete (referenced but not implemented)
- Destination URI parsing is placeholder - needs robust "section 118(5)" → URI conversion
- Cited legislation extraction not yet implemented

## Code Style Notes
- Uses `lxml` element builder: `from lxml.builder import E` for clean XML construction
- Logging via module-level `log = logging.getLogger(__name__)`
- Type hints present but incomplete (mixing `etree._Element` and `etree`)
- Test files in `tests/` mirror structure of `actsetl/` modules
