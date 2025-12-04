"""
Unit tests for the EISB parser.
"""
from pathlib import Path
import sys

from actsetl.parsers.patterns import RegexPatternLibrary
from actsetl.parsers.eisb_provisions import make_eid_snippet

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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


class TestMakeEidSnippet:
    """Tests for the make_eid_snippet function.
    
    According to AKN-NC v1.0 (OASIS Akoma Ntoso Naming Convention), eId values
    must only contain ASCII lowercase letters (a-z), decimal digits (0-9),
    underscore (_), and hyphen (-).
    
    Reference: https://docs.oasis-open.org/legaldocml/akn-nc/v1.0/akn-nc-v1.0.html
    """
    
    def test_make_eid_snippet_ascii_digits(self):
        """Test eId with ASCII digits."""
        result = make_eid_snippet('sect', '123')
        assert result == 'sect_123'
    
    def test_make_eid_snippet_uppercase_to_lowercase(self):
        """Test that uppercase ASCII letters are converted to lowercase."""
        result = make_eid_snippet('sect', 'ABC')
        assert result == 'sect_abc'
    
    def test_make_eid_snippet_mixed_case(self):
        """Test with mixed case letters and digits."""
        result = make_eid_snippet('sect', 'AbC123')
        assert result == 'sect_abc123'
    
    def test_make_eid_snippet_filters_irish_fada(self):
        """Test that Irish fada characters are filtered out per AKN-NC v1.0.
        
        The AKN-NC v1.0 specification requires only ASCII characters in eId values.
        Irish fada characters (á, é, í, ó, ú) are Unicode and must be filtered out.
        """
        result = make_eid_snippet('sect', 'áéíóú')
        assert result == 'sect_'
    
    def test_make_eid_snippet_mixed_ascii_and_unicode(self):
        """Test with a mix of ASCII and non-ASCII characters."""
        result = make_eid_snippet('sect', 'Sé1An')
        assert result == 'sect_s1an'
    
    def test_make_eid_snippet_filters_parentheses(self):
        """Test that parentheses and other special characters are filtered."""
        result = make_eid_snippet('subsect', '(1A)')
        assert result == 'subsect_1a'
    
    def test_make_eid_snippet_uppercase_fada_characters(self):
        """Test that uppercase fada characters (Á, É, Í, Ó, Ú) are filtered out."""
        result = make_eid_snippet('sect', 'ÁÉÍÓÚ')
        assert result == 'sect_'
    
    def test_make_eid_snippet_preserves_label(self):
        """Test that the label prefix is preserved correctly."""
        result = make_eid_snippet('subsection', '5')
        assert result.startswith('subsection_')
        assert result == 'subsection_5'
    
    def test_make_eid_snippet_euro_symbol(self):
        """Test that euro symbol (€) is filtered out."""
        result = make_eid_snippet('sect', '€100')
        assert result == 'sect_100'
    
    def test_make_eid_snippet_hyphen(self):
        """Test that hyphen is preserved as per AKN-NC v1.0 specification."""
        result = make_eid_snippet('sect', '1-2')
        assert result == 'sect_1-2'
    
    def test_make_eid_snippet_underscore(self):
        """Test that underscore is preserved as per AKN-NC v1.0 specification."""
        result = make_eid_snippet('sect', '1_a')
        assert result == 'sect_1_a'
