"""Centralized state name, code, and abbreviation mappings.

This module provides a single source of truth for all state-related mappings
to eliminate duplication across the codebase.
"""

from typing import Optional, Dict


class StateMapper:
    """Utility class for state name, code, and abbreviation conversions."""
    
    # FIPS code to state name mapping
    FIPS_TO_NAME: Dict[str, str] = {
        "01": "Alabama",
        "02": "Alaska",
        "04": "Arizona",
        "05": "Arkansas",
        "06": "California",
        "08": "Colorado",
        "09": "Connecticut",
        "10": "Delaware",
        "11": "District of Columbia",
        "12": "Florida",
        "13": "Georgia",
        "15": "Hawaii",
        "16": "Idaho",
        "17": "Illinois",
        "18": "Indiana",
        "19": "Iowa",
        "20": "Kansas",
        "21": "Kentucky",
        "22": "Louisiana",
        "23": "Maine",
        "24": "Maryland",
        "25": "Massachusetts",
        "26": "Michigan",
        "27": "Minnesota",
        "28": "Mississippi",
        "29": "Missouri",
        "30": "Montana",
        "31": "Nebraska",
        "32": "Nevada",
        "33": "New Hampshire",
        "34": "New Jersey",
        "35": "New Mexico",
        "36": "New York",
        "37": "North Carolina",
        "38": "North Dakota",
        "39": "Ohio",
        "40": "Oklahoma",
        "41": "Oregon",
        "42": "Pennsylvania",
        "44": "Rhode Island",
        "45": "South Carolina",
        "46": "South Dakota",
        "47": "Tennessee",
        "48": "Texas",
        "49": "Utah",
        "50": "Vermont",
        "51": "Virginia",
        "53": "Washington",
        "54": "West Virginia",
        "55": "Wisconsin",
        "56": "Wyoming",
        # Territories
        "72": "Puerto Rico",
        "78": "Virgin Islands"
    }
    
    # FIPS code to abbreviation mapping
    FIPS_TO_ABBREV: Dict[str, str] = {
        "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
        "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
        "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
        "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
        "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
        "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
        "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
        "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
        "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
        "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
        "56": "WY", "72": "PR", "78": "VI"
    }
    
    # Abbreviation to name mapping (derived)
    ABBREV_TO_NAME: Dict[str, str] = {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
        "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
        "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
        "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
        "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
        "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
        "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
        "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
        "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
        "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
        "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
        "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
        "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
        "PR": "Puerto Rico", "VI": "Virgin Islands"
    }
    
    # Reverse mappings (created on first use)
    _name_to_fips: Optional[Dict[str, str]] = None
    _abbrev_to_fips: Optional[Dict[str, str]] = None
    _name_to_abbrev: Optional[Dict[str, str]] = None
    
    @classmethod
    def _ensure_reverse_mappings(cls) -> None:
        """Create reverse mappings if they don't exist."""
        if cls._name_to_fips is None:
            cls._name_to_fips = {v: k for k, v in cls.FIPS_TO_NAME.items()}
        if cls._abbrev_to_fips is None:
            cls._abbrev_to_fips = {v: k for k, v in cls.FIPS_TO_ABBREV.items()}
        if cls._name_to_abbrev is None:
            cls._name_to_abbrev = {v: k for k, v in cls.ABBREV_TO_NAME.items()}
    
    @classmethod
    def fips_to_name(cls, fips_code: str) -> Optional[str]:
        """Convert FIPS code to state name."""
        return cls.FIPS_TO_NAME.get(fips_code)
    
    @classmethod
    def fips_to_abbrev(cls, fips_code: str) -> Optional[str]:
        """Convert FIPS code to state abbreviation."""
        return cls.FIPS_TO_ABBREV.get(fips_code)
    
    @classmethod
    def name_to_fips(cls, name: str) -> Optional[str]:
        """Convert state name to FIPS code."""
        cls._ensure_reverse_mappings()
        # Try exact match first
        if name in cls._name_to_fips:
            return cls._name_to_fips[name]
        # Try case-insensitive match
        name_lower = name.lower()
        for state_name, fips in cls._name_to_fips.items():
            if state_name.lower() == name_lower:
                return fips
        return None
    
    @classmethod
    def abbrev_to_fips(cls, abbrev: str) -> Optional[str]:
        """Convert state abbreviation to FIPS code."""
        cls._ensure_reverse_mappings()
        return cls._abbrev_to_fips.get(abbrev.upper())
    
    @classmethod
    def abbrev_to_name(cls, abbrev: str) -> Optional[str]:
        """Convert state abbreviation to name."""
        return cls.ABBREV_TO_NAME.get(abbrev.upper())
    
    @classmethod
    def name_to_abbrev(cls, name: str) -> Optional[str]:
        """Convert state name to abbreviation."""
        cls._ensure_reverse_mappings()
        # Try exact match first
        if name in cls._name_to_abbrev:
            return cls._name_to_abbrev[name]
        # Try case-insensitive match
        name_lower = name.lower()
        for state_name, abbrev in cls._name_to_abbrev.items():
            if state_name.lower() == name_lower:
                return abbrev
        return None
    
    @classmethod
    def is_valid_fips(cls, fips_code: str) -> bool:
        """Check if a FIPS code is valid."""
        return fips_code in cls.FIPS_TO_NAME
    
    @classmethod
    def is_valid_abbrev(cls, abbrev: str) -> bool:
        """Check if a state abbreviation is valid."""
        return abbrev.upper() in cls.ABBREV_TO_NAME
    
    @classmethod
    def is_valid_name(cls, name: str) -> bool:
        """Check if a state name is valid."""
        cls._ensure_reverse_mappings()
        return cls.name_to_fips(name) is not None
    
    @classmethod
    def get_all_fips_codes(cls) -> list[str]:
        """Get all FIPS codes."""
        return list(cls.FIPS_TO_NAME.keys())
    
    @classmethod
    def get_all_abbreviations(cls) -> list[str]:
        """Get all state abbreviations."""
        return list(cls.ABBREV_TO_NAME.keys())
    
    @classmethod
    def get_all_names(cls) -> list[str]:
        """Get all state names."""
        return list(cls.FIPS_TO_NAME.values())


# Convenience functions for backward compatibility
def get_state_name(fips_code: str) -> Optional[str]:
    """Get state name from FIPS code."""
    return StateMapper.fips_to_name(fips_code)


def get_state_abbrev(fips_code: str) -> Optional[str]:
    """Get state abbreviation from FIPS code."""
    return StateMapper.fips_to_abbrev(fips_code)


def get_fips_from_name(state_name: str) -> Optional[str]:
    """Get FIPS code from state name."""
    return StateMapper.name_to_fips(state_name)


def get_fips_from_abbrev(abbrev: str) -> Optional[str]:
    """Get FIPS code from state abbreviation."""
    return StateMapper.abbrev_to_fips(abbrev)


# Export the main mapping dictionaries for backward compatibility
STATE_NAMES = StateMapper.FIPS_TO_NAME
STATE_ABBREV = StateMapper.FIPS_TO_ABBREV