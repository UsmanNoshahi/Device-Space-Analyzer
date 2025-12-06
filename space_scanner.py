import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import subprocess
import threading
from pathlib import Path


class SpaceScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Disk Space Scanner")
        self.root.geometry("1000x600")

        self.files_data = []
        self.scanning = False

        self.setup_ui()
        self.load_drives()

    def setup_ui(self):
        """Setup the user interface"""
        # Top frame for controls
        control_frame = tk.Frame(self.root, padx=10, pady=10)
        control_frame.pack(fill=tk.X)

        # Drive selection
        tk.Label(control_frame, text="Select Drive:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        self.drive_var = tk.StringVar()
        self.drive_combo = ttk.Combobox(control_frame, textvariable=self.drive_var,
                                        width=15, state="readonly")
        self.drive_combo.pack(side=tk.LEFT, padx=5)

        # Scan button
        self.scan_btn = tk.Button(control_frame, text="Scan Drive",
                                  command=self.start_scan, bg="#4CAF50",
                                  fg="white", font=("Arial", 10, "bold"),
                                  padx=20, pady=5)
        self.scan_btn.pack(side=tk.LEFT, padx=10)

        # Progress label
        self.progress_label = tk.Label(control_frame, text="Ready",
                                       font=("Arial", 9), fg="gray")
        self.progress_label.pack(side=tk.LEFT, padx=10)

        # Frame for treeview and scrollbar
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")

        # Treeview for displaying files
        self.tree = ttk.Treeview(tree_frame,
                                 columns=("Size", "Readable Size", "Path"),
                                 show="headings",
                                 yscrollcommand=vsb.set,
                                 xscrollcommand=hsb.set)

        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Column headings
        self.tree.heading("Size", text="Size (Bytes)")
        self.tree.heading("Readable Size", text="Size")
        self.tree.heading("Path", text="File Path")

        # Column widths
        self.tree.column("Size", width=120, anchor="e")
        self.tree.column("Readable Size", width=120, anchor="e")
        self.tree.column("Path", width=700, anchor="w")

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Bottom frame for buttons
        button_frame = tk.Frame(self.root, padx=10, pady=10)
        button_frame.pack(fill=tk.X)

        self.open_location_btn = tk.Button(button_frame,
                                           text="Open File Location",
                                           command=self.open_file_location,
                                           bg="#2196F3", fg="white",
                                           font=("Arial", 10, "bold"),
                                           padx=20, pady=5)
        self.open_location_btn.pack(side=tk.LEFT, padx=5)

        # Status bar
        self.status_label = tk.Label(self.root, text="No files scanned",
                                     relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)

    def load_drives(self):
        """Load available drives on Windows"""
        drives = []

        if sys.platform == "win32":
            # Get all available drives on Windows
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
        else:
            # For Unix-like systems, use root
            drives = ["/"]

        self.drive_combo['values'] = drives
        if drives:
            self.drive_combo.current(0)

    def start_scan(self):
        """Start scanning the selected drive"""
        if self.scanning:
            messagebox.showwarning("Scanning", "A scan is already in progress!")
            return

        drive = self.drive_var.get()
        if not drive:
            messagebox.showerror("Error", "Please select a drive!")
            return

        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.files_data = []
        self.scanning = True
        self.scan_btn.config(state=tk.DISABLED)
        self.progress_label.config(text="Scanning...", fg="blue")

        # Start scanning in a separate thread
        thread = threading.Thread(target=self.scan_drive, args=(drive,), daemon=True)
        thread.start()

    def scan_drive(self, drive):
        """Scan the drive and collect file information"""
        file_count = 0

        try:
            for root, dirs, files in os.walk(drive):
                # Update progress periodically
                if file_count % 100 == 0:
                    self.root.after(0, self.update_progress,
                                   f"Scanning... Found {file_count} files")

                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)

                        self.files_data.append({
                            'path': file_path,
                            'size': file_size
                        })

                        file_count += 1
                    except (PermissionError, FileNotFoundError, OSError):
                        # Skip files we can't access
                        continue

        except Exception as e:
            self.root.after(0, messagebox.showerror, "Error",
                           f"Error scanning drive: {str(e)}")

        # Sort files by size (descending)
        self.files_data.sort(key=lambda x: x['size'], reverse=True)

        # Update UI with results
        self.root.after(0, self.display_results)

    def update_progress(self, message):
        """Update progress label"""
        self.progress_label.config(text=message)

    def format_size(self, size_bytes):
        """Format size to human-readable format (GB or MB)"""
        size_mb = size_bytes / (1024 * 1024)

        # If size is 1020 MB or more, convert to GB
        if size_mb >= 1020:
            size_gb = size_bytes / (1024 * 1024 * 1024)
            return f"{size_gb:.2f} GB"
        else:
            return f"{size_mb:.2f} MB"

    def display_results(self):
        """Display the scanned results in the treeview"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add files to treeview
        for file_info in self.files_data:
            size_bytes = file_info['size']
            readable_size = self.format_size(size_bytes)

            self.tree.insert("", tk.END, values=(
                f"{size_bytes:,}",
                readable_size,
                file_info['path']
            ))

        # Update status
        total_files = len(self.files_data)
        total_size_gb = sum(f['size'] for f in self.files_data) / (1024 * 1024 * 1024)

        self.status_label.config(
            text=f"Total files: {total_files:,} | Total size: {total_size_gb:.2f} GB"
        )
        self.progress_label.config(text="Scan complete!", fg="green")

        self.scanning = False
        self.scan_btn.config(state=tk.NORMAL)

    def open_file_location(self):
        """Open the folder containing the selected file"""
        selection = self.tree.selection()

        if not selection:
            messagebox.showwarning("No Selection", "Please select a file from the list!")
            return

        # Get the selected item
        item = selection[0]
        file_path = self.tree.item(item)['values'][2]

        # Get the directory containing the file
        directory = os.path.dirname(file_path)

        try:
            if sys.platform == "win32":
                # Open folder and select the file on Windows
                subprocess.run(['explorer', '/select,', file_path])
            elif sys.platform == "darwin":
                # macOS
                subprocess.run(['open', '-R', file_path])
            else:
                # Linux
                subprocess.run(['xdg-open', directory])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open location: {str(e)}")


def main():
    root = tk.Tk()
    app = SpaceScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
