"""
AstralSealTransl Core Module

This module contains core components for visual novel translation:
- CConfig: Configuration management
- Prompts: Translation and proofreading prompts
"""

from .CConfig import CConfig, TokenConfig, GPTConfig

__all__ = ['CConfig', 'TokenConfig', 'GPTConfig']
__version__ = '0.1.0'
