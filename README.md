# Disk Space Scanner

A Python desktop application to scan drives and identify large files to help free up disk space.

## Features

- Select any available drive on your PC
- Scan and list all files sorted by size (largest first)
- Display file sizes in both bytes and MB
- Open file location directly from the application
- Progress indicator during scanning
- Total files count and total size statistics

## Requirements

- Python 3.6 or higher
- tkinter (usually comes pre-installed with Python)

## Installation

1. Ensure Python is installed on your system
2. Clone or download this repository
3. No additional packages required - uses only Python standard library

## Usage

1. Run the application:
   ```
   python space_scanner.py
   ```

2. Select a drive from the dropdown menu

3. Click "Scan Drive" to start scanning

4. Wait for the scan to complete (progress is shown)

5. Browse the list of files sorted by size (heaviest files at top)

6. Select any file and click "Open File Location" to open the folder containing that file

## How to Run

### On Windows:
```cmd
python space_scanner.py
```

### Double-click option:
You can also double-click `space_scanner.py` if Python is properly associated with `.py` files.

## Features Explained

### Drive Selection
- Automatically detects all available drives on your PC
- Supports C:\, D:\, E:\ etc. on Windows
- Supports root (/) on Linux/Mac

### File Scanning
- Recursively scans all folders and subfolders
- Safely handles permission errors
- Shows real-time progress during scanning

### File Display
- Files sorted in descending order by size
- Shows size in bytes and MB for easy understanding
- Displays full file path

### Open File Location
- Select any file from the list
- Click "Open File Location" button
- Windows Explorer opens with the file selected

## Tips for Freeing Up Space

1. Look at the largest files first
2. Check if large files are duplicates or outdated
3. Move large media files to external storage
4. Delete temporary or cache files you no longer need

## Notes

- Scanning large drives may take time
- Some system files may not be accessible (permission errors are handled gracefully)
- Always verify files before deleting them

## Platform Support

- Windows (fully supported)
- Linux (supported)
- macOS (supported)
