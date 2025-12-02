"""
Python module to parse Irish Act XML into LegalDocML.

"""
import logging
import re
import io
from collections import namedtuple
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from lxml import etree
from lxml.builder import E
from dateutil.parser import parse as dtparse

from actsetl.akn.utils import (
    akn_write, akn_root, akn_notes, active_mods, parsing_errors_writer )
from actsetl.akn.skeleton import akn_skeleton


log = logging.getLogger(__name__)

RESOURCES_PATH = Path(__file__).parent.parent / 'resources'
XSLT_PATH = RESOURCES_PATH / 'xslt' / 'eisb_transform.xslt'


ODQ, CDQ, OSQ, CSQ = "“", "”", '‘', '’'

INSERTED_SECTION_THRESHOLD, PARAGRAPH_MARGIN_THRESHOLD, SUBPARAGRAPH_MARGIN_THRESHOLD = 8, 14, 17

# Data structure to hold parsed amendment metadata
AmendmentMetadata = namedtuple("AmendmentMetadata", "type source_eId destination_uri position old_text new_text")
ActMeta = namedtuple("ActMeta", "number year date_enacted status short_title long_title")


@dataclass
class ProvisionMetadata:
    tag: Optional[str] = "tblock"
    eid: Optional[str] = None
    inserted: bool = False
    pnumber: Optional[str] = None
    hanging: int = 0
    margin: int = 0
    align: str = "left"
    xml: Optional[etree._Element] = None
    text: str = ""


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
            r"by the substitution of (?P<new>[\"'\"'][^\"'\"']+[\"'\"']) for (?P<old>[\"'\"'][^\"'\"']+[\"'\"'])"
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
            quote_chars = '"\'"' + "'"
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


class AmendmentParser:
    """A state machine for parsing amendments."""
    def __init__(self, section_eid, principal_act_uri="#principal_act", patterns=None):
        self.state = "IDLE"  # Can be IDLE, PARSING_INSTRUCTION, CONSUMING_CONTENT
        self.section_eid = section_eid
        self.principal_act_uri = principal_act_uri
        self.mod_counter = 1
        self.active_mod_info = []
        self.current_mod_block = None
        self.current_amendment_details = {}
        self.content_buffer = []
        self.patterns = patterns or RegexPatternLibrary()

    def _parse_instruction(self, text: str):
        """
        Parses amendment instruction text to extract action, destination, etc.
        Returns a dictionary with parsed information, or None.
        """
        return self.patterns.match_amendment_instruction(text)

    def _generate_destination_uri(self, text):
        # This is a placeholder. A real implementation would need a robust way
        # to parse text like "section 118(5)" into a URI fragment.
        text = text.lower().replace("subsection", "subsect")
        parts = self.patterns.parse_destination_uri_components(text)
        if not parts:
            log.warning("Could not generate destination URI for: %s", text)
            return self.principal_act_uri
        
        uri_parts = [f"{p[0]}_{p[1]}" for p in parts]
        return f"{self.principal_act_uri}/{'__'.join(uri_parts)}"

    def process(self, provision):
        """
        Processes a provision, manages state, and returns a completed XML block or None.
        Returns a tuple: (status, data)
        status can be:
        - CONSUMED: The provision was consumed by the parser.
        - COMPLETED_BLOCK: The parser completed a <mod> block. Data is the block.
        - COMPLETED_INLINE: The parser completed an inline <mod>. Data is the mod.
        - IDLE: The parser is idle and did not consume the provision.
        """
        text = provision.text or ""

        if self.state == "IDLE":
            details = self._parse_instruction(text)
            if details:
                self.state = "PARSING_INSTRUCTION"
                self.current_amendment_details = details
                if details.get('inline'):
                    mod_eid = f"{self.section_eid}_mod_{self.mod_counter}"
                    mod_block = E.mod(
                        E.quotedText(details['new_text'], startQuote="“", endQuote="”"),
                        eId=mod_eid
                    )
                    dest_uri = self._generate_destination_uri(text)
                    meta = AmendmentMetadata(
                        type='substitution', source_eId=f"#{mod_eid}",
                        destination_uri=dest_uri, position=None,
                        old_text=details['old_text'], new_text=details['new_text']
                    )
                    self.active_mod_info.append(meta)
                    self.mod_counter += 1
                    self.state = "IDLE"
                    return ("COMPLETED_INLINE", mod_block)
                return ("CONSUMED", None)
            else:
                return ("IDLE", provision)

        elif self.state == "PARSING_INSTRUCTION":
            text = provision.text or ""
            if (text.startswith(ODQ) and ODQ not in text[1:]) or text == ODQ:
                self.state = "CONSUMING_CONTENT"
                mod_eid = f"{self.section_eid}_mod_{self.mod_counter}"
                self.current_mod_block = E.mod(E.quotedStructure(startQuote="“"), eId=mod_eid)

                dest_uri = self._generate_destination_uri(self.current_amendment_details.get('destination_text', ''))
                meta = AmendmentMetadata(
                    type=self.current_amendment_details['type'],
                    source_eId=f"#{mod_eid}",
                    destination_uri=dest_uri,
                    position=self.current_amendment_details.get('position'),
                    old_text=None, new_text=None
                )
                self.active_mod_info.append(meta)

                if provision.xml.text and provision.xml.text.startswith(ODQ):
                    provision.xml.text = provision.xml.text[len(ODQ):]
                self.content_buffer.append(provision)

                return ("CONSUMED", None)
            else: # Text between instruction and quote
                return ("CONSUMED", None)

        elif self.state == "CONSUMING_CONTENT":
            if provision.tag == "quoteend":
                if self.current_mod_block is not None and self.current_mod_block.find('quotedStructure') is not None:
                    self.current_mod_block.find('quotedStructure').attrib['endQuote'] = provision.text or '”'
                
                qs = self.current_mod_block.find('quotedStructure') if self.current_mod_block is not None else None
                if qs is not None and self.content_buffer:
                    # This is where a mini-hierarchy builder would go.
                    # For now, we just append the raw XML from the buffer.
                    temp_root = E.div()
                    for p in self.content_buffer:
                        # This logic is complex and needs to replicate section_hierarchy
                        # For now, append directly.
                        temp_root.append(p.xml)
                    
                    # Run a simplified hierarchy build on the buffered content
                    built_content = section_hierarchy([Provision("div", None, False, 0, 0, 'left', temp_root, "")] + self.content_buffer)
                    for child in built_content.getchildren():
                        qs.append(child)

                completed_block = E.block(self.current_mod_block, name="quotedStructure")
                
                self.mod_counter += 1
                self.state = "IDLE"
                self.current_mod_block = None
                self.content_buffer = []
                self.current_amendment_details = {}
                return ("COMPLETED_BLOCK", completed_block)

            else:
                self.content_buffer.append(provision)
                return ("CONSUMED", None)

        return ("IDLE", provision)

def transform_xml(infn: str) -> str:
    '''
    Act XML published on eISB encodes certain special characters, including fadas and euro symbols, as XML nodes defined by the legislation.dtd schema. 
    These are converted to regular characters via an XSLT (eisb_transform.xslt) and the XML is then reserialised as utf-8
    '''
    with open(XSLT_PATH, encoding="utf-8") as f:
        leg_dtd_xslt = f.read()
    xml_doc = etree.parse(infn)
    xslt_doc = etree.parse(io.StringIO(leg_dtd_xslt))
    transform = etree.XSLT(xslt_doc)
    clean_xml = transform(xml_doc)
    return etree.tostring(clean_xml, pretty_print=True).decode("utf-8")

# Module-level regex patterns instance
_regex_patterns = RegexPatternLibrary()

def parse_ojref(ojref:str) -> str:
    """
    Parses a footnote reference to the Official Journal of the EU (OJ[EU]) into Eurlex URI.
    """
    ojref = ojref.replace(".", "").replace(" ", "")
    ojre = _regex_patterns.parse_oj_reference(ojref)
    if not ojre:
        return ""
    sr, yr, num, pg = ojre.group("series"), ojre.group("year"), int(ojre.group("number")), int(ojre.group("page"))
    ojuri = f"uriserv:OJ.{sr}_.{yr}.{num:03}.01.{pg:04}.01.ENG"
    return f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri={ojuri}"

def parse_p(p: etree) -> etree:
    """
    Converts eISB text content <p> into LegalDocML correct <p>.
    """
    p.tag = "p"
    etree.strip_tags(p, ['font', 'xref'])
    if p.attrib.get("class"):
        loc = p.attrib.pop("class").split(" ")
        if len(loc) == 6:
            tindent = int(loc[0])/2 if loc[0] != "0" else 0
            margin = int(loc[1])/2 if loc[1] != "0" else 0
            p.attrib['style'] = f"text-indent:{tindent};margin-left:{margin};text-align:{loc[3]}"
    for child in list(p.iter()):
        if child.tag == "fn":
            ref_text = child.findtext("./marker/su")
            ref_target = child.find("./p//su").tail.strip() if child.find("./p//su") is not None else ""
            href = parse_ojref(ref_target) if ref_target.startswith("OJ") else ""
            idx = p.index(child)
            ref = E.sup(E.ref(ref_text, title=ref_target, href=href))
            p.insert(idx, ref)
        elif child.tag == "graphic":
            child.tag = "img"
            child.attrib['src'] = f"/images/{child.attrib.pop('href')}"
            child.attrib.pop("quality", None)
        elif child.tag in ("sb", "su"):
            child.tag = child.tag.lower()
        elif child.tag == "unicode":
            if p.text is None: p.text = ""
            p.text += chr(int("0x" + child.attrib["ch"], 16)) + (child.tail or "")
    
    for key in list(p.attrib.keys()):
        if key not in ["style"]:
            p.attrib.pop(key)
    etree.strip_elements(p, ["fn", "unicode"], with_tail=False)
    return p

def make_container(tag: str, num:E.b=None, heading:str=None, attribs:dict=None) -> E:
    """
    Generate a LegalDocML element with <tag> name and optional num/heading elements.
    """
    if not attribs: attribs = {}
    # Build a safe attributes dict (coerce keys to strings, skip None keys)
    safe_attribs = {}
    for k, v in attribs.items():
        if k is None or v is None:
            # skip invalid attribute keys or None-valued attributes
            continue
        safe_attribs[str(k)] = str(v)
    container = etree.Element(tag, attrib=safe_attribs)
    if heading is not None: container.append(heading)
    if num is not None: container.append(E.num(num))
    return container

def make_eid_snippet(label: str, num:str):
    """
    Generate partial eId.
    """
    return f"{label}_{''.join(d for d in num if d.isalnum())}"

def parse_table(table: etree):
    """
    Convert eISB table element (and children) into correct LegalDocML XML structure.
    """
    etree.strip_tags(table, "tbody")
    etree.cleanup_namespaces(table)
    style = ""
    if table.attrib.get("class"):
        loc = table.attrib.pop("class").split(" ")
        if len(loc) == 6:
            style = f"text-indent:{int(loc[0])/2 if loc[0]!='0' else 0};margin-left:{int(loc[1])/2 if loc[1]!='0' else 0};text-align:{loc[3]}"    
    
    colgroup = table.find("colgroup")
    colwidths = [w.strip("%") for w in colgroup.xpath("./col/@width")]
    style += ";colwidths:" + ",".join(colwidths)
    table.attrib['style'] = style
    table.attrib["width"] = table.attrib['width'].strip("%")
    table.remove(colgroup)
    for row_idx, tr in enumerate(table.xpath("./tr")):
        for col_idx, td in enumerate(tr.xpath("./td")):
            valign = td.attrib.pop("valign")
            td.tag = "th" if row_idx == 0 else "td"
            td.attrib['style'] = f"width:{colwidths[col_idx]};vertical-align:{valign}"
            for p in td.xpath("./p"):
                parse_p(p)
    for key in list(table.attrib.keys()):
        if key not in ["style", "width"]:
            table.attrib.pop(key)
    return table

def contains(string, s: set[str]):
    """ Check whether sequence str contains ANY of the items in set. """
    return any([c in string for c in s])

def parse_section(sect: etree):
    """
    Generate LegalDocML section container from eISB section content.
    This version uses the AmendmentParser state machine and preserves provision identification.
    """
    Provision = namedtuple("Provision", "tag eid ins hang margin align xml text")
    snumber = sect.find("number").text.strip()
    sheading = parse_p(sect.find("./title/p"))
    sheading.tag = "heading"
    eid = make_eid_snippet("sect", snumber)
    sect_xml = make_container("section", num=E.b(snumber), heading=sheading, attribs={"eId": eid})
    
    log.info("Parsing section %s", snumber)
    patterns = RegexPatternLibrary()
    amendment_parser = AmendmentParser(eid, patterns=patterns)

    # Pass 1: Convert all raw XML elements to Provision objects with correct tags
    raw_provisions = []
    provs = sect.xpath("./p|./table")
    is_huw = False
    
    for i, p in enumerate(provs):
        text_loc = p.get("class").split(" ")
        hanging, margin, alignment = [int(i) for i in text_loc[:2]] + [text_loc[3]] if len(text_loc) == 6 else (0, 0, "left")
        text = "".join(p.xpath(".//text()")).strip()
        
        # Default values encapsulated in ProvisionMetadata
        meta = ProvisionMetadata(hanging=hanging, margin=margin, align=alignment, text=text)

        if p.tag == "table":
            raw_provisions.append(Provision("table", None, False, hanging, margin, alignment, parse_table(p), text))
            continue

        if not text:
            raw_provisions.append(Provision("tblock", None, False, hanging, margin, alignment, parse_p(p), text))
            continue
        
        # --- Start of preserved provision identification logic ---
        b = p.find("./b")
        if b is not None and b.tail is not None:
            etree.strip_elements(p, 'b', with_tail=False)
            if hanging + margin > INSERTED_SECTION_THRESHOLD:
                meta.tag = "section"
                meta.inserted = True
                meta.pnumber = (b.text or "").strip()
                meta.eid = make_eid_snippet("sect", meta.pnumber)
        
        # Use RegexPatternLibrary for provision type matching
        provision_type, match = patterns.match_provision_type(p.text or "")
        
        if provision_type == 'subsection':
            meta.tag = "subsection"
            meta.pnumber = match.group(1)
            meta.eid = make_eid_snippet("subsect", meta.pnumber)
            p.text = p.text[match.end():].lstrip()
        elif provision_type == 'paragraph':
            ital = p.find("i")
            if p.text == "(" and ital is not None and ital.tail and ital.tail.startswith(")"):
                p.text += ital.text + ital.tail
                p.remove(ital)
                # Re-check after normalizing italic tags
                provision_type, match = patterns.match_provision_type(p.text or "")
            
            if provision_type == 'paragraph':
                meta.pnumber = match.group(1)
                eid_number = "".join(d for d in meta.pnumber if d.isalnum())
                if margin == PARAGRAPH_MARGIN_THRESHOLD:
                    meta.tag = "paragraph"
                elif eid_number[0] in "ivx" and (margin == SUBPARAGRAPH_MARGIN_THRESHOLD or not is_huw):
                    meta.tag = "subparagraph"
                else:
                    meta.tag = "paragraph"
                p.text = p.text[match.end():].lstrip()
                meta.eid = make_eid_snippet("para" if meta.tag == "paragraph" else "subpara", meta.pnumber)
                is_huw = meta.pnumber in "huw"
        elif provision_type == 'clause':
            meta.tag = "clause"
            meta.pnumber = match.group(1)
            meta.eid = make_eid_snippet("clause", meta.pnumber)
            p.text = p.text[match.end():].lstrip()
        elif provision_type == 'subclause':
            meta.tag = "subclause"
            meta.pnumber = match.group(1)
            meta.eid = make_eid_snippet("subclause", meta.pnumber)
            p.text = p.text[match.end():].lstrip()

        parse_p(p)

        xml_element = make_container(meta.tag, meta.pnumber, attribs={"eId": meta.eid})
        meta.xml = xml_element
        
        raw_provisions.append(
            Provision(
                meta.tag, meta.eid, meta.inserted, hanging, margin, alignment, 
                xml_element, "".join(p.xpath(".//text()"))
            )
        )

        raw_provisions.append(Provision("tblock", None, meta.inserted, hanging, margin, alignment, p, text))
        

        if text.endswith(CDQ) and text.count(CDQ) > text.count(ODQ):
            raw_provisions.append(Provision("quoteend", None, True, hanging, margin, alignment, None, text[-2:]))

    # Pass 2: Process with AmendmentParser and build final list for hierarchy builder
    processed_provisions = [Provision("section", eid, False, -3, 11, "left", sect_xml, None)]
    
    for prov in raw_provisions:
        status, data = amendment_parser.process(prov)
        if status == "CONSUMED":
            continue
        elif status == "COMPLETED_BLOCK":
            processed_provisions.append(Provision("mod_block", None, True, prov.hang, prov.margin, prov.align, data, None))
        elif status == "COMPLETED_INLINE":
            # Find the provision that contained the instruction and modify it
            for i in range(len(processed_provisions) - 1, -1, -1):
                if processed_provisions[i].text == prov.text:
                    # This is complex. For now, just append the modified <p> tag.
                    # A full implementation would replace text with the mod element.
                    p_tag = processed_provisions[i].xml
                    p_tag.append(data) # This is not ideal but shows intent
                    break
            log.warning("Inline modification added. Manual placement of <mod> tag may be required.")
        elif status == "IDLE":
            processed_provisions.append(prov)

    return processed_provisions, amendment_parser.active_mod_info

def locate_tag(parent, tags:list):
    """
    Finds location in hierarchy of element's parent.
    """
    if parent is None: return None
    if parent.tag in tags: return parent
    curr = parent.getparent()
    while curr is not None:
        if curr.tag in tags: return curr
        curr = curr.getparent()
    return None

def append_subdiv(parent_container: etree, subdiv: namedtuple) -> etree:
    """
    Appends a subdivision to its correct parent in the XML tree.
    """
    if parent_container is None:
        raise ValueError(f"Cannot determine parent for subdivision: {etree.tostring(subdiv.xml)}")
    
    if subdiv.eid:
        subdiv.xml.attrib['eId'] = f"{parent_container.attrib.get('eId')}_{subdiv.eid}"
    parent_container.append(subdiv.xml)
    
    pre = subdiv.xml.getprevious()
    if pre is not None and pre.tag == "content":
        pre.tag = "intro"
    return subdiv.xml

def section_hierarchy(subdivs: list) -> E.section:
    """
    Arranges list of subdiv elements into section hierarchy.
    """
    if len(subdivs) == 0: 
        return None
    sectionparent = parent = subdivs[0].xml

    for subdiv in subdivs[1:]:
        if subdiv.tag == "mod_block":
            container = parent.find("content")
            if container is None:
                container = E.content(); parent.append(container)
            container.append(subdiv.xml)
        elif subdiv.tag in ["tblock", "table"]:
            container = parent.find("content")
            if container is None:
                container = E.content(); parent.append(container)
            container.append(subdiv.xml)
        else:
            # Hierarchy logic based on tag
            if subdiv.tag == "subsection":
                tags = ["section"]
            elif subdiv.tag == "paragraph":
                tags = ["section", "subsection"]
            elif subdiv.tag == "subparagraph": 
                tags = ["section", "subsection", "paragraph"]
            elif subdiv.tag == "clause": 
                tags = ["section", "subsection", "paragraph", "subparagraph"]
            elif subdiv.tag == "subclause": 
                tags = ["section", "subsection", "paragraph", "subparagraph", "clause"]
            else: 
                tags = ["part", "chapter", "section", "subsection", "paragraph", "subparagraph", "clause", "subclause"]
            
            container = locate_tag(parent, tags) or sectionparent
            parent = append_subdiv(container, subdiv)
    return sectionparent

def parse_body(eisb_parent: etree, akn_parent: E) -> tuple:
    """
    Build out the LegalDocML skeleton with content from eISB XML.
    """
    all_mod_info = []
    toplevel_tags = ["part", "chapter", "division"]
    for eisb_subdiv in eisb_parent.getchildren():
        if eisb_subdiv.tag == "sect":
            akn_section_subdivs, mod_info = parse_section(eisb_subdiv)
            all_mod_info.extend(mod_info)
            akn_section = section_hierarchy(akn_section_subdivs)
            if akn_section is not None:
                akn_parent.append(akn_section)
            
        
        elif eisb_subdiv.tag in toplevel_tags:
            title = eisb_subdiv.find("title").getchildren()
            number = "".join(title[0].xpath(".//text()"))
            sdheading_p = title[1]
            sdheading = parse_p(sdheading_p)
            sdheading.tag = "heading"
            eid = make_eid_snippet(eisb_subdiv.tag, number.split(" ")[-1])
            akn_toplevel_elem = E(
                eisb_subdiv.tag, E.num(number), sdheading, {"eId": eid}
                )
            akn_parent.append(akn_toplevel_elem)
            if akn_toplevel_elem.tag in toplevel_tags[1:]:
                akn_toplevel_elem.attrib['eId'] = f"{akn_toplevel_elem.getparent().attrib['eId']}_{akn_toplevel_elem.attrib['eId']}"
            

            _, mod_info = parse_body(eisb_subdiv, akn_toplevel_elem)
            all_mod_info.extend(mod_info)
    return akn_parent, all_mod_info

def generate_toc(act: etree) -> E:
    """
    Generate the TOC for the Act.
    """
    toc = act.find("./coverPage/toc")
    body = act.find("./body")
    index_level = 1
    levels = []
    sxml = eisb_parent.find("sect")
    level = 1 + (1 if eisb_parent.tag == "part" else 0) + (2 if eisb_parent.tag == "chapter" else 0)
    toc.append(
        E.tocItem(
            {"level": str(level), "class": "section", "href": f"#{sxml.attrib['eId']}"},
            E.inline({"name": "tocNum"}, sxml.findtext("./num/b")),
            E.inline({"name": "tocHeading"}, "".join(sxml.xpath("./heading//text()")))
        )
    )

    level = "1" if subdiv.tag == "part" else "2" if subdiv.tag == "chapter" else "3"
    toc.append(
        E.tocItem(
            {"level": level, "class": subdiv.tag, "href": f"#{eid}"},
            E.inline({"name": "tocNum"}, number),
            E.inline({"name": "tocHeading"}, "".join(sdheading.xpath(".//text()")))
        )
    )

    toc.append(
        E.tocItem(
            {"level": "1", "class": "schedule", "href": f"#{eid}"},
            E.inline({"name": "tocNum"}, number),
            E.inline({"name": "tocHeading"}, heading)
        )
    )

def act_metadata(act: etree) -> namedtuple: 
    """
    Parses Act metadata from eISB Act XML and returns as a named tuple.
    """
    metadata = act.find("metadata")
    short_title, number, year = metadata.findtext("title"), metadata.findtext("number"), metadata.findtext("year")
    log.info("Parsing metadata for: %s", short_title)
    doe = metadata.findtext("dateofenactment")
    date_enacted = dtparse(doe).date()
    long_title_p = act.xpath("./frontmatter/p[(contains(text(), 'AN ACT TO')) or (contains(text(), 'An Act to'))]")[0]
    return ActMeta(number, year, date_enacted, "enacted", short_title, parse_p(long_title_p))

def parse_schedule(root, act):
    """
    Schedules may contain a wide range of content types.
    """
    body = act.find("./body")
    for idx, sch in enumerate(root.xpath("./backmatter/schedule")):
        number ="".join(sch.xpath("./title/p[1]//text()"))
        heading = "".join(sch.xpath("./title/p[2]//text()"))
        eid = f"sched_{idx+1}"
        schedule = E.hcontainer({"name": "schedule", "eId": eid}, E.num(number), E.heading(heading), E.content())
        body.append(schedule)

        for p in sch.xpath("./p|./table"):
            schedule.find("content").append(parse_p(p) if p.tag == "p" else parse_table(p))
    return body

def fix_headings(act):
    """
    Identify and correctly tag headings in inserted text.
    """
    for sd in act.xpath("./body//quotedStructure/*[self::part or self::chapter or self::hcontainer[@name='schedule']][./num]"):
        num = sd.find("num")
        if num is not None and num.getnext() is not None and num.getnext().tag in ["content", "intro"]:
            ctr, p = num.getnext(), num.getnext().find("p")
            if p is not None and 'text-align:center' in p.attrib.get('style', ''):
                idx = sd.index(ctr)
                p.tag = "heading"; sd.insert(idx, p)
                if not ctr.getchildren(): sd.remove(ctr)

def build_active_modifications(mod_info_list: list) -> E:
    """
    Builds the <activeModifications> XML block from a list of AmendmentMetadata.
    """
    active_mods_elem = E.activeModifications()
    for meta in mod_info_list:
        textual_mod = E.textualMod(type=meta.type)
        textual_mod.append(E.source(href=meta.source_eId))
        dest_attribs = {"href": meta.destination_uri}
        if meta.position: dest_attribs['pos'] = meta.position
        textual_mod.append(E.destination(**dest_attribs))
        if meta.old_text: textual_mod.append(E.old(meta.old_text))
        if meta.new_text: textual_mod.append(E.new(meta.new_text))
        active_mods_elem.append(textual_mod)
    return active_mods_elem

