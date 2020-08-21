import streamlit as st
import pandas as pd
import numpy as np
import yaml
from session import _get_state
from data import StockData
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import time


PATH = "D:\\Data\\Finance"

def main():
    state = _get_state()
    # Collect existing metadata
    meta = loadCache(PATH)
    state.companies = [*meta]

    pages = {
        "Dividend": page_dividend,
        "Data": page_data,
    }
    st.sidebar.title("Navigate")
    page = st.sidebar.radio("Select your page", tuple(pages.keys()))

    # Display the selected page with the session state
    pages[page](state)

    # Mandatory to avoid rollbacks with widgets, must be called at the end of your app
    state.sync()


def page_dividend(state):
    st.title("Dividend Analysis")

    # Provide instructions to the user
    readme_text = st.markdown(readFile("instructions.md"))

    ticker = st.selectbox("Company List", ["", *state.companies])
    year_range = st.number_input(label="How many years should the analysis include?", value=10,  min_value=1, max_value=20)
    target_yield = st.slider(label="Target yield", value=5.0, step=0.1,  min_value=0.1, max_value=20.0)
    submit = st.button("Submit")
    if submit:
        readme_text.empty()
        run_app(ticker, year_range, target_yield, PATH)


def page_data(state):
    st.title("Data")
    st.write("The following tickers can be refreshed")
    selection = st.selectbox("Company List", ["", *state.companies, "All"])
    ticker = st.text_input("Or type the ticker with its market name to load a new ticker (Ex: TSX:TD)", "")
    submit = st.button("Submit")
    if submit:
        if selection == "" and ticker == "":
            st.write("Please make a selection")
        elif selection != "" and ticker != "":
            st.write("Please leave one of the options blank")
        elif selection == "All":
            for company in state.companies:
                d = StockData(ticker=company, data_path=PATH)
                d.get(refresh=True)
                st.write(f"{company} is updated/accesible now, navigate to Dashboard to access it")
                time.sleep(8.5) # API limit is 5 per minute, 500 per day
        else:
            choice = selection if selection != "" else ticker
            refresh = True if selection != "" else False
            d = StockData(ticker=choice, data_path=PATH)
            d.get(refresh=refresh)
            st.write(f"{choice} is updated/accesible now, navigate to Dashboard to access it")


def run_app(company, year, target_yield, path):
    @st.cache
    def load_data(company, path):
        d = StockData(ticker=company, data_path=path)
        d.get(refresh=False)
        with open(d.name, "r") as f:
            out = pd.read_csv(f)
        return out

    @st.cache
    def create_div_history(company, data, year, target_yield):
        subset = data[["timestamp", "close", "dividend_amount"]]
        subset = subset.rename(columns={
            "timestamp": "ts", 
            "close": "price", 
            "dividend_amount": "div_amount"})
        subset["ts"] = pd.to_datetime(subset['ts'])
        
        today = datetime.now()
        cur_dt = datetime(today.year, 1, 1)
        start_dt = cur_dt - timedelta(days= 365 * year)
 
        history = subset[(subset["ts"] >= start_dt) & (subset["ts"] < cur_dt)]
        div_history = history[history["div_amount"] > 0]
        div_output = subset[(subset["ts"] >= start_dt) & (subset["div_amount"] > 0)]
        cur_year_df = subset[(subset["ts"] >= cur_dt) & (subset["div_amount"] > 0)]
 
        per = pd.DatetimeIndex(history.ts).to_period("Y")
        yield_df = history.groupby(per).agg({"price": ["mean"], "div_amount": ["sum"]})
        yield_df = yield_df.set_index(yield_df.index.strftime("%Y-%m-%d"))
        yield_df.columns = ["_".join(col).strip() for col in yield_df.columns.values]
        yield_df["yield"] = yield_df["div_amount_sum"] / yield_df["price_mean"] * 100
        yield_df["growth"] = (yield_df["price_mean"].shift(1) - yield_df["price_mean"]) / yield_df["price_mean"].shift(1) * 100
        yield_df = yield_df.reset_index()

        per = pd.DatetimeIndex(div_history.ts).to_period("Y")
        div_df = div_history.groupby(per).agg({"div_amount": ["sum", "count"]})
        div_df = div_df.set_index(div_df.index.strftime("%Y"))
        div_df.columns = ["_".join(col).strip() for col in div_df.columns.values]
        div_df = div_df.reset_index()
        initial_year = div_df.head(1)
        last_year = div_df.tail(1)
        div_freq = int(div_df["div_amount_count"].median())

        if len(cur_year_df)  == div_freq:
            cur_div_tot = cur_year_df["div_amount"].sum()
        else:
            cur_div_tot = cur_year_df["div_amount"].sum() + (div_freq - len(cur_year_df)) * cur_year_df["div_amount"].head(1).values

        init_div = initial_year["div_amount_sum"].values
        init_date = initial_year["ts"].values[0][:4]
        last_div = last_year["div_amount_sum"].values
        last_date = last_year["ts"].values[0][:4]
        avg_yield = yield_df["yield"].mean()
        hist_target_price = div_df["div_amount_sum"].mean() / (target_yield * 0.01)
        cur_target_price = cur_div_tot / (target_yield * 0.01)
        recent_date = str(subset["ts"].head(1).values[0])[:10]
        data = {
            f"Div in {init_date}": init_div,
            f"Div in {last_date}": last_div,
            f"Div in {today.year}":cur_div_tot,
            "Dividend Growth %" : (last_div-init_div)/init_div*100,
            "Avg Yield": avg_yield,
            f"Price on {recent_date}": subset["price"].head(1).values[0],
            "Historical Target Price*": hist_target_price,
            "Current Target Price*": cur_target_price
        }
        summary_df = pd.DataFrame.from_dict(data)
        summary_df = summary_df.set_index([pd.Index([company])])

        return div_output, summary_df, yield_df, div_df
    
    data = load_data(company, path)
    div_output, summary_df, yield_df, div_df = create_div_history(company, data, year, target_yield)

    st.write("## Dividend history")
    st.table(summary_df)
    st.write(f"*Target Price is the maximum price we want to pay for a given stock. The difference between the two is, historical is based on average dividend amount and current is based on the current dividend amount for {company}")
    st.vega_lite_chart(yield_df, {
        "width": 800,
        "height": 300,
        "mark": "line",
        "encoding": {
            "x": {"field": "ts", "type": "temporal", "title": "Date"},
            "y": {"field": "yield", "type": "quantitative", "title": "Yield"}
        }
    })

    st.vega_lite_chart(div_output, {
        "width": 800,
        "height": 300,
        "mark": "line",
        "encoding": {
            "x": {"field": "ts", "type": "temporal", "title": "Date"},
            "y": {"field": "div_amount", "type": "quantitative", "title": "Dividend Amount"}
        }
    })

    st.vega_lite_chart(div_df, {
        "width": 800,
        "height": 300,
        "mark": {"type": "bar", "xOffset": 0},
        "encoding": {
            "x": {"field": "ts", "type": "nominal", "band": 0.6, "title": "Year"},
            "y": {"field": "div_amount_sum", "type": "quantitative", "title": "Total Dividend"}
        }
    })
    return None

def readFile(path):
    with open(path) as f:
        content = f.readlines()
    return "".join(content)


def loadCache(path):
    with open(f"{path}\\cache.yaml", "r") as f:
        meta = yaml.safe_load(f)
        meta.pop("init", None)
    return meta


if __name__ == "__main__":
    # if need be provide argument parser
    import sys
    sys.dont_write_bytecode = True
    main()