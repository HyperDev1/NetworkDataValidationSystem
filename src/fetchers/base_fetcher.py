"""
Base fetcher interface for network data retrieval.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any


class NetworkDataFetcher(ABC):
    """Abstract base class for network data fetchers."""
    
    @abstractmethod
    def fetch_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fetch revenue and impression data for the given date range.
        
        Args:
            start_date: Start date for data fetch
            end_date: End date for data fetch
            
        Returns:
            Dictionary containing revenue and impressions data
            {
                'revenue': float,
                'impressions': int,
                'network': str,
                'date_range': {'start': str, 'end': str}
            }
        """
        pass
    
    @abstractmethod
    def get_network_name(self) -> str:
        """Return the name of the network."""
        pass
