"""
Test Prompt Caching Performance

This script tests OpenAI Prompt Caching (GPT-5.1 Extended Caching)
by sending multiple identical system prompts to measure cache hit rate.

Expected behavior:
- First request: All tokens uncached (cache MISS)
- Subsequent requests: System prompt tokens cached (cache HIT)
- Cache retention: 24 hours (GPT-5.1)
- Cost savings: ~90% for cached tokens

Usage:
    python test_cache.py
"""

from core.CConfig import CConfig
from core.COpenAIClient import COpenAIClient
from core.Prompts import GPT4_SYSTEM_PROMPT, GPT4_TRANS_PROMPT
import time


def test_prompt_caching():
    """
    Test prompt caching with multiple identical requests.

    Workflow:
    1. Load configuration (should have enablePromptCaching=true)
    2. Create OpenAI client
    3. Send 5 identical translation requests
    4. Measure cache hit rate and cost savings
    """
    print("\n" + "=" * 60)
    print("🧪 Testing OpenAI Prompt Caching (GPT-5.1)")
    print("=" * 60 + "\n")

    # Load configuration
    print("📋 Loading configuration...")
    config = CConfig("config.yaml")
    print(f"✓ Prompt Caching: {'Enabled' if config.gpt.enablePromptCaching else 'Disabled'}")
    print(f"✓ Cache Retention: {config.gpt.promptCacheRetention}")
    print(f"✓ Model: {config.get_primary_token().modelName}\n")

    if not config.gpt.enablePromptCaching:
        print("⚠️  WARNING: Prompt caching is disabled in config.yaml")
        print("   Set enablePromptCaching: true to test caching\n")
        return

    # Create OpenAI client
    client = COpenAIClient(config)

    # Prepare test messages (identical system prompt, different user input)
    test_cases = [
        '{"id": 1, "name": "ฟราน", "src": "สวัสดี"}',
        '{"id": 2, "name": "มายะ", "src": "ยินดีที่ได้รู้จัก"}',
        '{"id": 3, "src": "วันนี้อากาศดีจัง"}',
        '{"id": 4, "name": "ยูกิ", "src": "ขอบคุณมาก"}',
        '{"id": 5, "src": "ราตรีสวัสดิ์"}',
    ]

    print(f"🚀 Sending {len(test_cases)} translation requests...")
    print(f"   Each request has identical system prompt (~1,200 tokens)")
    print(f"   Expecting cache HIT after first request\n")

    # Send multiple requests
    for i, test_input in enumerate(test_cases, 1):
        print(f"📤 Request {i}/{len(test_cases)}: ", end="", flush=True)

        # Prepare prompt with glossary
        glossary = "ฟราน\tฟラン\tname\nมายะ\tマヤ\tname\nยูกิ\tユキ\tname"
        prompt = GPT4_TRANS_PROMPT.replace("[TargetLang]", config.targetLanguage)
        prompt = prompt.replace("[Glossary]", glossary)
        prompt = prompt.replace("[Input]", test_input)

        # Create messages (identical system prompt every time)
        messages = [
            {"role": "system", "content": GPT4_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "```jsonline\n"}  # Prime response
        ]

        try:
            # Send request
            start_time = time.time()
            response = client.send_chat_completion(messages)
            elapsed = time.time() - start_time

            # Extract translation
            content = client.parse_response(response)
            translations = client.extract_jsonline(content)

            print(f"✓ ({elapsed:.2f}s) - {len(translations)} translations")

            # Show cache info for this request
            if hasattr(response, 'usage') and response.usage:
                cached = getattr(response.usage, 'prompt_tokens_details', {}).get('cached_tokens', 0)
                total_prompt = response.usage.prompt_tokens
                cache_rate = (cached / total_prompt * 100) if total_prompt > 0 else 0

                if i == 1:
                    print(f"   └─ Cache MISS (first request) - {total_prompt} tokens uncached")
                else:
                    print(f"   └─ Cache HIT: {cached}/{total_prompt} tokens ({cache_rate:.1f}%)")

        except Exception as e:
            print(f"✗ Error: {e}")
            continue

        # Small delay between requests
        if i < len(test_cases):
            time.sleep(0.5)

    # Print final statistics
    print("\n" + "=" * 60)
    client.print_cache_statistics()

    # Recommendations
    stats = client.get_cache_statistics()
    if stats['cache_hit_rate'] > 70:
        print("✅ Cache performance: EXCELLENT")
        print(f"   You're saving ~{stats['estimated_savings_percent']:.0f}% on API costs!")
    elif stats['cache_hit_rate'] > 40:
        print("⚠️  Cache performance: MODERATE")
        print("   Consider increasing cache retention or reducing prompt variations")
    else:
        print("❌ Cache performance: POOR")
        print("   Check if:")
        print("   - Model supports prompt caching (GPT-5.1 recommended)")
        print("   - System prompt is truly identical across requests")
        print("   - Cache retention is set appropriately")

    print("\n💡 Tips for optimal caching:")
    print("   1. Keep system prompt identical across requests")
    print("   2. Place static content (glossary) in system prompt")
    print("   3. Only vary the user message (input batch)")
    print("   4. Use 24h retention for long translation sessions")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        test_prompt_caching()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
