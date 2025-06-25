import os
import base64
import configparser
from dotenv import load_dotenv

def read_config(profile):
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config[profile]

class Settings:
    def __init__(self):
        # Reload environment variables from .env file
        load_dotenv(override=True)

        # server
        self.TSTBTC_METADATA_DIR = os.getenv('TSTBTC_METADATA_DIR')
        # GitHub API settings
        self.GITHUB_REPO_OWNER = os.getenv('GITHUB_REPO_OWNER', 'bitcointranscripts')
        self.GITHUB_REPO_NAME = os.getenv('GITHUB_REPO_NAME', 'bitcointranscripts')
        self.GITHUB_METADATA_REPO_NAME = os.getenv('GITHUB_METADATA_REPO_NAME', 'bitcointranscripts-metadata')

        # cli
        self.TRANSCRIPTION_SERVER_URL = os.getenv('TRANSCRIPTION_SERVER_URL')

        # Load configuration from config.ini
        self.PROFILE = os.getenv('PROFILE', 'DEFAULT')
        self.config = read_config(self.PROFILE)

    def get_config_overview(self):
        overview = "Configuration Settings:\n"
        overview += f"PROFILE: {self.PROFILE}\n"
        overview += f"TSTBTC_METADATA_DIR: {self.TSTBTC_METADATA_DIR}\n"
        overview += f"GITHUB_REPO_OWNER: {self.GITHUB_REPO_OWNER}\n"
        overview += f"GITHUB_REPO_NAME: {self.GITHUB_REPO_NAME}\n"
        overview += f"GITHUB_METADATA_REPO_NAME: {self.GITHUB_METADATA_REPO_NAME}\n"
        overview += f"TRANSCRIPTION_SERVER_URL: {self.TRANSCRIPTION_SERVER_URL}\n"
        overview += f"BTC_TRANSCRIPTS_URL: {self.BTC_TRANSCRIPTS_URL}\n"
        overview += f"GEMINI_API_KEY: {'[SET]' if self.GEMINI_API_KEY else '[NOT SET]'}\n"
        overview += f"OPENAI_API_KEY: {'[SET]' if self.OPENAI_API_KEY else '[NOT SET]'}\n"
        overview += f"ANTHROPIC_API_KEY: {'[SET]' if self.ANTHROPIC_API_KEY else '[NOT SET]'}\n"
        overview += f"DEFAULT_SUMMARY_PROVIDER: {self.DEFAULT_SUMMARY_PROVIDER}\n"
        overview += f"DEFAULT_GEMINI_MODEL: {self.DEFAULT_GEMINI_MODEL}\n"
        overview += f"DEFAULT_OPENAI_MODEL: {self.DEFAULT_OPENAI_MODEL}\n"
        overview += f"DEFAULT_CLAUDE_MODEL: {self.DEFAULT_CLAUDE_MODEL}\n"
            
        # Add config.ini settings
        overview += "\nSettings from config.ini:\n"
        for key, value in self.config.items():
            overview += f"{key}: {value}\n"
        
        return overview

    @staticmethod
    def _get_env_variable(var_name, custom_message=None):
        value = os.getenv(var_name)
        if not value:
            error_message = custom_message or \
                f"{var_name} is not set in the environment or .env file. Please set it and restart the server."
            raise Exception(error_message)
        return value

    @property
    def DEEPGRAM_API_KEY(self):
        return self._get_env_variable('DEEPGRAM_API_KEY',
            "To use Deepgram as a transcription service you need to define a 'DEEPGRAM_API_KEY' in your .env file")

    @property
    def BTC_TRANSCRIPTS_URL(self):
        return self._get_env_variable('BTC_TRANSCRIPTS_URL')

    @property
    def S3_BUCKET(self):
        return self._get_env_variable('S3_BUCKET')

    @property
    def GITHUB_APP_ID(self):
        return self._get_env_variable('GITHUB_APP_ID',
            "To use GitHub App integration, you need to define a 'GITHUB_APP_ID' in your .env file")

    @property
    def GITHUB_PRIVATE_KEY(self):
        return base64.b64decode(self._get_env_variable('GITHUB_PRIVATE_KEY_BASE64',
            "To use GitHub App integration, you need to define a 'GITHUB_PRIVATE_KEY' in your .env file")).decode('utf-8')

    @property
    def GITHUB_INSTALLATION_ID(self):
        return self._get_env_variable('GITHUB_INSTALLATION_ID',
            "To use GitHub App integration, you need to define a 'GITHUB_INSTALLATION_ID' in your .env file")
    # Add these properties to the Settings class in app/config.py

    @property
    def GEMINI_API_KEY(self):
        # First check environment, then config file
        return os.getenv('GEMINI_API_KEY') or self.config.get('gemini_api_key', '')

    @property
    def OPENAI_API_KEY(self):
        return os.getenv('OPENAI_API_KEY') or self.config.get('openai_api_key', '')

    @property
    def ANTHROPIC_API_KEY(self):
        return os.getenv('ANTHROPIC_API_KEY') or self.config.get('anthropic_api_key', '')

    @property
    def DEFAULT_SUMMARY_PROVIDER(self):
        return os.getenv('DEFAULT_SUMMARY_PROVIDER') or self.config.get('default_summary_provider', 'gemini')

    @property
    def DEFAULT_GEMINI_MODEL(self):
        return os.getenv('DEFAULT_GEMINI_MODEL') or self.config.get('default_gemini_model', 'gemma-3-27b-it')

    @property
    def DEFAULT_OPENAI_MODEL(self):
        return os.getenv('DEFAULT_OPENAI_MODEL') or self.config.get('default_openai_model', 'gpt-4o')

    @property
    def DEFAULT_CLAUDE_MODEL(self):
        return os.getenv('DEFAULT_CLAUDE_MODEL') or self.config.get('default_claude_model', 'claude-3-7-sonnet-20250219')
# Initialize the Settings class and expose an instance
settings = Settings()

__all__ = ['settings']
