"""
Unit tests for combined scenarios converter aggregation logic.

Tests use real data patterns extracted from the production database
to ensure accurate validation of aggregation functionality.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from converters.convert_to_duckdb import LanduseCombinedScenarioConverter


class TestRCPSSPKeyExtraction:
    """Test extraction of RCP-SSP keys from GCM scenario names."""

    def test_extract_rcp45_ssp1_key(self, tmp_path):
        """Test extraction from RCP4.5 SSP1 scenario."""
        # Create dummy files to pass validation
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"

        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Test various GCM model formats
        scenarios = [
            "CNRM_CM5_rcp45_ssp1",
            "HadGEM2_ES365_rcp45_ssp1",
            "IPSL_CM5A_MR_rcp45_ssp1",
            "MRI_CGCM3_rcp45_ssp1",
            "NorESM1_M_rcp45_ssp1"
        ]

        for scenario in scenarios:
            key = converter._get_combined_scenario_key(scenario)
            assert key == "RCP45_SSP1", f"Failed to extract key from {scenario}"

    def test_extract_rcp85_ssp2_key(self, tmp_path):
        """Test extraction from RCP8.5 SSP2 scenario."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        scenarios = [
            "CNRM_CM5_rcp85_ssp2",
            "HadGEM2_ES365_rcp85_ssp2",
            "IPSL_CM5A_MR_rcp85_ssp2",
            "MRI_CGCM3_rcp85_ssp2",
            "NorESM1_M_rcp85_ssp2"
        ]

        for scenario in scenarios:
            key = converter._get_combined_scenario_key(scenario)
            assert key == "RCP85_SSP2", f"Failed to extract key from {scenario}"

    def test_extract_rcp85_ssp3_key(self, tmp_path):
        """Test extraction from RCP8.5 SSP3 scenario."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        key = converter._get_combined_scenario_key("HadGEM2_ES365_rcp85_ssp3")
        assert key == "RCP85_SSP3"

    def test_extract_rcp85_ssp5_key(self, tmp_path):
        """Test extraction from RCP8.5 SSP5 scenario."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        key = converter._get_combined_scenario_key("NorESM1_M_rcp85_ssp5")
        assert key == "RCP85_SSP5"

    def test_invalid_scenario_format(self, tmp_path):
        """Test handling of invalid scenario names."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Test scenarios without RCP or SSP
        assert converter._get_combined_scenario_key("invalid_scenario") is None
        assert converter._get_combined_scenario_key("CNRM_CM5_only") is None
        assert converter._get_combined_scenario_key("rcp45_only") is None
        assert converter._get_combined_scenario_key("ssp1_only") is None

    def test_case_insensitive_extraction(self, tmp_path):
        """Test that extraction works with different cases."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Mixed case scenarios
        assert converter._get_combined_scenario_key("CNRM_CM5_RCP45_SSP1") == "RCP45_SSP1"
        assert converter._get_combined_scenario_key("cnrm_cm5_rcp45_ssp1") == "RCP45_SSP1"
        assert converter._get_combined_scenario_key("CNRM_CM5_Rcp45_Ssp1") == "RCP45_SSP1"


class TestGCMAggregation:
    """Test GCM aggregation produces correct statistical values."""

    @pytest.fixture
    def sample_gcm_data(self):
        """Create sample data representing multiple GCMs for the same RCP-SSP."""
        return {
            "CNRM_CM5_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [
                        {"_row": "cr", "cr": 1000.0, "ps": 100.0, "fr": 50.0, "ur": 25.0, "rg": 10.0},
                        {"_row": "ps", "cr": 150.0, "ps": 2000.0, "fr": 75.0, "ur": 30.0, "rg": 15.0}
                    ]
                }
            },
            "HadGEM2_ES365_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [
                        {"_row": "cr", "cr": 1100.0, "ps": 110.0, "fr": 60.0, "ur": 30.0, "rg": 12.0},
                        {"_row": "ps", "cr": 160.0, "ps": 2100.0, "fr": 80.0, "ur": 35.0, "rg": 18.0}
                    ]
                }
            },
            "IPSL_CM5A_MR_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [
                        {"_row": "cr", "cr": 900.0, "ps": 90.0, "fr": 40.0, "ur": 20.0, "rg": 8.0},
                        {"_row": "ps", "cr": 140.0, "ps": 1900.0, "fr": 70.0, "ur": 25.0, "rg": 12.0}
                    ]
                }
            },
            "MRI_CGCM3_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [
                        {"_row": "cr", "cr": 1050.0, "ps": 105.0, "fr": 55.0, "ur": 27.5, "rg": 11.0},
                        {"_row": "ps", "cr": 155.0, "ps": 2050.0, "fr": 77.5, "ur": 32.5, "rg": 16.5}
                    ]
                }
            },
            "NorESM1_M_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [
                        {"_row": "cr", "cr": 950.0, "ps": 95.0, "fr": 45.0, "ur": 22.5, "rg": 9.0},
                        {"_row": "ps", "cr": 145.0, "ps": 1950.0, "fr": 72.5, "ur": 27.5, "rg": 13.5}
                    ]
                }
            }
        }

    def test_mean_aggregation(self, sample_gcm_data, tmp_path):
        """Test that mean aggregation produces correct values."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Aggregate the data
        aggregated = converter._aggregate_by_scenario(sample_gcm_data)

        # Check RCP45_SSP1 aggregation exists
        assert "RCP45_SSP1" in aggregated
        assert "2012-2020" in aggregated["RCP45_SSP1"]
        assert "01001" in aggregated["RCP45_SSP1"]["2012-2020"]

        # Get aggregated transitions
        transitions = aggregated["RCP45_SSP1"]["2012-2020"]["01001"]

        # Find crop to crop transition
        cr_to_cr = None
        for trans in transitions:
            if trans.get("_row") == "cr":
                cr_to_cr = trans.get("cr")
                break

        # Expected mean: (1000 + 1100 + 900 + 1050 + 950) / 5 = 1000
        assert cr_to_cr is not None
        assert abs(cr_to_cr - 1000.0) < 0.01, f"Expected mean ~1000, got {cr_to_cr}"

    def test_statistics_calculation(self, sample_gcm_data, tmp_path):
        """Test that std_dev, min, and max are calculated correctly."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        aggregated = converter._aggregate_by_scenario(sample_gcm_data)
        transitions = aggregated["RCP45_SSP1"]["2012-2020"]["01001"]

        # Find crop transitions
        cr_trans = None
        for trans in transitions:
            if trans.get("_row") == "cr":
                cr_trans = trans
                break

        assert cr_trans is not None

        # Check statistics fields exist
        assert "cr_std" in cr_trans
        assert "cr_min" in cr_trans
        assert "cr_max" in cr_trans

        # Verify min/max values
        assert cr_trans["cr_min"] == 900.0  # Minimum value from IPSL
        assert cr_trans["cr_max"] == 1100.0  # Maximum value from HadGEM2

        # Verify standard deviation calculation accuracy
        # Values: [1000, 1100, 900, 1050, 950]
        # Pandas uses ddof=1 by default
        expected_std = pd.Series([1000.0, 1100.0, 900.0, 1050.0, 950.0]).std()
        assert abs(cr_trans["cr_std"] - expected_std) < 0.01, \
            f"Expected std ~{expected_std:.2f}, got {cr_trans['cr_std']}"

    def test_missing_gcm_handling(self, tmp_path):
        """Test handling when some GCMs are missing data."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Data with missing GCM for specific county
        incomplete_data = {
            "CNRM_CM5_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 1000.0}]
                }
            },
            "HadGEM2_ES365_rcp45_ssp1": {
                "2012-2020": {
                    # County 01001 missing for this GCM
                    "01002": [{"_row": "cr", "cr": 2000.0}]
                }
            },
            "IPSL_CM5A_MR_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 900.0}]
                }
            }
        }

        aggregated = converter._aggregate_by_scenario(incomplete_data)

        # Should still aggregate available data for 01001
        assert "01001" in aggregated["RCP45_SSP1"]["2012-2020"]
        transitions = aggregated["RCP45_SSP1"]["2012-2020"]["01001"]

        # Find crop transition
        cr_trans = None
        for trans in transitions:
            if trans.get("_row") == "cr":
                cr_trans = trans
                break

        # Mean should be (1000 + 900) / 2 = 950
        assert cr_trans is not None
        assert abs(cr_trans["cr"] - 950.0) < 0.01

    def test_data_conservation(self, sample_gcm_data, tmp_path):
        """Test that aggregation preserves data relationships."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        aggregated = converter._aggregate_by_scenario(sample_gcm_data)

        # Check all land use types are preserved
        transitions = aggregated["RCP45_SSP1"]["2012-2020"]["01001"]
        from_landuses = {t["_row"] for t in transitions}

        assert "cr" in from_landuses
        assert "ps" in from_landuses

        # Check all destination land uses are preserved
        for trans in transitions:
            if trans["_row"] == "cr":
                assert all(lu in trans for lu in ["cr", "ps", "fr", "ur", "rg"])


class TestOVERALLScenarioCreation:
    """Test OVERALL scenario creation (ensemble mean across all scenarios)."""

    @pytest.fixture
    def multi_scenario_data(self):
        """Create data with multiple RCP-SSP combinations."""
        return {
            # RCP4.5-SSP1 scenarios
            "CNRM_CM5_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 1000.0, "ps": 100.0}]
                }
            },
            "HadGEM2_ES365_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 1100.0, "ps": 110.0}]
                }
            },
            # RCP8.5-SSP2 scenarios
            "CNRM_CM5_rcp85_ssp2": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 1200.0, "ps": 120.0}]
                }
            },
            "HadGEM2_ES365_rcp85_ssp2": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 1300.0, "ps": 130.0}]
                }
            },
            # RCP8.5-SSP3 scenarios
            "CNRM_CM5_rcp85_ssp3": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 1400.0, "ps": 140.0}]
                }
            },
            # RCP8.5-SSP5 scenarios
            "NorESM1_M_rcp85_ssp5": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 1500.0, "ps": 150.0}]
                }
            }
        }

    def test_overall_scenario_created(self, multi_scenario_data, tmp_path):
        """Test that OVERALL scenario is created."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        aggregated = converter._aggregate_by_scenario(multi_scenario_data)

        # Check OVERALL scenario exists
        assert "OVERALL" in aggregated
        assert "2012-2020" in aggregated["OVERALL"]
        assert "01001" in aggregated["OVERALL"]["2012-2020"]

    def test_overall_scenario_mean(self, multi_scenario_data, tmp_path):
        """Test that OVERALL scenario calculates mean across all GCMs."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        aggregated = converter._aggregate_by_scenario(multi_scenario_data)
        transitions = aggregated["OVERALL"]["2012-2020"]["01001"]

        # Find crop transition
        cr_trans = None
        for trans in transitions:
            if trans.get("_row") == "cr":
                cr_trans = trans
                break

        # Expected mean across all 6 scenarios:
        # (1000 + 1100 + 1200 + 1300 + 1400 + 1500) / 6 = 1250
        assert cr_trans is not None
        assert abs(cr_trans["cr"] - 1250.0) < 0.01

        # Expected mean for pasture:
        # (100 + 110 + 120 + 130 + 140 + 150) / 6 = 125
        assert abs(cr_trans["ps"] - 125.0) < 0.01

    def test_all_scenarios_included_in_overall(self, tmp_path):
        """Test that all scenarios contribute to OVERALL."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Create data with distinct values to verify inclusion
        data = {}
        expected_sum = 0
        num_scenarios = 20  # 4 RCP-SSP combinations × 5 GCMs

        for i, (rcp, ssp) in enumerate([("rcp45", "ssp1"), ("rcp85", "ssp2"),
                                        ("rcp85", "ssp3"), ("rcp85", "ssp5")]):
            for j, gcm in enumerate(["CNRM_CM5", "HadGEM2_ES365", "IPSL_CM5A_MR",
                                     "MRI_CGCM3", "NorESM1_M"]):
                scenario_name = f"{gcm}_{rcp}_{ssp}"
                value = float((i * 5 + j + 1) * 100)  # Unique value for each
                data[scenario_name] = {
                    "2012-2020": {
                        "01001": [{"_row": "cr", "cr": value}]
                    }
                }
                expected_sum += value

        aggregated = converter._aggregate_by_scenario(data)
        transitions = aggregated["OVERALL"]["2012-2020"]["01001"]

        cr_trans = None
        for trans in transitions:
            if trans.get("_row") == "cr":
                cr_trans = trans
                break

        expected_mean = expected_sum / num_scenarios
        assert cr_trans is not None
        assert abs(cr_trans["cr"] - expected_mean) < 0.01


class TestStatisticalAccuracy:
    """Test statistical calculations are mathematically correct."""

    def test_standard_deviation_accuracy_simple(self, tmp_path):
        """Test standard deviation with known values."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Create data with known values for easy verification
        data = {
            "GCM1_rcp45_ssp1": {
                "2020": {"01001": [{"_row": "cr", "cr": 100.0, "ps": 20.0}]}
            },
            "GCM2_rcp45_ssp1": {
                "2020": {"01001": [{"_row": "cr", "cr": 200.0, "ps": 40.0}]}
            },
            "GCM3_rcp45_ssp1": {
                "2020": {"01001": [{"_row": "cr", "cr": 300.0, "ps": 60.0}]}
            }
        }

        aggregated = converter._aggregate_by_scenario(data)
        cr_trans = aggregated["RCP45_SSP1"]["2020"]["01001"][0]

        # Verify mean
        expected_mean = (100 + 200 + 300) / 3
        assert abs(cr_trans["cr"] - expected_mean) < 0.01

        # Verify standard deviation (pandas uses ddof=1 by default)
        values = [100.0, 200.0, 300.0]
        expected_std = pd.Series(values).std()  # Uses ddof=1 like the converter
        assert abs(cr_trans["cr_std"] - expected_std) < 0.01

        # Verify min/max
        assert cr_trans["cr_min"] == 100.0
        assert cr_trans["cr_max"] == 300.0

    def test_zero_standard_deviation(self, tmp_path):
        """Test std_dev when all values are identical."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # All GCMs have identical values
        data = {
            f"GCM{i}_rcp45_ssp1": {
                "2020": {"01001": [{"_row": "cr", "cr": 150.0}]}
            }
            for i in range(1, 4)
        }

        aggregated = converter._aggregate_by_scenario(data)
        cr_trans = aggregated["RCP45_SSP1"]["2020"]["01001"][0]

        # Standard deviation should be 0
        assert cr_trans["cr_std"] == 0.0
        assert cr_trans["cr"] == 150.0
        assert cr_trans["cr_min"] == 150.0
        assert cr_trans["cr_max"] == 150.0


class TestNumericalEdgeCases:
    """Test handling of numerical edge cases."""

    def test_very_large_numbers(self, tmp_path):
        """Test aggregation with very large acre values."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        large_value = 1e15  # Very large but valid number
        data = {
            "GCM1_rcp45_ssp1": {
                "2020": {"01001": [{"_row": "cr", "cr": large_value}]}
            },
            "GCM2_rcp45_ssp1": {
                "2020": {"01001": [{"_row": "cr", "cr": large_value * 2}]}
            }
        }

        aggregated = converter._aggregate_by_scenario(data)
        cr_trans = aggregated["RCP45_SSP1"]["2020"]["01001"][0]

        expected_mean = (large_value + large_value * 2) / 2
        assert abs(cr_trans["cr"] - expected_mean) < large_value * 0.001  # 0.1% tolerance

    def test_float_precision(self, tmp_path):
        """Test preservation of float precision in calculations."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Use values that might cause precision issues
        data = {
            "GCM1_rcp45_ssp1": {
                "2020": {"01001": [{"_row": "cr", "cr": 0.1}]}
            },
            "GCM2_rcp45_ssp1": {
                "2020": {"01001": [{"_row": "cr", "cr": 0.2}]}
            },
            "GCM3_rcp45_ssp1": {
                "2020": {"01001": [{"_row": "cr", "cr": 0.3}]}
            }
        }

        aggregated = converter._aggregate_by_scenario(data)
        cr_trans = aggregated["RCP45_SSP1"]["2020"]["01001"][0]

        # Check mean calculation doesn't lose precision
        expected_mean = 0.2  # (0.1 + 0.2 + 0.3) / 3
        assert abs(cr_trans["cr"] - expected_mean) < 1e-10


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_scenario_format_handling(self, tmp_path):
        """Test handling of scenarios that don't match RCP-SSP pattern."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        data = {
            "invalid_scenario": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 1000.0}]
                }
            },
            "CNRM_CM5_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 900.0}]
                }
            }
        }

        # Should not raise error, just skip invalid scenarios
        aggregated = converter._aggregate_by_scenario(data)

        # Valid scenario should still be processed
        assert "RCP45_SSP1" in aggregated

        # Invalid scenario should not create a key
        assert "invalid_scenario" not in aggregated

    def test_empty_dataset_handling(self, tmp_path):
        """Test handling of empty datasets."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Empty data - this should raise an error or return empty
        # The OVERALL scenario needs at least one source scenario
        aggregated = converter._aggregate_by_scenario({})

        # With no input scenarios, only OVERALL should exist but be empty
        assert "OVERALL" in aggregated
        assert aggregated["OVERALL"] == {}

    def test_minimal_dataset_handling(self, tmp_path):
        """Test handling of minimal valid dataset."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        data = {
            "CNRM_CM5_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 1000.0}]
                }
            }
        }

        aggregated = converter._aggregate_by_scenario(data)

        # Should process single scenario
        assert "RCP45_SSP1" in aggregated
        assert "OVERALL" in aggregated

        # Both should have the same value (single source)
        rcp_trans = aggregated["RCP45_SSP1"]["2012-2020"]["01001"][0]
        overall_trans = aggregated["OVERALL"]["2012-2020"]["01001"][0]

        assert rcp_trans["cr"] == overall_trans["cr"]

    def test_batch_size_limit(self, tmp_path):
        """Test that batch size limits are enforced."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "test.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Create batch data exceeding limit
        batch_data = []
        for i in range(converter.MAX_BATCH_SIZE + 1):
            batch_data.append({
                'transition_id': i,
                'scenario_id': 1,
                'time_id': 1,
                'geography_id': 1,
                'from_landuse_id': 1,
                'to_landuse_id': 1,
                'acres': 100.0,
                'transition_type': 'same'
            })

        # Should raise error when batch exceeds limit
        with pytest.raises(ValueError, match="Batch size .* exceeds maximum"):
            converter._write_and_copy_batch(batch_data, 0)

    def test_batch_processing_exact_size(self, tmp_path):
        """Test processing when batch exactly matches batch size."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "test.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Create batch data exactly at limit
        batch_data = []
        for i in range(100000):  # Common batch size
            batch_data.append({
                'transition_id': i,
                'scenario_id': 1,
                'time_id': 1,
                'geography_id': 1,
                'from_landuse_id': 1,
                'to_landuse_id': 1,
                'acres': 100.0,
                'transition_type': 'same'
            })

        # Should process without error (but will fail on missing connection)
        converter.conn = None  # Ensure connection is None
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute"):
            converter._write_and_copy_batch(batch_data, 0)

    def test_batch_processing_empty(self, tmp_path):
        """Test handling of empty batches."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "test.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Empty batch should process without error
        batch_data = []
        try:
            converter._write_and_copy_batch(batch_data, 0)
        except Exception as e:
            # Should handle gracefully, not crash
            assert "empty" not in str(e).lower()

    def test_file_size_validation(self, tmp_path):
        """Test that file size limits are enforced."""
        # Create a mock large file
        large_file = tmp_path / "large.json"
        large_file.write_text("x" * 100)  # Small file for testing

        output_file = tmp_path / "output.db"

        # Mock the file size check
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 11 * 1024 * 1024 * 1024  # 11GB

            with pytest.raises(ValueError, match="Input file too large"):
                converter = LanduseCombinedScenarioConverter(
                    str(large_file), str(output_file)
                )

    def test_path_traversal_prevention(self, tmp_path):
        """Test that path traversal attempts are blocked."""
        # Create a dummy input file
        input_file = tmp_path / "input.json"
        input_file.write_text("{}")

        # Test input path traversal
        with pytest.raises(ValueError, match="Path traversal detected"):
            converter = LanduseCombinedScenarioConverter(
                "../../../etc/passwd", str(tmp_path / "output.db")
            )

        # Test output path traversal
        with pytest.raises(ValueError, match="Path traversal detected"):
            converter = LanduseCombinedScenarioConverter(
                str(input_file), "../../../tmp/malicious.db"
            )


class TestDataConservation:
    """Test that data is conserved during aggregation."""

    def test_transition_count_preserved(self, tmp_path):
        """Test that number of transitions is preserved."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        data = {
            "CNRM_CM5_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [
                        {"_row": "cr", "cr": 100, "ps": 50, "fr": 25},
                        {"_row": "ps", "cr": 30, "ps": 200, "fr": 40},
                        {"_row": "fr", "cr": 10, "ps": 20, "fr": 300}
                    ]
                }
            },
            "HadGEM2_ES365_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [
                        {"_row": "cr", "cr": 110, "ps": 55, "fr": 27},
                        {"_row": "ps", "cr": 33, "ps": 210, "fr": 42},
                        {"_row": "fr", "cr": 11, "ps": 22, "fr": 310}
                    ]
                }
            }
        }

        aggregated = converter._aggregate_by_scenario(data)
        transitions = aggregated["RCP45_SSP1"]["2012-2020"]["01001"]

        # Should have same number of from_landuse types
        from_types = {t["_row"] for t in transitions}
        assert len(from_types) == 3
        assert from_types == {"cr", "ps", "fr"}

    def test_zero_values_preserved(self, tmp_path):
        """Test that zero values are preserved in aggregation."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        data = {
            "CNRM_CM5_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [
                        {"_row": "ur", "cr": 0.0, "ps": 0.0, "ur": 1000.0}
                    ]
                }
            },
            "HadGEM2_ES365_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [
                        {"_row": "ur", "cr": 0.0, "ps": 0.0, "ur": 1100.0}
                    ]
                }
            }
        }

        aggregated = converter._aggregate_by_scenario(data)
        transitions = aggregated["RCP45_SSP1"]["2012-2020"]["01001"]

        ur_trans = None
        for trans in transitions:
            if trans.get("_row") == "ur":
                ur_trans = trans
                break

        # Zero transitions should be preserved
        assert ur_trans["cr"] == 0.0
        assert ur_trans["ps"] == 0.0
        assert ur_trans["ur"] == 1050.0  # Mean of 1000 and 1100


class TestIntegrationWithRealData:
    """Integration tests using real data patterns."""

    def test_real_scenario_patterns(self, tmp_path):
        """Test with scenario patterns from actual database."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        # Use real scenario names from database
        real_scenarios = [
            "CNRM_CM5_rcp45_ssp1",
            "HadGEM2_ES365_rcp85_ssp2",
            "NorESM1_M_rcp85_ssp2",
            "CNRM_CM5_rcp85_ssp2",
            "HadGEM2_ES365_rcp85_ssp3",
            "IPSL_CM5A_MR_rcp85_ssp3",
            "MRI_CGCM3_rcp85_ssp3",
            "NorESM1_M_rcp85_ssp5",
            "IPSL_CM5A_MR_rcp85_ssp5",
            "NorESM1_M_rcp45_ssp1"
        ]

        # Create data with real scenario names
        data = {}
        for scenario in real_scenarios:
            data[scenario] = {
                "2012-2020": {
                    "01001": [{"_row": "cr", "cr": 1000.0}]
                }
            }

        aggregated = converter._aggregate_by_scenario(data)

        # Check expected combined scenarios exist
        assert "RCP45_SSP1" in aggregated
        assert "RCP85_SSP2" in aggregated
        assert "RCP85_SSP3" in aggregated
        assert "RCP85_SSP5" in aggregated
        assert "OVERALL" in aggregated

    def test_count_total_transitions(self, tmp_path):
        """Test transition counting for progress tracking."""
        input_file = tmp_path / "dummy.json"
        input_file.write_text("{}")
        output_file = tmp_path / "dummy.db"
        converter = LanduseCombinedScenarioConverter(str(input_file), str(output_file))

        data = {
            "CNRM_CM5_rcp45_ssp1": {
                "2012-2020": {
                    "01001": [
                        {"_row": "cr", "cr": 100, "ps": 50, "fr": 25,
                         "cr_std": 5, "ps_std": 2, "fr_std": 1,
                         "cr_min": 95, "ps_min": 48, "fr_min": 24,
                         "cr_max": 105, "ps_max": 52, "fr_max": 26}
                    ]
                }
            }
        }

        # Should only count actual transitions, not statistics
        count = converter._count_total_transitions(data)
        assert count == 3  # cr, ps, fr (not the _std, _min, _max fields)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
