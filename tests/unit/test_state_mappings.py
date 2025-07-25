"""Test the centralized state mappings module."""

import pytest

from landuse.utilities.state_mappings import (
    StateMapper,
    get_state_name,
    get_state_abbrev,
    get_fips_from_name,
    get_fips_from_abbrev,
    STATE_NAMES,
    STATE_ABBREV
)


class TestStateMapper:
    """Test the StateMapper class."""
    
    def test_fips_to_name(self):
        """Test FIPS code to state name conversion."""
        assert StateMapper.fips_to_name("01") == "Alabama"
        assert StateMapper.fips_to_name("06") == "California"
        assert StateMapper.fips_to_name("36") == "New York"
        assert StateMapper.fips_to_name("72") == "Puerto Rico"
        assert StateMapper.fips_to_name("99") is None
    
    def test_fips_to_abbrev(self):
        """Test FIPS code to abbreviation conversion."""
        assert StateMapper.fips_to_abbrev("01") == "AL"
        assert StateMapper.fips_to_abbrev("06") == "CA"
        assert StateMapper.fips_to_abbrev("36") == "NY"
        assert StateMapper.fips_to_abbrev("72") == "PR"
        assert StateMapper.fips_to_abbrev("99") is None
    
    def test_name_to_fips(self):
        """Test state name to FIPS code conversion."""
        assert StateMapper.name_to_fips("Alabama") == "01"
        assert StateMapper.name_to_fips("California") == "06"
        assert StateMapper.name_to_fips("New York") == "36"
        # Test case insensitive
        assert StateMapper.name_to_fips("alabama") == "01"
        assert StateMapper.name_to_fips("CALIFORNIA") == "06"
        assert StateMapper.name_to_fips("Invalid State") is None
    
    def test_abbrev_to_fips(self):
        """Test abbreviation to FIPS code conversion."""
        assert StateMapper.abbrev_to_fips("AL") == "01"
        assert StateMapper.abbrev_to_fips("CA") == "06"
        assert StateMapper.abbrev_to_fips("NY") == "36"
        # Test case insensitive
        assert StateMapper.abbrev_to_fips("al") == "01"
        assert StateMapper.abbrev_to_fips("ca") == "06"
        assert StateMapper.abbrev_to_fips("XX") is None
    
    def test_abbrev_to_name(self):
        """Test abbreviation to state name conversion."""
        assert StateMapper.abbrev_to_name("AL") == "Alabama"
        assert StateMapper.abbrev_to_name("CA") == "California"
        assert StateMapper.abbrev_to_name("NY") == "New York"
        # Test case insensitive
        assert StateMapper.abbrev_to_name("al") == "Alabama"
        assert StateMapper.abbrev_to_name("XX") is None
    
    def test_name_to_abbrev(self):
        """Test state name to abbreviation conversion."""
        assert StateMapper.name_to_abbrev("Alabama") == "AL"
        assert StateMapper.name_to_abbrev("California") == "CA"
        assert StateMapper.name_to_abbrev("New York") == "NY"
        # Test case insensitive
        assert StateMapper.name_to_abbrev("alabama") == "AL"
        assert StateMapper.name_to_abbrev("Invalid State") is None
    
    def test_validation_methods(self):
        """Test validation methods."""
        # Valid FIPS
        assert StateMapper.is_valid_fips("01") is True
        assert StateMapper.is_valid_fips("06") is True
        assert StateMapper.is_valid_fips("99") is False
        
        # Valid abbreviations
        assert StateMapper.is_valid_abbrev("AL") is True
        assert StateMapper.is_valid_abbrev("ca") is True  # Case insensitive
        assert StateMapper.is_valid_abbrev("XX") is False
        
        # Valid names
        assert StateMapper.is_valid_name("Alabama") is True
        assert StateMapper.is_valid_name("california") is True  # Case insensitive
        assert StateMapper.is_valid_name("Invalid State") is False
    
    def test_get_all_methods(self):
        """Test methods that return all values."""
        fips_codes = StateMapper.get_all_fips_codes()
        assert len(fips_codes) == 53  # 50 states + DC + PR + VI
        assert "01" in fips_codes
        assert "72" in fips_codes
        
        abbreviations = StateMapper.get_all_abbreviations()
        assert len(abbreviations) == 53
        assert "AL" in abbreviations
        assert "PR" in abbreviations
        
        names = StateMapper.get_all_names()
        assert len(names) == 53
        assert "Alabama" in names
        assert "Puerto Rico" in names
    
    def test_district_of_columbia(self):
        """Test that DC is handled correctly."""
        assert StateMapper.fips_to_name("11") == "District of Columbia"
        assert StateMapper.fips_to_abbrev("11") == "DC"
        assert StateMapper.name_to_fips("District of Columbia") == "11"
        assert StateMapper.abbrev_to_fips("DC") == "11"
    
    def test_territories(self):
        """Test that territories are included."""
        # Puerto Rico
        assert StateMapper.fips_to_name("72") == "Puerto Rico"
        assert StateMapper.fips_to_abbrev("72") == "PR"
        
        # Virgin Islands
        assert StateMapper.fips_to_name("78") == "Virgin Islands"
        assert StateMapper.fips_to_abbrev("78") == "VI"


class TestConvenienceFunctions:
    """Test the convenience functions."""
    
    def test_get_state_name(self):
        """Test get_state_name function."""
        assert get_state_name("01") == "Alabama"
        assert get_state_name("36") == "New York"
        assert get_state_name("99") is None
    
    def test_get_state_abbrev(self):
        """Test get_state_abbrev function."""
        assert get_state_abbrev("01") == "AL"
        assert get_state_abbrev("36") == "NY"
        assert get_state_abbrev("99") is None
    
    def test_get_fips_from_name(self):
        """Test get_fips_from_name function."""
        assert get_fips_from_name("Alabama") == "01"
        assert get_fips_from_name("New York") == "36"
        assert get_fips_from_name("Invalid") is None
    
    def test_get_fips_from_abbrev(self):
        """Test get_fips_from_abbrev function."""
        assert get_fips_from_abbrev("AL") == "01"
        assert get_fips_from_abbrev("NY") == "36"
        assert get_fips_from_abbrev("XX") is None


class TestBackwardCompatibility:
    """Test backward compatibility exports."""
    
    def test_state_names_dict(self):
        """Test STATE_NAMES dictionary export."""
        assert STATE_NAMES["01"] == "Alabama"
        assert STATE_NAMES["06"] == "California"
        assert STATE_NAMES["72"] == "Puerto Rico"
        assert len(STATE_NAMES) == 53  # 50 states + DC + PR + VI
    
    def test_state_abbrev_dict(self):
        """Test STATE_ABBREV dictionary export."""
        assert STATE_ABBREV["01"] == "AL"
        assert STATE_ABBREV["06"] == "CA"
        assert STATE_ABBREV["72"] == "PR"
        assert len(STATE_ABBREV) == 53  # 50 states + DC + PR + VI