
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# ---- Page config ----
st.set_page_config(page_title="Superstore", layout="wide")
st.title("Sample Superstore")
st.markdown(
    "<style>div.block-container{padding-top:2rem;}</style>",
    unsafe_allow_html=True
)

# ---- Data loading helpers ----
DATA_FALLBACK = Path(__file__).parent / "data" / "Superstore.xls"  # put your file here

@st.cache_data
def load_uploaded_file(file):
    """
    Load dataframe from an uploaded file-like object.
    Supports csv, txt, xlsx, xls. Tries to parse dates in 'Order Date'.
    """
    name = file.name.lower()
    if name.endswith(".csv") or name.endswith(".txt"):
        df = pd.read_csv(file, encoding="ISO-8859-1")
    elif name.endswith(".xlsx"):
        df = pd.read_excel(file, engine="openpyxl")
    elif name.endswith(".xls"):
        df = pd.read_excel(file, engine="xlrd")
    else:
        raise ValueError("Unsupported file type. Please upload csv/txt/xlsx/xls.")
    # Ensure Order Date is datetime
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    return df

@st.cache_data
def load_fallback_file(path: Path):
    """
    Load bundled dataset from repo using a relative path.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Fallback file not found at {path}. "
            "Upload a file or add the dataset to your repo under 'data/Superstore.xlsx'."
        )
    # Choose engine based on extension
    if path.suffix.lower() == ".xlsx":
        df = pd.read_excel(path, engine="openpyxl")
    elif path.suffix.lower() == ".xls":
        df = pd.read_excel(path, engine="xlrd")
    else:
        # Allow csv as fallback too
        df = pd.read_csv(path, encoding="ISO-8859-1")
    # Ensure Order Date is datetime
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    return df

# ---- File uploader ----
uploaded = st.file_uploader("Upload a file", type=["csv", "txt", "xlsx", "xls"])

# ---- Load data ----
if uploaded is not None:
    df = load_uploaded_file(uploaded)
    st.success(f"Loaded file: **{uploaded.name}** ({len(df)} rows)")
else:
    df = load_fallback_file(DATA_FALLBACK)
    st.info(f"Using bundled dataset: **{DATA_FALLBACK.name}** ({len(df)} rows)")

# ---- Basic validations ----
required_cols = {"Order Date", "Region", "State", "City", "Category", "Sales"}
missing = required_cols - set(df.columns)
if missing:
    st.error(
        f"Your dataset is missing columns: {', '.join(sorted(missing))}. "
        "Please upload the correct Superstore file."
    )
    st.stop()

# ---- Date filter ----
col1, col2 = st.columns((2, 2))

# Clean up and establish min/max dates
df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
df = df.dropna(subset=["Order Date"])

startdate = df["Order Date"].min()
enddate = df["Order Date"].max()

with col1:
    date1 = pd.to_datetime(st.date_input("Start date", startdate))
with col2:
    date2 = pd.to_datetime(st.date_input("End date", enddate))

# Ensure valid range
if date1 > date2:
    st.warning("Start date is after end date. Adjust the date range.")
    st.stop()

df = df[(df["Order Date"] >= date1) & (df["Order Date"] <= date2)].copy()

# ---- Sidebar filters ----
st.sidebar.header("Choose your filter:")

# Region
region = st.sidebar.multiselect("Pick your Region", sorted(df["Region"].dropna().unique()))
df2 = df if not region else df[df["Region"].isin(region)]

# State
state = st.sidebar.multiselect("Pick the State", sorted(df2["State"].dropna().unique()))
df3 = df2 if not state else df2[df2["State"].isin(state)]

# City
city = st.sidebar.multiselect("Pick the City", sorted(df3["City"].dropna().unique()))

# Final filtered df
if not region and not state and not city:
    filtered_df = df
elif not state and not city:
    filtered_df = df[df["Region"].isin(region)]
elif not region and not city:
    filtered_df = df[df["State"].isin(state)]
elif state and city:
    filtered_df = df3[df3["State"].isin(state) & df3["City"].isin(city)]
elif region and city:
    filtered_df = df3[df3["Region"].isin(region) & df3["City"].isin(city)]
elif region and state:
    filtered_df = df3[df3["Region"].isin(region) & df3["State"].isin(state)]
elif city:
    filtered_df = df3[df3["City"].isin(city)]
else:
    filtered_df = df3[
        df3["Region"].isin(region) &
        df3["State"].isin(state) &
        df3["City"].isin(city)
    ]

# ---- Charts ----
category_df = filtered_df.groupby(by=["Category"], as_index=False)["Sales"].sum()

with col1:
    st.subheader("Category wise Sales")
    fig = px.bar(
        category_df,
        x="Category",
        y="Sales",
        text=[f'${x:,.2f}' for x in category_df["Sales"]],
        template="seaborn"
    )
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Region wise Sales")
    region_sum = filtered_df.groupby(by=["Region"], as_index=False)["Sales"].sum()
    fig = px.pie(region_sum, values="Sales", names="Region", hole=0.5)
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

cl1, cl2 = st.columns((2, 2))
with cl1:
    with st.expander("Category_ViewData"):
        st.write(category_df.style.background_gradient(cmap="Blues"))
        csv = category_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Data",
            data=csv,
            file_name="Category.csv",
            mime="text/csv",
            help="Click here to download the data as a CSV file"
        )

with cl2:
    with st.expander("Region_ViewData"):
        st.write(region_sum.style.background_gradient(cmap="Oranges"))
        csv = region_sum.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Data",
            data=csv,
            file_name="Region.csv",
            mime="text/csv",
            help="Click here to download the data as a CSV file"
        )

# ---- Time series ----
st.subheader("Time Series Analysis")
filtered_df["month_year"] = filtered_df["Order Date"].dt.to_period("M")
linechart = (
    filtered_df
    .groupby(filtered_df["month_year"].dt.strftime("%Y-%b"))["Sales"]
    .sum()
    .reset_index()
    .rename(columns={"month_year": "Month"})
)

fig2 = px.line(
    linechart,
    x="Month",
    y="Sales",
    labels={"Sales": "Amount"},
    height=500,
    template="plotly_white"
)
st.plotly_chart(fig2, use_container_width=True)

with st.expander("View Data of TimeSeries:"):
    st.write(linechart.T.style.background_gradient(cmap="Blues"))
    csv = linechart.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download Data",
        data=csv,
        file_name="TimeSeries.csv",
        mime="text/csv"
    )
