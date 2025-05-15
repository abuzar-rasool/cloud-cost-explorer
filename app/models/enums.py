"""
Enum definitions for the cloud pricing comparison application.
"""
from enum import Enum, auto


class StrEnum(str, Enum):
    """String Enum base class to allow for string comparison."""
    
    def __str__(self) -> str:
        return self.value


class ServiceType(StrEnum):
    """Types of cloud services."""
    COMPUTE = "compute"
    STORAGE = "storage"


class Region(StrEnum):
    """
    Supported geographic regions for the pricing comparison.
    When ALL is specified, prices from all available regions will be returned.
    """
    ALL = "all"  # Return prices from all available regions
    NORTH_AMERICA = "north-america"
    SOUTH_AMERICA = "south-america"
    EUROPE = "europe"
    ASIA = "asia"
    AFRICA = "africa"
    OCEANIA = "oceania"
    ANTARCTICA = "antarctica"
    MULTI_REGION = "multi-region"
    

from enum import Enum

class StorageTier(Enum):
    FREQUENT_ACCESS = "FrequentAccess"
    # Purpose:
    #   - Optimized for data read/write on every request
    #   - Lowest latency & highest throughput (SSD/NVMe)
    #   - Highest storage cost; minimal or no retrieval fees
    #   - Use Cases: live applications, active databases, CDN origin stores
    # Provider mappings:
    #   AWS → S3 Standard, S3 Express One Zone, S3 Intelligent-Tiering Frequent Access,
    #          S3 on Outposts :contentReference[oaicite:0]{index=0}, S3 Intelligent-Tiering Infrequent Access (when accessed)
    #   GCP → STANDARD (incl. Multi-Regional, Regional, Durable Reduced Availability)
    #   Azure → Hot, Premium Block Blob :contentReference[oaicite:3]{index=3}

    OCCASIONAL_ACCESS = "OccasionalAccess"
    # Purpose:
    #   - Balances cost vs. performance for intermittently accessed data
    #   - Moderate latency & throughput (e.g., HDD/SATA)
    #   - Lower storage cost than FREQUENT_ACCESS; retrieval fees apply
    #   - Minimum duration: 30 days
    #   - Use Cases: weekly backups, analytics datasets, secondary copies
    # Provider mappings:
    #   AWS → S3 Standard-IA, S3 One Zone-IA, S3 Intelligent-Tiering Infrequent Access 
    #   GCP → NEARLINE
    #   Azure → Cool 

    RARE_ACCESS = "RareAccess"
    # Purpose:
    #   - For data accessed infrequently but needs sub-second retrieval
    #   - Millisecond-scale latency; higher storage savings
    #   - Lower storage cost than OCCASIONAL_ACCESS; higher retrieval fees
    #   - Minimum duration: 90 days
    #   - Use Cases: compliance snapshots, long-term logs, DR images
    # Provider mappings:
    #   AWS → S3 Glacier Instant Retrieval, S3 Intelligent-Tiering Archive Instant Access :contentReference[oaicite:7]{index=7}
    #   GCP → COLDLINE 
    #   Azure → Cold 

    SHORT_TERM_ARCHIVE = "ShortTermArchive"
    # Purpose:
    #   - Archive for days to weeks; retrieval in minutes
    #   - Very low storage cost; higher per-GB retrieval & early-deletion fees
    #   - Minimum duration: 30–90 days
    #   - Use Cases: month-end financials, project archives
    # Provider mappings:
    #   AWS → S3 Glacier Flexible Retrieval, S3 Intelligent-Tiering Archive Access
    #   GCP → ARCHIVE 
    #   Azure → Archive 

    LONG_TERM_ARCHIVE = "LongTermArchive"
    # Purpose:
    #   - Deep-archive data almost never retrieved; retrieval in hours to days
    #   - Lowest storage cost; significant retrieval latency & fees
    #   - Minimum duration: 180–365 days
    #   - Use Cases: legal hold, regulatory compliance, historical archives
    # Provider mappings:
    #   AWS → S3 Glacier Deep Archive, S3 Intelligent-Tiering Deep Archive Access
    #   GCP → (none beyond ARCHIVE) 
    #   Azure → (none beyond ARCHIVE) 

    def __str__(self):
        return self.value

    

from enum import Enum

class StorageTier(Enum):
    
    SMART = "Smart"
    # Purpose:
    #   - Automatically moves data between tiers based on access patterns
    #   - Optimizes storage costs & performance
    #   - Reduces manual management overhead
    #   - Requires minimal configuration
    #   - Automatically moves data between tiers based on access patterns
    
    FREQUENT_ACCESS = "FrequentAccess"
    # Purpose:
    #   - Optimized for data read/written constantly
    #   - Lowest latency & highest IOPS (e.g., SSD/NVMe backing)
    #   - Highest storage cost; minimal or no retrieval fees
    #   - Availability: ≥99.9% (multi-AZ/multi-region)


    OCCASIONAL_ACCESS = "OccasionalAccess"
    # Purpose:
    #   - Balances cost vs. performance for data accessed intermittently
    #   - Moderate latency & throughput (e.g., HDD/SATA backing)
    #   - Lower storage cost than FREQUENT_ACCESS; retrieval fees apply
    #   - Minimum duration: 30 days
  

    RARE_ACCESS = "RareAccess"
    # Purpose:
    #   - For data accessed infrequently (e.g., quarterly) but requiring sub-second retrieval
    #   - Millisecond-scale latency; optimized for rare but speedy access
    #   - Lower storage cost than OCCASIONAL_ACCESS; higher retrieval fees
    #   - Minimum duration: 90 days

    SHORT_TERM_ARCHIVE = "ShortTermArchive"
    # Purpose:
    #   - Archive data retained days to weeks; retrieval in minutes
    #   - Very low storage cost; higher per-GB retrieval & early-deletion fees
    #   - Minimum duration: 30–90 days depending on provider

    LONG_TERM_ARCHIVE = "LongTermArchive"
    # Purpose:
    #   - Deep-archive for data you almost never retrieve
    #   - Lowest storage cost; retrieval latencies hours to days
    #   - Minimum duration: 180–365 days


    def __str__(self):
        return self.value



class Provider(StrEnum):
    """Supported cloud providers."""
    AWS = "aws"



class ComputeFamily(StrEnum):
    """Compute instance families."""
    GENERAL = "general"  # General purpose instances
    COMPUTE = "compute"  # Compute optimized instances
    MEMORY = "memory"  # Memory optimized instances


class ErrorSource(StrEnum):
    """Sources of errors in the application."""
    AWS = "aws"
    # Removed Azure and GCP
    GENERAL = "general" 