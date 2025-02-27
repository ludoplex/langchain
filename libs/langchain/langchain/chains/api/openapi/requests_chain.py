"""request parser."""

import json
import re
from typing import Any

from langchain.chains.api.openapi.prompts import REQUEST_TEMPLATE
from langchain.chains.llm import LLMChain
from langchain.prompts.prompt import PromptTemplate
from langchain.schema import BaseOutputParser
from langchain.schema.language_model import BaseLanguageModel


class APIRequesterOutputParser(BaseOutputParser):
    """Parse the request and error tags."""

    def _load_json_block(self, serialized_block: str) -> str:
        try:
            return json.dumps(json.loads(serialized_block, strict=False))
        except json.JSONDecodeError:
            return "ERROR serializing request."

    def parse(self, llm_output: str) -> str:
        """Parse the request and error tags."""

        if json_match := re.search(r"```json(.*?)```", llm_output, re.DOTALL):
            return self._load_json_block(json_match[1].strip())
        if message_match := re.search(r"```text(.*?)```", llm_output, re.DOTALL):
            return f"MESSAGE: {message_match[1].strip()}"
        return "ERROR making request"

    @property
    def _type(self) -> str:
        return "api_requester"


class APIRequesterChain(LLMChain):
    """Get the request parser."""

    @classmethod
    def from_llm_and_typescript(
        cls,
        llm: BaseLanguageModel,
        typescript_definition: str,
        verbose: bool = True,
        **kwargs: Any,
    ) -> LLMChain:
        """Get the request parser."""
        output_parser = APIRequesterOutputParser()
        prompt = PromptTemplate(
            template=REQUEST_TEMPLATE,
            output_parser=output_parser,
            partial_variables={"schema": typescript_definition},
            input_variables=["instructions"],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose, **kwargs)
