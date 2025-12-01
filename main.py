"""
main.py - Visual Novel Translation Demo

Demonstrates COpenAIClient with real OpenAI API integration.
Translates Japanese visual novel script to Thai using GPT-4.
"""

import logging
from core.CConfig import CConfig
from core.COpenAIClient import COpenAIClient
from core.Prompts import GPT4_SYSTEM_PROMPT, GPT4_TRANS_PROMPT


def main():
    """
    Main translation demo flow:
    1. Load configuration
    2. Initialize OpenAI client
    3. Build message structure with context
    4. Send translation request
    5. Parse and display results
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        # ============================================================
        # 1. Load Configuration
        # ============================================================
        logger.info("Loading configuration from config.yaml")
        config = CConfig("config.yaml")
        target_lang = config.targetLanguage
        logger.info(f"Source language: {config.srcLanguage}")
        logger.info(f"Target language: {target_lang}")

        # ============================================================
        # 2. Initialize OpenAI Client
        # ============================================================
        logger.info("Initializing OpenAI client")
        client = COpenAIClient(config)

        # ============================================================
        # 3. Prepare Sample Data (from input-output.md)
        # ============================================================

        # Previous context (8 sentences from Batch 1)
        context_translations = """"""

        # new_input = """{\"id\":1,\"name\":\"\",\"src\":\"教室の前の廊下は夕日のオレンジ色に染まっていた\"}
        # {\"id\":2,\"name\":\"\",\"src\":\"見慣れていて毎日目にする光景のはずなのに\"}
        # {\"id\":3,\"name\":\"\",\"src\":\"今日はなぜか全く違って見えた\"}
        # {\"id\":4,\"name\":\"\",\"src\":\"僕の名前はクサカ・ユウマ、高校二年生で生徒会の会計だ\"}
        # {\"id\":5,\"name\":\"\",\"src\":\"普段は放課後になると、生徒会の仕事をしている\"}
        # {\"id\":6,\"name\":\"\",\"src\":\"仕事がなければ、放課後すぐに家に帰る\"}
        # {\"id\":7,\"name\":\"\",\"src\":\"でも今日は違う。大事な約束があるからだ\"}
        # {\"id\":8,\"name\":\"\",\"src\":\"ドアを開けると、ひとりの少女が立っていた\"}
        # {\"id\":9,\"name\":\"\",\"src\":\"黒く艶やかな髪が風に揺れている\"}
        # {\"id\":10,\"name\":\"\",\"src\":\"夕日がその頬を赤く染めていた\"}"""

        new_input = """{\"id\":1,\"name\":\"Reika\",\"src\":\"ごめんなさい、こんな夕方に呼び出して\"}
        {\"id\":2,\"name\":\"\",\"src\":\"その声は普段とは違い、柔らかく耳に響いた\"}
        {\"id\":3,\"name\":\"Reika\",\"src\":\"私、もう決めたの\"}
        {\"id\":4,\"name\":\"Reika\",\"src\":\"今日、どうしてもあなたに伝えたいことがある\"}
        {\"id\":5,\"name\":\"\",\"src\":\"その瞳からは強い情熱が伝わってきた\"}
        {\"id\":6,\"name\":\"\",\"src\":\"ついに来たのだ。僕の時が\"}
        {\"id\":7,\"name\":\"Reika\",\"src\":\"ユウマ…\"}
        {\"id\":8,\"name\":\"Reika\",\"src\":\"私…\"}
        {\"id\":9,\"name\":\"Reika\",\"src\":\"私………\"}
        {\"id\":10,\"name\":\"\",\"src\":\"僕の心臓はこれまでにないほど激しく鼓動していた\"}
        {\"id\":11,\"name\":\"\",\"src\":\"ああ、ついに僕の青春が花開こうとしている\"}
        {\"id\":12,\"name\":\"\",\"src\":\"さあ、僕に告白してくれ！\"}
        {\"id\":13,\"name\":\"Reika\",\"src\":\"いつになったらお金を返すのよ！！！\"}"""

        # Glossary
        glossary = """"""

        # ============================================================
        # 4. Build Message Structure (5 messages)
        # ============================================================

        # Replace placeholders in prompt template
        user_prompt = GPT4_TRANS_PROMPT.replace("[TargetLang]", target_lang)
        user_prompt = user_prompt.replace("[Glossary]", glossary)
        user_prompt = user_prompt.replace("[Input]", new_input)

        messages = [
            # Message 1: System personality
            {
                "role": "system",
                "content": GPT4_SYSTEM_PROMPT
            },
            # Message 2: Context marker (for batch 2+)
            {
                "role": "user",
                "content": "<input>\n(...truncated history source texts...)\n</input>\n<output>"
            },
            # Message 3: Previous translations (context window)
            {
                "role": "assistant",
                "content": f"```jsonline\n{context_translations}\n```"
            },
            # Message 4: Full prompt with requirements + glossary + new input
            {
                "role": "user",
                "content": user_prompt
            },
            # Message 5: Priming to force JSONLine format
            {
                "role": "assistant",
                "content": "```jsonline"
            }
        ]

        logger.info(f"Built message structure: {len(messages)} messages")
        logger.info(f"Translating 10 sentences (id 11-20) with 8-sentence context")

        # ============================================================
        # 5. Send Translation Request
        # ============================================================
        logger.info("Sending translation request to OpenAI API...")
        response = client.send_chat_completion(messages)

        # ============================================================
        # 6. Parse Response
        # ============================================================
        logger.info("Parsing API response...")
        content = client.parse_response(response)

        # DEBUG: Show raw response content
        print("\n" + "="*70)
        print("🔍 RAW RESPONSE CONTENT (for debugging)")
        print("="*70)
        print(content)
        print("="*70)
        print(f"📏 Content length: {len(content)} characters")
        print("="*70)

        translations = client.extract_jsonline(content)

        # ============================================================
        # 7. Display Results
        # ============================================================
        print("\n" + "="*70)
        print("TRANSLATION RESULTS")
        print("="*70)

        # Token usage
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            print(f"\n📊 Token Usage:")
            print(f"  Prompt:     {usage.prompt_tokens:,} tokens")
            print(f"  Completion: {usage.completion_tokens:,} tokens")
            print(f"  Total:      {usage.total_tokens:,} tokens")

            # Cost estimation (GPT-4 Turbo rates)
            prompt_cost = usage.prompt_tokens * 0.01 / 1000
            completion_cost = usage.completion_tokens * 0.03 / 1000
            total_cost = prompt_cost + completion_cost
            print(f"  Est. Cost:  ${total_cost:.4f}")

        # Translations
        print(f"\n📝 Translations ({len(translations)} sentences):")
        print("-"*70)
        for item in translations:
            id_num = item.get('id', '?')
            name = item.get('name', '')
            dst = item.get('dst', '')

            if name:
                print(f"[{id_num:2d}] {name}: {dst}")
            else:
                print(f"[{id_num:2d}] {dst}")

        print("="*70)
        print("\n✅ Translation completed successfully!")

    except FileNotFoundError:
        logger.error("config.yaml not found. Please create configuration file.")
        return 1

    except ValueError as e:
        logger.error(f"Configuration or parsing error: {e}")
        return 1

    except Exception as e:
        logger.error(f"Translation failed: {type(e).__name__}: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
