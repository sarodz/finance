import streamlit as st
import pandas as pd
import numpy as np
import yaml
from session import _get_state
from data import StockData
#import matplotlib.pyplot as plt

PATH = "D:\\Data\\Finance"

def main():
    state = _get_state()
    # Collect existing metadata
    meta = loadCache()
    state.companies = [*meta]

    pages = {
        "Dashboard": page_dashboard,
        "Data": page_data,
    }
    st.sidebar.title("Navigate")
    page = st.sidebar.radio("Select your page", tuple(pages.keys()))

    # Display the selected page with the session state
    pages[page](state)

    # Mandatory to avoid rollbacks with widgets, must be called at the end of your app
    state.sync()


def page_dashboard(state):
    st.title("Dashboard page")

    # Provide instructions to the user
    readme_text = st.markdown(readFile("instructions.md"))

    ticker = st.selectbox("Company List", ["", *state.companies])
    if ticker == "":
        pass
    else:
        readme_text.empty()
        run_app(ticker, PATH)


def page_data(state):
    st.title("Data")
    st.write("The following tickers are stored in cache")
    st.selectbox("Company List", ["", *state.companies])
    ticker = st.text_input("Type ticker with market name to load a new ticker (Ex: TSX:TD)", "")
    if ticker != "":
        d = StockData(ticker=ticker, data_path=PATH)
        d.get(refresh=False)
        st.write(f"{ticker} is accesible now, navigate to Dashboard to access it")


def loadCache():
    with open(f"{PATH}\\cache.yaml", "r") as f:
        meta = yaml.safe_load(f)
        meta.pop("init", None)
    return meta


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
        subset = subset[subset["dividend_amount"] > 0]
        subset["yield"] = subset["dividend_amount"] / subset["close"]
        # update the above calculation
        return subset

    data = load_data(company, path)
    divs = create_div_history(data)

    st.write('## Dividend history', divs[:10])
    st.vega_lite_chart(divs, {
        "width": 800,
        "height": 300,
        "mark": "line",
        "encoding": {
            "x": {"field": "timestamp", "type": "temporal"},
            "y": {"field": "dividend_amount", "type": "quantitative"}
        }
    })
    return None

def readFile(path):
    with open(path) as f:
        content = f.readlines()
    return "".join(content)

if __name__ == "__main__":
    # if need be provide argument parser
    main()