"""
Python module to parse Irish Act XML into LegalDocML.

This module contains helpers to assemble LegalDocML subdivisions (sections,
subsections, paragraphs etc.) from intermediate Provision-like structures
returned from parse_section().
"""
import io
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from lxml import etree
from lxml.builder import E

from actsetl.parsers.eisb_provisions import parse_section, parse_schedule

log = logging.getLogger(__name__)

RESOURCES_PATH = Path(__file__).parent.parent / 'resources'
XSLT_PATH = RESOURCES_PATH / 'xslt' / 'eisb_transform.xslt'

# Canonical ordering of structural tags (higher-level first)
LEVELS = (
    "part", "chapter", "section", "subsection", 
    "paragraph", "subparagraph", "clause", "subclause"
    )

# Inline content/container tags that should be appended into a parent's content
INLINE_CONTAINER_TAGS = {"mod_block", "tblock", "table"}

# Top-level structural tags for recursive body parsing
TOPLEVEL_TAGS = ("part", "chapter", "division")


def transform_xml(eisb_xml: str) -> str:
    """
    Convert eISB XML encoding of special characters to plain UTF-8 XML via XSLT.
    """
    with open(XSLT_PATH, encoding="utf-8") as f:
        leg_dtd_xslt = f.read()
    xml_doc = etree.fromstring(eisb_xml)
    xslt_doc = etree.parse(io.StringIO(leg_dtd_xslt))
    transform = etree.XSLT(xslt_doc)
    clean_xml = transform(xml_doc)
    return etree.tostring(clean_xml, pretty_print=True).decode("utf-8")


def _get_level(tag: str) -> int:
    """Return index for tag in LEVELS; unknown tags are treated as deepest level."""
    try:
        return LEVELS.index(tag)
    except ValueError:
        return len(LEVELS)


def _ensure_content(parent: etree._Element) -> etree._Element:
    """Return the <content> child of parent, creating it if absent."""
    content = parent.find("content")
    if content is None:
        content = E.content()
        parent.append(content)
    return content


def _generate_child_eid(parent_eid: Optional[str], child_eid: Optional[str]) -> Optional[str]:
    """Generate concatenated eId for child when both parts are present."""
    if not child_eid:
        return None
    if parent_eid:
        return f"{parent_eid}_{child_eid}"
    # Fallback: if parent missing, return the child id as-is but log warning
    log.debug("Parent missing eId; using child eId '%s' without parent prefix", child_eid)
    return child_eid


def _append_subdiv(parent_container: etree._Element, subdiv) -> etree._Element:
    """
    Append subdiv.xml to parent_container, set eId if possible, and normalize
    the adjacent content/intro node if present.
    subdiv is expected to have attributes 'xml' (etree element) and 'eid' (str | None).
    """
    if parent_container is None:
        raise ValueError(f"Cannot determine parent for subdivision: {etree.tostring(subdiv.xml)}")

    parent_eid = parent_container.attrib.get("eId")
    new_eid = _generate_child_eid(parent_eid, getattr(subdiv, "eid", None))
    if new_eid:
        subdiv.xml.attrib["eId"] = new_eid
    parent_container.append(subdiv.xml)

    prev = subdiv.xml.getprevious()
    if prev is not None and prev.tag == "content":
        # If a content node precedes the appended node, convert it to intro
        prev.tag = "intro"
    return subdiv.xml


def section_hierarchy(subdivs: List[object]) -> Optional[etree._Element]:
    """
    Arrange a list of subdiv objects into a proper nested section hierarchy.

    The first element in subdivs is treated as the section root. Each subsequent
    subdiv is appended to the nearest ancestor whose LEVELS index is strictly
    less than the subdiv's level. Inline/container tags (mod_block, tblock,
    table) are appended into the nearest ancestor's <content>.
    """
    if not subdivs:
        return None

    root = subdivs[0].xml
    # Stack of (level_index, element) representing current path from root -> leaf
    stack: List[Tuple[int, etree._Element]] = [(_get_level(root.tag), root)]

    for subdiv in subdivs[1:]:
        tag = getattr(subdiv, "tag", None) or subdiv.xml.tag
        if tag in INLINE_CONTAINER_TAGS:
            # Attach inline containers into the current leaf's content
            parent = stack[-1][1]
            _ensure_content(parent).append(subdiv.xml)
            continue

        lvl = _get_level(tag)
        # Pop until we find a parent with a lower (higher-level) index
        while stack and stack[-1][0] >= lvl:
            stack.pop()
        container = stack[-1][1] if stack else root
        appended = _append_subdiv(container, subdiv)
        # New current node becomes the appended subdiv
        stack.append((lvl, appended))

    return root


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
                if not list(ctr):
                    subdiv.remove(ctr)
    return act


def parse_body(eisb_parent: etree._Element, akn_parent: etree._Element) -> Tuple[etree._Element, List]:
    """
    Build out the LegalDocML skeleton with content from eISB XML.

    Returns a tuple of (akn_parent, all_mod_info) where all_mod_info is a list
    of amendment metadata collected from sections.
    """
    all_mod_info = []
    for eisb_subdiv in list(eisb_parent):
        if eisb_subdiv.tag == "sect":
            akn_section_subdivs, mod_info = parse_section(eisb_subdiv)
            all_mod_info.extend(mod_info)
            akn_section = section_hierarchy(akn_section_subdivs)
            if akn_section is not None:
                akn_parent.append(akn_section)

        elif eisb_subdiv.tag in TOPLEVEL_TAGS:
            # parse_toplevel_elem may be defined elsewhere; call it if present
            try:
                akn_toplevel_elem = parse_toplevel_elem(eisb_subdiv) # type: ignore:name
            except NameError:
                log.debug("parse_toplevel_elem not available; skipping toplevel element %s", eisb_subdiv.tag)
                continue

            akn_parent.append(akn_toplevel_elem)
            # Robustly generate combined eId if possible
            parent_eid = akn_toplevel_elem.getparent().attrib.get("eId") if akn_toplevel_elem.getparent() is not None else None
            elem_eid = akn_toplevel_elem.attrib.get("eId")
            if elem_eid:
                combined = _generate_child_eid(parent_eid, elem_eid)
                if combined:
                    akn_toplevel_elem.attrib["eId"] = combined

            _, mod_info = parse_body(eisb_subdiv, akn_toplevel_elem)
            all_mod_info.extend(mod_info)
        else:
            log.debug("Skipping unrecognized tag %s under %s", eisb_subdiv.tag, eisb_parent.tag)

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