# config.py

import os
from google.cloud import storage
import json

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        self.env = os.getenv('ENVIRONMENT', 'development')
        self.project_id = os.getenv('PROJECT_ID')
        self.bland_api_key = os.getenv('')
        self.storage_client = storage.Client()
        self.config_bucket = os.getenv('CONFIG_BUCKET')
        self.load_config()

    def load_config(self):
        blob = self.storage_client.bucket(self.config_bucket).blob(f'config_{self.env}.json')
        config_str = blob.download_as_string()
        self.config = json.loads(config_str)

    def get(self, key, default=None):
        return self.config.get(key, default)

# Global config object
config = Config()