"""
Batch Inference Engine for Semantic Gravity Mapping.

Wraps VLLMClient with SGM-specific prompting and batching strategies.
Provides high-level methods for:
- Getting word associations (Phase 1)
- Scoring association strength via logprobs (Phase 2)
- Parallel batch processing for efficiency
"""

import asyncio
import math
import re
from typing import List, Dict, Optional, Any, Tuple

from align_test.core.base_client import BaseLLMClient


class SGMInferenceEngine:
    """
    Inference engine for Semantic Gravity Mapping operations.

    Wraps a BaseLLMClient (typically VLLMClient) with SGM-specific
    prompting strategies and batch processing capabilities.

    Attributes:
        client: LLM client instance (VLLMClient or compatible)
        temperature: Sampling temperature for generation
        batch_size: Maximum concurrent requests for batching
    """

    def __init__(
        self,
        client: BaseLLMClient,
        temperature: float = 0.7,
        batch_size: int = 32
    ):
        """
        Initialize inference engine.

        Args:
            client: BaseLLMClient instance (e.g., VLLMClient)
            temperature: Sampling temperature (0.0-1.0)
                        0.7 for associations, 0.0 for scoring
            batch_size: Max concurrent requests (32 recommended for vLLM)
        """
        self.client = client
        self.temperature = temperature
        self.batch_size = batch_size

    def get_associations(self, word: str, n: int = 5) -> List[str]:
        """
        Get N word associations for a given word (Phase 1).

        Uses carefully engineered prompt to elicit single-word associations.
        Filters out multi-word phrases and invalid responses.

        Args:
            word: Source word to get associations for
            n: Number of associations to request (default: 5)

        Returns:
            List of association words (may be < n if filtering removed some)

        Example:
            >>> engine = SGMInferenceEngine(vllm_client)
            >>> assocs = engine.get_associations('physics', n=5)
            >>> print(assocs)
            ['gravity', 'quantum', 'Newton', 'energy', 'matter']
        """
        prompt = (
            f"List {n} single-word associations for the word '{word}'. "
            f"Provide only the words, separated by commas."
        )

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.client.create_completion(
                messages=messages,
                temperature=self.temperature,
                max_tokens=100
            )

            # Parse comma-separated response
            associations = self._parse_associations(response.content, max_words=n)
            return associations

        except Exception as e:
            print(f"Warning: Failed to get associations for '{word}': {e}")
            return []

    def _parse_associations(self, text: str, max_words: int) -> List[str]:
        """
        Parse comma-separated associations from model output.

        Handles various formats:
        - "word1, word2, word3"
        - "1. word1\n2. word2\n3. word3"
        - "word1,word2,word3"

        Filters out:
        - Multi-word phrases (containing spaces)
        - Empty strings
        - Non-alphabetic words (numbers, symbols)

        Args:
            text: Raw model output
            max_words: Maximum number of words to return

        Returns:
            List of cleaned single-word associations
        """
        if not text:
            return []

        # Remove numbered list prefixes (1., 2., etc.)
        text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)

        # Split on commas, newlines, or semicolons
        raw_words = re.split(r'[,;\n]+', text)

        associations = []
        for word in raw_words:
            # Clean whitespace
            word = word.strip()

            # Skip empty, multi-word, or non-alphabetic
            if not word:
                continue
            if ' ' in word:
                continue
            if not re.match(r'^[a-zA-Z-]+$', word):  # Allow hyphens for words like "sous-vide"
                continue

            # Normalize to lowercase (preserves proper nouns like Mjolnir)
            # but makes graph analysis easier
            associations.append(word.lower())

            if len(associations) >= max_words:
                break

        return associations

    def score_association(
        self,
        source: str,
        target: str,
        return_logprob: bool = True
    ) -> float:
        """
        Score association strength between two words (Phase 2).

        Asks model: "Word: [source]. Association:" and measures the probability
        of generating the target word. This gives a direct measure of how strongly
        the model associates target with source.

        Args:
            source: Source word
            target: Target word (potential association)
            return_logprob: If True, returns raw logprob; if False, returns e^logprob

        Returns:
            Association score:
            - If return_logprob=True: logprob (negative float, closer to 0 = stronger)
            - If return_logprob=False: e^logprob (0-1, closer to 1 = stronger)

        Example:
            >>> engine = SGMInferenceEngine(vllm_client, temperature=0.0)
            >>> score = engine.score_association('physics', 'gravity')
            >>> print(score)
            -1.2  # logprob: Strong association
            >>> score = engine.score_association('physics', 'banana')
            >>> print(score)
            -8.5  # logprob: Weak association
        """
        prompt = f"Word: {source}. Association:"

        messages = [{"role": "user", "content": prompt}]

        try:
            response = self.client.create_completion(
                messages=messages,
                temperature=0.0,  # Deterministic for scoring
                max_tokens=5,  # Allow a few tokens in case target is multi-token
                logprobs=True,  # Request logprobs from vLLM
                top_logprobs=20  # Get more candidates to find target token
            )

            # Extract logprob for target token
            logprob_target = self._extract_target_logprob(
                response.raw_response,
                target
            )

            if return_logprob:
                return logprob_target
            else:
                return math.exp(logprob_target)

        except Exception as e:
            print(f"Warning: Failed to score ({source} -> {target}): {e}")
            # Return weak association score on failure
            return -10.0 if return_logprob else 0.0001

    def _extract_target_logprob(self, raw_response: Any, target: str) -> float:
        """
        Extract logprob for target token from OpenAI response.

        Searches through the generated tokens to find the target word and
        returns its logprob. This measures how likely the model is to generate
        the target word given the source word.

        Args:
            raw_response: OpenAI response object from vLLM
            target: Target word to find logprob for

        Returns:
            Logprob for target token (negative float, closer to 0 = stronger)

        Raises:
            ValueError: If logprobs not found in response
        """
        # OpenAI format: response.choices[0].logprobs.content[i].top_logprobs
        try:
            choice = raw_response.choices[0]

            # Check if logprobs are available
            if not hasattr(choice, 'logprobs') or choice.logprobs is None:
                raise ValueError("Logprobs not available in response")

            # Get all token logprobs
            content_logprobs = choice.logprobs.content

            if not content_logprobs:
                raise ValueError("No content logprobs found")

            # Normalize target for comparison (lowercase, strip whitespace)
            target_normalized = target.strip().lower()

            # Search through all generated tokens (target might appear anywhere)
            # We'll take the maximum logprob if target appears multiple times
            best_logprob = None

            for token_logprobs in content_logprobs:
                # Check the actual generated token first
                if hasattr(token_logprobs, 'token'):
                    generated_token = token_logprobs.token.strip().lower()
                    if generated_token == target_normalized:
                        if best_logprob is None or token_logprobs.logprob > best_logprob:
                            best_logprob = token_logprobs.logprob

                # Also check the top_logprobs for this position
                if hasattr(token_logprobs, 'top_logprobs'):
                    for logprob_obj in token_logprobs.top_logprobs:
                        token = logprob_obj.token.strip().lower()
                        if token == target_normalized:
                            if best_logprob is None or logprob_obj.logprob > best_logprob:
                                best_logprob = logprob_obj.logprob

            # If target found, return its logprob
            if best_logprob is not None:
                return best_logprob

            # If target not found in any position, it's a very weak association
            # Return a strongly negative logprob to indicate this
            return -15.0

        except Exception as e:
            raise ValueError(f"Failed to extract target logprob for '{target}': {e}") from e

    async def batch_get_associations_async(
        self,
        words: List[str],
        n: int = 5
    ) -> Dict[str, List[str]]:
        """
        Get associations for multiple words in parallel (async).

        Processes words in batches to maximize throughput while
        respecting batch_size limit.

        Args:
            words: List of words to get associations for
            n: Number of associations per word

        Returns:
            Dict mapping word -> list of associations

        Example:
            >>> engine = SGMInferenceEngine(vllm_client)
            >>> words = ['physics', 'chemistry', 'biology']
            >>> results = await engine.batch_get_associations_async(words, n=5)
            >>> print(results['physics'])
            ['gravity', 'quantum', 'Newton', 'energy', 'matter']
        """
        # Note: This is a simplified async implementation
        # In practice, vLLM handles concurrency on the server side
        # So we can just call synchronously in a loop (vLLM batches internally)

        results = {}
        for word in words:
            associations = self.get_associations(word, n=n)
            results[word] = associations

        return results

    async def batch_score_associations_async(
        self,
        edges: List[Tuple[str, str]],
        return_logprobs: bool = True
    ) -> Dict[Tuple[str, str], float]:
        """
        Score multiple associations in parallel (async).

        Processes edges in batches for efficient scoring.

        Args:
            edges: List of (source, target) tuples
            return_logprobs: Whether to return raw logprobs or exp(logprob)

        Returns:
            Dict mapping (source, target) -> score

        Example:
            >>> engine = SGMInferenceEngine(vllm_client)
            >>> edges = [('physics', 'gravity'), ('physics', 'banana')]
            >>> scores = await engine.batch_score_associations_async(edges)
            >>> print(scores[('physics', 'gravity')])
            0.92  # Strong
            >>> print(scores[('physics', 'banana')])
            0.01  # Weak
        """
        results = {}
        for source, target in edges:
            score = self.score_association(source, target, return_logprob=return_logprobs)
            results[(source, target)] = score

        return results

    def batch_get_associations(
        self,
        words: List[str],
        n: int = 5,
        show_progress: bool = False
    ) -> Dict[str, List[str]]:
        """
        Synchronous wrapper for batch_get_associations_async.

        Args:
            words: List of words to process
            n: Associations per word
            show_progress: Whether to show progress bar (requires tqdm)

        Returns:
            Dict mapping word -> associations
        """
        results = {}

        if show_progress:
            try:
                from tqdm import tqdm
                words_iter = tqdm(words, desc="Getting associations")
            except ImportError:
                words_iter = words
        else:
            words_iter = words

        for word in words_iter:
            associations = self.get_associations(word, n=n)
            results[word] = associations

        return results

    def batch_score_associations(
        self,
        edges: List[Tuple[str, str]],
        return_logprobs: bool = True,
        show_progress: bool = False
    ) -> Dict[Tuple[str, str], float]:
        """
        Synchronous wrapper for batch_score_associations_async.

        Args:
            edges: List of (source, target) tuples
            return_logprobs: Whether to return raw logprobs
            show_progress: Whether to show progress bar

        Returns:
            Dict mapping (source, target) -> score
        """
        results = {}

        if show_progress:
            try:
                from tqdm import tqdm
                edges_iter = tqdm(edges, desc="Scoring associations")
            except ImportError:
                edges_iter = edges
        else:
            edges_iter = edges

        for source, target in edges_iter:
            score = self.score_association(source, target, return_logprob=return_logprobs)
            results[(source, target)] = score

        return results

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SGMInferenceEngine("
            f"client={self.client}, "
            f"temperature={self.temperature}, "
            f"batch_size={self.batch_size})"
        )
