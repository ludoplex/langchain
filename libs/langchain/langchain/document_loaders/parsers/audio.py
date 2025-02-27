import time
from typing import Iterator, Optional

from langchain.document_loaders.base import BaseBlobParser
from langchain.document_loaders.blob_loaders import Blob
from langchain.schema import Document


class OpenAIWhisperParser(BaseBlobParser):
    """Transcribe and parse audio files.
    Audio transcription is with OpenAI Whisper model."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def lazy_parse(self, blob: Blob) -> Iterator[Document]:
        """Lazily parse the blob."""

        import io

        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package not found, please install it with "
                "`pip install openai`"
            )
        try:
            from pydub import AudioSegment
        except ImportError:
            raise ImportError(
                "pydub package not found, please install it with " "`pip install pydub`"
            )

        # Set the API key if provided
        if self.api_key:
            openai.api_key = self.api_key

        # Audio file from disk
        audio = AudioSegment.from_file(blob.path)

        # Define the duration of each chunk in minutes
        # Need to meet 25MB size limit for Whisper API
        chunk_duration = 20
        chunk_duration_ms = chunk_duration * 60 * 1000

        # Split the audio into chunk_duration_ms chunks
        for split_number, i in enumerate(range(0, len(audio), chunk_duration_ms)):
            # Audio chunk
            chunk = audio[i : i + chunk_duration_ms]
            file_obj = io.BytesIO(chunk.export(format="mp3").read())
            if blob.source is not None:
                file_obj.name = f"{blob.source}_part_{split_number}.mp3"
            else:
                file_obj.name = f"part_{split_number}.mp3"

            # Transcribe
            print(f"Transcribing part {split_number+1}!")
            attempts = 0
            while attempts < 3:
                try:
                    transcript = openai.Audio.transcribe("whisper-1", file_obj)
                    break
                except Exception as e:
                    attempts += 1
                    print(f"Attempt {attempts} failed. Exception: {str(e)}")
                    time.sleep(5)
            else:
                print("Failed to transcribe after 3 attempts.")
                continue

            yield Document(
                page_content=transcript.text,
                metadata={"source": blob.source, "chunk": split_number},
            )


class OpenAIWhisperParserLocal(BaseBlobParser):
    """Transcribe and parse audio files.
    Audio transcription is with OpenAI Whisper model locally from transformers
    NOTE: By default uses the gpu if available, if you want to use cpu,
    please set device = "cpu"
    """

    def __init__(self, device: str = "0", lang_model: Optional[str] = None):
        try:
            from transformers import pipeline
        except ImportError:
            raise ImportError(
                "transformers package not found, please install it with "
                "`pip install transformers`"
            )
        try:
            import torch
        except ImportError:
            raise ImportError(
                "torch package not found, please install it with " "`pip install torch`"
            )

        # set device, cpu by default check if there is a GPU available
        if device == "cpu":
            self.device = "cpu"
            if lang_model is None:
                # unless overridden, use the small base model on cpu
                self.lang_model = "openai/whisper-base"
            else:
                self.lang_model = lang_model
                print("WARNING! Model override. Using model: ", self.lang_model)
        elif torch.cuda.is_available():
            self.device = "cuda:0"
            # check GPU memory and select automatically the model
            mem = torch.cuda.get_device_properties(self.device).total_memory / (
                1024**2
            )
            if mem < 5000:
                rec_model = "openai/whisper-base"
            elif mem < 7000:
                rec_model = "openai/whisper-small"
            elif mem < 12000:
                rec_model = "openai/whisper-medium"
            else:
                rec_model = "openai/whisper-large"

            # check if model is overridden
            if lang_model is not None:
                self.lang_model = lang_model
                print("WARNING! Model override. Might not fit in your GPU")
            else:
                self.lang_model = rec_model
        else:
            "cpu"

        print("Using the following model: ", self.lang_model)

        # load model for inference
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model="openai/whisper-medium",
            chunk_length_s=30,
            device=self.device,
        )

    def lazy_parse(self, blob: Blob) -> Iterator[Document]:
        """Lazily parse the blob."""

        import io

        try:
            from pydub import AudioSegment
        except ImportError:
            raise ValueError(
                "pydub package not found, please install it with " "`pip install pydub`"
            )

        try:
            import librosa
        except ImportError:
            raise ValueError(
                "librosa package not found, please install it with "
                "`pip install librosa`"
            )

        # Audio file from disk
        audio = AudioSegment.from_file(blob.path)

        file_obj = io.BytesIO(audio.export(format="mp3").read())

        # Transcribe
        print(f"Transcribing part {blob.path}!")

        y, sr = librosa.load(file_obj, sr=16000)

        prediction = self.pipe(y.copy(), batch_size=8)["text"]

        yield Document(
            page_content=prediction,
            metadata={"source": blob.source},
        )
