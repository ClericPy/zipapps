# -*- coding: utf-8 -*-
"""Download standalone Python interpreter via uv.

Modes (mutually exclusive):
    (default)     List available downloads, no installation.
    -a / --auto   Auto-select the best match and install.
    -i            Interactive mode: select platform and version, then install.

Examples:
    python -m zipapps.uv_download_python                        # list current platform downloads
    python -m zipapps.uv_download_python --all-platforms        # list all platforms
    python -m zipapps.uv_download_python -k 3.12                # list, filter by keyword
    python -m zipapps.uv_download_python -a                     # auto install latest for current platform
    python -m zipapps.uv_download_python -a -k 3.12             # auto install latest 3.12.x
    python -m zipapps.uv_download_python -a -k 3.12 -t ./my_py # auto install to custom dir
    python -m zipapps.uv_download_python -a --dry-run           # preview what would be installed
    python -m zipapps.uv_download_python -i                     # interactive install (current platform)
    python -m zipapps.uv_download_python -i --all-platforms     # interactive install (all platforms)
    python -m zipapps.uv_download_python --uv /path/to/uv -a    # use custom uv binary
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Any

ArchMap = dict[str, str]
Download = dict[str, Any]
GroupedDownloads = OrderedDict[str, list[Download]]


def _uv_bin(uv_path: str = "") -> list[str]:
    """Resolve uv executable as a command list (safe for paths with spaces)."""
    if uv_path:
        # shlex.split treats backslashes as escapes, which breaks Windows paths.
        # Use shlex only for posix-style paths (forward slashes or quoted).
        if "\\" in uv_path and not uv_path.startswith('"'):
            return [uv_path]
        return shlex.split(uv_path)
    path = shutil.which("uv")
    if path:
        return [path]
    return [sys.executable, "-m", "uv"]


def _run_uv(
    *args: str, uv_path: str = "", check: bool = True
) -> subprocess.CompletedProcess[str]:
    """Run a uv command."""
    cmd = _uv_bin(uv_path) + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, check=check)  # noqa: S603


def get_downloads(
    all_platforms: bool = False,
    all_arches: bool = False,
    uv_path: str = "",
) -> list[Download]:
    """Fetch available Python downloads from uv."""
    uv_args: list[str] = [
        "python",
        "list",
        "--all-versions",
        "--only-downloads",
        "--output-format",
        "json",
    ]
    if all_platforms:
        uv_args.append("--all-platforms")
    if all_arches:
        uv_args.append("--all-arches")
    result = _run_uv(*uv_args, uv_path=uv_path)
    data: list[Download] = json.loads(result.stdout)
    return data


def filter_current_platform(downloads: list[Download]) -> list[Download]:
    """Keep only cpython + default variant for current OS/arch."""
    current_os = platform.system().lower()
    machine = platform.machine().lower()
    arch_map: ArchMap = {
        "amd64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "aarch64",
        "aarch64": "aarch64",
        "i686": "x86",
        "x86": "x86",
    }
    uv_arch = arch_map.get(machine, machine)
    return [
        d
        for d in downloads
        if d["os"] == current_os
        and d["arch"] == uv_arch
        and d.get("variant", "default") == "default"
        and d["implementation"] == "cpython"
    ]


def group_by_platform(downloads: list[Download]) -> GroupedDownloads:
    """Group downloads by os-arch(-libc)(-variant) tag."""
    groups: GroupedDownloads = OrderedDict()
    for d in downloads:
        tag = d["os"] + "-" + d["arch"]
        if d.get("libc") and d["libc"] != "none":
            tag += "-" + d["libc"]
        variant = d.get("variant", "default")
        if variant != "default":
            tag += "-" + variant
        groups.setdefault(tag, []).append(d)
    return groups


def _version_sort_key(item: Download) -> tuple[int, int, int]:
    """Sort by (major, minor, patch)."""
    p = item["version_parts"]
    return (p["major"], p["minor"], p["patch"])


def _unique_latest(downloads: list[Download]) -> list[Download]:
    """Keep only the latest patch version per (platform, major.minor)."""
    seen: dict[tuple[str, int, int], Download] = {}
    for d in downloads:
        platform_tag = d["os"] + "-" + d["arch"]
        key = (platform_tag, d["version_parts"]["major"], d["version_parts"]["minor"])
        if key not in seen or _version_sort_key(d) > _version_sort_key(seen[key]):
            seen[key] = d
    return sorted(
        seen.values(),
        key=lambda d: (_version_sort_key(d), d["os"], d["arch"]),
        reverse=True,
    )


def _all_unique(downloads: list[Download]) -> list[Download]:
    """List all versions sorted by platform, then version latest first."""
    return sorted(
        downloads,
        key=lambda d: (d["os"] + "-" + d["arch"], _version_sort_key(d)),
        reverse=False,
    )


def print_downloads(downloads: list[Download], show_all: bool = False) -> None:
    """Print download list to stdout."""
    items = _all_unique(downloads) if show_all else _unique_latest(downloads)
    if not items:
        print("[INFO] No matching downloads found.")
        return
    print(f"[INFO] {len(items)} version(s) available:\n")
    print(f"  {'Idx':<5} {'Version':<14} {'Key'}")
    print(f"  {'---':<5} {'-------':<14} {'---'}")
    for idx, d in enumerate(items):
        print(f"  {idx:<5} {d['version']:<14} {d['key']}")


def interactive_select(downloads: list[Download]) -> Download | None:
    """Interactive selection: platform -> version."""
    groups = group_by_platform(downloads)
    if not groups:
        print("[ERROR] No downloads available.")
        return None

    # 1. Select platform
    if len(groups) == 1:
        platform_tag = next(iter(groups))
        print(f"[INFO] Only one platform: {platform_tag}")
    else:
        print("[INFO] Available platforms:\n")
        tags = list(groups.keys())
        for idx, tag in enumerate(tags):
            count = len(_unique_latest(groups[tag]))
            print(f"  {idx:<5} {tag:<40} ({count} versions)")
        print()
        try:
            choice = input("Select platform index (default 0): ").strip()
            idx = int(choice) if choice else 0
            platform_tag = tags[idx]
        except (ValueError, IndexError):
            print("[ERROR] Invalid selection.")
            return None

    platform_downloads = groups[platform_tag]

    # 2. Show all or latest?
    show_all = False
    print("\n  0     Show latest per major.minor only (default)")
    print("  1     Show all versions")
    choice = input("Select mode (default 0): ").strip()
    if choice == "1":
        show_all = True

    items = (
        _all_unique(platform_downloads)
        if show_all
        else _unique_latest(platform_downloads)
    )
    print(f"\n[INFO] {len(items)} version(s) for {platform_tag}:\n")
    print(f"  {'Idx':<5} {'Version':<14}")
    print(f"  {'---':<5} {'-------':<14}")
    for idx, d in enumerate(items):
        print(f"  {idx:<5} {d['version']:<14}")

    # 3. Select version
    print()
    try:
        choice = input("Select version index: ").strip()
        idx = int(choice)
        selected = items[idx]
    except (ValueError, IndexError):
        print("[ERROR] Invalid selection.")
        return None

    print(f"\n[INFO] Selected: {selected['key']}")
    print(f"        URL: {selected['url']}")
    return selected


def filter_by_keywords(
    downloads: list[Download], keywords: list[str]
) -> list[Download]:
    """Filter downloads by keywords (all must match against the key)."""
    result = downloads
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        result = [d for d in result if kw in d["key"]]
    return result


def _cleanup_uv_artifacts(target_path: Path) -> None:
    """Remove uv-generated symlinks/junctions and metadata files."""
    for child in target_path.iterdir():
        if child.name.startswith("."):
            continue
        try:
            os.readlink(child)
            if sys.platform == "win32":
                os.remove(child)
            else:
                child.unlink()
        except OSError:
            pass

    for meta in (target_path / ".gitignore", target_path / ".lock"):
        if meta.is_file():
            meta.unlink()
    temp_dir = target_path / ".temp"
    if temp_dir.is_dir():
        shutil.rmtree(temp_dir)


def _flatten_install(target_path: Path) -> None:
    """Promote versioned sub-directory contents to target root.

    After uv installs, the target contains a versioned dir like
    ``cpython-3.12.13-windows-x86_64-none``.  This function moves everything
    from that directory up to *target_path*, removes the versioned dir, and
    cleans up uv metadata / broken junctions.
    """
    version_dir: Path | None = None
    for child in target_path.iterdir():
        if child.name.startswith("."):
            continue
        if child.is_dir():
            try:
                os.readlink(child)
                continue
            except OSError:
                version_dir = child
                break

    if version_dir:
        for item in version_dir.iterdir():
            dest = target_path / item.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            shutil.move(str(item), str(dest))
        shutil.rmtree(version_dir)

    _cleanup_uv_artifacts(target_path)


def install(
    request: str,
    target: str,
    uv_path: str = "",
    *,
    flatten: bool = False,
    on_output: Callable[[str], None] | None = None,
) -> Path:
    """Install Python via uv python install --install-dir."""
    target_path = Path(target).resolve()
    target_path.mkdir(parents=True, exist_ok=True)
    if on_output:
        on_output(f"Installing {request} to {target_path} ...")
    cmd = _uv_bin(uv_path) + [
        "python",
        "install",
        request,
        "--install-dir",
        str(target_path),
        "--no-bin",
    ]
    if on_output:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)  # noqa: S603
        assert proc.stdout is not None
        buf = ""
        while True:
            ch = proc.stdout.read(1)
            if not ch:
                break
            if ch in ("\r", "\n"):
                line = buf.strip()
                if line:
                    on_output(line)
                buf = ""
            else:
                buf += ch
        if buf.strip():
            on_output(buf.strip())
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(
                f"uv python install failed with return code {proc.returncode}"
            )
    else:
        print(f"[INFO] Installing {request} to {target_path} ...")
        result = subprocess.run(cmd)  # noqa: S603
        if result.returncode != 0:
            raise RuntimeError(
                f"uv python install failed with return code {result.returncode}"
            )

    if flatten:
        _flatten_install(target_path)
    else:
        # Remove uv-generated version-less symlinks/junctions and metadata
        _cleanup_uv_artifacts(target_path)

    # Find the actual python executable
    if flatten:
        if sys.platform == "win32":
            candidates = [
                target_path / "python.exe",
                target_path / "Scripts" / "python.exe",
            ]
        else:
            candidates = [
                target_path / "bin" / "python3",
                target_path / "bin" / "python",
                target_path / "python3",
                target_path / "python",
            ]
    else:
        # Default: python lives inside the versioned sub-directory
        if sys.platform == "win32":
            candidates = [
                target_path / "python.exe",
                target_path / "Scripts" / "python.exe",
            ]
        else:
            candidates = [
                target_path / "bin" / "python3",
                target_path / "bin" / "python",
                target_path / "python3",
                target_path / "python",
            ]
        # Also search inside any versioned sub-directory
        for child in target_path.iterdir():
            if child.name.startswith(".") or not child.is_dir():
                continue
            try:
                os.readlink(child)
                continue
            except OSError:
                if sys.platform == "win32":
                    candidates += [
                        child / "python.exe",
                        child / "Scripts" / "python.exe",
                    ]
                else:
                    candidates += [
                        child / "bin" / "python3",
                        child / "bin" / "python",
                        child / "python3",
                        child / "python",
                    ]

    for p in candidates:
        if p.is_file():
            print(f"\n[DONE] Python installed: {p}")
            return p
    print(f"\n[DONE] Python installed to: {target_path}")
    print("       (Could not locate python executable automatically)")
    return target_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download standalone Python interpreter via uv. Default mode: list only. Use -a to install or -i for interactive selection.",
    )
    parser.add_argument(
        "--auto",
        "-a",
        action="store_true",
        help="Auto choose the best match for current platform, e.g. -k 3.12 --auto",
    )
    parser.add_argument(
        "--keywords",
        "-k",
        default="",
        help="Keywords to filter, split by ',' for many keywords (e.g. 3.12 or 3.12,linux)",
    )
    parser.add_argument(
        "-t",
        "--target",
        default=".",
        help="Target directory for installation (default: .)",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive mode: select platform and version",
    )
    parser.add_argument(
        "--uv",
        default="",
        help="Path to uv executable (default: auto-detect)",
    )
    parser.add_argument(
        "--all-platforms",
        action="store_true",
        help="Show all platforms in interactive/list mode",
    )
    parser.add_argument(
        "--all-versions",
        action="store_true",
        help="Show all patch versions (not just latest per minor)",
    )
    parser.add_argument(
        "--all-arches",
        action="store_true",
        help="Show all architectures",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show selected version without installing",
    )
    parser.add_argument(
        "--flatten",
        action="store_true",
        help="Flatten versioned sub-directory into target root (python.exe directly in target dir)",
    )
    args = parser.parse_args()
    uv_path: str = args.uv

    # Pre-check: uv must be available
    try:
        _run_uv("--version", uv_path=uv_path)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"[ERROR] uv is not available: {exc}")
        sys.exit(1)

    # Fetch downloads
    downloads = get_downloads(
        all_platforms=args.all_platforms,
        all_arches=args.all_arches,
        uv_path=uv_path,
    )

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    # Common filtering: platform + keywords
    if not args.all_platforms:
        downloads = filter_current_platform(downloads)

    # Auto mode: filter -> pick latest -> install
    if args.auto:
        if not keywords:
            downloads = [d for d in downloads if d["version"].replace(".", "").isdigit()]
        else:
            downloads = filter_by_keywords(downloads, keywords)
        if not downloads:
            print("[ERROR] No matching downloads found.")
            sys.exit(1)
        best = sorted(downloads, key=_version_sort_key, reverse=True)[0]
        print(f"[INFO] Auto selected: {best['key']}")
        if args.dry_run:
            print(f"[DRY-RUN] Would install to: {Path(args.target).resolve()}")
            return
        install(best["key"], args.target, uv_path=uv_path, flatten=args.flatten)
        return

    # Interactive mode
    if args.interactive:
        print(
            f"[INFO] Current platform: {platform.system().lower()}-{platform.machine().lower()}"
        )
        if keywords:
            downloads = filter_by_keywords(downloads, keywords)
        selected = interactive_select(downloads)
        if selected:
            if args.dry_run:
                print(f"[DRY-RUN] Would install to: {Path(args.target).resolve()}")
                return
            install(selected["key"], args.target, uv_path=uv_path, flatten=args.flatten)
        return

    # List mode (default)
    if keywords:
        downloads = filter_by_keywords(downloads, keywords)
    print_downloads(downloads, show_all=args.all_versions)


if __name__ == "__main__":
    main()
