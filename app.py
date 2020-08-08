from data import StockData
import streamlit as st
import pandas as pd
import numpy as np
import yaml
#import matplotlib.pyplot as plt

def main(path):
    # Collect existing metadata
    with open(f"{path}\\cache.yaml", "r") as f:
        meta = yaml.safe_load(f)
        meta.pop("init", None)
    companies = meta.keys()

    # Provide instructions to the user
    readme_text = st.markdown(readFile("instructions.md"))

    st.sidebar.title("Company Selection")
    comp_list = st.sidebar.selectbox("Company List",
        ["Dropdown", *companies, "Add New"])
    if comp_list == "Dropdown":
        pass
    elif comp_list == "Add New":
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
    PATH = "D:\\Data\\Finance"
    main(PATH)