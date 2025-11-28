/home/stephen/Documents/code/ActsETL/
├── actsetl/
│   ├── __init__.py
│   ├── akn/
│   │   ├── __init__.py
│   │   ├── skeleton.py       # Renamed from akn_skeleton.py
│   │   └── utils.py          # Renamed from akn_utils.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── eisb.py           # Core logic from eisb2akn.py
│   ├── resources/
│   │   ├── schemas/
│   │   │   ├── akomantoso30.xsd
│   │   │   └── xml.xsd
│   │   └── xslt/
│   │       ├── akn2html.xslt
│   │       └── eisb_transform.xslt
│   ├── cli.py                # Command-line interface script
│   └── html.py               # Logic from akn2html.py
├── data/
│   ├── akn/                  # Output directory
│   └── eisb/                 # Input directory
├── scripts/
│   └── run_conversion.py     # Example script to run the ETL
├── .pylintrc
├── notes.yaml
└── pyproject.toml            # Recommended for project metadata and dependencies
