"""
Cascading dropdown prototype.

Goal: verify two things before porting into the main dashboard sidebar:
  1. Can a hover submenu render without being clipped by Streamlit's
     component iframe?
  2. Can a click on a submenu item propagate the selection back to
     Python/st.session_state without requiring a custom component build?

Approach: render the menu with components.v1.html. On click, each
submenu item writes the selection into window.top.location.search
and reloads — Streamlit then reads it via st.query_params on the
next run. No build step, no new dependencies.

Run:
  streamlit run test_cascade.py --server.port 8502
"""
import streamlit as st

st.set_page_config(page_title="Cascade test", layout="wide")

st.title("🧪 Cascading dropdown prototype")
st.caption("Testing hover-reveal submenu + round-trip to Python state.")

# -- Menu definition -------------------------------------------------
# Top-level items: either {"key": "...", "label": "..."} (leaf) or
# {"label": "...", "children": [...]} (parent with submenu).
MENU = [
    {"key": "poverty_rate", "label": "Poverty Rate"},
    {"key": "median_income", "label": "Median Income"},
    {
        "label": "Child Tax Credit",
        "children": [
            {"key": "ctc_avg_amount", "label": "Average Amount"},
            {"key": "ctc_participation_rate", "label": "Participation Rate"},
        ],
    },
    {
        "label": "EITC",
        "children": [
            {"key": "federal_eitc_avg_amount", "label": "Federal Avg Amount"},
            {"key": "state_eitc_avg_amount", "label": "State Avg Amount"},
            {"key": "eitc_participation_rate", "label": "Participation Rate"},
        ],
    },
    {"key": "alice_rate", "label": "ALICE Households"},
]

# -- Selection round-trip --------------------------------------------
# Read ?sel=... off the URL and stash it in session_state, then wipe
# the query string so a refresh doesn't keep re-firing the selection.
qp = st.query_params
if "sel" in qp:
    st.session_state["cascade_selection"] = qp["sel"]
    st.query_params.clear()

selection = st.session_state.get("cascade_selection")

# -- Render ----------------------------------------------------------
col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader("Menu")

    # Build the HTML menu. Each leaf item navigates the CURRENT page
    # (not an iframe — we render via st.html() which injects into the
    # main Streamlit frame) to ?sel=<key>. Inline onclick because
    # <script> tags may be stripped by sanitizers.
    def render_items(items, depth=0):
        html_parts = ['<ul class="cascade-menu">']
        for item in items:
            if "children" in item:
                html_parts.append(
                    f'<li class="cascade-parent">'
                    f'  <span class="cascade-label">{item["label"]} ▸</span>'
                    f'  {render_items(item["children"], depth + 1)}'
                    f'</li>'
                )
            else:
                # Plain anchor — Streamlit's HTML sanitizer strips
                # onclick/onmouse* handlers, but href stays intact.
                # Clicking navigates the page to ?sel=<key> and
                # Streamlit reruns with st.query_params populated.
                html_parts.append(
                    f'<li class="cascade-leaf">'
                    f'  <a href="?sel={item["key"]}" target="_self">'
                    f'    {item["label"]}'
                    f'  </a>'
                    f'</li>'
                )
        html_parts.append("</ul>")
        return "".join(html_parts)

    menu_html = f"""
    <style>
      :root {{
        --green: #6a9a50;
        --green-dark: #2a5a0c;
        --border: #b8d4a0;
      }}
      .cascade-root {{
        font-family: Roboto, system-ui, sans-serif;
        font-size: 14px;
        position: relative;
      }}
      .cascade-trigger {{
        display: inline-block;
        padding: 8px 16px;
        background: var(--green);
        color: white;
        font-weight: 600;
        border-radius: 4px;
        cursor: pointer;
        user-select: none;
      }}
      .cascade-menu {{
        list-style: none;
        padding: 4px 0;
        margin: 0;
        background: white;
        border: 1px solid var(--border);
        border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        min-width: 220px;
      }}
      /* Top-level menu: hidden until trigger hover */
      .cascade-root > .cascade-menu {{
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        z-index: 1000;
        margin-top: 4px;
      }}
      .cascade-root:hover > .cascade-menu,
      .cascade-root.open > .cascade-menu {{
        display: block;
      }}
      .cascade-menu li {{
        padding: 8px 14px;
        cursor: pointer;
        position: relative;
        color: var(--green-dark);
      }}
      .cascade-menu li:hover {{
        background: #eef6e3;
      }}
      .cascade-parent > .cascade-menu {{
        display: none;
        position: absolute;
        left: 100%;
        top: -5px;
        margin-left: 2px;
      }}
      .cascade-parent:hover > .cascade-menu {{
        display: block;
      }}
      .cascade-leaf {{
        user-select: none;
        padding: 0;  /* anchor handles padding so whole cell is clickable */
      }}
      .cascade-leaf > a {{
        display: block;
        padding: 8px 14px;
        color: var(--green-dark);
        text-decoration: none;
      }}
      .cascade-leaf:hover > a {{
        background: #eef6e3;
      }}
      .cascade-label {{
        pointer-events: none;
      }}
    </style>

    <div class="cascade-root" id="cascade-root">
      <div class="cascade-trigger">
        Choose a variable ▾
      </div>
      {render_items(MENU)}
    </div>
    """
    # st.html renders directly into the main Streamlit frame (NOT a
    # sandboxed iframe), so onclick can navigate window.location.
    st.html(menu_html)

with col_b:
    st.subheader("Current selection")
    if selection:
        st.success(f"`{selection}`")
    else:
        st.info("Nothing selected yet — hover the green button.")

    st.divider()
    st.caption("Raw st.session_state:")
    st.json({"cascade_selection": selection})
