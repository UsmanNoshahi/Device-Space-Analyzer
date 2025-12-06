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


class SpaceScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ultra Disk Space Scanner")
        self.root.geometry("1600x900")

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

        # Setup UI
        self.setup_ui()
        self.load_drives()
        self.apply_theme()

        # Restore last drive
        if hasattr(self, 'last_drive') and self.last_drive:
            self.drive_var.set(self.last_drive)

    def setup_ui(self):
        """Setup the user interface"""
        # Create menu bar
        self.create_menu_bar()

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 1: File Scanner
        self.files_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.files_tab, text="File Scanner")
        self.setup_files_tab()

        # Tab 2: Folder Analysis
        self.folders_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.folders_tab, text="Folder Analysis")
        self.setup_folders_tab()

        # Tab 3: Duplicates
        self.duplicates_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.duplicates_tab, text="Duplicate Files")
        self.setup_duplicates_tab()

        # Tab 4: Visualizations
        if HAS_MATPLOTLIB:
            self.viz_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.viz_tab, text="Visualizations")
            self.setup_viz_tab()

        # Tab 5: Trends & History (NEW)
        self.trends_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.trends_tab, text="Trends & History")
        self.setup_trends_tab()

        # Tab 6: Multi-Drive Comparison (NEW)
        self.comparison_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.comparison_tab, text="Drive Comparison")
        self.setup_comparison_tab()

        # Tab 7: Advanced Reports (NEW)
        self.reports_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.reports_tab, text="Advanced Reports")
        self.setup_reports_tab()

        # Tab 8: Heatmap View (NEW)
        if HAS_MATPLOTLIB and HAS_SQUARIFY:
            self.heatmap_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.heatmap_tab, text="Heatmap")
            self.setup_heatmap_tab()

        # Status bar
        self.status_label = tk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)

    def create_menu_bar(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Scan Specific Folder", command=self.scan_folder)
        file_menu.add_command(label="Scan All Drives", command=self.scan_all_drives)
        file_menu.add_separator()
        file_menu.add_command(label="Export to CSV", command=self.export_csv)
        if HAS_REPORTLAB:
            file_menu.add_command(label="Export to PDF", command=self.export_pdf)
        file_menu.add_command(label="Save Results", command=self.save_results)
        file_menu.add_command(label="Load Results", command=self.load_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Dark Mode", command=self.toggle_dark_mode)
        view_menu.add_command(label="Refresh", command=self.refresh_display)
        view_menu.add_command(label="Clear History", command=self.clear_history)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Find Duplicates", command=self.find_duplicates)
        tools_menu.add_command(label="Analyze Folders", command=self.analyze_folders)
        tools_menu.add_command(label="Generate Reports", command=self.generate_advanced_report)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def setup_files_tab(self):
        """Setup files scanner tab"""
        # Top control frame
        control_frame = tk.Frame(self.files_tab, padx=10, pady=10)
        control_frame.pack(fill=tk.X)

        # Row 1: Drive/Folder selection and scan controls
        row1 = tk.Frame(control_frame)
        row1.pack(fill=tk.X, pady=5)

        tk.Label(row1, text="Select Drive:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        self.drive_var = tk.StringVar()
        self.drive_combo = ttk.Combobox(row1, textvariable=self.drive_var,
                                        width=15, state="readonly")
        self.drive_combo.pack(side=tk.LEFT, padx=5)

        self.scan_btn = tk.Button(row1, text="Scan Drive",
                                  command=self.start_scan, bg="#4CAF50",
                                  fg="white", font=("Arial", 10, "bold"),
                                  padx=20, pady=5)
        self.scan_btn.pack(side=tk.LEFT, padx=5)

        self.pause_btn = tk.Button(row1, text="Pause",
                                   command=self.pause_scan, bg="#FF9800",
                                   fg="white", font=("Arial", 10, "bold"),
                                   padx=20, pady=5, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = tk.Button(row1, text="Cancel",
                                    command=self.cancel_scan, bg="#F44336",
                                    fg="white", font=("Arial", 10, "bold"),
                                    padx=20, pady=5, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(row1, mode='indeterminate',
                                           variable=self.progress_var)
        self.progress_bar.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        self.progress_label = tk.Label(row1, text="Ready", font=("Arial", 9), fg="gray")
        self.progress_label.pack(side=tk.LEFT, padx=5)

        # Row 2: Basic Filters
        row2 = tk.Frame(control_frame)
        row2.pack(fill=tk.X, pady=5)

        tk.Label(row2, text="Search:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.apply_filters)
        search_entry = tk.Entry(row2, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="File Type:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        self.file_type_var = tk.StringVar(value="All")
        file_type_combo = ttk.Combobox(row2, textvariable=self.file_type_var,
                                       values=["All", "Videos", "Images", "Documents",
                                              "Audio", "Archives", "Executables", "Other"],
                                       width=15, state="readonly")
        file_type_combo.pack(side=tk.LEFT, padx=5)
        file_type_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        tk.Label(row2, text="Min Size (MB):", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        self.min_size_var = tk.StringVar(value="0")
        min_size_entry = tk.Entry(row2, textvariable=self.min_size_var, width=10)
        min_size_entry.pack(side=tk.LEFT, padx=5)
        min_size_entry.bind('<KeyRelease>', lambda e: self.apply_filters())

        tk.Button(row2, text="Clear Filters", command=self.clear_filters).pack(side=tk.LEFT, padx=5)

        # Row 3: Smart Filters (NEW)
        row3 = tk.Frame(control_frame)
        row3.pack(fill=tk.X, pady=5)

        tk.Label(row3, text="Smart Filters:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        tk.Label(row3, text="Not accessed in:", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)

        self.access_days_var = tk.StringVar(value="0")
        access_days_entry = tk.Entry(row3, textvariable=self.access_days_var, width=8)
        access_days_entry.pack(side=tk.LEFT, padx=2)
        access_days_entry.bind('<KeyRelease>', lambda e: self.apply_filters())

        tk.Label(row3, text="days", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)

        tk.Label(row3, text="| Older than:", font=("Arial", 9)).pack(side=tk.LEFT, padx=10)

        self.age_days_var = tk.StringVar(value="0")
        age_days_entry = tk.Entry(row3, textvariable=self.age_days_var, width=8)
        age_days_entry.pack(side=tk.LEFT, padx=2)
        age_days_entry.bind('<KeyRelease>', lambda e: self.apply_filters())

        tk.Label(row3, text="days", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)

        tk.Label(row3, text="| Created in last:", font=("Arial", 9)).pack(side=tk.LEFT, padx=10)

        self.recent_days_var = tk.StringVar(value="0")
        recent_days_entry = tk.Entry(row3, textvariable=self.recent_days_var, width=8)
        recent_days_entry.pack(side=tk.LEFT, padx=2)
        recent_days_entry.bind('<KeyRelease>', lambda e: self.apply_filters())

        tk.Label(row3, text="days", font=("Arial", 9)).pack(side=tk.LEFT, padx=2)

        # Treeview frame
        tree_frame = tk.Frame(self.files_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview with access time column
        self.tree = ttk.Treeview(tree_frame,
                                 columns=("Size", "Readable Size", "Type", "Modified", "Accessed", "Path"),
                                 show="headings",
                                 yscrollcommand=vsb.set,
                                 xscrollcommand=hsb.set,
                                 selectmode="extended")

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Column headings with sort capability
        columns = [
            ("Size", "Size (Bytes)", 100),
            ("Readable Size", "Size", 100),
            ("Type", "Type", 90),
            ("Modified", "Modified", 140),
            ("Accessed", "Last Accessed", 140),
            ("Path", "File Path", 600)
        ]

        for col, heading, width in columns:
            self.tree.heading(col, text=heading,
                            command=lambda c=col: self.sort_tree_column(c))
            self.tree.column(col, width=width, anchor="w" if col == "Path" else "e")

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Right-click context menu
        self.create_context_menu()
        self.tree.bind("<Button-3>", self.show_context_menu)

        # Double-click to open location
        self.tree.bind("<Double-1>", lambda e: self.open_file_location())

        # Button frame
        button_frame = tk.Frame(self.files_tab, padx=10, pady=10)
        button_frame.pack(fill=tk.X)

        tk.Button(button_frame, text="Open File Location",
                 command=self.open_file_location, bg="#2196F3", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        if HAS_SEND2TRASH:
            tk.Button(button_frame, text="Delete Selected (to Recycle Bin)",
                     command=self.delete_files, bg="#F44336", fg="white",
                     font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="Show Properties",
                 command=self.show_file_properties, bg="#9C27B0", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

    def setup_folders_tab(self):
        """Setup folder analysis tab"""
        control_frame = tk.Frame(self.folders_tab, padx=10, pady=10)
        control_frame.pack(fill=tk.X)

        tk.Button(control_frame, text="Analyze Folders",
                 command=self.analyze_folders, bg="#4CAF50", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Label(control_frame, text="Top folders by size",
                font=("Arial", 10)).pack(side=tk.LEFT, padx=20)

        # Folder treeview
        tree_frame = tk.Frame(self.folders_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        self.folder_tree = ttk.Treeview(tree_frame,
                                        columns=("Size", "Readable Size", "Files", "Path"),
                                        show="headings",
                                        yscrollcommand=vsb.set,
                                        xscrollcommand=hsb.set)

        vsb.config(command=self.folder_tree.yview)
        hsb.config(command=self.folder_tree.xview)

        self.folder_tree.heading("Size", text="Size (Bytes)")
        self.folder_tree.heading("Readable Size", text="Size")
        self.folder_tree.heading("Files", text="File Count")
        self.folder_tree.heading("Path", text="Folder Path")

        self.folder_tree.column("Size", width=120, anchor="e")
        self.folder_tree.column("Readable Size", width=120, anchor="e")
        self.folder_tree.column("Files", width=100, anchor="e")
        self.folder_tree.column("Path", width=800, anchor="w")

        self.folder_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Button frame
        button_frame = tk.Frame(self.folders_tab, padx=10, pady=10)
        button_frame.pack(fill=tk.X)

        tk.Button(button_frame, text="Open Folder",
                 command=self.open_folder, bg="#2196F3", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

    def setup_duplicates_tab(self):
        """Setup duplicates detection tab"""
        control_frame = tk.Frame(self.duplicates_tab, padx=10, pady=10)
        control_frame.pack(fill=tk.X)

        tk.Button(control_frame, text="Find Duplicates",
                 command=self.find_duplicates, bg="#4CAF50", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        self.dup_label = tk.Label(control_frame, text="No duplicates found",
                                 font=("Arial", 10))
        self.dup_label.pack(side=tk.LEFT, padx=20)

        # Duplicates treeview
        tree_frame = tk.Frame(self.duplicates_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        self.dup_tree = ttk.Treeview(tree_frame,
                                     columns=("Size", "Readable Size", "Copies", "Path"),
                                     show="headings",
                                     yscrollcommand=vsb.set,
                                     xscrollcommand=hsb.set,
                                     selectmode="extended")

        vsb.config(command=self.dup_tree.yview)
        hsb.config(command=self.dup_tree.xview)

        self.dup_tree.heading("Size", text="Size (Bytes)")
        self.dup_tree.heading("Readable Size", text="Size")
        self.dup_tree.heading("Copies", text="Duplicates")
        self.dup_tree.heading("Path", text="File Path")

        self.dup_tree.column("Size", width=120, anchor="e")
        self.dup_tree.column("Readable Size", width=120, anchor="e")
        self.dup_tree.column("Copies", width=100, anchor="e")
        self.dup_tree.column("Path", width=800, anchor="w")

        self.dup_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Button frame
        button_frame = tk.Frame(self.duplicates_tab, padx=10, pady=10)
        button_frame.pack(fill=tk.X)

        tk.Button(button_frame, text="Open File Location",
                 command=self.open_duplicate_location, bg="#2196F3", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        if HAS_SEND2TRASH:
            tk.Button(button_frame, text="Delete Selected Duplicates",
                     command=self.delete_duplicates, bg="#F44336", fg="white",
                     font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

    def setup_viz_tab(self):
        """Setup visualizations tab"""
        if not HAS_MATPLOTLIB:
            return

        control_frame = tk.Frame(self.viz_tab, padx=10, pady=10)
        control_frame.pack(fill=tk.X)

        tk.Button(control_frame, text="Generate Charts",
                 command=self.generate_charts, bg="#4CAF50", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        # Canvas for charts
        self.chart_frame = tk.Frame(self.viz_tab)
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def setup_trends_tab(self):
        """Setup trends and history tab (NEW)"""
        control_frame = tk.Frame(self.trends_tab, padx=10, pady=10)
        control_frame.pack(fill=tk.X)

        tk.Label(control_frame, text="Disk Space Trends & History",
                font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10)

        tk.Button(control_frame, text="Refresh Trends",
                 command=self.refresh_trends, bg="#4CAF50", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        # Info label
        self.trends_info_label = tk.Label(control_frame, text="No history available",
                                          font=("Arial", 10))
        self.trends_info_label.pack(side=tk.LEFT, padx=20)

        # Canvas for trends charts
        self.trends_chart_frame = tk.Frame(self.trends_tab)
        self.trends_chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def setup_comparison_tab(self):
        """Setup multi-drive comparison tab (NEW)"""
        control_frame = tk.Frame(self.comparison_tab, padx=10, pady=10)
        control_frame.pack(fill=tk.X)

        tk.Label(control_frame, text="Multi-Drive Comparison",
                font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10)

        tk.Button(control_frame, text="Scan All Drives",
                 command=self.scan_all_drives, bg="#4CAF50", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(control_frame, text="Generate Comparison",
                 command=self.generate_drive_comparison, bg="#2196F3", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        # Comparison display frame
        self.comparison_frame = tk.Frame(self.comparison_tab)
        self.comparison_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def setup_reports_tab(self):
        """Setup advanced reports tab (NEW)"""
        control_frame = tk.Frame(self.reports_tab, padx=10, pady=10)
        control_frame.pack(fill=tk.X)

        tk.Label(control_frame, text="Advanced Analytics & Reports",
                font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10)

        tk.Button(control_frame, text="Generate Full Report",
                 command=self.generate_advanced_report, bg="#4CAF50", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        # Report display area
        self.report_text = tk.Text(self.reports_tab, wrap=tk.WORD, font=("Courier", 10))
        self.report_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Scrollbar for report
        report_scroll = ttk.Scrollbar(self.report_text, command=self.report_text.yview)
        report_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.report_text.config(yscrollcommand=report_scroll.set)

    def setup_heatmap_tab(self):
        """Setup heatmap/treemap view tab (NEW)"""
        if not HAS_MATPLOTLIB or not HAS_SQUARIFY:
            return

        control_frame = tk.Frame(self.heatmap_tab, padx=10, pady=10)
        control_frame.pack(fill=tk.X)

        tk.Label(control_frame, text="Treemap Visualization",
                font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10)

        tk.Button(control_frame, text="Generate Treemap",
                 command=self.generate_treemap, bg="#4CAF50", fg="white",
                 font=("Arial", 10, "bold"), padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Label(control_frame, text="Top:", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)

        self.treemap_limit_var = tk.StringVar(value="50")
        limit_entry = tk.Entry(control_frame, textvariable=self.treemap_limit_var, width=8)
        limit_entry.pack(side=tk.LEFT, padx=2)

        tk.Label(control_frame, text="items", font=("Arial", 10)).pack(side=tk.LEFT, padx=2)

        # Canvas for treemap
        self.heatmap_frame = tk.Frame(self.heatmap_tab)
        self.heatmap_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def create_context_menu(self):
        """Create right-click context menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open File Location", command=self.open_file_location)
        self.context_menu.add_command(label="Show Properties", command=self.show_file_properties)
        if HAS_SEND2TRASH:
            self.context_menu.add_separator()
            self.context_menu.add_command(label="Delete (to Recycle Bin)", command=self.delete_files)

    def show_context_menu(self, event):
        """Show context menu on right-click"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

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

        # Save last drive
        self.last_drive = drive
        self.save_settings()

        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.files_data = []
        self.filtered_data = []
        self.scanning = True
        self.scan_paused = False
        self.scan_cancelled = False

        # Update UI
        self.scan_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_bar.start()
        self.progress_label.config(text="Scanning...", fg="blue")

        # Start scanning thread
        self.scan_thread = threading.Thread(target=self.scan_drive, args=(drive,), daemon=True)
        self.scan_thread.start()

    def scan_folder(self):
        """Scan specific folder"""
        folder = filedialog.askdirectory(title="Select Folder to Scan")
        if not folder:
            return

        # Set drive variable and start scan
        self.drive_var.set(folder)
        self.start_scan()

    def scan_all_drives(self):
        """Scan all available drives (NEW)"""
        if self.scanning:
            messagebox.showwarning("Scanning", "A scan is already in progress!")
            return

        drives = self.drive_combo['values']
        if not drives:
            messagebox.showerror("Error", "No drives found!")
            return

        self.all_drives_data = {}
        self.progress_label.config(text="Scanning all drives...", fg="blue")

        # Scan each drive
        thread = threading.Thread(target=self._scan_all_drives_thread, args=(drives,), daemon=True)
        thread.start()

    def _scan_all_drives_thread(self, drives):
        """Thread function to scan all drives"""
        for i, drive in enumerate(drives):
            self.root.after(0, self.update_progress,
                           f"Scanning drive {i+1}/{len(drives)}: {drive}")

            drive_data = {
                'files': [],
                'total_size': 0,
                'total_files': 0
            }

            try:
                for root, dirs, files in os.walk(drive):
                    for file in files:
                        try:
                            file_path = os.path.join(root, file)
                            file_stat = os.stat(file_path)
                            file_size = file_stat.st_size

                            drive_data['files'].append({
                                'path': file_path,
                                'size': file_size
                            })
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
        self.progress_label.config(text="All drives scanned!", fg="green")
        messagebox.showinfo("Scan Complete",
                           f"Scanned {len(self.all_drives_data)} drives successfully!")

        # Auto-generate comparison
        self.generate_drive_comparison()

    def pause_scan(self):
        """Pause/Resume scan"""
        if self.scan_paused:
            self.scan_paused = False
            self.pause_btn.config(text="Pause")
            self.progress_label.config(text="Scanning...", fg="blue")
        else:
            self.scan_paused = True
            self.pause_btn.config(text="Resume")
            self.progress_label.config(text="Paused", fg="orange")

    def cancel_scan(self):
        """Cancel scan"""
        self.scan_cancelled = True
        self.progress_label.config(text="Cancelling...", fg="red")

    def scan_drive(self, path):
        """Scan drive/folder and collect file information"""
        file_count = 0
        scan_start_time = datetime.now()

        try:
            for root, dirs, files in os.walk(path):
                # Check for pause
                while self.scan_paused and not self.scan_cancelled:
                    time.sleep(0.1)

                # Check for cancel
                if self.scan_cancelled:
                    break

                # Update progress
                if file_count % 100 == 0:
                    self.root.after(0, self.update_progress,
                                   f"Scanning... Found {file_count:,} files")

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
            self.root.after(0, messagebox.showerror, "Error",
                           f"Error scanning: {str(e)}")

        # Sort and display
        if not self.scan_cancelled:
            self.files_data.sort(key=lambda x: x['size'], reverse=True)

            # Save to history
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
        """Finish scan and display results"""
        self.filtered_data = self.files_data.copy()
        self.display_results()

        total_files = len(self.files_data)
        total_size_gb = sum(f['size'] for f in self.files_data) / (1024 * 1024 * 1024)

        self.status_label.config(
            text=f"Total files: {total_files:,} | Total size: {total_size_gb:.2f} GB"
        )
        self.progress_label.config(text="Scan complete!", fg="green")

        self.reset_scan_ui()

    def reset_scan_ui(self):
        """Reset scan UI state"""
        self.scanning = False
        self.scan_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED, text="Pause")
        self.cancel_btn.config(state=tk.DISABLED)
        self.progress_bar.stop()

    def update_progress(self, message):
        """Update progress label"""
        self.progress_label.config(text=message)

    def get_file_type(self, extension):
        """Get file type category"""
        ext = extension.lower()

        video_ext = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        image_ext = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp'}
        doc_ext = {'.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.odt'}
        audio_ext = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'}
        archive_ext = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.iso'}
        exe_ext = {'.exe', '.msi', '.dll', '.so', '.app', '.deb', '.rpm'}

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
        """Format size to human-readable format"""
        size_mb = size_bytes / (1024 * 1024)

        if size_mb >= 1020:
            size_gb = size_bytes / (1024 * 1024 * 1024)
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"

    def display_results(self):
        """Display filtered results"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add files to treeview
        for file_info in self.filtered_data:
            self.tree.insert("", tk.END, values=(
                f"{file_info['size']:,}",
                self.format_size(file_info['size']),
                file_info['type'],
                file_info['modified'].strftime("%Y-%m-%d %H:%M:%S"),
                file_info['accessed'].strftime("%Y-%m-%d %H:%M:%S"),
                file_info['path']
            ))

    def apply_filters(self, *args):
        """Apply search and filters including smart filters (NEW)"""
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
            min_size_mb = 0
            access_days = 0
            age_days = 0
            recent_days = 0

        min_size_bytes = min_size_mb * 1024 * 1024
        now = datetime.now()

        # Filter data
        self.filtered_data = []
        for file_info in self.files_data:
            # Search filter
            if search_text and search_text not in file_info['path'].lower():
                continue

            # Type filter
            if file_type != "All" and file_info['type'] != file_type:
                continue

            # Size filter
            if file_info['size'] < min_size_bytes:
                continue

            # Access time filter (NEW)
            if access_days > 0:
                days_since_access = (now - file_info['accessed']).days
                if days_since_access < access_days:
                    continue

            # Age filter (NEW)
            if age_days > 0:
                days_since_modified = (now - file_info['modified']).days
                if days_since_modified < age_days:
                    continue

            # Recent files filter (NEW)
            if recent_days > 0:
                days_since_modified = (now - file_info['modified']).days
                if days_since_modified > recent_days:
                    continue

            self.filtered_data.append(file_info)

        # Display filtered results
        self.display_results()

        # Update status
        self.status_label.config(
            text=f"Showing {len(self.filtered_data):,} of {len(self.files_data):,} files"
        )

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

        # Sort filtered data
        if col == "Size":
            self.filtered_data.sort(key=lambda x: x['size'], reverse=self.sort_reverse)
        elif col == "Readable Size":
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
        """Delete selected files to Recycle Bin"""
        if not HAS_SEND2TRASH:
            messagebox.showerror("Error", "send2trash library not installed!")
            return

        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning("No Selection", "Please select files to delete!")
            return

        # Confirm deletion
        count = len(selection)
        result = messagebox.askyesno("Confirm Deletion",
                                     f"Move {count} file(s) to Recycle Bin?")

        if not result:
            return

        # Delete files
        deleted = 0
        errors = []

        for item in selection:
            file_path = self.tree.item(item)['values'][5]
            try:
                send2trash(file_path)
                self.tree.delete(item)
                # Remove from data
                self.files_data = [f for f in self.files_data if f['path'] != file_path]
                self.filtered_data = [f for f in self.filtered_data if f['path'] != file_path]
                deleted += 1
            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")

        # Show result
        if errors:
            messagebox.showwarning("Deletion Complete",
                                  f"Deleted {deleted} files.\nErrors:\n" + "\n".join(errors[:5]))
        else:
            messagebox.showinfo("Success", f"Moved {deleted} file(s) to Recycle Bin")

        # Update status
        self.status_label.config(
            text=f"Deleted {deleted} files | Showing {len(self.filtered_data):,} files"
        )

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
Created: {datetime.fromtimestamp(stat_info.st_ctime).strftime("%Y-%m-%d %H:%M:%S")}
"""

            messagebox.showinfo("File Properties", props)
        except Exception as e:
            messagebox.showerror("Error", f"Could not get properties: {str(e)}")

    def analyze_folders(self):
        """Analyze folder sizes"""
        if not self.files_data:
            messagebox.showwarning("No Data", "Please scan a drive first!")
            return

        self.folders_data = defaultdict(lambda: {'size': 0, 'files': 0})

        # Calculate folder sizes
        for file_info in self.files_data:
            folder = os.path.dirname(file_info['path'])
            self.folders_data[folder]['size'] += file_info['size']
            self.folders_data[folder]['files'] += 1

        # Sort by size
        sorted_folders = sorted(self.folders_data.items(),
                               key=lambda x: x[1]['size'],
                               reverse=True)

        # Clear tree
        for item in self.folder_tree.get_children():
            self.folder_tree.delete(item)

        # Display top folders
        for folder, info in sorted_folders[:1000]:
            self.folder_tree.insert("", tk.END, values=(
                f"{info['size']:,}",
                self.format_size(info['size']),
                f"{info['files']:,}",
                folder
            ))

        messagebox.showinfo("Analysis Complete",
                           f"Analyzed {len(sorted_folders):,} folders")

    def open_folder(self):
        """Open selected folder"""
        selection = self.folder_tree.selection()

        if not selection:
            messagebox.showwarning("No Selection", "Please select a folder!")
            return

        item = selection[0]
        folder_path = self.folder_tree.item(item)['values'][3]

        try:
            if sys.platform == "win32":
                subprocess.run(['explorer', folder_path])
            elif sys.platform == "darwin":
                subprocess.run(['open', folder_path])
            else:
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {str(e)}")

    def find_duplicates(self):
        """Find duplicate files based on hash"""
        if not self.files_data:
            messagebox.showwarning("No Data", "Please scan a drive first!")
            return

        # Show progress
        self.progress_label.config(text="Finding duplicates...", fg="blue")
        self.progress_bar.start()

        # Run in thread
        thread = threading.Thread(target=self._find_duplicates_thread, daemon=True)
        thread.start()

    def _find_duplicates_thread(self):
        """Thread function to find duplicates"""
        hash_dict = defaultdict(list)

        # Calculate hashes
        for i, file_info in enumerate(self.files_data):
            if i % 100 == 0:
                self.root.after(0, self.update_progress,
                               f"Hashing files... {i}/{len(self.files_data)}")

            try:
                file_hash = self.hash_file(file_info['path'])
                hash_dict[file_hash].append(file_info)
            except Exception:
                continue

        # Find duplicates
        self.duplicates_data = {h: files for h, files in hash_dict.items() if len(files) > 1}

        # Update UI
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
        """Display duplicate files"""
        # Clear tree
        for item in self.dup_tree.get_children():
            self.dup_tree.delete(item)

        total_duplicates = 0
        waste_size = 0

        # Display duplicates
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

        # Update label
        self.dup_label.config(
            text=f"Found {total_duplicates:,} duplicate files | "
                 f"Wasted space: {self.format_size(waste_size)}"
        )

        self.progress_label.config(text="Ready", fg="gray")
        self.progress_bar.stop()

        messagebox.showinfo("Duplicates Found",
                           f"Found {len(self.duplicates_data):,} sets of duplicates\n"
                           f"Total duplicate files: {total_duplicates:,}\n"
                           f"Wasted space: {self.format_size(waste_size)}")

    def open_duplicate_location(self):
        """Open duplicate file location"""
        selection = self.dup_tree.selection()

        if not selection:
            messagebox.showwarning("No Selection", "Please select a file!")
            return

        item = selection[0]
        file_path = self.dup_tree.item(item)['values'][3]

        try:
            if sys.platform == "win32":
                subprocess.run(['explorer', '/select,', file_path])
            elif sys.platform == "darwin":
                subprocess.run(['open', '-R', file_path])
            else:
                subprocess.run(['xdg-open', os.path.dirname(file_path)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open location: {str(e)}")

    def delete_duplicates(self):
        """Delete selected duplicate files"""
        if not HAS_SEND2TRASH:
            messagebox.showerror("Error", "send2trash library not installed!")
            return

        selection = self.dup_tree.selection()

        if not selection:
            messagebox.showwarning("No Selection", "Please select files to delete!")
            return

        count = len(selection)
        result = messagebox.askyesno("Confirm Deletion",
                                     f"Move {count} duplicate file(s) to Recycle Bin?")

        if not result:
            return

        deleted = 0
        for item in selection:
            file_path = self.dup_tree.item(item)['values'][3]
            try:
                send2trash(file_path)
                self.dup_tree.delete(item)
                deleted += 1
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete {file_path}: {str(e)}")

        messagebox.showinfo("Success", f"Moved {deleted} file(s) to Recycle Bin")

    def generate_charts(self):
        """Generate visualization charts"""
        if not HAS_MATPLOTLIB or not self.files_data:
            messagebox.showwarning("No Data", "Please scan a drive first!")
            return

        # Clear previous charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        # Create figure with subplots
        fig = Figure(figsize=(12, 8))

        # Chart 1: Top 10 largest files
        ax1 = fig.add_subplot(2, 2, 1)
        top_files = self.files_data[:10]
        names = [os.path.basename(f['path'])[:20] for f in top_files]
        sizes = [f['size'] / (1024*1024*1024) for f in top_files]
        ax1.barh(names, sizes, color='#4CAF50')
        ax1.set_xlabel('Size (GB)')
        ax1.set_title('Top 10 Largest Files')
        ax1.invert_yaxis()

        # Chart 2: File types distribution
        ax2 = fig.add_subplot(2, 2, 2)
        type_sizes = defaultdict(int)
        for f in self.files_data:
            type_sizes[f['type']] += f['size']

        labels = list(type_sizes.keys())
        sizes = [s / (1024*1024*1024) for s in type_sizes.values()]
        ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax2.set_title('Storage by File Type')

        # Chart 3: File size distribution
        ax3 = fig.add_subplot(2, 2, 3)
        sizes_mb = [f['size'] / (1024*1024) for f in self.files_data if f['size'] < 1024*1024*1024]
        ax3.hist(sizes_mb, bins=50, color='#2196F3', edgecolor='black')
        ax3.set_xlabel('File Size (MB)')
        ax3.set_ylabel('Number of Files')
        ax3.set_title('File Size Distribution (< 1GB)')
        ax3.set_xlim(left=0)

        # Chart 4: File type count
        ax4 = fig.add_subplot(2, 2, 4)
        type_counts = defaultdict(int)
        for f in self.files_data:
            type_counts[f['type']] += 1

        types = list(type_counts.keys())
        counts = list(type_counts.values())
        ax4.bar(types, counts, color='#FF9800')
        ax4.set_ylabel('Number of Files')
        ax4.set_title('File Count by Type')
        ax4.tick_params(axis='x', rotation=45)

        fig.tight_layout()

        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def refresh_trends(self):
        """Refresh trends visualization (NEW)"""
        if not HAS_MATPLOTLIB:
            messagebox.showwarning("No Matplotlib", "Matplotlib not installed!")
            return

        if len(self.scan_history) < 2:
            messagebox.showinfo("Insufficient Data",
                               "Need at least 2 scans for trend analysis.\n"
                               f"Current scans: {len(self.scan_history)}")
            return

        # Clear previous charts
        for widget in self.trends_chart_frame.winfo_children():
            widget.destroy()

        # Create figure
        fig = Figure(figsize=(14, 10))

        # Chart 1: Total size over time
        ax1 = fig.add_subplot(2, 2, 1)
        dates = [h['timestamp'] for h in self.scan_history]
        sizes_gb = [h['total_size'] / (1024*1024*1024) for h in self.scan_history]
        ax1.plot(dates, sizes_gb, marker='o', linewidth=2, markersize=8, color='#2196F3')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Total Size (GB)')
        ax1.set_title('Storage Usage Over Time')
        ax1.grid(True, alpha=0.3)
        fig.autofmt_xdate()

        # Chart 2: File count over time
        ax2 = fig.add_subplot(2, 2, 2)
        file_counts = [h['total_files'] for h in self.scan_history]
        ax2.plot(dates, file_counts, marker='s', linewidth=2, markersize=8, color='#4CAF50')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('File Count')
        ax2.set_title('File Count Over Time')
        ax2.grid(True, alpha=0.3)
        fig.autofmt_xdate()

        # Chart 3: Growth rate
        ax3 = fig.add_subplot(2, 2, 3)
        if len(sizes_gb) > 1:
            growth = [sizes_gb[i] - sizes_gb[i-1] for i in range(1, len(sizes_gb))]
            growth_dates = dates[1:]
            colors = ['#4CAF50' if g < 0 else '#F44336' for g in growth]
            ax3.bar(growth_dates, growth, color=colors)
            ax3.set_xlabel('Date')
            ax3.set_ylabel('Size Change (GB)')
            ax3.set_title('Storage Growth Rate')
            ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax3.grid(True, alpha=0.3)
            fig.autofmt_xdate()

        # Chart 4: File type trends (stacked area)
        ax4 = fig.add_subplot(2, 2, 4)
        if self.scan_history[-1].get('file_types'):
            type_names = list(self.scan_history[-1]['file_types'].keys())
            type_data = {t: [] for t in type_names}

            for scan in self.scan_history:
                if scan.get('file_types'):
                    for t in type_names:
                        size_gb = scan['file_types'].get(t, {}).get('size', 0) / (1024*1024*1024)
                        type_data[t].append(size_gb)

            bottom = [0] * len(dates)
            for t in type_names:
                if len(type_data[t]) == len(dates):
                    ax4.fill_between(dates, bottom, [bottom[i] + type_data[t][i] for i in range(len(dates))],
                                    label=t, alpha=0.7)
                    bottom = [bottom[i] + type_data[t][i] for i in range(len(dates))]

            ax4.set_xlabel('Date')
            ax4.set_ylabel('Size (GB)')
            ax4.set_title('File Type Distribution Over Time')
            ax4.legend(loc='upper left', fontsize=8)
            ax4.grid(True, alpha=0.3)
            fig.autofmt_xdate()

        fig.tight_layout()

        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.trends_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Update info label
        latest = self.scan_history[-1]
        oldest = self.scan_history[0]
        size_change = (latest['total_size'] - oldest['total_size']) / (1024*1024*1024)
        files_change = latest['total_files'] - oldest['total_files']

        self.trends_info_label.config(
            text=f"Scans: {len(self.scan_history)} | "
                 f"Size change: {size_change:+.2f} GB | "
                 f"Files change: {files_change:+,}"
        )

    def generate_drive_comparison(self):
        """Generate multi-drive comparison (NEW)"""
        if not self.all_drives_data:
            messagebox.showinfo("No Data", "Please scan all drives first!")
            return

        # Clear previous widgets
        for widget in self.comparison_frame.winfo_children():
            widget.destroy()

        # Create comparison table
        tree_frame = tk.Frame(self.comparison_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        comp_tree = ttk.Treeview(tree_frame,
                                 columns=("Drive", "Total Size", "Used", "Files", "Avg File Size"),
                                 show="headings",
                                 yscrollcommand=vsb.set,
                                 xscrollcommand=hsb.set)

        vsb.config(command=comp_tree.yview)
        hsb.config(command=comp_tree.xview)

        comp_tree.heading("Drive", text="Drive")
        comp_tree.heading("Total Size", text="Total Size")
        comp_tree.heading("Used", text="Used Space")
        comp_tree.heading("Files", text="File Count")
        comp_tree.heading("Avg File Size", text="Avg File Size")

        comp_tree.column("Drive", width=100, anchor="w")
        comp_tree.column("Total Size", width=150, anchor="e")
        comp_tree.column("Used", width=150, anchor="e")
        comp_tree.column("Files", width=120, anchor="e")
        comp_tree.column("Avg File Size", width=150, anchor="e")

        comp_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Populate comparison data
        for drive, data in sorted(self.all_drives_data.items()):
            total_size = data['total_size']
            file_count = data['total_files']
            avg_size = total_size / file_count if file_count > 0 else 0

            comp_tree.insert("", tk.END, values=(
                drive,
                self.format_size(total_size),
                self.format_size(total_size),
                f"{file_count:,}",
                self.format_size(avg_size)
            ))

        # Generate comparison chart if matplotlib available
        if HAS_MATPLOTLIB:
            chart_frame = tk.Frame(self.comparison_frame)
            chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            fig = Figure(figsize=(12, 5))

            # Chart 1: Size comparison
            ax1 = fig.add_subplot(1, 2, 1)
            drives = list(self.all_drives_data.keys())
            sizes = [self.all_drives_data[d]['total_size'] / (1024*1024*1024) for d in drives]
            ax1.bar(drives, sizes, color='#2196F3')
            ax1.set_ylabel('Size (GB)')
            ax1.set_title('Drive Size Comparison')
            ax1.tick_params(axis='x', rotation=45)

            # Chart 2: File count comparison
            ax2 = fig.add_subplot(1, 2, 2)
            file_counts = [self.all_drives_data[d]['total_files'] for d in drives]
            ax2.bar(drives, file_counts, color='#4CAF50')
            ax2.set_ylabel('File Count')
            ax2.set_title('Drive File Count Comparison')
            ax2.tick_params(axis='x', rotation=45)

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def generate_advanced_report(self):
        """Generate advanced analytics report (NEW)"""
        if not self.files_data:
            messagebox.showwarning("No Data", "Please scan a drive first!")
            return

        # Clear report
        self.report_text.delete(1.0, tk.END)

        # Generate report
        report = []
        report.append("=" * 80)
        report.append("ADVANCED DISK SPACE ANALYTICS REPORT")
        report.append("=" * 80)
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Basic statistics
        total_files = len(self.files_data)
        total_size = sum(f['size'] for f in self.files_data)
        avg_size = total_size / total_files if total_files > 0 else 0

        report.append("\n1. BASIC STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Files: {total_files:,}")
        report.append(f"Total Size: {self.format_size(total_size)} ({total_size:,} bytes)")
        report.append(f"Average File Size: {self.format_size(avg_size)}")

        # File type breakdown
        type_dist = self.get_type_distribution()
        report.append("\n2. FILE TYPE BREAKDOWN")
        report.append("-" * 80)
        report.append(f"{'Type':<15} {'Count':>12} {'Size':>15} {'% of Total':>12}")
        report.append("-" * 80)

        for ftype in sorted(type_dist.keys()):
            count = type_dist[ftype]['count']
            size = type_dist[ftype]['size']
            percent = (size / total_size * 100) if total_size > 0 else 0
            report.append(f"{ftype:<15} {count:>12,} {self.format_size(size):>15} {percent:>11.1f}%")

        # Top 20 largest files
        report.append("\n3. TOP 20 LARGEST FILES")
        report.append("-" * 80)
        report.append(f"{'Rank':<6} {'Size':>15} {'Path'}")
        report.append("-" * 80)

        for i, f in enumerate(self.files_data[:20], 1):
            report.append(f"{i:<6} {self.format_size(f['size']):>15} {f['path']}")

        # Storage growth rate (if history available)
        if len(self.scan_history) >= 2:
            report.append("\n4. STORAGE GROWTH ANALYSIS")
            report.append("-" * 80)

            latest = self.scan_history[-1]
            oldest = self.scan_history[0]

            size_diff = latest['total_size'] - oldest['total_size']
            files_diff = latest['total_files'] - oldest['total_files']
            days_diff = (latest['timestamp'] - oldest['timestamp']).days

            if days_diff > 0:
                daily_growth = size_diff / days_diff
                monthly_growth = daily_growth * 30
                yearly_growth = daily_growth * 365

                report.append(f"Time Period: {days_diff} days")
                report.append(f"Size Change: {self.format_size(abs(size_diff))} ({'increase' if size_diff > 0 else 'decrease'})")
                report.append(f"Files Change: {abs(files_diff):,} ({'increase' if files_diff > 0 else 'decrease'})")
                report.append(f"\nEstimated Growth Rates:")
                report.append(f"  Daily: {self.format_size(abs(daily_growth))}/day")
                report.append(f"  Monthly: {self.format_size(abs(monthly_growth))}/month")
                report.append(f"  Yearly: {self.format_size(abs(yearly_growth))}/year")

                # Prediction
                if size_diff > 0:
                    report.append(f"\nProjections (based on current growth rate):")
                    future_30 = latest['total_size'] + (daily_growth * 30)
                    future_90 = latest['total_size'] + (daily_growth * 90)
                    future_365 = latest['total_size'] + (daily_growth * 365)
                    report.append(f"  In 30 days: {self.format_size(future_30)}")
                    report.append(f"  In 90 days: {self.format_size(future_90)}")
                    report.append(f"  In 1 year: {self.format_size(future_365)}")

        # Access time analysis (files not accessed in long time)
        report.append("\n5. FILE ACCESS ANALYSIS")
        report.append("-" * 80)

        now = datetime.now()
        access_bins = {
            'Last 7 days': 0,
            'Last 30 days': 0,
            'Last 90 days': 0,
            'Last 1 year': 0,
            'Over 1 year': 0
        }

        for f in self.files_data:
            days_since = (now - f['accessed']).days
            if days_since <= 7:
                access_bins['Last 7 days'] += 1
            elif days_since <= 30:
                access_bins['Last 30 days'] += 1
            elif days_since <= 90:
                access_bins['Last 90 days'] += 1
            elif days_since <= 365:
                access_bins['Last 1 year'] += 1
            else:
                access_bins['Over 1 year'] += 1

        for period, count in access_bins.items():
            percent = (count / total_files * 100) if total_files > 0 else 0
            report.append(f"{period:<15}: {count:>8,} files ({percent:>5.1f}%)")

        # Old files that could be archived
        old_files = [f for f in self.files_data if (now - f['accessed']).days > 365]
        old_size = sum(f['size'] for f in old_files)
        report.append(f"\nFiles not accessed in over 1 year: {len(old_files):,}")
        report.append(f"Potential space for archival: {self.format_size(old_size)}")

        # Recommendations
        report.append("\n6. RECOMMENDATIONS")
        report.append("-" * 80)

        recommendations = []

        # Large old files
        large_old = [f for f in self.files_data
                    if f['size'] > 100*1024*1024 and (now - f['accessed']).days > 180]
        if large_old:
            large_old_size = sum(f['size'] for f in large_old)
            recommendations.append(
                f"• Found {len(large_old):,} files over 100MB not accessed in 6+ months "
                f"({self.format_size(large_old_size)}). Consider archiving or deleting."
            )

        # Check for duplicates indication
        if hasattr(self, 'duplicates_data') and self.duplicates_data:
            dup_count = sum(len(files)-1 for files in self.duplicates_data.values())
            dup_size = sum(sum(f['size'] for f in files[1:])
                          for files in self.duplicates_data.values())
            recommendations.append(
                f"• Found {dup_count:,} duplicate files wasting {self.format_size(dup_size)}. "
                f"Run duplicate detection to clean up."
            )

        # Large file types
        for ftype, data in type_dist.items():
            if data['size'] > total_size * 0.3:  # Over 30% of space
                recommendations.append(
                    f"• {ftype} files占用 {data['size']/total_size*100:.1f}% of total space. "
                    f"Review if all {data['count']:,} files are necessary."
                )

        if recommendations:
            for rec in recommendations:
                report.append(rec)
        else:
            report.append("• Storage usage looks healthy. No major issues detected.")

        # Display report
        report_text = "\n".join(report)
        self.report_text.insert(1.0, report_text)

        messagebox.showinfo("Report Generated", "Advanced analytics report generated successfully!")

    def generate_treemap(self):
        """Generate treemap visualization (NEW)"""
        if not HAS_MATPLOTLIB or not HAS_SQUARIFY or not self.files_data:
            messagebox.showwarning("Cannot Generate Treemap",
                                  "Need matplotlib, squarify, and scan data!")
            return

        # Clear previous treemap
        for widget in self.heatmap_frame.winfo_children():
            widget.destroy()

        try:
            limit = int(self.treemap_limit_var.get() or 50)
        except ValueError:
            limit = 50

        # Prepare data
        top_items = self.files_data[:limit]
        labels = [os.path.basename(f['path'])[:30] for f in top_items]
        sizes = [f['size'] for f in top_items]
        colors_map = {
            'Videos': '#E91E63',
            'Images': '#9C27B0',
            'Documents': '#2196F3',
            'Audio': '#00BCD4',
            'Archives': '#4CAF50',
            'Executables': '#FF9800',
            'Other': '#9E9E9E'
        }
        colors = [colors_map.get(f['type'], '#9E9E9E') for f in top_items]

        # Create treemap
        fig = Figure(figsize=(14, 10))
        ax = fig.add_subplot(111)

        squarify.plot(sizes=sizes, label=labels, color=colors, alpha=0.7, ax=ax,
                     text_kwargs={'fontsize': 8, 'weight': 'bold'})

        ax.set_title(f'Treemap: Top {limit} Largest Files', fontsize=16, weight='bold')
        ax.axis('off')

        # Add legend
        legend_elements = [mpatches.Patch(facecolor=color, label=ftype, alpha=0.7)
                          for ftype, color in colors_map.items()]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=10)

        fig.tight_layout()

        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.heatmap_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def export_csv(self):
        """Export results to CSV"""
        if not self.files_data:
            messagebox.showwarning("No Data", "No data to export!")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Path', 'Size (Bytes)', 'Size', 'Type', 'Modified', 'Accessed'])

                for file_info in self.files_data:
                    writer.writerow([
                        file_info['path'],
                        file_info['size'],
                        self.format_size(file_info['size']),
                        file_info['type'],
                        file_info['modified'].strftime("%Y-%m-%d %H:%M:%S"),
                        file_info['accessed'].strftime("%Y-%m-%d %H:%M:%S")
                    ])

            messagebox.showinfo("Success", f"Exported {len(self.files_data):,} files to CSV")
        except Exception as e:
            messagebox.showerror("Error", f"Could not export: {str(e)}")

    def export_pdf(self):
        """Export results to PDF"""
        if not HAS_REPORTLAB or not self.files_data:
            messagebox.showwarning("No Data", "No data to export or reportlab not installed!")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            elements = []

            # Title
            styles = getSampleStyleSheet()
            title = Paragraph("Disk Space Scanner Report", styles['Title'])
            elements.append(title)

            # Summary
            total_size = sum(f['size'] for f in self.files_data) / (1024*1024*1024)
            summary = Paragraph(
                f"<br/>Total Files: {len(self.files_data):,}<br/>"
                f"Total Size: {total_size:.2f} GB<br/>"
                f"Scan Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/><br/>",
                styles['Normal']
            )
            elements.append(summary)

            # Table with top 100 files
            data = [['File', 'Size', 'Type', 'Modified']]
            for file_info in self.files_data[:100]:
                data.append([
                    os.path.basename(file_info['path'])[:40],
                    self.format_size(file_info['size']),
                    file_info['type'],
                    file_info['modified'].strftime("%Y-%m-%d")
                ])

            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)

            doc.build(elements)
            messagebox.showinfo("Success", "Exported to PDF")
        except Exception as e:
            messagebox.showerror("Error", f"Could not export: {str(e)}")

    def save_results(self):
        """Save scan results to file"""
        if not self.files_data:
            messagebox.showwarning("No Data", "No data to save!")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            data = {
                'scan_date': datetime.now().isoformat(),
                'files': [{
                    'path': f['path'],
                    'size': f['size'],
                    'type': f['type'],
                    'extension': f['extension'],
                    'modified': f['modified'].isoformat(),
                    'accessed': f['accessed'].isoformat()
                } for f in self.files_data]
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            messagebox.showinfo("Success", "Results saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save: {str(e)}")

    def load_results(self):
        """Load scan results from file"""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.files_data = []
            for f in data['files']:
                self.files_data.append({
                    'path': f['path'],
                    'size': f['size'],
                    'type': f['type'],
                    'extension': f['extension'],
                    'modified': datetime.fromisoformat(f['modified']),
                    'accessed': datetime.fromisoformat(f['accessed'])
                })

            self.filtered_data = self.files_data.copy()
            self.display_results()

            messagebox.showinfo("Success", f"Loaded {len(self.files_data):,} files")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load: {str(e)}")

    def load_scan_history(self):
        """Load scan history from file (NEW)"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'rb') as f:
                    self.scan_history = pickle.load(f)
        except Exception:
            self.scan_history = []

    def save_scan_history(self):
        """Save scan history to file (NEW)"""
        try:
            # Keep only last 30 scans
            if len(self.scan_history) > 30:
                self.scan_history = self.scan_history[-30:]

            with open(self.history_file, 'wb') as f:
                pickle.dump(self.scan_history, f)
        except Exception:
            pass

    def clear_history(self):
        """Clear scan history (NEW)"""
        result = messagebox.askyesno("Clear History",
                                     "Clear all scan history? This cannot be undone.")
        if result:
            self.scan_history = []
            self.save_scan_history()
            messagebox.showinfo("Success", "Scan history cleared")

    def toggle_dark_mode(self):
        """Toggle dark mode"""
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.save_settings()

    def apply_theme(self):
        """Apply color theme"""
        if self.dark_mode:
            bg_color = "#2b2b2b"
            fg_color = "#ffffff"
            self.root.configure(bg=bg_color)
        else:
            bg_color = "#f0f0f0"
            fg_color = "#000000"
            self.root.configure(bg=bg_color)

    def refresh_display(self):
        """Refresh display"""
        self.display_results()

    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    self.dark_mode = settings.get('dark_mode', False)
                    self.last_drive = settings.get('last_drive', '')
        except Exception:
            pass

    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {
                'dark_mode': self.dark_mode,
                'last_drive': getattr(self, 'last_drive', '')
            }
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)
        except Exception:
            pass

    def show_about(self):
        """Show about dialog"""
        about_text = """Ultra Disk Space Scanner
Version 3.0

A comprehensive tool for analyzing and managing disk space.

NEW Features:
- Disk space trends & history tracking
- Smart filters (access time, file age)
- Multi-drive comparison
- Advanced analytics & reporting
- Treemap visualization
- Growth rate analysis
- And much more!

Created with Python and tkinter
"""
        messagebox.showinfo("About", about_text)


def main():
    root = tk.Tk()
    app = SpaceScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
