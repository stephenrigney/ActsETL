# Debugging in VS Code

This repository includes a launch configuration (`.vscode/launch.json`) with entries for local and Codespaces debugging, plus attach configurations for remote debugging.

## Launch configurations
- `Python: ActsETL (Local - launch)` — launches `actsetl.cli` using the selected Python interpreter in your local workspace.
- `Python: ActsETL (Codespaces - launch)` — launches `actsetl.cli` in Codespaces (runs inside the container/remote environment).

Both launch configs will run the `install-requirements` `preLaunchTask` (see `.vscode/tasks.json`) which installs your project in editable mode prior to debugging.

## Attach configurations
- `Python: ActsETL (Attach - debugpy)` — attaches to a `debugpy` server listening on port 5678.
- `Python: ActsETL (Attach - python)` — attaches via the Python debug adapter (also uses debugpy under the hood).

### Recommended attach flow (Codespaces)
1. In your Codespace terminal (or inside the container), start the app and have it wait for a debugger, for example:

```bash
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m actsetl.cli tests/test_data/eisb_input/part_and_1_section.eisb.xml --loglevel INFO
```

2. Ensure the `5678` port is forwarded in Codespaces (Ports panel) so VS Code can attach.
3. In VS Code, start the `Python: ActsETL (Attach - debugpy)` configuration to attach the debugger.

## Pre-launch task notes
- The `install-requirements` task runs `python -m pip install -e .` using your selected interpreter. This installs the package in editable mode and ensures packages declared in `pyproject.toml` are available to the debugger.
- If your project uses another dependency manager or you use `requirements.txt`, you can update `.vscode/tasks.json` to run the appropriate command:

Example for `requirements.txt`:
```json
{
  "command": "${command:python.interpreterPath} -m pip install -r requirements.txt"
}
```

## Debugging tips
- To debug startup code (e.g., code executed before the debugger attaches), use `--wait-for-client` so your program pauses until you attach.
- If you want to step into third-party library code, set `"justMyCode": false` in the launch config.
- To change program args, edit `args` in the launch configuration.
- Use `console: "integratedTerminal"` to see application logs and to provide stdin.

---

If you'd like, I can add a small `tasks.json` to support additional environment setup steps (for example installing dev tools, linting, or running tests), or add a compound config for server+client debugging (I won't implement that unless you ask). 
