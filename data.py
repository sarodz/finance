import yaml
from alpha_vantage.timeseries import TimeSeries
from datetime import datetime, timedelta
import os
import csv


class StockData(object):
    def __init__(self, ticker, freq="daily", data_path="."):
        with open("secrets.yaml", "r") as f:
            secrets = yaml.safe_load(f)
            API_key = secrets["alphavantage"]["API_key"]
        if ":" not in ticker:
            raise ValueError("Provide full ticker name, missing : in name")
        if "." in ticker:
            ticker = ticker.replace(".", "-") 
        self.cache_exist = StockData._checkCache(data_path, ticker)
        self.ticker = ticker
        self.client = TimeSeries(key=API_key, output_format="csv")    
        self.freq = freq
        self.data_parent_path = data_path


    @staticmethod
    def _checkCache(parent, ticker):
        file_name = f"{parent}\\cache.yaml"
        if not os.path.isfile(file_name):
            with open(file_name, "w") as f: 
                yaml.dump({"init": None}, f)

        with open(file_name, "r") as f:
            cache = yaml.safe_load(f)
        try:
            if ticker in cache.keys():
                return True
        except:
            pass
        return False

    @staticmethod
    def _readMeta(parent):
        with open(f"{parent}\\cache.yaml", "r") as f:
            meta = yaml.safe_load(f)
        return meta

    @staticmethod
    def _writeCache(parent, data, ticker, freq):
        ticker_temp = ticker.replace(":", "_")
        file_name = f"{parent}\\{ticker_temp}_{freq}.csv"

        if os.path.isfile(file_name):
            os.remove(file_name)

        with open(file_name, "w", newline="") as f:
            writer = csv.writer(f, delimiter=",", quotechar="\"", quoting=csv.QUOTE_MINIMAL)
            for row in data[0]:
                writer.writerow(row)

        meta = StockData._readMeta(parent)
        with open(f"{parent}\\cache.yaml", "w") as f:
            latest = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
            meta = {**meta, **{ticker: latest}}
            yaml.dump(meta, f)      


    @staticmethod
    def _readCache(parent, ticker, freq):
        ticker_temp = ticker.replace(":", "_")
        file_name = f"{parent}\\{ticker_temp}_{freq}.csv"
        with open(file_name, "r") as f:
            reader = csv.reader(f, delimiter=",")
        return reader


    def _getDaily(self, refresh):
        if not self.cache_exist:
            refresh = True

        if refresh == False:
            print("Using cache")
            data = StockData._readCache(self.data_parent_path, self.ticker, self.freq)
        else:
            print("Retrieving data")
            data = self.client.get_daily_adjusted(symbol=self.ticker, outputsize="full")
            StockData._writeCache(self.data_parent_path, data, self.ticker, self.freq)
        return data


    def get(self, refresh=False):
        if self.freq == "daily":
            return self._getDaily(refresh)
        else:
            raise NotImplementedError()


if __name__ == "__main__":
    d = StockData(ticker="TSX:REI.UN", data_path="D:\\Data\\Finance")
    data = d.get(refresh=False)
    print(data)
