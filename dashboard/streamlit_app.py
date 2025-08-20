import streamlit as st
import requests
import plotly.graph_objects as go

st.title("ESG Scoring Dashboard")

# Company selector
companies_response = requests.get("http://localhost:8000/companies")
companies = companies_response.json()

selected_company = st.selectbox(
    "Select Company",
    options=[c["symbol"] for c in companies],
    format_func=lambda x: next(c["name"] for c in companies if c["symbol"] == x)
)

if selected_company:
    # Get scores
    score_response = requests.get(f"http://localhost:8000/scores/{selected_company}")
    data = score_response.json()
    
    if "scores" in data:
        scores = data["scores"]
        
        # Display scores
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Environmental", f"{scores['E']}/10")
        with col2:
            st.metric("Social", f"{scores['S']}/10")
        with col3:
            st.metric("Governance", f"{scores['G']}/10")
        with col4:
            st.metric("Composite", f"{scores['composite']}/10")
        
        # Simple radar chart
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[scores['E'], scores['S'], scores['G']],
            theta=['Environmental', 'Social', 'Governance'],
            fill='toself',
            name=selected_company
        ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
            showlegend=True
        )
        
        st.plotly_chart(fig)