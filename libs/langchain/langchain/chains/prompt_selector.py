from abc import ABC, abstractmethod
from typing import Callable, List, Tuple

from pydantic import BaseModel, Field

from langchain.chat_models.base import BaseChatModel
from langchain.llms.base import BaseLLM
from langchain.schema import BasePromptTemplate
from langchain.schema.language_model import BaseLanguageModel


class BasePromptSelector(BaseModel, ABC):
    """Base class for prompt selectors."""

    @abstractmethod
    def get_prompt(self, llm: BaseLanguageModel) -> BasePromptTemplate:
        """Get default prompt for a language model."""


class ConditionalPromptSelector(BasePromptSelector):
    """Prompt collection that goes through conditionals."""

    default_prompt: BasePromptTemplate
    """Default prompt to use if no conditionals match."""
    conditionals: List[
        Tuple[Callable[[BaseLanguageModel], bool], BasePromptTemplate]
    ] = Field(default_factory=list)
    """List of conditionals and prompts to use if the conditionals match."""

    def get_prompt(self, llm: BaseLanguageModel) -> BasePromptTemplate:
        """Get default prompt for a language model.

        Args:
            llm: Language model to get prompt for.

        Returns:
            Prompt to use for the language model.
        """
        return next(
            (prompt for condition, prompt in self.conditionals if condition(llm)),
            self.default_prompt,
        )


def is_llm(llm: BaseLanguageModel) -> bool:
    """Check if the language model is a LLM.

    Args:
        llm: Language model to check.

    Returns:
        True if the language model is a BaseLLM model, False otherwise.
    """
    return isinstance(llm, BaseLLM)


def is_chat_model(llm: BaseLanguageModel) -> bool:
    """Check if the language model is a chat model.

    Args:
        llm: Language model to check.

    Returns:
        True if the language model is a BaseChatModel model, False otherwise.
    """
    return isinstance(llm, BaseChatModel)
