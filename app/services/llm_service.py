from abc import ABC, abstractmethod
import openai
from app.config import settings

class BaseLLM(ABC):
    @abstractmethod
    def correct_transcript(self, transcript_text: str, model: str) -> str:
        pass

    @abstractmethod
    def summarize_text(self, text: str, model: str) -> str:
        pass

class OpenAI_LLM(BaseLLM):
    def __init__(self, api_key):
        openai.api_key = api_key

    def correct_transcript(self, transcript_text: str, model: str) -> str:
        prompt = f"""Please correct the following transcript for punctuation, grammar, and spelling. Do not change the content.
        ---
        {transcript_text}"""
        
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def summarize_text(self, text: str, model: str) -> str:
        prompt = f"""Please summarize the following text.
        ---
        {text}"""
        
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

class LLMFactory:
    @staticmethod
    def create_llm_service(provider: str) -> BaseLLM:
        if provider == "openai":
            return OpenAI_LLM(api_key=settings.OPENAI_API_KEY)
        # Add other providers here
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
