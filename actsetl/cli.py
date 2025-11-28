"""
Command-line interface for ActsETL.
"""

import argparse
import yaml

from lxml import etree

from actsetl.parsers.eisb import act_metadata, parse_body, parse_schedule, fix_headings, transform_xml
from actsetl.akn.skeleton import akn_skeleton
from actsetl.akn.utils import (
    akn_root, akn_notes, active_mods, akn_write, pop_styles
)


def main():
    """Main entry point for the script.
    
    python -m actsetl.cli data/eisb/act_6_2025.eisb.xml data/akn/act_6_2025.akn.xml

    """
    parser = argparse.ArgumentParser(description="Parse Irish Act XML into LegalDocML.")
    parser.add_argument("input_xml", help="Path to the source eISB XML file.")
    parser.add_argument("output_akn", help="Path for the output Akoma Ntoso XML file.")
    parser.add_argument("--notes", default=None, help="Path to the notes YAML file.")
    parser.add_argument("--styles", action="store_false", help="Remove styles.")   
    parser.add_argument("--no-validate", action="store_true", help="Disable XML schema validation.")
    args = parser.parse_args()

    preprocessed_eisb_xml = transform_xml(args.input_xml)
    xml_parser = etree.XMLParser(remove_blank_text=True)

    eisb_act = etree.fromstring(preprocessed_eisb_xml, parser=xml_parser)
    akn_act_meta = act_metadata(eisb_act)
    akn_act = akn_skeleton(akn_act_meta)

    parse_body(eisb_act.find("body"), akn_act.find("./body"), akn_act.find("./coverPage/toc"))
    parse_schedule(eisb_act, akn_act)
    fix_headings(akn_act)

    akn_act_root = akn_root(akn_act)

    # Post process by adding active modifications, notes and any other meta elements
    #ToDo - textual modifications are not yet applied to inline text, only identifies text blocks.
    #ToDo - refactor ToC as post-processing step
    #ToDo - cited legislation
    if args.styles:
        pop_styles(akn_act_root)
    active_mods(akn_act_root)

    if args.notes is not None:
        with open(args.notes, encoding="utf-8") as f:
            notes = yaml.safe_load(f)
        akn_notes(akn_act_root, notes)

    akn_write(akn_act_root, args.output_akn, validate=not args.no_validate)

if __name__ == "__main__":
    main()
