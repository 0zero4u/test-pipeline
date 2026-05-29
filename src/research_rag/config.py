"""Configuration management for Research RAG."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class IngestionConfig(BaseModel):
    """Ingestion pipeline configuration."""

    parser: str = "docling"
    chunk_size_min: int = Field(default=500, ge=100)
    chunk_size_max: int = Field(default=900, le=2000)
    chunk_overlap: float = Field(default=0.12, ge=0.0, le=0.5)


class ExtractionConfig(BaseModel):
    """Entity extraction configuration."""

    entity_model: str = "deepseek/deepseek-v4-flash"
    embedding_model: str = "bge-base-en-v1.5"


class RetrievalConfig(BaseModel):
    """Retrieval configuration."""

    top_k: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SynthesisConfig(BaseModel):
    """Synthesis configuration."""

    model: str = "deepseek/deepseek-v4-flash"
    max_tokens: int = Field(default=2000, ge=100)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)


class StorageConfig(BaseModel):
    """Storage configuration."""

    chroma_path: Path = Field(default=Path("./data/chroma"))
    metadata_path: Path = Field(default=Path("./data/metadata"))


class Settings(BaseSettings):
    """Main settings class."""

    # API Keys (from environment)
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    embedding_api_key: Optional[str] = Field(default=None, alias="EMBEDDING_API_KEY")

    # Configuration sections
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    synthesis: SynthesisConfig = Field(default_factory=SynthesisConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    # General settings
    log_level: str = Field(default="INFO")
    debug: bool = False

    model_config = {
        "env_prefix": "RESEARCH_RAG_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def load_settings(config_path: Optional[Path] = None) -> Settings:
    """Load settings from file and environment."""
    import yaml

    if config_path and config_path.exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}
        return Settings(**config_data)

    return Settings()
