"""RPA 2020 Assessment domain context library for progressive disclosure.

This module contains structured domain knowledge from the USDA Forest Service
2020 RPA Assessment that can be injected into agent prompts based on query context.
Concepts are only explained when first relevant, avoiding information overload.
"""

from typing import Any

# US State name to abbreviation mapping for geography detection
US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

# Region definitions for geographic queries
US_REGIONS = {
    "northeast": ["CT", "ME", "MA", "NH", "RI", "VT", "NJ", "NY", "PA"],
    "southeast": ["AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "SC", "TN", "VA", "WV"],
    "midwest": ["IL", "IN", "IA", "KS", "MI", "MN", "MO", "NE", "ND", "OH", "SD", "WI"],
    "southwest": ["AZ", "NM", "OK", "TX"],
    "west": ["CO", "ID", "MT", "NV", "UT", "WY"],
    "pacific": ["CA", "OR", "WA", "AK", "HI"],
}


# Core RPA domain knowledge for progressive disclosure
RPA_CONTEXT_LIBRARY: dict[str, dict[str, Any]] = {
    # === FUNDAMENTAL ASSUMPTIONS ===
    "irreversibility": {
        "concept": "Development Irreversibility",
        "explanation": (
            "A KEY ASSUMPTION of RPA projections: Once land converts to urban/developed use, "
            "it stays urban permanently. This reflects the high economic and practical barriers "
            "to converting developed areas back to agricultural or natural uses. Urban areas can "
            "only increase or remain stable - all urbanization comes from conversion of agricultural "
            "or natural lands."
        ),
        "triggers": ["urban", "development", "irreversible", "permanent", "converted to urban"],
        "category": "assumption",
        "priority": 1,  # High priority - fundamental understanding
    },
    "private_land": {
        "concept": "Private Land Focus",
        "explanation": (
            "RPA projections cover PRIVATE LANDS ONLY (~70% of U.S. land area). Public lands "
            "(national forests, BLM, parks) are managed under different objectives and assumed "
            "static in these projections. This focuses analysis on lands most subject to economic "
            "development pressures and market-driven land use decisions."
        ),
        "triggers": ["total", "all land", "national", "entire", "public", "federal"],
        "category": "assumption",
        "priority": 1,
    },
    "historical_calibration": {
        "concept": "Historical Calibration",
        "explanation": (
            "The econometric model is calibrated to observed land use transitions from 2001-2012 "
            "using National Resources Inventory (NRI) data. It assumes continuation of historical "
            "patterns and relationships between drivers (population, income, climate) and land use "
            "change. The projections are POLICY-NEUTRAL - they don't incorporate future policy changes."
        ),
        "triggers": ["historical", "calibration", "model", "baseline", "nri", "methodology"],
        "category": "methodology",
        "priority": 2,
    },

    # === SCENARIO FRAMEWORK ===
    "scenario_framework": {
        "concept": "RPA Scenario Framework",
        "explanation": (
            "RPA uses 20 integrated scenarios combining climate and socioeconomic futures:\n"
            "- 5 Global Climate Models (GCMs) provide climate projections\n"
            "- 4 RCP/SSP pathways define emissions and socioeconomic trajectories\n\n"
            "The 4 main scenarios (user-friendly names):\n"
            "- LM (Low): RCP4.5 + SSP1 - Sustainability focus, low emissions, moderate growth\n"
            "- HM (High-Moderate): RCP8.5 + SSP2 - Business-as-usual trajectory\n"
            "- HL (High-Low): RCP8.5 + SSP3 - High emissions, slow fragmented growth\n"
            "- HH (High-High): RCP8.5 + SSP5 - Rapid fossil-fueled development"
        ),
        "triggers": ["scenario", "LM", "HM", "HL", "HH", "compare", "rcp", "ssp"],
        "category": "scenario",
        "priority": 1,
    },
    "scenario_lm": {
        "concept": "LM (Low) Scenario",
        "explanation": (
            "LM = RCP4.5 + SSP1 'Sustainability' pathway:\n"
            "- Lower emissions trajectory (peak and decline)\n"
            "- Moderate population and economic growth\n"
            "- Emphasis on sustainability and reduced resource use\n"
            "- Generally shows LESS urban expansion and land use pressure"
        ),
        "triggers": ["LM scenario", "low scenario", "sustainability", "RCP45", "SSP1"],
        "category": "scenario",
        "priority": 2,
    },
    "scenario_hh": {
        "concept": "HH (High-High) Scenario",
        "explanation": (
            "HH = RCP8.5 + SSP5 'Fossil-fueled Development' pathway:\n"
            "- Highest emissions trajectory (continued growth)\n"
            "- High population and economic growth\n"
            "- Energy-intensive, consumption-focused development\n"
            "- Shows MOST urban expansion and agricultural land conversion"
        ),
        "triggers": ["HH scenario", "high scenario", "fossil", "maximum", "RCP85", "SSP5"],
        "category": "scenario",
        "priority": 2,
    },

    # === LAND USE PATTERNS ===
    "forest_to_urban": {
        "concept": "Forest-to-Urban Conversion Pattern",
        "explanation": (
            "A DOMINANT HISTORICAL PATTERN: ~46% of new developed/urban land comes from "
            "forest conversion. This is particularly significant in the Eastern U.S. where "
            "forests often border expanding metropolitan areas. The pattern reflects suburban "
            "sprawl into forested exurban zones."
        ),
        "triggers": ["forest", "urban", "conversion", "source", "where does urban", "losing forest"],
        "category": "pattern",
        "priority": 1,
    },
    "agricultural_loss": {
        "concept": "Agricultural Land Loss",
        "explanation": (
            "Agricultural lands (cropland and pasture) also contribute significantly to urban "
            "expansion. Pasture is particularly vulnerable in urban fringe areas as it often "
            "represents lower-value agricultural use that can be economically displaced by "
            "development pressure. Cropland loss varies by region and soil quality."
        ),
        "triggers": ["crop", "pasture", "agricultural", "farmland", "farming", "agriculture"],
        "category": "pattern",
        "priority": 2,
    },
    "rangeland_dynamics": {
        "concept": "Rangeland Dynamics",
        "explanation": (
            "Rangelands (natural grasslands and shrublands) in the Western U.S. have complex "
            "dynamics. They can convert to cropland when irrigation is available, to urban use "
            "near expanding cities, or persist as low-intensity grazing land. Climate impacts "
            "on rangeland productivity vary significantly by scenario."
        ),
        "triggers": ["rangeland", "grassland", "western", "grazing", "range"],
        "category": "pattern",
        "priority": 2,
    },

    # === DATA STRUCTURE ===
    "county_resolution": {
        "concept": "County-Level Resolution",
        "explanation": (
            "All RPA projections are at COUNTY LEVEL - 3,075 U.S. counties with full spatial "
            "coverage. This enables local and regional analysis while maintaining computational "
            "feasibility. County-level aggregation smooths over parcel-level variability while "
            "preserving important geographic patterns."
        ),
        "triggers": ["county", "local", "specific area", "geographic", "where", "region"],
        "category": "data",
        "priority": 2,
    },
    "time_periods": {
        "concept": "Decadal Time Periods",
        "explanation": (
            "Projections are available at decadal intervals from 2020 to 2070:\n"
            "- 2020 (baseline)\n- 2030\n- 2040\n- 2050\n- 2060\n- 2070\n\n"
            "The 2020 baseline represents calibrated starting conditions. Each subsequent "
            "decade shows cumulative changes from that baseline."
        ),
        "triggers": ["2020", "2030", "2040", "2050", "2060", "2070", "year", "decade", "trend", "time"],
        "category": "data",
        "priority": 2,
    },
    "transition_matrix": {
        "concept": "Land Use Transition Matrix",
        "explanation": (
            "The database stores TRANSITIONS between land use types - how many acres changed "
            "from one type to another. The 5 land use categories are:\n"
            "- cr (Crop): Agricultural cropland\n"
            "- ps (Pasture): Livestock grazing, hay\n"
            "- fr (Forest): Forested areas\n"
            "- ur (Urban): Developed/built areas\n"
            "- rg (Rangeland): Natural grasslands\n\n"
            "Query for specific transitions using from_landuse and to_landuse fields."
        ),
        "triggers": ["transition", "change", "convert", "from", "to", "matrix"],
        "category": "data",
        "priority": 2,
    },

    # === REGIONAL PATTERNS ===
    "southeast_hotspot": {
        "concept": "Southeast Urbanization Hotspot",
        "explanation": (
            "The Southeast U.S. is a major urbanization hotspot, with states like Georgia, "
            "Florida, North Carolina, and Texas showing high projected urban expansion. "
            "Forest loss is particularly significant as suburban development extends into "
            "forested areas surrounding major metropolitan regions."
        ),
        "triggers": ["southeast", "georgia", "florida", "north carolina", "texas", "south"],
        "category": "regional",
        "priority": 3,
    },
    "midwest_agriculture": {
        "concept": "Midwest Agricultural Dynamics",
        "explanation": (
            "The Midwest sees complex agricultural dynamics with some cropland-pasture "
            "interchange and targeted urban expansion around cities. Climate scenarios "
            "significantly affect agricultural viability, with some scenarios projecting "
            "northward shifts in optimal growing conditions."
        ),
        "triggers": ["midwest", "iowa", "illinois", "kansas", "nebraska", "corn belt"],
        "category": "regional",
        "priority": 3,
    },
}


def get_concept_explanation(concept_key: str) -> str | None:
    """Get the explanation for a specific RPA concept.

    Args:
        concept_key: Key from RPA_CONTEXT_LIBRARY.

    Returns:
        The explanation string if found, None otherwise.
    """
    if concept_key in RPA_CONTEXT_LIBRARY:
        return RPA_CONTEXT_LIBRARY[concept_key]["explanation"]
    return None


def detect_relevant_concepts(query: str, already_explained: list[str]) -> list[str]:
    """Detect which RPA concepts are relevant to a query.

    Uses trigger words to identify concepts that should be explained.
    Excludes concepts already explained in this session.

    Args:
        query: User's natural language query.
        already_explained: List of concept keys already explained.

    Returns:
        List of relevant concept keys sorted by priority.
    """
    query_lower = query.lower()
    relevant = []

    for concept_key, info in RPA_CONTEXT_LIBRARY.items():
        # Skip if already explained
        if concept_key in already_explained:
            continue

        # Check if any trigger word appears in the query
        triggers = info.get("triggers", [])
        if any(trigger.lower() in query_lower for trigger in triggers):
            relevant.append((concept_key, info.get("priority", 5)))

    # Sort by priority (lower = more important)
    relevant.sort(key=lambda x: x[1])

    return [concept_key for concept_key, _ in relevant]


def detect_scenarios(query: str) -> list[str]:
    """Detect which climate scenarios are mentioned in a query.

    Args:
        query: User's natural language query.

    Returns:
        List of detected scenario codes (LM, HM, HL, HH).
    """
    query_upper = query.upper()
    scenarios = []

    scenario_patterns = {
        "LM": ["LM", "LOW", "SUSTAINABILITY", "RCP45", "RCP4.5", "SSP1"],
        "HM": ["HM", "HIGH-MODERATE", "BUSINESS AS USUAL", "RCP85_SSP2", "SSP2"],
        "HL": ["HL", "HIGH-LOW", "FRAGMENTED", "SSP3"],
        "HH": ["HH", "HIGH-HIGH", "FOSSIL", "MAXIMUM", "SSP5"],
    }

    for scenario, patterns in scenario_patterns.items():
        if any(pattern in query_upper for pattern in patterns):
            scenarios.append(scenario)

    return scenarios


def detect_geography(query: str) -> list[str]:
    """Detect geographic entities (states, regions) mentioned in a query.

    Args:
        query: User's natural language query.

    Returns:
        List of detected state abbreviations.
    """
    query_lower = query.lower()
    detected = []

    # Check for state names
    for state_name, abbrev in US_STATES.items():
        if state_name in query_lower:
            detected.append(abbrev)

    # Check for state abbreviations (exact match with strict filtering)
    # Common words that are also state abbreviations - don't match these
    common_words = {"in", "or", "me", "hi", "ok", "la", "de", "pa", "ma", "id", "oh", "md", "co", "va"}
    words = query_lower.replace(",", " ").replace(".", " ").split()
    for word in words:
        word_lower = word.lower()
        word_upper = word.upper()
        # Skip common English words that happen to be state abbreviations
        if word_lower in common_words:
            continue
        if word_upper in US_STATES.values() and word_upper not in detected:
            detected.append(word_upper)

    # Check for region names
    for region_name, states in US_REGIONS.items():
        if region_name in query_lower:
            for state in states:
                if state not in detected:
                    detected.append(state)

    return detected


def detect_time_range(query: str) -> tuple[int, int] | None:
    """Detect time range mentioned in a query.

    Args:
        query: User's natural language query.

    Returns:
        Tuple of (start_year, end_year) if detected, None otherwise.
    """
    import re

    years_found = []
    valid_years = {2020, 2030, 2040, 2050, 2060, 2070}

    # Find all 4-digit numbers that could be years
    year_matches = re.findall(r"\b(20[2-7]0)\b", query)
    for match in year_matches:
        year = int(match)
        if year in valid_years:
            years_found.append(year)

    if len(years_found) >= 2:
        return (min(years_found), max(years_found))
    elif len(years_found) == 1:
        return (years_found[0], years_found[0])

    return None


def classify_query_type(query: str) -> str:
    """Classify the type of query for context-appropriate responses.

    Args:
        query: User's natural language query.

    Returns:
        Query type: "aggregate", "comparison", "geographic", "temporal", or "general".
    """
    query_lower = query.lower()

    # Check for comparison queries
    comparison_words = ["compare", "difference", "versus", "vs", "between", "which scenario"]
    if any(word in query_lower for word in comparison_words):
        return "comparison"

    # Check for geographic queries
    geo_words = ["where", "state", "county", "region", "geographic", "location"]
    if any(word in query_lower for word in geo_words):
        return "geographic"

    # Check for temporal queries
    time_words = ["trend", "over time", "change", "decade", "year", "by 2050", "by 2070"]
    if any(word in query_lower for word in time_words):
        return "temporal"

    # Check for aggregate queries
    agg_words = ["total", "sum", "average", "mean", "how much", "how many"]
    if any(word in query_lower for word in agg_words):
        return "aggregate"

    return "general"


def build_context_injection(
    query: str,
    explained_concepts: list[str],
    max_concepts: int = 3,
) -> tuple[str, list[str]]:
    """Build context injection text for a query with progressive disclosure.

    Only injects concepts that are relevant and haven't been explained yet.

    Args:
        query: User's natural language query.
        explained_concepts: Concepts already explained in session.
        max_concepts: Maximum number of new concepts to inject.

    Returns:
        Tuple of (context_text, newly_explained_concepts).
    """
    relevant = detect_relevant_concepts(query, explained_concepts)

    if not relevant:
        return "", []

    # Limit to max_concepts
    concepts_to_explain = relevant[:max_concepts]

    context_parts = ["RELEVANT RPA CONTEXT FOR THIS QUERY:"]
    for concept_key in concepts_to_explain:
        info = RPA_CONTEXT_LIBRARY[concept_key]
        context_parts.append(f"\n{info['concept']}:\n{info['explanation']}")

    return "\n".join(context_parts), concepts_to_explain
