"""
Python module to parse Irish Act XML into LegalDocML.

"""
import logging
import io
from collections import namedtuple

from lxml import etree
from lxml.builder import E
from dateutil.parser import parse as dtparse

from actsetl.parsers.eisb_provisions import parse_section

from actsetl.parsers.common import XSLT_PATH, ActMeta


log = logging.getLogger(__name__)

def transform_xml(eisb_xml: str) -> str:
    '''
    Act XML published on eISB encodes certain special characters, including fadas and euro symbols, as XML nodes defined by the legislation.dtd schema. 
    These are converted to regular characters via an XSLT (eisb_transform.xslt) and the XML is then reserialised as utf-8
    '''
    with open(XSLT_PATH, encoding="utf-8") as f:
        leg_dtd_xslt = f.read()
    xml_doc = etree.fromstring(eisb_xml)
    xslt_doc = etree.parse(io.StringIO(leg_dtd_xslt))
    transform = etree.XSLT(xslt_doc)
    clean_xml = transform(xml_doc)
    return etree.tostring(clean_xml, pretty_print=True).decode("utf-8")

def locate_tag(parent, tags:list):
    """
    Finds location in hierarchy of element's parent.
    """
    if parent is None:
        return None
    if parent.tag in tags:
        return parent
    curr = parent.getparent()
    while curr is not None:
        if curr.tag in tags:
            return curr
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
                container = E.content()
                parent.append(container)
            container.append(subdiv.xml)
        elif subdiv.tag in ["tblock", "table"]:
            container = parent.find("content")
            if container is None:
                container = E.content()
                parent.append(container)
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



def fix_headings(act):
    """
    Identify and correctly tag headings in inserted text.
    """
    for subdiv in act.xpath("./body//quotedStructure/*[self::part or self::chapter or self::hcontainer[@name='schedule']][./num]"):
        num = subdiv.find("num")
        if num is not None and num.getnext() is not None and num.getnext().tag in ["content", "intro"]:
            ctr, p = num.getnext(), num.getnext().find("p")
            if p is not None and 'text-align:center' in p.attrib.get('style', ''):
                idx = subdiv.index(ctr)
                p.tag = "heading"
                subdiv.insert(idx, p)
                if not ctr.getchildren():
                    subdiv.remove(ctr)
    return act

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
            akn_toplevel_elem = parse_toplevel_elem(eisb_subdiv)

            akn_parent.append(akn_toplevel_elem)
            if akn_toplevel_elem.tag in toplevel_tags[1:]:
                akn_toplevel_elem.attrib['eId'] = f"{akn_toplevel_elem.getparent().attrib['eId']}_{akn_toplevel_elem.attrib['eId']}"
            

            _, mod_info = parse_body(eisb_subdiv, akn_toplevel_elem)
            all_mod_info.extend(mod_info)
    parse_schedule(eisb_parent, akn_parent)
    fix_headings(akn_parent)
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

