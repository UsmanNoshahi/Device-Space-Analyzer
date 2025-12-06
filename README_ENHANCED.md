# Advanced Disk Space Scanner

A comprehensive Python desktop application for analyzing disk space usage, finding duplicate files, and managing storage efficiently.

## Features Overview

### 1. File Scanning & Filtering
- **Drive/Folder Selection**: Scan entire drives or specific folders
- **Real-time Search**: Filter files by name or extension
- **File Type Filtering**: Filter by Videos, Images, Documents, Audio, Archives, Executables
- **Size Filtering**: Show only files above a minimum size threshold
- **Smart Sorting**: Click column headers to sort by size, type, or modification date
- **Progress Tracking**: Visual progress bar and real-time file count
- **Pause/Resume/Cancel**: Full control over scanning process

### 2. File Management
- **Delete to Recycle Bin**: Safely delete files with recovery option
- **Bulk Operations**: Select and delete multiple files at once
- **Open File Location**: Jump directly to file location in explorer
- **File Properties**: View detailed file information (size, dates, permissions)
- **Right-click Context Menu**: Quick access to common actions

### 3. Folder Analysis
- **Folder Size Calculation**: See which folders consume the most space
- **File Count Statistics**: Know how many files are in each folder
- **Sorted View**: Folders sorted by size (largest first)
- **Quick Navigation**: Open any folder directly from the list

### 4. Duplicate Detection
- **Hash-based Detection**: Find exact duplicates using MD5 hashing
- **Space Waste Calculator**: See how much space duplicates are wasting
- **Smart Grouping**: Duplicates grouped together with copy numbers
- **Selective Deletion**: Choose which duplicates to keep/delete

### 5. Data Visualization
- **Top 10 Largest Files Chart**: Bar chart showing biggest space consumers
- **File Type Distribution**: Pie chart of storage by file type
- **Size Distribution Histogram**: See file size patterns
- **File Count by Type**: Bar chart showing file type counts

### 6. Export & Reporting
- **CSV Export**: Export file lists for Excel/Sheets
- **PDF Reports**: Professional reports with tables and statistics
- **Save/Load Results**: Save scan results for later comparison
- **Scan History**: Track changes over time

### 7. User Experience
- **Dark Mode**: Toggle between light and dark themes
- **Settings Persistence**: Remembers last drive and preferences
- **Multi-tab Interface**: Organized tabs for different functions
- **Responsive Design**: Clean, modern interface
- **Keyboard Shortcuts**: Fast navigation and operations

### 8. Performance
- **Multi-threaded Scanning**: Non-blocking UI during scans
- **Efficient Memory Usage**: Handles millions of files
- **Fast Filtering**: Instant search and filter application
- **Optimized Display**: Smooth scrolling even with large datasets

## Installation

### Prerequisites
- Python 3.6 or higher
- tkinter (usually pre-installed)

### Install Dependencies

```bash
pip install -r requirements.txt
```

**Optional Dependencies:**
- `send2trash` - For safe file deletion (highly recommended)
- `matplotlib` - For data visualization charts
- `reportlab` - For PDF export functionality

### Minimal Installation (No Dependencies)
The application works without any external libraries, but with reduced functionality:
- No Recycle Bin support (files deleted permanently)
- No visualization charts
- No PDF export

## Usage

### Basic Usage

```bash
python space_scanner_enhanced.py
```

### Quick Start Guide

1. **Scan a Drive**
   - Select drive from dropdown (C:\, D:\, etc.)
   - Click "Scan Drive"
   - Wait for scan to complete
   - Browse results sorted by size

2. **Find Large Files**
   - Set "Min Size (MB)" filter (e.g., 100 for files > 100MB)
   - Use search box to find specific files
   - Click column headers to sort

3. **Delete Unnecessary Files**
   - Select files (hold Ctrl for multiple)
   - Click "Delete Selected (to Recycle Bin)"
   - Confirm deletion
   - Files safely moved to Recycle Bin

4. **Analyze Folders**
   - Switch to "Folder Analysis" tab
   - Click "Analyze Folders"
   - See which folders use most space
   - Double-click to open folder

5. **Find Duplicates**
   - Switch to "Duplicate Files" tab
   - Click "Find Duplicates"
   - Wait for hash calculation
   - Review duplicate groups
   - Delete unwanted copies

6. **View Charts**
   - Switch to "Visualizations" tab
   - Click "Generate Charts"
   - Analyze storage patterns visually

## Features in Detail

### File Type Categories

The application automatically categorizes files:

- **Videos**: .mp4, .avi, .mkv, .mov, .wmv, etc.
- **Images**: .jpg, .png, .gif, .bmp, .svg, etc.
- **Documents**: .pdf, .doc, .docx, .txt, .xls, etc.
- **Audio**: .mp3, .wav, .flac, .aac, etc.
- **Archives**: .zip, .rar, .7z, .tar, .gz, etc.
- **Executables**: .exe, .msi, .dll, etc.
- **Other**: Everything else

### Sorting Options

Click any column header to sort:
- **Size**: Sort by file size (bytes)
- **Type**: Sort by file type category
- **Modified**: Sort by modification date
- **Path**: Sort alphabetically by path

Click again to reverse sort order.

### Context Menu Actions

Right-click on any file for:
- Open File Location
- Show Properties
- Delete (to Recycle Bin)

### Keyboard Shortcuts

- **Double-click**: Open file location
- **Ctrl+Click**: Select multiple files
- **Shift+Click**: Select range of files

## Export Options

### CSV Export
- Contains: Path, Size, Type, Modified date
- Opens in: Excel, Google Sheets, LibreOffice

### PDF Export
- Includes: Summary statistics, Top 100 files
- Professional table format
- Timestamped report

### JSON Save/Load
- Complete scan results
- Includes all metadata
- Fast reload without rescanning

## Menu Options

### File Menu
- Scan Specific Folder
- Export to CSV
- Export to PDF
- Save Results
- Load Results
- Exit

### View Menu
- Toggle Dark Mode
- Refresh Display

### Tools Menu
- Find Duplicates
- Analyze Folders

### Help Menu
- About

## Performance Tips

### For Large Drives
1. Use "Min Size" filter to focus on large files
2. Scan specific folders instead of entire drive
3. Use Pause button if system becomes slow
4. Limit results display with filters

### For Faster Scans
1. Close other applications
2. Scan local drives (not network)
3. Use SSD drives when possible
4. Exclude system folders if not needed

## Troubleshooting

### "send2trash library not installed"
Install it: `pip install send2trash`

### No Visualization Tab
Install matplotlib: `pip install matplotlib`

### PDF Export Not Available
Install reportlab: `pip install reportlab`

### Scan Takes Too Long
- Use Pause/Cancel buttons
- Scan specific folders
- Use size filters to reduce results

### Permission Errors
- Run as Administrator (Windows)
- Some system files may not be accessible
- These are automatically skipped

### Application Freezes
- The UI should never freeze (multi-threaded)
- If it does, use Cancel button
- Report bug with details

## System Requirements

### Windows
- Windows 7 or higher
- Python 3.6+
- 100MB free RAM (minimum)
- 500MB free RAM (recommended for large scans)

### Linux
- Any modern distribution
- Python 3.6+
- python3-tk package
- xdg-open for folder opening

### macOS
- macOS 10.12 or higher
- Python 3.6+
- tkinter (included with Python.org distribution)

## Safety Features

### File Deletion Safety
- Uses Recycle Bin (not permanent deletion)
- Confirmation dialogs
- Detailed error reporting
- Undo capability via Recycle Bin

### Scan Safety
- Read-only operations
- Permission error handling
- No modification to scanned files
- Cancellable at any time

## Comparison: Basic vs Enhanced

| Feature | Basic Version | Enhanced Version |
|---------|--------------|------------------|
| File Scanning | ✓ | ✓ |
| Sort by Size | ✓ | ✓ |
| Open Location | ✓ | ✓ |
| Search/Filter | ✗ | ✓ |
| File Type Filter | ✗ | ✓ |
| Size Filter | ✗ | ✓ |
| Delete Files | ✗ | ✓ |
| Folder Analysis | ✗ | ✓ |
| Duplicate Detection | ✗ | ✓ |
| Visualizations | ✗ | ✓ |
| Export CSV/PDF | ✗ | ✓ |
| Save/Load Results | ✗ | ✓ |
| Pause/Resume | ✗ | ✓ |
| Dark Mode | ✗ | ✓ |
| Context Menu | ✗ | ✓ |
| File Properties | ✗ | ✓ |
| Multi-select | ✗ | ✓ |

## Tips for Freeing Space

### Quick Wins
1. **Find large video files**: Filter by "Videos" and sort by size
2. **Find old downloads**: Search for "download" folder
3. **Find temporary files**: Search for "temp" or "cache"
4. **Find large archives**: Filter by "Archives" type

### Duplicate Files
1. Run duplicate detection
2. Review grouped duplicates
3. Keep one copy, delete others
4. Can save gigabytes instantly

### Folder Analysis
1. Find largest folders
2. Investigate unexpected large folders
3. Clean up old project folders
4. Remove outdated backups

### Regular Maintenance
1. Scan monthly
2. Save results for comparison
3. Track storage trends
4. Clean proactively

## Data Privacy

- All scanning is local (no cloud/internet)
- No data collection or telemetry
- Settings stored locally only
- Complete privacy guaranteed

## File Format Support

The application works with ALL file types:
- Documents, images, videos, audio
- Archives, executables, databases
- Source code, logs, temporary files
- System files, hidden files
- Any file accessible to your user account

## Known Limitations

1. **System Files**: Some protected system files cannot be accessed
2. **Network Drives**: May be slower than local drives
3. **Large Drives**: Scanning 1TB+ may take significant time
4. **Memory**: Very large scans (millions of files) require adequate RAM

## Future Enhancements

Potential future features:
- Cloud storage integration
- Scheduled automatic scans
- File preview panel
- More chart types
- Custom file type definitions
- Advanced filtering rules
- Compression suggestions
- Cleanup automation

## Support

For issues, questions, or suggestions:
1. Check this README
2. Review error messages
3. Try with updated Python/libraries
4. Report bugs with details

## License

Free to use for personal and commercial purposes.

## Credits

Built with:
- Python 3
- tkinter (GUI)
- matplotlib (Charts)
- reportlab (PDF)
- send2trash (Safe deletion)

---

**Happy Space Cleaning!**

Version 2.0 - Advanced Edition
