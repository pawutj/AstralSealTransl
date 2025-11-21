"""
COpenAIClient - OpenAI API Communication Layer

Pure API communication layer for OpenAI Chat Completion API.
No business logic - handles only API calls, response parsing, and logging.
"""

from typing import List, Dict
from openai import OpenAI
from openai.types.chat import ChatCompletion
import json
import logging
import time
from .CConfig import CConfig


class COpenAIClient:
    """
    OpenAI API communication layer.

    Handles synchronous chat completion requests, response parsing,
    and JSONLine extraction. Uses CConfig for all configuration.

    Features:
    - Synchronous batch processing (no streaming)
    - Comprehensive request/response logging
    - Minimal validation (trusts OpenAI API)
    - Re-raises OpenAI exceptions directly

    Attributes:
        config (CConfig): Configuration instance
        client (OpenAI): OpenAI client instance
        logger (Logger): Logger for request/response tracking
    """

    def __init__(self, config: CConfig):
        """
        Initialize OpenAI API client with configuration.

        Args:
            config (CConfig): Configuration instance containing API credentials
                and GPT settings

        Raises:
            ValueError: If config validation fails
        """
        self.config = config
        self.token_config = config.get_primary_token()

        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Extract base URL from endpoint (remove /chat/completions if present)
        base_url = self.token_config.endpoint
        if base_url.endswith('/chat/completions'):
            base_url = base_url[:-len('/chat/completions')]

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=self.token_config.token,
            base_url=base_url
        )

        self.logger.info(
            f"Initialized COpenAIClient with model={self.token_config.modelName}, "
            f"endpoint={base_url}"
        )

    def send_chat_completion(self, messages: List[Dict[str, str]]) -> ChatCompletion:
        """
        Send synchronous chat completion request to OpenAI API.

        Sends a batch of messages to the configured OpenAI-compatible endpoint
        and returns the complete response. No streaming support.

        Args:
            messages (List[Dict[str, str]]): List of message dictionaries with
                'role' and 'content' keys. Example:
                [
                    {"role": "system", "content": "You are..."},
                    {"role": "user", "content": "Translate..."}
                ]

        Returns:
            ChatCompletion: OpenAI ChatCompletion response object

        Raises:
            openai.APIError: API-related errors (connection, auth, rate limit, etc.)
            ValueError: If messages is empty or invalid

        Example:
            >>> messages = [{"role": "system", "content": "You are Ciallo"}]
            >>> response = client.send_chat_completion(messages)
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        # Log request details
        self.logger.info(
            f"Sending request to {self.token_config.modelName} "
            f"with {len(messages)} messages"
        )
        self.logger.debug(
            f"Request parameters: temperature={self.config.gpt.temperature}, "
            f"frequency_penalty={self.config.gpt.frequency_penalty}"
        )

        # Track timing
        start_time = time.time()

        try:
            # Make API call (synchronous only)
            response = self.client.chat.completions.create(
                model=self.token_config.modelName,
                messages=messages,
                temperature=self.config.gpt.temperature,
                frequency_penalty=self.config.gpt.frequency_penalty,
                stream=False  # Explicitly disable streaming
            )

            # Calculate response time
            response_time = time.time() - start_time

            # Log response details
            if hasattr(response, 'usage') and response.usage:
                self.logger.info(
                    f"Received response: "
                    f"prompt_tokens={response.usage.prompt_tokens}, "
                    f"completion_tokens={response.usage.completion_tokens}, "
                    f"total_tokens={response.usage.total_tokens}, "
                    f"response_time={response_time:.2f}s"
                )
            else:
                self.logger.info(f"Received response in {response_time:.2f}s")

            # Log content preview
            if response.choices and response.choices[0].message.content:
                content_preview = response.choices[0].message.content[:100]
                self.logger.debug(
                    f"Response content preview: {content_preview}..."
                )

            return response

        except Exception as e:
            # Log error and re-raise
            self.logger.error(
                f"OpenAI API error: {type(e).__name__}: {str(e)}"
            )
            raise  # Re-raise exception directly

    def parse_response(self, response: ChatCompletion) -> str:
        """
        Parse ChatCompletion response and extract content string.

        Performs minimal validation and extracts the content from the first
        choice in the response.

        Args:
            response (ChatCompletion): OpenAI ChatCompletion response object

        Returns:
            str: Extracted content string from response

        Raises:
            ValueError: If response structure is invalid or content is missing

        Example:
            >>> content = client.parse_response(response)
            >>> print(content)  # "```jsonline\\n{...}\\n```"
        """
        # Minimal validation: check basic structure
        if not response.choices:
            raise ValueError("Response has no choices")

        if not response.choices[0].message:
            raise ValueError("Response choice has no message")

        content = response.choices[0].message.content

        if content is None:
            raise ValueError("Response message has no content")

        self.logger.debug(
            f"Parsed response content: {len(content)} characters"
        )

        return content

    def extract_jsonline(self, content: str) -> List[Dict]:
        """
        Extract and parse JSONLine format from response content.

        Extracts JSONLine data from markdown code block (```jsonline ... ```)
        and parses each line as a JSON object.

        Expected format:
        ```jsonline
        {"id": 1, "name": "Character", "dst": "Translation"}
        {"id": 2, "dst": "Another translation"}
        ```

        Args:
            content (str): Response content containing JSONLine in markdown

        Returns:
            List[Dict]: List of parsed JSON objects, one per line

        Raises:
            ValueError: If no JSONLine block found or content is empty
            json.JSONDecodeError: If JSON parsing fails

        Example:
            >>> content = '```jsonline\\n{"id": 1, "dst": "Hello"}\\n```'
            >>> result = client.extract_jsonline(content)
            >>> print(result)  # [{"id": 1, "dst": "Hello"}]
        """
        if not content:
            raise ValueError("Content is empty")

        # Extract content between ```jsonline and ```
        jsonline_start = content.find("```jsonline")
        if jsonline_start == -1:
            # Try alternative format without language specifier
            jsonline_start = content.find("```")
            if jsonline_start == -1:
                raise ValueError("No JSONLine code block found in content")
            jsonline_start += len("```")
        else:
            jsonline_start += len("```jsonline")

        jsonline_end = content.find("```", jsonline_start)
        if jsonline_end == -1:
            raise ValueError("Unclosed JSONLine code block")

        # Extract JSONLine content
        jsonline_content = content[jsonline_start:jsonline_end].strip()

        if not jsonline_content:
            raise ValueError("Empty JSONLine content")

        self.logger.debug(
            f"Extracting JSONLine: {len(jsonline_content)} characters, "
            f"{len(jsonline_content.splitlines())} lines"
        )

        # Parse each line as JSON
        results = []
        for line_num, line in enumerate(jsonline_content.splitlines(), 1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue

            try:
                parsed = json.loads(line)
                results.append(parsed)
            except json.JSONDecodeError as e:
                self.logger.error(
                    f"JSON decode error at line {line_num}: {e}"
                )
                raise

        self.logger.info(f"Extracted {len(results)} JSONLine objects")

        return results
