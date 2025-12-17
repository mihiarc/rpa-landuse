#!/usr/bin/env python3
"""
Response formatting utilities for consistent scenario presentation.

This module provides utilities for formatting agent responses with user-friendly
scenario names instead of technical database codes.

Version: 1.0.0
Created: 2025-09-30
"""

from typing import Union

import pandas as pd

from landuse.config.scenario_mappings import ScenarioMapping


class ResponseFormatter:
    """Format agent responses with consistent, user-friendly scenario naming.

    This class handles translation of technical database scenario names
    (e.g., "RCP45_SSP1") to user-friendly RPA codes and names (e.g., "LM (Lower-Moderate)")
    in both text responses and data tables.
    """

    @staticmethod
    def format_scenario_in_text(text: str, format: str = 'full') -> str:
        """Replace database scenario names with user-friendly names in text.

        Performs case-sensitive replacement of all scenario names found in text.
        Preserves sentence structure and other content.

        Args:
            text: Text containing scenario names (query results, explanations, etc.)
            format: Display format to use ('code', 'name', 'full', 'full_technical', 'detailed')

        Returns:
            Text with formatted scenario names

        Example:
            >>> text = "RCP45_SSP1 shows less growth than RCP85_SSP5"
            >>> ResponseFormatter.format_scenario_in_text(text)
            'LM (Lower-Moderate) shows less growth than HH (High-High)'
        """
        if not text:
            return text

        # Replace each database name with display name
        # Sort by length (longest first) to avoid partial replacements
        db_names = sorted(ScenarioMapping.DB_TO_RPA.keys(), key=len, reverse=True)

        formatted_text = text
        for db_name in db_names:
            if db_name in formatted_text:
                display_name = ScenarioMapping.get_display_name(db_name, format)
                formatted_text = formatted_text.replace(db_name, display_name)

        return formatted_text

    @staticmethod
    def format_dataframe_scenarios(
        df: pd.DataFrame,
        scenario_column: str = 'scenario_name',
        format: str = 'full',
        sort: bool = True
    ) -> pd.DataFrame:
        """Format scenario names in a DataFrame.

        Updates scenario column with user-friendly names and optionally sorts
        by standard scenario order (OVERALL, LM, HM, HL, HH).

        Args:
            df: DataFrame containing scenario column
            scenario_column: Name of the scenario column to format
            format: Display format to use
            sort: Whether to sort rows by scenario display order

        Returns:
            DataFrame with formatted scenario names (copy of original)

        Example:
            >>> df = pd.DataFrame({'scenario_name': ['RCP45_SSP1', 'RCP85_SSP5']})
            >>> formatted = ResponseFormatter.format_dataframe_scenarios(df)
            >>> print(formatted['scenario_name'].tolist())
            ['LM (Lower-Moderate)', 'HH (High-High)']
        """
        if df.empty or scenario_column not in df.columns:
            return df

        # Create copy to avoid modifying original
        df = df.copy()

        # Format scenario names
        df[scenario_column] = df[scenario_column].apply(
            lambda x: ScenarioMapping.get_display_name(x, format) if pd.notna(x) else x
        )

        # Sort by display order if requested
        if sort:
            df['_sort_order'] = df[scenario_column].apply(
                lambda x: ScenarioMapping.get_sort_key(x) if pd.notna(x) else 999
            )
            df = df.sort_values('_sort_order').drop('_sort_order', axis=1)

        return df

    @staticmethod
    def create_scenario_reference_table() -> str:
        """Create markdown reference table for all scenarios.

        Returns:
            Markdown-formatted table with scenario information

        Example:
            >>> table = ResponseFormatter.create_scenario_reference_table()
            >>> print(table)
            | Code | Name | Climate | Society | U.S. Growth |
            |------|------|---------|---------|-------------|
            | **LM** | Lower-Moderate | ... | ... | ... |
        """
        return ScenarioMapping.create_reference_table_markdown()

    @staticmethod
    def format_query_result_text(result_text: str) -> str:
        """Format complete query result text with enhanced scenario presentation.

        Applies text formatting and adds helpful context about scenarios when
        multiple scenarios are mentioned.

        Args:
            result_text: Complete query result text from agent

        Returns:
            Formatted text with enhanced scenario presentation

        Example:
            >>> result = "Query results for RCP45_SSP1 and RCP85_SSP5..."
            >>> formatted = ResponseFormatter.format_query_result_text(result)
        """
        # Apply standard text formatting
        formatted = ResponseFormatter.format_scenario_in_text(result_text, format='full')

        # Count unique scenarios mentioned
        scenarios_mentioned = []
        for code in ScenarioMapping.ALL_RPA_CODES:
            if code in formatted:
                scenarios_mentioned.append(code)

        # If multiple scenarios mentioned, add reference note
        if len(scenarios_mentioned) > 2:
            reference_note = (
                "\n\n*Scenario Reference: "
                "LM=Lower-Moderate (sustainable), "
                "HM=High-Moderate (middle road), "
                "HL=High-Low (rivalry), "
                "HH=High-High (fossil-fueled)*"
            )
            formatted += reference_note

        return formatted

    @staticmethod
    def get_scenario_summary(scenario: str) -> str:
        """Get concise summary of a scenario for inline reference.

        Args:
            scenario: Scenario name in any format (DB name, RPA code, or display name)

        Returns:
            Concise summary string, or original input if not recognized

        Example:
            >>> ResponseFormatter.get_scenario_summary('LM')
            'Lower-Moderate (sustainable, low emissions)'
            >>> ResponseFormatter.get_scenario_summary('RCP85_SSP5')
            'High-High (fossil-fueled, high emissions)'
        """
        info = ScenarioMapping.get_scenario_info(scenario)
        if not info:
            return scenario

        if info.code == 'OVERALL':
            return "Ensemble Mean (average across all scenarios)"

        # Create concise summary
        society_short = info.society.split('(')[1].rstrip(')') if '(' in info.society else info.society
        climate_short = "low emissions" if "4.5" in info.climate else "high emissions"

        return f"{info.name} ({society_short.lower()}, {climate_short})"
