# AstralSealTransl

Automated translation solution for visual novels supporting GPT-4 and OpenAI-compatible APIs.

## Features

- 🌍 **Multi-language Support**: Translate from any language to any language
- 📊 **Multiple File Formats**: XLSX, JSON, TXT, CSV support
- 🧠 **Context-Aware Translation**: Maintains 8-sentence context window for consistency
- 📦 **Batch Processing**: Efficient API usage with configurable batch sizes
- 📚 **Glossary System**: Preserve character names and custom terminology
- 🎯 **Visual Novel Optimized**: Special handling for dialogue, narration, and formatting
- ⚡ **Streaming Support**: Real-time translation output
- ✅ **Quality Assurance**: Optional proofreading pass for enhanced accuracy

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/AstralSealTransl.git
cd AstralSealTransl
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your settings:
```bash
cp config.example.yaml config.yaml
# Edit config.yaml with your API key and preferences
```

## Configuration

Edit `config.yaml` to configure your translation settings:

```yaml
backendSpecific:
  OpenAI-Compatible:
    tokens:
      - token: YOUR_API_KEY
        endpoint: https://api.openai.com/v1/chat/completions
        modelName: gpt-4-turbo-2024-04-09
        stream: true

common:
  language: "th"  # Target language (ISO 639-1 code)
  gpt:
    numPerRequestTranslate: 10  # Sentences per batch
    contextNum: 8               # Context window size
    temperature: 0.3            # Translation creativity (0.0-2.0)
    frequency_penalty: 0.2      # Reduce repetition (0.0-2.0)
  inputPath: "/input"
  inputType: "xlsx"
```

### Using CConfig Class

```python
from core import CConfig

# Load configuration
config = CConfig("config.yaml")

# Access settings
print(f"Target language: {config.language}")
print(f"Batch size: {config.gpt.numPerRequestTranslate}")

# Get primary API token
token = config.get_primary_token()
print(f"Model: {token.modelName}")
print(f"Endpoint: {token.endpoint}")

# Reload configuration
config.reload()
```

## Usage

### Basic Translation

```python
from core import CConfig
# Translation workflow will be implemented here
```

### Running Tests

```bash
python test_config.py
```

## Project Structure

```
AstralSealTransl/
├── config.yaml              # Your configuration (not in git)
├── config.example.yaml      # Example configuration
├── requirements.txt         # Python dependencies
├── core/
│   ├── __init__.py         # Core module exports
│   ├── CConfig.py          # Configuration manager
│   └── Prompts.py          # Translation prompts
├── input/                   # Input files directory
├── output/                  # Translated output
├── CLAUDE.md               # Claude Code instructions
└── README.md               # This file
```

## Translation Pipeline

```
Input File (XLSX)
    ↓
Parse sentences
    ↓
Create batches (10 sentences)
    ↓
Add context (8 previous sentences)
    ↓
Send to OpenAI API
    ↓
Parse JSONLine response
    ↓
(Optional) Proofreading pass
    ↓
Save translated file
```

## API Cost Estimation

Using GPT-4 Turbo as example:
- **Prompt**: ~1,247 tokens × $0.01/1K = $0.01247
- **Completion**: ~312 tokens × $0.03/1K = $0.00936
- **Total**: ~$0.022 per 10 sentences

For a typical visual novel with 10,000 sentences:
- Total batches: 1,000
- Estimated cost: $22-25

## Language Support

Supported target languages (use ISO 639-1 codes):
- `en` - English
- `th` - Thai
- `zh` - Chinese (Simplified: zh-Hans, Traditional: zh-Hant)
- `ja` - Japanese
- `ko` - Korean
- `es` - Spanish
- `fr` - French
- `de` - German
- And more...

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Your License Here]

## Acknowledgments

- Built with OpenAI GPT-4 API
- Inspired by visual novel translation community
