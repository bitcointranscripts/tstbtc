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
    def QUEUE_ENDPOINT(self):
        return self._get_env_variable('QUEUE_ENDPOINT')

    @property
    def BEARER_TOKEN(self):
        return self._get_env_variable('BEARER_TOKEN')

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

# Initialize the Settings class and expose an instance
settings = Settings()

__all__ = ['settings']
