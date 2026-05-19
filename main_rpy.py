"""
main_rpy.py - Complete RPY Translation Workflow

Translates Ren'Py translate block files (.rpy) using OpenAI API.
Reuses the batching + context pipeline from main_integral.py.

Workflow:
    1. Load configuration
    2. Read RPY → JSONLine format (via RPYCore)
    3. Translate via OpenAI API (batched with context window)
    4. Write JSONLine → RPY output (via RPYCore)
"""

import logging
from core.CConfig import CConfig
from core.COpenAIClient import COpenAIClient
from core.RPYCore import RPYCore
from main_integral import translate_with_api

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────
INPUT_RPY  = "input/s1_1.rpy"
OUTPUT_RPY = "output/s1_1.rpy"
# ──────────────────────────────────────────────────────────


def main():
    # ═══════════════════════════════════════════════════════
    # 1. Load Configuration
    # ═══════════════════════════════════════════════════════
    print("📋 Loading configuration...")
    config = CConfig("config.yaml")
    print(f"   ✓ Source language : {config.srcLanguage}")
    print(f"   ✓ Target language : {config.targetLanguage}")
    print(f"   ✓ Input  file     : {INPUT_RPY}")
    print(f"   ✓ Output file     : {OUTPUT_RPY}")
    print(f"   ✓ Batch size      : {config.gpt.numPerRequestTranslate}")
    print(f"   ✓ Context window  : {config.gpt.contextNum}")
    print()

    # ═══════════════════════════════════════════════════════
    # 2. Initialize RPYCore + OpenAI client
    # ═══════════════════════════════════════════════════════
    rpy_core = RPYCore(INPUT_RPY, OUTPUT_RPY)
    client   = COpenAIClient(config)

    # ═══════════════════════════════════════════════════════
    # 3. Read RPY → JSONLine
    # ═══════════════════════════════════════════════════════
    print("📖 Reading RPY file...")
    jsonline_data = rpy_core.readRpy()
    total_lines = len([l for l in jsonline_data.split('\n') if l.strip()])
    print(f"   ✓ Found {total_lines} translatable lines")
    print()

    # ═══════════════════════════════════════════════════════
    # 4. Translate via API (batched + context window)
    # ═══════════════════════════════════════════════════════
    print("🔄 Translating...")
    translated_jsonline = translate_with_api(
        jsonline_input=jsonline_data,
        config=config,
        client=client
    )
    translated_count = len([l for l in translated_jsonline.split('\n') if l.strip()])
    print(f"   ✅ Translated {translated_count} lines")
    print()

    # ═══════════════════════════════════════════════════════
    # 5. Write translated JSONLine → RPY output
    # ═══════════════════════════════════════════════════════
    print("💾 Writing output RPY...")
    rpy_core.writeRpy(translated_jsonline)
    print()

    # ═══════════════════════════════════════════════════════
    # 6. Cache statistics (if enabled)
    # ═══════════════════════════════════════════════════════
    if config.gpt.enablePromptCaching:
        client.print_cache_statistics()

    print("✅ Done!")


if __name__ == "__main__":
    main()
