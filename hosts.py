"""Module for migrating network device data from YAML to SQLite database."""

from pathlib import Path

import yaml

from utils.database import Device, create_db_and_tables, get_db
from utils.devices import clear_device_cache


def migrate_data():
    """Migrates device data from hosts.yaml to the SQLite database."""
    create_db_and_tables()

    yaml_file = Path("hosts.yaml")
    if not yaml_file.exists():
        print(f"{yaml_file} not found. Please create it with your device data.")
        return

    with get_db() as db:
        try:
            with yaml_file.open() as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error parsing hosts.yaml: {e}")
            return

        devices_data = data.get("devices", [])
        if not devices_data:
            print("No devices found in hosts.yaml")
            return

        # DRY: Introspect the model to get schema source of truth
        # Get all column names except the primary key 'id'
        model_columns = {c.name for c in Device.__table__.columns if c.name != "id"}

        new_devices_added = False
        for dev_data in devices_data:
            name = dev_data.get("name")

            # 1. Dynamic Validation against the Model
            # Check if the YAML has all the columns the Database requires
            missing_fields = model_columns - set(dev_data.keys())
            if missing_fields:
                print(f"Skipping '{name or 'unknown'}': missing fields {missing_fields}")
                continue

            existing_device = db.query(Device).filter(Device.name == name).first()
            if existing_device:
                print(f"Device {name} already exists, skipping.")
                continue

            # 2. Dynamic Instantiation
            # Unpack the dict directly. Because we validated keys above, this is safe.
            # This works even if you add new columns to the database later.
            device_args = {k: v for k, v in dev_data.items() if k in model_columns}
            device = Device(**device_args)

            db.add(device)
            print(f"Adding device {name}.")
            new_devices_added = True

        if new_devices_added:
            db.commit()
            clear_device_cache()
            print("Data migration complete.")
        else:
            print("No new devices to add.")


if __name__ == "__main__":
    migrate_data()
