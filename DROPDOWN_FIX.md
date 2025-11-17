# Dropdown Switching Fix for Google Cloud Deployment

## Problem

On Google Cloud deployment, the dropdown switching logic didn't work properly. Users had to:
1. First click "Select Variable..." on their current dropdown
2. Then select a variable from another dropdown

This was cumbersome and not the intended behavior.

## Root Cause

The issue was a **state synchronization problem** between Streamlit's widget state and session state in cloud environments:

### What Was Happening:

1. User selects a variable from Dropdown A
2. Code sets Dropdown B and C's session state values to `None`
3. Code calls `st.rerun()`
4. **BUT**: In Google Cloud, the selectbox widgets don't reliably update their displayed value to match the new session state immediately
5. The widget still shows the old value visually, even though session state is `None`
6. When user tries to select from Dropdown B, the comparison `selected_var != session_state_var` evaluates to `False` because the widget hasn't synced yet
7. No rerun happens, so the state doesn't update

### Why It Works Locally But Not in Cloud:

- **Local**: Fast execution, minimal latency, immediate widget-state synchronization
- **Cloud**: Network latency, distributed state management, slight delays in widget updates

## Solution Implemented

### 1. **Force Widget Refresh with Counter** ✅

Added a refresh counter that increments when state changes:

```python
# Force widget refresh by incrementing a counter
st.session_state['_dropdown_refresh_counter'] = st.session_state.get('_dropdown_refresh_counter', 0) + 1
```

### 2. **Dynamic Widget Keys** ✅

Changed widget keys to include the refresh counter, forcing Streamlit to recreate widgets:

```python
key=f"variable_selector_{st.session_state.get('_dropdown_refresh_counter', 0)}"
```

This ensures that when the counter changes, Streamlit treats it as a new widget and properly initializes it with the current session state.

### 3. **Explicit Session State Reads** ✅

Always read from session state at the start of widget rendering:

```python
# Get current variable index - always recalculate from session state
# This ensures cloud environments properly sync dropdown display with session state
selected_variable = st.session_state.get('selected_variable', None)
```

### 4. **Removed Conditional State Clearing** ✅

Changed from:
```python
if 'selected_food_security_variable' in st.session_state:
    st.session_state['selected_food_security_variable'] = None
```

To:
```python
st.session_state['selected_food_security_variable'] = None
```

This ensures other dropdowns are ALWAYS cleared, not just conditionally.

## Files Modified

- ✅ `src/ui/leaflet_map_view.py` - All three dropdown widgets (lines 798-925)

## Changes Applied to All Three Dropdowns

1. **Data Variables** dropdown (col2)
2. **Food Security** dropdown (col3)
3. **Housing & Transportation** dropdown (col4)

Each dropdown now:
- Uses dynamic keys with refresh counter
- Always reads from session state
- Explicitly clears other dropdown states
- Increments refresh counter on selection

## Testing

### Local Testing:
1. Select a variable from any dropdown
2. Verify other dropdowns reset to "Select Variable..."
3. Select from a different dropdown
4. Verify first dropdown resets properly
5. Repeat with all three dropdown combinations

### Cloud Testing (Google Cloud):
1. Deploy updated code
2. Test the same dropdown switching scenarios
3. Should now work seamlessly without needing to manually reset
4. Monitor for any performance impact from widget recreation

## Expected Behavior After Fix

### Before:
1. Select "ALICE Rate" from Data Variables ✓
2. Try to select "SNAP Households" from Food Security ✗ (doesn't work)
3. Must first click "Select Variable" in Data Variables
4. Then select from Food Security ✓

### After:
1. Select "ALICE Rate" from Data Variables ✓
2. Select "SNAP Households" from Food Security ✓ (works immediately!)
3. Data Variables automatically resets to "Select Variable" ✓

## Performance Considerations

The dynamic widget keys force widget recreation on state changes. This has minimal performance impact because:

- Widgets are only recreated when selections change (not on every rerun)
- The overhead is negligible for selectbox widgets
- Benefits (reliable state sync) far outweigh the minimal cost

## Alternative Solutions Considered

1. **Use `on_change` callbacks**: Doesn't solve the timing issue
2. **Use `st.experimental_rerun()`: Deprecated and same issues
3. **Delay state updates**: Adds complexity and doesn't guarantee sync
4. **Multiple reruns**: Causes flicker and poor UX

The **dynamic key + refresh counter** approach is the most reliable solution for cloud deployments.
