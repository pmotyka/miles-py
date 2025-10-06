"""
Tidbyt output data model for display formatting.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
import json


@dataclass
class TidbytOutput:
    """Data model for Tidbyt display output formatting."""
    
    total_miles: str
    last_updated: str
    source_count: int
    display_message: str
    
    def __post_init__(self):
        """Validate Tidbyt output data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate all Tidbyt output fields."""
        self._validate_total_miles()
        self._validate_last_updated()
        self._validate_source_count()
        self._validate_display_message()
    
    def _validate_total_miles(self) -> None:
        """Validate total miles is a properly formatted string."""
        if not isinstance(self.total_miles, str):
            raise ValueError("Total miles must be a string")
        
        # Check if it's a valid number format (e.g., "123.45")
        try:
            float(self.total_miles)
        except ValueError:
            raise ValueError("Total miles must be a valid number string")
    
    def _validate_last_updated(self) -> None:
        """Validate last updated is a properly formatted datetime string."""
        if not isinstance(self.last_updated, str):
            raise ValueError("Last updated must be a string")
        
        # Check if it's a valid ISO format datetime string
        try:
            datetime.fromisoformat(self.last_updated.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Last updated must be a valid ISO format datetime string")
    
    def _validate_source_count(self) -> None:
        """Validate source count is a non-negative integer."""
        if not isinstance(self.source_count, int) or self.source_count < 0:
            raise ValueError("Source count must be a non-negative integer")
    
    def _validate_display_message(self) -> None:
        """Validate display message is not empty."""
        if not isinstance(self.display_message, str):
            raise ValueError("Display message must be a string")
        
        if not self.display_message.strip():
            raise ValueError("Display message cannot be empty")
    
    def to_json(self) -> str:
        """Convert TidbytOutput to JSON string for Tidbyt consumption."""
        output_dict = {
            "total_miles": self.total_miles,
            "last_updated": self.last_updated,
            "source_count": self.source_count,
            "display_message": self.display_message,
            "generated_at": datetime.now().isoformat()
        }
        
        return json.dumps(output_dict, indent=2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TidbytOutput to dictionary."""
        return {
            "total_miles": self.total_miles,
            "last_updated": self.last_updated,
            "source_count": self.source_count,
            "display_message": self.display_message,
            "generated_at": datetime.now().isoformat()
        }
    
    @classmethod
    def from_aggregated_data(cls, aggregated_data) -> 'TidbytOutput':
        """Create TidbytOutput from AggregatedData instance."""
        # Format miles with 2 decimal places
        total_miles_str = f"{aggregated_data.total_miles:.2f}"
        
        # Format last updated timestamp
        last_updated_str = aggregated_data.last_updated.isoformat()
        
        # Create display message
        source_names = ", ".join(aggregated_data.sources)
        display_message = f"{total_miles_str} miles from {source_names}"
        
        return cls(
            total_miles=total_miles_str,
            last_updated=last_updated_str,
            source_count=len(aggregated_data.sources),
            display_message=display_message
        )
    
    @classmethod
    def create_fallback(cls, message: str = "No data available") -> 'TidbytOutput':
        """Create fallback TidbytOutput when no data is available."""
        return cls(
            total_miles="0.00",
            last_updated=datetime.now().isoformat(),
            source_count=0,
            display_message=message
        )