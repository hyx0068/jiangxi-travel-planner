from __future__ import annotations

import streamlit as st

from .config import PUBLIC_DEMO_MODE


def hide_default_nav() -> None:
    st.markdown(
        "<style>"
        "[data-testid='stSidebarNav']{display:none;}"
        "[data-testid='stSidebarCollapseButton']{display:none!important;}"
        "[data-testid='stToolbar']{display:none;}"
        "[data-testid='stDecoration']{display:none;}"
        "#MainMenu{visibility:hidden;}"
        "</style>",
        unsafe_allow_html=True,
    )


def render_nav() -> None:
    hide_default_nav()
    st.page_link("app.py", label="江西行程助手", icon="🧭")
    if not PUBLIC_DEMO_MODE:
        st.page_link("pages/1_后台.py", label="后台", icon="🛠️")
    st.page_link("pages/2_计划仓库.py", label="计划仓库", icon="🗂️")
