# FastHTML AppImage with daisyUI

This example demonstrates how to package a FastHTML application as a portable Linux AppImage using micromamba for Python environment management. Uses daisyUI for styling.

## Features

- **Portable**: Single executable file that runs on most Linux distributions
- **Self-contained**: Includes Python runtime and all dependencies via micromamba
- **Browser modes**: Can open in default browser, standalone window, or headless
- **Environment management**: Uses micromamba for reproducible Python environments
- **No installation required**: Just download and run

## Project Structure

```
fasthtml-appimage-daisyui/
├── build-resources/          # Build resource (used during build)
│   ├── AppRun                # Entry point script
│   └── fasthtml-demo.desktop # Desktop entry file
├── build.sh                  # Build script
├── environment.yml           # Conda environment specification
├── README.md                 # This file
├── requirements.txt          # Python package requirements
└── src/                      # FastHTML application source
    └── app.py                # Main FastHTML application
```

## Prerequisites

To build the AppImage, you need:

- Linux system (x86_64 or aarch64)
- `wget` and `file` commands
- Internet connection (for downloading tools and packages)

Optional:
- `ImageMagick` (for icon generation)

## Building the AppImage

1. Clone or download this example:
```bash
git clone https://github.com/cj-mills/fasthtml-appimage-daisyui.git
cd ./fasthtml-appimage-daisyui
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
This opens your FastHTML app in the default browser.

### Standalone window mode:
```bash
FASTHTML_BROWSER=app ./FastHTMLDemo-1.0.0-x86_64.AppImage
```
Opens in a chromeless browser window (if Chrome/Chromium is installed).

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

## How It Works

1. **AppRun Script**: The entry point that:
   - Sets up the micromamba environment
   - Configures Python paths
   - Launches the FastHTML application

2. **Micromamba**: Provides isolated Python environment:
   - Bundled inside the AppImage
   - Contains Python 3.11 and all dependencies
   - Completely isolated from system Python

3. **FastHTML Application**: Runs as a local web server:
   - Auto-finds available port
   - Opens browser automatically
   - Serves the web application locally

## Customization

### Adding Dependencies

1. Edit `environment.yml` for conda packages:
```yaml
dependencies:
  - python=3.11
  - numpy  # Add conda packages here
  - pip:
    - -r requirements.txt
```

2. Edit `requirements.txt` for pip-only packages:
```
python-fasthtml>=0.12.27
sqlite-minutils>=4.0.3
cjm-fasthtml-daisyui
new-package==1.0.0
```

3. Rebuild the AppImage

### Modifying the Application

1. Edit `src/app.py` with your FastHTML application
2. Add additional Python files to `src/` as needed
3. Rebuild the AppImage

### Changing App Metadata

1. Edit `AppDir/fasthtml-demo.desktop` for app name/description
2. Replace the icon by providing a PNG file
3. Update `APP_NAME` and `APP_VERSION` in `build.sh`

## Size Optimization

The AppImage size can be reduced by:

1. **Using pip-only dependencies** (skip conda packages when possible)
2. **Cleaning build artifacts** (already done in build script)
3. **Using `--no-deps` for packages** with unnecessary dependencies
4. **Excluding test files and documentation** from packages

## Troubleshooting

### AppImage won't run
- Make it executable: `chmod +x FastHTMLDemo-*.AppImage`
- Check architecture: `file FastHTMLDemo-*.AppImage`
- Try extracting: `./FastHTMLDemo-*.AppImage --appimage-extract`

### Module import errors
- Ensure all dependencies are in `environment.yml` or `requirements.txt`
- Check debug output: `DEBUG=1 ./FastHTMLDemo-*.AppImage`
- Try rebuilding the AppImage

## Advanced Usage

### Creating Multi-App Bundles

You can modify this example to bundle multiple FastHTML apps:

1. Add multiple apps to `src/`
2. Modify `AppRun` to accept app selection parameter
3. Create launcher script or menu for app selection

### Integrating with System

Create a `.desktop` file in `~/.local/share/applications/`:
```desktop
[Desktop Entry]
Type=Application
Name=My FastHTML App
Exec=/path/to/FastHTMLDemo-1.0.0-x86_64.AppImage
Icon=/path/to/icon.png
Categories=Development;
```

### CI/CD Integration

The build script can be integrated into CI/CD pipelines:
```yaml
# GitHub Actions example
- name: Build AppImage
  run: |
    cd fasthtml-appimage-daisyui
    ./build.sh

- name: Upload AppImage
  uses: actions/upload-artifact@v2
  with:
    name: appimage
    path: "*.AppImage"
```

## Resources

- [FastHTML Documentation](https://fastht.ml/)
- [AppImage Documentation](https://appimage.org/)
- [Micromamba Documentation](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html)