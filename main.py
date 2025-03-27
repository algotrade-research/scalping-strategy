from data.service import *
from backtesting.backtesting import *
from config.config import optimization_params

# Instantiate the DataService.
data_service = DataService()
train = pd.read_csv('train.csv')
backtester = Backtesting()
results = backtester.run(trading_data=train, params=optimization_params, asset_value=10000)
print(results)