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

        # Cache statistics
        self.cache_stats = {
            'total_requests': 0,
            'cached_tokens_saved': 0,
            'uncached_tokens': 0
        }

        self.logger.info(
            f"Initialized COpenAIClient with model={self.token_config.modelName}, "
            f"endpoint={base_url}, "
            f"prompt_caching={'enabled' if config.gpt.enablePromptCaching else 'disabled'}"
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
            # Prepare API call parameters
            api_params = {
                'model': self.token_config.modelName,
                'messages': messages,
                'stream': False  # Explicitly disable streaming
            }

            # Add prompt caching for GPT-5.1 (Extended Caching: 24h retention)
            if self.config.gpt.enablePromptCaching:
                # GPT-5.1 supports extended prompt caching with retention parameter
                if self.token_config.modelName.startswith('gpt-5'):
                    api_params['prompt_cache_retention'] = self.config.gpt.promptCacheRetention
                    self.logger.debug(
                        f"Prompt caching enabled: retention={self.config.gpt.promptCacheRetention}"
                    )

            # Make API call (synchronous only)
            # Note: GPT-5 models don't support temperature, frequency_penalty, or max_tokens
            response = self.client.chat.completions.create(**api_params)

            # Calculate response time
            response_time = time.time() - start_time

            # Track cache statistics
            self.cache_stats['total_requests'] += 1
            if hasattr(response, 'usage') and response.usage:
                # OpenAI returns cached_tokens in prompt_tokens_details
                cached_tokens = 0
                if hasattr(response.usage, 'prompt_tokens_details'):
                    prompt_details = response.usage.prompt_tokens_details
                    # Access Pydantic object attribute directly
                    cached_tokens = getattr(prompt_details, 'cached_tokens', 0)

                uncached_tokens = response.usage.prompt_tokens - cached_tokens

                self.cache_stats['cached_tokens_saved'] += cached_tokens
                self.cache_stats['uncached_tokens'] += uncached_tokens

                # Calculate cache hit rate
                cache_hit_rate = (cached_tokens / response.usage.prompt_tokens * 100) if response.usage.prompt_tokens > 0 else 0

                self.logger.info(
                    f"Received response: "
                    f"prompt_tokens={response.usage.prompt_tokens} "
                    f"(cached={cached_tokens}, uncached={uncached_tokens}, hit_rate={cache_hit_rate:.1f}%), "
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
                self.logger.warning(
                    f"Skipping malformed JSON at line {line_num}: {e}\n"
                    f"Problematic line: {line[:200]}..."
                )
                continue  # Skip and continue processing

        self.logger.info(f"Extracted {len(results)} JSONLine objects")

        # Warn if lines were skipped
        expected_lines = len([l for l in jsonline_content.splitlines() if l.strip()])
        if len(results) < expected_lines:
            self.logger.warning(
                f"Extracted {len(results)}/{expected_lines} lines - "
                f"{expected_lines - len(results)} lines skipped due to errors"
            )

        return results

    def get_cache_statistics(self) -> Dict[str, any]:
        """
        Get prompt caching performance statistics.

        Returns detailed metrics about cache usage including:
        - Total API requests made
        - Total cached tokens saved (90% cost reduction)
        - Total uncached tokens
        - Overall cache hit rate
        - Estimated cost savings

        Returns:
            Dict: Cache statistics with the following keys:
                - total_requests (int): Total API calls made
                - cached_tokens_saved (int): Total tokens served from cache
                - uncached_tokens (int): Total tokens not cached
                - cache_hit_rate (float): Percentage of tokens served from cache
                - estimated_savings_percent (float): Estimated cost savings percentage

        Example:
            >>> stats = client.get_cache_statistics()
            >>> print(f"Cache hit rate: {stats['cache_hit_rate']:.1f}%")
            >>> print(f"Cost savings: {stats['estimated_savings_percent']:.1f}%")
        """
        total_tokens = self.cache_stats['cached_tokens_saved'] + self.cache_stats['uncached_tokens']
        cache_hit_rate = (
            (self.cache_stats['cached_tokens_saved'] / total_tokens * 100)
            if total_tokens > 0 else 0
        )

        # Cached tokens are 90% cheaper (10% cost)
        # Savings = (cached_tokens * 0.9) / total_tokens
        estimated_savings = (
            (self.cache_stats['cached_tokens_saved'] * 0.9 / total_tokens * 100)
            if total_tokens > 0 else 0
        )

        return {
            'total_requests': self.cache_stats['total_requests'],
            'cached_tokens_saved': self.cache_stats['cached_tokens_saved'],
            'uncached_tokens': self.cache_stats['uncached_tokens'],
            'total_tokens': total_tokens,
            'cache_hit_rate': cache_hit_rate,
            'estimated_savings_percent': estimated_savings
        }

    def print_cache_statistics(self) -> None:
        """
        Print human-readable cache statistics to console.

        Displays a formatted summary of cache performance including
        hit rate and estimated cost savings.

        Example output:
            ╔═══════════════════════════════════════════════╗
            ║     OpenAI Prompt Caching Statistics         ║
            ╠═══════════════════════════════════════════════╣
            ║ Total Requests:           42                 ║
            ║ Cached Tokens Saved:      125,430 (85.2%)    ║
            ║ Uncached Tokens:          21,789 (14.8%)     ║
            ║ Total Tokens Processed:   147,219            ║
            ║ Estimated Cost Savings:   ~76.7%             ║
            ╚═══════════════════════════════════════════════╝
        """
        stats = self.get_cache_statistics()

        print("\n" + "═" * 55)
        print("    📊 OpenAI Prompt Caching Statistics")
        print("═" * 55)
        print(f"  Total Requests:           {stats['total_requests']}")
        print(f"  Cached Tokens Saved:      {stats['cached_tokens_saved']:,} "
              f"({stats['cache_hit_rate']:.1f}%)")
        print(f"  Uncached Tokens:          {stats['uncached_tokens']:,} "
              f"({100 - stats['cache_hit_rate']:.1f}%)")
        print(f"  Total Tokens Processed:   {stats['total_tokens']:,}")
        print(f"  Estimated Cost Savings:   ~{stats['estimated_savings_percent']:.1f}%")
        print("═" * 55 + "\n")
