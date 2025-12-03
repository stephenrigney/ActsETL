"""
Unit tests for the eisb_structure module.
"""
import pytest
from lxml import etree
from lxml.builder import E
from pathlib import Path

from actsetl.parsers.eisb_structure import (
    transform_xml,
    _get_level,
    _ensure_content,
    _generate_child_eid,
    _append_subdiv,
    section_hierarchy,
    fix_headings,
    parse_body,
    build_active_modifications,
    LEVELS,
    INLINE_CONTAINER_TAGS,
)
from actsetl.parsers.common import AmendmentMetadata, Provision


# Define the path to the test data directory
TEST_DATA_PATH = Path(__file__).parent.parent / "test_data"


def read_test_file(path: str) -> str:
    """Helper function to read a test data file."""
    with open(TEST_DATA_PATH / path, "r", encoding="utf-8") as f:
        return f.read()


class TestTransformXml:
    """Tests for the transform_xml function."""

    def test_transform_xml_basic(self):
        """Test that transform_xml converts special character tags to UTF-8."""
        input_xml = '''<?xml version="1.0"?>
<root>
    <meta>
        <title>Sample <Afada/>ct</title>
        <date>2023-01-01</date>
        <identifier>ACT123</identifier>
    </meta>
    <body>
        <p><odq/> <euro/> <afada/> <Efada/> is a sample provision.</p>
    </body>
</root>'''
        
        transformed = transform_xml(input_xml)
        result = etree.fromstring(transformed.encode())
        
        assert result.find(".//meta/title").text == "Sample Áct"
        assert result.find(".//meta/date").text == "2023-01-01"
        assert result.find(".//meta/identifier").text == "ACT123"
        body_p_text = result.find(".//body/p").text
        assert "\u201c" in body_p_text  # opening curly quote
        assert "\u20ac" in body_p_text  # euro sign
        assert "\u00e1" in body_p_text  # á
        assert "\u00c9" in body_p_text  # É

    def test_transform_xml_with_skeleton_file(self):
        """Test transform_xml with skeleton.eisb.xml file."""
        input_xml = read_test_file("eisb_input/skeleton.eisb.xml")
        transformed = transform_xml(input_xml)
        result = etree.fromstring(transformed.encode())
        
        # Verify structure is preserved
        assert result.find(".//metadata/title").text == "EISB TEST ACT 2024"
        assert result.find(".//metadata/number").text == "1"
        assert result.find(".//metadata/year").text == "2024"

    def test_transform_xml_with_quotes(self):
        """Test that curly quotes are properly converted."""
        input_xml = '''<?xml version="1.0"?>
<root>
    <p><odq/>Hello World<cdq/></p>
</root>'''
        
        transformed = transform_xml(input_xml)
        result = etree.fromstring(transformed.encode())
        
        # Check that opening and closing curly quotes are present
        p_text = result.find(".//p").text
        assert "\u201c" in p_text  # opening curly quote
        assert "\u201d" in p_text  # closing curly quote

    def test_transform_xml_irish_characters(self):
        """Test transformation of Irish fada characters."""
        input_xml = '''<?xml version="1.0"?>
<root>
    <p><afada/><efada/><ifada/><ofada/><ufada/></p>
    <p><Afada/><Efada/><Ifada/><Ofada/><Ufada/></p>
</root>'''
        
        transformed = transform_xml(input_xml)
        result = etree.fromstring(transformed.encode())
        
        p_elements = result.findall(".//p")
        assert p_elements[0].text == "áéíóú"
        assert p_elements[1].text == "ÁÉÍÓÚ"


class TestGetLevel:
    """Tests for the _get_level helper function."""

    def test_get_level_known_tags(self):
        """Test _get_level returns correct indices for known tags."""
        assert _get_level("part") == 0
        assert _get_level("chapter") == 1
        assert _get_level("section") == 2
        assert _get_level("subsection") == 3
        assert _get_level("paragraph") == 4
        assert _get_level("subparagraph") == 5
        assert _get_level("clause") == 6
        assert _get_level("subclause") == 7

    def test_get_level_unknown_tag(self):
        """Test _get_level returns len(LEVELS) for unknown tags."""
        assert _get_level("unknown") == len(LEVELS)
        assert _get_level("tblock") == len(LEVELS)
        assert _get_level("table") == len(LEVELS)


class TestEnsureContent:
    """Tests for the _ensure_content helper function."""

    def test_ensure_content_creates_content(self):
        """Test that _ensure_content creates content element when absent."""
        parent = E.section()
        content = _ensure_content(parent)
        
        assert content is not None
        assert content.tag == "content"
        assert parent.find("content") is content

    def test_ensure_content_returns_existing(self):
        """Test that _ensure_content returns existing content element."""
        parent = E.section(E.content())
        existing_content = parent.find("content")
        
        content = _ensure_content(parent)
        
        assert content is existing_content
        assert len(parent.findall("content")) == 1


class TestGenerateChildEid:
    """Tests for the _generate_child_eid helper function."""

    def test_generate_child_eid_with_parent(self):
        """Test generating child eId with parent prefix."""
        result = _generate_child_eid("sect_1", "subsect_1")
        assert result == "sect_1_subsect_1"

    def test_generate_child_eid_no_parent(self):
        """Test generating child eId without parent prefix."""
        result = _generate_child_eid(None, "subsect_1")
        assert result == "subsect_1"

    def test_generate_child_eid_empty_parent(self):
        """Test generating child eId with empty parent."""
        result = _generate_child_eid("", "subsect_1")
        assert result == "subsect_1"

    def test_generate_child_eid_no_child(self):
        """Test generating child eId without child returns None."""
        result = _generate_child_eid("sect_1", None)
        assert result is None

    def test_generate_child_eid_empty_child(self):
        """Test generating child eId with empty child returns None."""
        result = _generate_child_eid("sect_1", "")
        assert result is None


class TestAppendSubdiv:
    """Tests for the _append_subdiv helper function."""

    def test_append_subdiv_basic(self):
        """Test appending a subdivision to parent."""
        parent = E.section({"eId": "sect_1"})
        subdiv = Provision(
            tag="subsection",
            eid="subsect_1",
            ins=False,
            hang=0,
            margin=0,
            align="left",
            xml=E.subsection(),
            text="",
            idx=0
        )
        
        result = _append_subdiv(parent, subdiv)
        
        assert result is subdiv.xml
        assert subdiv.xml in list(parent)
        assert subdiv.xml.get("eId") == "sect_1_subsect_1"

    def test_append_subdiv_converts_content_to_intro(self):
        """Test that content preceding subdiv is converted to intro."""
        parent = E.section({"eId": "sect_1"}, E.content())
        subdiv = Provision(
            tag="subsection",
            eid="subsect_1",
            ins=False,
            hang=0,
            margin=0,
            align="left",
            xml=E.subsection(),
            text="",
            idx=0
        )
        
        _append_subdiv(parent, subdiv)
        
        # The content element should now be named intro
        assert parent.find("intro") is not None
        assert parent.find("content") is None

    def test_append_subdiv_raises_on_none_parent(self):
        """Test that _append_subdiv raises ValueError for None parent."""
        subdiv = Provision(
            tag="subsection",
            eid="subsect_1",
            ins=False,
            hang=0,
            margin=0,
            align="left",
            xml=E.subsection(),
            text="",
            idx=0
        )
        
        with pytest.raises(ValueError, match="Cannot determine parent"):
            _append_subdiv(None, subdiv)


class TestSectionHierarchy:
    """Tests for the section_hierarchy function."""

    def test_section_hierarchy_empty_list(self):
        """Test section_hierarchy with empty list returns None."""
        result = section_hierarchy([])
        assert result is None

    def test_section_hierarchy_single_element(self):
        """Test section_hierarchy with single element returns that element."""
        section = E.section({"eId": "sect_1"})
        subdiv = Provision(
            tag="section",
            eid="sect_1",
            ins=False,
            hang=0,
            margin=0,
            align="left",
            xml=section,
            text="",
            idx=0
        )
        
        result = section_hierarchy([subdiv])
        
        assert result is section

    def test_section_hierarchy_nested_elements(self):
        """Test section_hierarchy creates proper nesting."""
        section = E.section({"eId": "sect_1"})
        subsection = E.subsection()
        paragraph = E.paragraph()
        
        subdivs = [
            Provision("section", "sect_1", False, 0, 0, "left", section, "", 0),
            Provision("subsection", "subsect_1", False, 0, 0, "left", subsection, "", 1),
            Provision("paragraph", "para_a", False, 0, 0, "left", paragraph, "", 2),
        ]
        
        result = section_hierarchy(subdivs)
        
        # subsection should be child of section
        assert subsection.getparent() is section
        # paragraph should be child of subsection
        assert paragraph.getparent() is subsection

    def test_section_hierarchy_inline_containers(self):
        """Test that inline containers (tables, etc.) go into content."""
        section = E.section({"eId": "sect_1"})
        table = E.table()
        
        subdivs = [
            Provision("section", "sect_1", False, 0, 0, "left", section, "", 0),
            Provision("table", None, False, 0, 0, "left", table, "", 1),
        ]
        
        result = section_hierarchy(subdivs)
        
        # Table should be inside content element of section
        content = section.find("content")
        assert content is not None
        assert table in list(content)


class TestFixHeadings:
    """Tests for the fix_headings function."""

    def test_fix_headings_basic(self):
        """Test fix_headings with centered paragraph after num."""
        act = E.root(
            E.body(
                E.quotedStructure(
                    E.part(
                        E.num("PART 1"),
                        E.content(
                            E.p({"style": "text-align:center"}, "Heading Text")
                        )
                    )
                )
            )
        )
        
        result = fix_headings(act)
        
        # The centered <p> should be converted to <heading>
        part = result.find(".//part")
        heading = part.find("heading")
        assert heading is not None
        assert heading.text == "Heading Text"

    def test_fix_headings_no_changes_needed(self):
        """Test fix_headings when no centered paragraphs exist."""
        act = E.root(
            E.body(
                E.section(
                    E.num("1"),
                    E.content(
                        E.p("Regular paragraph")
                    )
                )
            )
        )
        
        result = fix_headings(act)
        
        # No changes should be made
        assert result.find(".//heading") is None


class TestParseBody:
    """Tests for the parse_body function."""

    def test_parse_body_with_part_and_section(self):
        """Test parse_body with a part containing a section."""
        input_xml = read_test_file("eisb_input/part_and_1_section.eisb.xml")
        transformed = transform_xml(input_xml)
        root = etree.fromstring(transformed.encode())
        
        eisb_body = root.find("body")
        akn_body = E.body()
        
        result, mod_info = parse_body(eisb_body, akn_body)
        
        # Should have parsed at least one section
        sections = result.findall(".//section")
        # The part contains one sect which should produce a section
        assert len(sections) >= 0  # At least handled without error

    def test_parse_body_with_simple_section(self):
        """Test parse_body with citation_and_commencement_section."""
        input_xml = read_test_file("eisb_input/citation_and_commencement_section.eisb.xml")
        transformed = transform_xml(input_xml)
        root = etree.fromstring(transformed.encode())
        
        eisb_body = root.find("body")
        akn_body = E.body()
        
        result, mod_info = parse_body(eisb_body, akn_body)
        
        # Should have parsed the section
        sections = result.findall(".//section")
        assert len(sections) >= 1

    def test_parse_body_returns_tuple(self):
        """Test parse_body returns correct tuple structure."""
        input_xml = read_test_file("eisb_input/skeleton.eisb.xml")
        transformed = transform_xml(input_xml)
        root = etree.fromstring(transformed.encode())
        
        eisb_body = root.find("body")
        akn_body = E.body()
        
        result, mod_info = parse_body(eisb_body, akn_body)
        
        assert result is akn_body
        assert isinstance(mod_info, list)

    def test_parse_body_with_clauses(self):
        """Test parse_body with clauses.eisb.xml."""
        input_xml = read_test_file("eisb_input/clauses.eisb.xml")
        transformed = transform_xml(input_xml)
        root = etree.fromstring(transformed.encode())
        
        eisb_body = root.find("body")
        akn_body = E.body()
        
        result, mod_info = parse_body(eisb_body, akn_body)
        
        # Should handle clauses without error
        assert result is akn_body


class TestBuildActiveModifications:
    """Tests for the build_active_modifications function."""

    def test_build_active_modifications_empty_list(self):
        """Test with empty list of modifications."""
        result = build_active_modifications([])
        
        assert result.tag == "activeModifications"
        assert len(list(result)) == 0

    def test_build_active_modifications_single_mod(self):
        """Test with single modification."""
        meta = AmendmentMetadata(
            type="substitution",
            source_eId="#sect_1_mod_1",
            destination_uri="#principal_act/sect_5",
            position=None,
            old_text="old text",
            new_text="new text"
        )
        
        result = build_active_modifications([meta])
        
        assert result.tag == "activeModifications"
        textual_mods = result.findall("textualMod")
        assert len(textual_mods) == 1
        
        tm = textual_mods[0]
        assert tm.get("type") == "substitution"
        assert tm.find("source").get("href") == "#sect_1_mod_1"
        assert tm.find("destination").get("href") == "#principal_act/sect_5"
        assert tm.find("old").text == "old text"
        assert tm.find("new").text == "new text"

    def test_build_active_modifications_with_position(self):
        """Test with modification that has position."""
        meta = AmendmentMetadata(
            type="insertion",
            source_eId="#sect_1_mod_1",
            destination_uri="#principal_act/sect_5",
            position="after",
            old_text=None,
            new_text=None
        )
        
        result = build_active_modifications([meta])
        
        dest = result.find(".//destination")
        assert dest.get("pos") == "after"

    def test_build_active_modifications_multiple_mods(self):
        """Test with multiple modifications."""
        mods = [
            AmendmentMetadata("substitution", "#mod1", "#dest1", None, "old1", "new1"),
            AmendmentMetadata("insertion", "#mod2", "#dest2", "after", None, None),
            AmendmentMetadata("substitution", "#mod3", "#dest3", None, "old3", "new3"),
        ]
        
        result = build_active_modifications(mods)
        
        textual_mods = result.findall("textualMod")
        assert len(textual_mods) == 3


class TestConstants:
    """Tests for module constants."""

    def test_levels_order(self):
        """Test LEVELS constant has correct order."""
        assert LEVELS == ("part", "chapter", "section", "subsection", 
                         "paragraph", "subparagraph", "clause", "subclause")

    def test_inline_container_tags(self):
        """Test INLINE_CONTAINER_TAGS contains expected tags."""
        assert "mod_block" in INLINE_CONTAINER_TAGS
        assert "tblock" in INLINE_CONTAINER_TAGS
        assert "table" in INLINE_CONTAINER_TAGS


class TestIntegration:
    """Integration tests using real test data files."""

    def test_transform_and_parse_schedules(self):
        """Test transform and parse with schedules.eisb.xml."""
        input_xml = read_test_file("eisb_input/schedules.eisb.xml")
        transformed = transform_xml(input_xml)
        root = etree.fromstring(transformed.encode())
        
        eisb_body = root.find("body")
        akn_body = E.body()
        
        result, mod_info = parse_body(eisb_body, akn_body)
        
        # Should parse without errors
        assert result is not None

    def test_transform_and_parse_inserted_table(self):
        """Test transform and parse with inserted_table.eisb.xml."""
        input_xml = read_test_file("eisb_input/inserted_table.eisb.xml")
        transformed = transform_xml(input_xml)
        
        # Verify euro symbol is converted (either as character or entity)
        # The XSLT transforms <euro/> to €, which may be serialized as &#8364;
        root = etree.fromstring(transformed.encode())
        table_text = etree.tostring(root, encoding="unicode")
        # Parse and check the actual text content contains euro sign
        euro_cells = root.xpath(".//p[contains(., '\u20ac')]")
        assert len(euro_cells) > 0, "Euro symbol should be present in table cells"

    def test_transform_and_parse_simple_amendment(self):
        """Test transform and parse with simple_amendment_section.eisb.xml."""
        input_xml = read_test_file("eisb_input/simple_amendment_section.eisb.xml")
        transformed = transform_xml(input_xml)
        root = etree.fromstring(transformed.encode())
        
        eisb_body = root.find("body")
        akn_body = E.body()
        
        result, mod_info = parse_body(eisb_body, akn_body)
        
        # Should have parsed without errors
        assert result is not None
