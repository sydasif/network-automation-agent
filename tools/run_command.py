import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Union

from langchain_core.tools import tool
from netmiko import ConnectHandler

from utils.devices import load_devices


@tool
def run_command(device: str | list[str], command: str) -> str:
    """Execute `command` on one or more devices defined in config.

    Returns JSON string with results for each device.
    """
    all_devices = load_devices()

    if isinstance(device, str):
        device_list = [device]
    else:
        device_list = device

    for dev in device_list:
        if dev not in all_devices:
            return json.dumps({
                "error": f"Device '{dev}' not found",
                "available_devices": list(all_devices.keys()),
            })

    results = {}

    def execute_on_device(dev_name: str):
        cfg = all_devices[dev_name]
        try:
            conn = ConnectHandler(
                device_type=cfg["device_type"],
                host=cfg["host"],
                username=cfg["username"],
                password=cfg["password"],
                timeout=30,
            )

            try:
                out = conn.send_command(command, use_textfsm=True)
                if isinstance(out, str):
                    parsed_type = "raw"
                    parsed_output = out
                else:
                    parsed_type = "structured"
                    parsed_output = out
            except Exception:
                out = conn.send_command(command)
                parsed_type = "raw"
                parsed_output = out

            conn.disconnect()

            return dev_name, {
                "success": True,
                "type": parsed_type,
                "data": parsed_output,
            }

        except Exception as e:
            return dev_name, {"success": False, "error": str(e)}

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(execute_on_device, d): d for d in device_list}
        for fut in as_completed(futures):
            dev, out = fut.result()
            results[dev] = out

    return json.dumps({"command": command, "devices": results}, indent=2)
