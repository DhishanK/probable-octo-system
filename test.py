import streamlit as st
from sqlalchemy import create_engine, text
import yfinance as yf
import pandas as pd
import datetime

st.set_page_config(page_title="S&P 500 Historical Dashboard", layout="centered")

st.title("📈 S&P 500 Historical Dashboard")

# =====================================================================
# DATA SYNC & LOAD ENGINE
# =====================================================================
@st.cache_data
def sync_and_load_db_data():
    DATABASE_URL = "postgresql+psycopg://postgres:Orange#11@localhost:5432/postgres"
    engine = create_engine(DATABASE_URL)

    # STAGE 1: Ensure Tables Exist
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS stock_prices (
        "Date" DATE PRIMARY KEY, "Open" NUMERIC, "High" NUMERIC, "Low" NUMERIC, "Close" NUMERIC, "Volume" BIGINT
    );
    CREATE TABLE IF NOT EXISTS stock_prices_filled (
        "Date" DATE PRIMARY KEY, "Open" NUMERIC, "High" NUMERIC, "Low" NUMERIC, "Close" NUMERIC, "Volume" BIGINT
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_table_sql))

    # STAGE 2: Get Max Date
    with engine.connect() as conn:
        max_db_date = conn.execute(text('SELECT MAX("Date") FROM stock_prices;')).scalar()

    # STAGE 3: Sync Fresh Data from Yahoo Finance
    if max_db_date is not None:
        fetch_start_date = (pd.to_datetime(max_db_date) + pd.Timedelta(days=0)).strftime('%Y-%m-%d')
        if fetch_start_date <= datetime.date.today().strftime('%Y-%m-%d'):
            new_data = yf.Ticker("^GSPC").history(start=fetch_start_date)
            if not new_data.empty:
                new_data = new_data.reset_index()
                new_data['Date'] = pd.to_datetime(new_data['Date']).dt.date
                new_data = new_data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                new_data = new_data[new_data['Date'] > max_db_date] # Prevent Unique Violations
                if not new_data.empty:
                    new_data.to_sql('stock_prices', con=engine, if_exists='append', index=False)
                    st.toast(f"Synced {len(new_data)} new records!", icon="💾")

    # STAGE 4: Rebuild missing date gaps table
    fill_data_sql = """
    TRUNCATE TABLE stock_prices_filled;
    INSERT INTO stock_prices_filled ("Date", "Open", "High", "Low", "Close", "Volume")
    WITH daily_calendar AS (
        SELECT generate_series((SELECT MIN("Date") FROM stock_prices), (SELECT MAX("Date") FROM stock_prices), '1 day'::interval)::date AS calc_date
    ),
    joined_data AS (
        SELECT c.calc_date AS "Date", s."Open", s."High", s."Low", s."Close", s."Volume", COUNT(s."Close") OVER (ORDER BY c.calc_date) AS grp
        FROM daily_calendar c LEFT JOIN stock_prices s ON c.calc_date = s."Date"
    ),
    all_filled_dates AS (
        SELECT "Date",
            FIRST_VALUE("Open") OVER (PARTITION BY grp ORDER BY "Date") AS "Open",
            FIRST_VALUE("High") OVER (PARTITION BY grp ORDER BY "Date") AS "High",
            FIRST_VALUE("Low") OVER (PARTITION BY grp ORDER BY "Date") AS "Low",
            FIRST_VALUE("Close") OVER (PARTITION BY grp ORDER BY "Date") AS "Close",
            FIRST_VALUE("Volume") OVER (PARTITION BY grp ORDER BY "Date") AS "Volume"
        FROM joined_data
    )
    SELECT f.* FROM all_filled_dates f WHERE f."Date" NOT IN (SELECT "Date" FROM stock_prices);
    """
    with engine.begin() as conn:
        conn.execute(text(fill_data_sql))

    # STAGE 5: Read complete dataset back via UNION
    union_query = 'SELECT "Date", "Close" FROM stock_prices UNION ALL SELECT "Date", "Close" FROM stock_prices_filled ORDER BY "Date" ASC;'
    df = pd.read_sql(union_query, con=engine)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    return df

with st.spinner("Processing structural timelines..."):
    data = sync_and_load_db_data()

min_data_date = data['Date'].min()
max_data_date = data['Date'].max()

# =====================================================================
# SIDEBAR CONTROLS
# =====================================================================
st.sidebar.header("Timeframe")
start_date = st.sidebar.date_input("Global Start Date", value=datetime.date(2000, 1, 1), min_value=min_data_date, max_value=max_data_date)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Return Threshold Filter")
threshold = st.sidebar.number_input(
    "Set Return Threshold (%)", 
    value=100.0, 
    step=1.0, 
    help="Draws a target line on the returns chart and filters periods exceeding this value."
)

# Initialize active period length session tracking state
if "active_period" not in st.session_state:
    st.session_state.active_period = 5  # Default initialization to 5 years

# =====================================================================
# YAHOO FINANCE-STYLE PERIOD BUTTONS
# =====================================================================
st.write("### Select Horizon Period in Years")
buttons = [1, 3, 5, 10, 15, 20, 25, 30, 35, 40, 45]

# Render horizontal timeline interval selection row buttons 
cols = st.columns(len(buttons))
for i, y in enumerate(buttons):
    # Highlight the currently chosen active filter button
    button_label = f"**{y}**" if st.session_state.active_period == y else f"{y}"
    if cols[i].button(button_label, key=f"btn_{y}", use_container_width=True):
        st.session_state.active_period = y



df_calc = data.copy().sort_values('Date')
days_offset = int(st.session_state.active_period * 365.25)

# Vectorized shift comparison for fast execution
df_calc['Past_Close'] = df_calc['Close'].shift(days_offset)
df_calc['Period_Return'] = ((df_calc['Close'] - df_calc['Past_Close']) / df_calc['Past_Close']) * 100

# Boundary Protection Guard
target_end_date = pd.to_datetime(start_date + pd.Timedelta(days=days_offset)).date()

if target_end_date > max_data_date:
    st.error(f"⚠️ The selected **{st.session_state.active_period}Y** horizon extends to **{target_end_date}**, which exceeds your latest available database record (**{max_data_date}**). Try adjusting your Global Start Date back.")
    st.stop()

# Grab localized specific coordinates
start_price = df_calc[df_calc['Date'] == start_date]['Close'].values[0]
end_price = df_calc[df_calc['Date'] == target_end_date]['Close'].values[0]

total_return = ((end_price - start_price) / start_price) * 100
cagr = (((end_price / start_price) ** (1 / st.session_state.active_period)) - 1) * 100

# Display high-level metrics banners

# =====================================================================
# GRAPH TIME-SERIES ROLLING RETURN VS THRESHOLD
# =====================================================================
#st.markdown("---")
st.write(f"### S&P 500 {st.session_state.active_period}-Year Rolling Returns Trends")
st.write("This graph maps what the total return *would have been* if you invested exactly $N$ years prior to that day.")

filtered_returns_df = df_calc[(df_calc['Date'] >= start_date + pd.Timedelta(days=days_offset)) & (df_calc['Date'] <= datetime.date.today())].copy()
filtered_returns_df['Threshold Line'] = threshold



# Backtrace accurate target transaction initialization timestamps
filtered_returns_df['Investment Date'] = filtered_returns_df['Date'].apply(lambda x: pd.to_datetime(x) - pd.Timedelta(days=days_offset))
filtered_returns_df['Investment Date'] = pd.to_datetime(filtered_returns_df['Investment Date']).dt.date


st.line_chart(
    filtered_returns_df, 
    x='Investment Date', 
    y=['Period_Return', 'Threshold Line'], 
    color=['#1f77b4', '#d62728'] # Financial Blue for returns data, Red for threshold marker line
)

st.write(f"### Periods Where {st.session_state.active_period}-Year Return Exceeded {threshold}%")

outperformance_df = filtered_returns_df[filtered_returns_df['Period_Return'] > threshold].copy()

if not outperformance_df.empty:
    table_output = outperformance_df[['Investment Date', 'Date', 'Period_Return']].rename(
        columns={
            'Investment Date': 'Purchase Date',
            'Date': 'Maturation Date',
            'Period_Return': 'Total Return (%)'
        }
    ).sort_values('Purchase Date')

    st.write(f"Found **{len(table_output):,}** calendar days matching criteria out of **{len(outperformance_df):,}**")
    st.dataframe(table_output, use_container_width=True, hide_index=True)
else:
    st.info(f"No {st.session_state.active_period}-year investment horizons yielded returns higher than {threshold}% during this specific timeframe.")
