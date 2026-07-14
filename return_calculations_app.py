
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date

st.set_page_config(page_title="S&P 500 100-Year Return Calculator", layout="centered")

st.title("S&P 500 Historical Return Calculator")
st.write("Calculate the performance of the S&P 500 over any custom interval using data from Yahoo Finance.")

def load_and_clean_data():
    # 1. Fetch maximum available history from Yahoo Finance (^GSPC)
    sp500 = yf.Ticker("^GSPC")
    df = sp500.history(period="max")

    # Clean up index and isolate the Close price
    df = df.reset_index()
    df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None) # Remove timezone
    df.set_index('Date', inplace=True)
    df = df[['Close']]

    # 2. Create a complete, unbroken daily calendar from min to max date
    full_calendar = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')

    # Reindex the DataFrame to include EVERY single day (weekends/holidays become NaN)
    df_filled = df.reindex(full_calendar)

    # 3. Forward-fill missing values with the last known day's Close price
    df_filled['Close'] = df_filled['Close'].ffill()

    # Reset index and cleanup naming for the Streamlit app
    df_filled = df_filled.reset_index().rename(columns={'index': 'Date'})
    df_filled['Date'] = df_filled['Date'].dt.date
    return df_filled

df = load_and_clean_data()



min_date = df['Date'].min()
max_date = df['Date'].max()

st.sidebar.header("Select Investment Interval")

start_date = st.sidebar.date_input("Start Date", value=date(2000,1,3), min_value = min_date, max_value = max_date) 
end_date = st.sidebar.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

if start_date >= end_date:
    st.error("Error: Start Date must be before End Date.")
else:
    start_row = df[df['Date'] >= start_date].iloc[0]
    end_row = df[df['Date'] <= end_date].iloc[-1]

    actual_start_date = start_row['Date']
    actual_end_date = end_row['Date'] 

    start_price = start_row['Close']
    end_price = end_row['Close']

    total_return = ((end_price - start_price) / start_price) * 100
    years = (end_date - start_date).days / 365.25
    cagr = (((end_price / start_price) ** (1 / years)) - 1) * 100 if years > 0 else 0

    # Display Metrics
    st.subheader(f"Results: {start_date} to {end_date}")
    col1, col2 = st.columns(2)
    col1.metric(label="Total Return", value=f"{total_return:,.2f}%")
    col2.metric(label="CAGR (Annualized)", value=f"{cagr:.2f}%" if years >= 0.5 else "N/A (< 6 months)")

    st.write(f"**Starting Index Price:** ${start_price:,.2f}")
    st.write(f"**Ending Index Price:** ${end_price:,.2f}")

    # Charting
    filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
    st.line_chart(data=filtered_df, x='Date', y='Close')


st.markdown("---")
st.header("📊 Historical Rolling Period Analysis")
st.write(f"Input a custom time horizon to see how *every* calendar day performed **between {start_date} and {end_date}**.")

rolling_years = st.number_input("Enter period length (in years):", min_value=1, max_value=50, value=5, step=1)

if st.button("Calculate Rolling Returns"):
    with st.spinner(f"Analyzing rolling {rolling_years}-year periods..."):

        # 1. Filter the data based on user-selected start and end dates first
        df_bounded = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].copy()

        if df_bounded.empty:
            st.error("No data available in the selected date range.")
            st.stop()

        df_bounded['Date'] = pd.to_datetime(df_bounded['Date'])
        df_bounded.set_index('Date', inplace=True)

        days_offset = int(rolling_years * 365.25)
        rolling_results = []

        max_idx_date = df_bounded.index.max()

        # 2. Loop through the bounded dataset
        for start_dt, row in df_bounded.iterrows():
            target_end_dt = start_dt + pd.Timedelta(days=days_offset)

            # Ensure the rolling window doesn't overflow the user's chosen End Date
            if target_end_dt > max_idx_date:
                break 

            start_price = row['Close']
            # Direct slice out the exact forward-filled calendar day within our bounds
            end_price = df_bounded.loc[target_end_dt, 'Close']

            period_return = ((end_price - start_price) / start_price) * 100

            rolling_results.append({
                "Start Date": start_dt.date(),
                "End Date": target_end_dt.date(),
                "Return (%)": round(period_return, 2)
            })

        results_df = pd.DataFrame(rolling_results)

        # 3. Render the statistics
        if not results_df.empty:
            st.subheader(f"Summary Statistics for {rolling_years}-Year Horizons ({start_date} to {end_date})")

            best_period = results_df.loc[results_df['Return (%)'].idxmax()]
            worst_period = results_df.loc[results_df['Return (%)'].idxmin()]
            avg_return = results_df['Return (%)'].mean()
            pct_positive = (results_df['Return (%)'] > 0).sum() / len(results_df) * 100

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Average Return", f"{avg_return:.2f}%")
            col2.metric("Win Rate", f"{pct_positive:.1f}%")
            col3.metric("Best Ever", f"{best_period['Return (%)']}%")
            col4.metric("Worst Ever", f"{worst_period['Return (%)']}%")

            st.write(f"🏆 **Best Period in Range:** {best_period['Start Date']} to {best_period['End Date']}")
            st.write(f"📉 **Worst Period in Range:** {worst_period['Start Date']} to {worst_period['Worst Ever' if 'Worst Ever' in worst_period else 'End Date']}")

            st.dataframe(results_df, use_container_width=True)
        else:
            st.warning(f"The selected date range ({years:.2f} years total) is too short to calculate a {rolling_years}-year rolling return.")
