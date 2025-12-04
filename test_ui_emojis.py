import logging

from ui import NetworkAgentUI, setup_colored_logging


def test_ui():
    # Setup logging
    setup_colored_logging()
    logger = logging.getLogger("test_ui")
    logger.setLevel(logging.DEBUG)

    # Initialize UI
    ui = NetworkAgentUI()

    # Test Header
    ui.print_header()

    # Test Log messages
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.debug("This is a debug message")

    # Test UI methods
    ui.print_device_status("R1", "connected", "192.168.1.1")
    ui.print_device_status("R2", "disconnected", "Connection timeout")

    ui.print_executing("show ip interface brief")
    ui.print_config_applied("Switch1")

    ui.print_result_header("Interface Status")
    ui.print_output(
        {"structured_data": {"interfaces": ["Gi0/0", "Gi0/1"]}, "summary": "Found 2 interfaces"}
    )

    ui.print_warning("High CPU usage detected")
    ui.print_error("Authentication failed")

    ui.print_footer()
    ui.print_goodbye()


if __name__ == "__main__":
    test_ui()
