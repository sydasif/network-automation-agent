from pathlib import Path

import yaml

from utils.database import Device, SessionLocal, create_db_and_tables


def migrate_data():
    # Create database tables if they don't exist
    create_db_and_tables()

    # Check if hosts.yaml exists
    if not Path("hosts.yaml").exists():
        print("hosts.yaml file not found. Please create it with your device data.")
        return

    db = SessionLocal()
    try:
        with Path("hosts.yaml").open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error parsing hosts.yaml: {e}")
        db.close()
        return
    except FileNotFoundError:
        print("hosts.yaml file not found. Please create it with your device data.")
        db.close()
        return

    devices = data.get("devices", [])
    if not devices:
        print("No devices found in hosts.yaml")
        db.close()
        return

    for device_data in devices:
        # Check if all required fields exist
        required_fields = ["name", "host", "username", "password", "device_type"]
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
            password=device_data["password"],
            device_type=device_data["device_type"],
        )
        db.add(device)
        print(f"Adding device {device_data['name']}.")

    db.commit()
    db.close()
    print("Data migration complete.")


if __name__ == "__main__":
    migrate_data()
