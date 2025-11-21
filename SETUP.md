# Setup Instructions for main.py

## Quick Start

### 1. Update API Configuration

Edit `config.yaml` and update the following:

```yaml
backendSpecific:
  OpenAI-Compatible:
    tokens:
      - token: sk-proj-YOUR_ACTUAL_OPENAI_API_KEY_HERE  # ⚠️ Replace with real key
        endpoint: https://api.openai.com/v1  # ⚠️ Fixed endpoint
        modelName: gpt-4-turbo-2024-04-09  # or gpt-4o, gpt-3.5-turbo
        stream: false  # main.py uses sync mode
```

**Critical Updates Required:**

1. **API Token**: Replace `sk-proj` with your full OpenAI API key from https://platform.openai.com/api-keys
2. **Endpoint**: Change from `https://api.openai.com/v1/responses` to `https://api.openai.com/v1`
3. **Model Name**: Use valid OpenAI model (e.g., `gpt-4-turbo-2024-04-09`, `gpt-4o`, `gpt-3.5-turbo`)
4. **Stream**: Set to `false` (main.py uses synchronous mode)

### 2. Install Dependencies

```bash
pip install openai pyyaml
```

### 3. Run Translation Demo

```bash
python main.py
```

## Expected Output

```
2025-01-21 10:30:00 - INFO - Loading configuration from config.yaml
2025-01-21 10:30:00 - INFO - Target language: th
2025-01-21 10:30:00 - INFO - Initializing OpenAI client
2025-01-21 10:30:00 - INFO - Initialized COpenAIClient with model=gpt-4-turbo-2024-04-09
2025-01-21 10:30:00 - INFO - Built message structure: 5 messages
2025-01-21 10:30:00 - INFO - Translating 10 sentences (id 11-20) with 8-sentence context
2025-01-21 10:30:00 - INFO - Sending request to gpt-4-turbo-2024-04-09 with 5 messages
2025-01-21 10:30:03 - INFO - Received response: prompt_tokens=1,247, completion_tokens=312, total_tokens=1,559, response_time=3.21s
2025-01-21 10:30:03 - INFO - Parsing API response...
2025-01-21 10:30:03 - INFO - Extracted 10 JSONLine objects

======================================================================
TRANSLATION RESULTS
======================================================================

📊 Token Usage:
  Prompt:     1,247 tokens
  Completion: 312 tokens
  Total:      1,559 tokens
  Est. Cost:  $0.0219

📝 Translations (10 sentences):
----------------------------------------------------------------------
[11] รุ่นพี่: Flan<br>อร่อยมากเลยนะ
[12] Flan: ค่ะ!<br>มากันอีกนะคะ!
[13] เธอดูพอใจมาก
[14] รุ่นพี่: ต่อไปจะกินอะไรดี?
[15] Flan: อืม<br>พาสต้าดีมั้ยคะ!
[16] รุ่นพี่: ดีนะ
[17] ทั้งสองคนคิดแผนครั้งต่อไป
[18] Flan: ตื่นเต้นจัง!
[19] รุ่นพี่: ผมก็เหมือนกัน
[20] จากนั้นก็ถึงเวลาเรียน
======================================================================

✅ Translation completed successfully!
```

## What This Demo Does

1. **Loads Configuration**: Reads `config.yaml` for API credentials and settings
2. **Initializes Client**: Creates `COpenAIClient` with OpenAI connection
3. **Builds Context**: Uses 5-message structure from `input-output.md`:
   - System prompt (translator personality)
   - Context marker (for batch continuity)
   - Previous translations (8 sentences from Batch 1)
   - Full translation prompt (requirements + glossary + new input)
   - Priming (forces JSONLine output format)
4. **Sends Request**: Translates 10 Japanese visual novel sentences to Thai
5. **Parses Results**: Extracts JSONLine translations and displays with metrics

## Sample Data

- **Input**: 10 Japanese visual novel sentences (id 11-20)
- **Context**: 8 previous Thai translations (id 3-10)
- **Target**: Thai language
- **Glossary**: Character names (フラン→Flan, 先輩→Senior)

## Architecture

```
main.py
  ↓ Load config.yaml
  ↓ Initialize COpenAIClient (core/COpenAIClient.py)
  ↓ Build 5-message structure (core/Prompts.py templates)
  ↓ Send to OpenAI API
  ↓ Parse JSONLine response
  ↓ Display results + metrics
```

## Token Cost Estimation

Based on GPT-4 Turbo pricing:
- **Prompt**: ~1,247 tokens × $0.01/1K = $0.01247
- **Completion**: ~312 tokens × $0.03/1K = $0.00936
- **Total**: ~$0.022 per 10 sentences

## Troubleshooting

### Error: "Config file not found"
- Ensure `config.yaml` exists in project root
- Check working directory: `python main.py` must run from project root

### Error: "No API tokens configured"
- Update `token:` field in `config.yaml` with real API key
- Remove any test/placeholder keys

### Error: "401 Unauthorized"
- Verify API key is correct and active
- Check key has sufficient credits: https://platform.openai.com/usage

### Error: "404 Not Found"
- Fix endpoint to `https://api.openai.com/v1` (remove `/responses`)
- Verify model name is valid (e.g., `gpt-4-turbo-2024-04-09`)

### Error: "429 Rate Limit"
- Wait and retry (API quota exceeded)
- Check usage: https://platform.openai.com/usage
- Consider upgrading plan

## Clean Implementation Features

✅ **Pure API Layer**: `COpenAIClient` handles only API communication
✅ **No Streaming**: Synchronous batch processing for simplicity
✅ **Comprehensive Logging**: Request/response metrics and timing
✅ **Token Tracking**: Cost estimation and usage statistics
✅ **Error Handling**: Graceful failures with informative messages
✅ **Context Management**: 8-sentence rolling window for consistency
✅ **JSONLine Parsing**: Robust extraction from markdown code blocks

## Next Steps

1. Update `config.yaml` with real API credentials
2. Run `python main.py` to test translation
3. Modify sample data in `main.py` for custom tests
4. Integrate into larger translation pipeline
5. Add batch processing for full visual novel scripts
6. Implement proofreading pass (use `GPT4_PROOFREAD_PROMPT`)
