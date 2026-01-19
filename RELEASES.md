# Release and Versioning Documentation

## Overview

This repository uses GitHub Actions to automatically build and release executables whenever code is pushed to the main branch or when version tags are created.

## How It Works

### Automatic Builds

The CI/CD pipeline (`.github/workflows/build-release.yml`) automatically:

1. **Builds executables** for Windows, Linux, and macOS using PyInstaller
2. **Creates releases** on the GitHub Releases page
3. **Uploads artifacts** (compiled executables) to each release

### Triggering Releases

Releases are triggered in two ways:

#### 1. Push to Main Branch (Automatic Versioning)
- When you push to the `main` or `master` branch
- Version is auto-generated as: `v[commit-count].[short-sha]`
- Example: `v42.a1b2c3d`
- Creates a **pre-release** (draft = false, prerelease = true)

#### 2. Git Tags (Manual Versioning)
- When you create and push a tag starting with `v`
- Version uses the tag name directly
- Example: `v1.0.0`, `v2.1.3`
- Creates a **full release** (draft = false, prerelease = false)

### Creating a Tagged Release

To create a manually versioned release:

```bash
# Create a tag
git tag v1.0.0

# Push the tag to GitHub
git push origin v1.0.0
```

Or create both together:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

### Version Numbering Strategy

We recommend following [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `v1.2.3`)
  - **MAJOR**: Breaking changes (e.g., `v2.0.0`)
  - **MINOR**: New features, backwards compatible (e.g., `v1.3.0`)
  - **PATCH**: Bug fixes, backwards compatible (e.g., `v1.2.4`)

### Build Artifacts

Each release includes three executables:

- `InternetAnalogRadio-windows.exe` - Windows executable
- `InternetAnalogRadio-linux` - Linux executable
- `InternetAnalogRadio-macos` - macOS executable

### Build Process

The build process:

1. Checks out the repository code
2. Sets up Python 3.11
3. Installs dependencies from `requirements.txt`
4. Installs PyInstaller
5. Installs VLC (required for the application)
6. Runs `build.py` to create the executable
7. Uploads the executable as an artifact

### VLC Requirement

The application requires VLC Media Player to be installed on the user's system. The CI installs VLC during the build process:

- **Linux**: `apt-get install vlc libvlc-dev`
- **macOS**: `brew install --cask vlc`
- **Windows**: VLC bindings are used via python-vlc

### Viewing Releases

All releases are available on the GitHub Releases page:
https://github.com/Glowing-Radiant/the_internet-analog_radio/releases

### Workflow Details

The workflow consists of two jobs:

1. **build**: Builds executables on all three platforms in parallel
2. **release**: Creates a GitHub release and uploads all artifacts

## Examples

### Example 1: Push to Main
```bash
git add .
git commit -m "Add new feature"
git push origin main
```
Result: Creates release `v43.d4e5f6g` (auto-versioned, pre-release)

### Example 2: Create Version Tag
```bash
git tag v1.0.0
git push origin v1.0.0
```
Result: Creates release `v1.0.0` (full release)

### Example 3: Create Patch Release
```bash
git tag v1.0.1
git push origin v1.0.1
```
Result: Creates release `v1.0.1` (full release)

## Troubleshooting

### Build Failures

If a build fails:

1. Check the Actions tab on GitHub
2. Review the logs for the failed job
3. Common issues:
   - Missing dependencies in `requirements.txt`
   - PyInstaller compatibility issues
   - Platform-specific build errors

### No Artifacts

If artifacts aren't uploaded:

1. Verify `dist/InternetAnalogRadio` (or `.exe`) was created
2. Check the build logs for PyInstaller errors
3. Ensure `build.py` completes successfully

## Notes

- Build artifacts (dist/, build/) are already in `.gitignore`
- The workflow only creates releases on `main`/`master` branches or tags
- Pre-releases are marked as such on the releases page
- All builds include the sounds directory required by the application
