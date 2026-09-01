"""Flask route blueprints."""

from .api import api_blueprint
from .auth import auth_blueprint
from .pages import pages_blueprint

__all__ = ["api_blueprint", "auth_blueprint", "pages_blueprint"]
