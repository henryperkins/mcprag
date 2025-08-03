"""
Compatibility patches for sandbox environments.
"""

from .socketpair_patch import apply_patches

__all__ = ['apply_patches']
