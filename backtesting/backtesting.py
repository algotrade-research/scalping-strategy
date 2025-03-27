from tqdm import tqdm
import pandas as pd

class Backtesting:
    # Global parameters as class attributes
    MAX_TOTAL_CONTRACTS = 45      # Global cap across all positions
    ATR_BASELINE = 1.0            # Baseline ATR value; adjust based on instrument
    TRADING_FEE = 0.47            # Trading fee per contract (example)
    TRAIL_MULTIPLIER = 1.5        # Multiplier to compute trailing stop distance

    def __init__(self):
        # (Optional) Place to initialize instance-specific parameters if needed.
        pass

    # -------------------------------
    # Helper Indicator Functions
    # -------------------------------
    def ATR(self, data, window=14):
        """
        Compute the Average True Range (ATR) of the instrument.
        Assumes data has 'high', 'low', and 'close' columns.
        """
        data = data.copy()
        data['H-L'] = data['high'] - data['low']
        data['H-PC'] = abs(data['high'] - data['close'].shift(1))
        data['L-PC'] = abs(data['low'] - data['close'].shift(1))
        data['TR'] = data[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        atr = data['TR'].rolling(window=window).mean()
        return atr

    def RSI(self, data, window=14):
        """
        Compute the Relative Strength Index.
        """
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    # -------------------------------
    # Dynamic Sizing Functions
    # -------------------------------
    def calculate_signal_strength_long(self, row, acceleration_threshold):
        """
        For a long signal, if the acceleration is above threshold,
        define signal strength as the ratio (capped at 1).
        """
        if row['Acceleration'] < acceleration_threshold:
            return 0
        ratio = row['Acceleration'] / acceleration_threshold
        return min(ratio, 1)

    def calculate_signal_strength_short(self, row, acceleration_threshold):
        """
        For a short signal, use the absolute acceleration.
        """
        if row['Acceleration'] > -acceleration_threshold:
            return 0
        ratio = abs(row['Acceleration']) / acceleration_threshold
        return min(ratio, 1)

    def calculate_contracts(self, volatility, signal_strength):
        """
        Determine contract size between 1 and 10.
        
        - In high volatility, size is scaled down.
        - In low volatility, size is scaled up.
        - Otherwise, size is based on signal strength.
        """
        base_contracts = int(round(signal_strength * 10))
        base_contracts = max(1, min(base_contracts, 10))
        high_vol_threshold = self.ATR_BASELINE * 1.5
        low_vol_threshold = self.ATR_BASELINE * 0.5

        if volatility > high_vol_threshold:
            adjusted = max(1, base_contracts // 2)
        elif volatility < low_vol_threshold:
            adjusted = min(10, int(round(base_contracts * 1.2)))
        else:
            adjusted = base_contracts
        return adjusted

    def get_allowed_size(self, desired_size, current_total):
        """
        Limit the size by the remaining capacity (global cap 45).
        """
        available = self.MAX_TOTAL_CONTRACTS - current_total
        return max(0, min(desired_size, available))

    # -------------------------------
    # Position Management Functions
    # -------------------------------
    def open_position(self, position_type, entry_point, contracts, holdings):
        """
        Create a new position represented as a dictionary.
        """
        position = {
            'position_type': position_type,
            'entry_price': entry_point,
            'contracts': contracts,        # current number of contracts in this position
            'has_partial_exited': False,   # flag to indicate partial exit occurred
            'trailing_stop': None          # will be set once partial exit is taken
        }
        holdings.append(position)
        return holdings

    def partial_close_position(self, position, cur_price, partial_fraction=0.5):
        """
        Exit a portion of the position.
        Returns realized PnL and number of contracts closed.
        """
        closed_contracts = int(round(position['contracts'] * partial_fraction))
        if closed_contracts < 1:
            closed_contracts = 1
        if position['position_type'] == 'LONG':
            realized_pnl = (cur_price - position['entry_price']) * closed_contracts - self.TRADING_FEE * closed_contracts
        else:  # SHORT
            realized_pnl = (position['entry_price'] - cur_price) * closed_contracts - self.TRADING_FEE * closed_contracts
        position['contracts'] -= closed_contracts
        position['has_partial_exited'] = True
        if position['position_type'] == 'LONG':
            position['trailing_stop'] = position['entry_price'] + self.TRADING_FEE
        else:
            position['trailing_stop'] = position['entry_price'] - self.TRADING_FEE
        return realized_pnl, closed_contracts

    def close_full_position(self, position, cur_price):
        """
        Fully exit the position.
        """
        contracts = position['contracts']
        if position['position_type'] == 'LONG':
            realized_pnl = (cur_price - position['entry_price']) * contracts - self.TRADING_FEE * contracts
        else:
            realized_pnl = (position['entry_price'] - cur_price) * contracts - self.TRADING_FEE * contracts
        return realized_pnl, contracts

    def update_trailing_stop(self, position, cur_price, trail_distance):
        """
        For LONG: move stop upward if (cur_price - trail_distance) exceeds current trailing stop.
        For SHORT: move stop downward if (cur_price + trail_distance) is lower than current trailing stop.
        """
        if position['position_type'] == 'LONG':
            new_stop = cur_price - trail_distance
            if new_stop > position['trailing_stop']:
                position['trailing_stop'] = new_stop
        else:
            new_stop = cur_price + trail_distance
            if new_stop < position['trailing_stop']:
                position['trailing_stop'] = new_stop
        return position

    # -------------------------------
    # Condition Functions
    # -------------------------------
    def check_long_position_conditions(self, row, acceleration_threshold, quantity_multiply, sma_gap, short_acceleration_threshold, rsi_threshold):
        conditions = [
            row['Acceleration'] > acceleration_threshold,
            row['VN30 Acceleration'] > 0,
            row['volume'] > row['Average Quantity'] * quantity_multiply,
            row['Price/SMA'] < 1 - sma_gap,
            row['Short Acceleration'] > short_acceleration_threshold,
            row['RSI'] < 50 - rsi_threshold
        ]
        # Allow at most one condition to fail
        return conditions.count(True) >= len(conditions) - 1

    def check_short_position_conditions(self, row, acceleration_threshold, quantity_multiply, sma_gap, short_acceleration_threshold, rsi_threshold):
        conditions = [
            row['Acceleration'] < -acceleration_threshold,
            row['VN30 Acceleration'] < 0,
            row['volume'] > row['Average Quantity'] * quantity_multiply,
            row['Price/SMA'] > 1 + sma_gap,
            row['Short Acceleration'] < -short_acceleration_threshold,
            row['RSI'] > 50 + rsi_threshold
        ]
        # Allow at most two conditions to fail
        return conditions.count(True) >= len(conditions) - 2

    # -------------------------------
    # Main Backtesting Function
    # -------------------------------
    def run(self, trading_data, params, asset_value=10000):
        """
        Run the backtesting strategy using the provided trading data and parameter dictionary.
        
        The params dictionary should contain:
            - sma_window_length
            - sma_gap
            - momentum_lookback
            - acceleration_threshold
            - short_acceleration_threshold
            - take_profit_threshold
            - cut_loss_threshold
            - quantity_window
            - quantity_multiply
            - short_extra_profit
            - rsi_window
            - rsi_threshold
        """
        # Extract parameters from the dictionary.
        sma_window_length = params.get("sma_window_length")
        sma_gap = params.get("sma_gap")
        momentum_lookback = params.get("momentum_lookback")
        acceleration_threshold = params.get("acceleration_threshold")
        short_acceleration_threshold = params.get("short_acceleration_threshold")
        take_profit_threshold = params.get("take_profit_threshold")
        cut_loss_threshold = params.get("cut_loss_threshold")
        quantity_window = params.get("quantity_window")
        quantity_multiply = params.get("quantity_multiply")
        short_extra_profit = params.get("short_extra_profit")
        rsi_window = params.get("rsi_window")
        rsi_threshold = params.get("rsi_threshold")
        
        trading_data = trading_data.copy()  
        trading_data['SMA'] = trading_data['close'].rolling(sma_window_length).mean()
        trading_data['Price/SMA'] = trading_data['close'] / trading_data['SMA']
        trading_data['Average Quantity'] = trading_data['volume'].rolling(quantity_window).mean()
        trading_data['Acceleration'] = trading_data['close'] - trading_data['close'].shift(momentum_lookback)
        trading_data['Short Acceleration'] = trading_data['close'] - trading_data['close'].shift(1)
        trading_data['VN30 Acceleration'] = trading_data['vn30'] - trading_data['vn30'].shift(momentum_lookback)
        trading_data['RSI'] = self.RSI(trading_data, rsi_window)
        trading_data['ATR'] = self.ATR(trading_data, window=14)
        trading_data.dropna(inplace=True)

        holdings = []              # list of open positions
        total_open_contracts = 0    # global count of contracts currently held
        cumulative_pnl = 0

        trading_data['Asset'] = asset_value
        trading_data['PNL'] = 0
        trading_data['Cumulative PNL'] = 0
        trading_data['Position'] = None
        trading_data['Entry Price'] = None

        asset_history = []
        pnl_history = []
        cumulative_pnl_history = []

        for i in tqdm(range(len(trading_data))):
            total_realized_pnl = 0
            cur_price = trading_data['close'].iloc[i]
            row = trading_data.iloc[i]
            current_atr = row['ATR']  # current volatility measure
            baseline = self.ATR_BASELINE

            # -------------------------
            # EXIT STRATEGY
            # -------------------------
            for pos in holdings[:]:
                if pos['position_type'] == 'LONG':
                    if cur_price < pos['entry_price'] - cut_loss_threshold:
                        pnl, closed = self.close_full_position(pos, cur_price)
                        total_realized_pnl += pnl
                        total_open_contracts -= closed
                        holdings.remove(pos)
                        continue
                    if cur_price >= pos['entry_price'] + take_profit_threshold and not pos['has_partial_exited']:
                        pnl, closed = self.partial_close_position(pos, cur_price, partial_fraction=0.5)
                        total_realized_pnl += pnl
                        total_open_contracts -= closed
                        pos['trailing_stop'] = pos['entry_price'] + take_profit_threshold
                    if pos['has_partial_exited'] and pos['trailing_stop'] is not None and cur_price < pos['trailing_stop']:
                        pnl, closed = self.close_full_position(pos, cur_price)
                        total_realized_pnl += pnl
                        total_open_contracts -= closed
                        holdings.remove(pos)
                        continue
                    if pos['has_partial_exited'] and pos['trailing_stop'] is not None:
                        trail_distance = self.TRAIL_MULTIPLIER * current_atr
                        pos = self.update_trailing_stop(pos, cur_price, trail_distance)

                if pos['position_type'] == 'SHORT':
                    if cur_price > pos['entry_price'] + cut_loss_threshold:
                        pnl, closed = self.close_full_position(pos, cur_price)
                        total_realized_pnl += pnl
                        total_open_contracts -= closed
                        holdings.remove(pos)
                        continue
                    if cur_price <= pos['entry_price'] - (take_profit_threshold + short_extra_profit) and not pos['has_partial_exited']:
                        pnl, closed = self.partial_close_position(pos, cur_price, partial_fraction=0.5)
                        total_realized_pnl += pnl
                        total_open_contracts -= closed
                        pos['trailing_stop'] = pos['entry_price'] - take_profit_threshold
                    if pos['has_partial_exited'] and pos['trailing_stop'] is not None and cur_price > pos['trailing_stop']:
                        pnl, closed = self.close_full_position(pos, cur_price)
                        total_realized_pnl += pnl
                        total_open_contracts -= closed
                        holdings.remove(pos)
                        continue
                    if pos['has_partial_exited'] and pos['trailing_stop'] is not None:
                        trail_distance = self.TRAIL_MULTIPLIER * current_atr
                        pos = self.update_trailing_stop(pos, cur_price, trail_distance)

            asset_value += total_realized_pnl
            cumulative_pnl += total_realized_pnl
            asset_history.append(asset_value)
            pnl_history.append(total_realized_pnl)
            cumulative_pnl_history.append(cumulative_pnl)

            # -------------------------
            # ENTRY STRATEGY
            # -------------------------
            if self.check_long_position_conditions(row, acceleration_threshold, quantity_multiply, sma_gap, short_acceleration_threshold, rsi_threshold):
                if holdings and holdings[0]['position_type'] == 'SHORT':
                    pass
                else:
                    signal_strength = self.calculate_signal_strength_long(row, acceleration_threshold)
                    desired_contracts = self.calculate_contracts(current_atr, signal_strength)
                    existing_long = None
                    for pos in holdings:
                        if pos['position_type'] == 'LONG':
                            existing_long = pos
                            break
                    if existing_long:
                        current_trade_contracts = existing_long['contracts']
                        additional_desired = desired_contracts
                        allowed_additional = self.get_allowed_size(additional_desired, total_open_contracts)
                        if current_trade_contracts + allowed_additional > 10:
                            allowed_additional = 10 - current_trade_contracts
                        if allowed_additional > 0:
                            existing_long['contracts'] += allowed_additional
                            total_open_contracts += allowed_additional
                    else:
                        allowed = self.get_allowed_size(desired_contracts, total_open_contracts)
                        if allowed > 0:
                            holdings = self.open_position('LONG', cur_price, allowed, holdings)
                            total_open_contracts += allowed

            if self.check_short_position_conditions(row, acceleration_threshold, quantity_multiply, sma_gap, short_acceleration_threshold, rsi_threshold):
                if holdings and holdings[0]['position_type'] == 'LONG':
                    pass
                else:
                    signal_strength = self.calculate_signal_strength_short(row, acceleration_threshold)
                    desired_contracts = self.calculate_contracts(current_atr, signal_strength)
                    existing_short = None
                    for pos in holdings:
                        if pos['position_type'] == 'SHORT':
                            existing_short = pos
                            break
                    if existing_short:
                        current_trade_contracts = existing_short['contracts']
                        additional_desired = desired_contracts
                        allowed_additional = self.get_allowed_size(additional_desired, total_open_contracts)
                        if current_trade_contracts + allowed_additional > 10:
                            allowed_additional = 10 - current_trade_contracts
                        if allowed_additional > 0:
                            existing_short['contracts'] += allowed_additional
                            total_open_contracts += allowed_additional
                    else:
                        allowed = self.get_allowed_size(desired_contracts, total_open_contracts)
                        if allowed > 0:
                            holdings = self.open_position('SHORT', cur_price, allowed, holdings)
                            total_open_contracts += allowed

            if holdings:
                trading_data.at[trading_data.index[i], 'Position'] = holdings[0]['position_type']
                trading_data.at[trading_data.index[i], 'Entry Price'] = holdings[0]['entry_price']
            else:
                trading_data.at[trading_data.index[i], 'Position'] = None
                trading_data.at[trading_data.index[i], 'Entry Price'] = None

        trading_data['Asset'] = asset_history
        trading_data['PNL'] = pnl_history
        trading_data['Cumulative PNL'] = cumulative_pnl_history

        return trading_data

backtesting = Backtesting()