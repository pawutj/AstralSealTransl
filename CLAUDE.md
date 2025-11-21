# AstralSealTransl - Visual Novel Translation Project

## Project Overview

**AstralSealTransl** is an automated visual novel translation tool that leverages OpenAI-compatible APIs (ChatGPT/GPT-4) to translate visual novel scripts from any language to any language while maintaining context, character consistency, and emotional nuance.

### Core Capabilities
- **Multi-format Support**: XLSX and other structured formats
- **Context-Aware Translation**: Maintains 8-sentence context window for consistency
- **Batch Processing**: Processes 10 sentences per API request for efficiency
- **Glossary System**: Supports character names, terminology, and custom translations
- **Streaming Support**: Real-time translation output
- **Proofreading Mode**: Secondary pass for quality assurance
- **JSONLine Format**: Structured input/output with id, name, src/dst fields

---

## Project Structure

```
AstralSealTransl/
├── config.yaml              # Configuration: API settings, language, batch size
├── core/
│   └── Prompts.py          # Translation & proofreading prompt templates
├── input-output.md         # API request/response examples
└── README.md               # Project description
```

---

## Technical Architecture

### Translation Pipeline

```
Input (XLSX) → Parser → Batch Creator (10 sentences)
                              ↓
                    Context Window (8 previous)
                              ↓
                    OpenAI API (with glossary)
                              ↓
                    JSONLine Response Parser
                              ↓
                    (Optional) Proofreading Pass
                              ↓
                    Output (Translated XLSX)
```

### Key Components

#### 1. **config.yaml**
- **Backend**: OpenAI-compatible endpoint configuration
  - API tokens and endpoints
  - Model selection (e.g., gpt-4-turbo, gpt-5-nano)
  - Streaming mode
- **Translation Settings**:
  - Target language (`language: "th"` for Thai)
  - Batch size (`numPerRequestTranslate: 10`)
  - Context window (`contextNum: 8`)
  - Input format (`inputType: "xlsx"`)

#### 2. **core/Prompts.py**
- **GPT4_SYSTEM_PROMPT**: Base translator personality
- **GPT4_TRANS_PROMPT**: Main translation instructions
  - Handles dialogue vs. narration
  - Preserves formatting and special characters
  - Applies glossary terms
  - Maintains emotional tone
- **GPT4_PROOFREAD_PROMPT**: Quality assurance pass
  - Checks completeness, correctness, fluency
  - Corrects pronouns, logic, wording

#### 3. **JSONLine Format**
```json
{"id": 1, "name": "Character", "src": "Source text"}
{"id": 2, "dst": "Translated text"}
```
- `id`: Sequential sentence identifier
- `name`: (Optional) Character name for dialogue
- `src`: Source language text
- `dst`: Destination language translation

---

## Claude Code Instructions

### When Working on This Project

#### Understanding Context
- **Visual Novel Domain**: Text is from interactive story games with:
  - Character dialogue (has `name` field)
  - Narration/monologue (no `name` field)
  - Special formatting: `<br>` (line breaks), `『』` (quotes), etc.
- **ACGN Culture**: Anime, Comics, Games, Novels - requires cultural localization
- **Emotional Fidelity**: Humor, sadness, tension must translate accurately

#### Code Patterns
1. **Prompt Engineering**:
   - Prompts use XML-like tags: `<ciallo_info>`, `<translation_requirements>`
   - Placeholders: `[TargetLang]`, `[Glossary]`, `[Input]`
   - Template variables must be replaced at runtime

2. **API Integration**:
   - Uses standard OpenAI Chat Completion format
   - Messages: system → user → assistant (context) → user (new batch) → assistant
   - Response parsing: Extract JSONLine from markdown code block

3. **Context Management**:
   - Rolling window: Keep last 8 translations from previous batch
   - Ensures character consistency and pronoun accuracy
   - Example: "彼女" (she) correctly refers to character from context

#### Best Practices

**✅ DO:**
- Preserve all special characters and formatting in prompts
- Test translations with both dialogue and narration samples
- Validate JSONLine parsing (handle malformed responses)
- Implement token counting for cost estimation
- Support multiple target languages (not just Chinese)
- Add error handling for API failures and retries
- Log translation quality metrics (token usage, time)

**❌ DON'T:**
- Remove or modify the XML-like prompt structure
- Skip the context window (breaks consistency)
- Ignore glossary terms (character names must be consistent)
- Hard-code language-specific logic (keep it configurable)
- Over-engineer: Keep prompts readable and maintainable

#### Security & Ethics
- **API Keys**: Never commit tokens to version control
- **Content Warning**: Visual novels may contain mature themes
- **Disclaimer**: System includes disclaimer about translation responsibility
- **Rate Limiting**: Implement backoff for API quota limits

---

## Development Workflow

### Adding New Features

#### 1. **Support New File Formats**
```yaml
Goal: Add .txt, .json, .csv support
Steps:
  1. Create parser in core/parsers/
  2. Update config.yaml with inputType options
  3. Implement common interface: parse() → List[Dict]
  4. Add format detection logic
```

#### 2. **Multi-Language Support**
```yaml
Goal: Support Thai, Spanish, French, etc.
Steps:
  1. Update language codes in config.yaml
  2. Test prompt with target language examples
  3. Adjust glossary format if needed
  4. Validate output encoding
```

#### 3. **Quality Improvements**
```yaml
Goal: Enhance translation accuracy
Steps:
  1. Analyze failed translations (save examples)
  2. Refine prompt instructions
  3. Adjust temperature/frequency_penalty
  4. A/B test prompt variations
  5. Implement proofreading mode
```

### Testing Guidelines

**Unit Tests**:
- Prompt template variable replacement
- JSONLine parsing (valid/invalid cases)
- Context window management
- Glossary application

**Integration Tests**:
- End-to-end translation (sample script)
- API error handling (timeout, rate limit)
- Multi-batch continuity
- Special character preservation

**Manual QA**:
- Emotional tone (humor, sadness, tension)
- Character consistency across batches
- Formatting preservation
- Cultural appropriateness

---

## Prompt Engineering Guidelines

### Modifying Translation Prompts

#### Structure Principles
1. **Clear Sections**: Use XML-like tags for organization
2. **Explicit Instructions**: No ambiguity in requirements
3. **Examples**: Show input/output patterns
4. **Constraints**: Specify what NOT to do

#### Translation Requirements
- **Dialogue vs. Narration**: Different handling rules
- **Onomatopoeia**: Convert to target language equivalents
- **Pronouns**: Infer from context (especially for languages without explicit subjects)
- **Emotional Tone**: Preserve humor, sadness, tension
- **Formatting**: Keep system symbols, spacing, line breaks

#### Output Format Enforcement
- **Priming**: Last assistant message starts with `"```jsonline"`
- **Schema**: Strictly enforce `{"id": int, "name"?: string, "dst": string}`
- **No Explanation**: Model should not add notes or commentary

### Glossary Best Practices
```
Format: SourceTerm\tTranslation\tContext/Notes
Example: フラン\tFlan\tname, lady, teacher
```
- Keep translations consistent across batches
- Include character names, places, special terms
- Add context (honorifics, gender, relationships)

---

## Configuration Reference

### config.yaml Structure

```yaml
backendSpecific:
  OpenAI-Compatible:
    tokens:
      - token: <API_KEY>          # OpenAI API key or compatible
        endpoint: <API_URL>       # API endpoint
        modelName: <MODEL>        # e.g., gpt-4-turbo-2024-04-09
        stream: true              # Enable streaming responses

common:
  language: "th"                  # Target language code (ISO 639-1)
  gpt:
    numPerRequestTranslate: 10    # Sentences per batch
    contextNum: 8                 # Previous sentences as context
    temperature: 0.3              # Creativity (0.0-1.0)
    frequency_penalty: 0.2        # Reduce repetition
  workersPerProject: 1            # Parallel workers (future)
  inputPath: "/input"             # Input directory
  inputType: "xlsx"               # Input format
```

### Recommended Settings

| Parameter | Recommended | Rationale |
|-----------|-------------|-----------|
| numPerRequestTranslate | 10 | Balance between context and cost |
| contextNum | 8 | Sufficient for character/pronoun consistency |
| temperature | 0.3 | Low creativity for accurate translation |
| frequency_penalty | 0.2 | Prevent repetitive phrasing |
| stream | true | Real-time feedback for long scripts |

---

## Common Tasks

### Task: Analyze Translation Quality
```bash
# Use Claude Code to analyze input-output.md examples
/analyze input-output.md --focus quality
```

### Task: Add New Language Support
```yaml
Steps:
  1. Update config.yaml language code
  2. Test prompt with sample text
  3. Verify output encoding
  4. Update glossary format if needed
```

### Task: Debug API Errors
```bash
# Check API response structure
/troubleshoot "API returning unexpected format"
# Examine error patterns in logs
/analyze logs/ --focus errors
```

### Task: Improve Prompt Effectiveness
```bash
# Analyze current prompts
/explain core/Prompts.py
# Suggest improvements
/improve core/Prompts.py --focus clarity
```

### Task: Implement New File Format Parser
```bash
# Design parser architecture
/design "Add .txt file format support"
# Implement with existing patterns
/implement --type service --framework python
```

---

## Personas & MCP Integration

### Recommended Personas

#### For Translation Work
- **scribe**: Documentation and localization expert (use `--persona-scribe=th` for Thai)
  - Understands cultural nuances
  - Maintains consistent terminology
  - Focuses on readability

#### For Development
- **backend**: API integration and data processing
  - OpenAI API integration
  - Batch processing logic
  - Error handling and retries

- **analyzer**: Quality assurance and debugging
  - Translation accuracy analysis
  - Error pattern detection
  - Performance optimization

### MCP Server Usage

#### Context7
- **Use For**: Researching translation best practices, API documentation
- **Activation**: `--c7` or automatic when researching libraries
- **Example**: "How to handle streaming responses in OpenAI API?"

#### Sequential
- **Use For**: Complex translation logic, multi-step processing
- **Activation**: `--seq` or automatic with `--think`
- **Example**: Debugging context window management

---

## Performance Optimization

### Token Efficiency
- **Batch Size**: 10 sentences balances API calls vs. context length
- **Context Window**: 8 sentences is sufficient without excessive tokens
- **Prompt Length**: ~1,200-1,500 tokens per request (with context)
- **Completion Length**: ~300-400 tokens per response

### Cost Estimation
```
Cost per batch = (prompt_tokens + completion_tokens) × model_rate
Example (GPT-4 Turbo):
  - Prompt: 1,247 tokens × $0.01/1K = $0.01247
  - Completion: 312 tokens × $0.03/1K = $0.00936
  - Total: ~$0.022 per 10 sentences
```

### Optimization Strategies
1. **Cache glossaries**: Don't re-send static terms every request
2. **Batch efficiently**: 10 sentences is optimal (tested)
3. **Compress context**: Use `--uc` for token reduction if needed
4. **Parallelize**: Future feature - multiple workers for large scripts

---

## Troubleshooting

### Issue: Inconsistent Character Names
**Symptom**: "Flan" becomes "弗兰" then "芙兰"
**Solution**:
- Verify glossary is included in every request
- Check context window includes previous usages
- Increase `contextNum` if needed

### Issue: Lost Formatting
**Symptom**: `<br>` tags or special quotes disappear
**Solution**:
- Verify prompt example shows formatting preservation
- Test with different temperature settings
- Add explicit formatting rules to prompt

### Issue: API Timeout
**Symptom**: Long scripts fail mid-translation
**Solution**:
- Implement retry logic with exponential backoff
- Reduce batch size temporarily
- Check API rate limits

### Issue: Wrong Emotional Tone
**Symptom**: Humor lost, sadness not conveyed
**Solution**:
- Add explicit examples in prompt
- Test with native speakers
- Adjust prompt to emphasize emotion preservation
- Consider proofreading pass

---

## Future Enhancements

### Planned Features
- [ ] Multiple file format support (.txt, .json, .csv)
- [ ] Web UI for non-technical users
- [ ] Translation memory/cache
- [ ] Quality metrics dashboard
- [ ] A/B testing framework for prompts
- [ ] Multi-language glossary management
- [ ] Integration with visual novel engines
- [ ] Community-contributed glossaries

### Research Areas
- Fine-tuned models for visual novel translation
- Cultural adaptation beyond literal translation
- Character voice consistency (speech patterns)
- Integration with OCR for untranslated games

---

## Resources

### Documentation
- OpenAI API: https://platform.openai.com/docs/api-reference
- Visual Novel Formats: Research game-specific script formats
- ACGN Translation: Study community translation practices

### Communities
- Visual Novel Translation Discord servers
- ACGN localization forums
- Machine translation research papers

---

## Questions for Claude Code

When working on this project, Claude Code should ask:

1. **Target Language**: "Which language are you translating to?"
2. **Input Format**: "What file format is the source script?"
3. **Glossary**: "Do you have character names or terms to preserve?"
4. **Quality vs. Speed**: "Prioritize accuracy or processing speed?"
5. **Cultural Adaptation**: "How much localization vs. literal translation?"

---

## Summary

**AstralSealTransl** is a specialized tool requiring:
- Deep understanding of visual novel format and culture
- Careful prompt engineering for context and quality
- Robust API integration with error handling
- Attention to emotional tone and character consistency

**Claude Code should**:
- Maintain prompt structure and formatting rules
- Test thoroughly with diverse script samples
- Monitor translation quality metrics
- Preserve the cultural sensitivity of visual novel localization
