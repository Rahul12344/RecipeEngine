from dataclasses import dataclass
from enum import Enum
from data_pipeline.meta_info.source_metadata import SourceMetadata

@dataclass
class ScrapeResponse:
    """Data class for raw recipe data retrieved from a source"""
    html: str
    source: str
    url: str

@dataclass
class ScrapeRequest:
    """Data class for a request to scrape a source"""
    source_metadata: SourceMetadata
    ingestion_type: IngestionType
    url: str | None = None

class IngestionType(Enum):
    INCREMENTAL = "incremental"
    FULL = "full"