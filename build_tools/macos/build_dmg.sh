#!/usr/bin/env bash
# Build an unsigned macOS DMG for local testing / GitHub release candidates.
#
# This script assumes the PyInstaller GUI app is available at
# dist/GONet Wizard.app. If it is missing, the script builds it using the
# repository PyInstaller spec before creating the DMG.

set -euo pipefail

APP_NAME="GONet Wizard"
VOLUME_NAME="GONet Wizard"
RUN_PYINSTALLER=auto
CLEAN_STAGING=1
APP_PATH_CUSTOM=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
BUILD_DIR="${REPO_ROOT}/build"
APP_PATH="${DIST_DIR}/${APP_NAME}.app"
OUTPUT_DIR="${DIST_DIR}"
ARCH_NAME="$(uname -m)"
APP_VERSION=""
DMG_NAME=""
DMG_NAME_CUSTOM=0

resolve_version() {
    if [[ -n "${APP_VERSION}" ]]; then
        printf '%s\n' "${APP_VERSION}"
        return 0
    fi

    python - <<'PYVERSION' 2>/dev/null || true
from importlib.metadata import PackageNotFoundError, version

try:
    print(version("GONet_Wizard"))
except PackageNotFoundError:
    pass
PYVERSION
}

sanitize_for_filename() {
    # Keep release filenames shell- and URL-friendly without changing the
    # human-facing version used inside the README.
    sed -E 's/[^A-Za-z0-9._+-]+/-/g; s/^-+//; s/-+$//'
}

usage() {
    cat <<USAGE
Usage: build_tools/macos/build_dmg.sh [options]

Build an unsigned drag-and-drop macOS DMG for GONet Wizard.

Options:
  --app-path PATH       Use an existing .app bundle instead of dist/GONet Wizard.app.
  --output-dir PATH     Directory where the DMG will be written. Default: dist/.
  --dmg-name NAME       Output DMG filename. Default: versioned unsigned name.
  --version VERSION     Version label to include in the default DMG name.
  --volume-name NAME    Mounted volume name. Default: ${VOLUME_NAME}
  --skip-pyinstaller   Do not run PyInstaller; fail if the .app bundle is missing.
  --force-pyinstaller  Always rebuild the .app bundle before creating the DMG.
  --no-clean-staging   Leave build/dmg-staging in place for inspection.
  -h, --help           Show this help message.

Examples:
  build_tools/macos/build_dmg.sh
  build_tools/macos/build_dmg.sh --skip-pyinstaller
  build_tools/macos/build_dmg.sh --dmg-name GONet-Wizard-test.dmg
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --app-path)
            APP_PATH="$2"
            APP_PATH_CUSTOM=1
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --dmg-name)
            DMG_NAME="$2"
            DMG_NAME_CUSTOM=1
            shift 2
            ;;
        --version)
            APP_VERSION="$2"
            shift 2
            ;;
        --volume-name)
            VOLUME_NAME="$2"
            shift 2
            ;;
        --skip-pyinstaller)
            RUN_PYINSTALLER=never
            shift
            ;;
        --force-pyinstaller)
            RUN_PYINSTALLER=always
            shift
            ;;
        --no-clean-staging)
            CLEAN_STAGING=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "ERROR: DMG creation requires macOS." >&2
    exit 1
fi

if ! command -v hdiutil >/dev/null 2>&1; then
    echo "ERROR: hdiutil was not found. DMG creation requires macOS hdiutil." >&2
    exit 1
fi

cd "${REPO_ROOT}"

RESOLVED_VERSION="$(resolve_version | head -n 1)"
if [[ -z "${RESOLVED_VERSION}" ]]; then
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        RESOLVED_VERSION="$(git describe --tags --dirty --always 2>/dev/null || true)"
    fi
fi
if [[ -z "${RESOLVED_VERSION}" ]]; then
    RESOLVED_VERSION="dev"
fi

SAFE_VERSION="$(printf '%s' "${RESOLVED_VERSION}" | sanitize_for_filename)"
if [[ -z "${SAFE_VERSION}" ]]; then
    SAFE_VERSION="dev"
fi

if [[ "${DMG_NAME_CUSTOM}" == "0" ]]; then
    DMG_NAME="GONet-Wizard-${SAFE_VERSION}-macOS-${ARCH_NAME}-unsigned.dmg"
fi

if [[ "${RUN_PYINSTALLER}" == "always" || ( "${RUN_PYINSTALLER}" == "auto" && "${APP_PATH_CUSTOM}" == "0" && ! -d "${APP_PATH}" ) ]]; then
    echo "Building ${APP_NAME}.app with PyInstaller..."
    python -m PyInstaller build_tools/pyinstaller/gonet_wizard_gui.spec --clean --noconfirm
fi

if [[ ! -d "${APP_PATH}" ]]; then
    cat >&2 <<ERROR
ERROR: App bundle not found: ${APP_PATH}

Build it first with:
  python -m PyInstaller build_tools/pyinstaller/gonet_wizard_gui.spec --clean --noconfirm

or pass --app-path PATH to an existing app bundle.
ERROR
    exit 1
fi

mkdir -p "${OUTPUT_DIR}" "${BUILD_DIR}"

STAGING_DIR="${BUILD_DIR}/dmg-staging"
DMG_PATH="${OUTPUT_DIR}/${DMG_NAME}"

rm -rf "${STAGING_DIR}"
mkdir -p "${STAGING_DIR}"

# Preserve macOS bundle metadata more reliably than a plain cp.
ditto "${APP_PATH}" "${STAGING_DIR}/${APP_NAME}.app"
ln -s /Applications "${STAGING_DIR}/Applications"

cat > "${STAGING_DIR}/README-FIRST.txt" <<README
GONet Wizard for macOS
======================

Version: ${RESOLVED_VERSION}

This is an unsigned test DMG intended for GitHub release testing.

Install:
1. Drag "${APP_NAME}.app" to the Applications shortcut.
2. Launch it from Applications.

Unsigned build note:
macOS may block the first launch because this build is not signed or notarized.
For internal testing, right-click/control-click the app and choose Open, or open
System Settings > Privacy & Security and allow the app after the first blocked
launch.

The command-line interface is still available through the normal Python package
installation path for power users and developers.
README

rm -f "${DMG_PATH}"

echo "Creating ${DMG_PATH}..."
echo "Version label: ${RESOLVED_VERSION}"
hdiutil create \
    -volname "${VOLUME_NAME}" \
    -srcfolder "${STAGING_DIR}" \
    -ov \
    -format UDZO \
    "${DMG_PATH}"

if [[ "${CLEAN_STAGING}" == "1" ]]; then
    rm -rf "${STAGING_DIR}"
fi

echo "DMG created: ${DMG_PATH}"
