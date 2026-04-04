"""Entry point: python -m secops"""
import sys
from secops.scanner.cli import run

sys.exit(run())
