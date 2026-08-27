import os
from pathlib import Path
import sys
import tempfile

import pytest


TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="ai-document-assistant-tests-"))
os.environ["AI_DOCUMENT_ASSISTANT_DATA_DIR"] = str(TEST_DATA_DIR)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


@pytest.fixture(autouse=True)
def clear_vector_store():
    from app.services.vectordb import get_collection

    collection = get_collection()
    ids = collection.get()["ids"]
    if ids:
        collection.delete(ids=ids)
