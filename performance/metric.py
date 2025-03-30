import matplotlib.pyplot as plt
import numpy as np

class Metric:
    def __init__(self, result_df):
        """
        Initialize with the result DataFrame from the backtesting.
        The DataFrame is expected to have at least these columns:
            - 'Cumulative PNL'
            - 'PNL'
            - 'Cumulative Long'
            - 'Cumulative Short'
        """
        self.result_df = result_df

    def plot_pnl(self):
        """
        Plot the cumulative PNL over time.
        """
        plt.figure(figsize=(12, 6))
        plt.plot(self.result_df.index, self.result_df['Cumulative PNL'], label='Cumulative PNL')
        plt.xlabel('Time')
        plt.ylabel('Cumulative PNL')
        plt.title('Cumulative PNL Over Time')
        plt.legend()
        plt.grid(True)
        plt.show()

    def calculate_sharpe(self, risk_free_rate=0.0001):
        """
        Calculate the annualized Sharpe ratio based on the 'PNL' column.
        We assume the PNL column represents daily returns over one year.
        
        Steps:
          1. Convert the annual risk-free rate (default 5%) to a daily rate.
             daily_rf = (1 + annual_rf)^(1/252) - 1
          2. Compute the excess daily return and then annualize the Sharpe ratio using sqrt(252).
        """
        pnl = self.result_df['PNL']
        # Convert 5% annual risk-free rate to a daily rate (assuming 252 trading days)
        daily_rf = (1 + risk_free_rate) ** (1/252) - 1
        mean_return = pnl.mean()
        std_return = pnl.std()
        if std_return == 0:
            return np.nan
        # Annualize Sharpe ratio
        sharpe = ((mean_return - daily_rf) / std_return) * np.sqrt(252)
        return sharpe

    def calculate_mdd(self):
        """
        Calculate the Maximum Drawdown (MDD) from the 'Cumulative PNL' series.
        MDD is computed as the maximum drop from a peak in the cumulative PNL.
        """
        cum_pnl = self.result_df['Cumulative PNL']
        running_max = cum_pnl.cummax()
        drawdown = running_max - cum_pnl
        max_drawdown = drawdown.max()
        return max_drawdown

    def calculate_win_rate(self):
        """
        Calculate the win rate as the fraction of periods with positive PNL 
        among those periods where PNL is nonzero.
        """
        pnl = self.result_df['PNL']
        valid = pnl[pnl != 0]
        if len(valid) == 0:
            return np.nan
        win_count = (valid > 0).sum()
        win_rate = win_count / len(valid)
        return win_rate

    def get_long_short_counts(self):
        """
        Retrieve the total number of long and short trades executed.
        Assumes the DataFrame has cumulative counts in the 'Cumulative Long'
        and 'Cumulative Short' columns.
        """
        last_row = self.result_df.iloc[-1]
        long_count = last_row.get('Cumulative Long', 0)
        short_count = last_row.get('Cumulative Short', 0)
        return long_count, short_count

    def show_metrics(self):
        """
        Calculate and print all performance metrics.
        Returns a dictionary with the following keys:
            - Sharpe Ratio
            - Maximum Drawdown
            - Win Rate
            - Total Long Trades
            - Total Short Trades
        """
        sharpe = self.calculate_sharpe()
        mdd = self.calculate_mdd()
        win_rate = self.calculate_win_rate()
        long_count, short_count = self.get_long_short_counts()

        metrics = {
            'Sharpe Ratio': sharpe,
            'Maximum Drawdown': mdd,
            'Win Rate': win_rate,
            'Total Long Trades': long_count,
            'Total Short Trades': short_count
        }

        print("Performance Metrics:")
        for key, value in metrics.items():
            print(f"{key}: {value}")
        return metrics

    def plot_contracts_held(self):
        """
        Plot the number of contracts held over time.
        """
        plt.figure(figsize=(12, 6))
        plt.plot(self.result_df.index, self.result_df['Contracts Held'], label='Contracts Held', marker='o', linestyle='-')
        plt.xlabel('Time')
        plt.ylabel('Contracts Held')
        plt.title('Contracts Held Over Time')
        plt.legend()
        plt.grid(True)
        plt.show()

    def get_contracts_held_series(self):
        """
        Return the 'Contracts Held' column as a pandas Series.
        """
        return self.result_df['Contracts Held']
