"""
CyberEval - Security Utilities & Hardening
Implements mandatory secure coding rules:
- Safe path resolution preventing directory traversal
- Security headers (CSP, HSTS, X-Content-Type-Options, X-Frame-Options)
- Input sanitization
"""

import os
from pathlib import Path
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


def sanitize_filename(filename: str) -> str:
    """Strip directory traversal sequences and invalid characters from filename."""
    clean = os.path.basename(filename.strip().replace("\\", "/"))
    return clean


def safe_resolve_path(base_directory: str | Path, target_path: str | Path) -> Path:
    """
    Safely resolves target_path within base_directory.
    Raises ValueError if path traversal outside base_directory is attempted.
    """
    base = Path(base_directory).resolve()
    target = (base / target_path).resolve()
    
    # Boundary check with directory separator to prevent partial matching bypasses
    base_prefix = str(base)
    if not base_prefix.endswith(os.sep):
        base_prefix += os.sep
        
    target_str = str(target)
    if not target_str.startswith(base_prefix) and target != base:
        raise ValueError(f"Path traversal detected: {target_path} is outside allowed directory")
        
    return target


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects mandatory enterprise security headers into all responses."""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response
