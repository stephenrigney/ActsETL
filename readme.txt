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

Debugging with VS Code
----------------------
Use the included `.vscode/launch.json` to debug locally or from Codespaces.

Local (launch)
- Select "Python: ActsETL (Local - launch)" from the Run/Debug configurations and hit F5.
- This runs the `actsetl.cli` module using the workspace Python interpreter and passes the default args (change them in the configuration as needed).

Codespaces (launch / attach)
- You can use the Codespaces "launch" config the same way if you want VS Code to start the process in the Codespace.
- Alternatively, start your process inside the Codespace container and attach to it. Example to start the app and wait for a debugger:

```bash
# Start Python and wait for debugger: default debugpy port is 5678
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m actsetl.cli tests/test_data/eisb_input/part_and_1_section.eisb.xml --loglevel INFO
```

- With the process running, select "Python: ActsETL (Attach - debugpy)" (or "Attach - python") and press F5 to connect.
- Ensure the port is forwarded in Codespaces (Ports panel) and that `pathMappings` are correct if the container workspace path differs from the path on your local machine.

Common notes
- To debug third-party code set `"justMyCode": false` in the config.
- For debugging start-up code, include `--wait-for-client` so the process pauses until the debugger attaches.
- Use `"console": "integratedTerminal"` to see process logs and provide input via the VS Code Terminal.

If you'd like, I can add a small `DEBUGGING.md` or more examples for compound configs and `tasks.json` preLaunch tasks.
