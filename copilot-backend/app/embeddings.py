import logging
from typing import List

from fastembed import TextEmbedding

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        logger.info("loading_embedding_model", extra={"model": model_name})
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name)
        logger.info("embedding_model_loaded")

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        result = list(self.model.embed(texts))
        return [vec.tolist() if hasattr(vec, "tolist") else list(vec) for vec in result]

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]
