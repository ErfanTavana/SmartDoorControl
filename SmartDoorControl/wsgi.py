"""Compatibility WSGI entrypoint for hosts expecting ``SmartDoorControl.wsgi``.

Delegates to ``config.wsgi`` so deployments configured with the old module path
continue to work without changes.
"""

from config.wsgi import *  # noqa: F401,F403
