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
from datetime import datetime
from collections import defaultdict
import time

# Try to import optional libraries
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
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


class SpaceScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Disk Space Scanner")
        self.root.geometry("1400x800")

        # Data storage
        self.files_data = []
        self.filtered_data = []
        self.folders_data = {}
        self.duplicates_data = {}

        # Scanning state
        self.scanning = False
        self.scan_paused = False
        self.scan_cancelled = False
        self.scan_thread = None

        # UI settings
        self.dark_mode = False
        self.sort_column = None
        self.sort_reverse = True

        # Settings file
        self.settings_file = "scanner_settings.json"

        # Load settings
        self.load_settings()

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

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Find Duplicates", command=self.find_duplicates)
        tools_menu.add_command(label="Analyze Folders", command=self.analyze_folders)

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

        # Row 2: Filters
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

        # Treeview frame
        tree_frame = tk.Frame(self.files_tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview with multiple selection
        self.tree = ttk.Treeview(tree_frame,
                                 columns=("Size", "Readable Size", "Type", "Modified", "Path"),
                                 show="headings",
                                 yscrollcommand=vsb.set,
                                 xscrollcommand=hsb.set,
                                 selectmode="extended")

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Column headings with sort capability
        columns = [
            ("Size", "Size (Bytes)", 120),
            ("Readable Size", "Size", 120),
            ("Type", "Type", 100),
            ("Modified", "Modified", 150),
            ("Path", "File Path", 700)
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

                        _, ext = os.path.splitext(file)
                        file_type = self.get_file_type(ext)

                        self.files_data.append({
                            'path': file_path,
                            'size': file_size,
                            'type': file_type,
                            'extension': ext.lower(),
                            'modified': file_mtime
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
                file_info['path']
            ))

    def apply_filters(self, *args):
        """Apply search and filters"""
        if not self.files_data:
            return

        search_text = self.search_var.get().lower()
        file_type = self.file_type_var.get()

        try:
            min_size_mb = float(self.min_size_var.get() or 0)
        except ValueError:
            min_size_mb = 0

        min_size_bytes = min_size_mb * 1024 * 1024

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
        file_path = self.tree.item(item)['values'][4]

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
            file_path = self.tree.item(item)['values'][4]
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
        file_path = values[4]

        try:
            stat_info = os.stat(file_path)

            props = f"""File Properties:

Path: {file_path}
Size: {values[1]} ({values[0]} bytes)
Type: {values[2]}
Modified: {values[3]}
Created: {datetime.fromtimestamp(stat_info.st_ctime).strftime("%Y-%m-%d %H:%M:%S")}
Accessed: {datetime.fromtimestamp(stat_info.st_atime).strftime("%Y-%m-%d %H:%M:%S")}
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
        for folder, info in sorted_folders[:1000]:  # Limit to top 1000
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

        # Find duplicates (files with same hash)
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
            # Sort by path
            files.sort(key=lambda x: x['path'])

            # Add all copies
            for i, file_info in enumerate(files):
                self.dup_tree.insert("", tk.END, values=(
                    f"{file_info['size']:,}",
                    self.format_size(file_info['size']),
                    f"{i+1}/{len(files)}",
                    file_info['path']
                ))

                # Count waste (all copies except one)
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

        # Chart 1: Top 10 largest files (bar chart)
        ax1 = fig.add_subplot(2, 2, 1)
        top_files = self.files_data[:10]
        names = [os.path.basename(f['path'])[:20] for f in top_files]
        sizes = [f['size'] / (1024*1024*1024) for f in top_files]  # GB
        ax1.barh(names, sizes, color='#4CAF50')
        ax1.set_xlabel('Size (GB)')
        ax1.set_title('Top 10 Largest Files')
        ax1.invert_yaxis()

        # Chart 2: File types distribution (pie chart)
        ax2 = fig.add_subplot(2, 2, 2)
        type_sizes = defaultdict(int)
        for f in self.files_data:
            type_sizes[f['type']] += f['size']

        labels = list(type_sizes.keys())
        sizes = [s / (1024*1024*1024) for s in type_sizes.values()]  # GB
        ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax2.set_title('Storage by File Type')

        # Chart 3: File size distribution (histogram)
        ax3 = fig.add_subplot(2, 2, 3)
        sizes_mb = [f['size'] / (1024*1024) for f in self.files_data if f['size'] < 1024*1024*1024]  # MB
        ax3.hist(sizes_mb, bins=50, color='#2196F3', edgecolor='black')
        ax3.set_xlabel('File Size (MB)')
        ax3.set_ylabel('Number of Files')
        ax3.set_title('File Size Distribution (< 1GB)')
        ax3.set_xlim(left=0)

        # Chart 4: File type count (bar chart)
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
                writer.writerow(['Path', 'Size (Bytes)', 'Size', 'Type', 'Modified'])

                for file_info in self.files_data:
                    writer.writerow([
                        file_info['path'],
                        file_info['size'],
                        self.format_size(file_info['size']),
                        file_info['type'],
                        file_info['modified'].strftime("%Y-%m-%d %H:%M:%S")
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
                    'modified': f['modified'].isoformat()
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
                    'modified': datetime.fromisoformat(f['modified'])
                })

            self.filtered_data = self.files_data.copy()
            self.display_results()

            messagebox.showinfo("Success", f"Loaded {len(self.files_data):,} files")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load: {str(e)}")

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
        about_text = """Advanced Disk Space Scanner
Version 2.0

A comprehensive tool for analyzing and managing disk space.

Features:
- File scanning with filters
- Folder analysis
- Duplicate detection
- Data visualization
- Export capabilities
- And more!

Created with Python and tkinter
"""
        messagebox.showinfo("About", about_text)


def main():
    root = tk.Tk()
    app = SpaceScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
