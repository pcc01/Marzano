"""
Shared pytest configuration and fixtures.
Tests run against the actual module code without a live server or database.
"""

import sys
import os
import pytest

# Put backend on the path so all backend modules are importable directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
