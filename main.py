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
        target_lang = config.language
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
        context_translations = """{"id":3,"name":"先輩","dst":"อ่า<br>ใช่แล้ว"}
{"id":4,"name":"Flan","dst":"มากินข้าวเช้าด้วยกันเถอะ!"}
{"id":5,"dst":"เธอยิ้มอย่างมีความสุข"}
{"id":6,"name":"先輩","dst":"อืม<br>ไปกันเถอะ"}
{"id":7,"name":"Flan","dst":"ดีจัง!"}
{"id":8,"dst":"ทั้งสองคนมุ่งหน้าไปที่โรงอาหาร"}
{"id":9,"name":"Flan","dst":"รุ่นพี่<br>อันนี้อร่อยมากเลย!"}
{"id":10,"name":"先輩","dst":"จริงด้วย"}"""

        # New input (10 sentences for Batch 2)
        new_input = """{\"id\":11,\"name\":\"先輩\",\"src\":\"フラン、<br>美味しかったね。\"}
{\"id\":12,\"name\":\"フラン\",\"src\":\"はい！<br>また来ましょう！\"}
{\"id\":13,\"src\":\"彼女は満足そうだった。\"}
{\"id\":14,\"name\":\"先輩\",\"src\":\"次は何食べる？\"}
{\"id\":15,\"name\":\"フラン\",\"src\":\"んー、<br>パスタがいいです！\"}
{\"id\":16,\"name\":\"先輩\",\"src\":\"いいね。\"}
{\"id\":17,\"src\":\"二人は次の予定を考えた。\"}
{\"id\":18,\"name\":\"フラン\",\"src\":\"楽しみです！\"}
{\"id\":19,\"name\":\"先輩\",\"src\":\"僕も。\"}
{\"id\":20,\"src\":\"そして授業の時間になった。\"}"""

        # Glossary
        glossary = """フラン\tFlan\tname, lady, teacher
先輩\tSenior\thonorific, used by Flan
魔法学院\tMagic Academy\tplace, school"""

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
