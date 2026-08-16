"""routes package — TeraBox standalone."""
from .terabox import terabox_bp
from .pages import pages_bp

__all__ = ["terabox_bp", "pages_bp"]
