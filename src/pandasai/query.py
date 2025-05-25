"""
Functions for querying the PandasAI semantic layers.
"""

import os
import pandas as pd
from pandasai import SmartDataframe
from pandasai.llm import BambooLLM
from dotenv import load_dotenv


def get_api_key():
    """Get the API key from environment variables."""
    load_dotenv(dotenv_path=".env")
    
    # Try PandasAI specific key first, then fallback to OpenAI key
    api_key = os.getenv("PANDABI_API_KEY")
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        
    if not api_key:
        raise ValueError(
            "No API key found in .env file. "
            "Please create a .env file with your PANDABI_API_KEY."
        )
    
    return api_key


def get_llm():
    """Get the LLM with the API key."""
    api_key = get_api_key()
    
    # Use BambooLLM with the provided API key
    # Note: PandasAI 3.0.0b17 uses BambooLLM instead of OpenAI directly
    return BambooLLM(api_key=api_key)


def load_datasets(parquet_dir="land_use_parquet"):
    """
    Load datasets from parquet files and create SmartDataframes.
    
    Args:
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        dict: Dictionary with SmartDataframe objects
    """
    llm = get_llm()
    
    # Paths for the parquet files
    transitions_parquet = f"{parquet_dir}/transitions_summary.parquet"
    transitions_changes_parquet = f"{parquet_dir}/transitions_changes_only.parquet"
    to_urban_parquet = f"{parquet_dir}/to_urban_transitions.parquet"
    from_forest_parquet = f"{parquet_dir}/from_forest_transitions.parquet"
    county_parquet = f"{parquet_dir}/county_transitions.parquet"
    county_changes_parquet = f"{parquet_dir}/county_transitions_changes_only.parquet"
    county_to_urban_parquet = f"{parquet_dir}/county_to_urban.parquet"
    county_from_forest_parquet = f"{parquet_dir}/county_from_forest.parquet"
    urbanization_parquet = f"{parquet_dir}/urbanization_trends.parquet"
    
    try:
        # Load the dataframes
        transitions_df = pd.read_parquet(transitions_parquet)
        transitions_changes_df = pd.read_parquet(transitions_changes_parquet)
        to_urban_df = pd.read_parquet(to_urban_parquet)
        from_forest_df = pd.read_parquet(from_forest_parquet)
        county_df = pd.read_parquet(county_parquet)
        county_changes_df = pd.read_parquet(county_changes_parquet)
        county_to_urban_df = pd.read_parquet(county_to_urban_parquet)
        county_from_forest_df = pd.read_parquet(county_from_forest_parquet)
        urbanization_df = pd.read_parquet(urbanization_parquet)
        
        # Create SmartDataframes
        transitions_smart_df = SmartDataframe(
            transitions_df,
            config={"llm": llm, "name": "Land Use Transitions"}
        )
        
        transitions_changes_smart_df = SmartDataframe(
            transitions_changes_df,
            config={"llm": llm, "name": "Land Use Transitions - Changes Only"}
        )
        
        to_urban_smart_df = SmartDataframe(
            to_urban_df,
            config={"llm": llm, "name": "Transitions TO Urban"}
        )
        
        from_forest_smart_df = SmartDataframe(
            from_forest_df,
            config={"llm": llm, "name": "Transitions FROM Forest"}
        )
        
        county_smart_df = SmartDataframe(
            county_df,
            config={"llm": llm, "name": "County Land Use Transitions"}
        )
        
        county_changes_smart_df = SmartDataframe(
            county_changes_df,
            config={"llm": llm, "name": "County Land Use Transitions - Changes Only"}
        )
        
        county_to_urban_smart_df = SmartDataframe(
            county_to_urban_df,
            config={"llm": llm, "name": "County Transitions TO Urban"}
        )
        
        county_from_forest_smart_df = SmartDataframe(
            county_from_forest_df,
            config={"llm": llm, "name": "County Transitions FROM Forest"}
        )
        
        urbanization_smart_df = SmartDataframe(
            urbanization_df,
            config={"llm": llm, "name": "Urbanization Trends"}
        )
        
        return {
            "transitions": transitions_smart_df,
            "transitions_changes": transitions_changes_smart_df,
            "to_urban": to_urban_smart_df,
            "from_forest": from_forest_smart_df,
            "county": county_smart_df,
            "county_changes": county_changes_smart_df,
            "county_to_urban": county_to_urban_smart_df,
            "county_from_forest": county_from_forest_smart_df,
            "urbanization": urbanization_smart_df
        }
    except Exception as e:
        raise RuntimeError(f"Failed to load datasets: {e}")


def query_transitions(query, parquet_dir="land_use_parquet"):
    """
    Query the land use transitions dataset with natural language.
    
    Args:
        query (str): Natural language query
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        object: Response from PandasAI
    """
    llm = get_llm()
    
    # Load the dataset
    transitions_df = pd.read_parquet(f"{parquet_dir}/transitions_summary.parquet")
    smart_df = SmartDataframe(
        transitions_df,
        config={"llm": llm, "name": "Land Use Transitions"}
    )
    
    # Query the dataset
    return smart_df.chat(query)


def query_transitions_changes(query, parquet_dir="land_use_parquet"):
    """
    Query the land use transitions dataset (changes only) with natural language.
    This dataset excludes records where from_category = to_category (no change).
    
    Args:
        query (str): Natural language query
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        object: Response from PandasAI
    """
    llm = get_llm()
    
    # Load the dataset
    transitions_df = pd.read_parquet(f"{parquet_dir}/transitions_changes_only.parquet")
    smart_df = SmartDataframe(
        transitions_df,
        config={"llm": llm, "name": "Land Use Transitions - Changes Only"}
    )
    
    # Query the dataset
    return smart_df.chat(query)


def query_to_urban(query, parquet_dir="land_use_parquet"):
    """
    Query the transitions TO Urban dataset with natural language.
    This dataset contains only transitions where land use changes TO Urban.
    
    Args:
        query (str): Natural language query
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        object: Response from PandasAI
    """
    llm = get_llm()
    
    # Load the dataset
    to_urban_df = pd.read_parquet(f"{parquet_dir}/to_urban_transitions.parquet")
    smart_df = SmartDataframe(
        to_urban_df,
        config={"llm": llm, "name": "Transitions TO Urban"}
    )
    
    # Query the dataset
    return smart_df.chat(query)


def query_from_forest(query, parquet_dir="land_use_parquet"):
    """
    Query the transitions FROM Forest dataset with natural language.
    This dataset contains only transitions where land use changes FROM Forest.
    
    Args:
        query (str): Natural language query
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        object: Response from PandasAI
    """
    llm = get_llm()
    
    # Load the dataset
    from_forest_df = pd.read_parquet(f"{parquet_dir}/from_forest_transitions.parquet")
    smart_df = SmartDataframe(
        from_forest_df,
        config={"llm": llm, "name": "Transitions FROM Forest"}
    )
    
    # Query the dataset
    return smart_df.chat(query)


def query_county_transitions(query, parquet_dir="land_use_parquet"):
    """
    Query the county-level transitions dataset with natural language.
    
    Args:
        query (str): Natural language query
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        object: Response from PandasAI
    """
    llm = get_llm()
    
    # Load the dataset
    county_df = pd.read_parquet(f"{parquet_dir}/county_transitions.parquet")
    smart_df = SmartDataframe(
        county_df,
        config={"llm": llm, "name": "County Land Use Transitions"}
    )
    
    # Query the dataset
    return smart_df.chat(query)


def query_county_transitions_changes(query, parquet_dir="land_use_parquet"):
    """
    Query the county-level transitions dataset (changes only) with natural language.
    This dataset excludes records where from_category = to_category (no change).
    
    Args:
        query (str): Natural language query
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        object: Response from PandasAI
    """
    llm = get_llm()
    
    # Load the dataset
    county_df = pd.read_parquet(f"{parquet_dir}/county_transitions_changes_only.parquet")
    smart_df = SmartDataframe(
        county_df,
        config={"llm": llm, "name": "County Land Use Transitions - Changes Only"}
    )
    
    # Query the dataset
    return smart_df.chat(query)


def query_county_to_urban(query, parquet_dir="land_use_parquet"):
    """
    Query the county-level transitions TO Urban dataset with natural language.
    This dataset contains only county-level transitions where land use changes TO Urban.
    
    Args:
        query (str): Natural language query
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        object: Response from PandasAI
    """
    llm = get_llm()
    
    # Load the dataset
    county_to_urban_df = pd.read_parquet(f"{parquet_dir}/county_to_urban.parquet")
    smart_df = SmartDataframe(
        county_to_urban_df,
        config={"llm": llm, "name": "County Transitions TO Urban"}
    )
    
    # Query the dataset
    return smart_df.chat(query)


def query_county_from_forest(query, parquet_dir="land_use_parquet"):
    """
    Query the county-level transitions FROM Forest dataset with natural language.
    This dataset contains only county-level transitions where land use changes FROM Forest.
    
    Args:
        query (str): Natural language query
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        object: Response from PandasAI
    """
    llm = get_llm()
    
    # Load the dataset
    county_from_forest_df = pd.read_parquet(f"{parquet_dir}/county_from_forest.parquet")
    smart_df = SmartDataframe(
        county_from_forest_df,
        config={"llm": llm, "name": "County Transitions FROM Forest"}
    )
    
    # Query the dataset
    return smart_df.chat(query)


def query_urbanization_trends(query, parquet_dir="land_use_parquet"):
    """
    Query the urbanization trends dataset with natural language.
    
    Args:
        query (str): Natural language query
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        object: Response from PandasAI
    """
    llm = get_llm()
    
    # Load the dataset
    urbanization_df = pd.read_parquet(f"{parquet_dir}/urbanization_trends.parquet")
    smart_df = SmartDataframe(
        urbanization_df,
        config={"llm": llm, "name": "Urbanization Trends"}
    )
    
    # Query the dataset
    return smart_df.chat(query)


def multi_dataset_query(query, datasets=None, parquet_dir="land_use_parquet"):
    """
    Query multiple datasets with natural language.
    
    Args:
        query (str): Natural language query
        datasets (list, optional): List of dataset names to include
                                  (transitions, transitions_changes, to_urban, from_forest,
                                   county, county_changes, county_to_urban, county_from_forest, 
                                   urbanization)
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        object: Response from PandasAI
    """
    # Default to all datasets if none specified
    if not datasets:
        datasets = ["transitions_changes", "to_urban", "from_forest", "county_changes", "urbanization"]
    
    # Validate dataset names
    valid_names = [
        "transitions", "transitions_changes", "to_urban", "from_forest",
        "county", "county_changes", "county_to_urban", "county_from_forest", 
        "urbanization"
    ]
    for name in datasets:
        if name not in valid_names:
            raise ValueError(f"Invalid dataset name: {name}. "
                           f"Valid names are: {', '.join(valid_names)}")
    
    # Load all datasets
    all_datasets = load_datasets(parquet_dir)
    
    # Filter to selected datasets
    selected_datasets = [all_datasets[name] for name in datasets]
    
    # For now, just use the first dataset since pandasai 2.4.2 doesn't support 
    # multi-dataset querying in the same way
    primary_dataset = selected_datasets[0]
    
    return primary_dataset.chat(f"Query across multiple datasets: {query}") 