"""
Version check module for comparing local version with GitHub releases.
"""
import os
import sys
import re
import requests
from pathlib import Path
from typing import Optional, Tuple

# GitHub API endpoint for releases
GITHUB_API_URL = "https://api.github.com/repos/Franko12345/WebScrappingApp/releases/latest"


def get_local_version() -> Optional[Tuple[int, int, int]]:
    """
    Read the local VERSION file and return version as (major, minor, patch).
    
    Returns:
        Tuple of (major, minor, patch) or None if file doesn't exist or is invalid.
    """
    # Handle PyInstaller bundle path
    if getattr(sys, 'frozen', False):
        # Running as a bundled executable
        version_path = Path(sys.executable).parent / "VERSION"
    else:
        # Running as a normal Python script
        version_path = Path(__file__).parent.parent / "VERSION"
    
    if not version_path.exists():
        return None
    
    try:
        with open(version_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse VERSION file format: VERSION_MAJOR = 1, VERSION_MINOR = 0, PATCHLEVEL = 0
        major_match = re.search(r'VERSION_MAJOR\s*=\s*(\d+)', content)
        minor_match = re.search(r'VERSION_MINOR\s*=\s*(\d+)', content)
        patch_match = re.search(r'PATCHLEVEL\s*=\s*(\d+)', content)
        
        if major_match and minor_match and patch_match:
            return (int(major_match.group(1)), int(minor_match.group(1)), int(patch_match.group(1)))
    except Exception as e:
        print(f"Error reading local version: {e}")
    
    return None


def get_github_version() -> Optional[Tuple[int, int, int]]:
    """
    Fetch the latest release version from GitHub API.
    
    Returns:
        Tuple of (major, minor, patch) or None if request fails.
    """
    try:
        response = requests.get(GITHUB_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract tag_name (e.g., "v1.0.0")
        tag_name = data.get('tag_name', '')
        if not tag_name:
            return None
        
        # Remove 'v' prefix and parse version
        version_str = tag_name.lstrip('v')
        version_parts = version_str.split('.')
        
        if len(version_parts) >= 3:
            return (int(version_parts[0]), int(version_parts[1]), int(version_parts[2]))
        elif len(version_parts) == 2:
            return (int(version_parts[0]), int(version_parts[1]), 0)
        elif len(version_parts) == 1:
            return (int(version_parts[0]), 0, 0)
    except requests.RequestException as e:
        print(f"Error fetching GitHub version: {e}")
    except Exception as e:
        print(f"Error parsing GitHub version: {e}")
    
    return None


def compare_versions(local: Tuple[int, int, int], remote: Tuple[int, int, int]) -> int:
    """
    Compare two version tuples.
    
    Returns:
        -1 if local < remote (update available)
        0 if local == remote (up to date)
        1 if local > remote (local is newer)
    """
    if local < remote:
        return -1
    elif local > remote:
        return 1
    else:
        return 0


def check_update_available() -> dict:
    """
    Check if an update is available by comparing local and GitHub versions.
    
    Returns:
        Dictionary with:
        - 'update_available': bool
        - 'local_version': str or None
        - 'remote_version': str or None
        - 'error': str or None
    """
    local_version = get_local_version()
    remote_version = get_github_version()
    
    if local_version is None:
        return {
            'update_available': False,
            'local_version': None,
            'remote_version': f"{remote_version[0]}.{remote_version[1]}.{remote_version[2]}" if remote_version else None,
            'error': 'Could not read local version file'
        }
    
    if remote_version is None:
        return {
            'update_available': False,
            'local_version': f"{local_version[0]}.{local_version[1]}.{local_version[2]}",
            'remote_version': None,
            'error': 'Could not fetch remote version from GitHub'
        }
    
    comparison = compare_versions(local_version, remote_version)
    update_available = comparison < 0
    
    return {
        'update_available': update_available,
        'local_version': f"{local_version[0]}.{local_version[1]}.{local_version[2]}",
        'remote_version': f"{remote_version[0]}.{remote_version[1]}.{remote_version[2]}",
        'error': None
    }


if __name__ == "__main__":
    # Test the version check
    result = check_update_available()
    print(f"Update available: {result['update_available']}")
    print(f"Local version: {result['local_version']}")
    print(f"Remote version: {result['remote_version']}")
    if result['error']:
        print(f"Error: {result['error']}")

