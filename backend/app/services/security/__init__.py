"""SSRF and URL safety utilities."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse


def is_safe_scheme(url: str) -> bool:
    return urlparse(url).scheme in ("http", "https")


async def is_loopback_url(url: str) -> bool:
    hostname = urlparse(url).hostname
    if not hostname:
        return True
    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo, hostname, None, socket.AF_INET
        )
    except socket.gaierror:
        return True
    return any(
        ipaddress.ip_address(info[4][0]).is_private
        or ipaddress.ip_address(info[4][0]).is_loopback
        or ipaddress.ip_address(info[4][0]).is_link_local
        or ipaddress.ip_address(info[4][0]).is_reserved
        for info in infos
    )


ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def is_allowed_upload(filename: str, size: int) -> tuple[bool, str]:
    from pathlib import Path

    ext = Path(filename).suffix.lower()
    allowed_list = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        return False, f"File type '{ext}' is not supported. Allowed: {allowed_list}"
    if size > MAX_UPLOAD_SIZE_BYTES:
        return False, (
            f"File size {size} bytes exceeds the {MAX_UPLOAD_SIZE_BYTES} byte limit."
        )
    return True, ""
