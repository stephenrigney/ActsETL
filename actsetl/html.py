"""
Python module to transform LegalDocML XML into HTML.

"""
import io
from pathlib import Path

from lxml import etree

RESOURCES_PATH = Path(__file__).parent / 'resources'

def transform_xml(xml_in: str, xslt_transform:str) -> str:
    """
    Transform LegalDocML XML into HTML.
    
    :param xml_in: input filename
    :type xml_in: str
    :param xslt_transform: input filename
    :type xslt_transform: str
    :return: HTML
    :rtype: str
    """

    xml_doc = etree.parse(xml_in)
    xslt_doc = etree.parse(xslt_transform)
    transform = etree.XSLT(xslt_doc)
    html = transform(xml_doc)
    return etree.tostring(html, pretty_print=True).decode("utf-8")


def main():
    xml_in = "./akn/HealthCrimJustCovid2021.akn.xml"
    xslt_transform = "./akn/schema/xslt/akn2html.xslt"
    # xslt_transform = "eisb_transform.xslt"
    html_out = "./akn/HealthCrimJustCovid2021.html"
    html_string = transform_xml(xml_in, xslt_transform)
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html_string)

if __name__=="__main__":
    main()
    