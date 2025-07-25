# Fixing Streamlit Duplicate Element IDs

## Problem

Streamlit generates automatic IDs for widgets based on their type and parameters. When multiple widgets have the same type and parameters, they get identical IDs, causing a `StreamlitDuplicateElementId` error.

## Error Message

```
StreamlitDuplicateElementId: There are multiple `selectbox` elements with the same auto-generated ID.
When this element is created, it is assigned an internal ID based on the element type and provided parameters.
Multiple elements with the same type and parameters will cause this error.

To fix this error, please pass a unique `key` argument to the selectbox element.
```

## Root Cause

In the data extraction page (`pages/extraction.py`), multiple widgets had identical parameters:

### Duplicate Selectboxes
- Multiple "Export format:" selectboxes with same options `["CSV", "Excel", "JSON", "Parquet"]`
- These appeared in different sections (templates, custom, bulk) but had identical parameters

### Duplicate Number Inputs
- Multiple "Preview rows:" number inputs with same min/max/value/step parameters
- Multiple "Export limit:" number inputs with same parameters

## Solution

Add unique `key` parameters to each widget to force different IDs:

### Fixed Selectboxes

```python
# Template section
export_format = st.selectbox(
    "Export format:",
    ["CSV", "Excel", "JSON", "Parquet"],
    help="Choose the file format for your export",
    key="template_export_format"  # ✅ Unique key
)

# Custom section
export_format = st.selectbox(
    "Export format:",
    ["CSV", "Excel", "JSON", "Parquet"],
    help="Choose the file format for your export",
    key="custom_export_format"  # ✅ Different key
)

# Bulk section
export_format = st.selectbox(
    "Export format:",
    ["CSV (ZIP)", "Excel", "Parquet (ZIP)"],
    help="Choose the format for bulk export",
    key="bulk_export_format"  # ✅ Different key
)
```

### Fixed Number Inputs

```python
# Template section
preview_rows = st.number_input(
    "Preview rows:",
    min_value=10,
    max_value=1000,
    value=100,
    step=10,
    help="Number of rows to preview",
    key="template_preview_rows"  # ✅ Unique key
)

# Custom section
preview_limit = st.number_input(
    "Preview rows:",
    min_value=10,
    max_value=1000,
    value=100,
    step=10,
    key="custom_preview_rows"  # ✅ Different key
)
```

## Complete Key Mapping

| Widget Type | Location | Key | Description |
|-------------|----------|-----|-------------|
| selectbox | Templates | `template_selector` | Template selection |
| selectbox | Templates | `template_export_format` | Export format for templates |
| selectbox | Custom | `custom_extract_type` | Custom extraction type |
| selectbox | Custom | `custom_transition_type` | Transition type filter |
| selectbox | Custom | `custom_export_format` | Export format for custom |
| selectbox | Bulk | `bulk_extract_type` | Bulk extraction type |
| selectbox | Bulk | `bulk_export_format` | Export format for bulk |
| number_input | Templates | `template_preview_rows` | Preview rows for templates |
| number_input | Templates | `template_export_limit` | Export limit for templates |
| number_input | Custom | `custom_preview_rows` | Preview rows for custom |
| number_input | Custom | `custom_export_limit` | Export limit for custom |
| number_input | Bulk | `bulk_row_limit` | Row limit for bulk |
| button | Templates | `template_preview_data` | Preview data button |
| button | Templates | `template_export_data` | Export data button |
| button | Custom | `custom_preview_query` | Preview query button |
| button | Custom | `custom_preview_data` | Preview data button |
| button | Custom | `custom_export_data` | Export data button |
| button | Bulk | `bulk_generate_export` | Generate bulk export button |

## Prevention

To avoid this issue in the future:

### 1. Always Use Keys for Repeated Widgets
```python
# ❌ Bad: Same parameters, no keys
st.selectbox("Format:", ["CSV", "JSON"])  # Section 1
st.selectbox("Format:", ["CSV", "JSON"])  # Section 2 - DUPLICATE!

# ✅ Good: Same parameters, unique keys
st.selectbox("Format:", ["CSV", "JSON"], key="section1_format")
st.selectbox("Format:", ["CSV", "JSON"], key="section2_format")
```

### 2. Use Descriptive Key Naming Convention
```python
# Pattern: {section}_{widget_purpose}
key="template_export_format"
key="custom_preview_rows"
key="bulk_row_limit"
```

### 3. Check for Duplicates During Development
```python
# Use this pattern to identify potential duplicates
widgets_to_check = [
    "selectbox", "multiselect", "text_input", 
    "number_input", "checkbox", "radio", "slider"
]

# Add keys proactively when creating similar widgets
```

## Testing

After adding keys, verify the fix:

1. **Import Test**: Check that the page imports without errors
2. **Runtime Test**: Navigate through all tabs and interact with widgets
3. **State Test**: Ensure widget states don't interfere with each other

## Related Issues

This pattern can affect any Streamlit widget that appears multiple times with identical parameters:
- `st.selectbox`
- `st.multiselect`
- `st.text_input`
- `st.number_input`
- `st.checkbox`
- `st.radio`
- `st.slider`
- `st.button`

Always provide unique `key` parameters when using repeated widgets across different sections of your app.
