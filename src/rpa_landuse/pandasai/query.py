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


def load_datasets(parquet_dir="semantic_layers/base_analysis"):
    """
    Load datasets from parquet files and create SmartDataframes.
    
    Args:
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        dict: Dictionary with SmartDataframe objects
    """
    llm = get_llm()
    
    # Paths for the parquet files
    reference_parquet = f"{parquet_dir}/reference.parquet"
    transitions_changes_parquet = f"{parquet_dir}/gross_change_ensemble_all.parquet"
    to_urban_parquet = f"{parquet_dir}/to_urban_transitions.parquet"
    from_forest_parquet = f"{parquet_dir}/from_forest_transitions.parquet"
    county_parquet = f"{parquet_dir}/county_transitions.parquet"
    county_changes_parquet = f"{parquet_dir}/county_transitions_changes_only.parquet"
    county_to_urban_parquet = f"{parquet_dir}/county_to_urban.parquet"
    county_from_forest_parquet = f"{parquet_dir}/county_from_forest.parquet"
    urbanization_parquet = f"{parquet_dir}/urbanization_trends.parquet"
    
    try:
        # Load the dataframes
        reference_df = pd.read_parquet(reference_parquet)
        transitions_changes_df = pd.read_parquet(transitions_changes_parquet)
        to_urban_df = pd.read_parquet(to_urban_parquet)
        from_forest_df = pd.read_parquet(from_forest_parquet)
        county_df = pd.read_parquet(county_parquet)
        county_changes_df = pd.read_parquet(county_changes_parquet)
        county_to_urban_df = pd.read_parquet(county_to_urban_parquet)
        county_from_forest_df = pd.read_parquet(county_from_forest_parquet)
        urbanization_df = pd.read_parquet(urbanization_parquet)
        
        # Create SmartDataframes
        reference_smart_df = SmartDataframe(
            reference_df,
            config={"llm": llm, "name": "Reference Information"}
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
            "reference": reference_smart_df,
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


def query_transitions(query, parquet_dir="semantic_layers/base_analysis"):
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
    transitions_df = pd.read_parquet(f"{parquet_dir}/gross_change_ensemble_all.parquet")
    smart_df = SmartDataframe(
        transitions_df,
        config={"llm": llm, "name": "Land Use Transitions - Ensemble Changes"}
    )
    
    # Query the dataset
    return smart_df.chat(query)


def query_to_urban(query, parquet_dir="semantic_layers/base_analysis"):
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


def query_from_forest(query, parquet_dir="semantic_layers/base_analysis"):
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


def query_county_transitions(query, parquet_dir="semantic_layers/base_analysis"):
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


def query_county_to_urban(query, parquet_dir="semantic_layers/base_analysis"):
    """
    Query the county-level transitions TO Urban dataset with natural language.
    
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


def query_county_from_forest(query, parquet_dir="semantic_layers/base_analysis"):
    """
    Query the county-level transitions FROM Forest dataset with natural language.
    
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


def query_urbanization_trends(query, parquet_dir="semantic_layers/base_analysis"):
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


def multi_dataset_query(query, datasets=None, parquet_dir="semantic_layers/base_analysis"):
    """
    Run a query against multiple datasets and return all results.
    
    Args:
        query (str): Natural language query
        datasets (list): List of dataset names to query, if None queries all
        parquet_dir (str): Directory containing parquet files
        
    Returns:
        dict: Dictionary with responses from each dataset
    """
    if datasets is None:
        datasets = [
            "transitions_changes",
            "to_urban",
            "from_forest",
            "county",
            "county_to_urban",
            "county_from_forest",
            "urbanization"
        ]
    
    # Load all datasets
    all_datasets = load_datasets(parquet_dir)
    
    # Query each dataset
    results = {}
    for dataset_name in datasets:
        if dataset_name in all_datasets:
            print(f"Querying {dataset_name}...")
            try:
                results[dataset_name] = all_datasets[dataset_name].chat(query)
            except Exception as e:
                results[dataset_name] = f"Error: {e}"
        else:
            results[dataset_name] = f"Dataset '{dataset_name}' not found"
    
    return results 