"""Chain that implements the ReAct paper from https://arxiv.org/pdf/2210.03629.pdf."""
from typing import Any, List, Optional, Sequence

from pydantic import Field

from langchain.agents.agent import Agent, AgentExecutor, AgentOutputParser
from langchain.agents.agent_types import AgentType
from langchain.agents.react.output_parser import ReActOutputParser
from langchain.agents.react.textworld_prompt import TEXTWORLD_PROMPT
from langchain.agents.react.wiki_prompt import WIKI_PROMPT
from langchain.agents.tools import Tool
from langchain.agents.utils import validate_tools_single_input
from langchain.docstore.base import Docstore
from langchain.docstore.document import Document
from langchain.schema import BasePromptTemplate
from langchain.schema.language_model import BaseLanguageModel
from langchain.tools.base import BaseTool


class ReActDocstoreAgent(Agent):
    """Agent for the ReAct chain."""

    output_parser: AgentOutputParser = Field(default_factory=ReActOutputParser)

    @classmethod
    def _get_default_output_parser(cls, **kwargs: Any) -> AgentOutputParser:
        return ReActOutputParser()

    @property
    def _agent_type(self) -> str:
        """Return Identifier of an agent type."""
        return AgentType.REACT_DOCSTORE

    @classmethod
    def create_prompt(cls, tools: Sequence[BaseTool]) -> BasePromptTemplate:
        """Return default prompt."""
        return WIKI_PROMPT

    @classmethod
    def _validate_tools(cls, tools: Sequence[BaseTool]) -> None:
        validate_tools_single_input(cls.__name__, tools)
        super()._validate_tools(tools)
        if len(tools) != 2:
            raise ValueError(f"Exactly two tools must be specified, but got {tools}")
        tool_names = {tool.name for tool in tools}
        if tool_names != {"Lookup", "Search"}:
            raise ValueError(
                f"Tool names should be Lookup and Search, got {tool_names}"
            )

    @property
    def observation_prefix(self) -> str:
        """Prefix to append the observation with."""
        return "Observation: "

    @property
    def _stop(self) -> List[str]:
        return ["\nObservation:"]

    @property
    def llm_prefix(self) -> str:
        """Prefix to append the LLM call with."""
        return "Thought:"


class DocstoreExplorer:
    """Class to assist with exploration of a document store."""

    def __init__(self, docstore: Docstore):
        """Initialize with a docstore, and set initial document to None."""
        self.docstore = docstore
        self.document: Optional[Document] = None
        self.lookup_str = ""
        self.lookup_index = 0

    def search(self, term: str) -> str:
        """Search for a term in the docstore, and if found save."""
        result = self.docstore.search(term)
        if isinstance(result, Document):
            self.document = result
            return self._summary
        else:
            self.document = None
            return result

    def lookup(self, term: str) -> str:
        """Lookup a term in document (if saved)."""
        if self.document is None:
            raise ValueError("Cannot lookup without a successful search first")
        if term.lower() != self.lookup_str:
            self.lookup_str = term.lower()
            self.lookup_index = 0
        else:
            self.lookup_index += 1
        lookups = [p for p in self._paragraphs if self.lookup_str in p.lower()]
        if not lookups:
            return "No Results"
        elif self.lookup_index >= len(lookups):
            return "No More Results"
        else:
            result_prefix = f"(Result {self.lookup_index + 1}/{len(lookups)})"
            return f"{result_prefix} {lookups[self.lookup_index]}"

    @property
    def _summary(self) -> str:
        return self._paragraphs[0]

    @property
    def _paragraphs(self) -> List[str]:
        if self.document is None:
            raise ValueError("Cannot get paragraphs without a document")
        return self.document.page_content.split("\n\n")


class ReActTextWorldAgent(ReActDocstoreAgent):
    """Agent for the ReAct TextWorld chain."""

    @classmethod
    def create_prompt(cls, tools: Sequence[BaseTool]) -> BasePromptTemplate:
        """Return default prompt."""
        return TEXTWORLD_PROMPT

    @classmethod
    def _validate_tools(cls, tools: Sequence[BaseTool]) -> None:
        validate_tools_single_input(cls.__name__, tools)
        super()._validate_tools(tools)
        if len(tools) != 1:
            raise ValueError(f"Exactly one tool must be specified, but got {tools}")
        tool_names = {tool.name for tool in tools}
        if tool_names != {"Play"}:
            raise ValueError(f"Tool name should be Play, got {tool_names}")


class ReActChain(AgentExecutor):
    """Chain that implements the ReAct paper.

    Example:
        .. code-block:: python

            from langchain import ReActChain, OpenAI
            react = ReAct(llm=OpenAI())
    """

    def __init__(self, llm: BaseLanguageModel, docstore: Docstore, **kwargs: Any):
        """Initialize with the LLM and a docstore."""
        docstore_explorer = DocstoreExplorer(docstore)
        tools = [
            Tool(
                name="Search",
                func=docstore_explorer.search,
                description="Search for a term in the docstore.",
            ),
            Tool(
                name="Lookup",
                func=docstore_explorer.lookup,
                description="Lookup a term in the docstore.",
            ),
        ]
        agent = ReActDocstoreAgent.from_llm_and_tools(llm, tools)
        super().__init__(agent=agent, tools=tools, **kwargs)
