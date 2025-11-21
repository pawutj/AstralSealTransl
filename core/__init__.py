"""
AstralSealTransl Core Module

This module contains core components for visual novel translation:
- CConfig: Configuration management
- COpenAIClient: OpenAI API communication layer
- Prompts: Translation and proofreading prompts
"""

from .CConfig import CConfig, TokenConfig, GPTConfig
from .COpenAIClient import COpenAIClient

__all__ = ['CConfig', 'TokenConfig', 'GPTConfig', 'COpenAIClient']
__version__ = '0.1.0'
