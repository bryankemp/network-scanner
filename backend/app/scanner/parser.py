"""
Parser for nmap XML output.
Extracted from network_scan/mapper.py
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any


def parse_nmap_xml(xml_file: str) -> List[Dict[str, Any]]:
    """
    Parse nmap XML output and extract host/service information.

    Args:
        xml_file: Path to nmap XML output file

    Returns:
        List of host dictionaries with discovered information
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    hosts = []
    for host in root.findall("host"):
        if host.find("status").get("state") != "up":
            continue

        host_data = {
            "ip": "",
            "hostname": "",
            "mac": "",
            "vendor": "",
            "ports": [],
            "os": "",
            "os_accuracy": None,
            "is_vm": False,
            "vm_type": "",
            "uptime_seconds": None,
            "last_boot": None,
            "distance": None,
            "cpe": None,
            "traceroute": [],
        }

        # Get IP address
        addr = host.find('address[@addrtype="ipv4"]')
        if addr is not None:
            host_data["ip"] = addr.get("addr")

        # Get MAC address and vendor
        mac_addr = host.find('address[@addrtype="mac"]')
        if mac_addr is not None:
            host_data["mac"] = mac_addr.get("addr")
            host_data["vendor"] = mac_addr.get("vendor", "")

            # Detect VMs by vendor
            vm_vendors = ["QEMU", "VMware", "VirtualBox", "Xen", "Microsoft", "Parallels"]
            for vm_vendor in vm_vendors:
                if vm_vendor.lower() in host_data["vendor"].lower():
                    host_data["is_vm"] = True
                    host_data["vm_type"] = vm_vendor
                    break

        # Get hostname
        hostnames = host.find("hostnames")
        if hostnames is not None:
            hostname = hostnames.find("hostname")
            if hostname is not None:
                host_data["hostname"] = hostname.get("name", "")

        # Get OS info with accuracy
        os_elem = host.find("os")
        if os_elem is not None:
            osmatch = os_elem.find("osmatch")
            if osmatch is not None:
                host_data["os"] = osmatch.get("name", "")
                host_data["os_accuracy"] = int(osmatch.get("accuracy", 0))

            # Get CPE from OS detection
            osclass = os_elem.find("osclass")
            if osclass is not None:
                cpe_elem = osclass.find("cpe")
                if cpe_elem is not None:
                    host_data["cpe"] = cpe_elem.text

        # Get uptime
        uptime_elem = host.find("uptime")
        if uptime_elem is not None:
            host_data["uptime_seconds"] = int(uptime_elem.get("seconds", 0))
            host_data["last_boot"] = uptime_elem.get("lastboot", "")

        # Get distance (network hops)
        distance_elem = host.find("distance")
        if distance_elem is not None:
            host_data["distance"] = int(distance_elem.get("value", 0))

        # Get traceroute
        trace_elem = host.find("trace")
        if trace_elem is not None:
            for hop in trace_elem.findall("hop"):
                hop_data = {
                    "ttl": int(hop.get("ttl", 0)),
                    "ip": hop.get("ipaddr", ""),
                    "hostname": hop.get("host", ""),
                    "rtt": float(hop.get("rtt", 0)),
                }
                host_data["traceroute"].append(hop_data)

        # Get ports and services
        ports = host.find("ports")
        if ports is not None:
            for port in ports.findall("port"):
                if port.find("state").get("state") == "open":
                    service = port.find("service")

                    # Get script output
                    import json

                    scripts = {}
                    for script in port.findall("script"):
                        script_id = script.get("id")
                        script_output = script.get("output", "")
                        if script_id and script_output:
                            scripts[script_id] = script_output

                    # Get CPE for service
                    service_cpe = None
                    if service is not None:
                        cpe_elem = service.find("cpe")
                        if cpe_elem is not None:
                            service_cpe = cpe_elem.text

                    port_data = {
                        "port": port.get("portid"),
                        "protocol": port.get("protocol"),
                        "service": service.get("name", "") if service is not None else "",
                        "product": service.get("product", "") if service is not None else "",
                        "version": service.get("version", "") if service is not None else "",
                        "extrainfo": service.get("extrainfo", "") if service is not None else "",
                        "cpe": service_cpe,
                        "script_output": json.dumps(scripts) if scripts else None,
                    }
                    host_data["ports"].append(port_data)

        hosts.append(host_data)

    return hosts


def detect_enhanced_vm(host_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced VM/container detection beyond basic MAC vendor matching.

    Args:
        host_data: Host dictionary from parse_nmap_xml

    Returns:
        Updated host_data with enhanced VM detection
    """
    # Already detected by MAC vendor
    if host_data.get("is_vm"):
        return host_data

    # Check OS string for virtualization indicators
    os_info = host_data.get("os", "").lower()
    vm_indicators = {
        "docker": "Docker",
        "lxc": "LXC",
        "container": "Container",
        "kvm": "KVM",
        "hyperv": "Hyper-V",
        "vmware": "VMware",
        "virtualbox": "VirtualBox",
        "xen": "Xen",
    }

    for indicator, vm_type in vm_indicators.items():
        if indicator in os_info:
            host_data["is_vm"] = True
            host_data["vm_type"] = vm_type
            break

    # Check for Docker bridge network patterns
    ip = host_data.get("ip", "")
    if ip.startswith("172.17.") or ip.startswith("172.18."):
        host_data["is_vm"] = True
        host_data["vm_type"] = "Docker" if not host_data.get("vm_type") else host_data["vm_type"]

    # Check for LXC network patterns (10.0.3.x is common in LXC)
    if ip.startswith("10.0.3."):
        host_data["is_vm"] = True
        host_data["vm_type"] = "LXC" if not host_data.get("vm_type") else host_data["vm_type"]

    return host_data
