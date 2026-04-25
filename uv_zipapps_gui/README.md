# uv-zipapps-gui

A Tkinter-based GUI for [zipapps](https://github.com/Clericpy/zipapps) configuration and Python version management via [uv](https://github.com/astral-sh/uv).

## Features

- **ZipApps Config** — Visual editor for all zipapps build options: entry point, interpreter, pip packages, includes, unzip rules, lazy install, layer mode, and more. Build `.pyz` files or package distributable bundles (pyz + interpreter + launcher) with one click.
- **Python Manager** — Browse, filter, install, and delete Python versions through uv. Auto-detects installed versions and sets the interpreter path for builds.
- **Cross-platform** — Works on Windows, macOS, and Linux. Generates platform-appropriate launchers (`.bat`/`.vbs` on Windows, `.sh` on Unix).

## Install

```bash
pip install uv-zipapps-gui
```

Requires Python >= 3.12 and [zipapps](https://github.com/Clericpy/zipapps) >= 2026.4.17.

## Usage

```bash
uv-zipapps-gui
# or run directly without installing:
uvx uv-zipapps-gui
```

### Quick Start

1. **Python Manager tab** — Set uv path (auto-detected if in PATH), select a Python version, and click **Install Selected**.
2. **ZipApps Config tab** — Configure build options, then click **pyz** to build a `.pyz` file, or **Dist** to create a distributable package.
3. Use **Load Config** / **Export Config** to save and restore build settings as JSON.

## Build Options

| Option | Description |
|--------|-------------|
| Output (`-o`) | Path of the output `.pyz` file |
| Interpreter (`-p`) | Python interpreter for the shebang line |
| Entry point (`-m`) | `package.module:function` format |
| Pip packages | Packages to install via pip |
| Includes (`-a`) | Extra paths to copy into the archive |
| Unzip (`-u`) | Names to extract at runtime (native extensions) |
| Compress (`-c`) | Deflate compression |
| Lazy install (`-d`) | Defer pip install to runtime |
| Layer mode | Serverless-friendly layout without `__main__.py` |
| Build ID (`-b`) | Skip duplicate builds based on file mtime |
| Dist | Package pyz + interpreter + launcher for distribution |

## License

MIT
