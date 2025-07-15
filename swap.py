import pandas as pd
import datetime
import streamlit as st
import plotly.graph_objs as go
import os

def get_latest_date_from_csvs():
    """Get the most recent date from existing CSV files"""
    latest_date = None
    
    # Check SOFR CSV
    sofr_csv_file = 'sofr_treasury_spread_log.csv'
    if os.path.isfile(sofr_csv_file):
        try:
            df_sofr = pd.read_csv(sofr_csv_file, parse_dates=['Date'])
            if not df_sofr.empty:
                sofr_latest = df_sofr['Date'].max()
                if latest_date is None or sofr_latest > latest_date:
                    latest_date = sofr_latest
        except:
            pass
    
    # Check yield CSV
    yield_csv_file = 'thirtyy_spread_log.csv'
    if os.path.isfile(yield_csv_file):
        try:
            df_yield = pd.read_csv(yield_csv_file, parse_dates=['Date'])
            if not df_yield.empty:
                yield_latest = df_yield['Date'].max()
                if latest_date is None or yield_latest > latest_date:
                    latest_date = yield_latest
        except:
            pass
    

    
    # If no date found, use 2025-01-15 as default
    if latest_date is None:
        latest_date = pd.Timestamp('2025-01-15')
    
    return latest_date.date()

def update_csv_with_current_values(sofr, treasury, us_yield, germany_yield, japan_yield, fed_rate, ecb_rate, boj_rate):
    """Update both CSV files with current values, removing duplicates"""
    import datetime
    today = datetime.date.today()  # Use today's date
    
    # Update SOFR/Treasury CSV
    sofr_spread = sofr - treasury
    sofr_csv_file = 'sofr_treasury_spread_log.csv'
    
    # Load existing SOFR data if present
    if os.path.isfile(sofr_csv_file):
        df_sofr = pd.read_csv(sofr_csv_file, parse_dates=['Date'])
        # Remove any rows with today's date
        df_sofr = df_sofr[df_sofr['Date'].dt.date != today]
    else:
        df_sofr = pd.DataFrame(columns=['Date', 'SOFR_Swap', 'Treasury_Yield', 'Spread'])
    
    # Append new SOFR row for today
    new_sofr_row = pd.DataFrame([[pd.Timestamp(today), f'{sofr:.4f}', f'{treasury:.4f}', f'{sofr_spread:.4f}']], 
                                columns=['Date', 'SOFR_Swap', 'Treasury_Yield', 'Spread'])
    df_sofr = pd.concat([df_sofr, new_sofr_row], ignore_index=True)
    # Remove duplicate dates, keep the last
    df_sofr = df_sofr.drop_duplicates(subset=['Date'], keep='last')
    # Sort by date
    df_sofr = df_sofr.sort_values('Date')
    # Write back to CSV
    df_sofr.to_csv(sofr_csv_file, index=False)
    
    # Update Yield/Policy CSV
    us_spread = us_yield - fed_rate
    germany_spread = germany_yield - ecb_rate
    japan_spread = japan_yield - boj_rate
    yield_csv_file = 'thirtyy_spread_log.csv'
    
    # Load existing yield data if present
    if os.path.isfile(yield_csv_file):
        df_yield = pd.read_csv(yield_csv_file, parse_dates=['Date'])
        # Remove any rows with today's date
        df_yield = df_yield[df_yield['Date'].dt.date != today]
    else:
        df_yield = pd.DataFrame(columns=[
            'Date',
            'US_30Y_Yield', 'US_Policy', 'US_Spread',
            'Germany_30Y_Yield', 'Germany_Policy', 'Germany_Spread',
            'Japan_30Y_Yield', 'Japan_Policy', 'Japan_Spread'])
    
    # Append new yield row for today
    new_yield_row = pd.DataFrame([[pd.Timestamp(today), f'{us_yield:.4f}', f'{fed_rate:.4f}', f'{us_spread:.4f}',
                                   f'{germany_yield:.4f}', f'{ecb_rate:.4f}', f'{germany_spread:.4f}',
                                   f'{japan_yield:.4f}', f'{boj_rate:.4f}', f'{japan_spread:.4f}']],
                                 columns=[
                                     'Date',
                                     'US_30Y_Yield', 'US_Policy', 'US_Spread',
                                     'Germany_30Y_Yield', 'Germany_Policy', 'Germany_Spread',
                                     'Japan_30Y_Yield', 'Japan_Policy', 'Japan_Spread'])
    df_yield = pd.concat([df_yield, new_yield_row], ignore_index=True)
    # Remove duplicate dates, keep the last
    df_yield = df_yield.drop_duplicates(subset=['Date'], keep='last')
    # Sort by date
    df_yield = df_yield.sort_values('Date')
    # Write back to CSV
    df_yield.to_csv(yield_csv_file, index=False)

def main():
    st.set_page_config(page_title="Bond Yield & Swap Analysis", layout="wide")
    st.title("📈 Bond Yield & Swap Analysis")
    
    # Input section at the top
    st.subheader("Data Input")
    
    # Create two columns for inputs with gap
    col1, spacer, col2 = st.columns([1, 0.2, 1])
    
    with col1:
        st.markdown("**30Y SOFR Swap vs Treasury**")
        sofr = st.number_input("30Y SOFR Swap Rate (%)", min_value=0.0, step=0.01, format="%.2f", value=4.30, key="sofr")
        treasury = st.number_input("30Y Treasury Yield (%)", min_value=0.0, step=0.01, format="%.2f", value=4.90, key="treasury")
        submit1 = st.button("Submit SOFR Data", key="submit1")
        if submit1 and (sofr is not None) and (treasury is not None):
            spread = sofr - treasury
            st.success(f"Spread (SOFR - Treasury): {spread:.2f}%")
            # Update SOFR CSV only when user submits
            today = datetime.date.today()
            sofr_csv_file = 'sofr_treasury_spread_log.csv'
            
            # Load existing SOFR data if present
            if os.path.isfile(sofr_csv_file):
                df_sofr = pd.read_csv(sofr_csv_file)
                if not df_sofr.empty:
                    # Convert Date column to datetime, handling errors
                    df_sofr['Date'] = pd.to_datetime(df_sofr['Date'], errors='coerce')
                    # Remove rows with invalid dates
                    df_sofr = df_sofr.dropna(subset=['Date'])
                    if not df_sofr.empty:
                        # Remove any rows with today's date
                        df_sofr = df_sofr[df_sofr['Date'].dt.date != today]
            else:
                df_sofr = pd.DataFrame(columns=['Date', 'SOFR_Swap', 'Treasury_Yield', 'Spread'])
            
            # Append new SOFR row
            new_sofr_row = pd.DataFrame([[pd.Timestamp(today), f'{sofr:.4f}', f'{treasury:.4f}', f'{spread:.4f}']], 
                                        columns=['Date', 'SOFR_Swap', 'Treasury_Yield', 'Spread'])
            df_sofr = pd.concat([df_sofr, new_sofr_row], ignore_index=True)
            # Remove duplicate dates, keep the last
            df_sofr = df_sofr.drop_duplicates(subset=['Date'], keep='last')
            # Sort by date
            df_sofr = df_sofr.sort_values('Date')
            # Write back to CSV
            df_sofr.to_csv(sofr_csv_file, index=False)
            st.info(f"Logged today's data to sofr_treasury_spread_log.csv")
    
    with col2:
        st.markdown("**30Y Yield vs Policy Rate Spread**")
        germany_yield = st.number_input("Germany 30Y Bund Yield (%)", min_value=0.0, step=0.01, format="%.2f", value=3.20, key="germany_yield")
        japan_yield = st.number_input("Japan 30Y JGB Yield (%)", min_value=0.0, step=0.01, format="%.2f", value=3.05, key="japan_yield")
        fed_rate = st.number_input("US Fed Funds Rate (%)", min_value=0.0, step=0.01, format="%.2f", value=4.50, key="fed_rate")
        ecb_rate = st.number_input("ECB Main Refinancing Rate (%)", min_value=0.0, step=0.01, format="%.2f", value=2.15, key="ecb_rate")
        boj_rate = st.number_input("BoJ Policy Rate (%)", min_value=0.0, step=0.01, format="%.2f", value=0.50, key="boj_rate")
        submit2 = st.button("Submit Yield Data", key="submit2")
        if submit2:
            us_spread = treasury - fed_rate  # Use treasury value from left column
            germany_spread = germany_yield - ecb_rate
            japan_spread = japan_yield - boj_rate
            st.success(f"US: {us_spread:.2f}% | Germany: {germany_spread:.2f}% | Japan: {japan_spread:.2f}%")
            # Update yield CSV only when user submits
            today = datetime.date.today()
            yield_csv_file = 'thirtyy_spread_log.csv'
            
            # Load existing yield data if present
            if os.path.isfile(yield_csv_file):
                df_yield = pd.read_csv(yield_csv_file)
                if not df_yield.empty:
                    # Convert Date column to datetime, handling errors
                    df_yield['Date'] = pd.to_datetime(df_yield['Date'], errors='coerce')
                    # Remove rows with invalid dates
                    df_yield = df_yield.dropna(subset=['Date'])
                    if not df_yield.empty:
                        # Remove any rows with today's date
                        df_yield = df_yield[df_yield['Date'].dt.date != today]
            else:
                df_yield = pd.DataFrame(columns=[
                    'Date',
                    'US_30Y_Yield', 'US_Policy', 'US_Spread',
                    'Germany_30Y_Yield', 'Germany_Policy', 'Germany_Spread',
                    'Japan_30Y_Yield', 'Japan_Policy', 'Japan_Spread'])
            
            # Append new yield row
            new_yield_row = pd.DataFrame([[pd.Timestamp(today), f'{treasury:.4f}', f'{fed_rate:.4f}', f'{us_spread:.4f}',
                                           f'{germany_yield:.4f}', f'{ecb_rate:.4f}', f'{germany_spread:.4f}',
                                           f'{japan_yield:.4f}', f'{boj_rate:.4f}', f'{japan_spread:.4f}']],
                                         columns=[
                                             'Date',
                                             'US_30Y_Yield', 'US_Policy', 'US_Spread',
                                             'Germany_30Y_Yield', 'Germany_Policy', 'Germany_Spread',
                                             'Japan_30Y_Yield', 'Japan_Policy', 'Japan_Spread'])
            df_yield = pd.concat([df_yield, new_yield_row], ignore_index=True)
            # Remove duplicate dates, keep the last
            df_yield = df_yield.drop_duplicates(subset=['Date'], keep='last')
            # Sort by date
            df_yield = df_yield.sort_values('Date')
            # Write back to CSV
            df_yield.to_csv(yield_csv_file, index=False)
            st.info(f"Logged today's data to thirtyy_spread_log.csv")
    
    # Plots section - side by side
    st.subheader("Data Visualization")
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("**US 30Y SOFR Swap, Treasury Yield, and Spread**")
        # Plot for left column
        csv_file = 'sofr_treasury_spread_log.csv'
        if os.path.isfile(csv_file):
            df_log = pd.read_csv(csv_file, parse_dates=['Date'])
            if not df_log.empty:
                df_log['Date'] = pd.to_datetime(df_log['Date'])
                df_log['SOFR_Swap'] = pd.to_numeric(df_log['SOFR_Swap'])
                df_log['Treasury_Yield'] = pd.to_numeric(df_log['Treasury_Yield'])
                df_log['Spread'] = pd.to_numeric(df_log['Spread'])
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_log['Date'], y=df_log['Spread'], mode='lines+markers', name='Spread', line=dict(color='green', width=2)))
                fig.add_trace(go.Scatter(x=df_log['Date'], y=df_log['SOFR_Swap'], mode='lines+markers', name='SOFR Swap', line=dict(color='blue', width=2)))
                fig.add_trace(go.Scatter(x=df_log['Date'], y=df_log['Treasury_Yield'], mode='lines+markers', name='Treasury Yield', line=dict(color='red', width=2)))
                # Highlight zero line
                fig.add_shape(type="line", x0=df_log['Date'].min(), x1=df_log['Date'].max(), y0=0, y1=0, line=dict(color="black", width=1, dash="dash"), xref='x', yref='y')
                fig.update_layout(
                    title="US 30Y SOFR Swap, Treasury Yield, and Spread",
                    xaxis_title="Date",
                    yaxis_title="Rate / Spread (%)",
                    legend_title="Series",
                    hovermode="x unified",
                    template="plotly_white",
                    height=400
                )
                fig.update_xaxes(
                    rangeslider_visible=False,
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1, label="1D", step="day", stepmode="backward"),
                            dict(count=7, label="7D", step="day", stepmode="backward"),
                            dict(count=1, label="1M", step="month", stepmode="backward"),
                            dict(count=3, label="3M", step="month", stepmode="backward"),
                            dict(count=6, label="6M", step="month", stepmode="backward"),
                            dict(count=1, label="1Y", step="year", stepmode="backward"),
                            dict(count=2, label="2Y", step="year", stepmode="backward"),
                            dict(count=5, label="5Y", step="year", stepmode="backward"),
                            dict(step="all", label="All")
                        ]),
                        bgcolor='lightgray',
                        activecolor='steelblue',
                        font=dict(size=10)
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Show data summary
                st.write(f"**Data Summary:** {len(df_log)} points | {df_log['Date'].min().strftime('%Y-%m-%d')} to {df_log['Date'].max().strftime('%Y-%m-%d')}")
    
    with col_right:
        st.markdown("**30Y Yield minus Policy Rate Spread: US, Germany, Japan**")
        # Plot for right column
        csv_file = 'thirtyy_spread_log.csv'
        
        # Load user-submitted data
        user_data = None
        if os.path.isfile(csv_file):
            user_data = pd.read_csv(csv_file)
            if not user_data.empty:
                # Convert Date column to datetime, handling errors
                user_data['Date'] = pd.to_datetime(user_data['Date'], errors='coerce')
                # Remove rows with invalid dates
                user_data = user_data.dropna(subset=['Date'])
                if not user_data.empty:
                    user_data['US_Spread'] = pd.to_numeric(user_data['US_Spread'], errors='coerce')
                    user_data['Germany_Spread'] = pd.to_numeric(user_data['Germany_Spread'], errors='coerce')
                    user_data['Japan_Spread'] = pd.to_numeric(user_data['Japan_Spread'], errors='coerce')
                    # Remove rows with invalid numeric data
                    user_data = user_data.dropna(subset=['US_Spread', 'Germany_Spread', 'Japan_Spread'])
        
        # Use user data for plotting
        if user_data is not None and not user_data.empty:
            combined_data = user_data.sort_values('Date')
            
            # Create plot
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=combined_data['Date'], y=combined_data['US_Spread'], mode='lines+markers', name='US', line=dict(color='blue', width=2)))
            fig.add_trace(go.Scatter(x=combined_data['Date'], y=combined_data['Germany_Spread'], mode='lines+markers', name='Germany', line=dict(color='red', width=2)))
            fig.add_trace(go.Scatter(x=combined_data['Date'], y=combined_data['Japan_Spread'], mode='lines+markers', name='Japan', line=dict(color='green', width=2)))
            # Highlight zero line
            fig.add_shape(type="line", x0=combined_data['Date'].min(), x1=combined_data['Date'].max(), y0=0, y1=0, line=dict(color="black", width=1, dash="dash"), xref='x', yref='y')
            fig.update_layout(
                title="30Y Yield minus Policy Rate Spread: US, Germany, Japan",
                xaxis_title="Date",
                yaxis_title="Spread (%)",
                legend_title="Country",
                hovermode="x unified",
                template="plotly_white",
                height=400
            )
            fig.update_xaxes(
                rangeslider_visible=False,
                rangeselector=dict(
                    buttons=list([
                        dict(count=1, label="1D", step="day", stepmode="backward"),
                        dict(count=7, label="7D", step="day", stepmode="backward"),
                        dict(count=1, label="1M", step="month", stepmode="backward"),
                        dict(count=3, label="3M", step="month", stepmode="backward"),
                        dict(count=6, label="6M", step="month", stepmode="backward"),
                        dict(count=1, label="1Y", step="year", stepmode="backward"),
                        dict(count=2, label="2Y", step="year", stepmode="backward"),
                        dict(count=5, label="5Y", step="year", stepmode="backward"),
                        dict(step="all", label="All")
                    ]),
                    bgcolor='lightgray',
                    activecolor='steelblue',
                    font=dict(size=10)
                )
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Show data summary
            st.write(f"**Data Summary:** {len(combined_data)} points | {combined_data['Date'].min().strftime('%Y-%m-%d')} to {combined_data['Date'].max().strftime('%Y-%m-%d')}")
    
# --- Historical Data Section: 30Y Swap Spread & Yield ---
st.markdown('---')
st.subheader('📈 Historical Data: 30Y Swap Spread & Yield')

swap_csv = '30y_swap.csv'
yield_csv = '30y.csv'

if os.path.isfile(swap_csv) and os.path.isfile(yield_csv):
    df_swap = pd.read_csv(swap_csv)
    df_yield = pd.read_csv(yield_csv)
    # Use capitalized column names
    if 'Date' in df_swap.columns and 'Price' in df_swap.columns and 'Date' in df_yield.columns and 'Price' in df_yield.columns:
        # Merge on Date
        df_swap['Date'] = pd.to_datetime(df_swap['Date'])
        df_yield['Date'] = pd.to_datetime(df_yield['Date'])
        df_merged = pd.merge(df_swap[['Date', 'Price']], df_yield[['Date', 'Price']], on='Date', suffixes=('_swap', '_yield'))
        df_merged['spread'] = df_merged['Price_swap'] - df_merged['Price_yield']

        # Date range selector (show all options as radio buttons)
        st.markdown('**Select time range to display:**')
        range_options = {
            '7 Days': 7,
            '1 Month': 30,
            '3 Months': 90,
            '6 Months': 180,
            '1 Year': 365,
            '2 Years': 365*2,
            '3 Years': 365*3,
            '5 Years': 365*5,
            'All': None
        }
        range_choice = st.radio('Time Range', list(range_options.keys()), index=len(range_options)-1, horizontal=True)
        days = range_options[range_choice]
        if days is not None:
            max_date = df_merged['Date'].max()
            min_date = max_date - pd.Timedelta(days=days)
            df_plot = df_merged[df_merged['Date'] >= min_date]
        else:
            df_plot = df_merged

        # Moving average options
        st.markdown('**Show moving averages:**')
        ma_periods = [7, 30, 60, 90]
        ma_options = {f'{p}-day MA': p for p in ma_periods}
        selected_ma = st.multiselect('Select moving averages to plot', list(ma_options.keys()), default=[], key='ma_select', help='Add moving averages for both series')

        # Compute moving averages if selected
        for p in ma_periods:
            if f'{p}-day MA' in selected_ma:
                df_plot[f'Yield_MA_{p}'] = df_plot['Price_yield'].rolling(window=p, min_periods=1).mean()
                df_plot[f'Spread_MA_{p}'] = df_plot['spread'].rolling(window=p, min_periods=1).mean()

        # Plot with secondary y-axis for swap spread
        fig = go.Figure()
        # Add raw series only if no moving average is selected
        if not selected_ma:
            # 30Y Yield on left y-axis
            fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Price_yield'], mode='lines', name='30Y Yield', line=dict(color='blue'), yaxis='y1'))
            # Swap Spread on right y-axis
            fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['spread'], mode='lines', name='Swap Spread', line=dict(color='green'), yaxis='y2'))
        # Add moving averages if selected
        ma_colors = {7: 'royalblue', 30: 'orange', 60: 'purple', 90: 'brown'}
        for p in ma_periods:
            if f'{p}-day MA' in selected_ma:
                fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot[f'Yield_MA_{p}'], mode='lines', name=f'30Y Yield {p}-day MA', line=dict(color=ma_colors[p], dash='dot'), yaxis='y1'))
                fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot[f'Spread_MA_{p}'], mode='lines', name=f'Swap Spread {p}-day MA', line=dict(color=ma_colors[p], dash='dash'), yaxis='y2'))
        # Highlight zero line on right y-axis
        fig.add_shape(type="line", x0=df_plot['Date'].min(), x1=df_plot['Date'].max(), y0=0, y1=0, line=dict(color="black", width=1, dash="dash"), xref='x', yref='y2')
        fig.update_layout(
            title="30Y Yield and Swap Spread Over Time",
            xaxis=dict(title="Date"),
            yaxis=dict(
                title="30Y Yield",
                tickfont=dict(color='blue')
            ),
            yaxis2=dict(
                title="Swap Spread",
                tickfont=dict(color='green'),
                overlaying='y',
                side='right',
                showgrid=False
            ),
            legend_title="Series",
            hovermode="x unified",
            template="plotly_white",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(f"Data points: {len(df_plot)} | {df_plot['Date'].min().strftime('%Y-%m-%d')} to {df_plot['Date'].max().strftime('%Y-%m-%d')}")
    else:
        st.warning('CSV files must contain columns: Date, Price')
else:
    st.info('Historical swap and yield CSV files not found in the directory.')


if __name__ == "__main__":
    main()
