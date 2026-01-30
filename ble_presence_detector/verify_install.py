#!/usr/bin/env python3
"""Verification script to check BLE presence detector installation."""

import sys
from pathlib import Path


def check_file_exists(filepath: Path, description: str) -> bool:
    """Check if a file exists."""
    if filepath.exists():
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description} MISSING: {filepath}")
        return False


def check_directory_exists(dirpath: Path, description: str) -> bool:
    """Check if a directory exists."""
    if dirpath.exists() and dirpath.is_dir():
        print(f"✓ {description}: {dirpath}")
        return True
    else:
        print(f"✗ {description} MISSING: {dirpath}")
        return False


def main():
    """Run verification checks."""
    print("BLE Presence Detector - Installation Verification")
    print("=" * 60)
    print()

    base_dir = Path(__file__).parent
    all_good = True

    # Check directory structure
    print("Checking directory structure...")
    dirs = [
        (base_dir / "src", "Source directory"),
        (base_dir / "src" / "core", "Core module"),
        (base_dir / "src" / "config", "Config module"),
        (base_dir / "src" / "identifiers", "Identifiers module"),
        (base_dir / "src" / "scanner", "Scanner module"),
        (base_dir / "src" / "tracking", "Tracking module"),
        (base_dir / "src" / "publishing", "Publishing module"),
        (base_dir / "src" / "repository", "Repository module"),
        (base_dir / "config", "Config directory"),
        (base_dir / "tests", "Tests directory"),
    ]

    for dirpath, desc in dirs:
        all_good &= check_directory_exists(dirpath, desc)

    print()

    # Check critical files
    print("Checking critical files...")
    files = [
        (base_dir / "src" / "main.py", "Main application"),
        (base_dir / "src" / "core" / "protocols.py", "Core protocols"),
        (base_dir / "src" / "core" / "exceptions.py", "Core exceptions"),
        (base_dir / "src" / "config" / "models.py", "Config models"),
        (base_dir / "src" / "config" / "loader.py", "Config loader"),
        (base_dir / "src" / "identifiers" / "base.py", "Base identifier"),
        (base_dir / "src" / "identifiers" / "factory.py", "Identifier factory"),
        (base_dir / "src" / "scanner" / "ble_scanner.py", "BLE scanner"),
        (base_dir / "src" / "tracking" / "presence_tracker.py", "Presence tracker"),
        (base_dir / "src" / "publishing" / "mqtt_publisher.py", "MQTT publisher"),
        (base_dir / "src" / "repository" / "json_repository.py", "JSON repository"),
        (base_dir / "config" / "devices.yaml", "Device configuration"),
        (base_dir / "requirements.txt", "Requirements file"),
        (base_dir / "README.md", "README"),
    ]

    for filepath, desc in files:
        all_good &= check_file_exists(filepath, desc)

    print()

    # Check service file
    print("Checking service integration...")
    service_file = base_dir.parent / "50-ble-presence.service"
    all_good &= check_file_exists(service_file, "Service file")

    print()

    # Try importing modules
    print("Checking Python imports...")
    try:
        sys.path.insert(0, str(base_dir))

        # Try importing without dependencies
        import src.core.protocols
        print("✓ Core protocols import")

        import src.core.exceptions
        print("✓ Core exceptions import")

        # These will fail without dependencies, which is expected
        print()
        print("Note: Some imports may fail until dependencies are installed.")
        print("Run: pip3 install -r requirements.txt")

    except Exception as e:
        print(f"✗ Import error: {e}")
        all_good = False

    print()
    print("=" * 60)

    if all_good:
        print("✓ ALL CHECKS PASSED")
        print()
        print("Next steps:")
        print("1. Install dependencies: pip3 install -r requirements.txt")
        print("2. Configure devices: edit config/devices.yaml")
        print("3. Test manually: python3 src/main.py config/devices.yaml")
        print("4. Install as service: ../ha-services-run.sh start ble-presence")
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        print()
        print("Please review the errors above and fix any issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
