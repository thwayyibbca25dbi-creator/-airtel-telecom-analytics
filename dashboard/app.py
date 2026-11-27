from pathlib import Path
import sqlite3
import html
import streamlit as st
import plotly.graph_objects as go

# ============================================================
# AIRTEL TELECOM ANALYTICS | CLASS A | GROUP 1 | DOMAIN A
# Retention dashboard — exactly two tabs: Overview and Detail
# Red + cream professional UI
# ============================================================

st.set_page_config(
    page_title="Airtel | Retention Intelligence",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "raw" / "airtel.db"
TABLE = "customer_features"
NATIONAL_REFERENCE = 23.75  # Supplied by the assignment guide; reference, not target.

# Enter only the actual validated T4 result from your earlier analysis.
T4_P_VALUE = None
T4_DIRECTION = None
T4_INTERPRETATION = None

# ----------------------------- Theme -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@600;700;800&display=swap');
:root {
  --cream:#fbf5e9; --cream2:#f4ead8; --paper:#fffdf8;
  --red:#b51224; --red2:#d51f35; --wine:#751322;
  --ink:#2c2020; --muted:#796b61; --line:#eadcc8;
}
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:linear-gradient(135deg,#fbf5e9 0%,#f8eddf 48%,#fffaf2 100%); color:var(--ink);}
[data-testid="stHeader"] {background:transparent;}
.block-container {max-width:1480px;padding-top:.4rem;padding-bottom:.2rem;}
.stPlotlyChart {margin-bottom:-18px;}
[data-testid='stVerticalBlock'] {gap:.4rem;}
[data-testid='stHorizontalBlock'] {gap:.6rem;}
h1,h2,h3 {font-family:'Manrope',sans-serif;color:var(--wine);}
.hero {
  background:linear-gradient(115deg,#781321 0%,#b51224 55%,#d51f35 100%);
  border-radius:14px;padding:9px 17px;color:#fff8ed;
  box-shadow:0 10px 28px rgba(117,19,34,.16); margin-bottom:7px;
  position:relative; overflow:hidden;
}
.hero:after {content:"";position:absolute;width:230px;height:230px;border:1px solid rgba(255,255,255,.16);
  border-radius:50%;right:-48px;top:-120px;box-shadow:0 0 0 24px rgba(255,255,255,.035),0 0 0 50px rgba(255,255,255,.025);}
.hero-kicker {font-size:.70rem;letter-spacing:.16em;font-weight:800;color:#ffd9c7;}
.hero-title {font-family:'Manrope',sans-serif;font-size:1.35rem;line-height:1.15;font-weight:800;color:#fffaf3;margin-top:4px;}
.hero-note {font-size:.72rem;color:#ffeadc;margin-top:7px;max-width:850px;}
.hero-filter {font-size:.72rem;color:#ffe1d4;margin-top:10px;font-weight:700;letter-spacing:.06em;}
.section-head {font-family:'Manrope',sans-serif;font-size:.84rem;font-weight:800;color:#781321;margin:4px 0 2px;}
.section-sub {font-size:.68rem;color:#796b61;margin-top:-3px;margin-bottom:2px;}
.kpi {
 background:linear-gradient(145deg,#fffefa,#f8efdf);border:1px solid #eadcc8;
 border-top:3px solid #b51224;border-radius:12px;padding:8px 12px;min-height:70px;
 box-shadow:0 5px 16px rgba(83,46,31,.055);transition:transform .2s ease,box-shadow .2s ease;
 animation:rise .55s ease both;
}
.kpi:hover {transform:translateY(-4px);box-shadow:0 10px 22px rgba(117,19,34,.12);}
.kpi-label {font-size:.69rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:#8b5b50;}
.kpi-value {font-family:'Manrope',sans-serif;font-size:1.3rem;font-weight:800;color:#791526;margin-top:4px;line-height:1.25;}
.kpi-note {font-size:.69rem;line-height:1.35;color:#796b61;margin-top:5px;}
.panel {background:#fffdf8;border:1px solid #eadcc8;border-radius:15px;padding:8px 10px 2px;
 box-shadow:0 4px 15px rgba(83,46,31,.045);}
div[data-testid="stTabs"] {background:#f2e6d5;padding:5px;border-radius:12px;gap:6px;}
div[data-testid="stTabs"] button {font-weight:800;color:#72554b;border-radius:9px;padding:8px 17px;}
div[data-testid="stTabs"] button[aria-selected="true"] {background:#b51224;color:#fffaf3;border-bottom:0;}
section[data-testid="stSidebar"] {background:linear-gradient(180deg,#781321 0%,#a91528 52%,#c51d31 100%);border-right:1px solid #8e1828;}
section[data-testid="stSidebar"] * {color:#fff8ed;}
section[data-testid="stSidebar"] [data-baseweb="select"] div,
section[data-testid="stSidebar"] input {color:#2c2020 !important;}
section[data-testid="stSidebar"] [data-baseweb="select"] {background:#fffdf8;border-radius:9px;}
section[data-testid="stSidebar"] hr {border-color:rgba(255,255,255,.3);}
div[data-testid="stDataFrame"] {border:1px solid #eadcc8;border-radius:12px;overflow:hidden;}
.stAlert {border-radius:11px;}
footer {visibility:hidden;}
@keyframes rise {from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:translateY(0)}}
@media (prefers-reduced-motion:reduce) {.kpi{animation:none;transition:none}.kpi:hover{transform:none}}
</style>
""", unsafe_allow_html=True)

# ----------------------------- SQL helpers -----------------------------
def q(sql, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

def objects():
    return q("SELECT name, type FROM sqlite_master WHERE type IN ('table','view')")

def columns_of(name):
    # name comes only from sqlite_master, not user input.
    with sqlite3.connect(DB_PATH) as conn:
        return {r[1] for r in conn.execute(f'PRAGMA table_info("{name}")').fetchall()}

def sql_ident(name):
    return '"' + str(name).replace('"', '""') + '"'

def metric_card(label, value, note):
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{html.escape(str(label))}</div>'
        f'<div class="kpi-value">{html.escape(str(value))}</div>'
        f'<div class="kpi-note">{html.escape(str(note))}</div></div>',
        unsafe_allow_html=True,
    )

def base_filter(connection_value, region_value):
    conditions, params = [], []
    if connection_value != "All":
        conditions.append("connection_type = ?")
        params.append(connection_value)
    if region_value != "All":
        conditions.append("region = ?")
        params.append(region_value)
    return (" WHERE " + " AND ".join(conditions)) if conditions else "", params

def plot_style(fig, height=285):
    fig.update_layout(
        height=height, margin=dict(l=8,r=8,t=38,b=8),
        paper_bgcolor="#fffdf8", plot_bgcolor="#fffdf8",
        font=dict(family="DM Sans",size=9,color="#493934"),
        title=dict(x=.025,xanchor="left",font=dict(family="Manrope",size=11,color="#781321")),
        hoverlabel=dict(bgcolor="#781321",font_color="#fffaf3"),
        transition=dict(duration=500,easing="cubic-in-out"),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False,linecolor="#eadcc8",tickfont_color="#65534b",title_font_color="#781321")
    fig.update_yaxes(gridcolor="#f0e6d8",zeroline=False,tickfont_color="#65534b",title_font_color="#781321")
    return fig

def add_reference(fig, horizontal=True):
    if horizontal:
        fig.add_hline(y=NATIONAL_REFERENCE,line_dash="dash",line_color="#9b765d",line_width=1.5,
                      annotation_text="National reference 23.75%",annotation_position="top left")
    else:
        fig.add_vline(x=NATIONAL_REFERENCE,line_dash="dash",line_color="#9b765d",line_width=1.5,
                      annotation_text="National reference 23.75%",annotation_position="top")

def optional_column(candidates):
    return next((c for c in candidates if c in COLS), None)

def available_monthly_data(circle_name, connection_value, region_value):
    # Only use a real date/month field if it exists in the validated feature table.
    date_col = optional_column(["churn_date","disconnection_date","exit_date","leaver_date","churned_at","churn_month"])
    if not date_col:
        return None, "Monthly leavers unavailable: no validated churn-date/month column was found."
    if date_col == "churn_month":
        month_expr = f"substr(CAST({sql_ident(date_col)} AS TEXT),1,7)"
    else:
        month_expr = f"strftime('%Y-%m', {sql_ident(date_col)})"
    clauses = ["circle_name = ?", "is_churned = 1", f"{sql_ident(date_col)} IS NOT NULL"]
    params = [circle_name]
    if connection_value != "All":
        clauses.append("connection_type = ?"); params.append(connection_value)
    if region_value != "All":
        clauses.append("region = ?"); params.append(region_value)
    rows = q(f"""SELECT {month_expr} AS month, COUNT(*) AS leavers
                 FROM {TABLE} WHERE {' AND '.join(clauses)}
                 GROUP BY month ORDER BY month""", params)
    return rows, None

# ----------------------------- Database validation -----------------------------
if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
    st.info(
        "The dashboard expects the SQLite database at data/raw/airtel.db. "
        "This file is excluded from Git, so it is unavailable in cloud deployments. "
        "Keep it at this path when running the dashboard locally."
    )
    st.stop()

DB_OBJECTS = objects()
if TABLE not in {o["name"] for o in DB_OBJECTS}:
    st.error(f"Required analysis table/view '{TABLE}' was not found.")
    st.write("Available database tables/views:", [o["name"] for o in DB_OBJECTS])
    st.stop()

COLS = columns_of(TABLE)
required = {"connection_type","region","circle_name","is_churned","tenure_years"}
missing = sorted(required - COLS)
if missing:
    st.error("The customer_features table is missing these required columns: " + ", ".join(missing))
    st.stop()

# ----------------------------- Sidebar -----------------------------
st.sidebar.markdown("## AIRTEL")
st.sidebar.caption("TELECOM ANALYTICS  /  CLASS A  /  GROUP 1")
st.sidebar.markdown("---")
st.sidebar.markdown("### Dashboard filters")

connection_values = ["All"] + [r["connection_type"] for r in q(
    f"SELECT DISTINCT connection_type FROM {TABLE} WHERE connection_type IS NOT NULL ORDER BY connection_type"
)]
region_values = ["All"] + [r["region"] for r in q(
    f"SELECT DISTINCT region FROM {TABLE} WHERE region IS NOT NULL ORDER BY region"
)]
connection_filter = st.sidebar.selectbox("Connection type", connection_values, key="connection_filter")
region_filter = st.sidebar.selectbox("Region", region_values, key="region_filter")
st.sidebar.markdown("---")
st.sidebar.markdown("**Source**")
st.sidebar.caption("Validated Airtel SQLite analysis database")
st.sidebar.caption("All filters update applicable cards, charts, selector and table.")
st.sidebar.markdown("---")
st.sidebar.caption("Churn rate = validated leavers ÷ relevant subscriber population. Confirm the source period in your analysis notes.")

where_sql, filter_params = base_filter(connection_filter, region_filter)

# Overview filtered summary: all arithmetic stays inside SQL.
overview_summary = q(
    f"""SELECT COUNT(*) AS subscribers,
               COALESCE(SUM(CASE WHEN is_churned = 1 THEN 1 ELSE 0 END),0) AS leavers,
               ROUND(100.0 * AVG(is_churned),2) AS churn_rate
        FROM {TABLE}{where_sql}""", filter_params
)[0]
fixed_base = q(f"SELECT COUNT(*) AS n FROM {TABLE}")[0]["n"]

# ----------------------------- Header -----------------------------
st.markdown(
    f'<div class="hero"><div class="hero-kicker">AIRTEL TELECOM ANALYTICS &nbsp; / &nbsp; DOMAIN A — RETENTION</div>'
    f'<div class="hero-title">Retention Intelligence</div>'
    f'<div class="hero-note">This dashboard helps the Head of Retention prioritise retention efforts and understand churn patterns.</div>'
    f'<div class="hero-filter">CONNECTION: {html.escape(connection_filter.upper())} &nbsp; • &nbsp; REGION: {html.escape(region_filter.upper())}</div></div>',
    unsafe_allow_html=True,
)

overview_tab, detail_tab = st.tabs(["01  Overview", "02  Detail"])

# ============================================================
# OVERVIEW — exactly 3 cards, then the three required charts.
# ============================================================
with overview_tab:
    st.markdown('<div class="section-head">Retention snapshot</div>',unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3,gap="medium")
    with c1:
        metric_card("Subscriber base",f'{fixed_base:,}',"Full validated subscriber base • fixed card • ignores filters")
    with c2:
        if T4_P_VALUE is None or T4_DIRECTION is None or T4_INTERPRETATION is None:
            metric_card("T4 test result","Awaiting validated result","Enter the actual one-tailed p-value, tested direction and interpretation from your T4 analysis.")
        else:
            metric_card("T4 test result",f"p = {T4_P_VALUE}",f"One-tailed • {T4_DIRECTION} • {T4_INTERPRETATION}")
    with c3:
        rate = f'{overview_summary["churn_rate"]:.2f}%' if overview_summary["churn_rate"] is not None else "N/A"
        metric_card("Filtered churn",rate,
                    f'{overview_summary["leavers"]:,} leavers ÷ {overview_summary["subscribers"]:,} subscribers • period: source analysis period')

    st.markdown('<div class="section-head">Where is churn concentrated?</div>',unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Rates are shown with the subscriber and leaver counts behind them.</div>',unsafe_allow_html=True)

    tenure_rows = q(
        f"""SELECT tenure_years, COUNT(*) AS subscribers,
                   COALESCE(SUM(CASE WHEN is_churned=1 THEN 1 ELSE 0 END),0) AS leavers,
                   ROUND(100.0*AVG(is_churned),2) AS churn_rate
            FROM {TABLE}{where_sql}
            GROUP BY tenure_years ORDER BY tenure_years""", filter_params
    )
    connection_rows = q(
        f"""SELECT connection_type, COUNT(*) AS subscribers,
                   COALESCE(SUM(CASE WHEN is_churned=1 THEN 1 ELSE 0 END),0) AS leavers,
                   ROUND(100.0*AVG(is_churned),2) AS churn_rate
            FROM {TABLE}{where_sql}
            GROUP BY connection_type ORDER BY churn_rate DESC""", filter_params
    )
    circle_rows = q(
        f"""SELECT circle_name, COUNT(*) AS subscribers,
                   COALESCE(SUM(CASE WHEN is_churned=1 THEN 1 ELSE 0 END),0) AS leavers,
                   ROUND(100.0*AVG(is_churned),2) AS churn_rate
            FROM {TABLE}{where_sql}
            GROUP BY circle_name ORDER BY churn_rate DESC, subscribers DESC""", filter_params
    )

    # Hero chart — tenure churn (line chart).
    if tenure_rows:
        fig = go.Figure(go.Scatter(
            x=[str(r["tenure_years"]) for r in tenure_rows],
            y=[r["churn_rate"] for r in tenure_rows],
            mode="lines+markers+text",
            line=dict(color="#b51224",width=3,shape="spline"),
            marker=dict(color="#b51224",size=8,line=dict(color="#fffdf8",width=2)),
            customdata=[[r["leavers"],r["subscribers"]] for r in tenure_rows],
            text=[f'{r["churn_rate"]:.1f}%' for r in tenure_rows],textposition="top center",
            hovertemplate="Tenure: %{x}<br>Churn: %{y:.2f}%<br>Leavers: %{customdata[0]:,}<br>Subscribers: %{customdata[1]:,}<extra></extra>"
        ))
        add_reference(fig,True)
        fig.update_layout(title="How does churn change across subscriber tenure?",
                          xaxis_title="Tenure group (years)",yaxis_title="Churn rate (%)")
        st.plotly_chart(plot_style(fig,195),use_container_width=True,config={"displayModeBar":False})
    else:
        st.info("No tenure records match the selected filters.")

    left,right = st.columns(2,gap="medium")
    with left:
        if connection_rows:
            fig = go.Figure(go.Bar(
                x=[r["connection_type"] for r in connection_rows],
                y=[r["churn_rate"] for r in connection_rows],
                marker_color=["#b51224","#d88976","#d8b88e"][:len(connection_rows)],
                text=[f'{r["churn_rate"]:.1f}%  ({r["leavers"]:,}/{r["subscribers"]:,})' for r in connection_rows],
                textposition="outside",
                hovertemplate="%{x}<br>Churn: %{y:.2f}%<extra></extra>"
            ))
            add_reference(fig,True)
            fig.update_layout(title="Does churn differ between prepaid and postpaid?",
                              xaxis_title="Connection type",yaxis_title="Churn rate (%)")
            st.plotly_chart(plot_style(fig,180),use_container_width=True,config={"displayModeBar":False})
        else:
            st.info("No connection-type records for these filters.")
    with right:
        if circle_rows:
            fig = go.Figure(go.Bar(
                x=[r["churn_rate"] for r in circle_rows],
                y=[r["circle_name"] for r in circle_rows],
                orientation="h",marker_color="#b51224",
                customdata=[[r["leavers"],r["subscribers"]] for r in circle_rows],
                hovertemplate="%{y}<br>Churn: %{x:.2f}%<br>Leavers: %{customdata[0]:,}<br>Subscribers: %{customdata[1]:,}<extra></extra>"
            ))
            add_reference(fig,False)
            fig.update_layout(title="Which circles rank highest for churn?",
                              xaxis_title="Churn rate (%)",yaxis_title="Circle",
                              yaxis=dict(autorange="reversed"))
            st.plotly_chart(plot_style(fig,180),use_container_width=True,config={"displayModeBar":False})
        else:
            st.info("No circle records for these filters.")

# ============================================================
# DETAIL — selected circle, deeper context, max 5 visuals.
# ============================================================
with detail_tab:
    # The selector shares the three-item summary row, as required by the guide.
    circle_options = [r["circle_name"] for r in q(
        f"""SELECT DISTINCT circle_name FROM {TABLE}{where_sql}
            {"AND" if where_sql else "WHERE"} circle_name IS NOT NULL
            ORDER BY circle_name""", filter_params
    )]

    if not circle_options:
        st.warning("No circles match the selected Connection type and Region filters.")
    else:
        if st.session_state.get("selected_circle") not in circle_options:
            st.session_state["selected_circle"] = circle_options[0]

        detail_clauses = ["circle_name = ?"]
        detail_params = [st.session_state["selected_circle"]]
        if connection_filter != "All":
            detail_clauses.append("connection_type = ?")
            detail_params.append(connection_filter)
        if region_filter != "All":
            detail_clauses.append("region = ?")
            detail_params.append(region_filter)
        detail_where = " WHERE " + " AND ".join(detail_clauses)

        a, b, c = st.columns([1.25, 1, 1], gap="small")
        with a:
            selected_circle = st.selectbox("Select Circle", circle_options, key="selected_circle")
        # Rebuild selected-circle WHERE after the selector value is known.
        detail_params = [selected_circle]
        detail_clauses = ["circle_name = ?"]
        if connection_filter != "All":
            detail_clauses.append("connection_type = ?")
            detail_params.append(connection_filter)
        if region_filter != "All":
            detail_clauses.append("region = ?")
            detail_params.append(region_filter)
        detail_where = " WHERE " + " AND ".join(detail_clauses)

        summary = q(
            f"""SELECT COUNT(*) AS subscribers,
                       COALESCE(SUM(CASE WHEN is_churned=1 THEN 1 ELSE 0 END),0) AS leavers,
                       ROUND(100.0*AVG(is_churned),2) AS churn_rate
                FROM {TABLE}{detail_where}""", detail_params
        )[0]
        with b:
            metric_card("Subscribers", f'{summary["subscribers"]:,}', "Selected circle • current filters")
        with c:
            metric_card("Leavers", f'{summary["leavers"]:,}', "Selected circle • current filters")

        st.markdown(
            f'<div class="section-head">{html.escape(selected_circle)} — selected circle profile</div>',
            unsafe_allow_html=True,
        )

        # Five detail visuals maximum; all measures are calculated in SQL.
        v1, v2, v3 = st.columns(3, gap="small")
        v4, v5 = st.columns(2, gap="small")

        # 1. Selected circle vs the supplied national reference.
        circle_rate = summary["churn_rate"] if summary["churn_rate"] is not None else 0
        fig = go.Figure(go.Bar(
            x=[selected_circle, "National ref."],
            y=[circle_rate, NATIONAL_REFERENCE],
            marker_color=["#b51224", "#cbb79a"],
            text=[f"{circle_rate:.1f}% ({summary['leavers']:,})", f"{NATIONAL_REFERENCE:.1f}%"],
            textposition="outside",
        ))
        fig.update_layout(title="Circle churn vs national reference", xaxis_title="Comparison", yaxis_title="Churn (%)")
        with v1:
            st.plotly_chart(plot_style(fig, 158), use_container_width=True, config={"displayModeBar": False})
            st.caption("23.75% is a reference, not automatically a target.")

        # 2. Open-ticket subscribers, only when a validated field exists.
        ticket_flag = optional_column(["has_open_ticket", "open_ticket_flag", "is_open_ticket", "open_ticket"])
        ticket_count = optional_column(["open_ticket_count", "open_tickets", "num_open_tickets"])
        with v2:
            if ticket_flag:
                col = sql_ident(ticket_flag)
                condition = f"({col}=1 OR LOWER(CAST({col} AS TEXT)) IN ('yes','true','open'))"
                ticket_row = q(
                    f"""SELECT COUNT(*) AS subscribers,
                               COALESCE(SUM(CASE WHEN {condition} THEN 1 ELSE 0 END),0) AS ticket_subscribers,
                               ROUND(100.0*SUM(CASE WHEN {condition} THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1) AS ticket_share
                        FROM {TABLE}{detail_where}""", detail_params
                )[0]
                fig = go.Figure(go.Bar(
                    x=["Open-ticket", "Other"],
                    y=[ticket_row["ticket_subscribers"], ticket_row["subscribers"]-ticket_row["ticket_subscribers"]],
                    marker_color=["#b51224", "#d9c7ad"],
                    text=[f'{ticket_row["ticket_subscribers"]:,}', f'{ticket_row["subscribers"]-ticket_row["ticket_subscribers"]:,}'],
                    textposition="outside",
                ))
                fig.update_layout(title=f'Open-ticket subscribers • {ticket_row["ticket_share"] or 0:.1f}%', xaxis_title="Ticket status", yaxis_title="Subscribers")
                st.plotly_chart(plot_style(fig, 158), use_container_width=True, config={"displayModeBar": False})
            elif ticket_count:
                col = sql_ident(ticket_count)
                ticket_row = q(
                    f"""SELECT COUNT(*) AS subscribers,
                               COALESCE(SUM(CASE WHEN CAST({col} AS REAL)>0 THEN 1 ELSE 0 END),0) AS ticket_subscribers,
                               ROUND(100.0*SUM(CASE WHEN CAST({col} AS REAL)>0 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1) AS ticket_share
                        FROM {TABLE}{detail_where}""", detail_params
                )[0]
                fig = go.Figure(go.Bar(x=["Open-ticket", "Other"],
                    y=[ticket_row["ticket_subscribers"], ticket_row["subscribers"]-ticket_row["ticket_subscribers"]],
                    marker_color=["#b51224", "#d9c7ad"], text=[ticket_row["ticket_subscribers"], ticket_row["subscribers"]-ticket_row["ticket_subscribers"]], textposition="outside"))
                fig.update_layout(title=f'Open-ticket subscribers • {ticket_row["ticket_share"] or 0:.1f}%', xaxis_title="Ticket status", yaxis_title="Subscribers")
                st.plotly_chart(plot_style(fig, 158), use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Open-ticket measure unavailable: no validated ticket field was found.")

        # 3. Churn by tenure within selected circle (line chart).
        circle_tenure = q(
            f"""SELECT tenure_years, COUNT(*) AS subscribers,
                       COALESCE(SUM(CASE WHEN is_churned=1 THEN 1 ELSE 0 END),0) AS leavers,
                       ROUND(100.0*AVG(is_churned),2) AS churn_rate
                FROM {TABLE}{detail_where}
                GROUP BY tenure_years ORDER BY tenure_years""", detail_params
        )
        with v3:
            if circle_tenure:
                fig = go.Figure(go.Scatter(
                    x=[str(r["tenure_years"]) for r in circle_tenure],
                    y=[r["churn_rate"] for r in circle_tenure],
                    mode="lines+markers+text", line=dict(color="#b51224",width=3,shape="spline"),
                    marker=dict(color="#b51224",size=8,line=dict(color="#fffdf8",width=2)),
                    customdata=[[r["leavers"], r["subscribers"]] for r in circle_tenure],
                    text=[f'{r["churn_rate"]:.1f}%' for r in circle_tenure], textposition="top center",
                    hovertemplate="Tenure: %{x}<br>Churn: %{y:.2f}%<br>Leavers: %{customdata[0]}<br>Subscribers: %{customdata[1]}<extra></extra>"
                ))
                add_reference(fig, True)
                fig.update_layout(title="Churn by tenure", xaxis_title="Tenure (years)", yaxis_title="Churn (%)")
                st.plotly_chart(plot_style(fig, 158), use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No tenure data for this circle.")

        # 4. Prepaid/postpaid comparison in selected circle.
        circle_connection = q(
            f"""SELECT connection_type, COUNT(*) AS subscribers,
                       COALESCE(SUM(CASE WHEN is_churned=1 THEN 1 ELSE 0 END),0) AS leavers,
                       ROUND(100.0*AVG(is_churned),2) AS churn_rate
                FROM {TABLE}{detail_where}
                GROUP BY connection_type ORDER BY churn_rate DESC""", detail_params
        )
        with v4:
            if circle_connection:
                fig = go.Figure(go.Bar(
                    x=[r["connection_type"] for r in circle_connection],
                    y=[r["churn_rate"] for r in circle_connection],
                    marker_color=["#b51224", "#d89a83"][:len(circle_connection)],
                    customdata=[[r["leavers"], r["subscribers"]] for r in circle_connection],
                    text=[f'{r["churn_rate"]:.1f}% ({r["leavers"]:,}/{r["subscribers"]:,})' for r in circle_connection],
                    textposition="outside",
                ))
                add_reference(fig, True)
                fig.update_layout(title="Prepaid vs postpaid churn", xaxis_title="Connection type", yaxis_title="Churn (%)")
                st.plotly_chart(plot_style(fig, 158), use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No connection-type data for this circle.")

        # 5. Monthly leavers line chart, only if a validated churn date/month exists.
        with v5:
            monthly_rows, monthly_note = available_monthly_data(selected_circle, connection_filter, region_filter)
            if monthly_rows is not None and monthly_rows:
                fig = go.Figure(go.Scatter(
                    x=[r["month"] for r in monthly_rows], y=[r["leavers"] for r in monthly_rows],
                    mode="lines+markers+text", line=dict(color="#b51224",width=3,shape="spline"),
                    marker=dict(color="#b51224",size=8), text=[r["leavers"] for r in monthly_rows], textposition="top center",
                ))
                fig.update_layout(title="Monthly leavers", xaxis_title="Churn month", yaxis_title="Leaver count")
                st.plotly_chart(plot_style(fig, 158), use_container_width=True, config={"displayModeBar": False})
            elif monthly_rows is not None:
                st.info("No monthly leavers match the current filters.")
            else:
                st.info(monthly_note)

st.caption("Source: customer_features in data/raw/airtel.db. Churn rate = leavers (is_churned=1) ÷ selected subscriber population. "
           "State the validated source period in your analysis notes. T4 remains unconfigured until its actual validated result is entered.")
