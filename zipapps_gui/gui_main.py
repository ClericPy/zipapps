# -*- coding: utf-8 -*-
"""zipapps_gui — tkinter GUI for zipapps configuration and uv Python management.

Usage:
    python gui_main.py
"""

import json
import os
import queue
import subprocess
import shlex
import shutil
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


def _bind_tooltip(widget: tk.Widget, text: str) -> None:
    tip_window: tk.Toplevel | None = None

    def show(event: tk.Event) -> None:
        nonlocal tip_window
        tip_window = tw = tk.Toplevel(widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{event.x_root + 15}+{event.y_root + 10}")
        label = tk.Label(
            tw, text=text, background="#ffffe0", relief="solid", borderwidth=1,
            font=("Segoe UI", 9), padx=4, pady=2,
        )
        label.pack()

    def hide(_event: tk.Event) -> None:
        nonlocal tip_window
        if tip_window:
            tip_window.destroy()
            tip_window = None

    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)


def _log_to(text_widget: tk.Text, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    text_widget.configure(state="normal")
    text_widget.insert(tk.END, f"[{ts}] {message}\n")
    text_widget.see(tk.END)
    text_widget.configure(state="disabled")


def _run_in_thread(
    fn: Callable[..., T],
    on_success: Callable[[T], None] | None = None,
    on_error: Callable[[BaseException], None] | None = None,
    before: Callable[[], None] | None = None,
    after: Callable[[], None] | None = None,
) -> threading.Thread:
    root = getattr(tk, "_default_root", None)
    _q: queue.Queue[tuple[str, Any]] = queue.Queue()

    def _poll() -> None:
        try:
            while True:
                msg_type, value = _q.get_nowait()
                if msg_type == "ok" and on_success:
                    on_success(value)
                elif msg_type == "err" and on_error:
                    on_error(value)
                elif msg_type == "after" and after:
                    after()
        except queue.Empty:
            pass
        if root:
            root.after(100, _poll)

    def _worker() -> None:
        try:
            result = fn()
            _q.put(("ok", result))
        except BaseException as exc:
            _q.put(("err", exc))
        finally:
            _q.put(("after", None))

    if before:
        before()
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    if root:
        root.after(100, _poll)
    return t


class _LogWriter:
    """Minimal file-like object that puts each line into a queue."""

    def __init__(self, q: queue.Queue[str]) -> None:
        self._q = q
        self._real = sys.stderr

    def write(self, msg: str) -> None:
        for line in msg.splitlines():
            if line.strip():
                self._q.put(line)

    def flush(self) -> None:
        pass

    def fileno(self) -> int:
        return self._real.fileno()


def _save_config(config: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_config(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Failed to load config: {exc}") from exc


# ---------------------------------------------------------------------------
# Build configuration panel
# ---------------------------------------------------------------------------


class _BuildConfigPanel(ttk.Frame):
    _FIELD_DEFS: list[tuple[str, str, str, str, str]] = [
        ("output", "Output file (-o)", "app.pyz", "entry",
         "The path of the output file, defaults to \"app.pyz\"."),
        ("interpreter", "Interpreter (-p)", "", "entry",
         "The path of the Python interpreter set as the shebang line. With shebang you can run app with ./app.pyz directly."),
        ("main", "Entry point (-m)", "", "entry",
         "The entry point function: package | package.module | package.module:function | module:function"),
        ("pip_args", "Pip packages", "", "text",
         "Packages to install via pip. All unknown args will be used by pip install."),
        ("includes", "Includes (-a)", "", "entry",
         "Paths copied to cache_path while packaging, split by \",\". For libs not from pypi or special config files."),
        ("unzip", "Unzip (-u)", "", "entry",
         "Names to unzip at runtime, split by \",\" without ext. For .so/.pyd files. Use * to unzip all, AUTO to auto-add .pyd/.so. Env: ZIPAPPS_UNZIP"),
        ("unzip_exclude", "Unzip exclude (-ue)", "", "entry",
         "The opposite of --unzip, names not to be unzipped. Env: ZIPAPPS_UNZIP_EXCLUDE"),
        ("unzip_path", "Unzip path (-up)", "", "entry",
         "Cache path for unzipped files. Supports $TEMP/$HOME/$SELF/$PID/$CWD variables."),
        ("cache_path", "Cache path (-cp)", "", "entry",
         "Cache path for site-packages and includes, treated as PYTHONPATH. If not set, creates and cleans up in TEMP dir automatically."),
        ("env_paths", "Env paths (--zipapps)", "", "entry",
         "Default --zipapps arg if not given while running. Supports $TEMP/$HOME/$SELF/$PID/$CWD prefix, separated by commas."),
        ("sys_paths", "Sys paths", "", "entry",
         "Paths inserted to sys.path[0] while running. Supports $TEMP/$HOME/$SELF/$PID/$CWD prefix, separated by commas."),
        ("uv_path", "UV path (--uv)", "", "entry",
         "The executable path of python-uv, to speed up pip install."),
        ("build_id", "Build ID (-b)", "", "entry",
         "Skip duplicate builds. File paths split by \",\" use modify time as build_id. Supports glob with *. Example: -b requirements.txt"),
        ("compressed", "Compress (-c)", "", "check", "Compress files with the deflate method."),
        ("compiled", "Compile to .pyc", "", "check",
         "Compile .py to .pyc for fast import. zipapp does not work unless you unzip it."),
        ("shell", "Shell (-s)", "", "check",
         "Only while main is not set, used for shell=True in subprocess.Popen."),
        ("main_shell", "Main shell (-ss)", "", "check",
         "Only for main is not null, call main with subprocess.Popen. Used for psutil ImportError of DLL load."),
        ("ignore_system_python_path", "Strict Python path (-spp)", "", "check",
         "Ignore global PYTHONPATH, only use zipapps_cache and app.pyz."),
        ("lazy_install", "Lazy install (-d)", "", "check",
         "Install packages with pip while running. Requirements will not be installed into pyz file. Default unzip path: SELF/zipapps_cache"),
        ("python_version_slice", "Version accuracy (-pva)", "2", "spin",
         "Only for lazy-install mode. pip target folders differ by sys.version_info[:slice]. Default 2 means 3.8.3 == 3.8.4"),
        ("layer_mode", "Layer mode", "", "check",
         "Layer mode for serverless. __main__.py / ensure_zipapps.py / activate_zipapps.py will not be set."),
        ("layer_mode_prefix", "Layer mode prefix", "python", "entry",
         "Only work with --layer-mode, move files in the given prefix folder."),
        ("clear_zipapps_cache", "Clear cache on run", "", "check",
         "Clear the zipapps cache folder after running. May fail for .pyd/.so files."),
        ("clear_zipapps_self", "Clear self on run", "", "check",
         "Clear the zipapps pyz file itself after running."),
        ("chmod", "Chmod", "", "entry",
         "os.chmod(int(chmod, 8)) for unzip files, e.g. 755. Unix-like system only."),
        ("rm_patterns", "Remove patterns", "*.dist-info,__pycache__", "entry",
         "Delete useless files/folders, split by \",\". Recursively glob: **/*.pyc"),
    ]

    # checkbox keys grouped to share one row (3 per row)
    _CHECK_GROUPS: list[tuple[str, ...]] = [
        ("compressed", "compiled", "shell"),
        ("main_shell", "ignore_system_python_path", "lazy_install"),
        ("layer_mode", "clear_zipapps_cache", "clear_zipapps_self"),
    ]

    def __init__(self, parent: ttk.Frame, log_fn: Callable[[str], None]) -> None:
        super().__init__(parent)
        self._log = log_fn
        self._vars: dict[str, tk.Variable] = {}
        self._interpreter_var: tk.StringVar | None = None
        self._text_widgets: dict[str, tk.Text] = {}
        self._build()
        self.pack(fill="both", expand=True)

    def _build(self) -> None:
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind(
            "<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _on_mousewheel)
        )
        canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

        btn_frame = ttk.Frame(scroll_frame)
        btn_frame.grid(row=0, column=0, columnspan=6, pady=(0, 5), sticky="ew")
        ttk.Button(btn_frame, text="Load Config", command=self.on_load).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame, text="Export Config", command=self.on_export).pack(
            side="left", padx=5
        )
        build_btn = tk.Button(
            btn_frame, text="Build .pyz", command=self.on_build,
            font=("", 10, "bold"), fg="#2e7d32",
        )
        build_btn.pack(side="left", padx=20)

        row = 1
        _group_members: set[str] = set()
        for group in self._CHECK_GROUPS:
            _group_members.update(group)

        for key, label, default, wtype, help_text in self._FIELD_DEFS:
            if wtype == "check" and key in _group_members and key != next(iter(next(g for g in self._CHECK_GROUPS if key in g))):
                continue

            ttk.Label(scroll_frame, text=label).grid(
                row=row, column=0, sticky="w", padx=5, pady=2
            )
            if wtype == "check":
                var: tk.Variable = tk.BooleanVar(value=False)
                cb = ttk.Checkbutton(scroll_frame, variable=var)
                cb.grid(row=row, column=1, sticky="w", padx=5, pady=2)
                _bind_tooltip(cb, help_text)
                # Place grouped checkboxes on the same row
                group = next((g for g in self._CHECK_GROUPS if key in g), None)
                if group:
                    for i, gkey in enumerate(group):
                        if gkey == key:
                            continue
                        g_def = next(d for d in self._FIELD_DEFS if d[0] == gkey)
                        _, g_label, _, _, g_help = g_def
                        col = 2 + (i * 2) if i < group.index(key) else 2 + ((i - 1) * 2)
                        ttk.Label(scroll_frame, text=g_label).grid(
                            row=row, column=col, sticky="w", padx=(20, 0), pady=2
                        )
                        g_var: tk.Variable = tk.BooleanVar(value=False)
                        g_cb = ttk.Checkbutton(scroll_frame, variable=g_var)
                        g_cb.grid(row=row, column=col + 1, sticky="w", padx=5, pady=2)
                        _bind_tooltip(g_cb, g_help)
                        self._vars[gkey] = g_var
            elif wtype == "text":
                var = tk.StringVar(value=default)
                txt = tk.Text(scroll_frame, height=3, width=60, wrap="word")
                txt.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=2)
                txt.insert("1.0", default)
                self._text_widgets[key] = txt
            elif wtype == "spin":
                var = tk.IntVar(value=int(default) if default else 2)
                ttk.Spinbox(
                    scroll_frame, from_=1, to=3, textvariable=var, width=5
                ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
            else:
                var = tk.StringVar(value=default)
                ttk.Entry(scroll_frame, textvariable=var, width=60).grid(
                    row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=2
                )
                if key == "output":
                    str_var = var
                    ttk.Button(
                        scroll_frame,
                        text="...",
                        width=3,
                        command=lambda: self._browse_output(str_var),
                    ).grid(row=row, column=3, padx=2)
                elif key == "interpreter":
                    str_var = var
                    self._interpreter_var = str_var
                    ttk.Button(
                        scroll_frame,
                        text="...",
                        width=3,
                        command=lambda: self._browse_interpreter(str_var),
                    ).grid(row=row, column=3, padx=2)
                elif key == "includes":
                    str_var = var
                    ttk.Button(
                        scroll_frame,
                        text="...",
                        width=3,
                        command=lambda: self._browse_includes(str_var),
                    ).grid(row=row, column=3, padx=2)

            self._vars[key] = var

            if help_text:
                self._create_tooltip(scroll_frame, help_text, row)

            row += 1

        scroll_frame.columnconfigure(1, weight=1)

    def _create_tooltip(
        self, parent: ttk.Frame, text: str, row: int, col_offset: int = 0
    ) -> None:
        widget = parent.grid_slaves(row=row, column=col_offset)[0]
        _bind_tooltip(widget, text)

    def _browse_includes(self, var: tk.StringVar) -> None:
        paths = filedialog.askopenfilenames(
            title="Select files/dirs to include",
        )
        if paths:
            existing = var.get().strip()
            new = ",".join(p for p in paths)
            var.set(f"{existing},{new}" if existing else new)

    def _browse_output(self, var: tk.StringVar) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".pyz",
            filetypes=[("Zipapp", "*.pyz"), ("All", "*.*")],
            initialfile=var.get(),
        )
        if path:
            var.set(path)

    def _browse_interpreter(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(
            title="Select Python interpreter",
            filetypes=[("Python", "python*"), ("All", "*.*")],
        )
        if path:
            var.set(path)

    def set_interpreter(self, path: str) -> None:
        if self._interpreter_var:
            self._interpreter_var.set(path)
            self._log(f"Interpreter set to: {path}")

    def _get_str(self, key: str) -> str:
        return str(self._vars[key].get())  # type: ignore[no-untyped-call]

    def _get_bool(self, key: str) -> bool:
        return bool(self._vars[key].get())  # type: ignore[no-untyped-call]

    def _get_int(self, key: str) -> int:
        return int(self._vars[key].get())  # type: ignore[no-untyped-call]

    def collect_config(self) -> dict[str, Any]:
        pip_text_widget = self._text_widgets.get("pip_args")
        if pip_text_widget:
            pip_args_text = pip_text_widget.get("1.0", "end").strip()
        else:
            pip_args_text = self._get_str("pip_args").strip()
        pip_args = shlex.split(pip_args_text) if pip_args_text else None

        return {
            "includes": self._get_str("includes"),
            "cache_path": self._get_str("cache_path") or None,
            "main": self._get_str("main"),
            "output": self._get_str("output") or None,
            "interpreter": self._get_str("interpreter") or None,
            "compressed": self._get_bool("compressed"),
            "shell": self._get_bool("shell"),
            "unzip": self._get_str("unzip"),
            "unzip_path": self._get_str("unzip_path"),
            "ignore_system_python_path": self._get_bool("ignore_system_python_path"),
            "main_shell": self._get_bool("main_shell"),
            "pip_args": pip_args,
            "compiled": self._get_bool("compiled"),
            "build_id": self._get_str("build_id"),
            "env_paths": self._get_str("env_paths"),
            "lazy_install": self._get_bool("lazy_install"),
            "sys_paths": self._get_str("sys_paths"),
            "python_version_slice": self._get_int("python_version_slice"),
            "layer_mode": self._get_bool("layer_mode"),
            "layer_mode_prefix": self._get_str("layer_mode_prefix"),
            "clear_zipapps_cache": self._get_bool("clear_zipapps_cache"),
            "clear_zipapps_self": self._get_bool("clear_zipapps_self"),
            "unzip_exclude": self._get_str("unzip_exclude"),
            "chmod": self._get_str("chmod"),
            "rm_patterns": self._get_str("rm_patterns"),
            "uv_path": self._get_str("uv_path"),
        }

    def apply_config(self, config: dict[str, Any]) -> None:
        for key, var in self._vars.items():
            if key not in config:
                continue
            value = config[key]
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            elif isinstance(var, tk.IntVar):
                var.set(int(value) if value is not None else 2)
            elif isinstance(var, tk.StringVar):
                if key == "pip_args" and isinstance(value, list):
                    text_value = " ".join(shlex.quote(str(a)) for a in value)
                    var.set(text_value)
                    if key in self._text_widgets:
                        tw = self._text_widgets[key]
                        tw.delete("1.0", tk.END)
                        tw.insert("1.0", text_value)
                else:
                    var.set(str(value) if value is not None else "")
                    if key in self._text_widgets:
                        tw = self._text_widgets[key]
                        tw.delete("1.0", tk.END)
                        tw.insert("1.0", str(value) if value is not None else "")

    def on_build(self) -> None:
        try:
            config = self.collect_config()
        except Exception as e:
            self._log(f"Config error: {e}")
            return
        self._log("Building .pyz ...")
        _log_q: queue.Queue[str] = queue.Queue()

        def _poll_log() -> None:
            try:
                while True:
                    msg = _log_q.get_nowait()
                    self._log(msg)
            except queue.Empty:
                pass
            root = self.winfo_toplevel()
            if root.winfo_exists():
                root.after(50, _poll_log)

        def do_build() -> Path:
            import json as _json

            script = (
                "import sys,json\n"
                "from zipapps.main import ZipApp\n"
                f"config = json.loads({_json.dumps(config)!r})\n"
                "app = ZipApp(**config)\n"
                "result = app.build()\n"
                "sys.stdout.write(str(result))\n"
            )
            proc = subprocess.Popen(
                [sys.executable, "-c", script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            assert proc.stdout is not None
            assert proc.stderr is not None
            buf = ""
            while True:
                ch = proc.stdout.read(1)
                if not ch:
                    break
                c = chr(ch[0])
                if c == "\r":
                    line = buf.strip()
                    if line:
                        _log_q.put(line)
                    buf = ""
                elif c == "\n":
                    line = buf.strip()
                    if line:
                        _log_q.put(line)
                    buf = ""
                else:
                    buf += c
            if buf.strip():
                _log_q.put(buf.strip())
            for line in proc.stderr.read().decode().strip().splitlines():
                if line.strip():
                    _log_q.put(line)
            proc.wait()
            if proc.returncode != 0:
                raise RuntimeError(f"Build failed with return code {proc.returncode}")
            return Path(config.get("output", "app.pyz"))

        root = self.winfo_toplevel()
        root.after(50, _poll_log)
        _run_in_thread(
            fn=do_build,
            on_success=lambda result: self._log(f"Built successfully: {result}"),
            on_error=lambda e: self._log(f"Build failed: {e}"),
        )

    def on_export(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
            title="Export Config",
        )
        if not path:
            return
        try:
            _save_config(self.collect_config(), Path(path))
            self._log(f"Config exported to: {path}")
        except OSError as e:
            messagebox.showerror("Export Error", str(e))

    def on_load(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json"), ("All", "*.*")],
            title="Load Config",
        )
        if not path:
            return
        try:
            config = _load_config(Path(path))
            self.apply_config(config)
            self._log(f"Config loaded from: {path}")
        except ValueError as e:
            messagebox.showerror("Load Error", str(e))


# ---------------------------------------------------------------------------
# UV Python manager panel
# ---------------------------------------------------------------------------


class _UvPythonPanel(ttk.Frame):
    def __init__(
        self,
        parent: ttk.Frame,
        log_fn: Callable[[str], None],
        on_set_interpreter: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._log = log_fn
        self._on_set_interpreter = on_set_interpreter
        self._downloads: list[dict[str, Any]] = []
        self._all_downloads: list[dict[str, Any]] = []
        self._build()
        self.pack(fill="both", expand=True)

    def _build(self) -> None:
        row = 0

        settings = ttk.LabelFrame(self, text="UV Settings", padding=5)
        settings.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        row += 1

        ttk.Label(settings, text="UV path:").grid(row=0, column=0, sticky="w")
        self._uv_path = tk.StringVar()
        ttk.Entry(settings, textvariable=self._uv_path, width=50).grid(
            row=0, column=1, padx=5
        )
        ttk.Button(settings, text="Auto-detect", command=self._auto_detect_uv).grid(
            row=0, column=2
        )
        ttk.Button(settings, text="...", width=3, command=self._browse_uv).grid(
            row=0, column=3, padx=2
        )
        self.after(100, self._auto_detect_uv)

        self._current_platform = tk.BooleanVar(value=True)
        cp_cb = ttk.Checkbutton(
            settings, text="Current platform only", variable=self._current_platform,
            command=self._on_platform_filter_changed,
        )
        cp_cb.grid(row=1, column=0, columnspan=3, sticky="w", pady=2)
        _bind_tooltip(cp_cb, "Only show Python builds for the current OS and architecture")

        ttk.Label(settings, text="Filter keyword:").grid(row=2, column=0, sticky="w")
        self._filter_kw = tk.StringVar()
        filter_entry = ttk.Entry(settings, textvariable=self._filter_kw, width=30)
        filter_entry.grid(row=2, column=1, sticky="w", padx=5)
        filter_entry.bind("<Return>", lambda _: self.refresh_versions())
        ttk.Button(settings, text="Filter", command=self.refresh_versions).grid(
            row=2, column=2
        )

        actions = ttk.LabelFrame(self, text="Actions", padding=5)
        actions.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        row += 1

        ttk.Button(
            actions, text="List Versions", command=self.refresh_versions
        ).pack(side="left", padx=5)

        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=row, column=0, sticky="nsew", padx=5, pady=5)
        row += 1

        columns = ("version", "key", "os", "arch")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=12
        )
        self._tree.heading("version", text="Version")
        self._tree.heading("key", text="Key")
        self._tree.heading("os", text="OS")
        self._tree.heading("arch", text="Arch")
        self._tree.column("version", width=80, minwidth=60)
        self._tree.column("key", width=350, minwidth=200)
        self._tree.column("os", width=80, minwidth=50)
        self._tree.column("arch", width=80, minwidth=50)

        tree_scroll = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=tree_scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        install_frame = ttk.LabelFrame(self, text="Install", padding=5)
        install_frame.grid(row=row, column=0, sticky="ew", padx=5, pady=5)
        row += 1

        ttk.Label(install_frame, text="Target dir:").grid(row=0, column=0, sticky="w")
        self._target_dir = tk.StringVar(value="./.cache")
        ttk.Entry(install_frame, textvariable=self._target_dir, width=50).grid(
            row=0, column=1, padx=5
        )
        ttk.Button(install_frame, text="Browse...", command=self._browse_target).grid(
            row=0, column=2
        )
        if sys.platform == "win32":
            ttk.Button(install_frame, text="Open", width=5, command=self._open_target).grid(
                row=0, column=3, padx=2
            )

        self._flatten = tk.BooleanVar(value=False)
        flatten_cb = ttk.Checkbutton(
            install_frame, text="Flatten install", variable=self._flatten
        )
        flatten_cb.grid(row=1, column=0, columnspan=3, sticky="w", pady=2)
        _bind_tooltip(flatten_cb, "Extract all files to the target dir instead of a versioned subdirectory")

        btn_row = ttk.Frame(install_frame)
        btn_row.grid(row=2, column=0, columnspan=3, pady=5)
        install_btn = ttk.Button(
            btn_row, text="Install Selected", command=self.install_selected
        )
        install_btn.pack(side="left", padx=5)
        _bind_tooltip(install_btn, "Install the selected Python version to the target directory")
        self._cancel_btn = ttk.Button(
            btn_row, text="Cancel Install", command=self.cancel_install, state="disabled"
        )
        self._cancel_btn.pack(side="left", padx=5)
        delete_btn = ttk.Button(
            btn_row, text="Delete Installed", command=self.delete_installed
        )
        delete_btn.pack(side="left", padx=5)
        _bind_tooltip(delete_btn, "Delete all contents in the target directory")
        self._install_proc: subprocess.Popen[bytes] | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

    def _bring_to_front(self) -> None:
        root = self.winfo_toplevel()
        root.lift()
        root.focus_force()
        if sys.platform == "win32":
            try:
                from ctypes import windll

                windll.user32.SetForegroundWindow(root.winfo_id())
            except OSError:
                pass

    def _auto_detect_uv(self) -> None:
        path = shutil.which("uv")
        if path:
            self._uv_path.set(path)
            self._log(f"uv found: {path}")
            self.refresh_versions()
        else:
            self._uv_path.set("")
            self._log("uv not found in PATH. Install it or set the path manually.")

    def _browse_uv(self) -> None:
        path = filedialog.askopenfilename(
            title="Select uv executable",
            filetypes=[("Executable", "uv*"), ("All", "*.*")],
        )
        if path:
            self._uv_path.set(path)
            self._log(f"uv path set to: {path}")

    def _browse_target(self) -> None:
        path = filedialog.askdirectory(title="Select install target directory")
        if path:
            self._target_dir.set(path)

    def _open_target(self) -> None:
        target = self._target_dir.get().strip()
        if target:
            path = Path(target).resolve()
            if path.is_dir():
                os.startfile(str(path))

    def _get_uv_path(self) -> str:
        return self._uv_path.get().strip()

    def _filter_downloads(
        self, downloads: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if self._current_platform.get():
            from zipapps.uv_download_python import filter_current_platform

            downloads = filter_current_platform(downloads)

        kw = self._filter_kw.get().strip()
        if kw:
            from zipapps.uv_download_python import filter_by_keywords

            downloads = filter_by_keywords(downloads, kw.split(","))
        return downloads

    def _on_platform_filter_changed(self) -> None:
        if self._all_downloads:
            self._apply_filter()

    def _on_tree_select(self, _event: tk.Event) -> None:
        sel = self._tree.selection()
        if not sel or sel[0] == getattr(self, "_last_selected", None):
            return
        self._last_selected = sel[0]
        tags = self._tree.item(sel[0], "tags")
        if "installed" not in tags:
            return
        values = self._tree.item(sel[0], "values")
        key = str(values[1])
        target = self._target_dir.get().strip() or "."
        target_path = Path(target).resolve()
        if self._flatten.get():
            if sys.platform == "win32":
                interp = str(target_path / "python.exe")
            else:
                interp = str(target_path / "bin" / "python3")
        else:
            if sys.platform == "win32":
                interp = str(target_path / key / "python.exe")
            else:
                interp = str(target_path / key / "bin" / "python3")
        if self._on_set_interpreter:
            self._on_set_interpreter(interp)
        self._log(f"Interpreter set to: {interp}")

    def _fetch_installed_keys(self) -> set[str]:
        target = self._target_dir.get().strip() or "."
        target_path = Path(target).resolve()
        if not target_path.is_dir():
            return set()
        return {f.stem for f in target_path.iterdir() if f.is_file() and f.suffix == ".version"}

    def _populate_treeview(self, downloads: list[dict[str, Any]]) -> None:
        self._all_downloads = downloads
        self._apply_filter()

    def _apply_filter(self) -> None:
        self._tree.delete(*self._tree.get_children())
        filtered = self._filter_downloads(self._all_downloads)
        self._downloads = filtered
        seen: dict[tuple[str, int, int], dict[str, Any]] = {}
        for d in filtered:
            tag = d["os"] + "-" + d["arch"]
            key = (tag, d["version_parts"]["major"], d["version_parts"]["minor"])
            if key not in seen:
                seen[key] = d
        items = sorted(seen.values(), key=lambda d: d["version"], reverse=True)

        installed_keys = self._fetch_installed_keys()

        for d in items:
            is_installed = d["key"] in installed_keys
            tag = ("installed",) if is_installed else ()
            self._tree.insert(
                "", "end",
                values=(d["version"], d["key"], d["os"], d["arch"]),
                tags=tag,
            )
        self._tree.tag_configure("installed", foreground="green")
        self._log(f"{len(items)} version(s) shown, {len(installed_keys)} installed.")

        # Auto-select first installed item to set interpreter
        children = self._tree.get_children()
        for item in children:
            tags = self._tree.item(item, "tags")
            if "installed" in tags:
                self._tree.selection_set(item)
                self._on_tree_select(None)
                break

    def refresh_versions(self) -> None:
        self._log("Fetching Python versions from uv ...")
        uv_path = self._get_uv_path()

        def fetch() -> list[dict[str, Any]]:
            from zipapps.uv_download_python import get_downloads

            return get_downloads(uv_path=uv_path)

        _run_in_thread(
            fn=fetch,
            on_success=self._populate_treeview,
            on_error=lambda e: self._log(f"Failed to fetch versions: {e}"),
        )

    def install_selected(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a version from the list first.")
            return
        values = self._tree.item(sel[0], "values")
        key = str(values[1])
        target = self._target_dir.get().strip() or "."
        flatten = self._flatten.get()
        uv_path = self._get_uv_path()

        from zipapps.uv_download_python import _uv_bin

        target_path = Path(target).resolve()
        target_path.mkdir(parents=True, exist_ok=True)
        cmd = _uv_bin(uv_path) + [
            "python", "install", key, "--install-dir", str(target_path), "--no-bin",
        ]
        self._log(f"Installing {key} to {target_path} ...")
        self._cancel_btn.configure(state="normal")

        def _worker() -> None:
            self._install_proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            assert self._install_proc.stdout is not None
            buf = ""
            while True:
                ch = self._install_proc.stdout.read(1)
                if not ch:
                    break
                c = chr(ch[0])
                if c == "\r":
                    line = buf.strip()
                    if line:
                        _log_q.put(("progress", line))
                    buf = ""
                elif c == "\n":
                    line = buf.strip()
                    if line:
                        _log_q.put(("log", line))
                    buf = ""
                else:
                    buf += c
            if buf.strip():
                _log_q.put(("log", buf.strip()))
            self._install_proc.wait()
            rc = self._install_proc.returncode
            self._install_proc = None

            if rc == 0:
                if flatten:
                    from zipapps.uv_download_python import _flatten_install
                    _flatten_install(target_path)
                else:
                    from zipapps.uv_download_python import _cleanup_uv_artifacts
                    _cleanup_uv_artifacts(target_path)
                # Find python executable
                if flatten:
                    if sys.platform == "win32":
                        candidates = [target_path / "python.exe", target_path / "Scripts" / "python.exe"]
                    else:
                        candidates = [target_path / "bin" / "python3", target_path / "bin" / "python", target_path / "python3", target_path / "python"]
                else:
                    import glob as _glob
                    dirs = sorted(_glob.glob(str(target_path / "*")), reverse=True)
                    if sys.platform == "win32":
                        candidates = [Path(d) / "python.exe" for d in dirs]
                    else:
                        candidates = [Path(d) / "bin" / "python3" for d in dirs]
                found = next((c for c in candidates if c.is_file()), target_path)
                (target_path / f"{key}.version").touch()
                _result_q.put(("ok", str(found)))
            else:
                _result_q.put(("err", RuntimeError(f"uv install failed with return code {rc}")))

        _log_q: queue.Queue[tuple[str, str]] = queue.Queue()
        _result_q: queue.Queue[tuple[str, Any]] = queue.Queue()
        _progress_line: list[str] = [""]

        def _poll() -> None:
            root = self.winfo_toplevel()
            if not root.winfo_exists():
                return
            try:
                while True:
                    kind, msg = _log_q.get_nowait()
                    if kind == "progress":
                        _progress_line[0] = msg
                    else:
                        _progress_line[0] = ""
                        self._log(msg)
            except queue.Empty:
                pass
            # Update status bar with current progress
            if _progress_line[0]:
                root = self.winfo_toplevel()
                if hasattr(root, "_status_var") and _progress_line[0]:
                    root._status_var.set(_progress_line[0])
            try:
                msg_type, value = _result_q.get_nowait()
                self._cancel_btn.configure(state="disabled")
                _progress_line[0] = ""
                if hasattr(root, "_status_var"):
                    root._status_var.set("Ready")
                if msg_type == "ok":
                    self._log(f"Installed: {value}")
                    self._bring_to_front()
                    self.refresh_versions()
                else:
                    self._log(f"Install failed: {value}")
                return
            except queue.Empty:
                pass
            root.after(50, _poll)

        threading.Thread(target=_worker, daemon=True).start()
        self.winfo_toplevel().after(50, _poll)

    def cancel_install(self) -> None:
        if self._install_proc and self._install_proc.poll() is None:
            self._install_proc.kill()
            self._log("Install cancelled.")
            self._cancel_btn.configure(state="disabled")

    def delete_installed(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a version from the list first.")
            return
        values = self._tree.item(sel[0], "values")
        key = str(values[1])
        target = self._target_dir.get().strip() or "."
        target_path = Path(target).resolve()

        version_file = target_path / f"{key}.version"
        if not version_file.is_file():
            messagebox.showinfo("Info", f"{key} is not installed in target directory.")
            return

        sub_dir = target_path / key
        if sub_dir.is_dir():
            del_path = sub_dir
            desc = str(sub_dir)
        else:
            del_path = target_path
            desc = str(target_path) + " (flatten mode)"
        if not messagebox.askyesno("Confirm", f"Delete:\n{desc}"):
            return

        self._log(f"Deleting {del_path} ...")

        def do_delete() -> None:
            shutil.rmtree(del_path)
            version_file = target_path / f"{key}.version"
            if version_file.is_file():
                version_file.unlink()

        def _on_delete_success(_: None) -> None:
            self._log(f"Deleted: {del_path}")
            self._on_platform_filter_changed()

        _run_in_thread(
            fn=do_delete,
            on_success=_on_delete_success,
            on_error=lambda e: self._log(f"Delete failed: {e}"),
        )

    def set_interpreter(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a version from the list first.")
            return
        target = self._target_dir.get().strip() or "."
        target_path = Path(target).resolve()
        if self._flatten.get():
            if sys.platform == "win32":
                interp = str(target_path / "python.exe")
            else:
                interp = str(target_path / "bin" / "python3")
        else:
            values = self._tree.item(sel[0], "values")
            key = str(values[1])
            if sys.platform == "win32":
                interp = str(target_path / key / "python.exe")
            else:
                interp = str(target_path / key / "bin" / "python3")
        if self._on_set_interpreter:
            self._on_set_interpreter(interp)
        else:
            self._log(f"Suggested interpreter: {interp}")


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------


class ZipAppsGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("zipapps GUI")
        self.geometry("900x750")
        self.minsize(700, 500)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._init_ui()
        self.after_idle(self._center)

    def _center(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"+{x}+{y}")

    def _on_close(self) -> None:
        self.destroy()

    def _init_ui(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=5, pady=(5, 0))

        uv_frame = ttk.Frame(self._notebook)
        self._notebook.add(uv_frame, text="Python Manager")
        self._uv_panel = _UvPythonPanel(
            uv_frame,
            log_fn=self.log,
            on_set_interpreter=lambda path: self._config_panel.set_interpreter(path),
        )

        config_frame = ttk.Frame(self._notebook)
        self._notebook.add(config_frame, text="ZipApps Config")
        self._config_panel = _BuildConfigPanel(config_frame, log_fn=self.log)

        uv_var_config = self._config_panel._vars.get("uv_path")
        uv_var_manager = self._uv_panel._uv_path
        if isinstance(uv_var_config, tk.StringVar):
            _syncing = False

            def _sync_to_config(*_args: object) -> None:
                nonlocal _syncing
                if _syncing:
                    return
                _syncing = True
                uv_var_config.set(uv_var_manager.get())
                _syncing = False

            def _sync_to_manager(*_args: object) -> None:
                nonlocal _syncing
                if _syncing:
                    return
                _syncing = True
                uv_var_manager.set(uv_var_config.get())
                _syncing = False

            uv_var_manager.trace_add("write", _sync_to_config)
            uv_var_config.trace_add("write", _sync_to_manager)

        log_frame = ttk.LabelFrame(self, text="Log", padding=3)
        log_frame.pack(fill="x", padx=5, pady=5)

        log_inner = ttk.Frame(log_frame)
        log_inner.pack(fill="x")

        self._log_text = tk.Text(
            log_inner, height=6, state="disabled", wrap="word", font=("Consolas", 9)
        )
        self._log_text.pack(side="left", fill="x", expand=True)
        log_scroll = ttk.Scrollbar(
            log_inner, orient="vertical", command=self._log_text.yview
        )
        log_scroll.pack(side="right", fill="y")
        self._log_text.configure(yscrollcommand=log_scroll.set)

        ttk.Button(log_frame, text="Clear", command=self._clear_log, width=6).pack(
            side="right", padx=3
        )

        try:
            from zipapps.main import __version__

            version = __version__
        except ImportError:
            version = "unknown"
        self._status_var = tk.StringVar(value=f"Ready | zipapps {version}")
        ttk.Label(
            self, textvariable=self._status_var, relief="sunken", anchor="w"
        ).pack(fill="x", side="bottom")

    def log(self, message: str) -> None:
        _log_to(self._log_text, message)

    def _clear_log(self) -> None:
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", tk.END)
        self._log_text.configure(state="disabled")


if __name__ == "__main__":
    app = ZipAppsGUI()
    app.mainloop()
