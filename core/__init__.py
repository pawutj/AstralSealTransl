"""
AstralSealTransl Core Module

This module contains core components for visual novel translation:
- CConfig: Configuration management
- COpenAIClient: OpenAI API communication layer
- Prompts: Translation and proofreading prompts
- XLSXCore: XLSX file processing engine
- RPYCore: Ren'Py translate block file processing engine
"""

from .CConfig import CConfig, TokenConfig, GPTConfig
from .COpenAIClient import COpenAIClient
from .XLSXCore import XLSXCore
from .RPYCore import RPYCore

__all__ = ['CConfig', 'TokenConfig', 'GPTConfig', 'COpenAIClient', 'XLSXCore', 'RPYCore']
__version__ = '0.1.0'
