"""Configuration management using pydantic-settings."""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    
    # Models (Groq)
    planner_model: str = Field(default="llama-3.1-70b-versatile", env="PLANNER_MODEL")
    executor_model: str = Field(default="llama-3.1-8b-instant", env="EXECUTOR_MODEL")
    vision_model: str = Field(default="llama-3.2-90b-vision-preview", env="VISION_MODEL")
    
    # Audio
    max_audio_size_mb: int = Field(default=25, env="MAX_AUDIO_SIZE_MB")
    whisper_model: str = Field(default="whisper-large-v3", env="WHISPER_MODEL")
    
    # OCR
    tesseract_lang: str = Field(default="eng", env="TESSERACT_LANG")
    ocr_confidence_threshold: float = Field(default=0.7, env="OCR_CONFIDENCE_THRESHOLD")
    
    # RAG & Embeddings
    vector_store: str = Field(default="chromadb", env="VECTOR_STORE")
    chroma_persist_dir: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIR")
    chunk_size: int = Field(default=512, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    retrieval_top_k: int = Field(default=3, env="RETRIEVAL_TOP_K")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    
    # HuggingFace Cache
    hf_home: str = Field(default="./hf_cache", env="HF_HOME")
    transformers_cache: str = Field(default="./hf_cache/transformers", env="TRANSFORMERS_CACHE")
    sentence_transformers_home: str = Field(default="./hf_cache/sentence_transformers", env="SENTENCE_TRANSFORMERS_HOME")
    
    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    cors_origins: List[str] = Field(default=["http://localhost:8000"], env="CORS_ORIGINS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Rate Limits (Groq Free Tier)
    groq_rate_limit_rpm: int = Field(default=30, env="GROQ_RATE_LIMIT_RPM")
    groq_rate_limit_tpm: int = Field(default=14400, env="GROQ_RATE_LIMIT_TPM")
    
    # Cost Estimation
    enable_cost_estimator: bool = Field(default=True, env="ENABLE_COST_ESTIMATOR")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()