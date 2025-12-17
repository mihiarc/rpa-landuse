#!/usr/bin/env python3
"""
Scenario naming mappings for RPA Assessment data.

This module provides bidirectional mapping between database scenario names
(technical RCP-SSP codes) and user-friendly RPA scenario codes/names.

Version: 1.0.0
Created: 2025-09-30
"""

from typing import Dict, NamedTuple, Optional


class ScenarioDisplay(NamedTuple):
    """Display information for a scenario.

    Attributes:
        code: Short RPA code (e.g., "LM", "HH")
        name: Full scenario name (e.g., "Lower-Moderate")
        theme: Narrative theme name from RPA documentation
        climate: Climate pathway description
        society: Socioeconomic pathway description
        growth_summary: Summary of US growth metrics
    """

    code: str
    name: str
    theme: str
    climate: str
    society: str
    growth_summary: str


class ScenarioMapping:
    """Bidirectional mapping between database and display names.

    This class provides translation between:
    - Database scenario names (e.g., "RCP45_SSP1")
    - RPA scenario codes (e.g., "LM")
    - Full scenario names (e.g., "Lower-Moderate")

    Based on 2020 USDA Forest Service RPA Assessment scenarios.
    """

    # Core mapping from database names to RPA codes
    DB_TO_RPA: Dict[str, str] = {
        "OVERALL": "OVERALL",  # Special case - ensemble mean
        "RCP45_SSP1": "LM",  # Lower-Moderate (Taking the Green Road)
        "RCP85_SSP2": "HM",  # High-Moderate (Middle of the Road)
        "RCP85_SSP3": "HL",  # High-Low (A Rocky Road)
        "RCP85_SSP5": "HH",  # High-High (Taking the Highway)
    }

    # Reverse mapping from RPA codes to database names
    RPA_TO_DB: Dict[str, str] = {v: k for k, v in DB_TO_RPA.items()}

    # Full display information for each scenario
    SCENARIO_INFO: Dict[str, ScenarioDisplay] = {
        "OVERALL": ScenarioDisplay(
            code="OVERALL",
            name="Ensemble Mean",
            theme="Baseline Projection",
            climate="All pathways averaged",
            society="All pathways averaged",
            growth_summary="Mean of all scenarios",
        ),
        "RCP45_SSP1": ScenarioDisplay(
            code="LM",
            name="Lower-Moderate",
            theme="Taking the Green Road",
            climate="RCP4.5 (2.5°C)",
            society="Sustainable (SSP1)",
            growth_summary="GDP: 3.0x, Pop: 1.5x",
        ),
        "RCP85_SSP2": ScenarioDisplay(
            code="HM",
            name="High-Moderate",
            theme="Middle of the Road",
            climate="RCP8.5 (4.5°C)",
            society="Middle road (SSP2)",
            growth_summary="GDP: 2.8x, Pop: 1.4x",
        ),
        "RCP85_SSP3": ScenarioDisplay(
            code="HL",
            name="High-Low",
            theme="A Rocky Road",
            climate="RCP8.5 (4.5°C)",
            society="Regional rivalry (SSP3)",
            growth_summary="GDP: 1.9x, Pop: 1.0x",
        ),
        "RCP85_SSP5": ScenarioDisplay(
            code="HH",
            name="High-High",
            theme="Taking the Highway",
            climate="RCP8.5 (4.5°C)",
            society="Fossil-fueled (SSP5)",
            growth_summary="GDP: 4.7x, Pop: 1.9x",
        ),
    }

    # Display order for sorting scenarios in results
    DISPLAY_ORDER: Dict[str, int] = {"OVERALL": 0, "LM": 1, "HM": 2, "HL": 3, "HH": 4}

    @classmethod
    def get_display_name(cls, db_name: str, format: str = "full") -> str:
        """Get display name for a database scenario name.

        Args:
            db_name: Database scenario name (e.g., 'RCP85_SSP3')
            format: Display format:
                - 'code': Just RPA code (e.g., "LM")
                - 'name': Just scenario name (e.g., "Lower-Moderate")
                - 'full': Code with name (e.g., "LM (Lower-Moderate)")
                - 'full_technical': Code, name, and DB name (e.g., "LM (Lower-Moderate, RCP45_SSP1)")
                - 'detailed': Full information including theme and growth

        Returns:
            Formatted scenario name, or original db_name if not recognized

        Example:
            >>> ScenarioMapping.get_display_name('RCP45_SSP1', 'full')
            'LM (Lower-Moderate)'
            >>> ScenarioMapping.get_display_name('RCP85_SSP5', 'code')
            'HH'
        """
        if db_name not in cls.SCENARIO_INFO:
            return db_name  # Fallback to original if not mapped

        info = cls.SCENARIO_INFO[db_name]

        if format == "code":
            return info.code
        elif format == "name":
            return info.name
        elif format == "full":
            if info.code == "OVERALL":
                return "OVERALL (Ensemble Mean)"
            return f"{info.code} ({info.name})"
        elif format == "full_technical":
            if info.code == "OVERALL":
                return "OVERALL (Ensemble Mean)"
            return f"{info.code} ({info.name}, {db_name})"
        elif format == "detailed":
            if info.code == "OVERALL":
                return "OVERALL: Ensemble Mean across all scenarios"
            return f"{info.code} ({info.name}): {info.climate}, {info.society} - {info.growth_summary}"
        else:
            return db_name

    @classmethod
    def get_db_name(cls, user_input: str) -> Optional[str]:
        """Parse user input to database scenario name.

        Handles various input formats:
        - RPA codes: LM, HM, HL, HH, OVERALL
        - Database names: RCP45_SSP1, RCP85_SSP2, etc.
        - Scenario names: "Lower-Moderate", "High-High", etc.
        - Partial matches in themes: "Green Road", "Rocky Road", etc.

        Args:
            user_input: User's scenario reference (case-insensitive)

        Returns:
            Database scenario name or None if not recognized

        Example:
            >>> ScenarioMapping.get_db_name('LM')
            'RCP45_SSP1'
            >>> ScenarioMapping.get_db_name('lower-moderate')
            'RCP45_SSP1'
            >>> ScenarioMapping.get_db_name('green road')
            'RCP45_SSP1'
        """
        if not user_input:
            return None

        input_upper = user_input.upper().strip()

        # Direct database name match
        if input_upper in cls.DB_TO_RPA:
            return input_upper

        # RPA code match
        if input_upper in cls.RPA_TO_DB:
            return cls.RPA_TO_DB[input_upper]

        # Check partial matches in names and themes
        for db_name, info in cls.SCENARIO_INFO.items():
            if (
                input_upper in info.name.upper()
                or input_upper in info.theme.upper()
                or input_upper.replace("-", " ") in info.name.upper().replace("-", " ")
            ):
                return db_name

        return None

    @classmethod
    def get_scenario_info(cls, scenario: str) -> Optional[ScenarioDisplay]:
        """Get full scenario information.

        Args:
            scenario: Either database name or RPA code

        Returns:
            ScenarioDisplay object or None if not found

        Example:
            >>> info = ScenarioMapping.get_scenario_info('LM')
            >>> print(f"{info.code}: {info.theme}")
            LM: Taking the Green Road
        """
        db_name = cls.get_db_name(scenario)
        if db_name:
            return cls.SCENARIO_INFO.get(db_name)
        return None

    @classmethod
    def get_sort_key(cls, scenario_name: str) -> int:
        """Get sort key for scenario ordering.

        Args:
            scenario_name: Scenario name in any format

        Returns:
            Sort order integer (lower = earlier in order)

        Example:
            >>> scenarios = ['HH', 'LM', 'OVERALL', 'HL', 'HM']
            >>> sorted(scenarios, key=ScenarioMapping.get_sort_key)
            ['OVERALL', 'LM', 'HM', 'HL', 'HH']
        """
        # Try to get RPA code from input
        info = cls.get_scenario_info(scenario_name)
        if info:
            return cls.DISPLAY_ORDER.get(info.code, 999)

        # Check if it's already a code
        code = scenario_name.split()[0] if " " in scenario_name else scenario_name
        return cls.DISPLAY_ORDER.get(code.upper(), 999)

    @classmethod
    def create_reference_table_markdown(cls) -> str:
        """Create markdown reference table for all scenarios.

        Returns:
            Markdown-formatted table string

        Example:
            >>> print(ScenarioMapping.create_reference_table_markdown())
            | Code | Name | Climate | Society | U.S. Growth |
            |------|------|---------|---------|-------------|
            | **LM** | Lower-Moderate | RCP4.5 (2.5°C) | ... |
        """
        rows = []
        for db_name, info in cls.SCENARIO_INFO.items():
            if db_name == "OVERALL":
                continue  # Skip overall in reference table
            rows.append(f"| **{info.code}** | {info.name} | {info.climate} | {info.society} | {info.growth_summary} |")

        header = "| Code | Name | Climate | Society | U.S. Growth |\n|------|------|---------|---------|-------------|"

        return header + "\n" + "\n".join(rows)


# Convenience constants for common use
OVERALL = "OVERALL"
LOWER_MODERATE = "LM"
HIGH_MODERATE = "HM"
HIGH_LOW = "HL"
HIGH_HIGH = "HH"

ALL_RPA_CODES = [OVERALL, LOWER_MODERATE, HIGH_MODERATE, HIGH_LOW, HIGH_HIGH]
COMPARISON_CODES = [LOWER_MODERATE, HIGH_MODERATE, HIGH_LOW, HIGH_HIGH]  # Exclude OVERALL
