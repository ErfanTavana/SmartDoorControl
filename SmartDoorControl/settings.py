"""Compatibility settings module for hosts configured with `SmartDoorControl.settings`.

This simply re-exports settings from ``config.settings`` so that legacy WSGI
configurations on platforms like PythonAnywhere can continue to import the
project settings without requiring changes to the host configuration.
"""

from config.settings import *  # noqa: F401,F403
