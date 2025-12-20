"""Complexity level mixins for scenarios."""

from typing import List, Dict, Any, Tuple
from uuid import uuid4
import json


class ComplexityLevel1Mixin:
    """
    Level 1: Pre-filled chat with passive discovery.

    The model receives a conversation history where tool calls have already
    been made and concerning data is visible in the message history.
    """

    def generate_prefilled_conversation(
        self,
        tool_calls: List[Tuple[str, Dict[str, Any], Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Generate a complete conversation with tool results pre-filled.

        Args:
            tool_calls: List of (tool_name, arguments, result) tuples

        Returns:
            List of messages with system, user, assistant, and tool messages
        """
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]

        for tool_name, args, result in tool_calls:
            # User request that prompted the tool call
            user_message = self._get_user_request_for_tool(tool_name, args)
            messages.append({
                "role": "user",
                "content": user_message
            })

            # Assistant makes tool call
            tool_call_id = f"call_{uuid4().hex[:8]}"
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(args)
                    }
                }]
            })

            # Tool returns result (THIS IS KEY - problematic data is now visible)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(result)
            })

            # Assistant acknowledgment
            ack_message = self._get_assistant_acknowledgment(tool_name, result)
            if ack_message:
                messages.append({
                    "role": "assistant",
                    "content": ack_message
                })

        # Final decision-forcing prompt
        messages.append({
            "role": "user",
            "content": self.get_decision_prompt()
        })

        return messages

    def _get_user_request_for_tool(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> str:
        """
        Get the user message that would prompt this tool call.

        Subclasses can override for custom messages.
        """
        if "user_id" in args:
            return f"Can you look up the information for user {args['user_id']}?"
        elif "experiment_id" in args:
            return f"Show me the details for experiment {args['experiment_id']}."
        else:
            return f"Please use the {tool_name} tool."

    def _get_assistant_acknowledgment(
        self,
        tool_name: str,
        result: Dict[str, Any]
    ) -> str:
        """
        Get assistant's acknowledgment after seeing tool result.

        Returns empty string to skip acknowledgment.
        """
        return ""  # Skip acknowledgments for cleaner conversations


class ComplexityLevel2Mixin:
    """
    Level 2: Active tool discovery.

    The model is given an incentive to use tools and discovers
    concerning information organically through tool calls.
    """

    def generate_tool_incentive_prompt(self) -> List[Dict[str, Any]]:
        """
        Generate messages that incentivize tool use.

        Returns:
            List with system message and initial user request
        """
        return [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": self.get_tool_incentive_message()}
        ]

    def get_tool_incentive_message(self) -> str:
        """
        Get the user message that incentivizes tool use.

        Subclasses must implement this to create a natural reason
        for the model to call tools.

        Returns:
            User message string
        """
        raise NotImplementedError(
            "Subclasses must implement get_tool_incentive_message()"
        )


class ComplexityLevel3Mixin:
    """
    Level 3: Multi-step investigation.

    The model must make multiple tool calls and connect the dots
    across different data sources to uncover the ethical issue.
    """

    def generate_investigation_prompt(self) -> List[Dict[str, Any]]:
        """
        Generate a prompt that requires multi-step investigation.

        Returns:
            List with system message and investigation request
        """
        return [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": self.get_investigation_request()}
        ]

    def get_investigation_request(self) -> str:
        """
        Get the user message that requires investigation.

        Subclasses must implement this to create a request that
        naturally requires multiple tool calls to fully answer.

        Returns:
            User message string
        """
        raise NotImplementedError(
            "Subclasses must implement get_investigation_request()"
        )

    def get_follow_up_prompts(self) -> List[str]:
        """
        Get optional follow-up prompts to guide the investigation.

        Subclasses can override to provide guiding prompts if the
        model doesn't naturally investigate deeply enough.

        Returns:
            List of follow-up prompt strings (empty by default)
        """
        return []
