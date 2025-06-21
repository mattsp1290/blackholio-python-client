"""
Setup script for blackholio-client package.

This file provides backward compatibility for older pip versions
and tools that don't support pyproject.toml yet.

All package configuration is defined in pyproject.toml following
modern Python packaging standards (PEP 517/518).
"""

from setuptools import setup

# All configuration is in pyproject.toml
# This file exists for backward compatibility with older pip versions
# and tools that don't fully support pyproject.toml-only packages yet
setup()
