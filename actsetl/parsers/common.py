"""
Common data structures, constants, and classes for EISB parsers.
"""
import re
from collections import namedtuple
from dataclasses import dataclass
from typing import Optional, List, Tuple
from pathlib import Path
from lxml import etree

# --- Constants ---

RESOURCES_PATH = Path(__file__).parent.parent / 'resources'
XSLT_PATH = RESOURCES_PATH / 'xslt' / 'eisb_transform.xslt'

ODQ, CDQ, OSQ, CSQ = "“", "”", '‘', '’'

INSERTED_SECTION_THRESHOLD, PARAGRAPH_MARGIN_THRESHOLD, SUBPARAGRAPH_MARGIN_THRESHOLD = 8, 14, 17

# --- Data Structures ---

AmendmentMetadata = namedtuple("AmendmentMetadata", "type source_eId destination_uri position old_text new_text")
ActMeta = namedtuple("ActMeta", "number year date_enacted status short_title long_title")

@dataclass
class Provision:
    """
    Intermediate representation for a provision derived from a raw eISB node.

    Field names intentionally match the original namedtuple order used by
    the existing AmendmentParser.process() so instances can be passed
    straight into that API.
    Fields: tag, eid, ins, hang, margin, align, xml, text, idx
    """
    tag: str
    eid: Optional[str]
    ins: bool
    hang: int
    margin: int
    align: str
    xml: Optional[etree._Element]
    text: str
    idx: int

class RegexPatternLibrary:
    """Centralized regex pattern library with compiled patterns and matching methods."""
    
    def __init__(self):
        # Amendment instruction patterns
        self.amendment_substitution = re.compile(
            r"by the substitution of .* for (?P<old_dest>.+)", 
            re.IGNORECASE
        )
        self.amendment_insertion_after = re.compile(
            r"by the insertion of .* after (?P<dest>.+)", 
            re.IGNORECASE
        )
        self.amendment_insertion_simple = re.compile(
            r"by the insertion of the following definitions:", 
            re.IGNORECASE
        )
        self.amendment_inline_substitution = re.compile(
            r'''by the substitution of (?P<new>["'"']["'"']?[^"'"']+'["'"']?) for (?P<old>["'"']["'"']?[^"'"']+'["'"'])'''
        )
        
        # Destination URI pattern
        self.destination_components = re.compile(
            r'(section|subsect|paragraph) (\w+)'
        )
        
        # OJ reference pattern
        self.oj_reference = re.compile(
            r"OJ(No)?(?P<series>[CL])(?P<number>\d+),\d+(?P<year>\d{4}),?p(?P<page>\d+)"
        )
        
        # Provision identification patterns (use optional curly quote, capture the whole marker)
        # Curly quotes are Unicode  \u201c (left) and \u201d (right)
        self.subsection_pattern = re.compile(r"^\s?([\u201c\u201d]?\(\d+[A-Z]*\))")
        self.paragraph_pattern = re.compile(r"^\s?([\u201c\u201d]?\([a-z]+\))")
        self.clause_pattern = re.compile(r"^\s?([\u201c\u201d]?\([IVX]+\))")
        self.subclause_pattern = re.compile(r"^\s?([\u201c\u201d]?\([A-Z]+\))")
    
    def match_amendment_instruction(self, text: str):
        """
        Match text against amendment instruction patterns.
        Returns dictionary with parsed information, or None.
        Order matters: more specific patterns first!
        """
        # Check inline substitution first (more specific)
        match = self.amendment_inline_substitution.search(text)
        if match:
            # Strip both straight and curly quotes
            quote_chars = '"\'' + "'"
            return {
                'type': 'substitution',
                'inline': True,
                'new_text': match.group('new').strip(quote_chars),
                'old_text': match.group('old').strip(quote_chars)
            }
        
        # General substitution (less specific)
        match = self.amendment_substitution.search(text)
        if match:
            return {
                'type': 'substitution',
                'destination_text': match.group('old_dest').strip(':')
            }
        
        match = self.amendment_insertion_after.search(text)
        if match:
            return {
                'type': 'insertion',
                'position': 'after',
                'destination_text': match.group('dest').strip(':')
            }
        
        match = self.amendment_insertion_simple.search(text)
        if match:
            return {
                'type': 'insertion',
                'position': None,
                'destination_text': ''
            }
        
        return None
    
    def parse_destination_uri_components(self, text: str):
        """Extract destination components from text."""
        return self.destination_components.findall(text)
    
    def parse_oj_reference(self, text: str):
        """Parse OJ reference, returns match object or None."""
        return self.oj_reference.search(text)
    
    def match_provision_type(self, text: str):
        """
        Identify provision type from text.
        Returns (provision_type, match_object) or (None, None).
        """
        match = self.subsection_pattern.match(text)
        if match:
            return ('subsection', match)
        
        match = self.paragraph_pattern.match(text)
        if match:
            return ('paragraph', match)
        
        match = self.clause_pattern.match(text)
        if match:
            return ('clause', match)
        
        match = self.subclause_pattern.match(text)
        if match:
            return ('subclause', match)
        
        return (None, None)
