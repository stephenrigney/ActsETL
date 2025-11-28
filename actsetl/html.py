"""
Python module to transform LegalDocML XML into HTML.

"""
import logging
import argparse

from lxml import etree

log = logging.getLogger(__name__)

def akn_2_html(xml_in: str, xslt_transform:str) -> str:
    """
    Transform LegalDocML XML into HTML.
    
    :param xml_in: input filename
    :type xml_in: str
    :param xslt_transform: input filename
    :type xslt_transform: str
    :return: HTML
    :rtype: str
    """
    log.info("Parsing input XML from %s", xml_in)
    xml_doc = etree.parse(xml_in)
    log.info("Parsing XSLT transform from %s", xslt_transform)
    xslt_doc = etree.parse(xslt_transform)
    transform = etree.XSLT(xslt_doc)
    log.info("Applying XSLT transformation")
    html = transform(xml_doc)
    return etree.tostring(html, pretty_print=True).decode("utf-8")


def main():
    """Main entry point for the HTML transformation script.
    python -m actsetl.html data/akn/act_6_2025.akn.xml actsetl/resources/xslt/akn2html.xslt data/html/act_6_2025.html
    """
    parser = argparse.ArgumentParser(description="Transform Akoma Ntoso XML to HTML.")
    parser.add_argument("input_xml", help="Path to the source Akoma Ntoso XML file.")
    parser.add_argument("xslt_file", help="Path to the XSLT transformation file.")
    parser.add_argument("output_html", help="Path for the output HTML file.")
    parser.add_argument(
        "--loglevel",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.loglevel,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    html_string = akn_2_html(args.input_xml, args.xslt_file)
    log.info("Writing HTML output to %s", args.output_html)
    with open(args.output_html, "w", encoding="utf-8") as f:
        f.write(html_string)
    log.info("Transformation complete.")

if __name__=="__main__":
    main()
    