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
        
        metadata = transcript.source.to_json()

        prompt = self._build_prompt(transcript.outputs['raw'], keywords, metadata)

        # Call the LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        corrected_text = response.choices[0].message.content
        
        # Store the corrected text in a new field
        transcript.outputs['corrected_text'] = corrected_text
        logger.info("Correction complete.")

    def _build_prompt(self, text, keywords, metadata):
        prompt = (
            "You are a domain expert in Bitcoin and blockchain technologies.\n\n"
            "The following transcript was generated using an automatic speech recognition (ASR) system. "
            "Your task is to correct it based on the contextual metadata provided.\n\n"
            "--- Contextual Metadata ---\n"
        )

        if metadata.get('title'):
            prompt += f"Title: {metadata['title']}\n"
        if metadata.get('speakers'):
            prompt += f"Speakers: {', '.join(metadata['speakers'])}\n"
        if metadata.get('tags'):
            prompt += f"Tags: {', '.join(metadata['tags'])}\n"
        
        prompt += "Please use this metadata to improve the accuracy of your corrections.\n"

        if keywords:
            prompt += (
                "\nAdditionally, prioritize the following keywords. Ensure they are spelled, cased, and formatted correctly "
                "whenever they appear in the transcript:\n- "
            )
            prompt += "\n- ".join(keywords)

        prompt += f"\n\n--- Transcript Start ---\n\n{text.strip()}\n\n--- Transcript End ---"
        return prompt
