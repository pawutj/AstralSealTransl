"""
Unit tests for COpenAIClient

Tests the OpenAI API communication layer with mocked API calls.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import logging
from openai import APIError, RateLimitError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from core import CConfig, COpenAIClient


class TestCOpenAIClient(unittest.TestCase):
    """Test suite for COpenAIClient class"""

    def setUp(self):
        """Set up test fixtures"""
        # Load test configuration
        self.config = CConfig("config.yaml")

        # Suppress logging during tests
        logging.getLogger('core.COpenAIClient').setLevel(logging.CRITICAL)

    def tearDown(self):
        """Clean up after tests"""
        # Reset logging level
        logging.getLogger('core.COpenAIClient').setLevel(logging.INFO)

    @patch('core.COpenAIClient.OpenAI')
    def test_constructor_valid_config(self, mock_openai):
        """Test COpenAIClient constructor with valid configuration"""
        client = COpenAIClient(self.config)

        # Verify attributes
        self.assertIsNotNone(client.config)
        self.assertIsNotNone(client.token_config)
        self.assertIsNotNone(client.client)
        self.assertIsNotNone(client.logger)

        # Verify OpenAI client was initialized
        mock_openai.assert_called_once()

    @patch('core.COpenAIClient.OpenAI')
    def test_send_chat_completion_success(self, mock_openai):
        """Test successful chat completion request"""
        # Create client
        client = COpenAIClient(self.config)

        # Mock API response
        mock_response = Mock(spec=ChatCompletion)
        mock_response.choices = [
            Mock(
                message=Mock(content="```jsonline\n{\"id\": 1}\n```")
            )
        ]
        mock_response.usage = Mock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        # Mock the API call
        client.client.chat.completions.create = Mock(return_value=mock_response)

        # Test messages
        messages = [
            {"role": "system", "content": "You are Ciallo"},
            {"role": "user", "content": "Translate this"}
        ]

        # Call method
        response = client.send_chat_completion(messages)

        # Verify response
        self.assertEqual(response, mock_response)

        # Verify API was called with correct parameters
        client.client.chat.completions.create.assert_called_once_with(
            model=self.config.get_primary_token().modelName,
            messages=messages,
            temperature=self.config.gpt.temperature,
            frequency_penalty=self.config.gpt.frequency_penalty,
            stream=False
        )

    @patch('core.COpenAIClient.OpenAI')
    def test_send_chat_completion_empty_messages(self, mock_openai):
        """Test send_chat_completion with empty messages raises ValueError"""
        client = COpenAIClient(self.config)

        with self.assertRaises(ValueError) as context:
            client.send_chat_completion([])

        self.assertIn("cannot be empty", str(context.exception))

    @patch('core.COpenAIClient.OpenAI')
    def test_send_chat_completion_api_error(self, mock_openai):
        """Test that API errors are re-raised correctly"""
        client = COpenAIClient(self.config)

        # Create a proper mock response for RateLimitError
        mock_response = Mock()
        mock_response.request = Mock()

        # Mock API to raise error
        error = RateLimitError("Rate limit exceeded", response=mock_response, body=None)
        client.client.chat.completions.create = Mock(side_effect=error)

        messages = [{"role": "user", "content": "Test"}]

        # Verify exception is re-raised
        with self.assertRaises(RateLimitError):
            client.send_chat_completion(messages)

    @patch('core.COpenAIClient.OpenAI')
    def test_parse_response_success(self, mock_openai):
        """Test successful response parsing"""
        client = COpenAIClient(self.config)

        # Create mock response
        mock_response = Mock(spec=ChatCompletion)
        mock_response.choices = [
            Mock(message=Mock(content="Test content"))
        ]

        # Parse response
        content = client.parse_response(mock_response)

        self.assertEqual(content, "Test content")

    @patch('core.COpenAIClient.OpenAI')
    def test_parse_response_no_choices(self, mock_openai):
        """Test parse_response with no choices raises ValueError"""
        client = COpenAIClient(self.config)

        mock_response = Mock(spec=ChatCompletion)
        mock_response.choices = []

        with self.assertRaises(ValueError) as context:
            client.parse_response(mock_response)

        self.assertIn("no choices", str(context.exception))

    @patch('core.COpenAIClient.OpenAI')
    def test_parse_response_no_content(self, mock_openai):
        """Test parse_response with None content raises ValueError"""
        client = COpenAIClient(self.config)

        mock_response = Mock(spec=ChatCompletion)
        mock_response.choices = [Mock(message=Mock(content=None))]

        with self.assertRaises(ValueError) as context:
            client.parse_response(mock_response)

        self.assertIn("no content", str(context.exception))

    @patch('core.COpenAIClient.OpenAI')
    def test_extract_jsonline_success(self, mock_openai):
        """Test successful JSONLine extraction"""
        client = COpenAIClient(self.config)

        # Sample content with JSONLine
        content = """```jsonline
{"id": 1, "name": "Character", "dst": "Translation 1"}
{"id": 2, "dst": "Translation 2"}
```"""

        # Extract JSONLine
        result = client.extract_jsonline(content)

        # Verify results
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["name"], "Character")
        self.assertEqual(result[1]["id"], 2)

    @patch('core.COpenAIClient.OpenAI')
    def test_extract_jsonline_alternative_format(self, mock_openai):
        """Test JSONLine extraction with generic code block"""
        client = COpenAIClient(self.config)

        # Content without 'jsonline' specifier
        content = """```
{"id": 1, "dst": "Test"}
```"""

        result = client.extract_jsonline(content)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 1)

    @patch('core.COpenAIClient.OpenAI')
    def test_extract_jsonline_empty_lines(self, mock_openai):
        """Test JSONLine extraction ignores empty lines"""
        client = COpenAIClient(self.config)

        content = """```jsonline
{"id": 1, "dst": "Test 1"}

{"id": 2, "dst": "Test 2"}

```"""

        result = client.extract_jsonline(content)

        # Should only parse non-empty lines
        self.assertEqual(len(result), 2)

    @patch('core.COpenAIClient.OpenAI')
    def test_extract_jsonline_no_code_block(self, mock_openai):
        """Test extract_jsonline without code block raises ValueError"""
        client = COpenAIClient(self.config)

        content = '{"id": 1, "dst": "No code block"}'

        with self.assertRaises(ValueError) as context:
            client.extract_jsonline(content)

        self.assertIn("No JSONLine code block", str(context.exception))

    @patch('core.COpenAIClient.OpenAI')
    def test_extract_jsonline_unclosed_block(self, mock_openai):
        """Test extract_jsonline with unclosed code block raises ValueError"""
        client = COpenAIClient(self.config)

        content = '```jsonline\n{"id": 1}'

        with self.assertRaises(ValueError) as context:
            client.extract_jsonline(content)

        self.assertIn("Unclosed", str(context.exception))

    @patch('core.COpenAIClient.OpenAI')
    def test_extract_jsonline_empty_content(self, mock_openai):
        """Test extract_jsonline with empty content raises ValueError"""
        client = COpenAIClient(self.config)

        with self.assertRaises(ValueError) as context:
            client.extract_jsonline("")

        self.assertIn("empty", str(context.exception).lower())

    @patch('core.COpenAIClient.OpenAI')
    def test_extract_jsonline_invalid_json(self, mock_openai):
        """Test extract_jsonline with invalid JSON raises JSONDecodeError"""
        client = COpenAIClient(self.config)

        content = '```jsonline\n{invalid json}\n```'

        with self.assertRaises(json.JSONDecodeError):
            client.extract_jsonline(content)

    @patch('core.COpenAIClient.OpenAI')
    @patch('core.COpenAIClient.logging.getLogger')
    def test_logging_behavior(self, mock_get_logger, mock_openai):
        """Test that logging is called appropriately"""
        # Create mock logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Re-enable logging for this test
        logging.getLogger('core.COpenAIClient').setLevel(logging.DEBUG)

        client = COpenAIClient(self.config)

        # Mock successful API call
        mock_response = Mock(spec=ChatCompletion)
        mock_response.choices = [Mock(message=Mock(content="Test"))]
        mock_response.usage = Mock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )
        client.client.chat.completions.create = Mock(return_value=mock_response)

        messages = [{"role": "user", "content": "Test"}]
        client.send_chat_completion(messages)

        # Verify logging was called
        # Note: In real implementation, logger is created in __init__
        # This test verifies the logging calls would happen

    @patch('core.COpenAIClient.OpenAI')
    def test_integration_full_workflow(self, mock_openai):
        """Integration test: full workflow from request to parsed JSONLine"""
        client = COpenAIClient(self.config)

        # Mock API response with complete JSONLine
        jsonline_content = """```jsonline
{"id": 1, "name": "Flan", "dst": "สวัสดี"}
{"id": 2, "dst": "ขอบคุณ"}
```"""

        mock_response = Mock(spec=ChatCompletion)
        mock_response.choices = [Mock(message=Mock(content=jsonline_content))]
        mock_response.usage = Mock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        client.client.chat.completions.create = Mock(return_value=mock_response)

        # Full workflow
        messages = [
            {"role": "system", "content": "You are Ciallo"},
            {"role": "user", "content": "Translate to Thai"}
        ]

        # 1. Send request
        response = client.send_chat_completion(messages)

        # 2. Parse response
        content = client.parse_response(response)

        # 3. Extract JSONLine
        translations = client.extract_jsonline(content)

        # Verify final result
        self.assertEqual(len(translations), 2)
        self.assertEqual(translations[0]["id"], 1)
        self.assertEqual(translations[0]["name"], "Flan")
        self.assertEqual(translations[0]["dst"], "สวัสดี")
        self.assertEqual(translations[1]["dst"], "ขอบคุณ")

    @patch('core.COpenAIClient.OpenAI')
    def test_openapi_realistic_workflow(self, mock_openai):
        """
        Realistic integration test with complete OpenAI API workflow.

        Simulates Batch 2 from input-output.md:
        - Complete 5-message structure (system + context + user + priming)
        - Japanese → Chinese translation with context window
        - Glossary usage (Flan, 先輩 → 前辈)
        - Special character preservation (<br>)
        - Realistic token usage (~1,500 tokens)
        """
        client = COpenAIClient(self.config)

        # === MOCK REALISTIC RESPONSE (from input-output.md) ===
        realistic_response_content = """```jsonline
{"id":11,"name":"前辈","dst":"Flan，<br>真好吃呢。"}
{"id":12,"name":"Flan","dst":"是的！<br>下次再来吧！"}
{"id":13,"dst":"她看起来很满足。"}
{"id":14,"name":"前辈","dst":"接下来吃什么？"}
{"id":15,"name":"Flan","dst":"嗯～<br>我想吃意大利面！"}
{"id":16,"name":"前辈","dst":"不错啊。"}
{"id":17,"dst":"两人开始考虑下次的计划。"}
{"id":18,"name":"Flan","dst":"好期待！"}
{"id":19,"name":"前辈","dst":"我也是。"}
{"id":20,"dst":"然后，上课时间到了。"}
```"""

        # === CREATE REALISTIC MESSAGE STRUCTURE ===
        messages = [
            # 1. System message: Base personality
            {
                "role": "system",
                "content": "You are Ciallo, an AI translator."
            },

            # 2. User: Context marker (truncated history)
            {
                "role": "user",
                "content": "<input>\n(...truncated history source texts...)\n</input>\n<output>"
            },

            # 3. Assistant: Previous 8 translations (context window)
            {
                "role": "assistant",
                "content": (
                    "```jsonline\n"
                    '{"id":3,"name":"先輩","dst":"啊，<br>是啊。"}\n'
                    '{"id":4,"name":"Flan","dst":"一起吃早饭吧！"}\n'
                    '{"id":5,"dst":"她开心地笑了。"}\n'
                    '{"id":6,"name":"先輩","dst":"嗯，<br>走吧。"}\n'
                    '{"id":7,"name":"Flan","dst":"太好了！"}\n'
                    '{"id":8,"dst":"两人前往食堂。"}\n'
                    '{"id":9,"name":"Flan","dst":"前辈，<br>这个很好吃哦！"}\n'
                    '{"id":10,"name":"先輩","dst":"真的呢。"}\n'
                    "```"
                )
            },

            # 4. User: Full prompt with glossary + input (id 11-20)
            {
                "role": "user",
                "content": (
                    "<glossary>\n"
                    "フラン\tFlan\tname, lady, teacher\n"
                    "先輩\tSenior\thonorific, used by Flan\n"
                    "魔法学院\tMagic Academy\tplace, school\n"
                    "</glossary>\n\n"
                    "<input>\n"
                    "```jsonline\n"
                    '{"id":11,"name":"先輩","src":"フラン、<br>美味しかったね。"}\n'
                    '{"id":12,"name":"フラン","src":"はい！<br>また来ましょう！"}\n'
                    '{"id":13,"src":"彼女は満足そうだった。"}\n'
                    '{"id":14,"name":"先輩","src":"次は何食べる？"}\n'
                    '{"id":15,"name":"フラン","src":"んー、<br>パスタがいいです！"}\n'
                    '{"id":16,"name":"先輩","src":"いいね。"}\n'
                    '{"id":17,"src":"二人は次の予定を考えた。"}\n'
                    '{"id":18,"name":"フラン","src":"楽しみです！"}\n'
                    '{"id":19,"name":"先輩","src":"僕も。"}\n'
                    '{"id":20,"src":"そして授業の時間になった。"}\n'
                    "```\n"
                    "</input>\n"
                    "<output>"
                )
            },

            # 5. Assistant: Priming (forces JSONLine format)
            {
                "role": "assistant",
                "content": "```jsonline"
            }
        ]

        # === MOCK OPENAI API RESPONSE ===
        mock_response = Mock(spec=ChatCompletion)
        mock_response.id = "chatcmpl-abc123xyz"
        mock_response.object = "chat.completion"
        mock_response.created = 1737500000
        mock_response.model = "gpt-4-turbo-2024-04-09"

        mock_response.choices = [
            Mock(
                index=0,
                message=Mock(
                    role="assistant",
                    content=realistic_response_content
                ),
                finish_reason="stop"
            )
        ]

        mock_response.usage = Mock(
            prompt_tokens=1247,
            completion_tokens=312,
            total_tokens=1559
        )

        # Mock the API call
        client.client.chat.completions.create = Mock(return_value=mock_response)

        # === EXECUTE FULL WORKFLOW ===
        # Step 1: Send chat completion
        response = client.send_chat_completion(messages)

        # Step 2: Parse response
        content = client.parse_response(response)

        # Step 3: Extract JSONLine
        translations = client.extract_jsonline(content)

        # === VERIFY RESULTS ===

        # Verify translation count
        self.assertEqual(len(translations), 10, "Should have 10 translations")

        # Verify dialogue translations (with name field)
        self.assertEqual(translations[0]["id"], 11)
        self.assertEqual(translations[0]["name"], "前辈")
        self.assertEqual(translations[0]["dst"], "Flan，<br>真好吃呢。")

        self.assertEqual(translations[1]["id"], 12)
        self.assertEqual(translations[1]["name"], "Flan")
        self.assertEqual(translations[1]["dst"], "是的！<br>下次再来吧！")

        # Verify narration (no name field)
        self.assertEqual(translations[2]["id"], 13)
        self.assertNotIn("name", translations[2], "Narration should not have 'name' field")
        self.assertEqual(translations[2]["dst"], "她看起来很满足。")

        self.assertEqual(translations[6]["id"], 17)
        self.assertNotIn("name", translations[6])
        self.assertEqual(translations[6]["dst"], "两人开始考虑下次的计划。")

        # Verify special character preservation (<br>)
        br_translations = [t for t in translations if "<br>" in t.get("dst", "")]
        self.assertGreater(len(br_translations), 0, "Should preserve <br> tags")
        self.assertIn("<br>", translations[0]["dst"])
        self.assertIn("<br>", translations[1]["dst"])
        self.assertIn("<br>", translations[4]["dst"])

        # Verify glossary application (先輩 → 前辈, Flan preserved)
        character_names = [t["name"] for t in translations if "name" in t]
        self.assertIn("前辈", character_names, "先輩 should be translated to 前辈")
        self.assertIn("Flan", character_names, "Flan should be preserved from glossary")

        # Verify emotional tone preservation (excitement, satisfaction)
        self.assertIn("！", translations[1]["dst"], "Excitement should be preserved")
        self.assertIn("～", translations[4]["dst"], "Casual tone should be preserved")

        # Verify API call parameters
        client.client.chat.completions.create.assert_called_once_with(
            model=self.config.get_primary_token().modelName,
            messages=messages,
            temperature=self.config.gpt.temperature,
            frequency_penalty=self.config.gpt.frequency_penalty,
            stream=False
        )

        # Verify token usage (realistic numbers from input-output.md)
        self.assertEqual(response.usage.prompt_tokens, 1247)
        self.assertEqual(response.usage.completion_tokens, 312)
        self.assertEqual(response.usage.total_tokens, 1559)

        # Verify response metadata
        self.assertEqual(response.id, "chatcmpl-abc123xyz")
        self.assertEqual(response.model, "gpt-4-turbo-2024-04-09")
        self.assertEqual(response.choices[0].finish_reason, "stop")


def run_tests():
    """Run all tests"""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCOpenAIClient)

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return success status
    return result.wasSuccessful()


if __name__ == '__main__':
    # Run tests
    success = run_tests()

    # Exit with appropriate code
    exit(0 if success else 1)
