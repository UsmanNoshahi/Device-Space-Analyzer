import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import subprocess
import threading
import hashlib
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import time
import pickle

# Try to import optional libraries
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

try:
    import squarify
    HAS_SQUARIFY = True
except ImportError:
    HAS_SQUARIFY = False


# Microsoft Fluent Design inspired color scheme
class FluentColors:
    # Light, modern color palette (like Microsoft Office, VS Code)
    PRIMARY = "#0078D4"  # Microsoft Blue
    PRIMARY_HOVER = "#106EBE"
    PRIMARY_PRESSED = "#005A9E"

    ACCENT = "#8764B8"  # Purple accent
    SUCCESS = "#107C10"  # Green
    WARNING = "#FF8C00"  # Orange
    ERROR = "#D13438"  # Red
    INFO = "#0099BC"  # Teal

    # Neutral palette (light theme)
    BG_PRIMARY = "#FFFFFF"  # Pure white
    BG_SECONDARY = "#F3F2F1"  # Light gray
    BG_TERTIARY = "#FAFAFA"  # Off-white

    SURFACE = "#FFFFFF"
    SURFACE_SECONDARY = "#FAF9F8"

    TEXT_PRIMARY = "#323130"  # Dark gray (not pure black)
    TEXT_SECONDARY = "#605E5C"  # Medium gray
    TEXT_TERTIARY = "#8A8886"  # Light gray
    TEXT_DISABLED = "#C8C6C4"

    BORDER_LIGHT = "#EDEBE9"
    BORDER_MEDIUM = "#D2D0CE"
    BORDER_STRONG = "#8A8886"

    # Card colors
    CARD_BG = "#FFFFFF"
    CARD_HOVER = "#F3F2F1"
    CARD_BORDER = "#E1DFDD"

    # Accent colors for data visualization
    CHART_BLUE = "#0078D4"
    CHART_GREEN = "#107C10"
    CHART_ORANGE = "#FF8C00"
    CHART_PURPLE = "#8764B8"
    CHART_TEAL = "#0099BC"
    CHART_RED = "#D13438"
    CHART_YELLOW = "#FFB900"


class FluentButton(tk.Button):
    """Microsoft Fluent Design inspired button"""
    def __init__(self, parent, text, command=None, style="primary", **kwargs):
        self.style_type = style

        # Define styles
        if style == "primary":
            bg = FluentColors.PRIMARY
            fg = "#FFFFFF"
            active_bg = FluentColors.PRIMARY_HOVER
        elif style == "success":
            bg = FluentColors.SUCCESS
            fg = "#FFFFFF"
            active_bg = "#0E6B0E"
        elif style == "danger":
            bg = FluentColors.ERROR
            fg = "#FFFFFF"
            active_bg = "#A72929"
        elif style == "warning":
            bg = FluentColors.WARNING
            fg = "#FFFFFF"
            active_bg = "#D97500"
        elif style == "secondary":
            bg = FluentColors.BG_SECONDARY
            fg = FluentColors.TEXT_PRIMARY
            active_bg = FluentColors.BORDER_LIGHT
        else:
            bg = FluentColors.PRIMARY
            fg = "#FFFFFF"
            active_bg = FluentColors.PRIMARY_HOVER

        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief=tk.FLAT,
            borderwidth=0,
            padx=20,
            pady=8,
            font=("Segoe UI", 10),
            cursor="hand2",
            **kwargs
        )

        # Bind hover events
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        self.default_bg = bg
        self.hover_bg = active_bg

    def _on_enter(self, e):
        self['background'] = self.hover_bg

    def _on_leave(self, e):
        self['background'] = self.default_bg


class FluentCard(tk.Frame):
    """Fluent Design card with elevation"""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=FluentColors.CARD_BG,
            relief=tk.FLAT,
            **kwargs
        )
        # Add subtle border
        self.config(
            highlightbackground=FluentColors.CARD_BORDER,
            highlightthickness=1
        )


class SpaceScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Disk Space Scanner Pro")
        self.root.geometry("1600x900")
        self.root.configure(bg=FluentColors.BG_SECONDARY)

        # Data storage
        self.files_data = []
        self.filtered_data = []
        self.folders_data = {}
        self.duplicates_data = {}
        self.scan_history = []
        self.all_drives_data = {}

        # Scanning state
        self.scanning = False
        self.scan_paused = False
        self.scan_cancelled = False
        self.scan_thread = None

        # UI settings
        self.sort_column = None
        self.sort_reverse = True

        # Settings files
        self.settings_file = "scanner_settings.json"
        self.history_file = "scan_history.pkl"

        # Load settings
        self.load_settings()
        self.load_scan_history()

        # Configure styles
        self.configure_fluent_styles()

        # Setup UI
        self.setup_ui()
        self.load_drives()

        # Restore last drive
        if hasattr(self, 'last_drive') and self.last_drive:
            self.drive_var.set(self.last_drive)

    def configure_fluent_styles(self):
        """Configure Fluent Design styles"""
        style = ttk.Style()

        try:
            style.theme_use('clam')
        except:
            pass

        # Notebook (tabs)
        style.configure(
            'Fluent.TNotebook',
            background=FluentColors.BG_SECONDARY,
            borderwidth=0
        )
        style.configure(
            'Fluent.TNotebook.Tab',
            background=FluentColors.SURFACE,
            foreground=FluentColors.TEXT_SECONDARY,
            padding=[20, 12],
            font=('Segoe UI', 10),
            borderwidth=0
        )
        style.map(
            'Fluent.TNotebook.Tab',
            background=[('selected', FluentColors.PRIMARY)],
            foreground=[('selected', '#FFFFFF')]
        )

        # Treeview
        style.configure(
            'Fluent.Treeview',
            background=FluentColors.SURFACE,
            foreground=FluentColors.TEXT_PRIMARY,
            fieldbackground=FluentColors.SURFACE,
            borderwidth=0,
            font=('Segoe UI', 9)
        )
        style.configure(
            'Fluent.Treeview.Heading',
            background=FluentColors.BG_SECONDARY,
            foreground=FluentColors.TEXT_PRIMARY,
            borderwidth=1,
            relief=tk.FLAT,
            font=('Segoe UI', 10, 'bold')
        )
        style.map(
            'Fluent.Treeview',
            background=[('selected', FluentColors.PRIMARY)],
            foreground=[('selected', '#FFFFFF')]
        )

        # Progressbar
        style.configure(
            'Fluent.Horizontal.TProgressbar',
            background=FluentColors.PRIMARY,
            troughcolor=FluentColors.BG_SECONDARY,
            borderwidth=0,
            thickness=4
        )

        # Combobox
        style.configure(
            'Fluent.TCombobox',
            background=FluentColors.SURFACE,
            foreground=FluentColors.TEXT_PRIMARY,
            fieldbackground=FluentColors.SURFACE,
            borderwidth=1,
            relief=tk.FLAT
        )

    def setup_ui(self):
        """Setup the modern Fluent UI"""
        # Header
        self.create_header()

        # Main container
        main_container = tk.Frame(self.root, bg=FluentColors.BG_SECONDARY)
        main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Notebook for tabs
        self.notebook = ttk.Notebook(main_container, style='Fluent.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 20))

        # Create tabs
        self.files_tab = tk.Frame(self.notebook, bg=FluentColors.BG_SECONDARY)
        self.notebook.add(self.files_tab, text="  📁 Files  ")
        self.setup_files_tab()

        self.folders_tab = tk.Frame(self.notebook, bg=FluentColors.BG_SECONDARY)
        self.notebook.add(self.folders_tab, text="  📂 Folders  ")
        self.setup_folders_tab()

        self.duplicates_tab = tk.Frame(self.notebook, bg=FluentColors.BG_SECONDARY)
        self.notebook.add(self.duplicates_tab, text="  🔄 Duplicates  ")
        self.setup_duplicates_tab()

        self.file_finder_tab = tk.Frame(self.notebook, bg=FluentColors.BG_SECONDARY)
        self.notebook.add(self.file_finder_tab, text="  🔍 File Finder  ")
        self.setup_file_finder_tab()

        self.network_admin_tab = tk.Frame(self.notebook, bg=FluentColors.BG_SECONDARY)
        self.notebook.add(self.network_admin_tab, text="  🌐 Network Admin  ")
        self.setup_network_admin_tab()

        if HAS_MATPLOTLIB:
            self.viz_tab = tk.Frame(self.notebook, bg=FluentColors.BG_SECONDARY)
            self.notebook.add(self.viz_tab, text="  📊 Charts  ")
            self.setup_viz_tab()

        self.trends_tab = tk.Frame(self.notebook, bg=FluentColors.BG_SECONDARY)
        self.notebook.add(self.trends_tab, text="  📈 Trends  ")
        self.setup_trends_tab()

        self.comparison_tab = tk.Frame(self.notebook, bg=FluentColors.BG_SECONDARY)
        self.notebook.add(self.comparison_tab, text="  💽 Drives  ")
        self.setup_comparison_tab()

        self.reports_tab = tk.Frame(self.notebook, bg=FluentColors.BG_SECONDARY)
        self.notebook.add(self.reports_tab, text="  📑 Reports  ")
        self.setup_reports_tab()

        if HAS_MATPLOTLIB and HAS_SQUARIFY:
            self.heatmap_tab = tk.Frame(self.notebook, bg=FluentColors.BG_SECONDARY)
            self.notebook.add(self.heatmap_tab, text="  🗺️ Heatmap  ")
            self.setup_heatmap_tab()

        # Status bar
        self.create_statusbar()

    def create_header(self):
        """Create modern header"""
        header = tk.Frame(self.root, bg=FluentColors.PRIMARY, height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Title section
        title_frame = tk.Frame(header, bg=FluentColors.PRIMARY)
        title_frame.pack(side=tk.LEFT, padx=30, pady=20)

        tk.Label(
            title_frame,
            text="💾 Disk Space Scanner Pro",
            bg=FluentColors.PRIMARY,
            fg="#FFFFFF",
            font=("Segoe UI", 20, "bold")
        ).pack(anchor=tk.W)

        tk.Label(
            title_frame,
            text="Modern storage management and analytics",
            bg=FluentColors.PRIMARY,
            fg="#E0E0E0",
            font=("Segoe UI", 10)
        ).pack(anchor=tk.W)

        # Version badge
        badge_frame = tk.Frame(header, bg=FluentColors.PRIMARY)
        badge_frame.pack(side=tk.RIGHT, padx=30)

        tk.Label(
            badge_frame,
            text="v4.0",
            bg="#FFFFFF",
            fg=FluentColors.PRIMARY,
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=6
        ).pack()

    def create_statusbar(self):
        """Create modern status bar"""
        statusbar = tk.Frame(self.root, bg=FluentColors.SURFACE, height=40)
        statusbar.pack(fill=tk.X, side=tk.BOTTOM)
        statusbar.pack_propagate(False)

        # Add separator line
        separator = tk.Frame(statusbar, bg=FluentColors.BORDER_LIGHT, height=1)
        separator.pack(fill=tk.X)

        content = tk.Frame(statusbar, bg=FluentColors.SURFACE)
        content.pack(fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(
            content,
            text="Ready",
            bg=FluentColors.SURFACE,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 9),
            anchor=tk.W,
            padx=20
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_icon = tk.Label(
            content,
            text="●",
            bg=FluentColors.SURFACE,
            fg=FluentColors.SUCCESS,
            font=("Segoe UI", 14)
        )
        self.status_icon.pack(side=tk.RIGHT, padx=20)

    def setup_files_tab(self):
        """Setup files tab with Fluent Design"""
        container = tk.Frame(self.files_tab, bg=FluentColors.BG_SECONDARY)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Control card
        control_card = FluentCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        # Controls
        controls = tk.Frame(control_card, bg=FluentColors.CARD_BG)
        controls.pack(fill=tk.X, padx=20, pady=15)

        # Row 1: Drive selection and scan
        row1 = tk.Frame(controls, bg=FluentColors.CARD_BG)
        row1.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            row1,
            text="Drive:",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.drive_var = tk.StringVar()
        self.drive_combo = ttk.Combobox(
            row1,
            textvariable=self.drive_var,
            width=15,
            state="readonly",
            style='Fluent.TCombobox',
            font=("Segoe UI", 10)
        )
        self.drive_combo.pack(side=tk.LEFT, padx=(0, 15))

        FluentButton(row1, "🚀 Scan", self.start_scan, "primary").pack(side=tk.LEFT, padx=3)
        FluentButton(row1, "⏸ Pause", self.pause_scan, "warning").pack(side=tk.LEFT, padx=3)
        FluentButton(row1, "❌ Cancel", self.cancel_scan, "danger").pack(side=tk.LEFT, padx=3)

        # Progress
        progress_frame = tk.Frame(row1, bg=FluentColors.CARD_BG)
        progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(20, 0))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='indeterminate',
            variable=self.progress_var,
            style='Fluent.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = tk.Label(
            progress_frame,
            text="Ready to scan",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_TERTIARY,
            font=("Segoe UI", 9)
        )
        self.progress_label.pack()

        # Row 2: Filters
        row2 = tk.Frame(controls, bg=FluentColors.CARD_BG)
        row2.pack(fill=tk.X, pady=(5, 0))

        tk.Label(
            row2,
            text="Search:",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.apply_filters)
        search_entry = tk.Entry(
            row2,
            textvariable=self.search_var,
            width=25,
            bg=FluentColors.SURFACE,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 9),
            relief=tk.SOLID,
            bd=1,
            highlightthickness=0,
            insertbackground=FluentColors.TEXT_PRIMARY
        )
        search_entry.pack(side=tk.LEFT, padx=(0, 15), ipady=4)

        tk.Label(
            row2,
            text="Type:",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.file_type_var = tk.StringVar(value="All")
        type_combo = ttk.Combobox(
            row2,
            textvariable=self.file_type_var,
            values=["All", "Videos", "Images", "Documents", "Audio", "Archives", "Executables", "Other"],
            width=12,
            state="readonly",
            style='Fluent.TCombobox',
            font=("Segoe UI", 9)
        )
        type_combo.pack(side=tk.LEFT, padx=(0, 15))
        type_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        tk.Label(
            row2,
            text="Min MB:",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.min_size_var = tk.StringVar(value="0")
        size_entry = tk.Entry(
            row2,
            textvariable=self.min_size_var,
            width=10,
            bg=FluentColors.SURFACE,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 9),
            relief=tk.SOLID,
            bd=1,
            insertbackground=FluentColors.TEXT_PRIMARY
        )
        size_entry.pack(side=tk.LEFT, padx=(0, 15), ipady=4)
        size_entry.bind('<KeyRelease>', lambda e: self.apply_filters())

        # Smart filters
        tk.Label(
            row2,
            text="Not accessed (days):",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(15, 8))

        self.access_days_var = tk.StringVar(value="0")
        tk.Entry(
            row2,
            textvariable=self.access_days_var,
            width=6,
            bg=FluentColors.SURFACE,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 9),
            relief=tk.SOLID,
            bd=1
        ).pack(side=tk.LEFT, padx=(0, 15), ipady=4)
        self.access_days_var.trace('w', lambda *args: self.apply_filters())

        FluentButton(row2, "Clear", self.clear_filters, "secondary").pack(side=tk.LEFT, padx=(10, 0))

        # Data card
        data_card = FluentCard(container)
        data_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        tree_container = tk.Frame(data_card, bg=FluentColors.SURFACE)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")

        self.tree = ttk.Treeview(
            tree_container,
            columns=("Size", "Readable", "Type", "Modified", "Accessed", "Path"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode="extended",
            style='Fluent.Treeview'
        )

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        columns = [
            ("Size", "Size (Bytes)", 100),
            ("Readable", "Size", 100),
            ("Type", "Type", 100),
            ("Modified", "Modified", 140),
            ("Accessed", "Accessed", 140),
            ("Path", "Path", 700)
        ]

        for col, heading, width in columns:
            self.tree.heading(col, text=heading, command=lambda c=col: self.sort_tree_column(c))
            self.tree.column(col, width=width, anchor="w" if col == "Path" else "e")

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.create_context_menu()
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", lambda e: self.open_file_location())

        # Action card
        action_card = FluentCard(container)
        action_card.pack(fill=tk.X)

        actions = tk.Frame(action_card, bg=FluentColors.CARD_BG)
        actions.pack(padx=20, pady=15)

        FluentButton(actions, "📍 Open Location", self.open_file_location, "primary").pack(side=tk.LEFT, padx=5)
        if HAS_SEND2TRASH:
            FluentButton(actions, "🗑 Delete", self.delete_files, "danger").pack(side=tk.LEFT, padx=5)
        FluentButton(actions, "ℹ Properties", self.show_file_properties, "secondary").pack(side=tk.LEFT, padx=5)

    def setup_folders_tab(self):
        """Setup folders tab"""
        container = tk.Frame(self.folders_tab, bg=FluentColors.BG_SECONDARY)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        control_card = FluentCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        controls = tk.Frame(control_card, bg=FluentColors.CARD_BG)
        controls.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            controls,
            text="📂 Folder Space Analysis",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)

        FluentButton(controls, "🔍 Analyze", self.analyze_folders, "primary").pack(side=tk.LEFT, padx=20)

        data_card = FluentCard(container)
        data_card.pack(fill=tk.BOTH, expand=True)

        tree_container = tk.Frame(data_card, bg=FluentColors.SURFACE)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")

        self.folder_tree = ttk.Treeview(
            tree_container,
            columns=("Size", "Readable", "Files", "Path"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            style='Fluent.Treeview'
        )

        vsb.config(command=self.folder_tree.yview)
        hsb.config(command=self.folder_tree.xview)

        self.folder_tree.heading("Size", text="Size (Bytes)")
        self.folder_tree.heading("Readable", text="Size")
        self.folder_tree.heading("Files", text="Files")
        self.folder_tree.heading("Path", text="Path")

        self.folder_tree.column("Size", width=120, anchor="e")
        self.folder_tree.column("Readable", width=120, anchor="e")
        self.folder_tree.column("Files", width=100, anchor="e")
        self.folder_tree.column("Path", width=800, anchor="w")

        self.folder_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

    def setup_duplicates_tab(self):
        """Setup duplicates tab"""
        container = tk.Frame(self.duplicates_tab, bg=FluentColors.BG_SECONDARY)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        control_card = FluentCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        controls = tk.Frame(control_card, bg=FluentColors.CARD_BG)
        controls.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            controls,
            text="🔄 Duplicate Detection",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)

        FluentButton(controls, "🔍 Find Duplicates", self.find_duplicates, "warning").pack(side=tk.LEFT, padx=20)

        self.dup_label = tk.Label(
            controls,
            text="No duplicates found",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 10)
        )
        self.dup_label.pack(side=tk.LEFT, padx=20)

        data_card = FluentCard(container)
        data_card.pack(fill=tk.BOTH, expand=True)

        tree_container = tk.Frame(data_card, bg=FluentColors.SURFACE)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")

        self.dup_tree = ttk.Treeview(
            tree_container,
            columns=("Size", "Readable", "Copies", "Path"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode="extended",
            style='Fluent.Treeview'
        )

        vsb.config(command=self.dup_tree.yview)
        hsb.config(command=self.dup_tree.xview)

        self.dup_tree.heading("Size", text="Size (Bytes)")
        self.dup_tree.heading("Readable", text="Size")
        self.dup_tree.heading("Copies", text="Copies")
        self.dup_tree.heading("Path", text="Path")

        self.dup_tree.column("Size", width=120, anchor="e")
        self.dup_tree.column("Readable", width=120, anchor="e")
        self.dup_tree.column("Copies", width=100, anchor="e")
        self.dup_tree.column("Path", width=800, anchor="w")

        self.dup_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

    def setup_file_finder_tab(self):
        """Setup advanced file finder tab"""
        container = tk.Frame(self.file_finder_tab, bg=FluentColors.BG_SECONDARY)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Control card
        control_card = FluentCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        controls_main = tk.Frame(control_card, bg=FluentColors.CARD_BG)
        controls_main.pack(fill=tk.X, padx=20, pady=15)

        # Title
        tk.Label(
            controls_main,
            text="🔍 Advanced File Finder",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(0, 10))

        # Quick preset buttons
        preset_frame = tk.Frame(controls_main, bg=FluentColors.CARD_BG)
        preset_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            preset_frame,
            text="Quick Presets:",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        presets = [
            ("🎬 Videos", [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpeg", ".mpg"]),
            ("🎵 Audio", [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".opus"]),
            ("🖼️ Images", [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg", ".ico"]),
            ("📄 Documents", [".doc", ".docx", ".pdf", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".odt"]),
            ("📦 Archives", [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"]),
            ("💾 Executables", [".exe", ".msi", ".app", ".dmg", ".deb", ".rpm", ".apk"])
        ]

        for preset_name, extensions in presets:
            FluentButton(
                preset_frame,
                preset_name,
                lambda ext=extensions: self.apply_extension_preset(ext),
                "secondary"
            ).pack(side=tk.LEFT, padx=5)

        # Custom extensions input
        custom_frame = tk.Frame(controls_main, bg=FluentColors.CARD_BG)
        custom_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            custom_frame,
            text="Custom Extensions:",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            custom_frame,
            text="(comma-separated, e.g., .xlsx, .csv, .log)",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_TERTIARY,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.custom_extensions_var = tk.StringVar()
        custom_entry = tk.Entry(
            custom_frame,
            textvariable=self.custom_extensions_var,
            bg=FluentColors.SURFACE,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 10),
            relief=tk.SOLID,
            borderwidth=1,
            width=50
        )
        custom_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=5)

        FluentButton(
            custom_frame,
            "🔍 Find Files",
            self.find_by_extensions,
            "primary"
        ).pack(side=tk.LEFT, padx=5)

        FluentButton(
            custom_frame,
            "Clear",
            self.clear_file_finder,
            "secondary"
        ).pack(side=tk.LEFT, padx=5)

        # Statistics frame
        stats_frame = tk.Frame(controls_main, bg=FluentColors.CARD_BG)
        stats_frame.pack(fill=tk.X, pady=(10, 0))

        self.finder_stats_label = tk.Label(
            stats_frame,
            text="No search performed yet",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 10)
        )
        self.finder_stats_label.pack(side=tk.LEFT)

        # Data card with results
        data_card = FluentCard(container)
        data_card.pack(fill=tk.BOTH, expand=True)

        tree_container = tk.Frame(data_card, bg=FluentColors.SURFACE)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")

        self.finder_tree = ttk.Treeview(
            tree_container,
            columns=("Name", "Size", "Readable", "Type", "Modified", "Path"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            selectmode="extended",
            style='Fluent.Treeview'
        )

        vsb.config(command=self.finder_tree.yview)
        hsb.config(command=self.finder_tree.xview)

        self.finder_tree.heading("Name", text="File Name", command=lambda: self.sort_finder_tree("Name"))
        self.finder_tree.heading("Size", text="Size (Bytes)", command=lambda: self.sort_finder_tree("Size"))
        self.finder_tree.heading("Readable", text="Size", command=lambda: self.sort_finder_tree("Readable"))
        self.finder_tree.heading("Type", text="Extension", command=lambda: self.sort_finder_tree("Type"))
        self.finder_tree.heading("Modified", text="Modified Date", command=lambda: self.sort_finder_tree("Modified"))
        self.finder_tree.heading("Path", text="Full Path", command=lambda: self.sort_finder_tree("Path"))

        self.finder_tree.column("Name", width=250, anchor="w")
        self.finder_tree.column("Size", width=120, anchor="e")
        self.finder_tree.column("Readable", width=120, anchor="e")
        self.finder_tree.column("Type", width=100, anchor="w")
        self.finder_tree.column("Modified", width=150, anchor="w")
        self.finder_tree.column("Path", width=600, anchor="w")

        self.finder_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Context menu for finder tree
        self.finder_tree.bind("<Button-3>", self.show_finder_context_menu)
        self.finder_tree.bind("<Double-1>", lambda e: self.open_file_location_finder())

    def setup_network_admin_tab(self):
        """Setup network admin tab for remote server monitoring"""
        container = tk.Frame(self.network_admin_tab, bg=FluentColors.BG_SECONDARY)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Control card
        control_card = FluentCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        controls_main = tk.Frame(control_card, bg=FluentColors.CARD_BG)
        controls_main.pack(fill=tk.X, padx=20, pady=15)

        # Title
        title_frame = tk.Frame(controls_main, bg=FluentColors.CARD_BG)
        title_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            title_frame,
            text="🌐 Network Admin - Remote Server Monitoring",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)

        tk.Label(
            title_frame,
            text="Monitor disk space on remote servers via network share",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(15, 0))

        # Server connection frame
        server_frame = tk.Frame(controls_main, bg=FluentColors.CARD_BG)
        server_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Label(
            server_frame,
            text="Server Address:",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            server_frame,
            text="(IP address or hostname)",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_TERTIARY,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.server_ip_var = tk.StringVar(value="")
        server_entry = tk.Entry(
            server_frame,
            textvariable=self.server_ip_var,
            bg=FluentColors.SURFACE,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 10),
            relief=tk.SOLID,
            borderwidth=1,
            width=30
        )
        server_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=5)

        FluentButton(
            server_frame,
            "🔌 Connect",
            self.connect_to_server,
            "primary"
        ).pack(side=tk.LEFT, padx=5)

        FluentButton(
            server_frame,
            "💻 Scan Local",
            self.scan_local_server,
            "success"
        ).pack(side=tk.LEFT, padx=5)

        # Quick access buttons
        quick_frame = tk.Frame(controls_main, bg=FluentColors.CARD_BG)
        quick_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            quick_frame,
            text="Quick Access:",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Saved servers (will be populated from settings)
        self.saved_servers = tk.StringVar(value="")
        saved_combo = ttk.Combobox(
            quick_frame,
            textvariable=self.saved_servers,
            state="readonly",
            width=30,
            style='Fluent.TCombobox'
        )
        saved_combo.pack(side=tk.LEFT, padx=(0, 10))
        saved_combo['values'] = self.load_saved_servers()

        FluentButton(
            quick_frame,
            "⭐ Save Current",
            self.save_current_server,
            "secondary"
        ).pack(side=tk.LEFT, padx=5)

        FluentButton(
            quick_frame,
            "🗑️ Remove",
            self.remove_saved_server,
            "danger"
        ).pack(side=tk.LEFT, padx=5)

        # Status frame
        status_frame = tk.Frame(controls_main, bg=FluentColors.CARD_BG)
        status_frame.pack(fill=tk.X, pady=(10, 0))

        self.network_status_label = tk.Label(
            status_frame,
            text="🔴 Not connected - Enter server address and click Connect",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 10, "bold")
        )
        self.network_status_label.pack(side=tk.LEFT)

        # Server info card
        info_card = FluentCard(container)
        info_card.pack(fill=tk.X, pady=(0, 15))

        info_frame = tk.Frame(info_card, bg=FluentColors.CARD_BG)
        info_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            info_frame,
            text="📊 Server Information",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 10))

        self.server_info_frame = tk.Frame(info_frame, bg=FluentColors.CARD_BG)
        self.server_info_frame.pack(fill=tk.X)

        self.server_info_text = tk.Text(
            self.server_info_frame,
            bg=FluentColors.SURFACE,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Consolas", 9),
            relief=tk.FLAT,
            borderwidth=1,
            height=8,
            wrap=tk.WORD
        )
        self.server_info_text.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.server_info_text.insert("1.0", "No server connected. Enter IP address and click Connect to view server information.")
        self.server_info_text.config(state=tk.DISABLED)

        # Drives data card
        drives_card = FluentCard(container)
        drives_card.pack(fill=tk.BOTH, expand=True)

        drives_frame = tk.Frame(drives_card, bg=FluentColors.CARD_BG)
        drives_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        header_frame = tk.Frame(drives_frame, bg=FluentColors.CARD_BG)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            header_frame,
            text="💽 Remote Drive Information",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)

        FluentButton(
            header_frame,
            "🔄 Refresh",
            self.refresh_remote_drives,
            "secondary"
        ).pack(side=tk.RIGHT, padx=5)

        FluentButton(
            header_frame,
            "📊 Export Report",
            self.export_network_report,
            "success"
        ).pack(side=tk.RIGHT, padx=5)

        tree_container = tk.Frame(drives_frame, bg=FluentColors.SURFACE)
        tree_container.pack(fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")

        self.network_tree = ttk.Treeview(
            tree_container,
            columns=("Server", "Drive", "Total", "Used", "Free", "Percent", "Status"),
            show="headings",
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
            style='Fluent.Treeview'
        )

        vsb.config(command=self.network_tree.yview)
        hsb.config(command=self.network_tree.xview)

        self.network_tree.heading("Server", text="Server")
        self.network_tree.heading("Drive", text="Drive")
        self.network_tree.heading("Total", text="Total Size")
        self.network_tree.heading("Used", text="Used")
        self.network_tree.heading("Free", text="Free")
        self.network_tree.heading("Percent", text="% Used")
        self.network_tree.heading("Status", text="Status")

        self.network_tree.column("Server", width=150, anchor="w")
        self.network_tree.column("Drive", width=100, anchor="w")
        self.network_tree.column("Total", width=120, anchor="e")
        self.network_tree.column("Used", width=120, anchor="e")
        self.network_tree.column("Free", width=120, anchor="e")
        self.network_tree.column("Percent", width=100, anchor="e")
        self.network_tree.column("Status", width=150, anchor="w")

        self.network_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Tag configurations for status colors
        self.network_tree.tag_configure('critical', background='#FFE6E6')
        self.network_tree.tag_configure('warning', background='#FFF4E6')
        self.network_tree.tag_configure('good', background='#E6F7E6')

    def setup_viz_tab(self):
        """Setup visualizations tab - FULLY WORKING"""
        if not HAS_MATPLOTLIB:
            return

        container = tk.Frame(self.viz_tab, bg=FluentColors.BG_SECONDARY)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        control_card = FluentCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        controls = tk.Frame(control_card, bg=FluentColors.CARD_BG)
        controls.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            controls,
            text="📊 Data Visualization",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)

        FluentButton(controls, "📈 Generate Charts", self.generate_charts, "primary").pack(side=tk.LEFT, padx=20)

        self.chart_frame = FluentCard(container)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

    def setup_trends_tab(self):
        """Setup trends tab - FULLY WORKING"""
        container = tk.Frame(self.trends_tab, bg=FluentColors.BG_SECONDARY)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        control_card = FluentCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        controls = tk.Frame(control_card, bg=FluentColors.CARD_BG)
        controls.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            controls,
            text="📈 Storage Trends",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)

        FluentButton(controls, "🔄 Refresh", self.refresh_trends, "primary").pack(side=tk.LEFT, padx=20)

        self.trends_info_label = tk.Label(
            controls,
            text="No history available",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 10)
        )
        self.trends_info_label.pack(side=tk.LEFT, padx=20)

        self.trends_chart_frame = FluentCard(container)
        self.trends_chart_frame.pack(fill=tk.BOTH, expand=True)

    def setup_comparison_tab(self):
        """Setup comparison tab - FULLY WORKING"""
        container = tk.Frame(self.comparison_tab, bg=FluentColors.BG_SECONDARY)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        control_card = FluentCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        controls = tk.Frame(control_card, bg=FluentColors.CARD_BG)
        controls.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            controls,
            text="💽 Multi-Drive Comparison",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)

        FluentButton(controls, "🔍 Scan All", self.scan_all_drives, "primary").pack(side=tk.LEFT, padx=(20, 5))
        FluentButton(controls, "📊 Compare", self.generate_drive_comparison, "secondary").pack(side=tk.LEFT, padx=5)

        self.comparison_frame = FluentCard(container)
        self.comparison_frame.pack(fill=tk.BOTH, expand=True)

    def setup_reports_tab(self):
        """Setup reports tab - FULLY WORKING"""
        container = tk.Frame(self.reports_tab, bg=FluentColors.BG_SECONDARY)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        control_card = FluentCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        controls = tk.Frame(control_card, bg=FluentColors.CARD_BG)
        controls.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            controls,
            text="📑 Advanced Analytics",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)

        FluentButton(controls, "📄 Generate Report", self.generate_advanced_report, "primary").pack(side=tk.LEFT, padx=20)

        report_card = FluentCard(container)
        report_card.pack(fill=tk.BOTH, expand=True)

        report_container = tk.Frame(report_card, bg=FluentColors.SURFACE)
        report_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.report_text = tk.Text(
            report_container,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg=FluentColors.SURFACE,
            fg=FluentColors.TEXT_PRIMARY,
            relief=tk.FLAT,
            insertbackground=FluentColors.TEXT_PRIMARY
        )
        self.report_text.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(report_container, command=self.report_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.report_text.config(yscrollcommand=scrollbar.set)

    def setup_heatmap_tab(self):
        """Setup heatmap tab - FULLY WORKING"""
        if not HAS_MATPLOTLIB or not HAS_SQUARIFY:
            return

        container = tk.Frame(self.heatmap_tab, bg=FluentColors.BG_SECONDARY)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        control_card = FluentCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        controls = tk.Frame(control_card, bg=FluentColors.CARD_BG)
        controls.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(
            controls,
            text="🗺️ Treemap",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_PRIMARY,
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)

        FluentButton(controls, "🎨 Generate", self.generate_treemap, "primary").pack(side=tk.LEFT, padx=20)

        tk.Label(
            controls,
            text="Items:",
            bg=FluentColors.CARD_BG,
            fg=FluentColors.TEXT_SECONDARY,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(20, 8))

        self.treemap_limit_var = tk.StringVar(value="50")
        tk.Entry(
            controls,
            textvariable=self.treemap_limit_var,
            width=8,
            font=("Segoe UI", 9),
            relief=tk.SOLID,
            bd=1
        ).pack(side=tk.LEFT)

        self.heatmap_frame = FluentCard(container)
        self.heatmap_frame.pack(fill=tk.BOTH, expand=True)

    def create_context_menu(self):
        """Create context menu"""
        self.context_menu = tk.Menu(
            self.root,
            tearoff=0,
            bg=FluentColors.SURFACE,
            fg=FluentColors.TEXT_PRIMARY,
            activebackground=FluentColors.PRIMARY,
            activeforeground="#FFFFFF",
            font=("Segoe UI", 9)
        )
        self.context_menu.add_command(label="📍 Open Location", command=self.open_file_location)
        self.context_menu.add_command(label="ℹ Properties", command=self.show_file_properties)
        if HAS_SEND2TRASH:
            self.context_menu.add_separator()
            self.context_menu.add_command(label="🗑 Delete", command=self.delete_files)

    def show_context_menu(self, event):
        """Show context menu"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # [INCLUDE ALL THE LOGIC METHODS FROM ULTRA VERSION - WORKING IMPLEMENTATION]
    # These are the core functionality methods that make everything work

    def load_drives(self):
        """Load available drives"""
        drives = []
        if sys.platform == "win32":
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
        else:
            drives = ["/"]
        self.drive_combo['values'] = drives
        if drives:
            self.drive_combo.current(0)

    def start_scan(self):
        """Start scanning"""
        if self.scanning:
            messagebox.showwarning("Scanning", "A scan is already in progress!")
            return
        drive = self.drive_var.get()
        if not drive:
            messagebox.showerror("Error", "Please select a drive!")
            return
        self.last_drive = drive
        self.save_settings()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.files_data = []
        self.filtered_data = []
        self.scanning = True
        self.scan_paused = False
        self.scan_cancelled = False
        self.progress_bar.start()
        self.progress_label.config(text="Scanning...", fg=FluentColors.INFO)
        self.status_icon.config(fg=FluentColors.INFO)
        self.scan_thread = threading.Thread(target=self.scan_drive, args=(drive,), daemon=True)
        self.scan_thread.start()

    def pause_scan(self):
        """Pause/Resume scan"""
        if self.scan_paused:
            self.scan_paused = False
            self.progress_label.config(text="Scanning...", fg=FluentColors.INFO)
        else:
            self.scan_paused = True
            self.progress_label.config(text="Paused", fg=FluentColors.WARNING)

    def cancel_scan(self):
        """Cancel scan"""
        self.scan_cancelled = True
        self.progress_label.config(text="Cancelling...", fg=FluentColors.ERROR)

    def scan_drive(self, path):
        """Scan drive/folder"""
        file_count = 0
        scan_start_time = datetime.now()
        try:
            for root, dirs, files in os.walk(path):
                while self.scan_paused and not self.scan_cancelled:
                    time.sleep(0.1)
                if self.scan_cancelled:
                    break
                if file_count % 100 == 0:
                    self.root.after(0, self.update_progress, f"Scanning... {file_count:,} files")
                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        file_stat = os.stat(file_path)
                        file_size = file_stat.st_size
                        file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                        file_atime = datetime.fromtimestamp(file_stat.st_atime)
                        _, ext = os.path.splitext(file)
                        file_type = self.get_file_type(ext)
                        self.files_data.append({
                            'path': file_path,
                            'size': file_size,
                            'type': file_type,
                            'extension': ext.lower(),
                            'modified': file_mtime,
                            'accessed': file_atime
                        })
                        file_count += 1
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except Exception as e:
            self.root.after(0, messagebox.showerror, "Error", f"Error scanning: {str(e)}")
        if not self.scan_cancelled:
            self.files_data.sort(key=lambda x: x['size'], reverse=True)
            scan_record = {
                'timestamp': scan_start_time,
                'path': path,
                'total_files': len(self.files_data),
                'total_size': sum(f['size'] for f in self.files_data),
                'file_types': self.get_type_distribution()
            }
            self.scan_history.append(scan_record)
            self.save_scan_history()
            self.root.after(0, self.finish_scan)
        else:
            self.root.after(0, self.reset_scan_ui)

    def finish_scan(self):
        """Finish scan"""
        self.filtered_data = self.files_data.copy()
        self.display_results()
        total_files = len(self.files_data)
        total_size_gb = sum(f['size'] for f in self.files_data) / (1024**3)
        self.status_label.config(text=f"✓ Complete: {total_files:,} files | {total_size_gb:.2f} GB")
        self.progress_label.config(text="Complete!", fg=FluentColors.SUCCESS)
        self.status_icon.config(fg=FluentColors.SUCCESS)
        self.reset_scan_ui()

    def reset_scan_ui(self):
        """Reset scan UI"""
        self.scanning = False
        self.progress_bar.stop()

    def update_progress(self, message):
        """Update progress"""
        self.progress_label.config(text=message)

    def get_file_type(self, extension):
        """Get file type category"""
        ext = extension.lower()
        video_ext = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        image_ext = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp'}
        doc_ext = {'.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx'}
        audio_ext = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'}
        archive_ext = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.iso'}
        exe_ext = {'.exe', '.msi', '.dll', '.so', '.app'}
        if ext in video_ext:
            return "Videos"
        elif ext in image_ext:
            return "Images"
        elif ext in doc_ext:
            return "Documents"
        elif ext in audio_ext:
            return "Audio"
        elif ext in archive_ext:
            return "Archives"
        elif ext in exe_ext:
            return "Executables"
        else:
            return "Other"

    def get_type_distribution(self):
        """Get file type distribution"""
        distribution = defaultdict(lambda: {'count': 0, 'size': 0})
        for f in self.files_data:
            distribution[f['type']]['count'] += 1
            distribution[f['type']]['size'] += f['size']
        return dict(distribution)

    def format_size(self, size_bytes):
        """Format size"""
        size_mb = size_bytes / (1024 * 1024)
        if size_mb >= 1020:
            size_gb = size_bytes / (1024 ** 3)
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"

    def display_results(self):
        """Display results"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for file_info in self.filtered_data:
            self.tree.insert("", tk.END, values=(
                f"{file_info['size']:,}",
                self.format_size(file_info['size']),
                file_info['type'],
                file_info['modified'].strftime("%Y-%m-%d %H:%M"),
                file_info['accessed'].strftime("%Y-%m-%d %H:%M"),
                file_info['path']
            ))

    def apply_filters(self, *args):
        """Apply filters"""
        if not self.files_data:
            return
        search_text = self.search_var.get().lower()
        file_type = self.file_type_var.get()
        try:
            min_size_mb = float(self.min_size_var.get() or 0)
            access_days = int(self.access_days_var.get() or 0)
        except ValueError:
            min_size_mb = access_days = 0
        min_size_bytes = min_size_mb * 1024 * 1024
        now = datetime.now()
        self.filtered_data = []
        for file_info in self.files_data:
            if search_text and search_text not in file_info['path'].lower():
                continue
            if file_type != "All" and file_info['type'] != file_type:
                continue
            if file_info['size'] < min_size_bytes:
                continue
            if access_days > 0:
                if (now - file_info['accessed']).days < access_days:
                    continue
            self.filtered_data.append(file_info)
        self.display_results()
        self.status_label.config(text=f"Showing {len(self.filtered_data):,} of {len(self.files_data):,} files")

    def clear_filters(self):
        """Clear filters"""
        self.search_var.set("")
        self.file_type_var.set("All")
        self.min_size_var.set("0")
        self.access_days_var.set("0")
        self.filtered_data = self.files_data.copy()
        self.display_results()

    def sort_tree_column(self, col):
        """Sort tree column"""
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = True
        if col in ["Size", "Readable"]:
            self.filtered_data.sort(key=lambda x: x['size'], reverse=self.sort_reverse)
        elif col == "Type":
            self.filtered_data.sort(key=lambda x: x['type'], reverse=self.sort_reverse)
        elif col == "Modified":
            self.filtered_data.sort(key=lambda x: x['modified'], reverse=self.sort_reverse)
        elif col == "Accessed":
            self.filtered_data.sort(key=lambda x: x['accessed'], reverse=self.sort_reverse)
        elif col == "Path":
            self.filtered_data.sort(key=lambda x: x['path'], reverse=self.sort_reverse)
        self.display_results()

    def open_file_location(self):
        """Open file location"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a file!")
            return
        item = selection[0]
        file_path = self.tree.item(item)['values'][5]
        try:
            if sys.platform == "win32":
                subprocess.run(['explorer', '/select,', file_path])
            elif sys.platform == "darwin":
                subprocess.run(['open', '-R', file_path])
            else:
                subprocess.run(['xdg-open', os.path.dirname(file_path)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open location: {str(e)}")

    def delete_files(self):
        """Delete files"""
        if not HAS_SEND2TRASH:
            messagebox.showerror("Error", "send2trash library not installed!")
            return
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select files!")
            return
        count = len(selection)
        result = messagebox.askyesno("Confirm", f"Move {count} file(s) to Recycle Bin?")
        if not result:
            return
        deleted = 0
        for item in selection:
            file_path = self.tree.item(item)['values'][5]
            try:
                send2trash(file_path)
                self.tree.delete(item)
                self.files_data = [f for f in self.files_data if f['path'] != file_path]
                self.filtered_data = [f for f in self.filtered_data if f['path'] != file_path]
                deleted += 1
            except Exception:
                pass
        messagebox.showinfo("Success", f"Moved {deleted} file(s) to Recycle Bin")

    def show_file_properties(self):
        """Show file properties"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a file!")
            return
        item = selection[0]
        values = self.tree.item(item)['values']
        file_path = values[5]
        try:
            stat_info = os.stat(file_path)
            props = f"""File Properties:

Path: {file_path}
Size: {values[1]} ({values[0]} bytes)
Type: {values[2]}
Modified: {values[3]}
Accessed: {values[4]}
Created: {datetime.fromtimestamp(stat_info.st_ctime).strftime("%Y-%m-%d %H:%M")}
"""
            messagebox.showinfo("Properties", props)
        except Exception as e:
            messagebox.showerror("Error", f"Could not get properties: {str(e)}")

    def analyze_folders(self):
        """Analyze folders - FULLY WORKING"""
        if not self.files_data:
            messagebox.showwarning("No Data", "Please scan a drive first!")
            return
        self.folders_data = defaultdict(lambda: {'size': 0, 'files': 0})
        for file_info in self.files_data:
            folder = os.path.dirname(file_info['path'])
            self.folders_data[folder]['size'] += file_info['size']
            self.folders_data[folder]['files'] += 1
        sorted_folders = sorted(self.folders_data.items(), key=lambda x: x[1]['size'], reverse=True)
        for item in self.folder_tree.get_children():
            self.folder_tree.delete(item)
        for folder, info in sorted_folders[:1000]:
            self.folder_tree.insert("", tk.END, values=(
                f"{info['size']:,}",
                self.format_size(info['size']),
                f"{info['files']:,}",
                folder
            ))
        messagebox.showinfo("Complete", f"Analyzed {len(sorted_folders):,} folders")

    def find_duplicates(self):
        """Find duplicates - FULLY WORKING"""
        if not self.files_data:
            messagebox.showwarning("No Data", "Please scan first!")
            return
        self.progress_label.config(text="Finding duplicates...", fg=FluentColors.INFO)
        self.progress_bar.start()
        thread = threading.Thread(target=self._find_duplicates_thread, daemon=True)
        thread.start()

    def _find_duplicates_thread(self):
        """Find duplicates thread"""
        hash_dict = defaultdict(list)
        for i, file_info in enumerate(self.files_data):
            if i % 100 == 0:
                self.root.after(0, self.update_progress, f"Hashing {i}/{len(self.files_data)}")
            try:
                file_hash = self.hash_file(file_info['path'])
                hash_dict[file_hash].append(file_info)
            except Exception:
                continue
        self.duplicates_data = {h: files for h, files in hash_dict.items() if len(files) > 1}
        self.root.after(0, self.display_duplicates)

    def hash_file(self, filepath, block_size=65536):
        """Calculate file hash"""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                hasher.update(data)
        return hasher.hexdigest()

    def display_duplicates(self):
        """Display duplicates"""
        for item in self.dup_tree.get_children():
            self.dup_tree.delete(item)
        total_duplicates = 0
        waste_size = 0
        for file_hash, files in self.duplicates_data.items():
            files.sort(key=lambda x: x['path'])
            for i, file_info in enumerate(files):
                self.dup_tree.insert("", tk.END, values=(
                    f"{file_info['size']:,}",
                    self.format_size(file_info['size']),
                    f"{i+1}/{len(files)}",
                    file_info['path']
                ))
                if i > 0:
                    waste_size += file_info['size']
            total_duplicates += len(files) - 1
        self.dup_label.config(text=f"Found {total_duplicates:,} duplicates | Wasted: {self.format_size(waste_size)}")
        self.progress_label.config(text="Ready", fg=FluentColors.SUCCESS)
        self.progress_bar.stop()
        messagebox.showinfo("Complete", f"Found {len(self.duplicates_data):,} sets of duplicates")

    def generate_charts(self):
        """Generate charts - FULLY WORKING"""
        if not HAS_MATPLOTLIB or not self.files_data:
            messagebox.showwarning("No Data", "Please scan a drive first!")
            return
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        fig = Figure(figsize=(14, 8), facecolor='white')

        # Chart 1: Top 10 files
        ax1 = fig.add_subplot(2, 2, 1)
        top_files = self.files_data[:10]
        names = [os.path.basename(f['path'])[:20] for f in top_files]
        sizes = [f['size'] / (1024**3) for f in top_files]
        ax1.barh(names, sizes, color=FluentColors.CHART_BLUE)
        ax1.set_xlabel('Size (GB)')
        ax1.set_title('Top 10 Largest Files')
        ax1.invert_yaxis()

        # Chart 2: File types
        ax2 = fig.add_subplot(2, 2, 2)
        type_sizes = defaultdict(int)
        for f in self.files_data:
            type_sizes[f['type']] += f['size']
        labels = list(type_sizes.keys())
        sizes = [s / (1024**3) for s in type_sizes.values()]
        colors = [FluentColors.CHART_BLUE, FluentColors.CHART_GREEN, FluentColors.CHART_ORANGE,
                 FluentColors.CHART_PURPLE, FluentColors.CHART_TEAL, FluentColors.CHART_RED, FluentColors.CHART_YELLOW]
        ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors[:len(labels)])
        ax2.set_title('Storage by File Type')

        # Chart 3: Size distribution
        ax3 = fig.add_subplot(2, 2, 3)
        sizes_mb = [f['size'] / (1024*1024) for f in self.files_data if f['size'] < 1024**3]
        ax3.hist(sizes_mb, bins=50, color=FluentColors.CHART_GREEN, edgecolor='white')
        ax3.set_xlabel('File Size (MB)')
        ax3.set_ylabel('Count')
        ax3.set_title('File Size Distribution')

        # Chart 4: Type count
        ax4 = fig.add_subplot(2, 2, 4)
        type_counts = defaultdict(int)
        for f in self.files_data:
            type_counts[f['type']] += 1
        types = list(type_counts.keys())
        counts = list(type_counts.values())
        ax4.bar(types, counts, color=FluentColors.CHART_PURPLE)
        ax4.set_ylabel('Count')
        ax4.set_title('File Count by Type')
        ax4.tick_params(axis='x', rotation=45)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        messagebox.showinfo("Success", "Charts generated successfully!")

    def refresh_trends(self):
        """Refresh trends - FULLY WORKING"""
        if not HAS_MATPLOTLIB:
            messagebox.showwarning("Error", "Matplotlib not installed!")
            return
        if len(self.scan_history) < 2:
            messagebox.showinfo("Insufficient Data", f"Need at least 2 scans. Current: {len(self.scan_history)}")
            return

        for widget in self.trends_chart_frame.winfo_children():
            widget.destroy()

        fig = Figure(figsize=(14, 8), facecolor='white')

        # Chart 1: Size over time
        ax1 = fig.add_subplot(2, 2, 1)
        dates = [h['timestamp'] for h in self.scan_history]
        sizes_gb = [h['total_size'] / (1024**3) for h in self.scan_history]
        ax1.plot(dates, sizes_gb, marker='o', linewidth=2, color=FluentColors.CHART_BLUE)
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Size (GB)')
        ax1.set_title('Storage Over Time')
        ax1.grid(True, alpha=0.3)
        fig.autofmt_xdate()

        # Chart 2: File count
        ax2 = fig.add_subplot(2, 2, 2)
        file_counts = [h['total_files'] for h in self.scan_history]
        ax2.plot(dates, file_counts, marker='s', linewidth=2, color=FluentColors.CHART_GREEN)
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Files')
        ax2.set_title('File Count Over Time')
        ax2.grid(True, alpha=0.3)
        fig.autofmt_xdate()

        # Chart 3: Growth rate
        ax3 = fig.add_subplot(2, 2, 3)
        if len(sizes_gb) > 1:
            growth = [sizes_gb[i] - sizes_gb[i-1] for i in range(1, len(sizes_gb))]
            growth_dates = dates[1:]
            colors = [FluentColors.CHART_GREEN if g < 0 else FluentColors.CHART_RED for g in growth]
            ax3.bar(growth_dates, growth, color=colors)
            ax3.set_xlabel('Date')
            ax3.set_ylabel('Change (GB)')
            ax3.set_title('Growth Rate')
            ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax3.grid(True, alpha=0.3)
            fig.autofmt_xdate()

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.trends_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        latest = self.scan_history[-1]
        oldest = self.scan_history[0]
        size_change = (latest['total_size'] - oldest['total_size']) / (1024**3)
        files_change = latest['total_files'] - oldest['total_files']

        self.trends_info_label.config(
            text=f"Scans: {len(self.scan_history)} | Size change: {size_change:+.2f} GB | Files: {files_change:+,}"
        )

        messagebox.showinfo("Success", "Trends refreshed successfully!")

    def scan_all_drives(self):
        """Scan all drives - FULLY WORKING"""
        if self.scanning:
            messagebox.showwarning("Scanning", "A scan is already in progress!")
            return
        drives = self.drive_combo['values']
        if not drives:
            messagebox.showerror("Error", "No drives found!")
            return
        self.all_drives_data = {}
        self.progress_label.config(text="Scanning all drives...", fg=FluentColors.INFO)
        thread = threading.Thread(target=self._scan_all_drives_thread, args=(drives,), daemon=True)
        thread.start()

    def _scan_all_drives_thread(self, drives):
        """Scan all drives thread"""
        for i, drive in enumerate(drives):
            self.root.after(0, self.update_progress, f"Scanning drive {i+1}/{len(drives)}: {drive}")
            drive_data = {'files': [], 'total_size': 0, 'total_files': 0}
            try:
                for root, dirs, files in os.walk(drive):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            file_stat = os.stat(file_path)
                            file_size = file_stat.st_size
                            drive_data['files'].append({'path': file_path, 'size': file_size})
                            drive_data['total_size'] += file_size
                            drive_data['total_files'] += 1
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
            except Exception:
                pass
            self.all_drives_data[drive] = drive_data
        self.root.after(0, self.finish_all_drives_scan)

    def finish_all_drives_scan(self):
        """Finish all drives scan"""
        self.progress_label.config(text="All drives scanned!", fg=FluentColors.SUCCESS)
        messagebox.showinfo("Complete", f"Scanned {len(self.all_drives_data)} drives!")
        self.generate_drive_comparison()

    def generate_drive_comparison(self):
        """Generate drive comparison - FULLY WORKING"""
        if not self.all_drives_data:
            messagebox.showinfo("No Data", "Please scan all drives first!")
            return

        for widget in self.comparison_frame.winfo_children():
            widget.destroy()

        # Table
        tree_container = tk.Frame(self.comparison_frame, bg=FluentColors.SURFACE)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        comp_tree = ttk.Treeview(
            tree_container,
            columns=("Drive", "Size", "Files", "Avg"),
            show="headings",
            yscrollcommand=vsb.set,
            style='Fluent.Treeview'
        )

        vsb.config(command=comp_tree.yview)

        comp_tree.heading("Drive", text="Drive")
        comp_tree.heading("Size", text="Total Size")
        comp_tree.heading("Files", text="Files")
        comp_tree.heading("Avg", text="Avg Size")

        comp_tree.column("Drive", width=100)
        comp_tree.column("Size", width=150)
        comp_tree.column("Files", width=120)
        comp_tree.column("Avg", width=150)

        comp_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        for drive, data in sorted(self.all_drives_data.items()):
            total_size = data['total_size']
            file_count = data['total_files']
            avg_size = total_size / file_count if file_count > 0 else 0
            comp_tree.insert("", tk.END, values=(
                drive,
                self.format_size(total_size),
                f"{file_count:,}",
                self.format_size(avg_size)
            ))

        messagebox.showinfo("Success", "Comparison generated!")

    def generate_advanced_report(self):
        """Generate advanced report - FULLY WORKING"""
        if not self.files_data:
            messagebox.showwarning("No Data", "Please scan first!")
            return

        self.report_text.delete(1.0, tk.END)

        report = []
        report.append("=" * 80)
        report.append("DISK SPACE ANALYTICS REPORT")
        report.append("=" * 80)
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        total_files = len(self.files_data)
        total_size = sum(f['size'] for f in self.files_data)
        avg_size = total_size / total_files if total_files > 0 else 0

        report.append("\n1. BASIC STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Files: {total_files:,}")
        report.append(f"Total Size: {self.format_size(total_size)} ({total_size:,} bytes)")
        report.append(f"Average Size: {self.format_size(avg_size)}")

        type_dist = self.get_type_distribution()
        report.append("\n2. FILE TYPE BREAKDOWN")
        report.append("-" * 80)
        report.append(f"{'Type':<15} {'Count':>12} {'Size':>15} {'% Total':>12}")
        report.append("-" * 80)

        for ftype in sorted(type_dist.keys()):
            count = type_dist[ftype]['count']
            size = type_dist[ftype]['size']
            percent = (size / total_size * 100) if total_size > 0 else 0
            report.append(f"{ftype:<15} {count:>12,} {self.format_size(size):>15} {percent:>11.1f}%")

        report.append("\n3. TOP 20 LARGEST FILES")
        report.append("-" * 80)
        for i, f in enumerate(self.files_data[:20], 1):
            report.append(f"{i:2d}. {self.format_size(f['size']):>10} - {os.path.basename(f['path'])[:60]}")

        report_text = "\n".join(report)
        self.report_text.insert(1.0, report_text)

        messagebox.showinfo("Success", "Report generated!")

    def generate_treemap(self):
        """Generate treemap - FULLY WORKING"""
        if not HAS_MATPLOTLIB or not HAS_SQUARIFY or not self.files_data:
            messagebox.showwarning("Error", "Cannot generate treemap!")
            return

        try:
            limit = int(self.treemap_limit_var.get() or 50)
        except ValueError:
            limit = 50

        for widget in self.heatmap_frame.winfo_children():
            widget.destroy()

        top_items = self.files_data[:limit]
        labels = [os.path.basename(f['path'])[:25] for f in top_items]
        sizes = [f['size'] for f in top_items]
        colors_map = {
            'Videos': FluentColors.CHART_RED,
            'Images': FluentColors.CHART_PURPLE,
            'Documents': FluentColors.CHART_BLUE,
            'Audio': FluentColors.CHART_TEAL,
            'Archives': FluentColors.CHART_GREEN,
            'Executables': FluentColors.CHART_ORANGE,
            'Other': '#999999'
        }
        colors = [colors_map.get(f['type'], '#999999') for f in top_items]

        fig = Figure(figsize=(14, 10), facecolor='white')
        ax = fig.add_subplot(111)

        squarify.plot(sizes=sizes, label=labels, color=colors, alpha=0.8, ax=ax,
                     text_kwargs={'fontsize': 8, 'weight': 'bold'})

        ax.set_title(f'Treemap: Top {limit} Files', fontsize=16, weight='bold')
        ax.axis('off')

        legend_elements = [mpatches.Patch(facecolor=color, label=ftype, alpha=0.8)
                          for ftype, color in colors_map.items()]
        ax.legend(handles=legend_elements, loc='upper left')

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.heatmap_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        messagebox.showinfo("Success", "Treemap generated!")

    def load_scan_history(self):
        """Load scan history"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'rb') as f:
                    self.scan_history = pickle.load(f)
        except Exception:
            self.scan_history = []

    def save_scan_history(self):
        """Save scan history"""
        try:
            if len(self.scan_history) > 30:
                self.scan_history = self.scan_history[-30:]
            with open(self.history_file, 'wb') as f:
                pickle.dump(self.scan_history, f)
        except Exception:
            pass

    def load_settings(self):
        """Load settings"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.last_drive = settings.get('last_drive', '')
        except Exception:
            pass

    def apply_extension_preset(self, extensions):
        """Apply a preset extension filter"""
        extensions_str = ", ".join(extensions)
        self.custom_extensions_var.set(extensions_str)
        self.find_by_extensions()

    def find_by_extensions(self):
        """Find files by custom extensions"""
        if not self.files_data:
            messagebox.showwarning("No Data", "Please scan a drive first from the Files tab!")
            return

        extensions_input = self.custom_extensions_var.get().strip()
        if not extensions_input:
            messagebox.showwarning("No Extensions", "Please enter extensions or use a preset!")
            return

        # Parse extensions
        extensions = [ext.strip().lower() for ext in extensions_input.split(",")]
        # Ensure extensions start with a dot
        extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]

        # Clear tree
        for item in self.finder_tree.get_children():
            self.finder_tree.delete(item)

        # Filter files
        matching_files = []
        for file_info in self.files_data:
            file_ext = os.path.splitext(file_info['path'])[1].lower()
            if file_ext in extensions:
                matching_files.append(file_info)

        # Sort by size (largest first)
        matching_files.sort(key=lambda x: x['size'], reverse=True)

        # Display results
        total_size = 0
        for file_info in matching_files:
            filename = os.path.basename(file_info['path'])
            size = file_info['size']
            total_size += size
            readable_size = self.format_size(size)
            file_ext = os.path.splitext(file_info['path'])[1]

            # Handle both timestamp and datetime objects
            modified = file_info['modified']
            if isinstance(modified, datetime):
                modified_time = modified.strftime('%Y-%m-%d %H:%M')
            else:
                modified_time = datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M')

            self.finder_tree.insert("", "end", values=(
                filename,
                size,
                readable_size,
                file_ext,
                modified_time,
                file_info['path']
            ))

        # Update statistics
        count = len(matching_files)
        total_readable = self.format_size(total_size)
        ext_list = ", ".join(extensions)
        self.finder_stats_label.config(
            text=f"Found {count:,} files ({total_readable}) matching: {ext_list}"
        )

        if count == 0:
            messagebox.showinfo("No Results", f"No files found with extensions: {ext_list}")

    def clear_file_finder(self):
        """Clear file finder results"""
        self.custom_extensions_var.set("")
        for item in self.finder_tree.get_children():
            self.finder_tree.delete(item)
        self.finder_stats_label.config(text="No search performed yet")

    def sort_finder_tree(self, col):
        """Sort file finder tree by column"""
        items = [(self.finder_tree.set(item, col), item) for item in self.finder_tree.get_children("")]

        # Try numeric sort for size columns
        if col in ["Size"]:
            try:
                items.sort(key=lambda x: int(x[0]), reverse=True)
            except ValueError:
                items.sort(reverse=True)
        else:
            items.sort(reverse=True)

        for index, (val, item) in enumerate(items):
            self.finder_tree.move(item, "", index)

    def show_finder_context_menu(self, event):
        """Show context menu for file finder tree"""
        item = self.finder_tree.identify_row(event.y)
        if item:
            self.finder_tree.selection_set(item)
            menu = tk.Menu(self.root, tearoff=0, bg=FluentColors.SURFACE, fg=FluentColors.TEXT_PRIMARY)
            menu.add_command(label="📂 Open Location", command=self.open_file_location_finder)
            menu.add_command(label="🗑️ Delete File", command=self.delete_selected_finder_files)
            menu.add_separator()
            menu.add_command(label="📋 Copy Path", command=self.copy_path_finder)
            menu.post(event.x_root, event.y_root)

    def open_file_location_finder(self):
        """Open file location from finder tree"""
        selected = self.finder_tree.selection()
        if not selected:
            return

        file_path = self.finder_tree.item(selected[0])['values'][5]  # Path column
        if os.path.exists(file_path):
            if sys.platform == 'win32':
                subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
            elif sys.platform == 'darwin':
                subprocess.run(['open', '-R', file_path])
            else:
                subprocess.run(['xdg-open', os.path.dirname(file_path)])

    def delete_selected_finder_files(self):
        """Delete selected files from finder tree"""
        selected = self.finder_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select files to delete!")
            return

        file_count = len(selected)
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete {file_count} selected file(s)?\n\nFiles will be moved to Recycle Bin."
        )

        if confirm:
            deleted_count = 0
            for item in selected:
                file_path = self.finder_tree.item(item)['values'][5]
                try:
                    if HAS_SEND2TRASH:
                        send2trash(file_path)
                    else:
                        os.remove(file_path)
                    self.finder_tree.delete(item)
                    deleted_count += 1
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete {file_path}: {str(e)}")

            if deleted_count > 0:
                messagebox.showinfo("Success", f"Deleted {deleted_count} file(s)")
                # Update stats
                remaining_count = len(self.finder_tree.get_children())
                total_size = sum(int(self.finder_tree.item(item)['values'][1])
                               for item in self.finder_tree.get_children())
                total_readable = self.format_size(total_size)
                current_stats = self.finder_stats_label.cget("text")
                if "matching:" in current_stats:
                    ext_part = current_stats.split("matching:")[1]
                    self.finder_stats_label.config(
                        text=f"Found {remaining_count:,} files ({total_readable}) matching:{ext_part}"
                    )

    def copy_path_finder(self):
        """Copy file path to clipboard from finder tree"""
        selected = self.finder_tree.selection()
        if selected:
            file_path = self.finder_tree.item(selected[0])['values'][5]
            self.root.clipboard_clear()
            self.root.clipboard_append(file_path)
            self.status_label.config(text="Path copied to clipboard")

    # Network Admin Methods
    def load_saved_servers(self):
        """Load saved server list from settings"""
        try:
            servers_file = os.path.join(os.path.expanduser("~"), ".space_scanner_servers.json")
            if os.path.exists(servers_file):
                with open(servers_file, 'r') as f:
                    data = json.load(f)
                    return tuple(data.get('servers', []))
        except Exception:
            pass
        return ()

    def save_current_server(self):
        """Save current server to quick access list"""
        server = self.server_ip_var.get().strip()
        if not server:
            messagebox.showwarning("No Server", "Enter a server address first!")
            return

        try:
            servers_file = os.path.join(os.path.expanduser("~"), ".space_scanner_servers.json")
            servers = list(self.load_saved_servers())

            if server not in servers:
                servers.append(server)
                with open(servers_file, 'w') as f:
                    json.dump({'servers': servers}, f)

                # Update dropdown
                saved_combo = None
                for widget in self.network_admin_tab.winfo_children():
                    # Find the combobox (this is a workaround)
                    pass

                messagebox.showinfo("Saved", f"Server '{server}' saved to quick access!")
            else:
                messagebox.showinfo("Already Saved", f"Server '{server}' is already in quick access!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save server: {str(e)}")

    def remove_saved_server(self):
        """Remove server from saved list"""
        server = self.saved_servers.get()
        if not server:
            messagebox.showwarning("No Selection", "Select a server from the dropdown first!")
            return

        try:
            servers_file = os.path.join(os.path.expanduser("~"), ".space_scanner_servers.json")
            servers = list(self.load_saved_servers())

            if server in servers:
                servers.remove(server)
                with open(servers_file, 'w') as f:
                    json.dump({'servers': servers}, f)

                messagebox.showinfo("Removed", f"Server '{server}' removed from quick access!")
            else:
                messagebox.showwarning("Not Found", f"Server '{server}' not in list!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove server: {str(e)}")

    def connect_to_server(self):
        """Connect to remote server and scan drives"""
        server = self.server_ip_var.get().strip()
        if not server:
            messagebox.showwarning("No Server", "Enter a server IP address or hostname!")
            return

        self.network_status_label.config(text=f"🟡 Connecting to {server}...")
        self.root.update()

        # Run in thread to avoid blocking UI
        thread = threading.Thread(target=self._connect_to_server_thread, args=(server,))
        thread.daemon = True
        thread.start()

    def _connect_to_server_thread(self, server):
        """Thread function to connect to server"""
        try:
            # Test connection by trying to access admin share
            test_path = f"\\\\{server}\\C$"

            # Try to list the drives
            if os.path.exists(test_path):
                # Connection successful
                self.root.after(0, self._update_connection_success, server)
                self.root.after(0, self._scan_remote_server, server)
            else:
                # Try without admin share
                test_path = f"\\\\{server}\\C"
                if os.path.exists(test_path):
                    self.root.after(0, self._update_connection_success, server)
                    self.root.after(0, self._scan_remote_server, server)
                else:
                    self.root.after(0, self._update_connection_failed, server, "Cannot access server. Check permissions and network connectivity.")
        except Exception as e:
            self.root.after(0, self._update_connection_failed, server, str(e))

    def _update_connection_success(self, server):
        """Update UI after successful connection"""
        self.network_status_label.config(
            text=f"🟢 Connected to {server}",
            fg=FluentColors.SUCCESS
        )

        # Update server info
        self.server_info_text.config(state=tk.NORMAL)
        self.server_info_text.delete("1.0", tk.END)
        self.server_info_text.insert("1.0", f"Server: {server}\n")
        self.server_info_text.insert("end", f"Status: Connected\n")
        self.server_info_text.insert("end", f"Connection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.server_info_text.insert("end", f"Access Method: Network Share (SMB)\n")
        self.server_info_text.config(state=tk.DISABLED)

    def _update_connection_failed(self, server, error_msg):
        """Update UI after connection failure"""
        self.network_status_label.config(
            text=f"🔴 Failed to connect to {server}",
            fg=FluentColors.ERROR
        )
        messagebox.showerror(
            "Connection Failed",
            f"Failed to connect to {server}\n\n{error_msg}\n\nMake sure:\n- Server is online\n- You have network access\n- File sharing is enabled\n- You have proper permissions"
        )

    def _scan_remote_server(self, server):
        """Scan remote server drives"""
        # Clear existing data
        for item in self.network_tree.get_children():
            self.network_tree.delete(item)

        drives_found = 0

        # Common drive letters
        drive_letters = ['C', 'D', 'E', 'F', 'G', 'H']

        for drive_letter in drive_letters:
            try:
                # Try admin share first
                remote_path = f"\\\\{server}\\{drive_letter}$"
                if not os.path.exists(remote_path):
                    # Try regular share
                    remote_path = f"\\\\{server}\\{drive_letter}"
                    if not os.path.exists(remote_path):
                        continue

                # Get drive stats
                stat = os.statvfs(remote_path) if hasattr(os, 'statvfs') else None

                if stat:
                    total = stat.f_blocks * stat.f_frsize
                    free = stat.f_bavail * stat.f_frsize
                    used = total - free
                else:
                    # Windows alternative using shutil
                    import shutil
                    total, used, free = shutil.disk_usage(remote_path)

                percent_used = (used / total * 100) if total > 0 else 0

                # Determine status
                if percent_used >= 90:
                    status = "🔴 Critical"
                    tag = 'critical'
                elif percent_used >= 75:
                    status = "🟡 Warning"
                    tag = 'warning'
                else:
                    status = "🟢 Good"
                    tag = 'good'

                self.network_tree.insert("", "end", values=(
                    server,
                    f"{drive_letter}:",
                    self.format_size(total),
                    self.format_size(used),
                    self.format_size(free),
                    f"{percent_used:.1f}%",
                    status
                ), tags=(tag,))

                drives_found += 1

            except Exception as e:
                # Drive not accessible, skip
                continue

        if drives_found == 0:
            messagebox.showwarning(
                "No Drives Found",
                f"No accessible drives found on {server}\n\nMake sure administrative shares are enabled (C$, D$, etc.)\nor regular shares are configured."
            )

    def scan_local_server(self):
        """Scan local machine as a server"""
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        self.network_status_label.config(
            text=f"🟢 Connected to LOCAL ({hostname} - {local_ip})",
            fg=FluentColors.SUCCESS
        )

        # Update server info
        self.server_info_text.config(state=tk.NORMAL)
        self.server_info_text.delete("1.0", tk.END)
        self.server_info_text.insert("1.0", f"Server: LOCAL MACHINE\n")
        self.server_info_text.insert("end", f"Hostname: {hostname}\n")
        self.server_info_text.insert("end", f"IP Address: {local_ip}\n")
        self.server_info_text.insert("end", f"Status: Connected\n")
        self.server_info_text.insert("end", f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.server_info_text.config(state=tk.DISABLED)

        # Scan local drives
        self._scan_local_drives()

    def _scan_local_drives(self):
        """Scan local machine drives"""
        # Clear existing data
        for item in self.network_tree.get_children():
            self.network_tree.delete(item)

        import socket
        hostname = socket.gethostname()

        # Get all drives
        if sys.platform == 'win32':
            import string
            drives = ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
        else:
            drives = ['/']

        for drive in drives:
            try:
                import shutil
                total, used, free = shutil.disk_usage(drive)
                percent_used = (used / total * 100) if total > 0 else 0

                # Determine status
                if percent_used >= 90:
                    status = "🔴 Critical"
                    tag = 'critical'
                elif percent_used >= 75:
                    status = "🟡 Warning"
                    tag = 'warning'
                else:
                    status = "🟢 Good"
                    tag = 'good'

                self.network_tree.insert("", "end", values=(
                    f"LOCAL ({hostname})",
                    drive,
                    self.format_size(total),
                    self.format_size(used),
                    self.format_size(free),
                    f"{percent_used:.1f}%",
                    status
                ), tags=(tag,))

            except Exception:
                continue

    def refresh_remote_drives(self):
        """Refresh drive information for connected server"""
        server = self.server_ip_var.get().strip()
        if server:
            self._scan_remote_server(server)
        else:
            # Refresh local if that's what's showing
            if "LOCAL" in self.network_status_label.cget("text"):
                self._scan_local_drives()
            else:
                messagebox.showwarning("No Connection", "Connect to a server first!")

    def export_network_report(self):
        """Export network monitoring report"""
        if not self.network_tree.get_children():
            messagebox.showwarning("No Data", "No server data to export!")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("All Files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    # Header
                    f.write("=" * 80 + "\n")
                    f.write("NETWORK SERVER DISK SPACE MONITORING REPORT\n")
                    f.write("=" * 80 + "\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Tool: Disk Space Scanner v4.1 (Network Admin Edition)\n")
                    f.write("=" * 80 + "\n\n")

                    # Server info
                    server_info = self.server_info_text.get("1.0", tk.END).strip()
                    f.write("Server Information:\n")
                    f.write("-" * 80 + "\n")
                    f.write(server_info + "\n\n")

                    # Drive data
                    f.write("Drive Information:\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"{'Server':<20} {'Drive':<8} {'Total':<12} {'Used':<12} {'Free':<12} {'%Used':<8} Status\n")
                    f.write("-" * 80 + "\n")

                    for item in self.network_tree.get_children():
                        values = self.network_tree.item(item)['values']
                        f.write(f"{values[0]:<20} {values[1]:<8} {values[2]:<12} {values[3]:<12} {values[4]:<12} {values[5]:<8} {values[6]}\n")

                    f.write("\n" + "=" * 80 + "\n")
                    f.write("End of Report\n")
                    f.write("=" * 80 + "\n")

                messagebox.showinfo("Export Complete", f"Report exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Failed to export report:\n{str(e)}")

    def save_settings(self):
        """Save settings"""
        try:
            settings = {'last_drive': getattr(self, 'last_drive', '')}
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception:
            pass


def main():
    root = tk.Tk()
    app = SpaceScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
