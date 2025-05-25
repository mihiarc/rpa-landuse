"""
FIPS Code utilities for mapping FIPS codes to state and county names.

This module provides dictionaries and functions to work with US FIPS codes.
"""

# Mapping of state FIPS codes to state names
STATE_FIPS = {
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
    "60": "American Samoa",
    "66": "Guam",
    "69": "Commonwealth of the Northern Mariana Islands",
    "72": "Puerto Rico",
    "78": "Virgin Islands"
}

# Dictionary mapping states to their region
STATE_TO_REGION = {
    "Connecticut": "Northeast",
    "Maine": "Northeast",
    "Massachusetts": "Northeast",
    "New Hampshire": "Northeast",
    "Rhode Island": "Northeast",
    "Vermont": "Northeast",
    "New Jersey": "Northeast",
    "New York": "Northeast",
    "Pennsylvania": "Northeast",
    "Illinois": "Midwest",
    "Indiana": "Midwest",
    "Michigan": "Midwest",
    "Ohio": "Midwest",
    "Wisconsin": "Midwest",
    "Iowa": "Midwest",
    "Kansas": "Midwest",
    "Minnesota": "Midwest",
    "Missouri": "Midwest",
    "Nebraska": "Midwest",
    "North Dakota": "Midwest",
    "South Dakota": "Midwest",
    "Delaware": "South",
    "Florida": "South",
    "Georgia": "South",
    "Maryland": "South",
    "North Carolina": "South",
    "South Carolina": "South",
    "Virginia": "South",
    "District of Columbia": "South",
    "West Virginia": "South",
    "Alabama": "South",
    "Kentucky": "South",
    "Mississippi": "South",
    "Tennessee": "South",
    "Arkansas": "South",
    "Louisiana": "South",
    "Oklahoma": "South",
    "Texas": "South",
    "Arizona": "West",
    "Colorado": "West",
    "Idaho": "West",
    "Montana": "West",
    "Nevada": "West",
    "New Mexico": "West",
    "Utah": "West",
    "Wyoming": "West",
    "Alaska": "West",
    "California": "West",
    "Hawaii": "West",
    "Oregon": "West",
    "Washington": "West"
}

def parse_fips(fips_code):
    """
    Parse a 5-digit FIPS code into state and county components.
    
    Args:
        fips_code: 5-digit FIPS code as string
        
    Returns:
        Tuple of (state_fips, county_fips)
    """
    if not fips_code or len(fips_code) != 5:
        return None, None
    
    state_fips = fips_code[:2]
    county_fips = fips_code[2:]
    
    return state_fips, county_fips

def get_state_from_fips(fips_code):
    """
    Get state name from a FIPS code.
    
    Args:
        fips_code: 5-digit FIPS code as string
        
    Returns:
        State name or None if not found
    """
    state_fips, _ = parse_fips(fips_code)
    return STATE_FIPS.get(state_fips)

def get_region_from_state(state_name):
    """
    Get region from state name.
    
    Args:
        state_name: Name of the state
        
    Returns:
        Region name or None if not found
    """
    return STATE_TO_REGION.get(state_name) 