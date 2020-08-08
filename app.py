from data import StockData
import streamlit as st
import pandas as pd
import numpy as np
import yaml
from datetime import datetime
#import matplotlib.pyplot as plt

def main(path):
    # Collect existing metadata
    with open(f"{path}\\cache.yaml", "r") as f:
        meta = yaml.safe_load(f)
        meta.pop("init", None)
    companies = [*meta]

    # Provide instructions to the user
    readme_text = st.markdown(readFile("instructions.md"))

    st.sidebar.title("Company Selection")
    comp_list = st.sidebar.selectbox("Company List", ["", *companies])
    if comp_list == "":
        pass
    else:
        readme_text.empty()
        run_app(comp_list, path)

def run_app(company, path):
    @st.cache
    def load_data(company, path):
        d = StockData(ticker=company, data_path=path)
        d.get(refresh=False)
        with open(d.name, "r") as f:
            out = pd.read_csv(f)
        return out

    @st.cache
    def create_div_history(data):
        subset = data[["timestamp", "close", "dividend_amount"]]
        subset = subset.rename(columns={
            "timestamp": "ts", 
            "close": "price", 
            "dividend_amount": "div_amount"})

        per = pd.DatetimeIndex(subset.ts).to_period("Y")
        yield_df = subset.groupby(per).agg({"price": ["mean"], "div_amount": ["sum"]})
        yield_df = yield_df.set_index(yield_df.index.strftime("%Y-%m-%d"))
        yield_df = yield_df.iloc[::-1]
        yield_df.columns = ["_".join(col).strip() for col in yield_df.columns.values]
        yield_df["yield"] = yield_df["div_amount_sum"] / yield_df["price_mean"] * 100

        div_df = subset[subset["div_amount"] > 0]

        return yield_df, div_df

    data = load_data(company, path)
    yield_df, div_df = create_div_history(data)

    st.write('## Dividend history', yield_df[:100])
    st.vega_lite_chart(div_df, {
        "width": 800,
        "height": 300,
        "mark": "line",
        "encoding": {
            "x": {"field": "ts", "type": "temporal"},
            "y": {"field": "div_amount", "type": "quantitative"}
        }
    })
    return None

def readFile(path):
    with open(path) as f:
        content = f.readlines()
    return "".join(content)

if __name__ == "__main__":
    # if need be provide argument parser
    PATH = "D:\\Data\\Finance"
    main(PATH)