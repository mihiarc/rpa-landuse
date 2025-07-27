# Streamlit Fragments Troubleshooting

## Overview

This guide covers common issues and solutions when using Streamlit fragments in the landuse application.

## Common Fragment Issues

### Issue: StreamlitAPIException with st.sidebar

**Error Message:**
```
StreamlitAPIException: Calling `st.sidebar` in a function wrapped with `st.fragment` is not supported. 
To write elements to the sidebar with a fragment, call your fragment function inside a with st.sidebar context manager.
```

**Cause:**
Functions decorated with `@st.fragment` cannot directly call `st.sidebar` or access sidebar elements.

**Solution:**

❌ **Incorrect (causes error):**
```python
@st.fragment
def handle_user_input():
    # ... processing logic ...
    
    # This will cause an error!
    with st.sidebar:
        st.caption(f"Query took {query_time:.1f}s")
```

✅ **Correct (solution 1 - use session state):**
```python
@st.fragment
def handle_user_input():
    # ... processing logic ...
    
    # Store data in session state instead
    st.session_state.last_query_time = query_time

def main():
    # Display in sidebar from main function
    with st.sidebar:
        if hasattr(st.session_state, 'last_query_time') and st.session_state.last_query_time:
            st.caption(f"⏱️ Last query: {st.session_state.last_query_time:.1f}s")
```

✅ **Correct (solution 2 - call fragment inside sidebar):**
```python
def handle_user_input_fragment():
    # Fragment logic without sidebar calls
    pass

def main():
    with st.sidebar:
        handle_user_input_fragment()  # Call fragment inside sidebar context
```

### Issue: Fragment Functions Must Be Self-Contained

**Problem:**
Fragments should be designed to operate independently without side effects on the rest of the page.

**Best Practices:**

1. **Use session state for communication:**
   ```python
   @st.fragment
   def query_processor():
       if st.button("Process"):
           result = process_query()
           st.session_state.query_result = result  # Store for use elsewhere
   ```

2. **Keep fragments focused:**
   ```python
   @st.fragment
   def chat_input():
       """Only handles chat input, nothing else"""
       if prompt := st.chat_input("Ask me..."):
           st.session_state.messages.append({"role": "user", "content": prompt})
   
   @st.fragment 
   def query_controls():
       """Only handles query control buttons"""
       col1, col2 = st.columns(2)
       with col1:
           if st.button("Clear"):
               st.session_state.messages = []
   ```

## Fragment Design Patterns

### 1. Input Isolation Pattern
```python
@st.fragment
def isolated_input():
    """Handles user input without affecting other components"""
    user_input = st.text_input("Enter query")
    if st.button("Submit"):
        st.session_state.user_query = user_input
        st.rerun()  # Trigger main page update
```

### 2. Display Fragment Pattern
```python
@st.fragment
def query_results_display():
    """Displays results independently"""
    if 'query_results' in st.session_state:
        st.dataframe(st.session_state.query_results)
```

### 3. Control Panel Pattern
```python
@st.fragment
def control_panel():
    """Isolated control buttons"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Reset"):
            st.session_state.clear()
    
    with col2:
        if st.button("Export"):
            st.session_state.export_flag = True
```

## Performance Benefits

Proper use of fragments provides:

- **Reduced Reruns**: Only the fragment reruns on interaction
- **Better UX**: Faster response times for user interactions
- **Isolated Updates**: Changes don't affect unrelated components
- **Memory Efficiency**: Less computation on each interaction

## Debugging Fragment Issues

### 1. Check Fragment Boundaries
```python
@st.fragment
def debug_fragment():
    st.write("Fragment start")
    # Your fragment code here
    st.write("Fragment end")
```

### 2. Monitor Session State
```python
def debug_session_state():
    with st.expander("Debug Session State"):
        st.json(dict(st.session_state))
```

### 3. Test Fragment Isolation
```python
@st.fragment
def test_fragment():
    st.write(f"Fragment run at: {time.time()}")
    
    if st.button("Fragment Button"):
        st.write("Fragment button clicked!")

def main():
    st.write(f"Main run at: {time.time()}")
    test_fragment()
    
    if st.button("Main Button"):
        st.write("Main button clicked!")
```

## Migration Checklist

When adding fragments to existing code:

- [ ] Identify isolated UI components
- [ ] Remove sidebar calls from fragments
- [ ] Use session state for data sharing
- [ ] Test fragment isolation
- [ ] Verify performance improvements
- [ ] Update tests to handle fragment behavior

## Related Documentation

- [Streamlit Fragments Official Docs](https://docs.streamlit.io/library/api-reference/performance/st.fragment)
- [Performance Optimization Guide](../performance/streamlit-fragments.md)
- [Session State Best Practices](https://docs.streamlit.io/library/api-reference/session-state)