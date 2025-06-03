"""
Data formatting utilities.

This module provides utility functions for formatting data for display and download.

It includes methods for formatting numeric columns, renaming columns, and preparing data for download.

The data is formatted to provide optimal display and download capabilities.
"""

import pandas as pd
from typing import Dict, Any, List
import streamlit as st


class DataFormatter:
    """Utility class for formatting data for display and download."""
    
    @staticmethod
    def format_display_data(df: pd.DataFrame, format_config: Dict[str, Any]) -> pd.DataFrame:
        """
        Format DataFrame for display in Streamlit.
        
        Args:
            df: DataFrame to format
            format_config: Configuration for formatting
            
        Returns:
            Formatted DataFrame
        """
        display_df = df.copy()
        
        # Format numeric columns
        for col, config in format_config.get('numeric_columns', {}).items():
            if col in display_df.columns:
                if config.get('format') == 'currency':
                    display_df[col] = display_df[col].map(lambda x: f"${x:,.0f}")
                elif config.get('format') == 'comma':
                    display_df[col] = display_df[col].map(lambda x: f"{x:,.0f}")
                elif config.get('format') == 'percent':
                    display_df[col] = display_df[col].map(lambda x: f"{x:,.1f}%")
                elif config.get('format') == 'decimal':
                    decimals = config.get('decimals', 1)
                    display_df[col] = display_df[col].map(lambda x: f"{x:,.{decimals}f}")
        
        # Rename columns
        if 'column_mapping' in format_config:
            display_df = display_df.rename(columns=format_config['column_mapping'])
        
        return display_df
    
    @staticmethod
    def prepare_download_data(
        df: pd.DataFrame, 
        metadata: Dict[str, Any], 
        column_order: List[str] = None
    ) -> pd.DataFrame:
        """
        Prepare DataFrame for CSV download with metadata.
        
        Args:
            df: DataFrame to prepare
            metadata: Metadata to add
            column_order: Optional column ordering
            
        Returns:
            DataFrame ready for download
        """
        download_df = df.copy()
        
        # Add metadata columns
        for key, value in metadata.items():
            download_df[key] = value
        
        # Reorder columns if specified
        if column_order:
            available_cols = [col for col in column_order if col in download_df.columns]
            remaining_cols = [col for col in download_df.columns if col not in available_cols]
            download_df = download_df[available_cols + remaining_cols]
        
        # Round numeric columns for better readability
        numeric_columns = download_df.select_dtypes(include=['number']).columns
        download_df[numeric_columns] = download_df[numeric_columns].round(2)
        
        return download_df
    
    @staticmethod
    def create_summary_metrics(df: pd.DataFrame, value_col: str, group_col: str = None) -> Dict[str, Any]:
        """
        Create summary metrics from DataFrame.
        
        Args:
            df: DataFrame to analyze
            value_col: Column to calculate metrics for
            group_col: Optional grouping column
            
        Returns:
            Dictionary of summary metrics
        """
        metrics = {}
        
        if group_col and group_col in df.columns:
            metrics['total_groups'] = df[group_col].nunique()
        
        if value_col in df.columns:
            metrics['total_value'] = df[value_col].sum()
            metrics['average_value'] = df[value_col].mean()
            metrics['max_value'] = df[value_col].max()
            metrics['min_value'] = df[value_col].min()
            metrics['std_value'] = df[value_col].std()
        
        return metrics 