import math
from datetime import date
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

def pmt_graph(amount, interest, months, start = date.today()):
    start_date = pd.Timestamp(start).normalize()
    #Monthly
    monthly_rate = (interest / 100) / 12
    pmt = amount * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)

    #x_months = [0]
    monthly_dates = [start_date]
    remaining_balances = [round(amount, 2)]
    total_monthly_interest = 0

    current_balance = amount
    for month in range(1, months + 1):
        interest_this_month = current_balance * monthly_rate
        total_monthly_interest += interest_this_month
        principal_this_month = pmt - interest_this_month
        current_balance -= principal_this_month

        payment_date = start_date + pd.DateOffset(months = month)
        monthly_dates.append(payment_date)
        #x_months.append(month)
        remaining_balances.append(max(round(current_balance, 2), 0.0))

    df_monthly = pd.DataFrame({"Date": monthly_dates, "Standard_Monthly": remaining_balances})


    #Biweekly
    biweekly_rate = (interest / 100) / 26
    biweekly_months_count = 26 * months / 12
    biweekly_payment = amount * (biweekly_rate * (1 + biweekly_rate) ** biweekly_months_count) / ((1 + biweekly_rate) ** biweekly_months_count - 1)

    total_biweekly_interest = 0
    #biweekly_weeks = [0]
    biweekly_dates = [start_date]
    biweekly_balances = [round(amount, 2)]
    current_balance = amount
    biweekly_period = 0

    while round(current_balance, 2) > 0:
        biweekly_period += 1
        interest_this_period = current_balance * biweekly_rate
        total_biweekly_interest += interest_this_period
        principal = biweekly_payment - interest_this_period

        if current_balance < principal:
            principal = current_balance

        current_balance -= principal
        #m = biweekly_period * (12 / 26)

        payment_date = start_date + pd.Timedelta(weeks = biweekly_period * 2)
        biweekly_dates.append(payment_date)
        #biweekly_weeks.append(m)
        biweekly_balances.append(max(round(current_balance, 2), 0.0))

    df_biweekly = pd.DataFrame({'Date': biweekly_dates, 'Biweekly':biweekly_balances})


    #Monthly Rounded Up
    pmt_round = math.ceil(pmt / 10) * 10
    total_monthly_interest_round = 0
    current_balance = amount
    monthly_period_round = 0
    additional_payment_monthly = 0
    #x_months_round = [0]
    monthly_round_dates = [start_date]
    remaining_balances_round = [round(amount, 2)]

    while round(current_balance, 2) > 0:
        monthly_period_round += 1
        interest_this_month = current_balance * monthly_rate
        total_monthly_interest_round += interest_this_month

        if (current_balance + interest_this_month) < pmt_round:
            additional_payment_monthly = (current_balance + interest_this_month)
            current_balance = 0
        else:
            principal_this_month = pmt_round - interest_this_month
            current_balance -= principal_this_month

        payment_date = start_date + pd.DateOffset(months = monthly_period_round)
        monthly_round_dates.append(payment_date)
        #x_months_round.append(monthly_period_round)
        remaining_balances_round.append(max(round(current_balance, 2), 0.0))

    df_monthly_round = pd.DataFrame({'Date': monthly_round_dates, 'Monthly_Rounded':remaining_balances_round})


    #Biweekly Rounded
    biweekly_payment_round = math.ceil(biweekly_payment / 10) * 10
    total_biweekly_interest_round = 0
    current_balance = amount
    biweekly_period_round = 0
    additional_payment_biweekly = 0
    biweekly_round_dates = [start_date]
    #biweekly_weeks_round = [0]
    biweekly_balances_round = [round(amount, 2)]

    while round(current_balance, 2) > 0:
        biweekly_period_round += 1
        interest_this_period = current_balance * biweekly_rate
        total_biweekly_interest_round += interest_this_period

        if (current_balance + interest_this_period) < biweekly_payment_round:
            additional_payment_biweekly = (current_balance + interest_this_period)
            current_balance = 0
        else:
            principal = biweekly_payment_round - interest_this_period
            current_balance -= principal

        #m = biweekly_period_round * (12 / 26)
        #biweekly_weeks_round.append(m)
        payment_date = start_date + pd.Timedelta(weeks = biweekly_period_round*2)
        biweekly_round_dates.append(payment_date)
        biweekly_balances_round.append(max(round(current_balance, 2), 0.0))

    df_biweekly_round = pd.DataFrame({'Date':biweekly_round_dates,'Biweekly_Rounded':biweekly_balances_round})

    df_final = df_monthly.merge(df_monthly_round, on='Date', how='outer')
    df_final = df_final.merge(df_biweekly, on = 'Date', how = 'outer')
    df_final = df_final.merge(df_biweekly_round, on = 'Date', how = 'outer')

    df_final = df_final.sort_values('Date').reset_index(drop=True)
    #df_final[['Standard_Monthly', 'Monthly_Rounded', 'Biweekly', 'Biweekly_Rounded']] = \
    #    df_final[['Standard_Monthly', 'Monthly_Rounded', 'Biweekly', 'Biweekly_Rounded']].ffill()


    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_final['Date'],
        y=df_final['Standard_Monthly'],
        mode='lines+markers',
        connectgaps=True,
        name='Standard Monthly'
    ))

    fig.add_trace(go.Scatter(
        x=df_final['Date'],
        y=df_final['Biweekly'],
        mode='lines+markers',
        connectgaps=True,
        name='Standard Biweekly'
    ))

    fig.add_trace(go.Scatter(
        x=df_final['Date'],
        y=df_final['Monthly_Rounded'],
        mode='lines+markers',
        connectgaps=True,
        name='Monthly Rounded'
    ))

    fig.add_trace(go.Scatter(
        x=df_final['Date'],
        y=df_final['Biweekly_Rounded'],
        mode='lines+markers',
        connectgaps=True,
        name='Biweekly Rounded'
    ))

    fig.update_layout(
        title="Loan Amount over Time",
        xaxis_title="Timeline (Date)",
        yaxis_title="Amount ($)"
    )

    stats = {
        "pmt": pmt, "total_monthly_interest": total_monthly_interest, "months": months,
        "biweekly_payment": biweekly_payment, "total_biweekly_interest": total_biweekly_interest, "biweekly_period": biweekly_period,
        "pmt_round": pmt_round, "total_monthly_interest_round": total_monthly_interest_round, "monthly_period_round": monthly_period_round, "additional_payment_monthly": additional_payment_monthly,
        "biweekly_payment_round": biweekly_payment_round, "total_biweekly_interest_round": total_biweekly_interest_round, "biweekly_period_round": biweekly_period_round, "additional_payment_biweekly": additional_payment_biweekly
    }

    return fig, stats, df_final

st.set_page_config(layout="wide")
st.title("Loan & Amortization Calculator")

# Sidebar for user inputs
st.sidebar.header("Loan Parameters")
input_amount = st.sidebar.number_input("Loan Amount ($)", min_value=1000.0,  value=12000.0, step=5000.0)
input_interest = st.sidebar.number_input("Interest Rate (%)", min_value=0.1, max_value=100.0, value=2.0, step=0.1)
input_months = st.sidebar.slider("Loan Term (Months)", min_value=12, max_value = 600, value=60, step=12)
input_start = st.sidebar.date_input("Start Date", date.today())

# Run the calculation function using the sidebar inputs
fig, stats, df_final = pmt_graph(input_amount, input_interest, input_months, input_start)

# Display the interactive Plotly graph
st.plotly_chart(fig, width='stretch')

# Display calculated statistics in neat columns
st.subheader("Payment Comparison Summary")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Standard Schedule")
    st.markdown(f"**Standard Monthly Payment:** ${stats['pmt']:.2f}")
    st.markdown(f"**Total Monthly Interest:** ${stats['total_monthly_interest']:.2f}")
    st.markdown(f"**Total Monthly Payments:** {stats['months']}")
    st.write("---")
    st.markdown(f"**Standard Biweekly Payment:** ${stats['biweekly_payment']:.2f}")
    st.markdown(f"**Total Biweekly Interest:** ${stats['total_biweekly_interest']:.2f}")
    st.markdown(f"**Total Biweekly Payments:** {stats['biweekly_period']}")

with col2:
    st.markdown("### Rounded Up Schedule (To nearest $10)")
    st.markdown(f"**Rounded Monthly Payment:** ${stats['pmt_round']:.2f}")
    st.markdown(f"**Total Rounded Monthly Interest:** ${stats['total_monthly_interest_round']:.2f}")
    st.markdown(f"**Total Rounded Monthly Payments:** {stats['monthly_period_round']} ({stats['monthly_period_round']} months)")
    st.markdown(f"**Final Patch Payment:** ${stats['additional_payment_monthly']:.2f}")
    st.write("---")
    st.markdown(f"**Rounded Biweekly Payment:** ${stats['biweekly_payment_round']:.2f}")
    st.markdown(f"**Total Rounded Biweekly Interest:** ${stats['total_biweekly_interest_round']:.2f}")
    st.markdown(f"**Total Rounded Biweekly Payments:** {stats['biweekly_period_round']} ({stats['biweekly_period_round'] * (12/26):.2f} months)")
    st.markdown(f"**Final Patch Payment:** ${stats['additional_payment_biweekly']:.2f}")

# Expander to see raw data
with st.expander("View Raw Amortization Data Matrix"):
    st.dataframe(df_final)
