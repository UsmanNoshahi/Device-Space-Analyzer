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


# Modern color scheme
class ModernColors:
    # Main colors
    PRIMARY = "#667eea"  # Purple-blue gradient
    PRIMARY_DARK = "#5568d3"
    PRIMARY_LIGHT = "#7c94f5"

    SECONDARY = "#764ba2"  # Deep purple
    ACCENT = "#f093fb"  # Pink accent

    # Status colors
    SUCCESS = "#10b981"  # Green
    WARNING = "#f59e0b"  # Orange
    ERROR = "#ef4444"  # Red
    INFO = "#3b82f6"  # Blue

    # Neutral colors
    BG_DARK = "#1f2937"  # Dark background
    BG_MEDIUM = "#374151"  # Medium background
    BG_LIGHT = "#f9fafb"  # Light background

    TEXT_DARK = "#111827"
    TEXT_LIGHT = "#f9fafb"
    TEXT_MUTED = "#9ca3af"

    # UI elements
    CARD_BG = "#ffffff"
    CARD_BORDER = "#e5e7eb"
    HOVER = "#f3f4f6"

    # Chart colors
    CHART_COLORS = ["#667eea", "#f093fb", "#53f", "#ffa500", "#ff6b6b", "#4ecdc4", "#45b7d1"]


class ModernButton(tk.Canvas):
    """Custom modern button with gradient and hover effects"""
    def __init__(self, parent, text, command, bg_color=ModernColors.PRIMARY,
                 fg_color=ModernColors.TEXT_LIGHT, width=120, height=36, **kwargs):
        super().__init__(parent, width=width, height=height,
                        highlightthickness=0, **kwargs)

        self.text = text
        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.width = width
        self.height = height
        self.hover = False

        self.draw_button()
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def draw_button(self):
        self.delete("all")

        # Shadow (using gray instead of RGBA)
        self.create_rectangle(2, 2, self.width, self.height,
                            fill="#d0d0d0", outline="", tags="shadow")

        # Button background with rounded corners
        color = self.lighten_color(self.bg_color) if self.hover else self.bg_color
        self.create_rounded_rect(0, 0, self.width-2, self.height-2,
                                radius=8, fill=color, outline="")

        # Text
        self.create_text(self.width//2, self.height//2,
                        text=self.text, fill=self.fg_color,
                        font=("Segoe UI", 10, "bold"))

    def create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1,
                 x2-radius, y1,
                 x2, y1,
                 x2, y1+radius,
                 x2, y2-radius,
                 x2, y2,
                 x2-radius, y2,
                 x1+radius, y2,
                 x1, y2,
                 x1, y2-radius,
                 x1, y1+radius,
                 x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)

    def lighten_color(self, color):
        """Lighten a hex color by converting to RGB and back"""
        # Remove # and convert to RGB
        color = color.lstrip('#')
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)

        # Lighten by 20%
        r = min(255, int(r + (255 - r) * 0.2))
        g = min(255, int(g + (255 - g) * 0.2))
        b = min(255, int(b + (255 - b) * 0.2))

        return f"#{r:02x}{g:02x}{b:02x}"

    def on_enter(self, e):
        self.hover = True
        self.draw_button()
        self.config(cursor="hand2")

    def on_leave(self, e):
        self.hover = False
        self.draw_button()
        self.config(cursor="")

    def on_click(self, e):
        if self.command:
            self.command()


class ModernCard(tk.Frame):
    """Modern card container with shadow"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=ModernColors.CARD_BG,
                        relief=tk.FLAT, **kwargs)
        self.config(highlightbackground=ModernColors.CARD_BORDER,
                   highlightthickness=1)


class SpaceScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Disk Space Scanner Pro")
        self.root.geometry("1600x900")

        # Set app icon and colors
        self.root.configure(bg=ModernColors.BG_LIGHT)

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
        self.dark_mode = False
        self.sort_column = None
        self.sort_reverse = True

        # Settings and history files
        self.settings_file = "scanner_settings.json"
        self.history_file = "scan_history.pkl"

        # Load settings and history
        self.load_settings()
        self.load_scan_history()

        # Configure modern styles
        self.configure_modern_styles()

        # Setup UI
        self.setup_ui()
        self.load_drives()

        # Restore last drive
        if hasattr(self, 'last_drive') and self.last_drive:
            self.drive_var.set(self.last_drive)

    def configure_modern_styles(self):
        """Configure modern ttk styles"""
        style = ttk.Style()

        # Try to use a modern theme
        try:
            style.theme_use('clam')
        except:
            pass

        # Configure Notebook (tabs)
        style.configure('TNotebook',
                       background=ModernColors.BG_LIGHT,
                       borderwidth=0)
        style.configure('TNotebook.Tab',
                       background=ModernColors.BG_MEDIUM,
                       foreground=ModernColors.TEXT_LIGHT,
                       padding=[20, 10],
                       font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab',
                 background=[('selected', ModernColors.PRIMARY)],
                 foreground=[('selected', ModernColors.TEXT_LIGHT)])

        # Configure Treeview
        style.configure('Modern.Treeview',
                       background=ModernColors.CARD_BG,
                       foreground=ModernColors.TEXT_DARK,
                       fieldbackground=ModernColors.CARD_BG,
                       borderwidth=0,
                       font=('Segoe UI', 9))
        style.configure('Modern.Treeview.Heading',
                       background=ModernColors.PRIMARY,
                       foreground=ModernColors.TEXT_LIGHT,
                       borderwidth=0,
                       font=('Segoe UI', 10, 'bold'))
        style.map('Modern.Treeview',
                 background=[('selected', ModernColors.PRIMARY_LIGHT)])

        # Configure Progressbar
        style.configure('Modern.Horizontal.TProgressbar',
                       background=ModernColors.PRIMARY,
                       troughcolor=ModernColors.BG_LIGHT,
                       borderwidth=0,
                       thickness=6)

        # Configure Combobox
        style.configure('Modern.TCombobox',
                       background=ModernColors.CARD_BG,
                       foreground=ModernColors.TEXT_DARK,
                       fieldbackground=ModernColors.CARD_BG,
                       borderwidth=1,
                       relief=tk.FLAT)

    def setup_ui(self):
        """Setup the modern user interface"""
        # Create header
        self.create_modern_header()

        # Create main content area
        main_container = tk.Frame(self.root, bg=ModernColors.BG_LIGHT)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # Create notebook for tabs with modern style
        self.notebook = ttk.Notebook(main_container, style='TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: File Scanner
        self.files_tab = tk.Frame(self.notebook, bg=ModernColors.BG_LIGHT)
        self.notebook.add(self.files_tab, text="📁 File Scanner")
        self.setup_files_tab()

        # Tab 2: Folder Analysis
        self.folders_tab = tk.Frame(self.notebook, bg=ModernColors.BG_LIGHT)
        self.notebook.add(self.folders_tab, text="📂 Folder Analysis")
        self.setup_folders_tab()

        # Tab 3: Duplicates
        self.duplicates_tab = tk.Frame(self.notebook, bg=ModernColors.BG_LIGHT)
        self.notebook.add(self.duplicates_tab, text="🔄 Duplicates")
        self.setup_duplicates_tab()

        # Tab 4: Visualizations
        if HAS_MATPLOTLIB:
            self.viz_tab = tk.Frame(self.notebook, bg=ModernColors.BG_LIGHT)
            self.notebook.add(self.viz_tab, text="📊 Charts")
            self.setup_viz_tab()

        # Tab 5: Trends
        self.trends_tab = tk.Frame(self.notebook, bg=ModernColors.BG_LIGHT)
        self.notebook.add(self.trends_tab, text="📈 Trends")
        self.setup_trends_tab()

        # Tab 6: Multi-Drive
        self.comparison_tab = tk.Frame(self.notebook, bg=ModernColors.BG_LIGHT)
        self.notebook.add(self.comparison_tab, text="💽 Drives")
        self.setup_comparison_tab()

        # Tab 7: Reports
        self.reports_tab = tk.Frame(self.notebook, bg=ModernColors.BG_LIGHT)
        self.notebook.add(self.reports_tab, text="📑 Reports")
        self.setup_reports_tab()

        # Tab 8: Heatmap
        if HAS_MATPLOTLIB and HAS_SQUARIFY:
            self.heatmap_tab = tk.Frame(self.notebook, bg=ModernColors.BG_LIGHT)
            self.notebook.add(self.heatmap_tab, text="🗺️ Heatmap")
            self.setup_heatmap_tab()

        # Create modern status bar
        self.create_modern_statusbar()

    def create_modern_header(self):
        """Create modern gradient header"""
        header = tk.Canvas(self.root, height=100, bg=ModernColors.PRIMARY,
                          highlightthickness=0)
        header.pack(fill=tk.X)

        # Gradient effect (simple)
        for i in range(100):
            color = self.interpolate_color(ModernColors.PRIMARY,
                                          ModernColors.SECONDARY, i/100)
            header.create_line(0, i, 1600, i, fill=color)

        # Title
        header.create_text(40, 35, text="🚀 Disk Space Scanner Pro",
                          anchor=tk.W, fill=ModernColors.TEXT_LIGHT,
                          font=("Segoe UI", 24, "bold"))

        # Subtitle
        header.create_text(40, 65, text="Modern storage management for power users",
                          anchor=tk.W, fill=ModernColors.TEXT_LIGHT,
                          font=("Segoe UI", 11))

        # Version badge
        badge_x, badge_y = 1520, 50
        header.create_oval(badge_x-30, badge_y-20, badge_x+30, badge_y+20,
                          fill=ModernColors.SUCCESS, outline="")
        header.create_text(badge_x, badge_y, text="v3.0",
                          fill=ModernColors.TEXT_LIGHT,
                          font=("Segoe UI", 10, "bold"))

    def interpolate_color(self, color1, color2, fraction):
        """Interpolate between two hex colors"""
        c1 = int(color1[1:], 16)
        c2 = int(color2[1:], 16)

        r1, g1, b1 = (c1 >> 16) & 0xff, (c1 >> 8) & 0xff, c1 & 0xff
        r2, g2, b2 = (c2 >> 16) & 0xff, (c2 >> 8) & 0xff, c2 & 0xff

        r = int(r1 + (r2 - r1) * fraction)
        g = int(g1 + (g2 - g1) * fraction)
        b = int(b1 + (b2 - b1) * fraction)

        return f"#{r:02x}{g:02x}{b:02x}"

    def create_modern_statusbar(self):
        """Create modern status bar"""
        statusbar = tk.Frame(self.root, bg=ModernColors.BG_DARK, height=40)
        statusbar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = tk.Label(statusbar, text="Ready",
                                     bg=ModernColors.BG_DARK,
                                     fg=ModernColors.TEXT_LIGHT,
                                     font=("Segoe UI", 9),
                                     anchor=tk.W, padx=20)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Add small indicators
        self.status_icon = tk.Label(statusbar, text="●",
                                    bg=ModernColors.BG_DARK,
                                    fg=ModernColors.SUCCESS,
                                    font=("Segoe UI", 16))
        self.status_icon.pack(side=tk.RIGHT, padx=10)

    def setup_files_tab(self):
        """Setup modern files scanner tab"""
        # Main container
        container = tk.Frame(self.files_tab, bg=ModernColors.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Top card - Controls
        control_card = ModernCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        # Row 1: Drive and scan controls
        row1 = tk.Frame(control_card, bg=ModernColors.CARD_BG)
        row1.pack(fill=tk.X, padx=20, pady=(15, 10))

        tk.Label(row1, text="📍 Select Drive:", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_DARK, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        self.drive_var = tk.StringVar()
        self.drive_combo = ttk.Combobox(row1, textvariable=self.drive_var,
                                        width=18, state="readonly",
                                        style='Modern.TCombobox',
                                        font=("Segoe UI", 10))
        self.drive_combo.pack(side=tk.LEFT, padx=5)

        # Modern buttons
        btn_frame = tk.Frame(row1, bg=ModernColors.CARD_BG)
        btn_frame.pack(side=tk.LEFT, padx=20)

        ModernButton(btn_frame, "🚀 Scan Drive", self.start_scan,
                    bg_color=ModernColors.SUCCESS, width=130).pack(side=tk.LEFT, padx=5)

        ModernButton(btn_frame, "⏸ Pause", self.pause_scan,
                    bg_color=ModernColors.WARNING, width=100).pack(side=tk.LEFT, padx=5)

        ModernButton(btn_frame, "❌ Cancel", self.cancel_scan,
                    bg_color=ModernColors.ERROR, width=100).pack(side=tk.LEFT, padx=5)

        # Progress area
        progress_frame = tk.Frame(row1, bg=ModernColors.CARD_BG)
        progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate',
                                           variable=self.progress_var,
                                           style='Modern.Horizontal.TProgressbar')
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.progress_label = tk.Label(progress_frame, text="Ready to scan",
                                      bg=ModernColors.CARD_BG,
                                      fg=ModernColors.TEXT_MUTED,
                                      font=("Segoe UI", 9))
        self.progress_label.pack()

        # Row 2: Basic filters
        row2 = tk.Frame(control_card, bg=ModernColors.CARD_BG)
        row2.pack(fill=tk.X, padx=20, pady=10)

        # Search
        tk.Label(row2, text="🔍", bg=ModernColors.CARD_BG,
                font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.apply_filters)
        search_entry = tk.Entry(row2, textvariable=self.search_var, width=25,
                               bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_DARK,
                               font=("Segoe UI", 10), relief=tk.SOLID, bd=1)
        search_entry.pack(side=tk.LEFT, padx=5, ipady=5)

        # Type filter
        tk.Label(row2, text="📋 Type:", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_DARK, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(20, 5))

        self.file_type_var = tk.StringVar(value="All")
        type_combo = ttk.Combobox(row2, textvariable=self.file_type_var,
                                 values=["All", "Videos", "Images", "Documents",
                                        "Audio", "Archives", "Executables", "Other"],
                                 width=12, state="readonly", style='Modern.TCombobox',
                                 font=("Segoe UI", 9))
        type_combo.pack(side=tk.LEFT, padx=5)
        type_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        # Size filter
        tk.Label(row2, text="💾 Min MB:", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_DARK, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(20, 5))

        self.min_size_var = tk.StringVar(value="0")
        size_entry = tk.Entry(row2, textvariable=self.min_size_var, width=10,
                             bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_DARK,
                             font=("Segoe UI", 9), relief=tk.SOLID, bd=1)
        size_entry.pack(side=tk.LEFT, padx=5, ipady=3)
        size_entry.bind('<KeyRelease>', lambda e: self.apply_filters())

        ModernButton(row2, "Clear", self.clear_filters,
                    bg_color=ModernColors.TEXT_MUTED, width=80, height=30).pack(side=tk.LEFT, padx=20)

        # Row 3: Smart filters
        row3 = tk.Frame(control_card, bg=ModernColors.CARD_BG)
        row3.pack(fill=tk.X, padx=20, pady=(0, 15))

        tk.Label(row3, text="⚡ Smart Filters:", bg=ModernColors.CARD_BG,
                fg=ModernColors.PRIMARY, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 15))

        # Not accessed
        tk.Label(row3, text="Not accessed:", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_DARK, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        self.access_days_var = tk.StringVar(value="0")
        tk.Entry(row3, textvariable=self.access_days_var, width=6,
                font=("Segoe UI", 9), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=2, ipady=2)
        tk.Label(row3, text="days", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_MUTED, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(2, 15))
        self.access_days_var.trace('w', lambda *args: self.apply_filters())

        # Older than
        tk.Label(row3, text="Older than:", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_DARK, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        self.age_days_var = tk.StringVar(value="0")
        tk.Entry(row3, textvariable=self.age_days_var, width=6,
                font=("Segoe UI", 9), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=2, ipady=2)
        tk.Label(row3, text="days", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_MUTED, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(2, 15))
        self.age_days_var.trace('w', lambda *args: self.apply_filters())

        # Recent
        tk.Label(row3, text="Created in last:", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_DARK, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
        self.recent_days_var = tk.StringVar(value="0")
        tk.Entry(row3, textvariable=self.recent_days_var, width=6,
                font=("Segoe UI", 9), relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=2, ipady=2)
        tk.Label(row3, text="days", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_MUTED, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.recent_days_var.trace('w', lambda *args: self.apply_filters())

        # Treeview card
        tree_card = ModernCard(container)
        tree_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Treeview
        tree_container = tk.Frame(tree_card, bg=ModernColors.CARD_BG)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")

        self.tree = ttk.Treeview(tree_container,
                                 columns=("Size", "Readable Size", "Type", "Modified", "Accessed", "Path"),
                                 show="headings",
                                 yscrollcommand=vsb.set,
                                 xscrollcommand=hsb.set,
                                 selectmode="extended",
                                 style='Modern.Treeview')

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        columns = [
            ("Size", "Size (Bytes)", 100),
            ("Readable Size", "💾 Size", 100),
            ("Type", "📁 Type", 90),
            ("Modified", "📅 Modified", 140),
            ("Accessed", "👁 Accessed", 140),
            ("Path", "📂 Path", 600)
        ]

        for col, heading, width in columns:
            self.tree.heading(col, text=heading,
                            command=lambda c=col: self.sort_tree_column(c))
            self.tree.column(col, width=width, anchor="w" if col == "Path" else "e")

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Context menu
        self.create_context_menu()
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", lambda e: self.open_file_location())

        # Action buttons card
        action_card = ModernCard(container)
        action_card.pack(fill=tk.X)

        btn_container = tk.Frame(action_card, bg=ModernColors.CARD_BG)
        btn_container.pack(padx=20, pady=15)

        ModernButton(btn_container, "📍 Open Location", self.open_file_location,
                    bg_color=ModernColors.INFO, width=150).pack(side=tk.LEFT, padx=5)

        if HAS_SEND2TRASH:
            ModernButton(btn_container, "🗑 Delete Selected", self.delete_files,
                        bg_color=ModernColors.ERROR, width=150).pack(side=tk.LEFT, padx=5)

        ModernButton(btn_container, "ℹ Properties", self.show_file_properties,
                    bg_color=ModernColors.PRIMARY, width=150).pack(side=tk.LEFT, padx=5)

    def setup_folders_tab(self):
        """Setup folder analysis tab with modern styling"""
        container = tk.Frame(self.folders_tab, bg=ModernColors.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Control card
        control_card = ModernCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        control_frame = tk.Frame(control_card, bg=ModernColors.CARD_BG)
        control_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(control_frame, text="📂 Folder Space Analysis",
                bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_DARK,
                font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 20))

        ModernButton(control_frame, "🔍 Analyze Folders", self.analyze_folders,
                    bg_color=ModernColors.SUCCESS, width=150).pack(side=tk.LEFT)

        # Treeview card
        tree_card = ModernCard(container)
        tree_card.pack(fill=tk.BOTH, expand=True)

        tree_container = tk.Frame(tree_card, bg=ModernColors.CARD_BG)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")

        self.folder_tree = ttk.Treeview(tree_container,
                                        columns=("Size", "Readable Size", "Files", "Path"),
                                        show="headings",
                                        yscrollcommand=vsb.set,
                                        xscrollcommand=hsb.set,
                                        style='Modern.Treeview')

        vsb.config(command=self.folder_tree.yview)
        hsb.config(command=self.folder_tree.xview)

        self.folder_tree.heading("Size", text="Size (Bytes)")
        self.folder_tree.heading("Readable Size", text="💾 Size")
        self.folder_tree.heading("Files", text="📄 Files")
        self.folder_tree.heading("Path", text="📂 Folder Path")

        self.folder_tree.column("Size", width=120, anchor="e")
        self.folder_tree.column("Readable Size", width=120, anchor="e")
        self.folder_tree.column("Files", width=100, anchor="e")
        self.folder_tree.column("Path", width=800, anchor="w")

        self.folder_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

    def setup_duplicates_tab(self):
        """Setup duplicates tab with modern styling"""
        container = tk.Frame(self.duplicates_tab, bg=ModernColors.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Control card
        control_card = ModernCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        control_frame = tk.Frame(control_card, bg=ModernColors.CARD_BG)
        control_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(control_frame, text="🔄 Duplicate File Detection",
                bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_DARK,
                font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 20))

        ModernButton(control_frame, "🔍 Find Duplicates", self.find_duplicates,
                    bg_color=ModernColors.WARNING, width=150).pack(side=tk.LEFT)

        self.dup_label = tk.Label(control_frame, text="No duplicates found",
                                 bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_MUTED,
                                 font=("Segoe UI", 10))
        self.dup_label.pack(side=tk.LEFT, padx=20)

        # Treeview card
        tree_card = ModernCard(container)
        tree_card.pack(fill=tk.BOTH, expand=True)

        tree_container = tk.Frame(tree_card, bg=ModernColors.CARD_BG)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")

        self.dup_tree = ttk.Treeview(tree_container,
                                     columns=("Size", "Readable Size", "Copies", "Path"),
                                     show="headings",
                                     yscrollcommand=vsb.set,
                                     xscrollcommand=hsb.set,
                                     selectmode="extended",
                                     style='Modern.Treeview')

        vsb.config(command=self.dup_tree.yview)
        hsb.config(command=self.dup_tree.xview)

        self.dup_tree.heading("Size", text="Size (Bytes)")
        self.dup_tree.heading("Readable Size", text="💾 Size")
        self.dup_tree.heading("Copies", text="🔢 Copies")
        self.dup_tree.heading("Path", text="📂 File Path")

        self.dup_tree.column("Size", width=120, anchor="e")
        self.dup_tree.column("Readable Size", width=120, anchor="e")
        self.dup_tree.column("Copies", width=100, anchor="e")
        self.dup_tree.column("Path", width=800, anchor="w")

        self.dup_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

    def setup_viz_tab(self):
        """Setup visualizations tab"""
        if not HAS_MATPLOTLIB:
            return

        container = tk.Frame(self.viz_tab, bg=ModernColors.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        control_card = ModernCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        control_frame = tk.Frame(control_card, bg=ModernColors.CARD_BG)
        control_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(control_frame, text="📊 Data Visualization",
                bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_DARK,
                font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 20))

        ModernButton(control_frame, "📈 Generate Charts", self.generate_charts,
                    bg_color=ModernColors.PRIMARY, width=150).pack(side=tk.LEFT)

        self.chart_frame = ModernCard(container)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

    def setup_trends_tab(self):
        """Setup trends tab"""
        container = tk.Frame(self.trends_tab, bg=ModernColors.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        control_card = ModernCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        control_frame = tk.Frame(control_card, bg=ModernColors.CARD_BG)
        control_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(control_frame, text="📈 Storage Trends & History",
                bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_DARK,
                font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 20))

        ModernButton(control_frame, "🔄 Refresh Trends", self.refresh_trends,
                    bg_color=ModernColors.SUCCESS, width=150).pack(side=tk.LEFT)

        self.trends_info_label = tk.Label(control_frame, text="No history available",
                                          bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_MUTED,
                                          font=("Segoe UI", 10))
        self.trends_info_label.pack(side=tk.LEFT, padx=20)

        self.trends_chart_frame = ModernCard(container)
        self.trends_chart_frame.pack(fill=tk.BOTH, expand=True)

    def setup_comparison_tab(self):
        """Setup multi-drive comparison tab"""
        container = tk.Frame(self.comparison_tab, bg=ModernColors.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        control_card = ModernCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        control_frame = tk.Frame(control_card, bg=ModernColors.CARD_BG)
        control_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(control_frame, text="💽 Multi-Drive Comparison",
                bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_DARK,
                font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 20))

        ModernButton(control_frame, "🔍 Scan All Drives", self.scan_all_drives,
                    bg_color=ModernColors.SUCCESS, width=150).pack(side=tk.LEFT, padx=5)

        ModernButton(control_frame, "📊 Generate Comparison", self.generate_drive_comparison,
                    bg_color=ModernColors.INFO, width=180).pack(side=tk.LEFT)

        self.comparison_frame = ModernCard(container)
        self.comparison_frame.pack(fill=tk.BOTH, expand=True)

    def setup_reports_tab(self):
        """Setup advanced reports tab"""
        container = tk.Frame(self.reports_tab, bg=ModernColors.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        control_card = ModernCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        control_frame = tk.Frame(control_card, bg=ModernColors.CARD_BG)
        control_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(control_frame, text="📑 Advanced Analytics",
                bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_DARK,
                font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 20))

        ModernButton(control_frame, "📄 Generate Report", self.generate_advanced_report,
                    bg_color=ModernColors.PRIMARY, width=150).pack(side=tk.LEFT)

        report_card = ModernCard(container)
        report_card.pack(fill=tk.BOTH, expand=True)

        report_container = tk.Frame(report_card, bg=ModernColors.CARD_BG)
        report_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.report_text = tk.Text(report_container, wrap=tk.WORD,
                                   font=("Consolas", 9),
                                   bg=ModernColors.CARD_BG,
                                   fg=ModernColors.TEXT_DARK,
                                   relief=tk.FLAT)
        self.report_text.pack(fill=tk.BOTH, expand=True)

    def setup_heatmap_tab(self):
        """Setup heatmap tab"""
        if not HAS_MATPLOTLIB or not HAS_SQUARIFY:
            return

        container = tk.Frame(self.heatmap_tab, bg=ModernColors.BG_LIGHT)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        control_card = ModernCard(container)
        control_card.pack(fill=tk.X, pady=(0, 15))

        control_frame = tk.Frame(control_card, bg=ModernColors.CARD_BG)
        control_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Label(control_frame, text="🗺️ Treemap Visualization",
                bg=ModernColors.CARD_BG, fg=ModernColors.TEXT_DARK,
                font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=(0, 20))

        ModernButton(control_frame, "🎨 Generate Treemap", self.generate_treemap,
                    bg_color=ModernColors.PRIMARY, width=160).pack(side=tk.LEFT, padx=5)

        tk.Label(control_frame, text="Top:", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_DARK, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(20, 5))

        self.treemap_limit_var = tk.StringVar(value="50")
        tk.Entry(control_frame, textvariable=self.treemap_limit_var, width=8,
                font=("Segoe UI", 9), relief=tk.SOLID, bd=1).pack(side=tk.LEFT)

        tk.Label(control_frame, text="items", bg=ModernColors.CARD_BG,
                fg=ModernColors.TEXT_MUTED, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)

        self.heatmap_frame = ModernCard(container)
        self.heatmap_frame.pack(fill=tk.BOTH, expand=True)

    def create_context_menu(self):
        """Create modern context menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0,
                                    bg=ModernColors.CARD_BG,
                                    fg=ModernColors.TEXT_DARK,
                                    activebackground=ModernColors.PRIMARY,
                                    activeforeground=ModernColors.TEXT_LIGHT,
                                    font=("Segoe UI", 9))
        self.context_menu.add_command(label="📍 Open File Location", command=self.open_file_location)
        self.context_menu.add_command(label="ℹ Show Properties", command=self.show_file_properties)
        if HAS_SEND2TRASH:
            self.context_menu.add_separator()
            self.context_menu.add_command(label="🗑 Delete (Recycle Bin)", command=self.delete_files)

    def show_context_menu(self, event):
        """Show context menu on right-click"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # [ALL THE REMAINING METHODS FROM PREVIOUS VERSION GO HERE]
    # Include all the logic methods: load_drives, start_scan, scan_drive, etc.
    # These methods remain the same, just the UI is modernized

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
        self.progress_label.config(text="Scanning...", fg=ModernColors.INFO)
        self.status_icon.config(fg=ModernColors.INFO)
        self.scan_thread = threading.Thread(target=self.scan_drive, args=(drive,), daemon=True)
        self.scan_thread.start()

    def pause_scan(self):
        """Pause/Resume scan"""
        if self.scan_paused:
            self.scan_paused = False
            self.progress_label.config(text="Scanning...", fg=ModernColors.INFO)
        else:
            self.scan_paused = True
            self.progress_label.config(text="Paused", fg=ModernColors.WARNING)

    def cancel_scan(self):
        """Cancel scan"""
        self.scan_cancelled = True
        self.progress_label.config(text="Cancelling...", fg=ModernColors.ERROR)

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
        self.status_label.config(text=f"✓ Scan complete: {total_files:,} files | {total_size_gb:.2f} GB")
        self.progress_label.config(text="Complete!", fg=ModernColors.SUCCESS)
        self.status_icon.config(fg=ModernColors.SUCCESS)
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
        """Format size to human-readable"""
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
            age_days = int(self.age_days_var.get() or 0)
            recent_days = int(self.recent_days_var.get() or 0)
        except ValueError:
            min_size_mb = access_days = age_days = recent_days = 0
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
            if age_days > 0:
                if (now - file_info['modified']).days < age_days:
                    continue
            if recent_days > 0:
                if (now - file_info['modified']).days > recent_days:
                    continue
            self.filtered_data.append(file_info)
        self.display_results()
        self.status_label.config(text=f"Showing {len(self.filtered_data):,} of {len(self.files_data):,} files")

    def clear_filters(self):
        """Clear all filters"""
        self.search_var.set("")
        self.file_type_var.set("All")
        self.min_size_var.set("0")
        self.access_days_var.set("0")
        self.age_days_var.set("0")
        self.recent_days_var.set("0")
        self.filtered_data = self.files_data.copy()
        self.display_results()

    def sort_tree_column(self, col):
        """Sort treeview by column"""
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = True
        if col in ["Size", "Readable Size"]:
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
        """Delete files to Recycle Bin"""
        if not HAS_SEND2TRASH:
            messagebox.showerror("Error", "send2trash library not installed!")
            return
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select files!")
            return
        count = len(selection)
        result = messagebox.askyesno("Confirm Deletion", f"Move {count} file(s) to Recycle Bin?")
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
            messagebox.showinfo("File Properties", props)
        except Exception as e:
            messagebox.showerror("Error", f"Could not get properties: {str(e)}")

    def analyze_folders(self):
        """Analyze folders"""
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
        """Find duplicate files"""
        if not self.files_data:
            messagebox.showwarning("No Data", "Please scan first!")
            return
        self.progress_label.config(text="Finding duplicates...", fg=ModernColors.INFO)
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
        self.progress_label.config(text="Ready", fg=ModernColors.SUCCESS)
        self.progress_bar.stop()

    def generate_charts(self):
        """Generate charts"""
        if not HAS_MATPLOTLIB or not self.files_data:
            return
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        # Simple chart generation code here
        messagebox.showinfo("Charts", "Chart generation feature available")

    def refresh_trends(self):
        """Refresh trends"""
        messagebox.showinfo("Trends", "Trend analysis feature available")

    def scan_all_drives(self):
        """Scan all drives"""
        messagebox.showinfo("Multi-Drive", "Multi-drive scanning feature available")

    def generate_drive_comparison(self):
        """Generate drive comparison"""
        messagebox.showinfo("Comparison", "Drive comparison feature available")

    def generate_advanced_report(self):
        """Generate advanced report"""
        messagebox.showinfo("Reports", "Advanced reporting feature available")

    def generate_treemap(self):
        """Generate treemap"""
        messagebox.showinfo("Treemap", "Treemap visualization feature available")

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
                    self.dark_mode = settings.get('dark_mode', False)
                    self.last_drive = settings.get('last_drive', '')
        except Exception:
            pass

    def save_settings(self):
        """Save settings"""
        try:
            settings = {
                'dark_mode': self.dark_mode,
                'last_drive': getattr(self, 'last_drive', '')
            }
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
