# Discussion on Parsing Alternatives for ActsETL

This document contains a summary of a conversation about finding alternatives to regex for parsing legal text, specifically focusing on the `lark` and `pyparsing` libraries.

---

### **User:** What alternatives could I use to pattern matching instead of the regex used by RegexPatternLibrary.

**File:** `/home/stephen/Documents/code/ActsETL/actsetl/parsers/patterns.py`

---

### **Agent:**

Based on the content of `actsetl/parsers/patterns.py`, the regular expressions are used to parse specific, structured phrases in legal text. Here are several alternatives to this regex-based approach, ranging from simple to more powerful methods.

#### 1. Basic String Methods (`.startswith()`, `.find()`, `.split()`)

For the simplest patterns, you can use Python's built-in string functions. This is only suitable for fixed, exact matches.

*   **How it would work:**
    Instead of `re.compile(r"by the insertion of the following definitions:")`, you could check `text.startswith("by the insertion of the following definitions:")`. For a substitution like `"by the substitution of Y for X"`, you could use `.split(" for ")` and then process the two resulting parts.

*   **Pros:**
    *   No external libraries needed.
    *   Very fast for simple, exact matches.

*   **Cons:**
    *   Extremely brittle. Fails with minor variations in whitespace, punctuation, or capitalization.
    *   Becomes complex and unreadable for anything beyond simple presence checks (e.g., extracting the destination text in `amendment_substitution`).
    *   Not a viable general replacement for the logic in this file.

#### 2. Grammar-Based Parsing (e.g., `lark`, `pyparsing`)

This is the most powerful and fitting alternative for your use case. These libraries allow you to define a formal grammar that describes the structure of your text. The library then generates a parser that can read the text and produce a structured output (like a tree).

*   **How it would work (with `lark`):**
    You would define a grammar to describe the amendment instructions.

    ```python
    # Grammar definition (can be in a separate file)
    amendment_grammar = r"""
        ?start: substitution | insertion

        substitution: "by" "the" "substitution" "of" /.+/ "for" destination -> substitution
        insertion: "by" "the" "insertion" "of" /.+/ "after" destination -> insertion_after

        destination: /.+/

        %import common.WS
        %ignore WS
    """

    from lark import Lark
    parser = Lark(amendment_grammar, ignore_case=True)

    tree = parser.parse("by the substitution of the words 'new text' for the words 'old text':")
    # 'tree' would be a structured Tree object that you can easily navigate
    ```

*   **Pros:**
    *   **Clear and Maintainable:** A grammar is often more readable and easier to maintain than a collection of complex, interacting regular expressions.
    *   **Robust:** Handles complex and nested structures gracefully.
    *   **Structured Output:** Automatically creates a parse tree, which is much cleaner to work with than manually building dictionaries from regex match groups.

*   **Cons:**
    *   Requires adding a new library (`lark-parser` or `pyparsing`).
    *   Has a learning curve to understand how to write grammars.

#### 3. Natural Language Processing (NLP) with `spaCy`

For highly variable or natural language text, you could use an NLP library. `spaCy`'s "Matcher" can find sequences of words (tokens) based on their linguistic properties, not just their characters.

*   **How it would work:**
    You would define a pattern based on tokens (words, punctuation) and their attributes. This example looks for the words "substitution", "of", and "for".

    ```python
    import spacy
    from spacy.matcher import Matcher

    nlp = spacy.load("en_core_web_sm")
    matcher = Matcher(nlp.vocab)

    # Pattern to find "substitution of ... for ..."
    pattern = [
        {"LOWER": "substitution"},
        {"LOWER": "of"},
        {"IS_ASCII": True, "OP": "+"}, # One or more tokens for the new text
        {"LOWER": "for"},
        {"IS_ASCII": True, "OP": "+"}  # One or more tokens for the destination
    ]
    matcher.add("SUBSTITUTION", [pattern])

    doc = nlp("by the substitution of section 5 for section 4")
    matches = matcher(doc)
    # 'matches' contains the start/end token indices for matched spans
    ```

*   **Pros:**
    *   **Highly Flexible:** Can handle wide variations in phrasing, word order, and grammar.
    *   **Semantic Matching:** Can match on lemmas (base form of a word), part-of-speech, named entities, etc.

*   **Cons:**
    *   **High Complexity:** A significant increase in complexity and dependencies (`spaCy` and its models).
    *   **Slower Performance:** Much slower than regex or grammar-based parsing.
    *   **Overkill for this Problem:** The legal text in your file appears to be highly formulaic, making this approach unnecessarily complex for the current task.

#### Recommendation

For the patterns in `actsetl/parsers/patterns.py`, **Grammar-Based Parsing with a library like `lark` is the best alternative.** It provides a sweet spot between the brittleness of simple string methods and the high complexity of a full NLP solution. It would allow you to define the formulaic structure of the legal text in a clean, readable, and robust way.

---

### **User:** Why would I use lark instead of regex?

---

### **Agent:**

Excellent question. While regular expressions are powerful for finding patterns, `lark` is often a better choice for *parsing* structured text, which is what you're doing in `patterns.py`.

Here's a breakdown of why you would prefer `lark` for this specific file:

#### 1. Readability and Maintainability

Regex patterns can quickly become cryptic. A `lark` grammar, on the other hand, is declarative and often reads like a formal description of your data structure.

*   **Regex (from your file):**
    ```python
    re.compile(r'''by the substitution of (?P<new>["'"']["'"']?[^"'"']+'["'"']?) for (?P<old>["'"']["'"']?[^"'"']+'["'"'])''')
    ```
    This is dense and difficult to decipher for someone unfamiliar with the pattern.

*   **Lark Grammar (Conceptual):**
    ```lark
    substitution : "by the substitution of" quoted_string "for" quoted_string
    quoted_string : ESCAPED_STRING
    ```
    This is much easier to read. It clearly states that a `substitution` consists of literal phrases surrounding two `quoted_string`s. You are defining *what the structure is*, not *how to match it character-by-character*.

#### 2. Handling Structural Complexity

Your current code uses an `if/elif/else` chain in `match_amendment_instruction` to try multiple regex patterns in a specific order. This is a classic sign that you are trying to parse a language.

*   **With Regex:** You have to manually manage the priority and relationships between different patterns. If a new, more specific amendment type is added, you have to carefully place it in the `if/elif` chain.

*   **With Lark:** You can define all alternatives in one place using the `|` operator. The parser handles the logic of figuring out which rule matches.

    ```lark
    amendment : substitution | insertion_after | insertion_simple
    ```
    This single `amendment` rule replaces the entire `match_amendment_instruction` function. The grammar itself documents the different possible forms an amendment can take.

#### 3. Structured and Usable Output

With `regex`, you get a match object and have to manually pull out captured groups by name or index to build a dictionary or object. `lark` does this for you automatically by creating a **Parse Tree**.

*   **Regex:**
    ```python
    match = self.amendment_substitution.search(text)
    if match:
        return {
            'type': 'substitution',
            'destination_text': match.group('old_dest').strip(':')
        }
    ```
    You are mixing the parsing logic (`.search()`) with data extraction and transformation (`.group()`, `.strip()`).

*   **Lark:** The parser returns a tree structure that mirrors your grammar. You can then use a `Transformer` to cleanly convert this tree into your desired Python objects. This separates the parsing from the processing.

    ```python
    # A Lark Transformer class
    class MyTransformer(Transformer):
        def substitution(self, items):
            return {'type': 'substitution', 'destination_text': items[1]}
    ```

#### 4. Better Error Handling

When a regex pattern fails to match, you simply get `None`. It gives you no information about *why* or *where* it failed. A parser can tell you exactly where it encountered something it didn't expect.

*   **Regex:** `match` is `None`. Why? Was the "for" missing? Was there a typo? You don't know without more code.
*   **Lark:** Can raise an exception like `UnexpectedToken: Unexpected token ... at line 1, column 45. Expected: "for"`. This makes debugging your parser and your input data vastly easier.

---

**In summary:** Use **regex** when you need to **find** simple, independent patterns in a string (like finding all email addresses). Use a **parser generator like `lark`** when you need to **parse** text that has a nested or compositional structure—in other words, a grammar.

For `patterns.py`, you are not just finding substrings; you are interpreting a mini-language of legal amendments. This is a perfect use case for `lark`.

---

### **User:** Show me how the higlighted lines in patterns.py could be implemented in lark.

**Selection:**
```python
        # Provision identification patterns (use optional curly quote, capture the whole marker)
        # Curly quotes are Unicode  \u201c (left) and \u201d (right)
        self.subsection_pattern = re.compile(r"^\s?(“?\(\d+[A-Z]*\))")
        self.paragraph_pattern = re.compile(r"^\s?(“?\([a-z]+\))")
        self.subparagraph_pattern = re.compile(r"^\s?(“?\([ivx]+[a-z]*\))")
        self.clause_pattern = re.compile(r"^\s?(“?\([IVX]+\))")
        self.subclause_pattern = re.compile(r"^\s?(“?\([A-Z]+\))")
```

---

### **Agent:**

Of course. Here is how you could implement the logic for identifying provision markers using `lark` instead of the five separate regular expressions.

The solution has two parts:
1.  A **Lark grammar** that defines the structure of all possible markers in a single, readable format.
2.  A **Python function** that uses the grammar to parse the beginning of a line of text.

#### 1. The Lark Grammar

Instead of five separate regex patterns, you can define all the provision markers in one clear grammar. This grammar describes *what* a marker is, making it much easier to read and maintain than the regex.

```lark
// File: provision_grammar.lark

?start: provision_marker

// A provision marker is one of the following types.
// The "->" syntax creates a named rule in the parse tree.
provision_marker: subsection | paragraph | subparagraph | clause | subclause

// Define the structure for each marker type
subsection:     _OPEN _DIGITS [_UPPER] _CLOSE      -> subsection
paragraph:      _OPEN _LOWER _CLOSE               -> paragraph
subparagraph:   _OPEN _ROMAN_L [_LOWER] _CLOSE    -> subparagraph
clause:         _OPEN _ROMAN_U _CLOSE             -> clause
subclause:      _OPEN _UPPER _CLOSE               -> subclause

// --- Terminal Definitions ---
// These are the basic building blocks, like tokens in regex.

// Optional curly quote “ followed by an opening parenthesis
_OPEN:      "“"? "("
_CLOSE:     ")"

// Number and letter patterns
_DIGITS:    /\d+/
_UPPER:     /[A-Z]+/
_LOWER:     /[a-z]+/
_ROMAN_L:   /[ivx]+/
_ROMAN_U:   /[IVX]+/

// Lark ignores whitespace between tokens by default, which works well here.
%import common.WS
%ignore WS
```

#### 2. Python Implementation

This Python code loads the grammar and uses it in a function that replicates the behavior of your original `match_provision_type` method.

```python
import lark

# Load the grammar from the string defined above
provision_grammar = """
    ?start: provision_marker
    provision_marker: subsection | paragraph | subparagraph | clause | subclause
    subsection:     _OPEN _DIGITS [_UPPER] _CLOSE      -> subsection
    paragraph:      _OPEN _LOWER _CLOSE               -> paragraph
    subparagraph:   _OPEN _ROMAN_L [_LOWER] _CLOSE    -> subparagraph
    clause:         _OPEN _ROMAN_U _CLOSE             -> clause
    subclause:      _OPEN _UPPER _CLOSE               -> subclause
    _OPEN:      "“"? "("
    _CLOSE:     ")"
    _DIGITS:    /\d+/
    _UPPER:     /[A-Z]+/
    _LOWER:     /[a-z]+/
    _ROMAN_L:   /[ivx]+/
    _ROMAN_U:   /[IVX]+/
    %import common.WS
    %ignore WS
"""

# Create a Lark parser instance from the grammar
provision_parser = lark.Lark(provision_grammar, start='provision_marker')

def match_provision_type_lark(text: str):
    """
    Identifies a provision type from the beginning of a line using a Lark parser.
    This mimics the behavior of the original regex-based method.

    Returns:
        A tuple of (provision_type, matched_marker_text) if a match is found,
        otherwise (None, None).
    """
    # 1. Isolate the potential marker (the first "word" of the line)
    # This is analogous to how the `^` and capture group work in the regex.
    stripped_text = text.lstrip()
    potential_marker = stripped_text.split(" ", 1)[0]

    try:
        # 2. Try to parse the potential marker
        tree = provision_parser.parse(potential_marker)

        # 3. If successful, return the type and the text we parsed.
        # The provision type comes from the rule alias (e.g., "-> subsection").
        provision_type = tree.data
        return (provision_type, potential_marker)

    except lark.exceptions.LarkError:
        # If parsing fails, it's not a valid provision marker.
        return (None, None)
```

#### Key Advantages of this Approach

*   **Readability:** The grammar is self-documenting. It's immediately clear that a `subsection` is composed of `_OPEN`, `_DIGITS`, an optional `_UPPER`, and `_CLOSE`.
*   **Maintainability:** If you need to add a new provision type (e.g., `sub-subparagraph`), you simply add a new line to the grammar. You don't need to write a new regex and add another `elif` to your Python code.
*   **Centralization:** All parsing logic for these markers is in one place (the grammar), not spread across multiple `re.compile` statements and a separate Python function that orchestrates them.

---

### **User:** show me how this would be implemented in pyparsing

---

### **Agent:**

Certainly. Here’s how you could implement the provision identification logic using the `pyparsing` library. This approach is similar to `lark` in that it builds a structured parser, but it does so programmatically in Python instead of using a separate grammar language.

#### 1. Pyparsing Expression Definitions

First, you define the building blocks of your parser using `pyparsing` classes. You combine these small expressions to build up the full parser for all provision markers.

```python
import pyparsing as pp

# --- Define pyparsing expressions for provision markers ---

# Define basic character and word patterns.
# `Word` is used for sequences of characters.
digits = pp.Word(pp.nums)
upper_letters = pp.Word(pp.alphas.upper())
lower_letters = pp.Word(pp.alphas.lower())
# Define character sets for roman numerals
lower_roman = pp.Word("ivx")
upper_roman = pp.Word("IVX")

# Define literal punctuation
LPAR, RPAR = map(pp.Literal, "()")
OPT_Q = pp.Optional("“") # Optional curly quote

# Combine the blocks to define the core structure of each marker.
# This is analogous to the main parts of your regex patterns.
subsection_core = OPT_Q + LPAR + digits + pp.Optional(upper_letters) + RPAR
paragraph_core = OPT_Q + LPAR + lower_letters + RPAR
subparagraph_core = OPT_Q + LPAR + lower_roman + pp.Optional(lower_letters) + RPAR
clause_core = OPT_Q + LPAR + upper_roman + RPAR
subclause_core = OPT_Q + LPAR + upper_letters + RPAR

# --- Helper function to tag results ---
def set_result_name(name):
    """A helper to create a parse action that tags the result with a 'type' name."""
    def parse_action(tokens):
        tokens["type"] = name
    return parse_action

# --- Create final expressions for each type ---
# `original_text_for` captures the exact substring that matches the expression.
# The parse action then adds our custom 'type' field to the results.
subsection_expr = pp.original_text_for(subsection_core).set_parse_action(set_result_name("subsection"))
paragraph_expr = pp.original_text_for(paragraph_core).set_parse_action(set_result_name("paragraph"))
subparagraph_expr = pp.original_text_for(subparagraph_core).set_parse_action(set_result_name("subparagraph"))
clause_expr = pp.original_text_for(clause_core).set_parse_action(set_result_name("clause"))
subclause_expr = pp.original_text_for(subclause_core).set_parse_action(set_result_name("subclause"))

# --- Combine all expressions into a single parser ---
# `MatchFirst` (^) is an efficient OR, trying each expression in order.
provision_parser = pp.MatchFirst([
    subsection_expr,
    paragraph_expr,
    subparagraph_expr,
    clause_expr,
    subclause_expr,
])
```

#### 2. Python Implementation

Now, you use the `provision_parser` object in a function that scans the beginning of a line of text, mimicking the original regex behavior.

```python
def match_provision_type_pyparsing(text: str):
    """
    Identifies a provision type from the beginning of a line using pyparsing.
    This mimics the behavior of the original regex-based method.

    Returns:
        A tuple of (provision_type, matched_marker_text) if a match is found,
        otherwise (None, None).
    """
    try:
        # `parse_string` with `parse_all=False` matches only from the start of
        # the string, which is equivalent to `re.match()`.
        # We .lstrip() to handle optional leading whitespace (`^\s?`).
        results = provision_parser.parse_string(text.lstrip(), parse_all=False)

        # Extract the data from the ParseResults object:
        # - The matched text comes from `original_text_for`.
        # - The provision type was added by our `set_result_name` parse action.
        matched_text = results[0]
        provision_type = results["type"]

        return (provision_type, matched_text)

    except pp.ParseException:
        # If the string doesn't match the grammar, pyparsing raises an exception.
        return (None, None)
```

#### Key `pyparsing` Concepts Used

*   **Expressions:** You build parsers by combining expression objects (`Word`, `Literal`, `Optional`) using standard Python operators like `+` (And) and `^` (MatchFirst/Or).
*   **`original_text_for()`:** This is a key helper that wraps an expression and returns the original, unmodified substring that it matched. This is perfect for getting the exact marker text.
*   **Parse Actions:** A parse action is a function that is called when an expression successfully matches. We use it here to attach a `type` name to the result, making it easy to identify which provision was found.
*   **`parse_string(..., parse_all=False)`:** This makes `pyparsing` behave like `re.match`, which is exactly what's needed to replace the logic in `patterns.py`.

---

### **User:** what are the pros and cons of lark vs pyparsing

---

### **Agent:**

Excellent question. Both `lark` and `pyparsing` are fantastic libraries for this task, and choosing between them often comes down to a preference in style and a trade-off between different strengths.

Here’s a comparison of their pros and cons, specifically for the task of parsing the provision markers in your file.

#### Lark

Lark is a "parser generator." You write a grammar in a dedicated syntax (similar to EBNF), and Lark generates a highly optimized parser from it.

**Pros:**

1.  **Clean Separation of Concerns:** The grammar is defined in a single, declarative string. This forces a clean separation between defining the *structure* of your language (the grammar) and writing the Python code that *processes* it (the `Transformer`). Many find this more readable and maintainable.
2.  **High Performance:** Lark generates a table-driven LALR(1) parser by default, which is extremely fast—often an order of magnitude faster than `pyparsing`. While not critical for this specific task, it's a major advantage for larger or more frequent parsing jobs.
3.  **Concise and Readable Grammar:** EBNF-style grammars are a standard, concise way to describe a language's structure. It's often easier to get a high-level overview of your language from a Lark grammar than from reading `pyparsing`'s Python code.
4.  **Excellent Error Messages:** When parsing fails, Lark provides very specific errors, like `Unexpected token ... at line 1, column 10. Expected one of: ...`, which makes debugging much easier.

**Cons:**

1.  **Grammar is "Just a String":** Your Lark grammar is written inside a Python string. This means your IDE's features (like code completion, syntax highlighting, and static analysis) won't apply to it. A typo in the grammar is a runtime error, not a linting error.
2.  **Learning a Mini-Language:** You have to learn Lark's specific EBNF-style syntax. While simple, it's another thing to learn on top of Python.

#### Pyparsing

Pyparsing takes a different approach. You build your parser programmatically by combining Python objects that represent the grammar rules.

**Pros:**

1.  **It's All Python:** You define your parser using pure Python code. This means you can leverage your IDE for code completion, refactoring, and debugging. It feels very "native" to a Python developer.
2.  **Highly Flexible and Dynamic:** Because it's just Python, you can build your grammar dynamically. You could, for example, create parser elements in a loop or configure them based on other variables, which is difficult to do with Lark's static grammar string.
3.  **Easy to Embed Actions:** It's very intuitive to attach "parse actions" (callback functions) to any part of your grammar to process data as it's being parsed, without needing a separate `Transformer` class.
4.  **Gentle Learning Curve:** If you know Python, the learning curve is arguably flatter, as you are simply learning a new library's API, not a new declarative language.

**Cons:**

1.  **Lower Performance:** `pyparsing` is a recursive-descent parser, which has more overhead and is generally significantly slower than Lark's LALR(1) parser. Again, this is not a concern for your specific use case, but it matters at scale.
2.  **Can Be Verbose:** Building a grammar programmatically can sometimes require more lines of code than the equivalent Lark grammar, and the core structure can be obscured by the Python syntax.
3.  **No Left-Recursion:** Standard `pyparsing` expressions cannot handle left-recursive grammars (e.g., `expr = expr + term`). This requires using special helpers like `pp.operatorPrecedence` and can be a stumbling block for complex mathematical or logical grammars. (This is not an issue for your provision markers).

#### Summary and Recommendation

| Aspect            | Lark                                          | Pyparsing                                              |
| ----------------- | --------------------------------------------- | ------------------------------------------------------ |
| **Paradigm**      | Declarative (write a grammar)                 | Programmatic (build a grammar with Python code)        |
| **Performance**   | **++** (Very Fast)                            | **-** (Slower)                                         |
| **Readability**   | **+** (Clean, separate grammar)               | **+/-** (Can be verbose, but it's all Python)          |
| **IDE Support**   | **-** (Grammar is an opaque string)           | **++** (It's all Python, full IDE support)             |
| **Flexibility**   | **-** (Grammar is mostly static)              | **++** (Grammars can be built dynamically)             |
| **Winner for...** | **Speed and formal correctness**              | **Python-native feel and dynamic parser construction** |

**For your specific use case of parsing provision markers:**

Both libraries are excellent choices and vastly superior to a collection of regular expressions.

*   If you prefer a clean, formal definition of your markers and want a solution that is standard in the world of language parsing, **choose Lark**.
*   If you prefer to stay entirely within the Python ecosystem and want your parser definition to be treated like any other Python code by your tools, **choose Pyparsing**.

Since the performance difference is irrelevant here, the decision truly comes down to which coding style you and your team find more readable and maintainable.

---

### **User:** Why do you state Lark is "a solution that is standard to the world of language parsing"?

---

### **Agent:**

That's a fair question, and I should clarify my statement. When I say Lark represents a "standard" solution, I'm referring to the **methodology** it employs, which is a cornerstone of computer science and language design, rather than suggesting the Lark library itself is the only tool everyone uses.

Here’s a more detailed breakdown:

#### 1. The Paradigm of Formal Grammars

The "standard" way to design and parse a structured language (from simple configuration files to complex programming languages like Python itself) is to first define its structure using a **formal grammar**.

*   **EBNF (Extended Backus-Naur Form):** Lark uses an EBNF-style syntax. This is a universally recognized, standard notation for formally describing the syntax of a language. It's what you would learn in any university course on compilers or programming language theory.
*   **Parser Generators:** The concept of writing a grammar and using a tool to automatically generate a parser has been a standard practice for decades. Classic, industry-defining tools like **Yacc** (Yet Another Compiler-Compiler) and **Lex** in the C world, or the widely-used **ANTLR** in the Java ecosystem, all follow this exact paradigm.

Lark is a modern, fast, and Python-native implementation of this classic, time-tested, and standard approach to parsing.

#### 2. Why it's a "Standard Solution" for Your Problem

The text you are trying to parse in `patterns.py` isn't just random text; it has clear, compositional rules:
*   A `provision_marker` can be a `subsection` OR a `paragraph` OR a `clause`, etc.
*   A `subsection` is composed of an `open_paren`, `digits`, an optional `letter`, and a `close_paren`.

This structure makes it a "mini-language." Applying a tool designed for parsing languages is therefore the standard and most robust engineering solution.

#### 3. Contrast with Non-Standard Approaches

*   **Regex Collections:** Using a series of `if/elif` statements with multiple, independent regex patterns is an *ad-hoc* approach. It works for simple cases, but it's not a standard methodology for parsing structured language. It often becomes brittle and hard to maintain as the "language" (the legal text formats) grows in complexity.
*   **Manual String Splitting:** Manually parsing with `.split()` and `.find()` is even more ad-hoc and is generally not considered a scalable or robust solution for anything but the simplest formats.

In short, I called the approach "standard" because **Lark applies decades of established computer science principles for language parsing** to your problem, providing a solution that is more robust, maintainable, and scalable than assembling a parser manually from regex and conditional logic.

---

### **User:** Tell me what you need me to provide to help you create a Lark grammar for my use case of eisb act XML parsing.

---

### **Agent:**

Excellent question. To create a robust Lark grammar for your entire `eisb.xml` parsing use case, I need to understand the structure of the input files and the desired output. The regex patterns you've highlighted are just one piece of the puzzle.

Here is what I need you to provide to help you best:

#### 1. A Representative Sample of the Input XML

This is the most important item. I need to see the structure I'll be parsing. A small but complete example is perfect. Based on your file structure, the contents of these two files would be a great start:

*   `tests/test_data/eisb_input/part_and_1_section.eisb.xml` (for a simple, common structure)
*   `tests/test_data/eisb_input/full_act.eisb.xml` (for a more complete picture of a whole document)

#### 2. An Example of the Desired Output

The project name `ActsETL` and the presence of an `akn/` directory suggest you are transforming the EISB format into Akoma Ntoso XML. To understand the goal of the transformation, please provide the **expected output** that corresponds to one of the input files. For example:

*   The content of `tests/test_data/akn_expected_output/part_and_1_section.akn.xml`.

This will tell me exactly which elements need to be extracted and how they should be structured in the final result.

#### 3. An Explanation of the Document Hierarchy

A brief description of how a typical Act is structured would be very helpful. For example:

*   "An Act always starts with a `num` and `year`, followed by a `citation` section. Then it contains one or more `Part`s. Each `Part` has a heading and contains multiple `Section`s. Some sections are special, like 'commencement' sections..."

#### 4. Details on Special Cases and Inline Content

Your test data suggests there are many special cases. To create a comprehensive grammar, I would need examples and explanations for things like:

*   **Amendments:** What does the XML for a `complex_amendment_provisions.eisb.xml` look like?
*   **Tables:** How are tables (`inserted_table.eisb.xml`) represented?
*   **Definitions:** How are definition lists structured within a section (`part_definitions_section.eisb.xml`)?
*   **Inline elements:** Besides the provision markers, are there other inline tags for things like bold, italics, or other text formatting?

Once I have a clearer picture of these four things, I can help you design a Lark grammar that accurately models your `eisb.xml` format and facilitates its transformation.

---

### **User:** Please clarify how I should provide these examples and explanations. Can they all be added as context items using the "@" context flag or should I add them to a specific directory?

---

### **Agent:**

Great question. The best way is a combination of both methods. Here is a clear guide on how to provide the information I need:

1.  **For File Contents (Input and Output):**
    Please provide the contents of the XML files by referencing them with the `@` flag directly in your message. This is the most effective way for me to see their content. For example:

    `@tests/test_data/eisb_input/full_act.eisb.xml`
    `@tests/test_data/akn_expected_output/part_and_1_section.akn.xml`

2.  **For Explanations (Hierarchy and Special Cases):**
    For the descriptions of the document structure, special cases (like amendments and tables), and any other rules, you can write those explanations directly here in the chat. Plain text is perfect for this.

To summarize, you can put it all in one message like this:

---
**Example Message:**

Here are the files and explanations you requested:

`@tests/test_data/eisb_input/full_act.eisb.xml`
`@tests/test_data/akn_expected_output/part_and_1_section.akn.xml`

**Document Hierarchy:**
"An Act always starts with a `num` and `year`, followed by a `citation` section. Then it contains one or more `Part`s..."

**Special Cases:**
"Tables are represented with a `<table ...>` tag inside a `<content>` block. Amendments are marked with `<amendment ...>` tags..."
---

Once you provide those items, I'll have everything I need to start drafting the Lark grammar for you.
