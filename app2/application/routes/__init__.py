# Routes package
from .main_routes import pages_bp, api_bp
from .upload_routes import upload_bp
from .branch_routes import branch_bp
from .level_routes import level_bp

__all__ = ['pages_bp', 'api_bp', 'upload_bp', 'branch_bp', 'level_bp']