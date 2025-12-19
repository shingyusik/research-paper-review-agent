import argparse
import json
import logging
import os
import threading
import queue
from pathlib import Path
from typing import Dict, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from ..core.agent import run_agent
from ..models.schemas import Settings
from ..services.config_service import load_env, set_config
from ..utils.logger import setup_logger


LANG_OPTIONS = ["ko", "en", "ja", "zh", "de", "fr", "es", "pt", "ru"]
PAPER_TYPE_OPTIONS = ["auto", "standard", "review"]
MODEL_OPTIONS = ["openai:gpt-4o-mini", "openai:gpt-4o"]
MODEL_DEFAULT_SENTINEL = "Use default model"
DEFAULT_INPUT_REL = Path("PDF") / "sample_01" / "2508.19205v1.pdf"
DEFAULT_OUTPUT_REL = Path("PDF") / "sample_01"
DEFAULT_KEYWORD_REL = Path("config") / "keywords.json"
MODEL_RATINGS = {
    "openai:gpt-4o-mini": {"speed": 4, "price": 4},
    "openai:gpt-4o": {"speed": 2, "price": 2},
}
MODEL_RATING_MAX = 5

NODE_FIELDS = [
    "extract_title",
    "extract_abstract",
    "extract_conclusion",
    "extract_basic_info",
    "extract_keywords",
    "extract_sections",
    "detect_paper_type",
    "extract_dynamic_sections",
    "analize_background",
    "analize_research_purpose",
    "analize_methodologies",
    "analize_result",
    "analize_identify_keypoints",
    "analyze_dynamic_section",
    "translate_analysis",
]


class SafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "name_short"):
            record.name_short = record.name
        return super().format(record)


class TkLogHandler(logging.Handler):
    def __init__(self, log_queue: "queue.Queue[str]") -> None:
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        self.log_queue.put(msg)


class ReviewAgentApp(tk.Tk):
    def __init__(self, initial_config_path: Optional[str] = None) -> None:
        super().__init__()
        self.title("Research Paper Review Agent")
        self.minsize(1080, 720)
        self.configure(bg="#f6f2ea")

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.ui_queue: "queue.Queue[tuple]" = queue.Queue()
        self.log_handler: Optional[TkLogHandler] = None

        default_input = str(Path.cwd() / DEFAULT_INPUT_REL)
        default_output = str(Path.cwd() / DEFAULT_OUTPUT_REL)
        default_keyword = str(Path.cwd() / DEFAULT_KEYWORD_REL)
        self.vars = {
            "input_path": tk.StringVar(value=default_input),
            "output_path": tk.StringVar(value=default_output),
            "keyword_file_path": tk.StringVar(value=default_keyword),
            "target_language": tk.StringVar(value="ko"),
            "max_analysis_length": tk.IntVar(value=1000),
            "paper_type": tk.StringVar(value="auto"),
            "default_model": tk.StringVar(value="openai:gpt-4o-mini"),
        }
        self.node_vars: Dict[str, tk.StringVar] = {
            name: tk.StringVar(value="") for name in NODE_FIELDS
        }
        self.model_options = list(MODEL_OPTIONS)
        self.model_dropdowns: Dict[str, ttk.Combobox] = {}
        self.default_model_dropdown: Optional[ttk.Combobox] = None

        self._configure_style()
        self._build_layout()
        self._bind_preview_updates()
        self._attach_logging()
        self._poll_queues()

        load_env()
        if initial_config_path:
            self._load_config_file(initial_config_path)
        else:
            sample_path = Path(__file__).resolve().parents[2] / "config" / "settings-sample.json"
            if sample_path.exists():
                self._load_config_file(str(sample_path))

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background="#f6f2ea")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Header.TLabel", background="#f6f2ea", font=("Segoe UI Semibold", 18))
        style.configure("Subheader.TLabel", background="#f6f2ea", foreground="#4f4b45", font=("Segoe UI", 11))
        style.configure("TLabel", background="#ffffff", foreground="#2b2a28", font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#6b655d")
        style.configure("TButton", font=("Segoe UI Semibold", 10))
        style.configure("Accent.TButton", background="#2f6b4f", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#275d44")])
        style.configure("TEntry", fieldbackground="#f7f4f0", foreground="#2b2a28")
        style.configure("TCombobox", fieldbackground="#f7f4f0")

    def _build_layout(self) -> None:
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Research Paper Review Agent", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Product-ready LangGraph pipeline control center",
            style="Subheader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))
        body.columnconfigure(0, weight=3, uniform="col")
        body.columnconfigure(1, weight=2, uniform="col")
        body.rowconfigure(0, weight=1)

        settings_card = ttk.Frame(body, style="Card.TFrame")
        settings_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        settings_card.columnconfigure(0, weight=1)
        settings_card.rowconfigure(1, weight=1)

        ttk.Label(settings_card, text="Settings", font=("Segoe UI Semibold", 12)).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6)
        )

        notebook = ttk.Notebook(settings_card)
        notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        self._build_general_tab(notebook)
        self._build_llm_tab(notebook)
        self._build_models_tab(notebook)
        self._build_advanced_tab(notebook)

        right_card = ttk.Frame(body, style="Card.TFrame")
        right_card.grid(row=0, column=1, sticky="nsew")
        right_card.columnconfigure(0, weight=1)
        right_card.rowconfigure(3, weight=1)

        ttk.Label(right_card, text="Run & Monitor", font=("Segoe UI Semibold", 12)).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6)
        )

        status_frame = ttk.Frame(right_card, style="Card.TFrame")
        status_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        status_frame.columnconfigure(1, weight=1)

        ttk.Label(status_frame, text="Status", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", padx=6, pady=6
        )
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).grid(
            row=0, column=1, sticky="w", padx=6, pady=6
        )

        self.progress = ttk.Progressbar(right_card, mode="indeterminate")
        self.progress.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))

        log_frame = ttk.Frame(right_card, style="Card.TFrame")
        log_frame.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 12))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)
        ttk.Label(log_frame, text="Live Log", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", padx=6, pady=6
        )
        self.log_text = ScrolledText(
            log_frame,
            height=12,
            wrap="word",
            font=("Consolas", 9),
            bg="#0f1412",
            fg="#d6e0d5",
            insertbackground="#d6e0d5",
            relief="flat",
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.log_text.configure(state="disabled")

        button_row = ttk.Frame(right_card, style="Card.TFrame")
        button_row.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        button_row.columnconfigure(2, weight=1)

        self.run_button = ttk.Button(button_row, text="Run Analysis", style="Accent.TButton", command=self._run)
        self.run_button.grid(row=0, column=0, sticky="ew", padx=4, pady=6)

        ttk.Button(button_row, text="Clear Log", command=self._clear_log).grid(
            row=0, column=1, sticky="ew", padx=4, pady=6
        )
        ttk.Button(button_row, text="Open Output", command=self._open_output).grid(
            row=0, column=2, sticky="ew", padx=4, pady=6
        )

        toolbar = ttk.Frame(settings_card, style="Card.TFrame")
        toolbar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        toolbar.columnconfigure(2, weight=1)

        ttk.Button(toolbar, text="Load Config", command=self._prompt_load).grid(
            row=0, column=0, padx=4, pady=6
        )
        ttk.Button(toolbar, text="Save Config As", command=self._prompt_save).grid(
            row=0, column=1, padx=4, pady=6
        )
        ttk.Button(toolbar, text="Use Sample", command=self._load_sample).grid(
            row=0, column=2, padx=4, pady=6, sticky="w"
        )

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

    def _build_general_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, style="Card.TFrame")
        frame.columnconfigure(1, weight=1)
        notebook.add(frame, text="General")

        row = 0
        row = self._add_path_row(frame, row, "Input PDF", "input_path", filetypes=[("PDF files", "*.pdf")])
        row = self._add_path_row(frame, row, "Output Folder", "output_path", is_dir=True)
        row = self._add_path_row(frame, row, "Keyword JSON", "keyword_file_path", filetypes=[("JSON files", "*.json")])

        ttk.Label(frame, text="Target Language").grid(row=row, column=0, sticky="w", padx=16, pady=8)
        ttk.Combobox(frame, textvariable=self.vars["target_language"], values=LANG_OPTIONS, state="readonly").grid(
            row=row, column=1, sticky="ew", padx=16, pady=8
        )
        row += 1

        ttk.Label(frame, text="Max Analysis Length").grid(row=row, column=0, sticky="w", padx=16, pady=8)
        ttk.Spinbox(
            frame,
            from_=200,
            to=5000,
            increment=50,
            textvariable=self.vars["max_analysis_length"],
        ).grid(row=row, column=1, sticky="ew", padx=16, pady=8)
        row += 1

        ttk.Label(frame, text="Paper Type").grid(row=row, column=0, sticky="w", padx=16, pady=8)
        ttk.Combobox(frame, textvariable=self.vars["paper_type"], values=PAPER_TYPE_OPTIONS, state="readonly").grid(
            row=row, column=1, sticky="ew", padx=16, pady=8
        )
        row += 1

        ttk.Label(frame, text="Default LLM Model").grid(row=row, column=0, sticky="w", padx=16, pady=8)
        self.default_model_dropdown = self._add_model_selector(
            frame,
            row,
            self.vars["default_model"],
            allow_default=False,
        )
        row += 1

    def _build_llm_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, style="Card.TFrame")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        notebook.add(frame, text="LLM Models")

        canvas = tk.Canvas(frame, borderwidth=0, background="#ffffff", highlightthickness=0)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas, style="Card.TFrame")

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        for idx, node in enumerate(NODE_FIELDS):
            ttk.Label(inner, text=node).grid(row=idx, column=0, sticky="w", padx=16, pady=6)
            self.model_dropdowns[node] = self._add_model_selector(
                inner,
                idx,
                self.node_vars[node],
                allow_default=True,
            )
            inner.columnconfigure(1, weight=1)

    def _build_advanced_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, style="Card.TFrame")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        notebook.add(frame, text="Advanced")

        ttk.Label(frame, text="Config Preview", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 4)
        )
        self.preview_text = ScrolledText(
            frame,
            height=12,
            wrap="word",
            font=("Consolas", 9),
            bg="#f7f4f0",
            relief="flat",
        )
        self.preview_text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.preview_text.configure(state="disabled")

    def _bind_preview_updates(self) -> None:
        def _refresh(*_args: object) -> None:
            self._update_preview(self._build_config_dict())

        for var in self.vars.values():
            var.trace_add("write", _refresh)
        for var in self.node_vars.values():
            var.trace_add("write", _refresh)

        _refresh()

    def _build_models_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook, style="Card.TFrame")
        frame.columnconfigure(0, weight=1)
        notebook.add(frame, text="Models")

        ttk.Label(frame, text="Model Info", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 6)
        )
        ttk.Label(frame, text="Speed: ■■■■■ = fast", style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", padx=16
        )
        ttk.Label(frame, text="Price: ■■■■■ = low cost", style="Muted.TLabel").grid(
            row=2, column=0, sticky="w", padx=16, pady=(0, 8)
        )

        table = ttk.Frame(frame, style="Card.TFrame")
        table.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 16))
        table.columnconfigure(0, weight=2)
        table.columnconfigure(1, weight=1)
        table.columnconfigure(2, weight=1)

        ttk.Label(table, text="Model", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 6)
        )
        ttk.Label(table, text="Speed", style="Muted.TLabel").grid(
            row=0, column=1, sticky="w", padx=(0, 12), pady=(0, 6)
        )
        ttk.Label(table, text="Price", style="Muted.TLabel").grid(
            row=0, column=2, sticky="w", padx=(0, 12), pady=(0, 6)
        )

        for idx, model in enumerate(self.model_options, start=1):
            ratings = MODEL_RATINGS.get(model, {})
            speed = self._rating_bar(ratings.get("speed"))
            price = self._rating_bar(ratings.get("price"))
            ttk.Label(table, text=model).grid(row=idx, column=0, sticky="w", padx=(0, 12), pady=4)
            ttk.Label(table, text=speed).grid(row=idx, column=1, sticky="w", padx=(0, 12), pady=4)
            ttk.Label(table, text=price).grid(row=idx, column=2, sticky="w", padx=(0, 12), pady=4)

    def _rating_bar(self, value: Optional[int]) -> str:
        if not value:
            return "N/A"
        value = max(0, min(value, MODEL_RATING_MAX))
        return "■" * value + "□" * (MODEL_RATING_MAX - value)

    def _add_path_row(
        self,
        frame: ttk.Frame,
        row: int,
        label: str,
        var_key: str,
        is_dir: bool = False,
        filetypes: Optional[list] = None,
    ) -> int:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=16, pady=8)
        ttk.Entry(frame, textvariable=self.vars[var_key]).grid(
            row=row, column=1, sticky="ew", padx=(16, 6), pady=8
        )
        ttk.Button(
            frame,
            text="Browse",
            command=lambda: self._browse_path(var_key, is_dir, filetypes),
        ).grid(row=row, column=2, sticky="e", padx=(0, 16), pady=8)
        frame.columnconfigure(1, weight=1)
        return row + 1

    def _add_model_selector(
        self,
        frame: ttk.Frame,
        row: int,
        var: tk.StringVar,
        allow_default: bool,
    ) -> ttk.Combobox:
        current = var.get().strip()
        if allow_default and not current:
            var.set(MODEL_DEFAULT_SENTINEL)
        else:
            self._ensure_model_option(current)
        values = self._model_values(allow_default=allow_default)
        combo = ttk.Combobox(frame, textvariable=var, values=values, state="readonly")
        combo.grid(row=row, column=1, sticky="ew", padx=16, pady=6)
        return combo

    def _ensure_model_option(self, value: str) -> None:
        if value and value not in self.model_options:
            self.model_options.append(value)

    def _model_values(self, allow_default: bool) -> list[str]:
        if allow_default:
            return [MODEL_DEFAULT_SENTINEL, *self.model_options]
        return list(self.model_options)

    def _refresh_model_dropdowns(self) -> None:
        if self.default_model_dropdown:
            self.default_model_dropdown.configure(values=self._model_values(allow_default=False))
        for combo in self.model_dropdowns.values():
            combo.configure(values=self._model_values(allow_default=True))

    def _browse_path(self, var_key: str, is_dir: bool, filetypes: Optional[list]) -> None:
        initial_dir = self.vars[var_key].get().strip() or str(Path.cwd())
        if is_dir:
            path = filedialog.askdirectory(initialdir=initial_dir)
        else:
            path = filedialog.askopenfilename(
                filetypes=filetypes or [("All files", "*.*")],
                initialdir=initial_dir,
            )
        if path:
            self.vars[var_key].set(path)

    def _attach_logging(self) -> None:
        log_level = "INFO"
        setup_logger(log_level)
        logger = logging.getLogger("research_paper_review_agent")
        if self.log_handler:
            logger.removeHandler(self.log_handler)
        self.log_handler = TkLogHandler(self.log_queue)
        self.log_handler.setLevel(getattr(logging, log_level, logging.INFO))
        formatter = SafeFormatter(
            "[%(asctime)s] %(levelname)-8s | %(name_short)-16s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.log_handler.setFormatter(formatter)
        logger.addHandler(self.log_handler)

    def _poll_queues(self) -> None:
        while not self.log_queue.empty():
            message = self.log_queue.get_nowait()
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.configure(state="disabled")
            self.log_text.see("end")

        while not self.ui_queue.empty():
            event, payload = self.ui_queue.get_nowait()
            if event == "status":
                self.status_var.set(payload)
            elif event == "done":
                self._set_running_state(False)
                if payload:
                    messagebox.showinfo("Complete", "Analysis finished successfully.")
                else:
                    messagebox.showerror("Error", "Analysis failed. Check the log for details.")

        self.after(150, self._poll_queues)

    def _set_running_state(self, running: bool) -> None:
        if running:
            self.status_var.set("Running")
            self.progress.start(8)
            self.run_button.configure(state="disabled")
        else:
            self.status_var.set("Ready")
            self.progress.stop()
            self.run_button.configure(state="normal")

    def _build_config_dict(self) -> dict:
        default_model = self.vars["default_model"].get().strip()
        nodes = {}
        for name, var in self.node_vars.items():
            value = var.get().strip()
            if value in (MODEL_DEFAULT_SENTINEL, default_model):
                value = ""
            if value:
                nodes[name] = value

        config = {
            "input_path": self.vars["input_path"].get().strip(),
            "output_path": self.vars["output_path"].get().strip(),
            "keyword_file_path": self.vars["keyword_file_path"].get().strip() or None,
            "target_language": self.vars["target_language"].get(),
            "max_analysis_length": int(self.vars["max_analysis_length"].get()),
            "paper_type": self.vars["paper_type"].get(),
            "llm": {
                "default_model": default_model,
                "nodes": nodes,
            },
        }
        return config

    def _update_preview(self, config: dict) -> None:
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", json.dumps(config, indent=4))
        self.preview_text.configure(state="disabled")

    def _validate_settings(self, config: dict) -> Optional[Settings]:
        try:
            settings = Settings(**config)
        except Exception as exc:
            messagebox.showerror("Invalid Settings", str(exc))
            return None

        if not Path(settings.input_path).exists():
            messagebox.showerror("Invalid Path", "Input PDF file does not exist.")
            return None
        return settings

    def _run(self) -> None:
        self._attach_logging()
        config = self._build_config_dict()
        self._update_preview(config)
        settings = self._validate_settings(config)
        if not settings:
            return

        self._set_running_state(True)
        worker = threading.Thread(target=self._run_worker, args=(settings,), daemon=True)
        worker.start()

    def _run_worker(self, settings: Settings) -> None:
        try:
            set_config(settings)
            run_agent(settings)
            self.ui_queue.put(("done", True))
        except Exception:
            logging.getLogger("research_paper_review_agent").exception("GUI run failed")
            self.ui_queue.put(("done", False))

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _open_output(self) -> None:
        output_path = self.vars["output_path"].get().strip()
        if not output_path:
            messagebox.showinfo("Output Folder", "Set an output folder first.")
            return
        path = Path(output_path)
        if path.is_file():
            path = path.parent
        if path.exists():
            os.startfile(path)
        else:
            messagebox.showerror("Output Folder", "Output folder does not exist.")

    def _prompt_load(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            initialdir=str(Path.cwd()),
        )
        if path:
            self._load_config_file(path)

    def _prompt_save(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialdir=str(Path.cwd()),
        )
        if path:
            config = self._build_config_dict()
            self._update_preview(config)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Config Saved", f"Saved to {path}")

    def _load_sample(self) -> None:
        sample_path = Path(__file__).resolve().parents[2] / "config" / "settings-sample.json"
        if sample_path.exists():
            self._load_config_file(str(sample_path))
        else:
            messagebox.showerror("Missing Sample", "settings-sample.json was not found.")

    def _load_config_file(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as exc:
            messagebox.showerror("Load Failed", str(exc))
            return

        self.vars["input_path"].set(config.get("input_path", str(Path.cwd() / DEFAULT_INPUT_REL)))
        self.vars["output_path"].set(config.get("output_path", str(Path.cwd() / DEFAULT_OUTPUT_REL)))
        self.vars["keyword_file_path"].set(
            config.get("keyword_file_path", str(Path.cwd() / DEFAULT_KEYWORD_REL)) or ""
        )
        self.vars["target_language"].set(config.get("target_language", "ko"))
        self.vars["max_analysis_length"].set(int(config.get("max_analysis_length", 1000)))
        self.vars["paper_type"].set(config.get("paper_type", "auto"))
        llm = config.get("llm", {})
        default_model = llm.get("default_model", "openai:gpt-4o-mini")
        self._ensure_model_option(default_model)
        self.vars["default_model"].set(default_model)

        nodes = llm.get("nodes", {})
        for name in NODE_FIELDS:
            node_model = nodes.get(name, "")
            if node_model and node_model != default_model:
                self._ensure_model_option(node_model)
                self.node_vars[name].set(node_model)
            else:
                self.node_vars[name].set(MODEL_DEFAULT_SENTINEL)

        self._refresh_model_dropdowns()
        self._update_preview(self._build_config_dict())


def run_gui(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Research paper review GUI")
    parser.add_argument("-c", "--config", type=str, default=None, help="Path to config.json")
    args = parser.parse_args(argv)

    app = ReviewAgentApp(initial_config_path=args.config)
    app.mainloop()
