#!/usr/bin/env python3
"""Fix missing state names in the geography dimension table."""

import duckdb

# State FIPS code to name mapping
STATE_FIPS_TO_NAME = {
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
    "72": "Puerto Rico",
    "78": "Virgin Islands",
}

# Region mapping
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
    "Washington": "West",
    "Puerto Rico": "Territory",
    "Virgin Islands": "Territory",
}


def fix_state_names(db_path="data/processed/landuse_analytics.duckdb"):
    """Update missing state names and regions in dim_geography table."""

    print(f"Connecting to database: {db_path}")
    conn = duckdb.connect(database=db_path, read_only=False)

    try:
        # Check current state of the data
        result = conn.execute("""
            SELECT COUNT(*) as total,
                   COUNT(state_name) as with_name,
                   COUNT(region) as with_region
            FROM dim_geography
        """).fetchone()

        print(f"Current status: {result[0]} total records, {result[1]} with state names, {result[2]} with regions")

        # Update state names based on FIPS codes
        updates_made = 0
        for fips_code, state_name in STATE_FIPS_TO_NAME.items():
            region = STATE_TO_REGION.get(state_name, "Unknown")

            conn.execute(
                """
                UPDATE dim_geography
                SET state_name = ?, region = ?
                WHERE state_code = ?
            """,
                (state_name, region, fips_code),
            )

            affected = conn.execute("SELECT COUNT(*) FROM dim_geography WHERE state_code = ?", (fips_code,)).fetchone()[
                0
            ]
            if affected > 0:
                updates_made += affected
                print(f"Updated {affected} records for {state_name} (FIPS: {fips_code}, Region: {region})")

        # Also update county names if we have a mapping (simplified example for a few counties)
        # In production, you'd load this from a complete FIPS database
        print("\nUpdating sample county names...")
        sample_counties = [
            ("06037", "Los Angeles County"),
            ("48201", "Harris County"),
            ("17031", "Cook County"),
            ("04013", "Maricopa County"),
            ("06073", "San Diego County"),
            ("06059", "Orange County"),
            ("12086", "Miami-Dade County"),
            ("48113", "Dallas County"),
            ("36047", "Kings County"),
            ("06065", "Riverside County"),
        ]

        for fips, county_name in sample_counties:
            conn.execute(
                """
                UPDATE dim_geography
                SET county_name = ?
                WHERE fips_code = ?
            """,
                (county_name, fips),
            )

        # Commit changes
        conn.commit()

        # Verify the updates
        result = conn.execute("""
            SELECT COUNT(*) as total,
                   COUNT(state_name) as with_name,
                   COUNT(region) as with_region
            FROM dim_geography
        """).fetchone()

        print(f"\nFinal status: {result[0]} total records, {result[1]} with state names, {result[2]} with regions")

        # Show sample of updated data
        print("\nSample of updated records:")
        sample = conn.execute("""
            SELECT fips_code, county_name, state_code, state_name, region
            FROM dim_geography
            WHERE state_name IS NOT NULL
            LIMIT 5
        """).fetchall()

        for row in sample:
            print(f"  {row[0]}: {row[1]}, {row[3]}, {row[4]}")

        print(f"\nSuccessfully updated {updates_made} records!")

    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/landuse_analytics.duckdb"
    fix_state_names(db_path)
