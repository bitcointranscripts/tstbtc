from app.transcript import Transcript
from app.logging import get_logger
import openai
from app.config import settings

logger = get_logger()

class SummarizerService:
    def __init__(self, provider='openai', model='gpt-4o'):
        self.provider = provider
        self.model = model
        if self.provider == 'openai':
            self.client = openai
            self.client.api_key = settings.OPENAI_API_KEY
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def process(self, transcript: Transcript, **kwargs):
        logger.info(f"Summarizing transcript with {self.provider}...")
        text_to_summarize = transcript.outputs.get('corrected_text', transcript.outputs['raw'])
        
        prompt = f"""Please summarize the following text.\n---\n{text_to_summarize}"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        summary = response.choices[0].message.content
        transcript.summary = summary
        logger.info("Summarization complete.")
