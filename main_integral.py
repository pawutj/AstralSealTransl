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
    """Main execution workflow for multi-sheet translation"""

    # ═══════════════════════════════════════════════════════
    # 1. Load Configuration
    # ═══════════════════════════════════════════════════════
    print("📋 Loading configuration...")
    config = CConfig("config.yaml")
    print(f"   ✓ Source language: {config.srcLanguage}")
    print(f"   ✓ Target language: {config.targetLanguage}")
    print(f"   ✓ Input file: {config.xlsx.filePath}")
    print(f"   ✓ Output file: {config.xlsx.outputPath}")
    print(f"   ✓ Sheets to process: {', '.join(config.xlsx.sheetName)}")
    print(f"   ✓ Prompt Caching: {'Enabled' if config.gpt.enablePromptCaching else 'Disabled'}")
    if config.gpt.enablePromptCaching:
        print(f"   ✓ Cache Retention: {config.gpt.promptCacheRetention}")
    print()

    # ═══════════════════════════════════════════════════════
    # 2. Initialize Processors (Reuse OpenAI client)
    # ═══════════════════════════════════════════════════════
    xlsx_core = XLSXCore(config)
    openai_client = COpenAIClient(config)

    # ═══════════════════════════════════════════════════════
    # 3. Validate Sheets Exist (Fail Fast)
    # ═══════════════════════════════════════════════════════
    print("🔍 Validating sheets...")
    try:
        validate_sheets_exist(config.xlsx.filePath, config.xlsx.sheetName)
        print(f"   ✅ All {len(config.xlsx.sheetName)} sheets found")
    except ValueError as e:
        print(f"   ❌ Validation Error: {e}")
        return
    print()

    # ═══════════════════════════════════════════════════════
    # 4. Process Each Sheet Sequentially
    # ═══════════════════════════════════════════════════════
    total_sheets = len(config.xlsx.sheetName)
    translations_by_sheet = {}  # Store all results: {sheet_name: jsonline}
    results = []  # Track success/failure per sheet

    for sheet_num, sheet_name in enumerate(config.xlsx.sheetName, 1):
        print("=" * 60)
        print(f"[{sheet_num}/{total_sheets}] Processing sheet: {sheet_name}")
        print("=" * 60)

        try:
            # Read XLSX → JSONLine
            print(f"📖 Reading sheet '{sheet_name}'...")
            jsonline_data = xlsx_core.readXlsx(sheet_name)

            lines = jsonline_data.split('\n')
            print(f"   ✓ Read {len(lines)} sentences")

            # Translate via API
            print(f"🔄 Translating...")
            print(f"   ℹ️  Batch size: {config.gpt.numPerRequestTranslate}")
            print(f"   ℹ️  Context window: {config.gpt.contextNum}")

            translated_jsonline = translate_with_api(
                jsonline_input=jsonline_data,
                config=config,
                client=openai_client
            )

            # Store result
            translations_by_sheet[sheet_name] = translated_jsonline

            result_lines = len(translated_jsonline.split('\n'))
            print(f"   ✅ Translated {result_lines} sentences")

            results.append({
                "sheet": sheet_name,
                "status": "success",
                "sentences": result_lines
            })

        except FileNotFoundError as e:
            print(f"   ❌ File Error: {e}")
            results.append({"sheet": sheet_name, "status": "failed", "error": str(e)})
            continue  # Continue to next sheet

        except ValueError as e:
            print(f"   ❌ Validation Error: {e}")
            results.append({"sheet": sheet_name, "status": "failed", "error": str(e)})
            continue

        except Exception as e:
            print(f"   ❌ Translation Error: {e}")
            logger.exception(f"Sheet '{sheet_name}' translation failed")
            results.append({"sheet": sheet_name, "status": "failed", "error": str(e)})
            continue

        print()

    # ═══════════════════════════════════════════════════════
    # 5. Write All Sheets to Single Output File
    # ═══════════════════════════════════════════════════════
    if translations_by_sheet:
        print("=" * 60)
        print("💾 Writing all translations to output file...")
        print("=" * 60)

        try:
            xlsx_core.writeMultipleSheets(translations_by_sheet)
            print()
        except Exception as e:
            print(f"   ❌ Write Error: {e}")
            logger.exception("Failed to write translations")
            return
    else:
        print("⚠️  No translations to write (all sheets failed)")
        print()

    # ═══════════════════════════════════════════════════════
    # 6. Print Summary Report
    # ═══════════════════════════════════════════════════════
    print_summary(results, config.xlsx.outputPath)

    # Display cache statistics
    if config.gpt.enablePromptCaching:
        print()
        openai_client.print_cache_statistics()


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
            # USER DECISION: For dual-target mode, include only dst1 to save tokens
            if config.xlsx.has_dual_target():
                # Extract only dst1 for context (40% token savings)
                for item in translations:
                    context_item = {"id": item["id"]}
                    if 'dst1' in item:
                        context_item["dst1"] = item["dst1"]
                    elif 'dst' in item:
                        # Fallback for backward compatibility
                        context_item["dst1"] = item["dst"]
                    context_window.append(context_item)
            else:
                # Single-target mode: keep full context (legacy)
                context_window.extend(translations)

            if len(context_window) > context_size:
                context_window = context_window[-context_size:]

            logger.info(f"  ✓ Translated {len(translations)} sentences")

        except Exception as e:
            logger.error(f"  ✗ Batch {batch_num} failed: {e}")
            raise

    # Convert back to JSONLine format
    result_lines = []
    is_dual_target = config.xlsx.has_dual_target()

    for item in all_translations:
        # Detect dual-target vs single-target response
        if 'dst1' in item and 'dst2' in item:
            # Perfect dual-target response
            result_lines.append(
                json.dumps({
                    "id": item["id"],
                    "dst1": item["dst1"],
                    "dst2": item["dst2"]
                }, ensure_ascii=False)
            )
        elif 'dst' in item and is_dual_target:
            # Fallback: API returned single dst in dual-target mode
            # USER DECISION: Duplicate to both columns
            result_lines.append(
                json.dumps({
                    "id": item["id"],
                    "dst1": item["dst"],
                    "dst2": item["dst"]  # Duplicate
                }, ensure_ascii=False)
            )
        elif 'dst1' in item and is_dual_target:
            # Fallback: API returned only dst1 (incomplete dual-target)
            # Duplicate dst1 to both columns
            result_lines.append(
                json.dumps({
                    "id": item["id"],
                    "dst1": item["dst1"],
                    "dst2": item["dst1"]  # Duplicate
                }, ensure_ascii=False)
            )
        elif 'dst' in item:
            # Single-target mode (backward compatibility)
            result_lines.append(
                json.dumps({"id": item["id"], "dst": item["dst"]}, ensure_ascii=False)
            )
        else:
            raise ValueError(f"Invalid API response format: missing dst/dst1/dst2 in {item}")

    return "\n".join(result_lines)


def validate_sheets_exist(input_path: str, sheet_names: List[str]) -> None:
    """
    Validate that all specified sheets exist in the input file.

    Args:
        input_path: Path to input XLSX file
        sheet_names: List of sheet names to validate

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If any sheet doesn't exist
    """
    from openpyxl import load_workbook

    file_path = Path(input_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    workbook = load_workbook(input_path, read_only=True)
    available_sheets = workbook.sheetnames
    workbook.close()

    invalid_sheets = [s for s in sheet_names if s not in available_sheets]
    if invalid_sheets:
        raise ValueError(
            f"Sheets not found: {', '.join(invalid_sheets)}\n"
            f"Available sheets: {', '.join(available_sheets)}"
        )


def print_summary(results: List[Dict], output_path: str) -> None:
    """
    Print processing summary with success/failure statistics.

    Args:
        results: List of result dicts with sheet, status, sentences, error
        output_path: Path to output file
    """
    print("=" * 60)
    print("📊 MULTI-SHEET PROCESSING SUMMARY")
    print("=" * 60)

    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    # Print per-sheet results
    for result in results:
        if result["status"] == "success":
            print(f"✅ {result['sheet']}: {result['sentences']} sentences")
        else:
            error_msg = result.get("error", "Unknown error")
            print(f"❌ {result['sheet']}: {error_msg}")

    print()
    print(f"Total: {len(successful)}/{len(results)} sheets processed successfully")

    if successful:
        total_sentences = sum(r["sentences"] for r in successful)
        print(f"Output: {output_path} ({total_sentences} total sentences)")

    if failed:
        print()
        print(f"⚠️  {len(failed)} sheet(s) failed - review errors above")

    print("=" * 60)


if __name__ == "__main__":
    main()
