# Copyright (c) 2026 Paul Christopher Cerda
# This source code is licensed under the Business Source License 1.1
# found in the LICENSE.md file in the root directory of this source tree.

"""
Shared pytest configuration and fixtures.
Tests run against the actual module code without a live server or database.
"""

import sys
import os
import pytest

# Put backend on the path so all backend modules are importable directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
