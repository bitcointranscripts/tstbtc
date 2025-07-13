from app.transcript import Transcript
from app.logging import get_logger
import openai
from app.config import settings

logger = get_logger()

class CorrectionService:
    def __init__(self, provider='openai', model='gpt-4o'):
        self.provider = provider
        self.model = model
        if self.provider == 'openai':
            self.client = openai
            self.client.api_key = settings.OPENAI_API_KEY
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def process(self, transcript: Transcript, **kwargs):
        logger.info(f"Correcting transcript with {self.provider}...")
        keywords = kwargs.get('keywords', [])
        
        # Build the prompt
        prompt = self._build_prompt(transcript.outputs['raw'], keywords)

        # Call the LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        corrected_text = response.choices[0].message.content
        
        # Store the corrected text in a new field
        transcript.outputs['corrected_text'] = corrected_text
        logger.info("Correction complete.")

    def _build_prompt(self, text, keywords):
        prompt = "Please correct the following transcript for punctuation, grammar, and spelling. Do not change the content or the speaker labels."
        if keywords:
            prompt += "\n\nPlease pay special attention to the following keywords and ensure they are spelled correctly:\n- "
            prompt += "\n- ".join(keywords)
        prompt += f"\n\n---\n\n{text}"
        return prompt
