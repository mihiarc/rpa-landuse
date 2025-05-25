import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
# import pandasai as pai
# from pandasai_openai import OpenAI

# Set page configuration
st.set_page_config(
    page_title="RPA Land Use Viewer",
    page_icon="🌳",
    layout="wide"
)

# Title and description
st.title("2020 Resources Planning Act (RPA) Assessment")
st.subheader("Land-Use Change Viewer")
st.markdown("""
This application visualizes land use transition projections from the USDA Forest Service's Resources Planning Act (RPA) Assessment.
Explore how land use is expected to change across the United States from 2020 to 2070 under different climate and socioeconomic scenarios.
""")

# Load the parquet files
@st.cache_data
def load_parquet_data():
    # Define data directory - support both local and cloud paths
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "semantic_layers/base_analysis")
    
    try:
        # Try to load raw data
        raw_data = {
            "Average Gross Change Across All Scenarios (2020-2070)": pd.read_parquet(os.path.join(data_dir, "gross_change_ensemble_all.parquet")),
            "Urbanization Trends By Decade": pd.read_parquet(os.path.join(data_dir, "urbanization_trends.parquet")),
            "Transitions to Urban Land": pd.read_parquet(os.path.join(data_dir, "to_urban_transitions.parquet")),
            "Transitions from Forest Land": pd.read_parquet(os.path.join(data_dir, "from_forest_transitions.parquet")),
            "County-Level Land Use Transitions": pd.read_parquet(os.path.join(data_dir, "county_transitions.parquet"))
        }
    except Exception as e:
        st.error(f"Error loading data from {data_dir}: {e}")
        # Fallback to direct paths for Streamlit Cloud
        try:
            raw_data = {
                "Average Gross Change Across All Scenarios (2020-2070)": pd.read_parquet("semantic_layers/base_analysis/gross_change_ensemble_all.parquet"),
                "Urbanization Trends By Decade": pd.read_parquet("semantic_layers/base_analysis/urbanization_trends.parquet"),
                "Transitions to Urban Land": pd.read_parquet("semantic_layers/base_analysis/to_urban_transitions.parquet"),
                "Transitions from Forest Land": pd.read_parquet("semantic_layers/base_analysis/from_forest_transitions.parquet"),
                "County-Level Land Use Transitions": pd.read_parquet("semantic_layers/base_analysis/county_transitions.parquet")
            }
        except Exception as e2:
            st.error(f"Error with fallback path: {e2}")
            raise e2
    
    # Convert hundred acres to acres for all datasets
    data = {}
    for key, df in raw_data.items():
        df_copy = df.copy()
        
        # Convert total_area column if it exists
        if "total_area" in df_copy.columns:
            df_copy["total_area"] = df_copy["total_area"] * 100
            
        # Convert specific columns for urbanization trends dataset
        if key == "Urbanization Trends By Decade":
            area_columns = ["forest_to_urban", "cropland_to_urban", "pasture_to_urban"]
            for col in area_columns:
                if col in df_copy.columns:
                    df_copy[col] = df_copy[col] * 100
        
        data[key] = df_copy
    
    return data

# Load RPA documentation
@st.cache_data
def load_rpa_docs():
    try:
        with open("docs/rpa_text/gtr_wo102_Chap4_chunks.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning("RPA documentation file not found")
        return []

# Main layout with tabs
# tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Data Explorer", "Urbanization Trends", "Forest Transitions", "Natural Language Query"])
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Data Explorer", "Urbanization Trends", "Forest Transitions"])

# Load data
try:
    data = load_parquet_data()
    rpa_docs = load_rpa_docs()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# ---- OVERVIEW TAB ----
with tab1:
    st.header("Land Use Projections Overview")
    
    st.markdown("""
        ### Key Findings
        - Developed land area is projected to increase under all scenarios, with most of the new developed land coming at the expense of forest land.
        - Higher projected population and income growth lead to relatively less forest land, while hotter projected future climates lead to relatively more forest land.
        - Projected future land use change is more sensitive to the variation in economic factors across RPA scenarios than to the variation among climate projections.
        """)

# ---- DATA EXPLORER TAB ----
with tab2:
    st.header("Data Explorer")
    
    # Select dataset to explore
    dataset_options = list(data.keys())
    selected_dataset = st.selectbox("Select Dataset", options=dataset_options)
    
    # Show dataset
    st.subheader(f"Exploring: {selected_dataset}")
    selected_df = data[selected_dataset]
    
    # Add info message about acres conversion
    st.info("Note: All area values are displayed in acres.")
    
    # Show basic stats
    col1, col2 = st.columns([1, 1])
    with col1:
        st.metric("Number of Rows", selected_df.shape[0])
    with col2:
        st.metric("Number of Columns", selected_df.shape[1])
    
    # Show column info
    st.subheader("Column Information")
    # Convert object types to string to avoid PyArrow conversion issues
    col_df = pd.DataFrame({
        "Column": selected_df.columns,
        "Type": [str(dtype) for dtype in selected_df.dtypes],
        "Sample Values": [str(selected_df[col].iloc[0]) if len(selected_df) > 0 else "Empty" for col in selected_df.columns]
    })
    st.dataframe(col_df)
    
    # Show data
    st.subheader("Data Preview")
    # Convert object columns to string to avoid PyArrow conversion issues
    preview_df = selected_df.head(100).copy()
    for col in preview_df.select_dtypes(include=['object']).columns:
        preview_df[col] = preview_df[col].astype(str)
    st.dataframe(preview_df)
    
    # Allow download
    csv = selected_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=f'{selected_dataset}.csv',
        mime='text/csv',
    )


# ---- URBANIZATION TRENDS TAB ----
with tab3:
    st.header("Urbanization Trends")
    
    # Filter controls
    st.subheader("Explore Urbanization Trends")
    
    urbanization_df = data["Urbanization Trends By Decade"]
    # Convert to string for display in selectbox
    scenarios = urbanization_df["scenario_name"].unique().tolist()
    scenarios = [str(s) for s in scenarios]
    selected_scenario = st.selectbox("Select Scenario", options=scenarios)
    
    # Filter data based on selection
    filtered_urban = urbanization_df[urbanization_df["scenario_name"] == selected_scenario]
    
    # Plot the data
    st.subheader(f"Land Conversion to Urban Areas: {selected_scenario}")
    
    fig, ax = plt.figure(figsize=(10, 6)), plt.subplot()
    ax.plot(filtered_urban["decade_name"], filtered_urban["forest_to_urban"], marker='o', label="Forest to Urban")
    ax.plot(filtered_urban["decade_name"], filtered_urban["cropland_to_urban"], marker='s', label="Cropland to Urban")
    ax.plot(filtered_urban["decade_name"], filtered_urban["pasture_to_urban"], marker='^', label="Pasture to Urban")
    ax.set_xlabel("Time Period")
    ax.set_ylabel("Acres")
    ax.set_title(f"Land Conversion to Urban Areas: {selected_scenario}")
    ax.legend()
    plt.tight_layout()
    
    st.pyplot(fig)
    
    with st.expander("Show Data Table"):
        # Convert object columns to string to avoid PyArrow conversion issues
        display_df = filtered_urban.copy()
        for col in display_df.select_dtypes(include=['object']).columns:
            display_df[col] = display_df[col].astype(str)
        st.dataframe(display_df)
    
    st.subheader("Top Counties Converting to Urban Land")
    
    # Get county transitions data 
    county_df = data["County-Level Land Use Transitions"]
    # Filter for urban transitions only (where to_category is 'Urban')
    urban_counties_df = county_df[county_df["to_category"] == "Urban"]
    
    # Group by county and sum total area
    urban_by_county = urban_counties_df.groupby(["county_name", "state_name"])["total_area"].sum().reset_index()
    urban_by_county = urban_by_county.sort_values("total_area", ascending=False).head(10)
    
    fig2, ax2 = plt.figure(figsize=(10, 6)), plt.subplot()
    ax2.bar(urban_by_county["county_name"] + ", " + urban_by_county["state_name"], urban_by_county["total_area"])
    ax2.set_xlabel("County")
    ax2.set_ylabel("Acres")
    ax2.set_title("Top 10 Counties by Urbanization")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    
    st.pyplot(fig2)

# ---- FOREST TRANSITIONS TAB ----
with tab4:
    st.header("Forest Land Transitions")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        from_forest_df = data["Transitions from Forest Land"]
        # Convert to string for display in selectbox
        forest_scenarios = from_forest_df["scenario_name"].unique().tolist()
        forest_scenarios = [str(s) for s in forest_scenarios]
        selected_scenario_forest = st.selectbox("Select Scenario", 
                                               options=forest_scenarios,
                                               key="forest_scenario")
    
    # Filter data
    filtered_forest = from_forest_df[from_forest_df["scenario_name"] == selected_scenario_forest]
    
    # Aggregate data by destination land use
    forest_to_use = filtered_forest.groupby(["to_category", "decade_name"])["total_area"].sum().reset_index()
    
    # Pivot table for plotting
    pivot_forest = forest_to_use.pivot(index="decade_name", columns="to_category", values="total_area")
    
    # Plot the data
    st.subheader(f"Forest Land Conversion: {selected_scenario_forest}")
    
    fig3, ax3 = plt.figure(figsize=(10, 6)), plt.subplot()
    pivot_forest.plot(kind="bar", ax=ax3)
    ax3.set_xlabel("Time Period")
    ax3.set_ylabel("Acres")
    ax3.set_title(f"Forest Land Conversion by Destination: {selected_scenario_forest}")
    plt.tight_layout()
    
    st.pyplot(fig3)
    
    with st.expander("Show Data Table"):
        # Convert object columns to string to avoid PyArrow conversion issues
        display_forest_df = filtered_forest.copy()
        for col in display_forest_df.select_dtypes(include=['object']).columns:
            display_forest_df[col] = display_forest_df[col].astype(str)
        st.dataframe(display_forest_df)
    
    # Add additional information from RPA docs
    st.subheader("Forest Land Projections from RPA Assessment")
    rpa_forest_info = """
    Over the 50-year period from 2020 to 2070, the RPA Assessment projects a total net forest land loss of between 7.6 and 15.0 million acres. 
    When averaging results across RPA scenario-climate futures, approximately 91 percent of current forest land is projected to remain in forest use by 2070.
    
    Most of the gross forest loss (19.8 to 26.0 million acres) is projected to convert to developed land, which is assumed to be a permanent change.
    About 25.3 million acres of new forest land will be added from conversions out of pasture land (17.4 million), crop land (2.4 million acres), and rangeland (5.5 million acres).
    """
    st.markdown(rpa_forest_info)
    
    # Add a section for county-level forest loss
    st.subheader("Top Counties with Forest Land Loss")
    
    # Get county transitions with forest as source
    county_df = data["County-Level Land Use Transitions"]
    forest_loss_counties = county_df[(county_df["from_category"] == "Forest") & (county_df["to_category"] != "Forest")]
    
    # Group by county and sum total area
    forest_loss_by_county = forest_loss_counties.groupby(["county_name", "state_name"])["total_area"].sum().reset_index()
    forest_loss_by_county = forest_loss_by_county.sort_values("total_area", ascending=False).head(10)
    
    fig4, ax4 = plt.figure(figsize=(10, 6)), plt.subplot()
    ax4.bar(forest_loss_by_county["county_name"] + ", " + forest_loss_by_county["state_name"], forest_loss_by_county["total_area"])
    ax4.set_xlabel("County")
    ax4.set_ylabel("Acres")
    ax4.set_title("Top 10 Counties by Forest Land Loss")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    
    st.pyplot(fig4)
        
# ---- NATURAL LANGUAGE QUERY TAB ----
# Commenting out Natural Language Query functionality to resolve deployment issues
"""
with tab5:
    st.header("Natural‑Language Query")

    # 1. wrap DataFrame once
    if "pai_df" not in st.session_state:
        st.session_state["pai_df"] = pai.DataFrame(
            data["Transitions to Urban Land"],
            name="Transitions to Urban Land",
        )
    df = st.session_state["pai_df"]
    # Access the underlying DataFrame correctly
    raw_df = df.dataframe.copy() if hasattr(df, 'dataframe') else df.copy()

    # 2. LLM client
    llm = OpenAI(
        api_token=os.environ["OPENAI_API_KEY"],
        model="gpt-4o-mini",
    )
    pai.config.set({
        "llm": llm,
        "instructions": "Answer the user's question specifically with 1 to 2 concise English sentences"
                        " for a non‑technical audience. Include numerical values in whole numbers with commas."
                        "Area values are in acres."
                        "These are projections under different climate and socioeconomic scenarios and not predictions."
    })

    # 3. preview
    with st.expander("🔎 Preview Table"):
        st.dataframe(raw_df.tail(10))

    query = st.text_area("🗣️ Ask me anything about this table")
    debug = st.checkbox("Show generated Python code", value=False)
    if debug:
        codebox = st.empty()

    if query:
        with st.spinner("Running Query…"):
            # 1️⃣  first call – let PandaAI decide; may return a chart path
            resp_plot = df.chat(
                query + "\n\nIf a chart helps, include one."
            )

            # 2️⃣  second call – always get a one‑sentence explanation
            resp_text = df.chat(query)

        # ── display plot if we got one ─────────────────────────────────────
        st.image(resp_plot.value, caption="Generated figure",
                use_container_width=True)

        # ── display narrative sentence ────────────────────────────────────
        st.write(resp_text.value)

        # 5. optional debug code
        if debug:
            codebox.code(resp_text.last_code_executed, language="python")
"""

# Footer
st.markdown("---")
st.markdown("""
**RPA Land Use Viewer** - Built with Streamlit

Data Source: This dataset was developed by Mihiar, Lewis & Coulston for the USDA Forest Service for the Resources Planning Act (RPA) 2020 Assessment.
""") 