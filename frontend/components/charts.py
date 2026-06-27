import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


THEME_COLORS = ["#6366F1", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#3B82F6", "#EC4899"]


def radar_chart(categories, values, title="", max_val=100):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        name="Score",
        line=dict(color="#6366F1", width=2),
        fillcolor="rgba(99, 102, 241, 0.3)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, max_val])),
        showlegend=False,
        title=title,
        height=400,
        margin=dict(l=80, r=80, t=40, b=80),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#334155"),
    )
    st.plotly_chart(fig, use_container_width=True)


def bar_chart(labels, values, title="", color="#6366F1", horizontal=False):
    if horizontal:
        fig = px.bar(
            x=values, y=labels, orientation="h",
            title=title, color_discrete_sequence=[color],
            labels={"x": "Score", "y": ""},
        )
    else:
        fig = px.bar(
            x=labels, y=values, title=title,
            color_discrete_sequence=[color],
            labels={"x": "", "y": "Score"},
        )
    fig.update_layout(
        height=350, margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#334155"),
        showlegend=False,
    )
    fig.update_traces(marker=dict(line=dict(width=0)))
    st.plotly_chart(fig, use_container_width=True)


def pie_chart(labels, values, title="", hole=0.4):
    colors = THEME_COLORS[:len(labels)]
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=hole,
        marker=dict(colors=colors),
        textinfo="label+percent", textposition="outside",
    )])
    fig.update_layout(
        title=title, height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#334155"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def line_chart(data, x_col, y_col, title="", color="#6366F1"):
    df = pd.DataFrame(data) if not isinstance(data, pd.DataFrame) else data
    fig = px.line(
        df, x=x_col, y=y_col, title=title,
        markers=True, color_discrete_sequence=[color],
        labels={x_col: "", y_col: "Score"},
    )
    fig.update_layout(
        height=350, margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#334155"),
        showlegend=False,
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8))
    st.plotly_chart(fig, use_container_width=True)


def gauge_chart(value, title="", max_val=100):
    color = "#10B981" if value >= 70 else "#F59E0B" if value >= 40 else "#EF4444"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 16, "color": "#334155"}},
        number={"font": {"size": 40, "color": color}},
        gauge={
            "axis": {"range": [0, max_val], "tickwidth": 1, "tickcolor": "#CBD5E1"},
            "bar": {"color": color, "thickness": 0.75},
            "bgcolor": "#F1F5F9",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 40], "color": "#FEE2E2"},
                {"range": [40, 70], "color": "#FEF3C7"},
                {"range": [70, 100], "color": "#D1FAE5"},
            ],
        },
    ))
    fig.update_layout(
        height=250, margin=dict(l=40, r=40, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#334155"),
    )
    st.plotly_chart(fig, use_container_width=True)


def grouped_bar_chart(data_dict, title="", colors=None):
    if colors is None:
        colors = THEME_COLORS
    fig = go.Figure()
    for i, (label, values) in enumerate(data_dict.items()):
        color = colors[i % len(colors)]
        if isinstance(values, dict):
            fig.add_trace(go.Bar(
                name=label,
                x=list(values.keys()),
                y=list(values.values()),
                marker_color=color,
            ))
        elif isinstance(values, (list, tuple)):
            fig.add_trace(go.Bar(
                name=label,
                x=list(range(len(values))),
                y=values,
                marker_color=color,
            ))
    fig.update_layout(
        title=title, barmode="group", height=350,
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#334155"),
    )
    st.plotly_chart(fig, use_container_width=True)
