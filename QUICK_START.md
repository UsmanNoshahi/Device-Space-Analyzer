# Quick Start Guide

## Installation (Windows)

### Option 1: Automatic Installation
1. Double-click `INSTALL.bat`
2. Wait for installation to complete
3. Double-click `RUN_ENHANCED.bat` to start

### Option 2: Manual Installation
```cmd
pip install send2trash matplotlib reportlab
python space_scanner_enhanced.py
```

## First Use

### Step 1: Scan Your Drive
1. Select a drive from the dropdown (e.g., C:\)
2. Click "Scan Drive" button
3. Wait for scanning to complete
4. Files are automatically sorted by size (largest first)

### Step 2: Filter and Search
- **Search Box**: Type filename or extension (e.g., ".mp4")
- **File Type**: Select category (Videos, Images, etc.)
- **Min Size**: Enter minimum MB (e.g., 100 for files > 100MB)

### Step 3: Free Up Space

#### Method 1: Delete Large Files
1. Select files you want to delete (Ctrl+Click for multiple)
2. Click "Delete Selected (to Recycle Bin)"
3. Confirm deletion
4. Files moved to Recycle Bin (can be recovered)

#### Method 2: Find Duplicates
1. Switch to "Duplicate Files" tab
2. Click "Find Duplicates"
3. Wait for analysis
4. Review duplicate groups
5. Select duplicates to delete
6. Click "Delete Selected Duplicates"

#### Method 3: Analyze Folders
1. Switch to "Folder Analysis" tab
2. Click "Analyze Folders"
3. See which folders use most space
4. Open large folders to investigate

## Common Tasks

### Find Large Video Files
1. Set "File Type" to "Videos"
2. Set "Min Size" to "500" (500MB+)
3. Sort by clicking "Size" header
4. Review and delete unwanted videos

### Find Old Downloads
1. Type "download" in search box
2. Review files in Downloads folder
3. Delete outdated files

### Clean Temporary Files
1. Type "temp" in search box
2. Check file dates in "Modified" column
3. Delete old temporary files

### Find Space Wasters
1. Switch to "Visualizations" tab
2. Click "Generate Charts"
3. Review "Top 10 Largest Files" chart
4. Review "Storage by File Type" pie chart

## Keyboard Shortcuts

- **Double-click file**: Open file location
- **Ctrl+Click**: Select multiple files
- **Shift+Click**: Select range of files
- **Right-click**: Show context menu

## Safety Tips

1. **Always use Recycle Bin**: Files can be recovered
2. **Review before deleting**: Check file paths carefully
3. **Start with duplicates**: Safest way to free space
4. **Export results first**: Save scan before making changes
5. **Keep backups**: Have backups of important data

## Troubleshooting

### Application won't start
- Run `INSTALL.bat` first
- Check Python is installed: `python --version`
- Try: `pip install -r requirements.txt`

### "send2trash not installed" error
- Run: `pip install send2trash`
- Or use INSTALL.bat

### Scan is very slow
- Click "Pause" button
- Use "Scan Specific Folder" instead of full drive
- Use "Min Size" filter to reduce results

### No visualizations tab
- Install matplotlib: `pip install matplotlib`

## Tips for Best Results

1. **Start with largest files**: Sort by size, review top files
2. **Use filters**: Focus on specific file types
3. **Check duplicates**: Often the easiest space to free
4. **Analyze folders**: Find unexpected space users
5. **Export before cleanup**: Save results for reference
6. **Regular scans**: Monthly scans prevent buildup

## Getting Help

Check these resources:
1. README_ENHANCED.md - Full documentation
2. Error messages in the application
3. Status bar for current state
4. Progress indicators during operations

## Next Steps

Once comfortable with basics:
- Export results to CSV for analysis
- Save scan results for comparison
- Use dark mode (View → Toggle Dark Mode)
- Generate PDF reports
- Set up regular scanning routine

---

**Ready to start? Double-click `RUN_ENHANCED.bat` now!**
