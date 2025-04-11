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

if __name__ == "__main__":
    choice = input("Select backtest type ('in', 'out', or 'both'): ").strip().lower()
    if choice == "in":
        insample_result = result.backtest_insample_data()
        print("In-sample Backtest Result:")
        print(insample_result.head())
        metrics = Metric(insample_result)
        metrics.show_metrics()
        metrics.plot_pnl()

    elif choice == "out":
        outsample_result = result.backtest_outsample_data()
        print("Out-of-sample Backtest Result:")
        print(outsample_result.head())
        metrics = Metric(outsample_result)
        metrics.show_metrics()
        metrics.plot_pnl()

    elif choice == "both":
        print("Running In-sample Backtest...")
        insample_result = result.backtest_insample_data()
        print(insample_result.head())
        metrics = Metric(insample_result)
        metrics.show_metrics()
        metrics.plot_pnl()

        print("\nRunning Out-of-sample Backtest...")
        outsample_result = result.backtest_outsample_data()
        print(outsample_result.head())
        metrics = Metric(outsample_result)
        metrics.show_metrics()
        metrics.plot_pnl()

    else:
        print("Invalid choice. Please select 'insample', 'outsample', or 'both'.")
