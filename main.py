from data.service import *
from backtesting.backtesting import *
from config.config import optimization_params
from optimization.optimization import *
from performance.result import BacktestResult
from performance.metric import Metric
import pandas as pd

# Load the data
data_service = DataService()
train_data = data_service.get_train_data()
test_data = data_service.get_test_data()

# Print the head of the data
print("Train Data:")
print(train_data.head())
print("Test Data:")
print(test_data.head())

# Run the backtest with the best parameters
result = BacktestResult(optimization_params)

# In-sample backtest
insample_result = result.backtest_insample_data()
print("Insample Backtest Result:")
print(insample_result.head())
metrics = Metric(insample_result)
metrics.show_metrics()
metrics.plot_pnl()

# Out-of-sample backtest
outsample_result = result.backtest_outsample_data()
print("Out-of-sample Backtest Result:")
print(outsample_result.head())
metrics = Metric(outsample_result)
metrics.show_metrics()
metrics.plot_pnl()