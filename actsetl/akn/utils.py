"""
Python module to generate Akoma Ntoso/LegalDocML XML from eISB XML.

"""
import logging
from collections import namedtuple
from pathlib import Path

from lxml import etree
from lxml.builder import ElementMaker, E

log = logging.getLogger(__name__)


AKN_SCHEMA_LOCATION = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0 http://docs.oasis-open.org/legaldocml/akn-core/v1.0/cos01/part2-specs/schemas/akomantoso30.xsd"
AKN_SCHEMA_URL = "http://docs.oasis-open.org/legaldocml/akn-core/v1.0/cos01/part2-specs/schemas/akomantoso30.xsd"
AKN_NS = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"

RESOURCES_PATH = Path(__file__).parent.parent / 'resources'

def eli_uri_fragment(meta: etree, lang:str="en") -> namedtuple:
    """
    Composes FRBR URI snippets from eISB act metadata and returns as named tuple

    Note - URIs do not include domain deliberately, pending decision over domain name (https://data.oireachtas.ie or https://www.electronicstatutebook.ie)
    
    :param meta: Description
    :type meta: etree
    :param lang: Description
    :type lang: str

    :return: Named tuple (FRBR) with fields work, exp, mani
    :rtype: namedtuple
    """
    FRBR = namedtuple("FRBR", "work exp mani")
    year = meta.year
    num = meta.number
    work_uri =  f"/eli/ie/oireachtas/{year}/act/{num}"
    exp_uri = f"{work_uri}/{meta.status}/{lang}"
    mani_uri = f"{exp_uri}/akn"
    return FRBR(work=work_uri, exp=exp_uri, mani=mani_uri)

def akn_root(act: etree) -> etree:
    """
    Generate base LegalDocML element.
    
    :param act: Description
    :type act: etree
    
    """

    attr_qname = etree.QName('http://www.w3.org/2001/XMLSchema-instance', "schemaLocation")
    akn_e = ElementMaker(
        namespace=AKN_NS, nsmap={None: AKN_NS, 'xsi': 'http://www.w3.org/2001/XMLSchema-instance'})
    akn = akn_e.akomaNtoso(
            {attr_qname: AKN_SCHEMA_LOCATION},
            act)
    return akn

def akn_notes(akn, notesdict):
    """
    Add editorial notes to LegalDocML file.
    
    :param akn: Description
    :param notesdict: Description
    """
    this = akn.xpath("./act/meta/identification/FRBRWork/FRBRthis/@value")[0]
    if notesdict is None:
        return akn
    act_notes = [n for n in notesdict if n['ActUri'] == this]
    if len(act_notes) > 0:
        notes = [n for nn in act_notes for n in nn['Notes']]
        akn_notes_elem = E.notes(source="#source")
        for note in notes:
            eid = f"note-{note['eId']}"
            akn_note = E.note(
                E.p(note['note']),
                {"class": note['class'], "eId": eid}
            )
            akn_notes_elem.append(akn_note)
            akn_noteref = E.noteRef(href=f"#{eid}", marker="*")
            loc = akn.xpath(f"./act/body//*[contains(@eId, '{note['eId']}')]/num")[0]
            loc.append(akn_noteref)
            akn_notes_elem.append(akn_note)
        akn.find("./act/meta").append(akn_notes_elem)
    return akn

def date_suffix(day: int) -> str:
    """
    Turns cardinal number into ordinal: 1->1st, 2->2nd, etc.
    
    :param day: Description
    :type day: int
    :return: Description
    :rtype: str
    """
    suffix = ""
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1]
    return f"{day}{suffix}"

def pop_styles(akn: etree):
    """
    Remove style attributes from elements.
    This is done for readability, but not required for XML validation.
    
    :param akn: Description
    :type akn: etree
    :return: Description
    :rtype: etree
    """ 
    log.info("Removing style attributes")
    for elem in akn.xpath("//*[@style]"):
        elem.attrib.pop("style")
    return akn


def write_xml(xml: str, outfn:str):
    """
    Write XML to file.
    
    :param xml: Description
    :type xml: str
    :param outfn: Description
    :type outfn: str
    """ 
    with open(outfn, "w", encoding="utf-8") as f:
        f.write(xml)

def akn_write(akn:etree, fn:str, validate:bool=True):
    """
    validates and serializes LegalDocML XML.
    
    :param akn: Description
    :type akn: etree
    :param fn: Description
    :type fn: str
    :param validate: Description
    :type validate: bool
    """
    schema_path = RESOURCES_PATH / 'schemas' / 'akomantoso30.xsd'
    xsd_doc = etree.parse(schema_path)
    xsd = etree.XMLSchema(xsd_doc)
    xml = etree.tostring(
        akn, pretty_print=True, 
        xml_declaration=True, encoding="utf-8"
        ).decode("utf-8")
    if validate:
        for child in akn.find("act").iter():
            child.tag = f"{{{AKN_NS}}}{child.tag}"
        try:
            xsd.assertValid(akn)
        except etree.DocumentInvalid as exc:
            logging.error("Invalid XML")
            for error in exc.error_log:
                
                logging.error(
                    f"  [Line {error.line}, Column {error.column}] Path: {error.path}, Message: {error.message}"
                    )
                logging.error(etree.tostring(akn.xpath(error.path)[0]))
                logging.error("*********")
    logging.info("Writing XML")

    write_xml(xml, fn)

def active_mods(akn: E) -> E:
    """
    Records ActiveMod metadata under meta/analysis.

    #ToDo: parse hrefs
    
    :param akn: Description
    :type akn: E
    :return: Description
    :rtype: Any
    """
    active_mods_list = akn.find("./act/meta/analysis/activeModifications")
    mods = akn.xpath("./act/body//mod")
    if len(mods) == 0:
        akn.find("./act/meta/analysis").remove(active_mods_list)
        return akn
    for mod in mods:
        tmod = E.textualMod(
            E.source(href=f"#{mod.attrib['eId']}"),
            E.destination(href="/"),
            type="substitution"
        )
        active_mods_list.append(tmod)
    return akn


class TextMatchWrapper:
    """
    Utility to wrap matched text strings in specified XML tag if string is in parent tex.
    
    """
    def __init__(self, parent: etree, tag:str, matches:list[str]):
        self.p = parent
        self.tag = tag
        self.matches = matches
        if self.matches is None:
            self.matches = []

    def iter_matches(self):
        """
        Iterate through parent text and wrap matched text in specified tag.
        """
        for match in self.matches:
            if self.p.text and match in self.p.text:
                self._wrap_text(self.p, match)
            else:
                self._iter_children(match)
    
    def _iter_children(self, match):
        for c in self.p.iter():
            if etree.QName(c).localname == self.tag:
                if c.text and match in c.text:
                    break

            if c.text and match in c.text:
                self._wrap_text(c, match, tail=False, child=True)
            if c.tail and match in c.tail:
                self._wrap_text(c, match, tail=True, child=True)
    
    def _wrap_text(self, elem, match, tail=False, child=False):
        text = elem.tail if tail else elem.text
        m = text.find(match)
        if tail:
            elem.tail = elem.tail[:m]
        else:
            elem.text = elem.text[:m]
        wrapper = E(self.tag, text[m:m+len(match)])
        wrapper.tail = text[m+len(match):]
        if child:
            elem.getparent().append(wrapper)
        else:
            elem.append(wrapper)