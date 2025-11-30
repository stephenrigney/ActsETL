"""
Python module to parse Irish Act XML into LegalDocML.

"""
import logging
import re
import io
from collections import namedtuple
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

def transform_xml(infn: str) -> str:
    '''
    Act XML published on eISB encodes certain special characters, including fadas and euro symbols, as XML nodes defined by the legislation.dtd schema. 
    These are converted to regular characters via an XSLT (eisb_transform.xslt) and the XML is then reserialised as utf-8
    
    :param infn: input filename
    :type infn: str
    :return: eISB XML in utf-8 format
    :rtype: str
    '''
    with open(XSLT_PATH, encoding="utf-8") as f:
        leg_dtd_xslt = f.read()
    xml_doc = etree.parse(infn)
    xslt_doc = etree.parse(io.StringIO(leg_dtd_xslt))
    transform = etree.XSLT(xslt_doc)
    clean_xml = transform(xml_doc)
    return etree.tostring(clean_xml, pretty_print=True).decode("utf-8")

def parse_ojref(ojref:str) -> str:
    """
    Parses a footnote reference to the Official Journal of the EU (OJ[EU]) into Eurlex URI.
    
    :param ojref: Description
    :type ojref: str    
    :return: Description
    :rtype: str
    """
    
    ojref = ojref.replace(".", "").replace(" ", "")
    ojre = re.search(
        "OJ(No)?(?P<series>[CL])(?P<number>\d+),\d+(?P<year>\d{4}),?p(?P<page>\d+)", 
        ojref
        )
    if not ojre:

        return ""
    sr = ojre.group("series")
    yr = ojre.group("year")
    num = int(ojre.group("number"))
    pg = int(ojre.group("page"))
    ojuri = f"uriserv:OJ.{sr}_.{yr}.{num:03}.01.{pg:04}.01.ENG"
    eurlex_uri = f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri={ojuri}"
    return eurlex_uri


def parse_p(p: etree) -> etree:
    """
    Converts eISB text content <p> into LegalDocML correct <p>.

    
    :param p: Description
    :type p: etree.eisb.p
    :return: Description
    :rtype: Any
    """
    p.tag = "p"
    etree.strip_tags(p, ['font', 'xref'])
    if p.attrib.get("class"):
        loc = p.attrib.pop("class").split(" ")
        if len(loc) == 6:
            tindent = int(loc[0])/2 if loc[0] != "0" else 0
            margin =  int(loc[1])/2 if loc[1] != "0" else 0
            p.attrib['style'] = f"text-indent:{tindent};margin-left:{margin};text-align:{loc[3]}"
    for child in p.iter():
        if child.tag == "fn":
            ref_text = child.find("./marker/su").text
            ref_target = child.find("./p//su").tail.strip()
            href = ""
            if ref_target.startswith("OJ"):
                href = parse_ojref(ref_target)
            idx = p.index(child)
            ref = E.sup(
                E.ref(
                ref_text, title=ref_target, href=href
                )
            )
            p.insert(idx, ref)
        # eISB XML inserts images for complex content, eg, math formulae
        elif child.tag == "graphic":
            child.tag = "img"
            # Base URL is currently https://www.irishstatutebook.ie
            child.attrib['src'] = f"/images/{child.attrib.pop('href')}"
            
            child.attrib.pop("quality")
        elif child.tag == "sb":
            child.tag = "sub"
        elif child.tag == "su":
            child.tag = "sup"
        elif child.tag == "unicode":
            p.text += chr(int("0x" + child.attrib["ch"], 16)) + child.tail

    keys = p.attrib.keys()
    for key in keys:
        if key not in ["style"]:
            p.attrib.pop(key)
    etree.strip_elements(p, ["fn", "unicode"], with_tail=False)
    return p

def make_container(tag: str, num:E.b=None, heading:str=None, attribs:dict=None) -> E:
    """
    Generate a LegalDocML element with <tag> name and optional num/heading elements
    
    :param tag: Description
    :type tag: str
    :param num: Description
    :type num: E.b
    :param heading: Description
    :type heading: str
    :param attribs: Description
    :type attribs: dict
    """
    if not attribs:
        attribs = {}
    container = E(tag, attribs)
    if heading is not None:
        container.append(heading)
    if num is not None:
        container.append(E.num(num))

    return container

def make_eid_snippet(label: str, num:str):
    """
    Generate partial eId.
    
    :param label: Description
    :type label: str
    :param num: Description
    :type num: str
    """
    return f"{label}_{''.join(d for d in num if d.isalnum())}"

def parse_table(table: etree):
    """
    Convert eISB table element (and children) into correct LegalDocML XML structure.
    
    :param table: Description
    :type table: etree.eisb.table
    :param alignment: Description
    :type alignment: Str
    """
    etree.strip_tags(table, "tbody")
    etree.cleanup_namespaces(table)
    style = ""
    if table.attrib.get("class"):
        loc = table.attrib.pop("class").split(" ")
        if len(loc) == 6:
            tindent = int(loc[0])/2 if loc[0] != "0" else 0
            margin =  int(loc[1])/2 if loc[1] != "0" else 0
            style = f"text-indent:{tindent};margin-left:{margin};text-align:{loc[3]}"    

    colgroup = table.find("colgroup")
    colwidths = [w.strip("%") for w in colgroup.xpath("./col/@width")]
    style += ";colwidths:" ",".join(colwidths)
    table.attrib['style'] = style
    table.attrib["width"] =  table.attrib['width'].strip("%")
    table.remove(colgroup)
    for row_idx, tr in enumerate(table.xpath("./tr")):
        for col_idx, td in enumerate(tr.xpath("./td")):
            valign = td.attrib.pop("valign")
            if row_idx == 0:
                td.tag = "th"
                td.attrib['style'] = f"width:{colwidths[col_idx]};vertical-align:{valign}"
            else:
                td.attrib['style'] = f"vertical-align:{valign}"  
            for p in td.xpath("./p"):
                p = parse_p(p)
    keys = table.attrib.keys()
    for key in keys:
        if key not in ["style", "width"]:
            table.attrib.pop(key)
    return table

def contains(string, s: set[str]):
    """ Check whether sequence str contains ANY of the items in set. """
    return any([c in string for c in s])

def parse_section(sect: etree) -> list:
    """
    Generate LegalDocML section container from eISB section content.
    Parse <p> and <table> elements into correct LegalDocML element type.
    Location in hierarchy is identified via a combination of provision number and the hanging/indentation
    of the <p>, as contained in the class attribute in the node.

    Text may have nested provisions, eg "1. (1) (a) This section..." 
    so paragraphs are checked for 
    section->subsection->paragraph->subparagraph->clause->subclause.

    When a provision number is found, it's stripped out of the text and added to the subdivs list 
    (section_hierarchy will put them in hierarchical order)
    
    :param sect: Description
    :type sect: etree.root.subdiv
    :return: Description
    :rtype: list
    """
    Provision = namedtuple("Provision", "tag eid ins hang margin align xml text")
    snumber = sect.find("number").text.strip()
    sheading = parse_p(sect.find("./title/p"))
    sheading.tag = "heading"
    subdivs = []
    provs = sect.xpath("./p|./table")
    ptype = "section"
    inserted = False
    # Flag to avoid misclassifying paragraph numbers i, v, x as subparagraphs by checking preceding letter.
    # If preceding letter is h, u or w classify i, v or x as paragraph.
    # ToDo: will be wrong if a subparagraph is nested within a paragraph numbered h, u or w.
    is_huw = False    
    log.info("Parsing section %s", snumber)
    eid = make_eid_snippet("sect", snumber)
    sect = make_container(ptype, num=E.b(snumber), heading=sheading, attribs={"eId": eid})
    subdivs.append(
        Provision(
        tag="section", eid=eid, 
        ins=inserted, 
        hang=-3, margin=11, align="left", xml=sect, text=None
        ))
    for i, p in enumerate(provs):
        text_loc = p.get("class").split(" ")
        if len(text_loc) == 6:
            hanging, margin = [int(i) for i in text_loc[:2]]
            alignment = text_loc[3]
        else:
            hanging = 0
            text = 0
            margin = 0
            alignment = "left"
        text = "".join(p.xpath(".//text()")).strip()

        if p.tag == "table":
            p = parse_table(p)
            subdivs.append(
                Provision(
                tag="table", eid=None, ins=inserted, 
                hang=hanging, margin=margin, align=alignment, xml=p, text=text
                ))
            continue
        if len(text) == 0:
            # Text block is a non-numbered content paragraph, eg. definition block.
            p = parse_p(p)
            subdivs.append(
                Provision(
                tag="tblock", eid=None, ins=inserted, 
                hang=hanging, margin=margin, align=alignment, xml=p, text=None
                ))
            continue
        # Flag for inserted text
        if (text.startswith(ODQ) and (CDQ) not in text[:-2] and ODQ not in text[1:]) or text == ODQ:
            inserted = True

            subdivs.append(
                Provision(
                tag="quotestart", eid=None, ins=inserted,
                hang=hanging, margin=margin, align=alignment,
                xml=make_container("quotedStructure", attribs={"startQuote": "“"}), text=None
                )
                )

        b = p.find("./b")
        # Section numbers are Arabic numerals in bold with possible capital case letters appended.
        if b is not None and b.tail is not None:
            etree.strip_elements(p, 'b', with_tail=False)
            if hanging + margin > 8:
                ptype = "section"
                inserted = True
                pnumber = b.text.strip()
                eid = make_eid_snippet("sect", pnumber)
                subdivs.append(
                    Provision(
                    tag=ptype, eid=eid, 
                    ins=inserted, hang=hanging, 
                    margin=margin, align=alignment, xml=make_container(ptype, b, attribs={"eId":eid}), text=None
                    ))
        # Subsections are Arabic numerals in parenthesis with possible capital case letters: (1), (2), (1A), (1AB) .
        subsect_re = re.match("^\s?(“?\(\d+[A-Z]*\))", p.text or "")
        if subsect_re:
            inserted = False
            if hanging + margin > 8 or (ptype in ["section", "subsection"] and inserted is True):
                inserted = True
            ptype = "subsection"
            pnumber = subsect_re.group(1)
            eid = make_eid_snippet("subsect", pnumber)
            p.text = p.text[subsect_re.end():].lstrip()
            subdivs.append(
                Provision(
                tag=ptype, 
                eid=eid, 
                ins=inserted, hang=hanging, margin=margin, align=alignment, 
                xml=make_container(ptype, pnumber, attribs={"eId": eid}), text=None
                ))
        # Before ca. 2010, section and subsection numbers are italicised, eg, "<p>(<i>a</i>)...</p>". 
        # Making editorial decision to remove italicisation for consistency and ease of parsing.
        ital = p.find("i")
        if p.text == "(" and ital is not None and ital.tail.startswith(")"):
            p.text += ital.text + ital.tail
            p.remove(ital)

        # Paragraphs are lower case letters in parenthesis - (a), (b), (aab)
        para_re = re.match("^\s?(“?\([a-z]+\))", p.text or "")
        #ToDo older Acts use itals
        if para_re:
            inserted = False
            pnumber = para_re.group(1)
            eid_number = "".join(d for d in pnumber if d.isalnum())
            if margin == 14:
                ptype = "paragraph"
            # subparagraphs are 
            elif eid_number[0] in "ivx" and margin == 17:
                ptype = "subparagraph"              
            elif eid_number[0] in "ivx" and not is_huw:

                # Subparagraphs are lower case roman numerals (i, ii..v..x) 
                # but paragraphs can sometimes use (i) (and encountered paragraphs v and x in s. 96 of Finance Act 2012, although these are effectivly table rows). 
                ptype = "subparagraph"
                inserted = True
            else:
                ptype = "paragraph"
                inserted = True
            p.text = p.text[para_re.end():].lstrip()
            eid = make_eid_snippet("para", pnumber)       
            if ptype == "subparagraph":
                eid = make_eid_snippet("subpara", pnumber)

            
            subdivs.append(
                Provision(
                tag=ptype, 
                eid=eid, 
                ins=inserted, hang=hanging, margin=margin, align=alignment,
                xml=make_container(ptype, pnumber, attribs={"eId": eid}), text=None
                ))
            is_huw = pnumber in "huw"
        # This is done twice to catch paragraph->subparagraph provisions
        subpara_re = re.match("^\s?(“?\([a-z]+\))", p.text or "")
        if subpara_re:
            inserted = False
            ptype = "subparagraph"
            pnumber = para_re.group(1)
            if margin > 17:
                inserted = True
            p.text = p.text[subpara_re.end():].lstrip()
            eid = make_eid_snippet("subpara", pnumber)
            subdivs.append(
                Provision(
                tag=ptype,
                eid=eid,
                ins=inserted, hang=hanging, margin=margin, align=alignment, xml=make_container(ptype, pnumber, attribs={"eId": eid}), text=None
                ))
        # Clause is upper Roman numberal - (I), (V), (X), (II)
        clause_re = re.match(r"^\s?(“?\([IVX]+\))", p.text or "")
        if clause_re:
            inserted = False
            ptype = "clause"
            pnumber = clause_re.group(1)
            if margin > 20:
                inserted = True
            p.text = p.text[clause_re.end():].lstrip()
            eid = make_eid_snippet("clause", pnumber)
            subdivs.append(
                Provision(
                tag=ptype,
                eid=eid,
                ins=inserted, hang=hanging, margin=margin, align=alignment, xml=make_container(ptype, pnumber, attribs={"eId": eid}), text=None
                ))
        # Subclause is upper case alphabet - (A), (B), (AB)
        subclause_re = re.match(r"^\s?(“?\([A-Z]+\))", p.text or "")
        if subclause_re:
            inserted = False
            ptype = "subclause"
            pnumber = subclause_re.group(1)
            if margin > 23:
                inserted = True
            p.text = p.text[subclause_re.end():].lstrip()
            eid = make_eid_snippet("subclause", pnumber)
            subdivs.append(
                Provision(tag=ptype, eid=eid, 
                ins=inserted, hang=hanging, margin=margin, align=alignment,
                xml=make_container(ptype, pnumber, attribs={"eId": eid}),
                text=None
                ))
        # Article is an element of a schedule (see S.23 of Finance Act 2022)
        #ToDo: not completely accurate as a descriptor - may be better to use hcontainer
        article_re = re.match(r"^\s?(“?\d+\.)", p.text or "")
        if article_re:
            ptype = "article"
            pnumber = article_re.group(1)
            # inserted uses pre-existing status - list will follow a header or at least the first number will have opening quotes.
            subdivs.append(
                Provision(
                tag=ptype,
                eid=make_eid_snippet("article", pnumber), 
                ins=inserted, hang=hanging, margin=margin, align=alignment, xml=make_container(ptype, pnumber, attribs={"eId": eid}), text=None
                ))
        is_header_for_table = False
        if p.tag == 'p' and (i + 1) < len(provs) and provs[i+1].tag == 'table':
            is_header_for_table = True

        #ToDo - better identification of real parts over schedule parts
        if alignment == "center" and ("PART" in text or "Part" in text or "Chapter" in text or "SCHEDULE" in text) and not is_header_for_table:
            if "part" in text.lower():
                inserted = True
                ptype = "part"
                pnumber = text.strip()
                eid = make_eid_snippet("part", pnumber.lower().replace("part", "").upper())
                pxml = make_container(ptype, pnumber, attribs={"eId": eid})
            elif "Chapter" in text:
                inserted = True
                ptype = "chapter"
                pnumber = text.strip()
                eid = make_eid_snippet("chapter", pnumber.replace("Chapter", ""))
                pxml = make_container(ptype, pnumber, attribs={"eId": eid})
            elif "SCHEDULE" in text:
                inserted = True
                ptype = "schedule"
                pnumber = text.strip()
                eid = make_eid_snippet("schedule", pnumber.replace("SCHEDULE", ""))
                pxml = make_container("hcontainer", pnumber, attribs={"eId": eid, "name": ptype})
            subdivs.append(
                Provision(
                tag=ptype, eid=eid, 
                ins=inserted, hang=hanging, margin=margin, align=alignment, 
                xml=pxml,
                text="".join(pxml.xpath(".//text()"))
                ))
            continue
        
        # Now that subdivision type has been identified, the text content can be parsed
        parse_p(p)

        # Identify definition blocks.
        defining_words = ["means", "mean", "meaning", "construed", "referred to"]
        if (
            (ODQ in text and CDQ in text and contains(text, set(defining_words))
             ) or (
            OSQ in text and CSQ in text and contains(text, set(defining_words)))):
            pass
        ptype = "tblock"
        subdivs.append(
            Provision(
            tag=ptype, eid=None, 
            ins=inserted, hang=hanging, margin=margin, align=alignment, xml=p, text="".join(p.xpath(".//text()"))
            ))
        # End quote for inserted text       
        if len(text) > 1 and text[-2] == "”":
            inserted = True
            subdivs.append(
                Provision(
                tag="quoteend", eid=None, ins=inserted, 
                hang=hanging, margin=margin, align=alignment,
                xml=None, text=text[-2:]
                ))
    return subdivs

def locate_tag(parent, tags:list):
    """
    Finds location in hierarchy of element's parent.
    
    :param parent: Description
    :param tags: Description
    :type tags: list
    """
    logging.debug("Finding parent of element from %s, with tags %s", parent, tags)
    if parent.tag in tags:
        # logging.debug("Parent is %s", parent.tag)
        return parent
    
    curr = parent.getparent()
    while curr is not None:
        if curr.tag in tags:
            return curr
        curr = curr.getparent()

    logging.debug("Ancestors are %s", list(parent.iterancestors()))
    for ancestor in parent.iterancestors(tags):
        logging.debug("Ancestor iter is %s", ancestor.tag)
        if ancestor.tag in tags:
            logging.debug("Ancestor parent is %s", ancestor.tag)
            return ancestor
    return None

def append_subdiv(parent_container: etree, modparent: etree, subdiv: namedtuple, mod: bool) -> etree:
    """
    Appends a subdivision to its correct parent in the XML tree.

    This function handles creating hierarchical eIds, appending to either a
    standard container or a modification block, and adjusting sibling tags.

    :param container: The standard hierarchical parent element.
    :param modparent: The parent for modified/inserted content.
    :param subdiv: The Provision object for the subdivision to append.
    :param mod: A flag indicating if currently inside a modification.
    """
    pre_target = None
    if parent_container is not None:
        subdiv.xml.attrib['eId'] = f"{parent_container.attrib.get('eId')}_{subdiv.xml.attrib.get('eId')}"
        # logging.debug("Appending %s to %s", subdiv.xml.attrib.get('eId'), parent_container.attrib.get('eId'))
        parent_container.append(subdiv.xml)
        pre_target = parent_container
    elif mod:
        modparent.append(subdiv.xml)
        pre_target = modparent
    else:
        raise ValueError(
            f"Cannot determine parent for subdivision: {subdiv.xml.attrib.get('eId')}"
            )
    
    parent = subdiv.xml
    pre = parent.getprevious()
    if pre is not None and pre.tag == "content":
        pre.tag = "intro"
    return pre_target

def section_hierarchy(subdivs: list) -> E.section:
    """
    Arranges list of subdiv elements into section hierarchy based on subdiv tags.
    
    :param subdivs: Description
    :type subdivs: list
    :return: Description
    :rtype: Any
    """
    sectionparent = parent = subdivs[0].xml

    mod = False
    modparent = None
    outerparent = None
    i = 1
    while i < len(subdivs):
        subdiv = subdivs[i]
        next_subdiv = subdivs[i + 1] if (i + 1) < len(subdivs) else None
        is_table_header = (
            subdiv.tag == 'tblock' and
            subdiv.xml.tag == 'p' and
            'text-align:center' in subdiv.xml.attrib.get('style', '') and
            next_subdiv and
            next_subdiv.tag == 'table'
        )


        if (
            subdivs[0].eid == "sect_76" and 
            subdiv.eid == "para_c" and
            etree.tostring(subdiv.xml) == b'<paragraph eId="para_c"><num>(c)</num></paragraph>'):
            logging.info(
                "Parent eId: %s, previous eId: %s,current eId: %s", 
                parent.attrib.get("eId"),
                subdivs[i-1].eid,
                subdiv.eid,
            )
            parsing_errors_writer(sectionparent)

        if subdiv.tag == "quotestart":
            mod = True
            outerparent = parent

            logging.debug("Quotestart outerparent: %s", outerparent)
            modparent = parent = subdiv.xml
            logging.debug("Quote end modparent: %s", modparent)
        elif subdiv.tag == "quoteend":
            try:
                modparent.attrib['endQuote'] = subdiv.text

                modblock = E.block(
                    E.mod(
                    modparent
                    ),
                    {"name": "quotedStructure"}
                )
                parent = outerparent
                logging.debug("Quoteend parent: %s", parent)
                content = parent.find("content")
                if content is None:
                    content = E.content()
                    parent.append(content)
                content.append(modblock)
                modparent = None
                mod = False
            except AttributeError:
                # this is caused by a typo in section 46(2) of FA2022, which incorrectly ends with '”.'
                log.exception(
                    "Failed to process quoteend for parent eId '%s'. This may be due to a source typo.", parent.attrib.get("eId")
                )

        elif mod:
            if subdiv.xml is not None:
                modparent.append(subdiv.xml)

        elif subdiv.tag in ["tblock", "table"]:
            content = parent.find("content")
            if parent.attrib.get("eId") and content is None:
                if parent.tag in ["part", "chapter", "schedule", "division"]:
                    pass
                    
                parent.append(E.content(subdiv.xml))
            elif content is not None:
                content.append(subdiv.xml)
            else:
                parent.append(subdiv.xml)

        elif subdiv.tag == "schedule":
            modparent.append(subdiv.xml)
            parent = subdiv.xml

        elif subdiv.tag == "part":
            modparent.append(subdiv.xml)
            parent = subdiv.xml

        elif subdiv.tag == "chapter":
            tags = ["part"]
            container = locate_tag(parent, tags)
            parent = append_subdiv(container, modparent, subdiv, mod)

        elif subdiv.tag == "section":

            tags = ["chapter", "part"]
            container = locate_tag(parent, tags)
            pre_p = subdivs[i-1].xml
            if pre_p.tag == "p" and pre_p.find("b") is not None:
                
                pre_p.tag = "heading"
                subdiv.xml.insert(1, pre_p)
            parent = append_subdiv(container, modparent, subdiv, mod)
        
        elif subdiv.tag == "subsection":
            tags = ["section"]
            container = locate_tag(parent, tags)
            parent = append_subdiv(container, modparent, subdiv, mod)
      
        elif subdiv.tag == "paragraph":

            tags = ["section", "subsection"]
            container = locate_tag(parent, tags)


            parent = append_subdiv(container, modparent, subdiv, mod)
            
        elif subdiv.tag == "subparagraph":
            tags = ["section", "subsection", "paragraph"]
            container = locate_tag(parent, tags)

            parent = append_subdiv(container, modparent, subdiv, mod)

            if parent is None:
                parsing_errors_writer(parent.getroot())
                raise ValueError(f"{subdiv.eid} parent not found")

        elif subdiv.tag == "clause":
            tags =  ["section", "subsection", "paragraph", "subparagraph"]
            container = locate_tag(parent, tags)
            parent = append_subdiv(container, modparent, subdiv, mod)

        elif subdiv.tag == "subclause":
            tags =  ["section", "subsection", "paragraph", "subparagraph", "clause"]
            container = locate_tag(parent, tags)
            parent = append_subdiv(container, modparent, subdiv, mod)

        elif subdiv.tag == "article":
            tags =  ["section", "subsection", "paragraph", "subparagraph", "clause", "subclause"]
            container = locate_tag(parent, tags)
            parent = append_subdiv(container, modparent, subdiv, mod)

        i+=1

    for idx, mod in enumerate(sectionparent.xpath(".//mod")):
        parent_eid = sectionparent.attrib['eId']
        mod_eid = f"{parent_eid}_mod_{idx+1}"
        mod.attrib['eId'] = mod_eid
        for idx2, el in enumerate(mod.xpath(".//*[@eId]")):
            
            el.attrib['eId'] = f"{mod_eid}_{el.attrib['eId']}"
    return sectionparent

def parse_body(eisb_parent: etree, akn_parent: E, toc: E) -> tuple:
    """
    Build out the LegalDocML skeleton (pxml) with content from eISB XML (parent).

    As eISB XML is hierarchical only as deep as section level, 
    lower level nodes (subsection, paragraph, subparagraph, clause, subclause)
    as well as inserted text have to be parsed from a flat <p> to the appropriate hierarchy in
    the LegalDocML schema.

    In Irish convention, tables of contents only include Parts, Chapters, sections and Schedules.

    #ToDo: decide whether ToCs need to be in XML at all.
    
    :param parent: eISB XML
    :type parent: etree.root.body
    :param pxml: LegalDocML XML
    :type pxml: E.act.body
    :param toc: Table of contents element from LegalDocML XML object.
    :type toc: E.act.body.toc
    :return: Description
    :rtype: tuple
    """
    for i, subdiv in enumerate(eisb_parent.getchildren()):

        if subdiv.tag == "sect":
            subdivs = parse_section(subdiv)
            sxml = section_hierarchy(subdivs)

            akn_parent.append(
                sxml
            )
            level = 1
            if eisb_parent.tag == "part":
                level += 1
            if eisb_parent.tag == "chapter":
                level += 2

            toc.append(
                E.tocItem(
                {"level": str(level), "class": sxml.tag, "href": f"#{sxml.attrib['eId']}"},
                E.inline({"name": "tocNum"}, sxml.find("./num/b").text),
                E.inline({"name": "tocHeading"}, "".join(sxml.xpath("./heading//text()")))
                )
            )
        tags = ["part", "chapter", "division"]
        if subdiv.tag in tags:

            title = subdiv.find("title").getchildren()
            number = "".join(title[0].xpath(".//text()"))
            sdheading = parse_p(title[1])
            sdheading.tag = "heading"
            eid = make_eid_snippet(subdiv.tag, number.split(" ")[-1])
            subdivxml = E(
                subdiv.tag, E.num(number), sdheading, {"eId": eid}
                )
            akn_parent.append(subdivxml)
            if subdivxml.tag in tags[1:]:
                subdivxml.attrib['eId'] = f"{subdivxml.getparent().attrib['eId']}_{subdivxml.attrib['eId']}"
            if subdiv.tag == "part":
                level = "1"
            elif subdiv.tag == "chapter":
                level = "2"
            else:
                level = "3"
            
            toc.append(
                E.tocItem(
                {"level": level, "class": subdiv.tag, "href": f"#{eid}"},
                E.inline({"name": "tocNum"}, number),
                E.inline({"name": "tocHeading"}, "".join(sdheading.xpath("./heading//text()")))
                )
            )
            
            divs = parse_body(subdiv, subdivxml, toc)
    return akn_parent, toc

def act_metadata(act: etree) -> namedtuple: 
    """
    Parses Act metadata from eISB Act XML and returns as a named tuple
    
    :param act: etree.root of eISB Act
    :type act: lxml.etree.root
    :return: Named tuple "ActMeta" with fields: number, year, date_enacted, status, short_title, long_title
    :rtype: namedtuple
    """
    
    ActMeta = namedtuple("ActMeta", "number year date_enacted status short_title long_title")
    metadata = act.find("metadata")
    short_title = metadata.find("title").text
    log.info("Parsing metadata for: %s", short_title)
    number = metadata.find("number").text
    year = metadata.find("year").text
    doe = metadata.find("dateofenactment").text
    date_enacted = dtparse(doe).date()
    long_title = parse_p(act.xpath(
        "./frontmatter/p[(contains(text(), 'AN ACT TO')) or (contains(text(), 'An Act to'))]"
        )[0])
    # long_title = parse_p(act.find("./frontmatter/p[@class='0 8 0 left 1 0']"))

    return ActMeta(
        number=number, year=year, date_enacted=date_enacted, 
        status="enacted", short_title=short_title, long_title=long_title
        )

def parse_schedule(root, act):
    """
    Schedules may contain a wide range of content types. 
    The parse loop simply recreates the eISB hierarchy of flat paragraphs and tables below Schedule level with LegalDocML elements.
    This is a simpler alternative to trying to contend with specific Schedules but it means that it doesn't recognise useful semantics in some Schedules, eg where they contain amendments.
    
    :param root: Description
    :param act: Description
    """
    body = act.find("./body")
    toc = act.find("./coverPage/toc")
    schedules = root.xpath("./backmatter/schedule")
    for idx, sch in enumerate(schedules):
        number = "".join(sch.xpath("./title/p[1]//text()")[0])
        eid_num = number.replace("SCHEDULE", "").strip()
        heading = "".join(sch.xpath("./title/p[2]//text()"))
        
        eid = f"sched_{idx+1}"
        schedule = E.hcontainer(
            {"name": "schedule", "eId": eid},
            E.num(number),
            E.heading(heading),
            E.content()
        )
        body.append(schedule)
        toc.append(
            E.tocItem(
            {"level": "1", "class": "schedule", "href": f"#{eid}"},
            E.inline({"name": "tocNum"}, number),
            E.inline({"name": "tocHeading"}, heading)
            )
        )
        for p in sch.xpath("./p|./table"):
            if p.tag == "p":
                schedule.find("content").append(parse_p(p))
            else:
                schedule.find("content").append(parse_table(p))
    return body

def fix_headings(act):
    """
    Identify and correctly tag headings in inserted text.
    
    :param act: Description
    """
    inserted_sds = act.xpath(
        "./body//quotedStructure/*[(local-name()='part') or (local-name()='chapter') or (local-name()='hcontainer' and @name='schedule')][./num]")
    for sd in inserted_sds:
        num = sd.find("num")
        if num is not None and num.getnext().tag in ["content", "intro"]:
            ctr = num.getnext()
            p = num.getnext().find("p")
            if p.attrib['style'] == 'text-indent:0;margin-left:0;text-align:center':

                idx = sd.index(ctr)
                p.tag = "heading"
                sd.insert(idx, p)
                if len(ctr.getchildren()) == 0:
                    sd.remove(ctr)
    # inserted_sects = act.xpath("./body//quotedStructure//section")
