from typing import Any, Dict, List, Mapping, Optional, Tuple

import requests
from pydantic import BaseModel, Extra, root_validator

from langchain.embeddings.base import Embeddings
from langchain.utils import get_from_dict_or_env


class MosaicMLInstructorEmbeddings(BaseModel, Embeddings):
    """MosaicML embedding service.

    To use, you should have the
    environment variable ``MOSAICML_API_TOKEN`` set with your API token, or pass
    it as a named parameter to the constructor.

    Example:
        .. code-block:: python

            from langchain.llms import MosaicMLInstructorEmbeddings
            endpoint_url = (
                "https://models.hosted-on.mosaicml.hosting/instructor-large/v1/predict"
            )
            mosaic_llm = MosaicMLInstructorEmbeddings(
                endpoint_url=endpoint_url,
                mosaicml_api_token="my-api-key"
            )
    """

    endpoint_url: str = (
        "https://models.hosted-on.mosaicml.hosting/instructor-xl/v1/predict"
    )
    """Endpoint URL to use."""
    embed_instruction: str = "Represent the document for retrieval: "
    """Instruction used to embed documents."""
    query_instruction: str = (
        "Represent the question for retrieving supporting documents: "
    )
    """Instruction used to embed the query."""
    retry_sleep: float = 1.0
    """How long to try sleeping for if a rate limit is encountered"""

    mosaicml_api_token: Optional[str] = None

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate that api key and python package exists in environment."""
        mosaicml_api_token = get_from_dict_or_env(
            values, "mosaicml_api_token", "MOSAICML_API_TOKEN"
        )
        values["mosaicml_api_token"] = mosaicml_api_token
        return values

    @property
    def _identifying_params(self) -> Mapping[str, Any]:
        """Get the identifying parameters."""
        return {"endpoint_url": self.endpoint_url}

    def _embed(
        self, input: List[Tuple[str, str]], is_retry: bool = False
    ) -> List[List[float]]:
        payload = {"input_strings": input}

        # HTTP headers for authorization
        headers = {
            "Authorization": f"{self.mosaicml_api_token}",
            "Content-Type": "application/json",
        }

        # send request
        try:
            response = requests.post(self.endpoint_url, headers=headers, json=payload)
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error raised by inference endpoint: {e}")

        try:
            parsed_response = response.json()

            if "error" in parsed_response:
                # if we get rate limited, try sleeping for 1 second
                if (
                    not is_retry
                    and "rate limit exceeded" in parsed_response["error"].lower()
                ):
                    import time

                    time.sleep(self.retry_sleep)

                    return self._embed(input, is_retry=True)

                raise ValueError(
                    f"Error raised by inference API: {parsed_response['error']}"
                )

            # The inference API has changed a couple of times, so we add some handling
            # to be robust to multiple response formats.
            if isinstance(parsed_response, dict):
                if "data" in parsed_response:
                    output_item = parsed_response["data"]
                elif "output" in parsed_response:
                    output_item = parsed_response["output"]
                else:
                    raise ValueError(
                        f"No key data or output in response: {parsed_response}"
                    )

                if isinstance(output_item, list) and isinstance(output_item[0], list):
                    embeddings = output_item
                else:
                    embeddings = [output_item]
            elif isinstance(parsed_response, list):
                first_item = parsed_response[0]
                if isinstance(first_item, list):
                    embeddings = parsed_response
                elif isinstance(first_item, dict):
                    if "output" in first_item:
                        embeddings = [item["output"] for item in parsed_response]
                    else:
                        raise ValueError(
                            f"No key data or output in response: {parsed_response}"
                        )
                else:
                    raise ValueError(f"Unexpected response format: {parsed_response}")
            else:
                raise ValueError(f"Unexpected response type: {parsed_response}")

        except requests.exceptions.JSONDecodeError as e:
            raise ValueError(
                f"Error raised by inference API: {e}.\nResponse: {response.text}"
            )

        return embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents using a MosaicML deployed instructor embedding model.

        Args:
            texts: The list of texts to embed.

        Returns:
            List of embeddings, one for each text.
        """
        instruction_pairs = [(self.embed_instruction, text) for text in texts]
        return self._embed(instruction_pairs)

    def embed_query(self, text: str) -> List[float]:
        """Embed a query using a MosaicML deployed instructor embedding model.

        Args:
            text: The text to embed.

        Returns:
            Embeddings for the text.
        """
        instruction_pair = (self.query_instruction, text)
        return self._embed([instruction_pair])[0]
