import streamlit as st
import pandas as pd
import plotly.express as px
import pickle
from streamlit_option_menu import option_menu

# Page configuration
st.set_page_config(page_title="Startup Dashboard",page_icon="🚀" layout="wide")

# Sidebar navigation
with st.sidebar:
    page = option_menu("Startup Dashboard",
                       ["Overview", "Profile & Geography", "Model Insights", "Predict"],
                       icons=["house", "globe", "bar-chart-line", "graph-up-arrow"],
                       menu_icon="cast", default_index=0)

# Load CSV files
@st.cache_data
def load_data():
    try:
        df_main = pd.read_csv("startup_predictions-offline.csv")
        df_geo = pd.read_csv("Final-startup_success_predictions.csv")
        df_imp = pd.read_csv("feature_importance.csv")
        return df_main, df_geo, df_imp
    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
        st.stop()

df, df_geo, df_imp = load_data()

# Convert one-hot encoded columns back to categorical
def reverse_one_hot(df, prefix):
    cols = [col for col in df.columns if col.startswith(prefix + "_")]
    if cols:
        df[prefix] = df[cols].idxmax(axis=1).str.replace(f"{prefix}_", "")
    return df

for col in ["Country", "Industry", "Funding Stage"]:
    df = reverse_one_hot(df, col)
    df_geo = reverse_one_hot(df_geo, col)

# Handle Startup Age and Predicted Category
if "Startup Age" not in df_geo.columns and "Founded Year" in df_geo.columns:
    df_geo["Startup Age"] = 2025 - df_geo["Founded Year"]

if "Predicted Category" not in df_geo.columns and "Predicted" in df_geo.columns:
    df_geo["Predicted Category"] = df_geo["Predicted"].map({0: "Low", 1: "Medium", 2: "High"})

# ---------------- Overview Page ----------------
if page == "Overview":
    st.title("🚀 Startup Overview + Success Analysis")
    st.subheader("Filter Data")
    df_filtered = df.copy()

    c1, c2, c3 = st.columns(3)
    with c1:
        country = st.selectbox("Country", ["All"] + sorted(df["Country"].dropna().unique().tolist()))
        if country != "All":
            df_filtered = df_filtered[df_filtered["Country"] == country]

    with c2:
        industry = st.selectbox("Industry", ["All"] + sorted(df["Industry"].dropna().unique().tolist()))
        if industry != "All":
            df_filtered = df_filtered[df_filtered["Industry"] == industry]

    with c3:
        stage = st.selectbox("Funding Stage", ["All"] + sorted(df["Funding Stage"].dropna().unique().tolist()))
        if stage != "All":
            df_filtered = df_filtered[df_filtered["Funding Stage"] == stage]

    if df_filtered.empty:
        st.warning("No records match the selected filters.")
    else:
        st.subheader("📌 Key Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Startups", len(df_filtered))
        m2.metric("Avg Funding ($M)", f"{df_filtered['Total Funding ($M)'].mean():,.2f}")
        m3.metric("Avg Valuation ($B)", f"{df_filtered['Valuation ($B)'].mean():,.2f}")
        m4.metric("Total Acquisitions", int(df_filtered["Acquired?"].sum()))

        st.subheader("📊 Success Category vs Funding Stage")
        col1, col2 = st.columns(2)
        with col1:
            if "Predicted Category" in df_filtered.columns:
                fig_pie = px.pie(df_filtered, names="Predicted Category", title="Success Category Distribution", hole=0.3)
                st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            if "Funding Stage" in df_filtered.columns and "Predicted Category" in df_filtered.columns:
                fig_bar = px.histogram(df_filtered, x="Funding Stage", color="Predicted Category", barmode="group",
                                       category_orders={"Predicted Category": ["Low", "Medium", "High"]})
                st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("📌 Success by Industry (Treemap)")
        if "Industry" in df_filtered.columns and "Total Funding ($M)" in df_filtered.columns:
            fig_tree = px.treemap(df_filtered,
                                  path=[px.Constant("All"), "Industry", "Predicted Category"],
                                  values="Total Funding ($M)", title="Treemap of Industry Success")
            st.plotly_chart(fig_tree, use_container_width=True)

# ---------------- Profile & Geography Page ----------------
elif page == "Profile & Geography":
    st.title("🌍 Startup Profile & Geography")
    df_filtered_geo = df_geo.copy()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        country = st.selectbox("Country", ["All"] + sorted(df_geo["Country"].dropna().unique().tolist()))
        if country != "All":
            df_filtered_geo = df_filtered_geo[df_filtered_geo["Country"] == country]

    with col2:
        industry = st.selectbox("Industry", ["All"] + sorted(df_geo["Industry"].dropna().unique().tolist()))
        if industry != "All":
            df_filtered_geo = df_filtered_geo[df_filtered_geo["Industry"] == industry]

    with col3:
        stage = st.selectbox("Funding Stage", ["All"] + sorted(df_geo["Funding Stage"].dropna().unique().tolist()))
        if stage != "All":
            df_filtered_geo = df_filtered_geo[df_filtered_geo["Funding Stage"] == stage]

    with col4:
        pred_cat = st.selectbox("Predicted Category", ["All", "Low", "Medium", "High"])
        if pred_cat != "All":
            df_filtered_geo = df_filtered_geo[df_filtered_geo["Predicted Category"] == pred_cat]

    if df_filtered_geo.empty:
        st.warning("No data for selected filters.")
    else:
        st.subheader("🗺️ Global Startup Spread")
        if "Country" in df_filtered_geo.columns:
            fig_map = px.scatter_geo(df_filtered_geo, locations="Country", locationmode='country names',
                                     size="Total Funding ($M)", color="Country",
                                     hover_name="Country", title="Startup Spread by Country")
            st.plotly_chart(fig_map, use_container_width=True)

        st.subheader("🏭 Avg Funding by Industry")
        if "Industry" in df_filtered_geo.columns:
            avg_funding = df_filtered_geo.groupby("Industry")["Total Funding ($M)"].mean().reset_index()
            fig_ind = px.bar(avg_funding, x="Industry", y="Total Funding ($M)", title="Avg Funding by Industry")
            st.plotly_chart(fig_ind, use_container_width=True)

        st.subheader("📈 Age vs Valuation")
        if "Startup Age" in df_filtered_geo.columns and "Valuation ($B)" in df_filtered_geo.columns:
            fig_scatter = px.scatter(df_filtered_geo, x="Startup Age", y="Valuation ($B)",
                                     color="Predicted Category", hover_data=["Country", "Industry"],
                                     title="Startup Age vs Valuation")
            st.plotly_chart(fig_scatter, use_container_width=True)

# ---------------- Model Insights Page ----------------
elif page == "Model Insights":
    st.title("📊 Model Insights & Feature Importance")

    st.subheader("🧠 Feature Importance")
    fig_feat = px.bar(df_imp.sort_values(by="Importance", ascending=True),
                      x="Importance", y="Feature", orientation="h",
                      title="Feature Importance (Low to High)")
    st.plotly_chart(fig_feat, use_container_width=True)

    st.subheader("📋 Complete Dataset (Offline Predictions)")
    with st.expander("View Full Dataset"):
        st.dataframe(df)

# ---------------- Predict Page ----------------
elif page == "Predict":
    st.title("🎯 Predict Startup Success Score")

    # Load model
    with open("success_score_model.pkl", "rb") as f:
        model = pickle.load(f)

    with open("model_features.pkl", "rb") as f:
        model_features = pickle.load(f)

    with st.form("input_form"):
        st.subheader("Enter Startup Details")
        age = st.number_input("Startup Age", min_value=0, max_value=100, value=3)
        funding = st.number_input("Total Funding ($M)", min_value=0, value=1)
        employees = st.number_input("Number of Employees", min_value=1, value=10)
        revenue = st.number_input("Annual Revenue ($M)", min_value=0, value=2)
        valuation = st.number_input("Valuation ($B)", min_value=0.0, value=0.5)
        customers = st.number_input("Customer Base (Millions)", min_value=0, value=1)
        followers = st.number_input("Social Media Followers", min_value=0, value=1000)
        acquired = st.selectbox("Acquired?", ["No", "Yes"])
        ipo = st.selectbox("IPO?", ["No", "Yes"])
        country = st.selectbox("Country", ["USA", "India", "UK", "Germany", "Other"])
        industry = st.selectbox("Industry", ["Tech", "Health", "Finance", "Education", "Other"])
        stage = st.selectbox("Funding Stage", ["Seed", "Series A", "Series B", "Series C", "Public"])
        tech = st.selectbox("Tech Stack", ["Python", "Java", "Node.js", "Ruby", "Other"])

        submitted = st.form_submit_button("Predict Success Score")

    if submitted:
        input_dict = {
            "Total Funding ($M)": funding,
            "Number of Employees": employees,
            "Annual Revenue ($M)": revenue,
            "Valuation ($B)": valuation,
            "Customer Base (Millions)": customers,
            "Social Media Followers": followers,
            "Acquired?": 1 if acquired == "Yes" else 0,
            "IPO?": 1 if ipo == "Yes" else 0,
            "Startup Age": age,
        }

        df_input = pd.DataFrame([input_dict])

        for col in model_features:
            if col not in df_input.columns:
                df_input[col] = 0

        cat_values = {
            f"Country_{country}": 1,
            f"Industry_{industry}": 1,
            f"Funding Stage_{stage}": 1,
            f"Tech Stack_{tech}": 1
        }

        for col in cat_values:
            if col in df_input.columns:
                df_input[col] = 1

        df_input = df_input[model_features]

        score = model.predict(df_input)[0]
        st.success(f"🎯 Predicted Success Score: **{round(score, 2)}**")
