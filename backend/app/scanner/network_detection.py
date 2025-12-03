"""
Automatic network detection utility.
Detects the current network(s) the host is connected to.
"""

import ipaddress
import socket
import subprocess
from typing import List, Optional


def get_default_gateway() -> Optional[str]:
    """Get the default gateway IP address."""
    try:
        # Try to get default gateway using netstat
        result = subprocess.run(["netstat", "-rn"], capture_output=True, text=True, timeout=5)

        for line in result.stdout.split("\n"):
            parts = line.split()
            # Look for default route (0.0.0.0 or default)
            if len(parts) >= 2 and (parts[0] == "default" or parts[0] == "0.0.0.0"):
                gateway = parts[1]
                # Validate it's an IP address
                try:
                    ipaddress.ip_address(gateway)
                    return gateway
                except ValueError:
                    continue

        return None
    except Exception as e:
        print(f"Error getting default gateway: {e}")
        return None


def get_local_ip_and_netmask() -> Optional[tuple]:
    """
    Get the local IP address and netmask of the primary network interface.
    Returns tuple of (ip_address, netmask) or None.
    """
    try:
        # Get default gateway first
        gateway = get_default_gateway()
        if not gateway:
            return None

        # Use ifconfig to get interface details
        result = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5)

        ip_addr = None
        netmask = None

        for line in result.stdout.split("\n"):
            # New interface
            if line and not line.startswith("\t") and not line.startswith(" "):
                # Check if previous interface had the gateway's network
                if ip_addr and netmask:
                    try:
                        network = ipaddress.ip_network(f"{ip_addr}/{netmask}", strict=False)
                        gateway_ip = ipaddress.ip_address(gateway)
                        if gateway_ip in network:
                            return (ip_addr, netmask)
                    except ValueError:
                        pass

                line.split(":")[0].strip()
                ip_addr = None
                netmask = None

            # Look for inet line with IP address
            if "inet " in line and "inet6" not in line:
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part == "inet" and i + 1 < len(parts):
                        ip_addr = parts[i + 1]
                    elif part == "netmask" and i + 1 < len(parts):
                        # Netmask might be in hex format (0xffffff00)
                        netmask_value = parts[i + 1]
                        if netmask_value.startswith("0x"):
                            # Convert hex netmask to dotted decimal
                            hex_val = int(netmask_value, 16)
                            netmask = ".".join(
                                [
                                    str((hex_val >> 24) & 0xFF),
                                    str((hex_val >> 16) & 0xFF),
                                    str((hex_val >> 8) & 0xFF),
                                    str(hex_val & 0xFF),
                                ]
                            )
                        else:
                            netmask = netmask_value

        # Check last interface
        if ip_addr and netmask:
            try:
                network = ipaddress.ip_network(f"{ip_addr}/{netmask}", strict=False)
                gateway_ip = ipaddress.ip_address(gateway)
                if gateway_ip in network:
                    return (ip_addr, netmask)
            except ValueError:
                pass

        return None

    except Exception as e:
        print(f"Error getting local IP and netmask: {e}")
        return None


def netmask_to_cidr(netmask: str) -> int:
    """Convert dotted decimal netmask to CIDR prefix length."""
    try:
        return ipaddress.IPv4Network(f"0.0.0.0/{netmask}").prefixlen
    except ValueError:
        # Default to /24 if conversion fails
        return 24


def detect_current_network() -> Optional[str]:
    """
    Detect the current network in CIDR notation using socket library.
    Returns network like "192.168.1.0/24" or None if detection fails.
    Works in containers without ifconfig.
    """
    try:
        # Create a socket to determine the local IP
        # This works by connecting to an external address (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        try:
            # Connect to Google DNS (doesn't matter if it fails, we just need the local IP)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        finally:
            s.close()

        # Default to /24 network (common for home/office networks)
        # This is a reasonable assumption for most local networks
        network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
        return str(network)

    except Exception as e:
        print(f"Error detecting network: {e}")
        # Fallback: try the old method
        ip_and_netmask = get_local_ip_and_netmask()
        if ip_and_netmask:
            ip_addr, netmask = ip_and_netmask
            try:
                cidr_prefix = netmask_to_cidr(netmask)
                network = ipaddress.ip_network(f"{ip_addr}/{cidr_prefix}", strict=False)
                return str(network)
            except Exception:
                pass
        return None


def detect_all_local_networks() -> List[str]:
    """
    Detect all local networks the host is connected to.
    Returns list of networks in CIDR notation.
    """
    networks = []

    try:
        result = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5)

        current_ip = None
        current_netmask = None

        for line in result.stdout.split("\n"):
            # New interface
            if line and not line.startswith("\t") and not line.startswith(" "):
                # Process previous interface
                if current_ip and current_netmask:
                    try:
                        cidr_prefix = netmask_to_cidr(current_netmask)
                        network = ipaddress.ip_network(f"{current_ip}/{cidr_prefix}", strict=False)
                        network_str = str(network)

                        # Skip loopback and link-local
                        if not network_str.startswith("127.") and not network_str.startswith(
                            "169.254."
                        ):
                            networks.append(network_str)
                    except Exception:
                        pass

                current_ip = None
                current_netmask = None

            # Look for inet line
            if "inet " in line and "inet6" not in line:
                parts = line.strip().split()
                for i, part in enumerate(parts):
                    if part == "inet" and i + 1 < len(parts):
                        current_ip = parts[i + 1]
                    elif part == "netmask" and i + 1 < len(parts):
                        netmask_value = parts[i + 1]
                        if netmask_value.startswith("0x"):
                            hex_val = int(netmask_value, 16)
                            current_netmask = ".".join(
                                [
                                    str((hex_val >> 24) & 0xFF),
                                    str((hex_val >> 16) & 0xFF),
                                    str((hex_val >> 8) & 0xFF),
                                    str(hex_val & 0xFF),
                                ]
                            )
                        else:
                            current_netmask = netmask_value

        # Process last interface
        if current_ip and current_netmask:
            try:
                cidr_prefix = netmask_to_cidr(current_netmask)
                network = ipaddress.ip_network(f"{current_ip}/{cidr_prefix}", strict=False)
                network_str = str(network)

                if not network_str.startswith("127.") and not network_str.startswith("169.254."):
                    networks.append(network_str)
            except Exception:
                pass

    except Exception as e:
        print(f"Error detecting networks: {e}")

    # Remove duplicates while preserving order
    seen = set()
    unique_networks = []
    for net in networks:
        if net not in seen:
            seen.add(net)
            unique_networks.append(net)

    return unique_networks


if __name__ == "__main__":
    # Test network detection
    print("Detecting current network...")
    current = detect_current_network()
    if current:
        print(f"Current network: {current}")
    else:
        print("Could not detect current network")

    print("\nAll local networks:")
    all_networks = detect_all_local_networks()
    for net in all_networks:
        print(f"  - {net}")
