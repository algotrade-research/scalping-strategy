import optuna
import json
import pandas as pd
from backtesting.backtesting import Backtesting  # adjust import according to your module structure

class Optimization:
    def __init__(self, train_data_path, study_name, storage, n_trials, seed=42):
        """
        Initialize the optimization instance.
        
        Parameters:
            train_data_path (str): Path to the CSV file containing training data.
            study_name (str): The name of the Optuna study.
            storage (str): Storage URL for the study (e.g., 'sqlite:///sma.db').
            n_trials (int): Number of optimization trials.
            seed (int): Seed for the sampler (default 42).
        """
        self.train = pd.read_csv(train_data_path)
        self.study_name = study_name
        self.storage = storage
        self.n_trials = n_trials
        self.sampler = optuna.samplers.TPESampler(seed=seed)
        self.backtest = Backtesting()
    
    def objective(self, trial):
        """
        Objective function for Optuna that suggests parameter values,
        runs the backtesting strategy, and returns the cumulative PNL.
        """
        params = {
            "sma_window_length": trial.suggest_int('sma_window_length', 10, 100),
            "sma_gap": trial.suggest_float('sma_gap', 0.0005, 0.1),
            "momentum_lookback": trial.suggest_int('momentum_lookback', 2, 10),
            "acceleration_threshold": trial.suggest_float('acceleration_threshold', 0.1, 1),
            "short_acceleration_threshold": trial.suggest_float('short_acceleration_threshold', 0.05, 0.5),
            "take_profit_threshold": trial.suggest_float('take_profit_threshold', 1, 5),
            "cut_loss_threshold": trial.suggest_float('cut_loss_threshold', 1, 2),
            "quantity_window": trial.suggest_int('quantity_window', 2, 20),
            "quantity_multiply": trial.suggest_int('quantity_multiply', 0, 5),
            "short_extra_profit": trial.suggest_float('short_extra_profit', 0, 2),
            "rsi_window": trial.suggest_int('rsi_window', 5, 100),
            "rsi_threshold": trial.suggest_int('rsi_threshold', 5, 45)
        }
        result = self.backtest.run(self.train, params)
        # We assume that the last row contains the final cumulative PNL.
        return result.iloc[-1]["Cumulative PNL"]

    def run_optimization(self):
        """
        Create and run the Optuna study, returning the best parameters.
        """
        study = optuna.create_study(
            study_name=self.study_name,
            storage=self.storage,
            load_if_exists=True,
            sampler=self.sampler,
            direction="maximize"
        )
        study.optimize(self.objective, n_trials=self.n_trials)
        return study.best_params

    def save_best_params(self, best_params, filepath = 'optimization/best_params.json'):
        """
        Save the best parameters to a JSON file.
        
        Parameters:
            best_params (dict): The best parameters found by Optuna.
            filepath (str): Path to save the JSON file (default: 'best_params.json').
        """
        with open(filepath, 'w') as f:
            json.dump(best_params, f, indent=4)
        return best_params
    
        
# Example usage:
# optimizer = Optimization(train_data_path='data/train.csv', study_name='sma-vq2', storage='sqlite:///sma.db', n_trials=3000)
# best_parameters = optimizer.save_best_params('best_params.json')
# print("Best Parameters:", best_parameters)
