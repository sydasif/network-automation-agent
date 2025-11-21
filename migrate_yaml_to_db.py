import yaml
from utils.database import SessionLocal, Device

def migrate_data():
    db = SessionLocal()
    with open("hosts.yaml", "r") as f:
        data = yaml.safe_load(f)

    devices = data.get("devices", [])
    for device_data in devices:
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
