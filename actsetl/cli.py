"""
Command-line interface for ActsETL.
"""
import sys
from pathlib import Path
if __name__ == "__main__" and __package__ is None:
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

import logging
import argparse
import yaml
from pathlib import Path

from lxml import etree

from actsetl.parsers.eisb import (
    act_metadata, parse_body, parse_schedule, 
    fix_headings, transform_xml, build_active_modifications
)
from actsetl.akn.skeleton import akn_skeleton
from actsetl.akn.utils import (
    akn_root, akn_notes, akn_write, pop_styles
)

AKN_DATA_DIR = Path(__file__).parent.parent / "data" / "akn"

def parse_eisb(args):
    '''
    Process an eISB XML file into an Akoma Ntoso XML file.
    
    '''

    logging.basicConfig(
        level=args.loglevel,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        filename=args.logfile
    )
    log = logging.getLogger(__name__)

    log.info("Starting processing for %s", args.input_xml)

    preprocessed_eisb_xml = transform_xml(args.input_xml)
    xml_parser = etree.XMLParser(remove_blank_text=True)

    eisb_act = etree.fromstring(preprocessed_eisb_xml, parser=xml_parser)
    akn_act_meta = act_metadata(eisb_act)
    akn_act = akn_skeleton(akn_act_meta)

    # Refactored call to parse_body to capture amendment metadata
    _, all_mod_info = parse_body(
        eisb_act.find("body"), akn_act.find("./body")
            )
    parse_schedule(eisb_act, akn_act)
    fix_headings(akn_act)

    akn_act_root = akn_root(akn_act)

    # Post process by adding active modifications, notes and any other meta elements
    #ToDo - textual modifications are not yet applied to inline text, only identifies text blocks.
    #ToDo - refactor ToC as post-processing step
    #ToDo - cited legislation
    if args.styles:
        pop_styles(akn_act_root)

    # New logic to build and insert the <activeModifications> block
    if len(all_mod_info):
        log.info("Building active modifications block.")
        analysis_block = akn_act.find("./meta/analysis")
        if analysis_block is not None:
            # Remove the placeholder created by the skeleton
            existing_active_mods = analysis_block.find("activeModifications")
            if existing_active_mods is not None:
                analysis_block.remove(existing_active_mods)
            
            active_mods_elem = build_active_modifications(all_mod_info)
            analysis_block.append(active_mods_elem)

    if args.notes is not None:
        with open(args.notes, encoding="utf-8") as f:
            notes = yaml.safe_load(f)
        akn_notes(akn_act_root, notes)

    output_fn = args.output or str(AKN_DATA_DIR / args.input_xml.split("/")[-1].replace(".eisb.xml", ".akn.xml"))
    print(output_fn)
    log.info("Writing output to %s", output_fn)

    akn_write(akn_act_root, output_fn, validate=not args.no_validate)
    log.info("Successfully wrote output to %s", output_fn)

def main():
    """Main entry point for the script.
    
    python -m actsetl.cli data/eisb/act_6_2025.eisb.xml data/akn/act_6_2025.akn.xml

    """
    parser = argparse.ArgumentParser(description="Parse Irish Act XML into LegalDocML.")
    parser.add_argument("input_xml", help="Path to the source eISB XML file.")
    parser.add_argument("--output", default=None, help="Path for the output Akoma Ntoso XML file.")
    parser.add_argument("--notes", default=None, help="Path to the notes YAML file.")
    parser.add_argument("--styles", action="store_false", help="Remove styles.")   
    parser.add_argument("--no-validate", action="store_true", help="Disable XML schema validation.")
    parser.add_argument(
        "--loglevel",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )
    parser.add_argument("--logfile", help="Path to a file to write logs to.")
    args = parser.parse_args()

    parse_eisb(args)

if __name__ == "__main__":
    main()
