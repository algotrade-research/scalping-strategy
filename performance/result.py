import pandas as pd
from backtesting.backtesting import Backtesting  # Adjust this import based on your project structure

class BacktestResult:
    def __init__(self, params, asset_value=10000):
        """
        Initialize with the parameters for the backtest and an initial asset value.
        
        Parameters:
            params (dict): A dictionary of strategy parameters.
            asset_value (float): Starting asset value (default: 10000).
        """
        self.params = params
        self.asset_value = asset_value
        self.backtester = Backtesting()

    def backtest_insample_data(self, file_path = "data/train.csv"):
        """
        Run the backtesting strategy on insample data.
        
        Parameters:
            file_path (str): Path to the CSV file containing insample data.
        
        Returns:
            DataFrame: The result of the backtest.
        """
        insample_data = pd.read_csv(file_path)
        result = self.backtester.run(insample_data, self.params, self.asset_value)
        return result

    def backtest_outsample_data(self, file_path = "data/test.csv"):
        """
        Run the backtesting strategy on outsample data.
        
        Parameters:
            file_path (str): Path to the CSV file containing outsample data.
        
        Returns:
            DataFrame: The result of the backtest.
        """
        outsample_data = pd.read_csv(file_path)
        result = self.backtester.run(outsample_data, self.params, self.asset_value)
        return result

