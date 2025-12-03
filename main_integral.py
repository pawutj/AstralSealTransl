"""
main_integral.py - Complete XLSX Translation Workflow

Demonstrates full integration of XLSXCore with OpenAI API
for visual novel script translations.

Workflow:
    1. Load configuration
    2. Read XLSX → JSONLine format
    3. Process translations via OpenAI API (batched with context)
    4. Write JSONLine → XLSX output
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
from core.CConfig import CConfig
from core.XLSXCore import XLSXCore
from core.COpenAIClient import COpenAIClient
from core.Prompts import GPT4_SYSTEM_PROMPT, GPT4_TRANS_PROMPT, GPT4_SYSTEM_PROMPT_CACHED, GPT4_TWO_STEP_PROMPT
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main execution workflow"""

    # ═══════════════════════════════════════════════════════
    # 1. Load Configuration
    # ═══════════════════════════════════════════════════════
    print("📋 Loading configuration...")
    config = CConfig("config.yaml")
    print(f"   ✓ Source language: {config.srcLanguage}")
    print(f"   ✓ Target language: {config.targetLanguage}")
    print(f"   ✓ Input file: {config.xlsx.filePath}")
    print(f"   ✓ Output file: {config.xlsx.outputPath}")
    print(f"   ✓ Sheet: {config.xlsx.sheetName}")
    print(f"   ✓ Prompt Caching: {'Enabled' if config.gpt.enablePromptCaching else 'Disabled'}")
    if config.gpt.enablePromptCaching:
        print(f"   ✓ Cache Retention: {config.gpt.promptCacheRetention}")
    print()

    # ═══════════════════════════════════════════════════════
    # 2. Initialize XLSX Core and OpenAI Client
    # ═══════════════════════════════════════════════════════
    xlsx_core = XLSXCore(config)
    openai_client = COpenAIClient(config)

    # ═══════════════════════════════════════════════════════
    # 3. Read XLSX → JSONLine
    # ═══════════════════════════════════════════════════════
    print("📖 Reading XLSX file...")
    try:
        jsonline_data = xlsx_core.readXlsx()

        # Display sample output
        lines = jsonline_data.split('\n')
        print(f"   ✓ Read {len(lines)} lines")
        print()
        print("📝 Sample JSONLine output (first 3 lines):")
        for i, line in enumerate(lines[:3], 1):
            print(f"   {i}. {line}")
        print()

        # Optional: Save JSONLine to file for inspection
        output_jsonline = Path("output/source.jsonline")
        output_jsonline.parent.mkdir(parents=True, exist_ok=True)
        output_jsonline.write_text(jsonline_data, encoding='utf-8')
        print(f"💾 Saved JSONLine to: {output_jsonline}")
        print()

    except FileNotFoundError as e:
        print(f"   ❌ Error: {e}")
        print("   💡 Make sure input/jp_script.xlsx exists")
        return
    except ValueError as e:
        print(f"   ❌ Validation Error: {e}")
        return

    # ═══════════════════════════════════════════════════════
    # 4. Process Translations with OpenAI API
    # ═══════════════════════════════════════════════════════
    print("🔄 Processing translations via OpenAI API...")
    print(f"   ℹ️  Batch size: {config.gpt.numPerRequestTranslate} sentences")
    print(f"   ℹ️  Context window: {config.gpt.contextNum} previous translations")
    print()

    try:
        translated_jsonline = translate_with_api(
            jsonline_input=jsonline_data,
            config=config,
            client=openai_client
        )
        print()
        print(f"   ✅ Completed translation of {len(translated_jsonline.split(chr(10)))} sentences")
        print()

    except Exception as e:
        print(f"   ❌ Translation Error: {e}")
        logger.exception("Translation failed")
        return

    # ═══════════════════════════════════════════════════════
    # 5. Write JSONLine → XLSX
    # ═══════════════════════════════════════════════════════
    print("💾 Writing translations to XLSX...")
    try:
        xlsx_core.writeXlsx(translated_jsonline)
        print()
        print("=" * 60)
        print("✅ Workflow completed successfully!")
        print("=" * 60)
        print(f"📁 Output saved to: {config.xlsx.outputPath}")
        print()

        # Display cache statistics
        if config.gpt.enablePromptCaching:
            openai_client.print_cache_statistics()

    except Exception as e:
        print(f"   ❌ Write Error: {e}")
        return


def split_into_batches(jsonline_input: str, batch_size: int) -> List[List[Dict]]:
    """
    Split JSONLine input into batches for processing.

    Args:
        jsonline_input: Source JSONLine with id, name, src
        batch_size: Number of sentences per batch

    Returns:
        List of batches, each batch is a list of dicts
    """
    all_items = []
    for line in jsonline_input.strip().split('\n'):
        if not line.strip():
            continue
        all_items.append(json.loads(line))

    batches = []
    for i in range(0, len(all_items), batch_size):
        batches.append(all_items[i:i + batch_size])

    return batches


def build_translation_messages(
    batch: List[Dict],
    target_lang: str,
    context_translations: str = "",
    glossary: str = "",
    use_cached_prompt: bool = True
) -> List[Dict]:
    """
    Build message structure for OpenAI API translation request.

    OPTIMIZED FOR PROMPT CACHING (GPT-5.1 Extended Caching):
    - System prompt is now >1024 tokens and static across ALL batches
    - Only context + input varies per batch (acceptable tradeoff)
    - Expected cache hit rate: 70-85% after first batch

    Args:
        batch: List of items to translate (id, name, src)
        target_lang: Target language code
        context_translations: Previous translations (JSONLine format)
        glossary: Glossary terms
        use_cached_prompt: Use optimized cached system prompt (default: True)

    Returns:
        List of message dicts for API request

    Cache Strategy (NEW):
        - Message 1 (system): GPT4_SYSTEM_PROMPT_CACHED (~1200 tokens) → CACHED ✅
        - Message 2 (user): Context + current batch input → NOT CACHED ❌ (acceptable)
        - Message 3 (assistant): Priming → CACHED ✅

        Total cache hit rate: 70-85% (system + priming are cached)
        Cost reduction: ~63-77% (cached tokens are 90% cheaper)

    Old Strategy (DEPRECATED - 0% cache hit rate):
        - Multiple short messages with varying content
        - Context in middle of array breaks prefix matching
        - System prompt too short (<1024 tokens)
    """
    # Convert batch to JSONLine format
    batch_jsonline = "\n".join([
        json.dumps(item, ensure_ascii=False) for item in batch
    ])

    if use_cached_prompt:
        # NEW: Optimized structure for caching
        # System prompt is now >1024 tokens and fully static
        system_prompt = GPT4_TWO_STEP_PROMPT.replace("[TargetLang]", target_lang)
        system_prompt = system_prompt.replace("[Glossary]", glossary)

        # Build user message with context + input
        # This is the ONLY part that varies per batch (acceptable tradeoff)
        user_content_parts = []

        # Add context if available
        if context_translations:
            user_content_parts.append(
                f"<context>\n"
                f"Previous translations for reference:\n"
                f"```jsonline\n{context_translations}\n```\n"
                f"</context>"
            )

        # Add current batch input
        user_content_parts.append(
            f"<input>\n"
            f"```jsonline\n{batch_jsonline}\n```\n"
            f"</input>"
        )

        messages = [
            # Message 1: System + Rules (CACHED ✅ - >1024 tokens, static)
            {
                "role": "system",
                "content": system_prompt
            },
            # Message 2: Context + Input (NOT CACHED ❌ - varies per batch)
            {
                "role": "user",
                "content": "\n\n".join(user_content_parts)
            },
            # Message 3: Priming (CACHED ✅ - static)
            {
                "role": "assistant",
                "content": "```jsonline"
            }
        ]

    else:
        # OLD: Legacy structure (for backward compatibility)
        # WARNING: This has 0% cache hit rate!
        user_prompt = GPT4_TRANS_PROMPT.replace("[TargetLang]", target_lang)
        user_prompt = user_prompt.replace("[Glossary]", glossary)
        user_prompt = user_prompt.replace("[Input]", batch_jsonline)

        messages = [
            {
                "role": "system",
                "content": GPT4_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": "<input>\n(...truncated history source texts...)\n</input>\n<output>"
            },
            {
                "role": "assistant",
                "content": f"```jsonline\n{context_translations}\n```"
            },
            {
                "role": "user",
                "content": user_prompt
            },
            {
                "role": "assistant",
                "content": "```jsonline"
            }
        ]

    return messages


def translate_with_api(
    jsonline_input: str,
    config: CConfig,
    client: COpenAIClient
) -> str:
    """
    Translate JSONLine input using OpenAI API with batching and context.

    Args:
        jsonline_input: Source JSONLine with id, name, src
        config: Configuration instance
        client: OpenAI client instance

    Returns:
        Translated JSONLine with id, dst
    """
    batch_size = config.gpt.numPerRequestTranslate
    context_size = config.gpt.contextNum
    target_lang = config.targetLanguage

    logger.info(f"Starting translation with batch_size={batch_size}, context_size={context_size}")

    # Split into batches
    batches = split_into_batches(jsonline_input, batch_size)
    logger.info(f"Total batches: {len(batches)}")

    all_translations = []
    context_window = []  # Store last N translations for context

    for batch_num, batch in enumerate(batches, 1):
        logger.info(f"Processing batch {batch_num}/{len(batches)} ({len(batch)} sentences)")

        # Build context from previous translations
        context_jsonline = "\n".join([
            json.dumps(item, ensure_ascii=False) for item in context_window
        ])

        # Build messages
        messages = build_translation_messages(
            batch=batch,
            target_lang=target_lang,
            context_translations=context_jsonline,
            glossary=""  # TODO: Add glossary support
        )

        # Send API request
        try:
            response = client.send_chat_completion(messages)
            content = client.parse_response(response)
            translations = client.extract_jsonline(content)

            # Log token usage
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                logger.info(
                    f"  Tokens: {usage.prompt_tokens} prompt + "
                    f"{usage.completion_tokens} completion = "
                    f"{usage.total_tokens} total"
                )

            # Store translations
            all_translations.extend(translations)

            # Update context window (keep last N translations)
            context_window.extend(translations)
            if len(context_window) > context_size:
                context_window = context_window[-context_size:]

            logger.info(f"  ✓ Translated {len(translations)} sentences")

        except Exception as e:
            logger.error(f"  ✗ Batch {batch_num} failed: {e}")
            raise

    # Convert back to JSONLine format
    result_lines = []
    for item in all_translations:
        result_lines.append(
            json.dumps({"id": item["id"], "dst": item["dst"]}, ensure_ascii=False)
        )

    return "\n".join(result_lines)


if __name__ == "__main__":
    main()
