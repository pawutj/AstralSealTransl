"""
Configuration Manager for AstralSealTransl

This module provides CConfig class for loading and managing
configuration from config.yaml file.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TokenConfig:
    """Configuration for a single API token/endpoint"""
    token: str
    endpoint: str
    modelName: str
    stream: bool = True


@dataclass
class GPTConfig:
    """GPT-specific translation settings"""
    numPerRequestTranslate: int = 10
    contextNum: int = 8
    temperature: float = 0.3
    frequency_penalty: float = 0.2

    # Prompt Caching settings (GPT-5.1 Extended Caching)
    enablePromptCaching: bool = True
    promptCacheRetention: str = "24h"  # "5m", "1h", "24h"


@dataclass
class XLSXConfig:
    """XLSX file processing settings"""
    filePath: str = "input/jp_script.xlsx"
    outputPath: str = "output/translated.xlsx"
    nameColumn: str = "who_talk"
    srcColumn: str = "talk"
    targetColumn: str = "talk_jp"
    targetColumn2: Optional[str] = None  # Second target column for dual-target mode
    sheetName: str = "Sheet1"
    validateColumns: bool = True

    def has_dual_target(self) -> bool:
        """Check if dual-target mode is enabled"""
        return self.targetColumn2 is not None


class CConfig:
    """
    Configuration manager for AstralSealTransl project.

    Loads and provides access to all configuration parameters
    from config.yaml file.

    Usage:
        config = CConfig("config.yaml")
        print(config.language)  # "th"
        print(config.tokens[0].modelName)  # "gpt-5-nano"
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration from YAML file.

        Args:
            config_path: Path to config.yaml file (default: "config.yaml")

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is malformed
            ValueError: If required fields are missing
        """
        self.config_path = Path(config_path)
        self._raw_config: Dict[str, Any] = {}

        # Backend-specific settings
        self.tokens: List[TokenConfig] = []

        # Common settings
        self.srcLanguage: str = "en"      # Source language
        self.targetLanguage: str = "en"   # Target language
        self.language: str = "en"         # Deprecated: use targetLanguage
        self.gpt: GPTConfig = GPTConfig()
        self.workersPerProject: int = 1
        self.inputPath: str = "/input"
        self.inputType: str = "xlsx"

        # XLSX-specific settings
        self.xlsx: XLSXConfig = XLSXConfig()

        # Load configuration
        self._load()

    def _load(self) -> None:
        """Load and parse configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._raw_config = yaml.safe_load(f)

        if not self._raw_config:
            raise ValueError("Config file is empty")

        # Parse backend-specific settings
        self._parse_backend_specific()

        # Parse common settings
        self._parse_common()

        # Parse XLSX settings
        self._parse_xlsx()

        # Validate configuration
        self._validate()

    def _parse_backend_specific(self) -> None:
        """Parse backendSpecific section"""
        backend = self._raw_config.get('backendSpecific', {})
        openai_config = backend.get('OpenAI-Compatible', {})
        tokens_list = openai_config.get('tokens', [])

        self.tokens = []
        for token_data in tokens_list:
            self.tokens.append(TokenConfig(
                token=token_data.get('token', ''),
                endpoint=token_data.get('endpoint', ''),
                modelName=token_data.get('modelName', 'gpt-4'),
                stream=token_data.get('stream', True)
            ))

    def _parse_common(self) -> None:
        """Parse common section"""
        common = self._raw_config.get('common', {})

        # Language settings
        self.srcLanguage = common.get('srcLanguage', 'en')
        self.targetLanguage = common.get('targetLanguage', 'en')
        # Backward compatibility: language defaults to targetLanguage
        self.language = common.get('language', self.targetLanguage)

        # GPT settings
        gpt_config = common.get('gpt', {})
        self.gpt = GPTConfig(
            numPerRequestTranslate=gpt_config.get('numPerRequestTranslate', 10),
            contextNum=gpt_config.get('contextNum', 8),
            temperature=gpt_config.get('temperature', 0.3),
            frequency_penalty=gpt_config.get('frequency_penalty', 0.2),
            enablePromptCaching=gpt_config.get('enablePromptCaching', True),
            promptCacheRetention=gpt_config.get('promptCacheRetention', '24h')
        )

        # Other common settings
        self.workersPerProject = common.get('workersPerProject', 1)
        self.inputPath = common.get('inputPath', '/input')
        self.inputType = common.get('inputType', 'xlsx')

    def _parse_xlsx(self) -> None:
        """Parse xlsx section"""
        xlsx_config = self._raw_config.get('xlsx', {})

        self.xlsx = XLSXConfig(
            filePath=xlsx_config.get('filePath', 'input/jp_script.xlsx'),
            outputPath=xlsx_config.get('outputPath', 'output/translated.xlsx'),
            nameColumn=xlsx_config.get('nameColumn', 'who_talk'),
            srcColumn=xlsx_config.get('srcColumn', 'talk'),
            targetColumn=xlsx_config.get('targetColumn', 'talk_jp'),
            targetColumn2=xlsx_config.get('targetColumn2'),  # Optional: dual-target mode
            sheetName=xlsx_config.get('sheetName', 'Sheet1'),
            validateColumns=xlsx_config.get('validateColumns', True)
        )

    def _validate(self) -> None:
        """Validate configuration values"""
        errors = []

        # Validate tokens
        if not self.tokens:
            errors.append("No API tokens configured")

        for i, token in enumerate(self.tokens):
            if not token.token:
                errors.append(f"Token #{i}: token is empty")
            if not token.endpoint:
                errors.append(f"Token #{i}: endpoint is empty")
            if not token.modelName:
                errors.append(f"Token #{i}: modelName is empty")

        # Validate GPT settings
        if self.gpt.numPerRequestTranslate <= 0:
            errors.append("numPerRequestTranslate must be positive")
        if self.gpt.contextNum < 0:
            errors.append("contextNum must be non-negative")
        if not (0.0 <= self.gpt.temperature <= 2.0):
            errors.append("temperature must be between 0.0 and 2.0")
        if not (0.0 <= self.gpt.frequency_penalty <= 2.0):
            errors.append("frequency_penalty must be between 0.0 and 2.0")

        # Validate common settings
        if not self.srcLanguage:
            errors.append("srcLanguage is required")
        if not self.targetLanguage:
            errors.append("targetLanguage is required")
        if self.workersPerProject <= 0:
            errors.append("workersPerProject must be positive")
        if not self.inputPath:
            errors.append("inputPath is required")
        if not self.inputType:
            errors.append("inputType is required")

        # Validate XLSX settings
        if not self.xlsx.filePath:
            errors.append("xlsx.filePath is required")
        if not self.xlsx.outputPath:
            errors.append("xlsx.outputPath is required")
        if not self.xlsx.nameColumn:
            errors.append("xlsx.nameColumn is required")
        if not self.xlsx.srcColumn:
            errors.append("xlsx.srcColumn is required")
        if not self.xlsx.targetColumn:
            errors.append("xlsx.targetColumn is required")
        if not self.xlsx.sheetName:
            errors.append("xlsx.sheetName is required")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    def get_primary_token(self) -> TokenConfig:
        """
        Get the first (primary) token configuration.

        Returns:
            TokenConfig: Primary token configuration

        Raises:
            IndexError: If no tokens configured
        """
        if not self.tokens:
            raise IndexError("No tokens configured")
        return self.tokens[0]

    def reload(self) -> None:
        """Reload configuration from file"""
        self._load()

    def to_dict(self) -> Dict[str, Any]:
        """
        Export configuration as dictionary.

        Returns:
            Dict: Configuration as nested dictionary
        """
        return {
            'backendSpecific': {
                'OpenAI-Compatible': {
                    'tokens': [
                        {
                            'token': t.token,
                            'endpoint': t.endpoint,
                            'modelName': t.modelName,
                            'stream': t.stream
                        }
                        for t in self.tokens
                    ]
                }
            },
            'common': {
                'srcLanguage': self.srcLanguage,
                'targetLanguage': self.targetLanguage,
                'gpt': {
                    'numPerRequestTranslate': self.gpt.numPerRequestTranslate,
                    'contextNum': self.gpt.contextNum,
                    'temperature': self.gpt.temperature,
                    'frequency_penalty': self.gpt.frequency_penalty,
                    'enablePromptCaching': self.gpt.enablePromptCaching,
                    'promptCacheRetention': self.gpt.promptCacheRetention
                },
                'workersPerProject': self.workersPerProject,
                'inputPath': self.inputPath,
                'inputType': self.inputType
            },
            'xlsx': {
                'filePath': self.xlsx.filePath,
                'outputPath': self.xlsx.outputPath,
                'nameColumn': self.xlsx.nameColumn,
                'srcColumn': self.xlsx.srcColumn,
                'targetColumn': self.xlsx.targetColumn,
                'targetColumn2': self.xlsx.targetColumn2,
                'sheetName': self.xlsx.sheetName,
                'validateColumns': self.xlsx.validateColumns
            }
        }

    def __repr__(self) -> str:
        """String representation of configuration"""
        return (
            f"CConfig(\n"
            f"  srcLanguage='{self.srcLanguage}',\n"
            f"  targetLanguage='{self.targetLanguage}',\n"
            f"  tokens={len(self.tokens)},\n"
            f"  inputType='{self.inputType}',\n"
            f"  batchSize={self.gpt.numPerRequestTranslate},\n"
            f"  contextWindow={self.gpt.contextNum}\n"
            f")"
        )


# Example usage
if __name__ == "__main__":
    try:
        config = CConfig("../config.yaml")
        print("Configuration loaded successfully!")
        print(config)
        print(f"\nSource language: {config.srcLanguage}")
        print(f"Target language: {config.targetLanguage}")
        print(f"Model: {config.get_primary_token().modelName}")
        print(f"Batch size: {config.gpt.numPerRequestTranslate}")
        print(f"Context window: {config.gpt.contextNum}")

    except Exception as e:
        print(f"Error loading configuration: {e}")
