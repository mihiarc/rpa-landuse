#!/usr/bin/env python3
"""
Natural Language Query Module for RPA Land Use Projections

This module uses pandasai to allow users to ask natural language questions
about the RPA land use projections data.
"""

import pandas as pd
from pandasai import SmartDataframe
from pandasai_openai import OpenAI
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
import matplotlib.pyplot as plt

# Add src directory to path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from src.db.database import DBManager

load_dotenv()

class NaturalLanguageQuery:
    """
    A class to handle natural language queries about the RPA land use data.
    Enhanced for PandasAI 3.0 and Streamlit integration.
    """

    def __init__(self, db_path="data/database/rpa.db"):
        """
        Initializes the NaturalLanguageQuery class.

        Args:
            db_path (str): The path to the DuckDB database.
        """
        self.db_path = db_path
        self.llm = OpenAI()
        self.df = self._load_data()
        
        # Create exports directory if it doesn't exist
        os.makedirs("exports/charts", exist_ok=True)

    def _load_data(self):
        """
        Loads the data from the DuckDB database.

        Returns:
            pd.DataFrame: A pandas DataFrame containing the data.
        """
        try:
            # Query the county_level_transitions view
            query = "SELECT * FROM county_level_transitions"
            df = DBManager.query_df(query)
            
            # Add some helpful metadata to the dataframe
            if not df.empty:
                print(f"Loaded {len(df)} rows of land use transition data")
                print(f"Available columns: {', '.join(df.columns)}")
                print(f"Date range: {df['decade_name'].min()} to {df['decade_name'].max()}")
                
            return df
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame()

    def get_data_info(self):
        """
        Returns information about the loaded data for user guidance.
        
        Returns:
            dict: Information about the dataset
        """
        if self.df.empty:
            return {"status": "No data loaded"}
            
        return {
            "status": "Data loaded successfully",
            "rows": len(self.df),
            "columns": list(self.df.columns),
            "scenarios": self.df['scenario_name'].unique().tolist() if 'scenario_name' in self.df.columns else [],
            "states": self.df['state_name'].unique().tolist()[:10] if 'state_name' in self.df.columns else [],  # First 10 states
            "land_use_categories": {
                "from": self.df['from_category'].unique().tolist() if 'from_category' in self.df.columns else [],
                "to": self.df['to_category'].unique().tolist() if 'to_category' in self.df.columns else []
            }
        }

    def ask(self, question: str):
        """
        Asks a question about the data.

        Args:
            question (str): The question to ask.

        Returns:
            The response from pandasai, with formatting applied to DataFrames.
        """
        if self.df.empty:
            return "No data available to query. Please check your database connection."
            
        try:
            # Enhanced configuration for PandasAI 3.0
            config = {
                "llm": self.llm,
                "save_charts": True,
                "save_charts_path": "exports/charts",
                "enable_cache": True,
                "verbose": True,
                "custom_whitelisted_dependencies": ["matplotlib", "seaborn", "plotly"]
            }
            
            sdf = SmartDataframe(self.df, config=config)
            response = sdf.chat(question)

            # Enhanced response handling
            if isinstance(response, pd.DataFrame):
                # Clean up column names for better display
                df_clean = response.copy()
                
                # Improve column names
                column_mapping = {
                    'total_area': 'Total Area',
                    'state_name': 'State',
                    'county_name': 'County', 
                    'from_category': 'From Land Use',
                    'to_category': 'To Land Use',
                    'scenario_name': 'Scenario',
                    'decade_name': 'Time Period',
                    'fips_code': 'FIPS Code'
                }
                
                # Apply column renaming if columns exist
                df_clean = df_clean.rename(columns={k: v for k, v in column_mapping.items() 
                                                  if k in df_clean.columns})
                
                # Smart number formatting with proper units
                numeric_cols = df_clean.select_dtypes(include=['number']).columns
                
                for col in numeric_cols:
                    if 'area' in col.lower() or 'acres' in col.lower():
                        max_val = df_clean[col].max()
                        if max_val > 1000000:  # Convert to millions
                            df_clean[col] = df_clean[col] / 1000000
                            new_col_name = col.replace('Total Area', 'Total Area (million acres)')
                            df_clean = df_clean.rename(columns={col: new_col_name})
                        elif max_val > 1000:  # Convert to thousands
                            df_clean[col] = df_clean[col] / 1000
                            new_col_name = col.replace('Total Area', 'Total Area (thousand acres)')
                            df_clean = df_clean.rename(columns={col: new_col_name})
                        else:
                            new_col_name = col.replace('Total Area', 'Total Area (acres)')
                            df_clean = df_clean.rename(columns={col: new_col_name})
                
                # Apply professional styling
                styled_df = df_clean.style
                
                # Format numeric columns
                numeric_cols = df_clean.select_dtypes(include=['number']).columns
                format_dict = {}
                
                for col in numeric_cols:
                    if df_clean[col].dtype == 'int64':
                        format_dict[col] = '{:,.0f}'
                    else:
                        format_dict[col] = '{:,.1f}'
                
                styled_df = styled_df.format(format_dict)
                
                # Add professional styling
                styled_df = styled_df.set_properties(**{
                    'text-align': 'center',
                    'font-family': 'Arial, sans-serif',
                    'font-size': '12px',
                    'border': '1px solid #ddd'
                })
                
                # Style headers
                styled_df = styled_df.set_table_styles([
                    {'selector': 'th', 
                     'props': [
                         ('text-align', 'center'), 
                         ('font-weight', 'bold'),
                         ('background-color', '#f8f9fa'),
                         ('color', '#495057'),
                         ('border', '1px solid #dee2e6'),
                         ('padding', '8px')
                     ]},
                    {'selector': 'td', 
                     'props': [
                         ('padding', '6px'),
                         ('border', '1px solid #dee2e6')
                     ]},
                    {'selector': 'table', 
                     'props': [
                         ('border-collapse', 'collapse'),
                         ('margin', '10px 0'),
                         ('font-size', '0.9em'),
                         ('width', '100%')
                     ]}
                ])
                
                # Add conditional formatting for numeric columns
                for col in numeric_cols:
                    if len(df_clean) > 1:  # Only apply if there are multiple rows to compare
                        # Apply gradient coloring for better visual comparison
                        styled_df = styled_df.background_gradient(
                            subset=[col], 
                            cmap='RdYlGn_r',  # Red-Yellow-Green reversed (high values = red)
                            alpha=0.3
                        )
                
                # Highlight maximum values in each numeric column
                def highlight_max(s):
                    is_max = s == s.max()
                    return ['background-color: #ffe6e6; font-weight: bold' if v else '' for v in is_max]
                
                for col in numeric_cols:
                    if len(df_clean) > 1:
                        styled_df = styled_df.apply(highlight_max, subset=[col])
                
                return styled_df
                
            elif isinstance(response, str):
                # Check if it's a path to a saved chart
                if "exports/charts" in response and os.path.exists(response):
                    return ("chart", response)
                else:
                    # Add some context to text responses
                    if len(response) < 50:  # Short responses might need context
                        context_response = f"**Answer:** {response}\n\n*This information is based on the RPA land use projections data loaded in the system.*"
                        return context_response
                    return response
                    
            elif hasattr(response, 'savefig'):  # Matplotlib figure
                # Save the figure and return the path
                chart_path = f"exports/charts/chart_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
                response.savefig(chart_path, dpi=300, bbox_inches='tight')
                plt.close(response)
                return ("chart", chart_path)
                
            else:
                return response
                
        except Exception as e:
            return f"Error processing your question: {str(e)}. Please try rephrasing your question or check that you're asking about available data."

if __name__ == '__main__':
    # Example usage
    nlq = NaturalLanguageQuery()
    if not nlq.df.empty:
        # Show data info
        info = nlq.get_data_info()
        print("Data Info:", info)
        
        # Test query
        response = nlq.ask("What are the top 5 counties with the most forest loss?")
        print("Response:", response)
    else:
        print("Dataframe is empty, could not run example.") 