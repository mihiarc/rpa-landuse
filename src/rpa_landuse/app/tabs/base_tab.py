"""
Base tab class for common functionality.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
import streamlit as st

from ..services import DataService, GeographicService, AnalysisService

logger = logging.getLogger(__name__)


class BaseTab(ABC):
    """Base class for all tab implementations."""
    
    def __init__(self, data: Dict[str, pd.DataFrame]):
        """
        Initialize the tab with data.
        
        Args:
            data: Dictionary of loaded DataFrames
        """
        self.data = data
        self.data_service = DataService()
        self.geo_service = GeographicService()
    
    @abstractmethod
    def render(self) -> None:
        """Render the tab content. Must be implemented by subclasses."""
        pass
    
    def show_error(self, message: str, exception: Exception = None) -> None:
        """Show error message to user and log the exception."""
        st.error(message)
        if exception:
            logger.error(f"{message}: {exception}")
    
    def show_warning(self, message: str) -> None:
        """Show warning message to user."""
        st.warning(message)
        logger.warning(message)
    
    def show_info(self, message: str) -> None:
        """Show info message to user."""
        st.info(message)
        logger.info(message)
    
    def show_success(self, message: str) -> None:
        """Show success message to user."""
        st.success(message)
        logger.info(message) 