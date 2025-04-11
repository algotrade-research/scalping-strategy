from data.service import *
from backtesting.backtesting import *
from config.config import optimization_params
from optimization.optimization import *
from performance.result import BacktestResult
from performance.metric import Metric
from backtesting.backtesting import Backtesting
import pandas as pd

# Load the data
data_service = DataService()
train_data = data_service.get_train_data()

backtesting = Backtesting()

study_name = "sma_v2"
storage = "sqlite:///sma.db"
n_trials = 1000
sampler = 22
train_data_path = "data/train.csv"

optimization = Optimization(train_data_path, study_name, storage, n_trials, sampler)

results = optimization.run_optimization()
optimization.save_best_params(results)
