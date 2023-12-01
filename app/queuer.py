from dotenv import dotenv_values
import requests

from app import __version__
from app.logging import get_logger
from app.transcript import Transcript
from app.utils import write_to_json


logger = get_logger()


class Queuer:
    def __init__(self, test_mode=False):
        if not test_mode:
            self._config_endpoint()

    def _config_endpoint(self):
        config = dotenv_values(".env")
        if "QUEUE_ENDPOINT" not in config:
            raise Exception(
                "To push to a queue you need to define a 'QUEUE_ENDPOINT' in your .env file")
        if "BEARER_TOKEN" not in config:
            raise Exception(
                "To push to a queue you need to define a 'BEARER_TOKEN' in your .env file")
        self.url = config["QUEUE_ENDPOINT"] + "/api/transcripts"
        self.headers = {
            'Authorization': f'Bearer {config["BEARER_TOKEN"]}',
            'Content-Type': 'application/json'
        }

    def push_to_queue(self, transcript_json):
        """Push the payload with the resulting transcript to the Queuer backend"""
        try:
            payload = {
                "content": transcript_json
            }
            response = requests.post(
                self.url, json=payload, headers=self.headers)
            if response.status_code == 200:
                logger.info(
                    f"Transcript added to queue with id={response.json()['id']}")
            else:
                logger.error(
                    f"Transcript not added to queue: ({response.status_code}) {response.text}")
            return response
        except Exception as e:
            logger.error(f"Transcript not added to queue: {e}")
