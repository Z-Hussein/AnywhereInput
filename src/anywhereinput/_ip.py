"""Shared IP parsing and validation utilities."""

import ipaddress
from typing import List, Tuple


def parse_ip_str(addr: str) -> Tuple[str, int]:
    """Parse 'host:port' or bare host from aiohttp request.remote.

    Returns (host, port) tuple.
    """
    addr = addr.strip()
    if not addr or addr == "unknown":
        return ("unknown", 0)
    if addr.startswith("["):
        bracket_end = addr.rfind("]")
        if (
            bracket_end != -1
            and bracket_end + 1 < len(addr)
            and addr[bracket_end + 1] == ":"
        ):
            host = addr[1:bracket_end]
            port_str = addr[bracket_end + 2 :]
            port = int(port_str) if port_str.isdigit() else 0
            return (host, port)
        return (addr[1:-1] if addr.endswith("]") else addr, 0)
    last_colon = addr.rfind(":")
    if last_colon > 0:
        potential_port = addr[last_colon + 1 :]
        if potential_port.isdigit():
            return (addr[:last_colon], int(potential_port))
    return (addr, 0)


def extract_ip(client_ip: str) -> str:
    """Extract IP address from stored format:
    - Bracketed IPv6 with port: [::1]:8080 -> ::1
    - Bare IPv6 (no port): 2003:abc::1 or 2003:abc::1%eth0 -> 2003:abc::1
    - IPv4 with port: 192.168.1.1:8080 -> 192.168.1.1
    - Bare IPv4: 192.168.1.1 -> 192.168.1.1
    """
    if client_ip.startswith("["):
        # Bracketed IPv6 with port: [::1]:8080 -> extract ::1
        bracket_end = client_ip.find("]")
        return client_ip[1:bracket_end] if bracket_end > 0 else client_ip
    # Bare IPv6: 2003:abc::1 or 2003:abc::1%eth0 (multiple colons or zone index)
    if client_ip.count(":") >= 2 or "%" in client_ip:
        return client_ip.split("%")[0]  # strip zone index if present
    # IPv4 with port: 192.168.1.1:8080 or bare IP
    return client_ip.split(":")[0] if ":" in client_ip else client_ip


def ip_allowed(client_ip: str, allowed_ips: List[str]) -> bool:
    """Check if client_ip matches any CIDR or exact IP in allowed_ips."""
    try:
        client = ipaddress.ip_address(extract_ip(client_ip))
        for allowed in allowed_ips:
            allowed = allowed.strip()
            if not allowed:
                continue
            try:
                if "/" in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if client in network:
                        return True
                else:
                    if client == ipaddress.ip_address(allowed):
                        return True
            except ValueError:
                continue
    except ValueError:
        pass
    return False


def ip_blocked(client_ip: str, ip_list: List[str]) -> bool:
    """Check if client_ip matches any CIDR or exact IP in ip_list."""
    try:
        client = ipaddress.ip_address(extract_ip(client_ip))
        for blocked in ip_list:
            blocked = blocked.strip()
            if not blocked:
                continue
            try:
                if "/" in blocked:
                    network = ipaddress.ip_network(blocked, strict=False)
                    if client in network:
                        return True
                else:
                    if client == ipaddress.ip_address(blocked):
                        return True
            except ValueError:
                continue
    except ValueError:
        pass
    return False
