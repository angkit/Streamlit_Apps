import streamlit as st
import math
import yfinance as yf
import datetime

st.set_page_config(page_title="TMF to ETF Call Converter", layout="centered")
st.title("🔁 TMF Exposure via ETF Call Options")

# --- Fetch TMF price first so it's available for ETF value sliders ---
tmf = yf.Ticker("TMF")
try:
    tmf_price = tmf.history(period="1d")['Close'].iloc[-1]
except:
    st.error("Failed to fetch TMF price. Try again later.")
    st.stop()

# --- Input: TMF holdings ---
tmf_shares = st.number_input("📊 How many TMF shares do you hold?", min_value=1, value=7270, step=10)

# --- Input: Dynamic ETF tickers, values, and multiples ---
st.markdown("---")
with st.expander("📋 Enter Your Existing ETF Holdings (can add multiple)", expanded=False):
    st.subheader("📋 Enter Your Existing ETF Holdings (can add multiple)")

    def get_default_ticker(i):
        return "TLT" if i == 0 else ("EDV" if i == 1 else "")

    def get_default_multiple(ticker):
        if ticker == "TLT":
            return 2.2
        elif ticker == "EDV":
            return 1.5
        else:
            return 1.3

    num_etfs = st.number_input("How many different ETF tickers do you own?", min_value=1, value=2, step=1)
    etf_tickers = []
    etf_values = []
    etf_prices = []
    etf_multiples = []

    for i in range(int(num_etfs)):
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            default_ticker = get_default_ticker(i)
            ticker = st.text_input(f"ETF ticker #{i+1}", value=default_ticker, key=f"etf_ticker_{i}").upper()
        with col2:
            value = st.slider(
                f"Total current value of {ticker} ($)",
                min_value=0,
                max_value=int(tmf_shares * tmf_price),
                value=0,
                step=100,
                format="%d",
                key=f"etf_value_{i}"
            )
        with col3:
            default_multiple = get_default_multiple(ticker)
            multiple = st.number_input(f"Multiple for {ticker} (vs TMF)", min_value=0.1, value=default_multiple, step=0.1, format="%.2f", key=f"etf_multiple_{i}")
        etf_tickers.append(ticker)
        etf_values.append(value)
        etf_multiples.append(multiple)

    for ticker in etf_tickers:
        try:
            price = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
        except:
            price = 0.0
        etf_prices.append(price)

# --- Calculate exposures and show table ---
tmf_exposure = tmf_shares * tmf_price

data = []
for ticker, value, price, multiple in zip(etf_tickers, etf_values, etf_prices, etf_multiples):
    shares = int(round(value / price)) if price > 0 else 0
    exposure = shares * price
    target_exposure = tmf_exposure * multiple
    net_needed_exposure = target_exposure - exposure
    data.append({
        'ETF': ticker,
        'Shares': shares,
        'Current Value': value,
        'Current Exposure': exposure,
        'Net Exposure Needed': net_needed_exposure,
        'Multiple': multiple,
        'Price': price,
        'Target Exposure': target_exposure
    })

import pandas as pd
exposure_df = pd.DataFrame(data)
# Remove the ETF Exposure Table section
# (Do not show exposure_df or its header/markdown)

# --- User selects which ETF to use for call options ---
# (rest of the code continues as before, using net_needed_exposure for the selected ETF)

# --- Option chain selection for remaining exposure ---
st.markdown("---")
st.subheader("🧩 Select ETF Call Options for Comparison")

# Add a 'multiple' input
multiple = st.number_input(
    'Multiple (ETF 2 compared to ETF 1):',
    min_value=0.01, value=1.3, step=0.01, format="%.2f"
)

col_left, col_gap, col_right = st.columns([3, 1, 3])

with col_left:
    st.markdown("**Left: Select Call for ETF 1**")
    option_etf1 = st.selectbox("Choose ETF 1 for call option", etf_tickers, key="option_etf1")
    option_etf1_price = etf_prices[etf_tickers.index(option_etf1)]
    percent_slider1 = st.slider(
        f"Select ±% from current price for {option_etf1} (to visualize target strike):",
        min_value=-75.0, max_value=75.0, value=-10.0, step=0.1, format="%.2f",
        key="slider1"
    )
    target_price1 = option_etf1_price * (1 + percent_slider1 / 100)
    st.info(f"Target price: ${target_price1:.2f}")
    entry_mode1_default = 1 if option_etf1 == "TLT" else 0
    entry_mode1 = st.radio("Choose entry mode for ETF 1:", ["Automatic (yfinance data)", "Manual entry"], key="entry_mode1", index=entry_mode1_default)

with col_right:
    st.markdown("**Right: Select Call for ETF 2**")
    option_etf2 = st.selectbox("Choose ETF 2 for call option", etf_tickers, key="option_etf2", index=etf_tickers.index("EDV") if "EDV" in etf_tickers else 0)
    option_etf2_price = etf_prices[etf_tickers.index(option_etf2)]
    percent_slider2_val = percent_slider1 * multiple
    percent_slider2_val = max(-75.0, min(75.0, percent_slider2_val))
    percent_slider2 = st.slider(
        f"Select ±% from current price for {option_etf2} (auto-adjusted by multiple):",
        min_value=-75.0, max_value=75.0, value=percent_slider2_val, step=0.1, format="%.2f",
        key="slider2",
        disabled=True
    )
    target_price2 = option_etf2_price * (1 + percent_slider2 / 100)
    st.info(f"Target price: ${target_price2:.2f}")
    entry_mode2 = st.radio("Choose entry mode for ETF 2:", ["Automatic (yfinance data)", "Manual entry"], key="entry_mode2", index=1)

# Helper to get call details (automatic/manual)
def get_call_details(option_etf, option_etf_price, entry_mode, slider_key, call_key, expiry_key, target_price):
    import math
    import datetime
    if entry_mode == "Automatic (yfinance data)":
        option_etf_ticker = yf.Ticker(option_etf)
        expirations = option_etf_ticker.options
        if not expirations:
            st.error(f"No options data found for {option_etf}.")
            st.stop()
        # For sell call section, select default expiry at least 30 days out
        today = datetime.date.today()
        default_expiry_idx = 0
        for i, exp in enumerate(expirations):
            try:
                exp_date = datetime.datetime.strptime(exp, "%Y-%m-%d").date()
                if (exp_date - today).days >= 30:
                    default_expiry_idx = i
                    break
            except Exception:
                continue
        expiry = st.selectbox(f"Choose Expiration Date for {option_etf}", expirations, key=expiry_key, index=default_expiry_idx)
        opt_chain = option_etf_ticker.option_chain(expiry)
        calls = opt_chain.calls
        if calls.empty:
            st.error(f"No call options found for {option_etf} on {expiry}.")
            st.stop()
        calls_display = calls.copy()
        calls_display["Display"] = calls_display.apply(
            lambda r: f"Strike: ${r['strike']:.2f} | Bid: ${r['bid']:.2f} | Ask: ${r['ask']:.2f} | Volume: {r['volume']} | OI: {r['openInterest']}",
            axis=1
        )
        # No default selection
        selected_call_index = st.selectbox(
            f"Choose {option_etf} Call Contract (showing all {len(calls_display)} available):",
            range(len(calls_display)),
            format_func=lambda x: calls_display.iloc[x]["Display"],
            key=call_key,
            index=None  # No default
        )
        if selected_call_index is not None:
            selected_call = calls.iloc[selected_call_index]
            strike = selected_call.strike
            premium = selected_call.bid
            delta = getattr(selected_call, "delta", None)
            if delta is None or math.isnan(delta):
                delta = st.number_input(f"⚠️ Delta not available for {option_etf}. Enter manually:", min_value=0.1, max_value=1.0, value=0.9, key=f"delta_{call_key}")
                st.warning("Delta not found in data, please enter it manually.")
            return strike, premium, delta
        else:
            return None, None, None
    else:
        col1, col2 = st.columns(2)
        with col1:
            # Set manual defaults for TLT and EDV
            if option_etf == "TLT":
                manual_strike_default = 70.0
                manual_bid_default = 16.45
            elif option_etf == "EDV":
                manual_strike_default = 56.0
                manual_bid_default = 8.7
            else:
                manual_strike_default = None
                manual_bid_default = None
            manual_strike = st.number_input(
                f"Strike Price ($) for {option_etf}:",
                min_value=0.01,
                value=manual_strike_default,
                step=0.01,
                format="%.2f",
                key=f"strike_{call_key}"
            )
            manual_bid = st.number_input(f"Bid Price ($) for {option_etf}:", min_value=0.0, value=manual_bid_default, step=0.01, format="%.2f", key=f"bid_{call_key}")
        with col2:
            manual_delta = st.number_input(f"Delta for {option_etf}:", min_value=0.1, max_value=1.0, value=0.9, step=0.01, format="%.2f", key=f"delta_{call_key}")
        return manual_strike, manual_bid, manual_delta

# Get call details for both ETFs
with col_left:
    strike1, bid1, delta1 = get_call_details(option_etf1, option_etf1_price, entry_mode1, "slider1", "call1", "expiry1", target_price1)
with col_right:
    strike2, bid2, delta2 = get_call_details(option_etf2, option_etf2_price, entry_mode2, "slider2", "call2", "expiry2", target_price2)

# Calculate per-contract exposure and contracts needed for both
contract_exposure1 = delta1 * 100 * option_etf1_price if delta1 is not None else 0
contract_exposure2 = delta2 * 100 * option_etf2_price if delta2 is not None else 0
contracts_needed1 = net_needed_exposure / contract_exposure1 if contract_exposure1 else 0
contracts_needed2 = net_needed_exposure / contract_exposure2 if contract_exposure2 else 0
contracts_needed_rounded1 = contracts_needed1
contracts_needed_rounded2 = contracts_needed2
total_premium_cost1 = contracts_needed_rounded1 * bid1 * 100 if bid1 is not None else 0
total_premium_cost2 = contracts_needed_rounded2 * bid2 * 100 if bid2 is not None else 0

st.markdown("---")
st.subheader("📉 Sell Calls (TLT & EDV)")
col_sell_left, col_sell_gap, col_sell_right = st.columns([3, 1, 3])

# Dividend yield user input
col_div1, col_div2 = st.columns(2)
with col_div1:
    tlt_yield = st.number_input("TLT Dividend Yield (%)", min_value=0.0, max_value=20.0, value=3.9, step=0.01, format="%.2f", key="tlt_div_yield")
with col_div2:
    edv_yield = st.number_input("EDV Dividend Yield (%)", min_value=0.0, max_value=20.0, value=4.9, step=0.01, format="%.2f", key="edv_div_yield")
yield_dict = {'TLT': tlt_yield, 'EDV': edv_yield}

# User input for multiple
st.markdown("**Strike Offset Multiple (EDV vs TLT):**")
strike_multiple = st.number_input("Multiple (EDV offset = TLT offset × multiple)", min_value=0.01, value=1.3, step=0.01, format="%.2f", key="sell_strike_multiple")

percent_min = -50.0
percent_max = 50.0
percent_default = 5.0

with col_sell_left:
    st.markdown("**TLT Call to Sell**")
    tlt_price = etf_prices[etf_tickers.index('TLT')] if 'TLT' in etf_tickers else 0
    tlt_offset = st.slider(
        f"Select TLT strike as % from current price:",
        min_value=percent_min,
        max_value=percent_max,
        value=percent_default,
        step=0.1,
        format="%.1f%%",
        key="sell_strike_percent_TLT"
    )
    # --- TLT Sell Call Option Selection ---
    if 'TLT' in etf_tickers:
        option_etf_ticker = yf.Ticker('TLT')
        expirations = option_etf_ticker.options
        if expirations:
            today = datetime.date.today()
            default_expiry_idx = 0
            for i, exp in enumerate(expirations):
                try:
                    exp_date = datetime.datetime.strptime(exp, "%Y-%m-%d").date()
                    if (exp_date - today).days >= 30:
                        default_expiry_idx = i
                        break
                except Exception:
                    continue
            expiry = st.selectbox(f"Choose Expiration Date for TLT (Sell)", expirations, key="sell_expiry_TLT", index=default_expiry_idx)
            opt_chain = option_etf_ticker.option_chain(expiry)
            calls = opt_chain.calls
            if not calls.empty:
                target_strike = tlt_price * (1 + tlt_offset / 100)
                closest_idx = (calls['strike'] - target_strike).abs().idxmin()
                selected_call = calls.loc[closest_idx]
                st.info(f"Strike: ${selected_call['strike']:.2f} | Bid: ${selected_call['bid']:.2f} | Ask: ${selected_call['ask']:.2f} | Volume: {selected_call['volume']} | OI: {selected_call['openInterest']}")

with col_sell_right:
    st.markdown("**EDV Call to Sell**")
    edv_price = etf_prices[etf_tickers.index('EDV')] if 'EDV' in etf_tickers else 0
    edv_offset = tlt_offset * strike_multiple
    edv_offset = max(percent_min, min(percent_max, edv_offset))
    st.markdown(f"EDV strike offset: {edv_offset:.2f}% (auto-calculated)")
    # --- EDV Sell Call Option Selection ---
    if 'EDV' in etf_tickers:
        option_etf_ticker = yf.Ticker('EDV')
        expirations = option_etf_ticker.options
        if expirations:
            today = datetime.date.today()
            default_expiry_idx = 0
            for i, exp in enumerate(expirations):
                try:
                    exp_date = datetime.datetime.strptime(exp, "%Y-%m-%d").date()
                    if (exp_date - today).days >= 30:
                        default_expiry_idx = i
                        break
                except Exception:
                    continue
            expiry = st.selectbox(f"Choose Expiration Date for EDV (Sell)", expirations, key="sell_expiry_EDV", index=default_expiry_idx)
            opt_chain = option_etf_ticker.option_chain(expiry)
            calls = opt_chain.calls
            if not calls.empty:
                target_strike = edv_price * (1 + edv_offset / 100)
                closest_idx = (calls['strike'] - target_strike).abs().idxmin()
                selected_call = calls.loc[closest_idx]
                st.info(f"Strike: ${selected_call['strike']:.2f} | Bid: ${selected_call['bid']:.2f} | Ask: ${selected_call['ask']:.2f} | Volume: {selected_call['volume']} | OI: {selected_call['openInterest']}")



# Show comparison table
import pandas as pd
comparison_df = pd.DataFrame({
    'ETF': [option_etf1, option_etf2],
    # 'Strike': [strike1, strike2],
    # 'Bid Premium': [bid1, bid2],
    # 'Delta': [delta1, delta2],
    'Per-Contract Exposure': [contract_exposure1, contract_exposure2],
    'Contracts Needed': [contracts_needed_rounded1, contracts_needed_rounded2],
    'Total Premium Cost': [total_premium_cost1, total_premium_cost2]
})

# Merge ETF exposure and comparison table, drop 'Multiple', 'Strike', 'Bid Premium', 'Delta', 'Price', 'Target Exposure' if present
merged_df = pd.merge(
    exposure_df,
    comparison_df,
    on='ETF',
    how='inner'
)
# Rename 'Exposure' to 'Current Exposure'
if 'Exposure' in merged_df.columns:
    merged_df = merged_df.rename(columns={'Exposure': 'Current Exposure'})
# Remove unwanted columns except 'Net Exposure Needed' and 'Per-Contract Exposure'
for col in ['Multiple', 'Strike', 'Bid Premium', 'Delta', 'Price', 'Target Exposure']:
    if col in merged_df.columns:
        merged_df = merged_df.drop(columns=[col])
# Add 'Total Exposure' column
merged_df['Total Exposure'] = merged_df['Current Exposure'] + merged_df['Total Premium Cost']

# Move 'Current Exposure' just before 'Total Premium Cost' in the final table
cols = list(merged_df.columns)
if 'Current Exposure' in cols and 'Total Premium Cost' in cols:
    cols.remove('Current Exposure')
    idx = cols.index('Total Premium Cost')
    cols.insert(idx, 'Current Exposure')
    merged_df = merged_df[cols]

# Round up 'Contracts Needed' and format all cost/exposure columns as integer dollar values
import numpy as np
if 'Contracts Needed' in merged_df.columns:
    merged_df['Contracts Needed'] = np.ceil(merged_df['Contracts Needed']).astype(int)
for col in ['Current Exposure', 'Net Exposure Needed', 'Total Premium Cost', 'Total Exposure', 'Per-Contract Exposure']:
    if col in merged_df.columns:
        merged_df[col] = merged_df[col].apply(lambda x: f"${int(round(x)):,}")

# --- Safe Short Call Contracts Section ---
st.markdown("---")
with st.expander("🛡️ Safe Short Call Contracts to Sell", expanded=False):
    st.subheader("🛡️ Safe Short Call Contracts to Sell")

    # Show safe short calls for each selected ETF
    for etf_idx, (etf, strike, bid, current_price) in enumerate([(option_etf1, strike1, bid1, option_etf1_price), (option_etf2, strike2, bid2, option_etf2_price)]):
        if strike is not None and bid is not None:
            st.markdown(f"### {etf} Safe Short Call Analysis")
            
            # Get available expirations for short calls
            try:
                etf_ticker = yf.Ticker(etf)
                expirations = etf_ticker.options
                if expirations:
                    # Select expiry for short calls (default to first available)
                    short_expiry = st.selectbox(
                        f"Select expiry for {etf} short calls:",
                        options=expirations,
                        key=f"short_expiry_{etf}",
                        index=0
                    )
                    
                    if short_expiry:
                        # Get option chain for selected expiry
                        opt_chain = etf_ticker.option_chain(short_expiry)
                        calls = opt_chain.calls.copy()
                        
                        if not calls.empty:
                            # Calculate DTE
                            dte = (datetime.datetime.strptime(short_expiry, "%Y-%m-%d") - datetime.datetime.today()).days
                            calls['dte'] = dte
                            
                            # Calculate safe price for each call option
                            calls['safe_price'] = strike + bid - calls['bid']
                            
                            # Calculate margin for each call option
                            calls['margin'] = calls['strike'] - calls['safe_price']
                            
                            # Filter for safe calls (safe_price > 0 and margin > 0)
                            safe_calls = calls[(calls['safe_price'] > 0) & (calls['margin'] > 0)].copy()
                            
                            if not safe_calls.empty:
                                # Sort by margin (ascending)
                                safe_calls = safe_calls.sort_values('margin', ascending=True)
                                
                                # Display safe calls table
                                st.markdown(f"#### Safe Short Calls for {etf} ({dte} DTE)")
                                st.info(f"**Safe Price Formula:** Strike (${strike:.2f}) + Premium Paid (${bid:.2f}) - Premium Received from Short Call")
                                display_cols = ['strike', 'bid', 'ask', 'safe_price', 'margin']
                                available_cols = [col for col in display_cols if col in safe_calls.columns]
                                st.dataframe(
                                    safe_calls[available_cols],
                                    use_container_width=True
                                )
                            else:
                                st.warning(f"No safe short call options found for {etf} on {short_expiry}. All options would result in negative margins.")
                        else:
                            st.warning(f"No call options available for {etf} on {short_expiry}")
                    else:
                        st.info(f"Please select an expiry for {etf} short calls")
                else:
                    st.warning(f"No option expirations available for {etf}")
            except Exception as e:
                st.error(f"Error loading options for {etf}: {e}")

st.markdown("---")
with st.expander("📊 Final Combined Table", expanded=False):
    st.subheader("📊 Final Combined Table")
    st.dataframe(merged_df, hide_index=True, use_container_width=True)

# --- New: Multiple Strategy Capital Allocation and Contract Summary for TLT and EDV ---
if set(['TLT', 'EDV']).issubset(set(etf_tickers)):
    st.markdown("---")
    st.subheader("📊 Multiple Strategy Capital Allocation (TLT & EDV)")
    total_capital = tmf_shares * tmf_price
    
    # Strategy management
    num_strategies = st.number_input("Number of strategies to compare:", min_value=1, max_value=5, value=2, step=1)
    
    all_strategies_data = []
    
    for strategy_num in range(int(num_strategies)):
        st.markdown(f"---")
        st.markdown(f"**Strategy {strategy_num + 1}**")
        
        # Create flexible capital allocation inputs for this strategy
        col_alloc1, col_alloc2 = st.columns(2)
        
        with col_alloc1:
            st.markdown("**TLT Allocation**")
            tlt_shares_pct = st.number_input(
                f"TLT Shares (%) - Strategy {strategy_num + 1}",
                min_value=0.0,
                max_value=100.0,
                value=0.0 if strategy_num == 0 else 50.0,
                step=1.0,
                format="%.0f",
                key=f"tlt_shares_pct_{strategy_num}"
            )
            tlt_calls_pct = st.number_input(
                f"TLT Calls (%) - Strategy {strategy_num + 1}",
                min_value=0.0,
                max_value=100.0,
                value=50.0 if strategy_num == 0 else 0.0,
                step=1.0,
                format="%.0f",
                key=f"tlt_calls_pct_{strategy_num}"
            )
        
        with col_alloc2:
            st.markdown("**EDV Allocation**")
            edv_shares_pct = st.number_input(
                f"EDV Shares (%) - Strategy {strategy_num + 1}",
                min_value=0.0,
                max_value=100.0,
                value=50.0 if strategy_num == 0 else 0.0,
                step=1.0,
                format="%.0f",
                key=f"edv_shares_pct_{strategy_num}"
            )
            edv_calls_pct = st.number_input(
                f"EDV Calls (%) - Strategy {strategy_num + 1}",
                min_value=0.0,
                max_value=100.0,
                value=0.0 if strategy_num == 0 else 50.0,
                step=1.0,
                format="%.0f",
                key=f"edv_calls_pct_{strategy_num}"
            )
        
        # Calculate total allocated percentage for this strategy
        total_allocated = tlt_shares_pct + tlt_calls_pct + edv_shares_pct + edv_calls_pct
        remaining_pct = 100.0 - total_allocated
        
        if total_allocated > 100.0:
            st.error(f"⚠️ Strategy {strategy_num + 1}: Total allocation exceeds 100% ({total_allocated:.1f}%). Please reduce allocations.")
        else:
            st.info(f"📊 Strategy {strategy_num + 1}: Total allocated: {total_allocated:.1f}% | Remaining: {remaining_pct:.1f}%")
        
        # Get TMF Equivalent for TLT and EDV from merged_df
        tmf_equiv_dict = dict(zip(merged_df['ETF'], merged_df['Net Exposure Needed'])) if 'Net Exposure Needed' in merged_df.columns else {}
        strategy_data = []
        
        for etf in ['TLT', 'EDV']:
            price = 0.0
            if etf in etf_tickers:
                idx = etf_tickers.index(etf)
                price = etf_prices[idx]
            
            # Get allocation percentages for this ETF in this strategy
            if etf == 'TLT':
                shares_pct = tlt_shares_pct
                calls_pct = tlt_calls_pct
            else:  # EDV
                shares_pct = edv_shares_pct
                calls_pct = edv_calls_pct
            
            # Calculate capital amounts
            capital_for_shares = total_capital * (shares_pct / 100)
            capital_for_calls = total_capital * (calls_pct / 100)
            
            # Calculate shares and contracts
            shares_bought = int(capital_for_shares // price) if price > 0 else 0
            
            # Use the selected call contract from the call options section
            if etf == option_etf1:
                contract_cost = bid1 * 100 if bid1 is not None else 0
                contracts_bought = int(capital_for_calls // contract_cost) if contract_cost > 0 else 0
            elif etf == option_etf2:
                contract_cost = bid2 * 100 if bid2 is not None else 0
                contracts_bought = int(capital_for_calls // contract_cost) if contract_cost > 0 else 0
            else:
                contract_cost = 0.0
                contracts_bought = 0
            
            contracts_on_shares = shares_bought // 100
            total_contracts = contracts_bought + contracts_on_shares
            total_capital_controlled = total_contracts * 100 * price
            tmf_equiv = tmf_equiv_dict.get(etf, "-")
            
            # Calculate TLT Equivalent Capital
            if etf == 'TLT':
                tlt_equivalent_capital = total_capital_controlled
            elif etf == 'EDV':
                tlt_equivalent_capital = total_capital_controlled * 1.3
            else:
                tlt_equivalent_capital = total_capital_controlled
            
            strategy_data.append({
                'Strategy': f"Strategy {strategy_num + 1}",
                'ETF': etf,
                'Shares Allocation (%)': f"{shares_pct:.0f}%",
                'Calls Allocation (%)': f"{calls_pct:.0f}%",
                'Capital for Shares': f"${int(round(capital_for_shares)):,}",
                'Shares Bought': shares_bought,
                'Capital for Calls': f"${int(round(capital_for_calls)):,}",
                'Contracts Bought': contracts_bought,
                'Contracts on Shares': contracts_on_shares,
                'Total Contracts': total_contracts,
                'Total Capital Controlled': f"${int(round(total_capital_controlled)):,}",
                'TLT Equivalent Capital': f"${int(round(tlt_equivalent_capital)):,}"
            })
        
        all_strategies_data.extend(strategy_data)
    
    # Create combined summary table for all strategies
    if all_strategies_data:
        summary_df = pd.DataFrame(all_strategies_data)
        
        # Strategy comparison summary
        strategy_summary = []
        for strategy_num in range(int(num_strategies)):
            strategy_data = [row for row in all_strategies_data if row['Strategy'] == f"Strategy {strategy_num + 1}"]
            
            total_capital_used = 0
            total_contracts = 0
            total_shares = 0
            total_capital_controlled = 0
            total_tlt_equivalent_capital = 0
            
            for row in strategy_data:
                # Extract numeric values from formatted strings
                capital_shares = int(row['Capital for Shares'].replace('$', '').replace(',', ''))
                capital_calls = int(row['Capital for Calls'].replace('$', '').replace(',', ''))
                total_capital_used += capital_shares + capital_calls
                total_contracts += row['Total Contracts']
                total_shares += row['Shares Bought']
                
                # Get total capital controlled from the row
                total_capital_controlled_str = row['Total Capital Controlled']
                total_capital_controlled += int(total_capital_controlled_str.replace('$', '').replace(',', ''))
                
                # Get TLT equivalent capital from the row
                tlt_equivalent_capital_str = row['TLT Equivalent Capital']
                total_tlt_equivalent_capital += int(tlt_equivalent_capital_str.replace('$', '').replace(',', ''))
            
            strategy_summary.append({
                'Strategy': f"Strategy {strategy_num + 1}",
                'Total Contracts': total_contracts,
                'Total Shares': total_shares,
                'Total Capital Used': f"${total_capital_used:,}",
                'Total Capital Controlled': f"${total_capital_controlled:,}",
                'Total TLT Equivalent Capital': f"${total_tlt_equivalent_capital:,}"
            })
        
        summary_comparison_df = pd.DataFrame(strategy_summary)

# --- Sell Calls Section for TLT and EDV (side-by-side) ---


# --- User Input: Projected Upside and Time Horizon ---
st.markdown("---")
col_upside, col_time = st.columns(2)
with col_upside:
    projected_upside_pct = st.number_input(
        "🔼 Expected Upside (%)",
        min_value=-500.0,  # Allow negative values
        max_value=500.0,
        value=10.0,
        step=0.5,
        format="%.2f"
    )
with col_time:
    projected_months = st.number_input(
        "⏳ Time Horizon (months)",
        min_value=1, max_value=60, value=12, step=1
    )

# --- Calculate Button ---
st.markdown("---")
calculate_button = st.button("🚀 **START ANALYSIS**", type="primary", use_container_width=True)

# --- Results Section (Full Width) ---
if calculate_button:
    st.markdown("---")
    st.markdown("## 📊 Analysis Results")
    
    # --- Strategy Comparison Tables (Hidden by default) ---
    if all_strategies_data:
        with st.expander("📊 Combined Strategy Comparison", expanded=False):
            st.dataframe(summary_df, hide_index=True, use_container_width=True)
        
        with st.expander("📊 Strategy Summary Comparison", expanded=False):
            st.dataframe(summary_comparison_df, hide_index=True, use_container_width=True)

    # --- Sell Calls Premium Table (Hidden by default) ---
    if set(['TLT', 'EDV']).issubset(set(etf_tickers)):
        with st.expander("📊 Sell Calls Premium Table", expanded=False):
            # Calculate sell calls data for all strategies
            all_strategies_sell_data = []
            
            for strategy_num in range(int(num_strategies)):
                strategy_name = f"Strategy {strategy_num + 1}"
                strategy_data = [row for row in all_strategies_data if row['Strategy'] == strategy_name]
                
                # Get data for this strategy
                contracts_dict = {row['ETF']: row['Total Contracts'] for row in strategy_data}
                shares_dict = {row['ETF']: row['Shares Bought'] for row in strategy_data}
                
                # Calculate total capital used for this strategy
                strategy_capital_used = 0
                for row in strategy_data:
                    capital_shares = int(row['Capital for Shares'].replace('$', '').replace(',', ''))
                    capital_calls = int(row['Capital for Calls'].replace('$', '').replace(',', ''))
                    strategy_capital_used += capital_shares + capital_calls
                
                # Calculate sell calls for each ETF in this strategy
                for etf, price, offset in [('TLT', tlt_price, tlt_offset), ('EDV', edv_price, edv_offset)]:
                    if etf in etf_tickers:
                        option_etf_ticker = yf.Ticker(etf)
                        expirations = option_etf_ticker.options
                        if expirations:
                            # Use the same expiry that was selected in the left panel
                            expiry = st.session_state.get(f"sell_expiry_{etf}", expirations[0])
                            if expiry in expirations:
                                opt_chain = option_etf_ticker.option_chain(expiry)
                                calls = opt_chain.calls
                                if not calls.empty:
                                    target_strike = price * (1 + offset / 100)
                                    closest_idx = (calls['strike'] - target_strike).abs().idxmin()
                                    selected_call = calls.loc[closest_idx]
                                    bid = selected_call['bid']
                                    contracts_sold = contracts_dict.get(etf, 0)
                                    total_premium = contracts_sold * bid * 100
                                    annual_premium = total_premium * 12
                                    shares_held = shares_dict.get(etf, 0)
                                    div_yield = yield_dict[etf] / 100.0
                                    annual_dividend = shares_held * price * div_yield
                                    total_annual_income = annual_dividend + annual_premium
                                    monthly_total_income = total_annual_income / 12
                                    # Calculate return as percentage of strategy capital
                                    annual_return_pct = (total_annual_income / strategy_capital_used * 100) if strategy_capital_used > 0 else 0
                                    
                                    all_strategies_sell_data.append({
                                        'Strategy': strategy_name,
                                        'ETF': etf,
                                        'Strike Price': f"${selected_call['strike']:,.2f}",
                                        'Bid Premium': f"${bid:,.2f}",
                                        'Contracts Sold': contracts_sold,
                                        'Total Premium Collected': f"${int(round(total_premium)):,}",
                                        'Annual Premium': f"${int(round(annual_premium)):,}",
                                        'Annual Dividend Income': f"${int(round(annual_dividend)):,}",
                                        'Total Annual Income': f"${int(round(total_annual_income)):,}",
                                        'Monthly Total Income': f"${int(round(monthly_total_income)):,}",
                                        'Annual Return (%)': f"{annual_return_pct:.2f}%"
                                    })
            
            # Create comprehensive sell calls table for all strategies
            if all_strategies_sell_data:
                comprehensive_sell_df = pd.DataFrame(all_strategies_sell_data)
                st.dataframe(comprehensive_sell_df, hide_index=True, use_container_width=True)
                
                # Calculate and display summary for each strategy
                with st.expander("📊 Strategy Sell Calls Summary", expanded=False):
                    # Create summary data for table
                    summary_data = []
                
                    for strategy_num in range(int(num_strategies)):
                        strategy_name = f"Strategy {strategy_num + 1}"
                        strategy_sell_data = [row for row in all_strategies_sell_data if row['Strategy'] == strategy_name]
                        
                        if strategy_sell_data:
                            # Calculate total capital used for this strategy
                            strategy_data = [row for row in all_strategies_data if row['Strategy'] == strategy_name]
                            strategy_capital_used = 0
                            for row in strategy_data:
                                capital_shares = int(row['Capital for Shares'].replace('$', '').replace(',', ''))
                                capital_calls = int(row['Capital for Calls'].replace('$', '').replace(',', ''))
                                strategy_capital_used += capital_shares + capital_calls
                            
                            # Calculate combined strategy return
                            total_strategy_annual_income = sum([
                                int(row['Total Annual Income'].replace('$', '').replace(',', '')) 
                                for row in strategy_sell_data
                            ])
                            combined_strategy_return = (total_strategy_annual_income / strategy_capital_used * 100) if strategy_capital_used > 0 else 0
                            
                            # Calculate monthly income
                            monthly_income = total_strategy_annual_income / 12
                            
                            summary_data.append({
                                'Strategy': strategy_name,
                                'Annual Return (%)': f"{combined_strategy_return:.2f}%",
                                'Total Capital Used': f"${strategy_capital_used:,}",
                                'Total Annual Income': f"${total_strategy_annual_income:,}",
                                'Monthly Income': f"${int(round(monthly_income)):,}"
                            })
                    
                    # Display summary table
                    if summary_data:
                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(summary_df, hide_index=True, use_container_width=True)
                    else:
                        st.info("No sell calls data available for the configured strategies.")

        # --- Combined Summary Section ---
        if all_strategies_data:
            st.markdown("---")
            st.subheader("📊 Combined Strategy & Sell Calls Summary")
            
            # Create combined summary data
            combined_summary_data = []
            
            for strategy_num in range(int(num_strategies)):
                strategy_name = f"Strategy {strategy_num + 1}"
                
                # Get strategy summary data
                strategy_summary_row = None
                for row in strategy_summary:
                    if row['Strategy'] == strategy_name:
                        strategy_summary_row = row
                        break
                
                # Get sell calls summary data
                sell_calls_summary_row = None
                if 'summary_data' in locals():
                    for row in summary_data:
                        if row['Strategy'] == strategy_name:
                            sell_calls_summary_row = row
                            break
                
                # Calculate Current TLT (2.2x Total Capital Used)
                total_capital_used_str = strategy_summary_row['Total Capital Used'] if strategy_summary_row else '$0'
                total_capital_used_num = int(total_capital_used_str.replace('$', '').replace(',', '')) if total_capital_used_str else 0
                current_tlt = total_capital_used_num * 2.2
                current_tlt_str = f"${int(round(current_tlt)):,}"
                
                # Combine the data
                combined_row = {
                    'Strategy': strategy_name,
                    'Total Contracts': strategy_summary_row['Total Contracts'] if strategy_summary_row else 0,
                    'Total Shares': strategy_summary_row['Total Shares'] if strategy_summary_row else 0,
                    'Total Capital Used': total_capital_used_str,
                    'Total Capital Controlled': strategy_summary_row['Total Capital Controlled'] if strategy_summary_row else '$0',
                    'Total TLT Equivalent Capital': strategy_summary_row['Total TLT Equivalent Capital'] if strategy_summary_row else '$0',
                    'Current TLT': current_tlt_str,
                    'Annual Return (%)': sell_calls_summary_row['Annual Return (%)'] if sell_calls_summary_row else '0.00%',
                    'Total Annual Income': sell_calls_summary_row['Total Annual Income'] if sell_calls_summary_row else '$0',
                    'Monthly Income': sell_calls_summary_row['Monthly Income'] if sell_calls_summary_row else '$0'
                }
                
                combined_summary_data.append(combined_row)
            
            # Display combined summary table
            if combined_summary_data:
                combined_summary_df = pd.DataFrame(combined_summary_data)
                # Explicitly set column order to ensure 'Current TLT' is always visible
                column_order = [
                    'Strategy',
                    'Total Capital Used',
                    'Total Capital Controlled',
                    'Total TLT Equivalent Capital',
                    'Current TLT',
                    'Annual Return (%)',
                    'Total Annual Income',
                    'Monthly Income'
                ]
                # Only include columns that exist in the DataFrame (in case of missing data)
                column_order = [col for col in column_order if col in combined_summary_df.columns]
                combined_summary_df = combined_summary_df[column_order]
                st.dataframe(combined_summary_df, hide_index=True, use_container_width=True)
                
                # --- Projected Return Calculation ---
                contracts_shares_df = pd.DataFrame(combined_summary_data)[['Strategy', 'Total Contracts', 'Total Shares', 'Total Capital Used', 'Total TLT Equivalent Capital']]
                projected_returns = []
                for idx, row in contracts_shares_df.iterrows():
                    # Parse numbers from formatted strings
                    tlt_equiv_cap = int(str(row['Total TLT Equivalent Capital']).replace('$', '').replace(',', ''))
                    capital_used = int(str(row['Total Capital Used']).replace('$', '').replace(',', ''))
                    # Calculate projected return dollar amount
                    projected_return_dollar = tlt_equiv_cap * (projected_upside_pct / 100)
                    # Annualize the projected return percentage based on user-inputted months
                    if capital_used > 0 and projected_months > 0:
                        period_return_pct = projected_return_dollar / capital_used * 100
                        annualized_return_pct = ((1 + period_return_pct / 100) ** (12 / projected_months) - 1) * 100
                    else:
                        annualized_return_pct = 0
                    projected_returns.append({
                        'Projected Return ($)': f"${int(round(projected_return_dollar)):,}",
                        'Annualized Return (%)': f"{annualized_return_pct:.2f}%"
                    })
                projected_returns_df = pd.DataFrame(projected_returns)
                # Only show Strategy, Total Contracts, Total Shares, Total Capital Used, Total TLT Equivalent Capital, Projected Return ($), Annualized Return (%)
                display_cols = ['Strategy', 'Total Contracts', 'Total Shares', 'Total Capital Used', 'Total TLT Equivalent Capital', 'Projected Return ($)', 'Annualized Return (%)']
                contracts_shares_df = pd.concat([contracts_shares_df, projected_returns_df], axis=1)
                contracts_shares_df = contracts_shares_df[display_cols]
                st.markdown('#### Total Contracts and Shares by Strategy')
                st.dataframe(contracts_shares_df, hide_index=True, use_container_width=True)