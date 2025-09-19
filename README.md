# System Monitor Dashboard - FastHTML AppImage

A real-time system monitoring dashboard built with FastHTML and packaged as a portable Linux AppImage. Leverages UI components from daisyUI and real-time updates via Server-Sent Events (SSE).



## Features

### System Monitoring Capabilities

- **Operating System Information**
  - System type, release, and architecture
  - Hostname and Python version
  - Boot time and uptime tracking
  - CPU core counts (physical and logical)
- **CPU Monitoring**
  - Real-time overall CPU usage percentage
  - Per-core usage visualization
  - CPU frequency monitoring (current/min/max)
  - Dynamic color-coded progress bars
- **Memory Monitoring**
  - RAM usage with percentage and bytes
  - Available memory display
  - Swap memory usage tracking
  - Visual progress indicators
- **Disk Usage**
  - Multiple disk/partition support
  - Device, mountpoint, and filesystem information
  - Usage percentages with progress bars
  - Free space indicators
- **Network Monitoring**
  - Real-time bandwidth monitoring (upload/download speeds)
  - Network interface details with IP addresses
  - Packets sent/received statistics
  - Bandwidth calculation with accurate per-second rates
- **Process Monitoring**
  - Total process count with status breakdown
  - Top CPU-consuming processes
  - Top memory-consuming processes
  - Detailed process tables with PID and usage percentages
- **GPU Monitoring**
  - NVIDIA GPU detection and monitoring (via nvitop)
  - GPU utilization percentage
  - GPU memory usage tracking
  - Temperature monitoring
- **Temperature Sensors**
  - CPU temperature monitoring
  - GPU temperature (when available)
  - Disk temperature sensors
  - Color-coded temperature warnings

### UI/UX Features

- **Real-time Updates**: SSE-based streaming for live data
- **Configurable Refresh Rates**: Independent update intervals for each component
- **Theme Support**: Built-in theme switcher
- **Responsive Design**: Adaptive grid layout for different screen sizes
- **Status Indicators**: Color-coded alerts and progress bars
- **Settings Modal**: Easy configuration of refresh intervals

### Technical Features

- **Portable**: Single AppImage file that runs on most Linux distributions
- **Self-contained**: Includes Python runtime and all dependencies via micromamba
- **Modular Architecture**: Clean separation of monitoring logic and UI components
- **Performance Optimized**: Fine-grained updates and efficient DOM manipulation
- **No Installation Required**: Just download and run



## Project Structure

```
fasthtml-appimage-sysmon/
├── build-resources/          # Build resources (used during build)
│   ├── AppRun               # Entry point script
│   └── fasthtml-demo.desktop # Desktop entry file
├── claude-docs/             # Documentation for Claude AI integration
├── src/                     # Application source code
│   ├── app.py              # Main FastHTML application
│   ├── config.py           # Configuration and constants
│   ├── utils.py            # Utility functions
│   ├── routes.py           # Route definitions
│   ├── monitors/           # System monitoring modules
│   │   ├── __init__.py
│   │   ├── cpu.py         # CPU monitoring functions
│   │   ├── disk.py        # Disk usage monitoring
│   │   ├── gpu.py         # GPU detection and monitoring
│   │   ├── memory.py      # Memory monitoring
│   │   ├── network.py     # Network interface monitoring
│   │   ├── process.py     # Process monitoring
│   │   ├── sensors.py     # Temperature sensor monitoring
│   │   └── system.py      # Static system information
│   └── components/         # UI components
│       ├── __init__.py
│       ├── base.py        # Base component utilities
│       ├── cards.py       # Card components for each metric
│       ├── charts.py      # Chart components (future)
│       ├── common.py      # Common UI elements
│       ├── layout.py      # Layout components
│       ├── modals.py      # Modal dialogs (settings)
│       └── tables.py      # Table components for processes
├── build.sh                # Build script for AppImage
├── environment.yml         # Conda environment specification
├── requirements.txt        # Python package requirements
└── README.md              # This file
```



## Prerequisites

To build the AppImage, you need:

- Linux system (x86_64 or aarch64)
- `wget` and `file` commands
- Internet connection (for downloading tools and packages)

Optional:
- `ImageMagick` (for icon generation)



## Building the AppImage

1. Clone the repository:
```bash
git clone https://github.com/cj-mills/fasthtml-appimage-sysmon.git
cd fasthtml-appimage-sysmon
```

2. Run the build script:
```bash
./build.sh
```

The build script will:
- Download micromamba and AppImage tools
- Create a conda environment with FastHTML and dependencies
- Package everything into an AppImage
- Output: `FastHTMLDemo-1.0.0-x86_64.AppImage`



## Running the AppImage

### Basic usage:
```bash
./FastHTMLDemo-1.0.0-x86_64.AppImage
```
This opens your System Monitor Dashboard in the default browser.

### Standalone window mode:
```bash
FASTHTML_BROWSER=app ./FastHTMLDemo-1.0.0-x86_64.AppImage
```
Opens in a chromeless browser window (requires Chrome/Chromium).

### Headless mode:
```bash
FASTHTML_BROWSER=none ./FastHTMLDemo-1.0.0-x86_64.AppImage
```
Runs the server without opening a browser.

### Debug mode:
```bash
DEBUG=1 ./FastHTMLDemo-1.0.0-x86_64.AppImage
```
Shows detailed debug information.

### Other commands:
```bash
# Enter a shell with the FastHTML environment
./FastHTMLDemo-1.0.0-x86_64.AppImage shell

# Run Python directly
./FastHTMLDemo-1.0.0-x86_64.AppImage python -c "import fasthtml; print(fasthtml.__version__)"

# Install additional packages
./FastHTMLDemo-1.0.0-x86_64.AppImage pip install some-package

# Extract the AppImage contents (for inspection)
./FastHTMLDemo-1.0.0-x86_64.AppImage --appimage-extract
```



## Environment Variables

- `FASTHTML_HOST`: Server host (default: 127.0.0.1)
- `FASTHTML_PORT`: Server port (default: auto-assign)
- `FASTHTML_BROWSER`: Browser mode - `default`, `app`, or `none`
- `DEBUG`: Enable debug output



## Dashboard Components

### Main Dashboard Features:

1. **System Overview Card**: Static system information including OS details, hostname, and uptime
2. **CPU Usage Card**: Real-time CPU metrics with per-core visualization
3. **Memory Usage Card**: RAM and swap usage with progress bars
4. **Disk Usage Card**: Storage information for all mounted drives
5. **Network Card**: Interface status and bandwidth monitoring
6. **Process Card**: Top processes by CPU and memory usage
7. **GPU Card**: NVIDIA GPU metrics and utilization
8. **Temperature Card**: Thermal monitoring for CPU, GPU, and disks

### Settings Panel:

- Adjustable refresh intervals for each component
- Immediate application of settings
- Persistent configuration during session



## Customization

### Adding Dependencies

1. Edit `environment.yml` for conda packages:

   ```text
   dependencies:
     - python=3.11
     - numpy  # Add conda packages here
     - pip:
       - -r requirements.txt
   ```
2. Edit `requirements.txt` for pip packages:

   ```text
   python-fasthtml>=0.12.27
   psutil>=5.9.0
   nvitop>=1.3.2  # For NVIDIA GPU monitoring
   cjm-fasthtml-daisyUI
   cjm-fasthtml-sse
   ```
3. Rebuild the AppImage

### Modifying the Dashboard

1. **Add new monitoring features**: Create a new module in `src/monitors/`
2. **Add UI components**: Create components in `src/components/`
3. **Update main app**: Modify `src/app.py` to include new components
4. **Rebuild the AppImage**

### Changing App Metadata

1. Edit `build-resources/fasthtml-demo.desktop` for app name/description
2. Replace the icon by providing a PNG file
3. Update `APP_NAME` and `APP_VERSION` in `build.sh`



## Troubleshooting

### AppImage won't run
- Make it executable: `chmod +x FastHTMLDemo-*.AppImage`
- Check architecture: `file FastHTMLDemo-*.AppImage`
- Try extracting: `./FastHTMLDemo-*.AppImage --appimage-extract`

### Module import errors
- Ensure all dependencies are in `environment.yml` or `requirements.txt`
- Check debug output: `DEBUG=1 ./FastHTMLDemo-*.AppImage`
- Try rebuilding the AppImage

### GPU monitoring not working
- Ensure NVIDIA drivers are installed
- Check if `nvidia-smi` is accessible
- Verify nvitop installation in requirements



## Resources

- [FastHTML Documentation](https://docs.fastht.ml/)
- [daisyUI Components](https://daisyUI.com/)
- [AppImage Documentation](https://appimage.org/)
- [Micromamba Documentation](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html)
- [psutil Documentation](https://psutil.readthedocs.io/)
- [nvitop Documentation](https://github.com/XuehaiPan/nvitop)
