"""Kept so existing deployments keep working – the portal now lives in client_portal.py."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("client_portal.py")), run_name="__main__")
