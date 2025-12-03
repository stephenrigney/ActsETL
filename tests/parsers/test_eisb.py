"""
Unit tests for the EISB parser.
"""
import pytest
from lxml import etree
from lxml.builder import E
from pathlib import Path
from dateutil.parser import parse as dtparse


# It's good practice to add the project source to the path if needed,
# but pytest often handles this automatically.
# import sys
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from actsetl.parsers.eisb import (
    act_metadata, parse_body, parse_p, ActMeta, 
    RegexPatternLibrary, transform_xml, parse_ojref,
    make_eid_snippet
)
from actsetl.akn.skeleton import akn_skeleton


# Define the path to the test data directory
TEST_DATA_PATH = Path(__file__).parent.parent / "test_data"

class EISBParsingError(Exception):
    """Custom exception for errors during EISB parsing."""
    pass

def test_regex_library():
    """Test that the RegexPatternLibrary class works as expected."""
    patterns = RegexPatternLibrary()
    
    # Test amendment instruction matching
    print("Testing amendment instruction matching...")
    
    # Test substitution
    result = patterns.match_amendment_instruction(
        "by the substitution of something for section 5"
    )
    assert result is not None
    assert result['type'] == 'substitution'
    assert 'section 5' in result['destination_text']
    print("✓ Substitution pattern works")
    
    # Test insertion after
    result = patterns.match_amendment_instruction(
        "by the insertion of new text after section 10"
    )
    assert result is not None
    assert result['type'] == 'insertion'
    assert result['position'] == 'after'
    print("✓ Insertion after pattern works")
    
    # Test simple insertion
    result = patterns.match_amendment_instruction(
        "by the insertion of the following definitions:"
    )
    assert result is not None
    assert result['type'] == 'insertion'
    assert result['position'] is None
    print("✓ Simple insertion pattern works")
    
    # Test inline substitution
    result = patterns.match_amendment_instruction(
        "by the substitution of 'new text' for 'old text'"
    )
    assert result is not None
    assert result['type'] == 'substitution'
    assert result['inline'] is True
    assert result['new_text'] == 'new text'
    assert result['old_text'] == 'old text'
    print("✓ Inline substitution pattern works")
    
    # Test provision type matching
    print("\nTesting provision type matching...")
    
    # Test subsection
    ptype, match = patterns.match_provision_type("(1) Some text")
    assert ptype == 'subsection'
    assert match.group(1) == '(1)'
    print("✓ Subsection pattern works")
    
    # Test paragraph
    ptype, match = patterns.match_provision_type("(a) Some text")
    assert ptype == 'paragraph'
    assert match.group(1) == '(a)'
    print("✓ Paragraph pattern works")
    
    # Test clause
    ptype, match = patterns.match_provision_type("(I) Some text")
    assert ptype == 'clause'
    assert match.group(1) == '(I)'
    print("✓ Clause pattern works")
    
    # Test subclause
    ptype, match = patterns.match_provision_type("(A) Some text")
    assert ptype == 'subclause'
    assert match.group(1) == '(A)'
    print("✓ Subclause pattern works")
    
    # Test no match
    ptype, match = patterns.match_provision_type("Regular text without markers")
    assert ptype is None
    assert match is None
    print("✓ Non-matching text returns None correctly")
    
    # Test destination URI components
    print("\nTesting destination URI component parsing...")
    parts = patterns.parse_destination_uri_components("section 118 paragraph 5")
    assert len(parts) > 0
    print(f"✓ Found {len(parts)} component(s)")
    
    # Test OJ reference
    print("\nTesting OJ reference parsing...")
    match = patterns.parse_oj_reference("OJL150,12020,p5")
    assert match is not None
    assert match.group('series') == 'L'
    assert match.group('year') == '2020'
    print("✓ OJ reference pattern works")
    
    print("\n✅ All tests passed!")

def test_amendment_parser():
    """Test that amendment instructions are parsed correctly."""
    patterns = RegexPatternLibrary()
    
    test_instructions = [
        "by the substitution of something for section 5",
        "by the insertion of new text after section 10",
        "by the insertion of the following definitions:",
        "by the substitution of 'new text' for 'old text'"
    ]
    
    for instruction in test_instructions:
        result = patterns.match_amendment_instruction(instruction)
        assert result is not None, f"Failed to parse instruction: {instruction}"
        print(f"Parsed instruction: {instruction} -> {result}")
    
    print("✅ All amendment instruction tests passed!")

def test_transform_xml():
    """Test that the transform_xml function works as expected."""
    # Sample input XML
    input_xml = '''
    <root>
        <meta>
            <title>Sample <Afada/>ct</title>
            <date>2023-01-01</date>
            <identifier>ACT123</identifier>
        </meta>
        <body>
            <p><odq/> <euro/> <afada/> <Efada/> is a sample provision.</p>
        </body>
    </root>
    '''
    
    # Transform the XML
    transformed_xml = etree.fromstring(transform_xml(input_xml))

    # Check that the transformed XML has the expected structure
    assert transformed_xml.find(".//meta/title").text == "Sample Áct"
    assert transformed_xml.find(".//meta/date").text == "2023-01-01"
    assert transformed_xml.find(".//meta/identifier").text == "ACT123"
    assert transformed_xml.find(".//body/p").text == "“ € á É is a sample provision."
    
    print("✅ transform_xml test passed!")

def test_parse_ojref():
    """Test that OJ references are parsed correctly."""
    patterns = RegexPatternLibrary()
    
    test_ojrefs = [
        ("OJ No. L198, 25.7.2019. p.1.", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=uriserv:OJ.L_.2019.198.01.0001.01.ENG"),
        ("OJ No. L302, 17.11.2009, p. 32", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=uriserv:OJ.L_.2009.302.01.0032.01.ENG"),
        ("OJ No. L174, 1.7.2011, p. 1", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=uriserv:OJ.L_.2011.174.01.0001.01.ENG")
    ]
    
    for ojref, uri in test_ojrefs:
        match = parse_ojref(ojref)
        print(f"Parsed OJ reference: {ojref} -> {match}")
        print(match)
        assert match is not None, f"Failed to parse OJ reference: {ojref}"
        assert match == uri, f"Incorrect URI for OJ reference: {ojref}"
    print("✅ All OJ reference tests passed!")

def test_parse_p():
    """Test that parse_p function works as expected."""
    # Sample provision XML
    eisb_xml_file = TEST_DATA_PATH / "eisb_input" / "parse_p_input.eisb.xml"
    expected_output_file = TEST_DATA_PATH / "akn_expected_output" / "expected_parse_p_output.xml"
    with open(eisb_xml_file, "r", encoding="utf-8") as f:
        eisb_xml_snippet = f.read()
    p_transformed = transform_xml(eisb_xml_snippet)
    provision_xml = etree.fromstring(p_transformed)
    # Parse the provision
    p = parse_p(provision_xml)

    with open(expected_output_file, "r", encoding="utf-8") as f:
        expected_output = f.read()
    assert p.text == " In this section and "
    assert etree.tostring(p, pretty_print=True).decode("utf-8") == expected_output
    print("✅ parse_p test passed!")

def test_make_container():
    """Test that make_container function creates XML elements correctly."""
    from actsetl.parsers.eisb import make_container
    
    tag = "subsection"
    number = "1"
    heading = E.heading("Test heading")
    attribs = {"eId": "sect_1"}
    
    element = make_container(tag, number, heading, attribs)
    
    assert element.tag == tag
    assert element.get("eId") == "sect_1"
    assert element.find(".//heading").text == "Test heading"

    element = make_container(tag, number, None, None)

    assert element.find(".//heading") is None
    assert element.get("eId") is None

    print("✅ make_container test passed!")

def test_make_eid_snippet():
    """Test that make_eid_snippet function creates eId snippets correctly."""
    
    tag = "section"
    pnumber = "5A"
    
    eid_snippet = make_eid_snippet(tag, pnumber)
    
    assert eid_snippet == "section_5A"
    
    print("✅ make_eid_snippet test passed!")

def test_parse_table():
    """
    Tests the parse_table function using the inserted_table.eisb.xml file.
    It checks if the table is correctly transformed into the LegalDocML format.
    """
    # Arrange: Load and parse the input XML file
    eisb_xml_file = TEST_DATA_PATH / "eisb_input" / "inserted_table.eisb.xml"
    with open(eisb_xml_file, "r", encoding="utf-8") as f:
        eisb_xml_content = f.read()

    # The transform_xml function handles character entities like <euro/>
    # We parse the whole document and find the table, similar to how the main parser would
    transformed_content = transform_xml(eisb_xml_content)
    root = etree.fromstring(transformed_content)
    table_element = root.find(".//body/sect/table")

    # Act: Call the function under test
    from actsetl.parsers.eisb import parse_table
    parsed_table = parse_table(table_element)

    # Assert: Check various aspects of the transformation
    
    # 1. Check table attributes
    assert parsed_table.attrib['width'] == '100'
    assert 'text-indent:0' in parsed_table.attrib['style']
    assert 'margin-left:0' in parsed_table.attrib['style']
    assert 'text-align:left' in parsed_table.attrib['style']
    assert 'colwidths:70,30' in parsed_table.attrib['style']
    assert len(parsed_table.attrib) == 2 # Only 'width' and 'style' should remain

    # 2. Check that <colgroup> is removed
    assert parsed_table.find("colgroup") is None

    # 3. Check header row (first <tr> should have <th> cells)
    header_row = parsed_table.find("./tr[1]")
    header_cells = header_row.findall("./th")
    assert len(header_cells) == 2, "Header row should contain 2 <th> elements"
    
    # Check styles and content of header cells
    assert header_cells[0].attrib['style'] == 'width:70;vertical-align:top'
    p_in_th1 = header_cells[0].find('p')
    assert p_in_th1 is not None
    assert 'Class of Insured Person' in p_in_th1.find('b').text

    assert header_cells[1].attrib['style'] == 'width:30;vertical-align:top'
    p_in_th2 = header_cells[1].find('p')
    assert p_in_th2 is not None
    assert 'Amount of premium to be paid from Fund' in p_in_th2.find('b').text

    # 4. Check a data row (e.g., the second <tr> should have <td> cells)
    data_row = parsed_table.find("./tr[2]")
    data_cells = data_row.findall("./td")
    assert len(data_cells) == 2, "Data row should contain 2 <td> elements"

    # Check styles and content of data cells
    assert data_cells[0].attrib['style'] == 'width:70;vertical-align:top'
    p_in_td1 = data_cells[0].find('p')
    assert p_in_td1 is not None
    assert 'Male aged 70 years' in p_in_td1.text

    assert data_cells[1].attrib['style'] == 'width:30;vertical-align:top'
    p_in_td2 = data_cells[1].find('p')
    assert p_in_td2 is not None
    # The <euro/> tag is converted to '€' by transform_xml
    assert '€350' in p_in_td2.text

    # 5. Check total number of rows
    assert len(parsed_table.findall("./tr")) == 9

def test_parse_section():
    """Test that parse_section function works as expected."""
    from actsetl.parsers.eisb import parse_section
    
    # Sample section XML
    section_xml = E.section(
        E.p("This is section text.")
    )
    
    section_element = parse_section(section_xml)
    
    assert section_element.tag == "section"
    assert section_element.find(".//p").text == "This is section text."
    
    print("✅ parse_section test passed!")

def test_locate_tag():
    """Test that locate_tag function works as expected."""
    from actsetl.parsers.eisb import locate_tag
    
    # Sample XML
    sample_xml = E.root(
        E.section(
            E.p("This is section text.")
        ),
        E.clause(
            E.p("This is clause text.")
        )
    )
    
    section = locate_tag(sample_xml, "section")
    clause = locate_tag(sample_xml, "clause")
    
    assert section is not None
    assert section.tag == "section"
    assert clause is not None
    assert clause.tag == "clause"
    
    print("✅ locate_tag test passed!")

def test_append_subdiv():
    """Test that append_subdiv function works as expected."""
    from actsetl.parsers.eisb import append_subdiv
    
    # Sample parent XML
    parent_xml = E.root()
    
    # Sample child XML
    child_xml = E.subsection(
        E.p("This is subsection text.")
    )
    
    append_subdiv(parent_xml, child_xml)
    
    subdiv = parent_xml.find(".//subsection")
    assert subdiv is not None
    assert subdiv.find(".//p").text == "This is subsection text."
    
    print("✅ append_subdiv test passed!")

def test_section_hierarchy():
    """Test that section hierarchy is built correctly."""
    from actsetl.parsers.eisb import SectionMeta, build_section_hierarchy
    
    # Sample sections
    section1 = SectionMeta(tag="section", pnumber="1", eid="sec1", xml=E.section())
    subsection1 = SectionMeta(tag="subsection", pnumber="1", eid="subsec1", xml=E.subsection())
    subsection2 = SectionMeta(tag="subsection", pnumber="2", eid="subsec2", xml=E.subsection())
    
    sections = [section1, subsection1, subsection2]
    
    hierarchy = build_section_hierarchy(sections)
    
    assert len(hierarchy) == 1
    assert hierarchy[0].tag == "section"
    assert len(hierarchy[0].children) == 2
    assert hierarchy[0].children[0].tag == "subsection"
    
    print("✅ section hierarchy test passed!")

def test_parse_body():
    """Test that parse_body function works as expected."""
    from actsetl.parsers.eisb import parse_body
    
    # Sample body XML
    body_xml = E.body(
        E.section(
            E.p("This is section text.")
        ),
        E.clause(
            E.p("This is clause text.")
        )
    )
    
    akn_body = E.body()
    
    status, mod_info = parse_body(body_xml, akn_body)
    
    assert status == "IDLE"
    assert len(mod_info) == 0
    assert akn_body.find(".//section").find(".//p").text == "This is section text."
    
    print("✅ parse_body test passed!")

def read_test_file(path: str) -> str:
    """Helper function to read a test data file."""
    with open(TEST_DATA_PATH / path, "r", encoding="utf-8") as f:
        return f.read()

def test_parse_malformed_input():
    """
    Tests that the parser raises EISBParsingError when given a malformed XML file.
    """
    # Arrange
    malformed_input = read_test_file("eisb_input/malformed.xml")
    
    # Act & Assert
    with pytest.raises(EISBParsingError, match="Malformed XML"):
        pass

def test_parse_empty_input():
    """
    Tests that the parser raises EISBParsingError when given an empty string.
    """
    # Arrange
    empty_input = "" # Directly use an empty string
    
    # Act & Assert
    with pytest.raises(EISBParsingError, match="Input XML content cannot be empty."):
        pass

def test_parse_empty_file():
    """
    Tests that the parser raises EISBParsingError when given content from an empty file.
    """
    # Arrange
    empty_file_content = read_test_file("eisb_input/empty.xml")

    # Act & Assert
    with pytest.raises(EISBParsingError, match="Input XML content cannot be empty."):
        pass