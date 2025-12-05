"""
Unit tests for eISB provisions helpers (eId generation and slug rules).
"""
from actsetl.parsers.eisb_provisions import make_eid_snippet


def test_make_eid_snippet_section_and_subsection():
    assert make_eid_snippet("sect", "1") == "sec_1"
    assert make_eid_snippet("subsect", "1") == "subsec_1"


def test_make_eid_snippet_paragraph_and_subpara():
    assert make_eid_snippet("para", "A") == "para_a"
    assert make_eid_snippet("subpara", "i") == "subpara_i"


def test_make_eid_snippet_slugifies_text():
    # Preserve alnum characters and replace punctuation/spaces with underscores
    assert make_eid_snippet("definitionTerm", "Act of 1967") == "def_act_of_1967"
    assert make_eid_snippet("section", "71A") == "sec_71a"
