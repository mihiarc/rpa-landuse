# Dark Mode Testing Guide

## Important Configuration Change

**The toolbar was set to "minimal" which was hiding the settings menu. This has been fixed.**

## How to Test Dark Mode

The Streamlit app now has proper dark mode support using Streamlit's built-in theme system.

### Access Theme Settings

1. Run the app: `uv run streamlit run landuse_app.py`
2. Look for the **⋮** (three dots) menu in the top-right corner of the app
3. Click on it and select **Settings**
4. In the Settings dialog, you'll see **"Choose app theme, colors, and fonts"**
5. You'll see theme options:
   - **Light** - Light theme
   - **Dark** - Dark theme
   - **Use system setting** - Follows your OS preference
   - **Custom theme** - Uses the app's custom theme (defined in `.streamlit/config.toml`)

### What's Changed

#### Theme-Aware CSS Updates:

1. **Feature Cards**:
   - Changed from hard-coded white (`#ffffff`) to semi-transparent (`rgba(128, 128, 128, 0.05)`)
   - Works well in both light and dark modes

2. **Text Colors**:
   - Changed from hard-coded colors to `inherit`
   - Automatically adapts to theme

3. **Borders**:
   - Changed to semi-transparent rgba values
   - Visible in both themes

4. **Hover States**:
   - Use semi-transparent overlays instead of fixed colors

5. **Explorer Page**:
   - Table type indicators now use semi-transparent backgrounds
   - Works properly in both themes

### Elements That Stay Colored

These elements intentionally keep their colors for branding/hierarchy:

1. **Hero Section** - Purple gradient (branding)
2. **Metric Cards** - Purple gradient (visual hierarchy)
3. **Primary Actions** - Use Streamlit's primaryColor

### Testing Checklist

- [ ] Switch to Dark mode via Settings menu
- [ ] Verify feature cards are readable
- [ ] Check text contrast in both modes
- [ ] Verify hover states work properly
- [ ] Test explorer page table cards
- [ ] Switch back to Light mode
- [ ] Test "Use system setting" option

### Known Behavior

- The custom theme (defined in `.streamlit/config.toml`) appears as "Custom theme" option
- Users' theme preference persists across sessions
- The app respects OS dark mode when "Use system setting" is selected