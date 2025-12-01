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
    act_metadata, parse_body, parse_p, ActMeta
)
from actsetl.akn.skeleton import akn_skeleton


# Define the path to the test data directory
TEST_DATA_PATH = Path(__file__).parent.parent / "test_data"

class EISBParsingError(Exception):
    """Custom exception for errors during EISB parsing."""
    pass

def parse_eisb_to_akn(xml_content: str) -> etree._Element:
    """
    Parses an EISB XML string and transforms it into an Akoma Ntoso XML element.
    This is a simplified entry point for testing purposes.
    """
    if not xml_content:
        raise EISBParsingError("Input XML content cannot be empty.")

    try:
        # The real 'transform_xml' expects a file path. For this unit test on a string,
        # we'll parse directly, assuming UTF-8 and no special file-based entities
        # that the XSLT would otherwise handle.
        parser = etree.XMLParser(recover=False)
        root = etree.fromstring(xml_content.encode('utf-8'), parser)
    except etree.XMLSyntaxError as e:
        raise EISBParsingError(f"Malformed XML: {e}") from e

    # Create a basic AKN skeleton using placeholder metadata
    act_meta_tuple = act_metadata(root) if root.find("metadata") is not None else ActMeta(
        number=root.findtext("docNumber") or "0",
        year="1900",
        date_enacted=dtparse("1900-01-01"),
        status="enacted",
        short_title=root.findtext("docTitle") or "Untitled Act",
        long_title=parse_p(E.p(root.findtext("docTitle") or "An Act"))
    )
    
    akn_act = akn_skeleton(act_meta_tuple)
    
    # Get the body of the EISB and parse it
    eisb_body = root.find("body")
    if eisb_body is None:
        # If there's no body, return the skeleton with a warning or empty body.
        # For testing, we'll treat this as an error.
        raise EISBParsingError("EISB XML must contain a <body> element.")
        
    akn_body = akn_act.find("body")
    
    # The parse_body function returns multiple values, we capture them all
    final_body, final_toc, mod_info = parse_body(eisb_body, akn_body, toc)

    return akn_act

def read_test_file(path: str) -> str:
    """Helper function to read a test data file."""
    with open(TEST_DATA_PATH / path, "r", encoding="utf-8") as f:
        return f.read()

def test_parse_happy_path():
    """
    Tests that a well-formed EISB input file is correctly parsed into the expected AKN XML structure.
    """
    # Arrange
    eisb_input = read_test_file("eisb_input/happy_path.xml")
    expected_akn_output_str = read_test_file("akn_expected_output/happy_path.xml")
    
    # Act
    actual_akn_tree = parse_eisb_to_akn(eisb_input)
    
    # Assert
    # Parse the expected output string into an XML tree
    expected_akn_tree = etree.fromstring(expected_akn_output_str.encode('utf-8'))

    # Canonicalize both XML trees to ensure a consistent string representation
    # This makes the comparison robust against differences in whitespace, attribute order, etc.
    actual_akn_str_c14n = etree.tostring(actual_akn_tree, method="c14n")
    expected_akn_str_c14n = etree.tostring(expected_akn_tree, method="c14n")

    # For debugging, print the differences if they don't match
    if actual_akn_str_c14n != expected_akn_str_c14n:
        print("Actual XML:\n", etree.tostring(actual_akn_tree, pretty_print=True).decode())
        print("\nExpected XML:\n", etree.tostring(expected_akn_tree, pretty_print=True).decode())

    assert actual_akn_str_c14n == expected_akn_str_c14n

def test_parse_malformed_input():
    """
    Tests that the parser raises EISBParsingError when given a malformed XML file.
    """
    # Arrange
    malformed_input = read_test_file("eisb_input/malformed.xml")
    
    # Act & Assert
    with pytest.raises(EISBParsingError, match="Malformed XML"):
        parse_eisb_to_akn(malformed_input)

def test_parse_empty_input():
    """
    Tests that the parser raises EISBParsingError when given an empty string.
    """
    # Arrange
    empty_input = "" # Directly use an empty string
    
    # Act & Assert
    with pytest.raises(EISBParsingError, match="Input XML content cannot be empty."):
        parse_eisb_to_akn(empty_input)

def test_parse_empty_file():
    """
    Tests that the parser raises EISBParsingError when given content from an empty file.
    """
    # Arrange
    empty_file_content = read_test_file("eisb_input/empty.xml")

    # Act & Assert
    with pytest.raises(EISBParsingError, match="Input XML content cannot be empty."):
        parse_eisb_to_akn(empty_file_content)