from google.cloud import firestore
from app import config

_client = None


def get_db() -> firestore.Client:
    global _client
    if _client is None:
        kwargs = {}
        if config.GCP_PROJECT_ID:
            kwargs["project"] = config.GCP_PROJECT_ID
        _client = firestore.Client(**kwargs)
    return _client
