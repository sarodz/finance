import streamlit as st
import pandas as pd
import numpy as np
import yaml
from session import _get_state
from data import StockData
from datetime import datetime, timedelta
#import matplotlib.pyplot as plt

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
    year_range = st.number_input(label="How many years should the analysis include?", value=0,  min_value=0, max_value=20)
    target_yield = st.slider(label="Target yield", value=0.0, step=0.1,  min_value=0.0, max_value=20.0)
    submit = st.button("Submit")
    if submit:
        readme_text.empty()
        run_app(ticker, year_range, target_yield, PATH)


def page_data(state):
    st.title("Data")
    st.write("The following tickers can be accessed")
    st.selectbox("Company List", ["", *state.companies])
    ticker = st.text_input("Type the ticker with its market name to load a new ticker (Ex: TSX:TD)", "")
    if ticker != "":
        d = StockData(ticker=ticker, data_path=PATH)
        d.get(refresh=False)
        st.write(f"{ticker} is accesible now, navigate to Dashboard to access it")


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
        #TODO: Deal with the unfinished year by repeating the latest div
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

        per = pd.DatetimeIndex(history.ts).to_period("Y")
        yield_df = history.groupby(per).agg({"price": ["mean"], "div_amount": ["sum"]})
        yield_df = yield_df.set_index(yield_df.index.strftime("%Y-%m-%d"))
        yield_df.columns = ["_".join(col).strip() for col in yield_df.columns.values]
        yield_df["yield"] = yield_df["div_amount_sum"] / yield_df["price_mean"] * 100
        yield_df["growth"] = (yield_df["price_mean"].shift(1) - yield_df["price_mean"]) / yield_df["price_mean"].shift(1) * 100
        yield_df = yield_df.reset_index()

        per = pd.DatetimeIndex(div_history.ts).to_period("Y")
        div_df = div_history.groupby(per).agg({"div_amount": ["sum"]})
        div_df = div_df.set_index(div_df.index.strftime("%Y-%m-%d"))
        div_df.columns = ["_".join(col).strip() for col in div_df.columns.values]
        div_df = div_df.reset_index()
        initial_year = div_df.head(1)
        last_year = div_df.tail(1)

        init_div = initial_year["div_amount_sum"].values
        last_div = last_year["div_amount_sum"].values
        avg_yield = yield_df["yield"].mean()
        target_price = div_df["div_amount_sum"].mean() / (target_yield * 0.01)
        data = {
            "Initial Year": initial_year["ts"].values[0][:4],
            "Initial Year Div": init_div,
            "Last Year": last_year["ts"].values[0][:4],
            "Last Year Div": last_div,
            "Dividend Growth %" : (last_div-init_div)/init_div*100,
            "Avg Yield": avg_yield,
            "Target Price*": target_price
        }
        summary_df = pd.DataFrame.from_dict(data)
        summary_df = summary_df.set_index([pd.Index([company])])

        return div_output, summary_df, yield_df, div_df

    data = load_data(company, path)
    div_output, summary_df, yield_df, div_df = create_div_history(company, data, year, target_yield)

    st.write("## Dividend history")
    st.table(summary_df)
    st.write(f"*Target Price is calculated based on the average dividend for the given period and shows the highest we should pay for {company}")
    st.vega_lite_chart(yield_df, {
        "width": 800,
        "height": 300,
        "mark": "line",
        "encoding": {
            "x": {"field": "ts", "type": "temporal"},
            "y": {"field": "yield", "type": "quantitative"}
        }
    })

    st.vega_lite_chart(div_output, {
        "width": 800,
        "height": 300,
        "mark": "line",
        "encoding": {
            "x": {"field": "ts", "type": "temporal"},
            "y": {"field": "div_amount", "type": "quantitative"}
        }
    })

    st.vega_lite_chart(div_df, {
        "width": 800,
        "height": 300,
        "mark": "bar",
        "encoding": {
            "x": {"field": "ts", "type": "temporal"},
            "y": {"field": "div_amount_sum", "type": "quantitative"}
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
    main()