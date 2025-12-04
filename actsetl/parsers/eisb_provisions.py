'''
Parses provisions of an Act
'''
import logging
from typing import List, Tuple
from collections import namedtuple
from dataclasses import dataclass
from dateutil.parser import parse as dtparse
from typing import List, Optional, Tuple

from lxml import etree
from lxml.builder import E


from actsetl.parsers.patterns import RegexPatternLibrary

log = logging.getLogger(__name__)

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

# Module-level regex patterns instance
_regex_patterns = RegexPatternLibrary()

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
                    #built_content = section_hierarchy([Provision("div", None, False, 0, 0, 'left', temp_root, "")] + self.content_buffer)
                    built_content = E.dummy_container()

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

def _contains_string(string, s: set[str]):
    """ Check whether sequence str contains ANY of the items in set. """
    return any([c in string for c in s])

def _get_text_layout(node: etree._Element) -> Tuple[int, int, str]:
    """
    Extract hanging, margin and alignment from a node's class attribute.
    Falls back to defaults if class is missing or malformed.
    """
    cls = node.get("class") or ""
    parts = cls.split()
    if len(parts) == 6:
        try:
            hang = int(parts[0]) if parts[0] != "0" else 0
            margin = int(parts[1]) if parts[1] != "0" else 0
            align = parts[3]
            return hang, margin, align
        except Exception:
            pass
    # defaults
    return 0, 0, "left"

def _identify_provision(node: etree._Element, patterns: RegexPatternLibrary, is_huw_flag: bool):
    """
    Identify structural metadata for a <p> node:
    - whether it's a subsection/paragraph/clause/subclause,
    - any explicit <b> marker indicating an inserted section title,
    - returns a dict with keys: tag, pnumber, eid, inserted, is_huw (updated)
    Does not mutate the node except in small, documented normalisations (like combining '(' + <i> cases).
    """
    meta = {
        "tag": "tblock",
        "pnumber": None,
        "eid": None,
        "inserted": False,
        "is_huw": is_huw_flag
    }

    # Combine a lone "(" + <i> ... ")" pattern
    ital = node.find("i")
    if node.text == "(" and ital is not None and ital.tail and ital.tail.startswith(")"):
        # Normalize into node.text and remove the italic so matching will work
        node.text = (node.text or "") + (ital.text or "") + (ital.tail or "")
        node.remove(ital)

    # Check for bolded marker (inserted section)
    b = node.find("./b")
    if b is not None and b.tail is not None:
        # Remove the <b> element but preserve the surrounding text per original approach
        etree.strip_elements(node, 'b', with_tail=False)
        # We'll treat this as an inserted section heading if layout indicates insertion
        # (preserve heuristic from original code)
        # Caller will supply hanging/margin values to decide threshold; we signal inserted here,
        # actual "inserted" decision is made by the caller based on hanging+margin threshold.
        meta["pnumber"] = (b.text or "").strip()
        meta['tag'] = "section"
         # set a temporary eid; caller may reassign based on exact tag chosen
        meta["eid"] = make_eid_snippet("sect", meta["pnumber"])

    # Provision type matching (subsection / paragraph / clause / subclause)
    provision_type, match = patterns.match_provision_type(node.text or "")
    if provision_type == 'subsection' and match is not None:
        meta["tag"] = "subsection"
        meta["pnumber"] = match.group(1)
        meta["eid"] = make_eid_snippet("subsect", meta["pnumber"])
        node.text = (node.text or "")[match.end():].lstrip()
    elif provision_type == 'paragraph' and match is not None:
        meta["pnumber"] = match.group(1)
        # determine paragraph vs subparagraph as original code did
        eid_number = "".join(d for d in meta["pnumber"] if d.isalnum())
        # decision about tag (paragraph vs subparagraph) is deferred until caller provides margin/is_huw
        meta["tag"] = "paragraph" # may be updated by caller
        node.text = (node.text or "")[match.end():].lstrip()
    elif provision_type == 'clause' and match is not None:
        meta["tag"] = "clause"
        meta["pnumber"] = match.group(1)
        meta["eid"] = make_eid_snippet("clause", meta["pnumber"])
        node.text = (node.text or "")[match.end():].lstrip()
    elif provision_type == 'subclause' and match is not None:
        meta["tag"] = "subclause"
        meta["pnumber"] = match.group(1)
        meta["eid"] = make_eid_snippet("subclause", meta["pnumber"])
        node.text = (node.text or "")[match.end():].lstrip()

    return meta

def extract_raw_provisions(sect: etree._Element, patterns: RegexPatternLibrary) -> List[Provision]:
    """
    Convert the raw <sect> children into a list of Provision objects.
    Each raw <p> or <table> can produce one or more Provision entries (structural + tblock).
    A monotonic integer idx is assigned to each Provision for stable referencing.
    """
    raw_provisions: List[Provision] = []
    nodes = sect.xpath("./p|./table")
    is_huw = False
    idx_counter = 0

    for node in nodes:
        hang, margin, align = _get_text_layout(node)
        text = "".join(node.xpath(".//text()")).strip()

        # Tables: convert and append as single provision
        if node.tag == "table":
            tbl = parse_table(node)
            raw_provisions.append(Provision("table", None, False, hang, margin, align, tbl, text, idx_counter))
            idx_counter += 1
            continue

        # Empty paragraph (tblock) - normalise and append
        if not text:
            p_el = parse_p(node)
            raw_provisions.append(Provision("tblock", None, False, hang, margin, align, p_el, text, idx_counter))
            idx_counter += 1
            continue

        # Identify potential structural markers and inserted headings
        meta = _identify_provision(node, patterns, is_huw)

        # If bold marker found earlier, and heuristic indicates inserted section, mark as such
        if meta['tag'] == "section" and (hang + margin) > INSERTED_SECTION_THRESHOLD:
            meta_tag = "section"
            meta_ins = True
            meta_eid = make_eid_snippet("sect", meta["pnumber"])
            # Build an XML container for this inserted section title (caller may later rename tag)
            xml_element = make_container(meta_tag, meta["pnumber"], attribs={"eId": meta_eid})
            # Append a provision representing the inserted section container
            raw_provisions.append(Provision("section", meta_eid, True, hang, margin, align, xml_element, text, idx_counter))
            idx_counter += 1
            # mark that we created an inserted section; also append the following tblock normally below
        else:
            # If identify_provision returned a paragraph-like marker, refine tag decisions here
            if meta["pnumber"] and meta["tag"] == "paragraph":
                # decide subparagraph vs paragraph using margin and is_huw heuristics
                eid_number = "".join(d for d in meta["pnumber"] if d.isalnum())
                if margin == PARAGRAPH_MARGIN_THRESHOLD:
                    chosen_tag = "paragraph"
                elif eid_number and eid_number[0].lower() in "ivx" and (margin == SUBPARAGRAPH_MARGIN_THRESHOLD or not is_huw):
                    chosen_tag = "subparagraph"
                else:
                    chosen_tag = "paragraph"
                meta["tag"] = chosen_tag
                meta["eid"] = make_eid_snippet("para" if chosen_tag == "paragraph" else "subpara", meta["pnumber"])
                # Update is_huw flag depending on pnumber being exactly "huw" (match original intent)
                is_huw = (meta["pnumber"] == "huw")

            # If meta indicates a structural element with xml, build the container element
            if meta.get("tag") and meta["tag"] != "tblock":
                xml_element = make_container(meta["tag"], meta.get("pnumber"), attribs={"eId": meta.get("eid")})
                raw_provisions.append(Provision(meta["tag"], meta.get("eid"), meta.get("inserted", False), hang, margin, align, xml_element, text, idx_counter))
                idx_counter += 1

        # Now the paragraph content itself (tblock) — ensure parse_p is called to normalise the p element
        parsed_p = parse_p(node)
        raw_provisions.append(Provision("tblock", None, meta.get("inserted", False), hang, margin, align, parsed_p, text, idx_counter))
        idx_counter += 1

        # If text ends with a closing curly double quote and there are more closing quotes than opening,
        # append a quoteend provision (retain original heuristic but slightly more explicit).
        if text.endswith(CDQ) and text.count(CDQ) > text.count(ODQ):
            raw_provisions.append(Provision("quoteend", None, True, hang, margin, align, None, text[-2:], idx_counter))
            idx_counter += 1

    return raw_provisions

def process_amendments_and_build(processor: AmendmentParser, raw_provisions: List[Provision]) -> Tuple[List[Provision], List[AmendmentMetadata]]:
    """
    Run the AmendmentParser over raw_provisions and build a processed_provisions list
    suitable for section_hierarchy().

    Uses stable idx linking to place inline <mod> elements: when the AmendmentParser
    returns a COMPLETED_INLINE event (produced for the instruction provision), the
    appropriate place to attach the returned <mod> is the most recent processed
    provision with xml not None whose input idx is less than the instruction's idx.
    """
    processed: List[Provision] = []
    for prov in raw_provisions:
        status, data = processor.process(prov)
        if status == "CONSUMED":
            # provision consumed as part of amendment parsing instruction/content
            continue
        elif status == "COMPLETED_BLOCK":
            # data is an XML block representing the completed <mod> block wrapped appropriately
            # wrap as a provision to be inserted into the hierarchy builder
            processed.append(Provision("mod_block", None, True, prov.hang, prov.margin, prov.align, data, None, prov.idx))
        elif status == "COMPLETED_INLINE":
            # Inline mod produced immediately on encountering an inline instruction.
            # Attach to the nearest preceding processed provision that has xml.
            mod_element = data
            attached = False
            for j in range(len(processed) - 1, -1, -1):
                candidate = processed[j]
                if candidate.xml is not None:
                    try:
                        candidate.xml.append(mod_element)
                        attached = True
                        break
                    except Exception:
                        # If append fails for any reason continue searching
                        continue
            if not attached:
                # fallback: append as top-level mod_block so it is not lost
                processed.append(Provision("mod_block", None, True, prov.hang, prov.margin, prov.align, mod_element, None, prov.idx))
                log.warning("Inline modification could not be attached to a previous provision; appended as mod_block")
        elif status == "IDLE":
            # No amendment activity — move provision forward
            processed.append(prov)
        else:
            # Unknown status — treat conservatively
            processed.append(prov)

    return processed, processor.active_mod_info

def parse_section(sect: etree._Element) -> Tuple[List[Provision], List[AmendmentMetadata]]:
    """
    Orchestrator: parse a <sect> element into a list of Provision objects (ready for section_hierarchy)
    and a list of AmendmentMetadata for active modifications.

    """
    # Basic section header handling
    snumber_el = sect.find("number")
    if snumber_el is None or snumber_el.text is None:
        raise ValueError("Section element missing <number>")
    snumber = snumber_el.text.strip()

    sheading_p = sect.find("./title/p")
    if sheading_p is None:
        raise ValueError("Section element missing title/p")
    sheading = parse_p(sheading_p)
    sheading.tag = "heading"

    eid = make_eid_snippet("sect", snumber)
    sect_xml = make_container("section", num=E.b(snumber), heading=sheading, attribs={"eId": eid})

    log.info("Parsing section %s  ...", snumber)

    patterns = RegexPatternLibrary()
    amendment_parser = AmendmentParser(eid, patterns=patterns)

    # Pass 1: Extract raw provisions
    raw_provisions = extract_raw_provisions(sect, patterns)

    # Prepend the section container itself (so hierarchy builder has a root for this section)
    # Use hang=-3, margin=11, align="left" to match original behaviour
    processed_provisions = [Provision("section", eid, False, -3, 11, "left", sect_xml, None, -1)]

    # Pass 2: Process amendments and build final processed list
    processed, active_mod_info = process_amendments_and_build(amendment_parser, raw_provisions)

    # Append processed to the initial container list
    processed_provisions.extend(processed)

    return processed_provisions, active_mod_info


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

def make_container(tag: str, num:E.b=None, heading:etree.Element=None, attribs:dict=None) -> E:
    """
    Generate a LegalDocML element with <tag> name and optional num/heading elements.
'    """
    if not attribs: attribs = {}
    # Build a safe attributes dict (coerce keys to strings, skip None keys)
    safe_attribs = {}
    for k, v in attribs.items():
        if k is None or v is None:
            # skip invalid attribute keys or None-valued attributes
            continue
        safe_attribs[str(k)] = str(v)
    container = etree.Element(tag, attrib=safe_attribs)
    if heading is not None:
        container.append(heading)
    if num is not None:
        container.append(E.num(num))
    return container

def _is_valid_eid_char(char: str) -> bool:
    """Check if character is valid for eId according to AKN-NC v1.0.
    
    Valid characters are: ASCII alphanumeric (a-z, 0-9), hyphen (-), underscore (_).
    """
    return char.isascii() and (char.isalnum() or char in '-_')


def make_eid_snippet(label: str, num: str) -> str:
    """
    Generate partial eId.
    
    According to AKN-NC v1.0 (OASIS Akoma Ntoso Naming Convention), the eId
    attribute may only contain ASCII lowercase letters (a-z), decimal digits (0-9),
    underscore (_), and hyphen (-). This function filters the input to only include
    these characters and converts to lowercase for compliance.
    
    References:
    - https://docs.oasis-open.org/legaldocml/akn-nc/v1.0/akn-nc-v1.0.html
    - akomantoso30.xsd (noWhiteSpace type allows any non-whitespace, but AKN-NC restricts this)
    """
    filtered_num = ''.join(d.lower() for d in num if _is_valid_eid_char(d))
    return f"{label}_{filtered_num}"

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

def parse_toplevel_elem(eisb_subdiv: etree) -> E:
    '''
    Parse a top-level eISB element into a LegalDocML element.
    '''
    
    
    title = eisb_subdiv.find("title").getchildren()
    number = "".join(title[0].xpath(".//text()"))
    sdheading_p = title[1]
    sdheading = parse_p(sdheading_p)
    sdheading.tag = "heading"
    eid = make_eid_snippet(eisb_subdiv.tag, number.split(" ")[-1])
    akn_toplevel_elem = E(
        eisb_subdiv.tag, E.num(number), sdheading, {"eId": eid}
        )
    return akn_toplevel_elem

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

def act_metadata(act: etree) -> ActMeta: 
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