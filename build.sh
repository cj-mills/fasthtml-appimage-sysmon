#!/bin/bash
set -e

# FastHTML AppImage Builder Script
# This script builds a portable AppImage containing a FastHTML application
# with micromamba for Python environment management

echo "======================================"
echo "FastHTML AppImage Builder"
echo "======================================"

# Configuration
APP_NAME="FastHTMLDemo"
APP_VERSION="1.0.0"
ARCH=$(uname -m)
PYTHON_VERSION="3.11"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
APPDIR="$SCRIPT_DIR/AppDir"
SRC_DIR="$SCRIPT_DIR/src"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check dependencies
check_dependencies() {
    info "Checking dependencies..."

    # Check for required tools
    local missing_deps=()

    if ! command -v wget &> /dev/null; then
        missing_deps+=("wget")
    fi

    if ! command -v file &> /dev/null; then
        missing_deps+=("file")
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        error "Missing dependencies: ${missing_deps[*]}. Please install them first."
    fi

    info "All dependencies found!"
}

# Download micromamba
download_micromamba() {
    info "Downloading micromamba..."

    local MICROMAMBA_VERSION="latest"
    local MICROMAMBA_URL="https://micro.mamba.pm/api/micromamba/linux-64/latest"
    local MICROMAMBA_BIN="$BUILD_DIR/micromamba"

    mkdir -p "$BUILD_DIR"

    if [ -f "$MICROMAMBA_BIN" ] && [ -x "$MICROMAMBA_BIN" ] && file "$MICROMAMBA_BIN" | grep -q "ELF"; then
        warn "Micromamba already exists, skipping download"
    else
        # Download as tar.bz2 and extract
        wget -q --show-progress -O "$BUILD_DIR/micromamba.tar.bz2" "$MICROMAMBA_URL"
        cd "$BUILD_DIR"
        tar -xjf micromamba.tar.bz2 bin/micromamba
        mv bin/micromamba micromamba
        rmdir bin
        rm micromamba.tar.bz2
        cd "$SCRIPT_DIR"
        chmod +x "$MICROMAMBA_BIN"
        info "Micromamba downloaded and extracted successfully"
    fi
}

# Download AppImage tools
download_appimage_tools() {
    info "Downloading AppImage tools..."

    local APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    local APPIMAGETOOL="$BUILD_DIR/appimagetool"

    if [ -f "$APPIMAGETOOL" ]; then
        warn "appimagetool already exists, skipping download"
    else
        wget -q --show-progress -O "$APPIMAGETOOL" "$APPIMAGETOOL_URL"
        chmod +x "$APPIMAGETOOL"
        info "AppImage tools downloaded successfully"
    fi
}

# Prepare AppDir structure
prepare_appdir() {
    info "Preparing AppDir structure..."

    # Clean and create AppDir
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR"
    mkdir -p "$APPDIR/usr/share/applications"
    mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

    # Copy application source
    cp -r "$SRC_DIR" "$APPDIR/src"

    # Copy AppRun from build-resources
    if [ -f "$SCRIPT_DIR/build-resources/AppRun" ]; then
        cp "$SCRIPT_DIR/build-resources/AppRun" "$APPDIR/AppRun"
        chmod +x "$APPDIR/AppRun"
        info "AppRun copied successfully"
    else
        error "AppRun not found at $SCRIPT_DIR/build-resources/AppRun"
    fi

    info "AppDir structure prepared"
}

# Setup micromamba environment in AppDir
setup_micromamba_env() {
    info "Setting up micromamba environment in AppDir..."

    local MAMBA_ROOT="$APPDIR/micromamba"
    local ENV_NAME="fasthtml-app"

    # Copy micromamba binary
    mkdir -p "$MAMBA_ROOT/bin"
    cp "$BUILD_DIR/micromamba" "$MAMBA_ROOT/bin/"

    # Initialize micromamba
    export MAMBA_ROOT_PREFIX="$MAMBA_ROOT"

    # Create environment from YAML file
    info "Creating conda environment..."
    "$MAMBA_ROOT/bin/micromamba" create -y \
        -n "$ENV_NAME" \
        -f "$SCRIPT_DIR/environment.yml" \
        --root-prefix "$MAMBA_ROOT" \
        -c conda-forge

    # Verify installation
    local PYTHON_BIN="$MAMBA_ROOT/envs/$ENV_NAME/bin/python"
    if [ ! -f "$PYTHON_BIN" ]; then
        error "Python not found in micromamba environment!"
    fi

    info "Python version: $($PYTHON_BIN --version)"

    # Clean up unnecessary files to reduce size
    info "Cleaning up environment to reduce size..."
    find "$MAMBA_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$MAMBA_ROOT" -name "*.pyc" -delete 2>/dev/null || true
    find "$MAMBA_ROOT" -name "*.pyo" -delete 2>/dev/null || true
    rm -rf "$MAMBA_ROOT/pkgs"
    rm -rf "$MAMBA_ROOT/envs/$ENV_NAME/lib/python*/test"
    rm -rf "$MAMBA_ROOT/envs/$ENV_NAME/lib/python*/tests"

    info "Micromamba environment setup complete"
}

# Create desktop entry
create_desktop_entry() {
    info "Creating desktop entry..."

    # Copy desktop file from build-resources
    if [ -f "$SCRIPT_DIR/build-resources/fasthtml-demo.desktop" ]; then
        cp "$SCRIPT_DIR/build-resources/fasthtml-demo.desktop" "$APPDIR/fasthtml-demo.desktop"
    else
        # Create it if it doesn't exist
        cat > "$APPDIR/fasthtml-demo.desktop" << EOF
[Desktop Entry]
Type=Application
Name=FastHTML Demo
Comment=FastHTML AppImage Demo Application
Exec=AppRun
Icon=fasthtml-icon
Categories=Development;WebDevelopment;
Terminal=false
StartupNotify=true
EOF
    fi

    # Link desktop file
    ln -sf ../../../fasthtml-demo.desktop "$APPDIR/usr/share/applications/fasthtml-demo.desktop"

    # Create a simple icon (you can replace this with a proper icon)
    create_icon "$APPDIR/usr/share/icons/hicolor/256x256/apps/fasthtml-icon.png"
    cp "$APPDIR/usr/share/icons/hicolor/256x256/apps/fasthtml-icon.png" "$APPDIR/fasthtml-icon.png"
    ln -sf fasthtml-icon.png "$APPDIR/.DirIcon"

    info "Desktop entry created"
}

# Create a simple icon (SVG converted to PNG using ImageMagick if available, otherwise a placeholder)
create_icon() {
    local ICON_PATH="$1"

    if command -v convert &> /dev/null; then
        # Create SVG and convert to PNG
        cat > /tmp/fasthtml-icon.svg << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256">
  <rect width="256" height="256" fill="#1e40af"/>
  <text x="128" y="140" font-family="Arial, sans-serif" font-size="72" font-weight="bold" text-anchor="middle" fill="white">FH</text>
  <text x="128" y="180" font-family="Arial, sans-serif" font-size="24" text-anchor="middle" fill="white">FastHTML</text>
</svg>
EOF
        convert -background none /tmp/fasthtml-icon.svg "$ICON_PATH" 2>/dev/null || \
            warn "Could not convert SVG to PNG, using placeholder"
    fi

    # If conversion failed or ImageMagick not available, create a placeholder
    if [ ! -f "$ICON_PATH" ]; then
        # Create a minimal PNG placeholder (1x1 blue pixel)
        echo -n -e '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x00\x00\x00\x00IEND\xaeB`\x82' > "$ICON_PATH"
    fi
}

# Build the AppImage
build_appimage() {
    info "Building AppImage..."

    local OUTPUT_NAME="${APP_NAME}-${APP_VERSION}-${ARCH}.AppImage"

    # Set environment variables for appimagetool
    export ARCH="$ARCH"
    export VERSION="$APP_VERSION"

    # Run appimagetool
    "$BUILD_DIR/appimagetool" "$APPDIR" "$SCRIPT_DIR/$OUTPUT_NAME"

    if [ $? -eq 0 ]; then
        info "AppImage created successfully: $OUTPUT_NAME"
        info "File size: $(du -h "$SCRIPT_DIR/$OUTPUT_NAME" | cut -f1)"
    else
        error "Failed to create AppImage"
    fi
}

# Test the AppImage
test_appimage() {
    local OUTPUT_NAME="${APP_NAME}-${APP_VERSION}-${ARCH}.AppImage"

    if [ -f "$SCRIPT_DIR/$OUTPUT_NAME" ]; then
        info "Testing AppImage..."
        info "You can test the AppImage with:"
        echo ""
        echo "  ./$OUTPUT_NAME"
        echo ""
        echo "Or extract and inspect it with:"
        echo "  ./$OUTPUT_NAME --appimage-extract"
        echo ""
        echo "Environment variables you can set:"
        echo "  FASTHTML_BROWSER=app ./$OUTPUT_NAME  # Open in standalone window"
        echo "  FASTHTML_BROWSER=none ./$OUTPUT_NAME # Don't open browser"
        echo "  DEBUG=1 ./$OUTPUT_NAME                # Enable debug output"
    fi
}

# Main build process
main() {
    echo ""
    info "Starting build process..."
    echo ""

    check_dependencies
    download_micromamba
    download_appimage_tools
    prepare_appdir
    setup_micromamba_env
    create_desktop_entry
    build_appimage
    test_appimage

    echo ""
    info "Build complete!"
    echo ""
}

# Run main function
main "$@"