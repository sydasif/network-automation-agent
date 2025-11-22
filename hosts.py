"""Module for migrating network device data from YAML to SQLite database.

This module provides functionality to migrate network device configurations
from a YAML file to a SQLite database. It's used during the initial setup
process to populate the device inventory database.
"""

from pathlib import Path

import yaml

from utils.database import Device, create_db_and_tables, get_db

from utils.devices import clear_device_cache


def migrate_data():
    """Migrates device data from hosts.yaml to the SQLite database.

    This function reads device configurations from hosts.yaml, validates
    the required fields, and adds them to the database. It skips devices
    that already exist in the database and clears the device cache after
    successful migration.

    The function handles various error conditions including:
    - Missing hosts.yaml file
    - YAML parsing errors
    - Missing required device fields
    - Database operations

    This function should be run after configuring the hosts.yaml file to
    initialize the device inventory database.
    """
    # Create database tables if they don't exist
    create_db_and_tables()

    # Check if hosts.yaml exists
    if not Path("hosts.yaml").exists():
        print("hosts.yaml file not found. Please create it with your device data.")
        return

    with get_db() as db:
        try:
            with Path("hosts.yaml").open() as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error parsing hosts.yaml: {e}")
            return
        except FileNotFoundError:
            print("hosts.yaml file not found. Please create it with your device data.")
            return

        devices = data.get("devices", [])
        if not devices:
            print("No devices found in hosts.yaml")
            return

        new_devices_added = False
        for device_data in devices:
            # Check if all required fields exist
            required_fields = ["name", "host", "username", "password_env_var", "device_type"]
            missing_fields = [field for field in required_fields if field not in device_data]
            if missing_fields:
                print(f"Skipping device due to missing fields: {missing_fields}")
                continue

            existing_device = db.query(Device).filter(Device.name == device_data["name"]).first()
            if existing_device:
                print(f"Device {device_data['name']} already exists, skipping.")
                continue

            device = Device(
                name=device_data["name"],
                host=device_data["host"],
                username=device_data["username"],
                password_env_var=device_data["password_env_var"],
                device_type=device_data["device_type"],
            )
            db.add(device)
            print(f"Adding device {device_data['name']}.")
            new_devices_added = True

        if new_devices_added:
            db.commit()

            clear_device_cache()

            print("Data migration complete.")
        else:
            print("No new devices to add.")


if __name__ == "__main__":
    migrate_data()
