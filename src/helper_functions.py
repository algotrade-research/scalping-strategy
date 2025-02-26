from tqdm import tqdm
import psycopg2
import pandas as pd

# Define weights for each depth
WEIGHTS = {1: 0.5, 2: 0.3, 3: 0.2}
TRADING_FEE = 0.47

# Database connection parameters
DB_PARAMS = {
    "host": "api.algotrade.vn",
    "port": 5432,
    "database": "algotradeDB",
    "user": "intern_read_only",
    "password": "ZmDaLzFf8pg5"
}

BIDSIZE_QUERY = """
    select b.datetime, b.tickersymbol, b.quantity, b.depth 
    from quote.bidsize b 
    join quote.futurecontractcode fc on date(b.datetime) = fc.datetime and fc.tickersymbol = b.tickersymbol
    where fc.futurecode = 'VN30F1M'
        and b.datetime between %s and %s
        and (
            b.datetime::TIME BETWEEN '09:00:00' AND '11:30:00'
            OR b.datetime::TIME BETWEEN '13:00:00' AND '14:30:00'
        )
    order by b.datetime
"""

ASKSIZE_QUERY = """
  select a.datetime, a.tickersymbol, a.quantity, a.depth
  from quote.asksize a 
  join quote.futurecontractcode fc on date(a.datetime) = fc.datetime and fc.tickersymbol = a.tickersymbol
  where fc.futurecode = 'VN30F1M'
    and a.datetime between %s and %s
    and (
        a.datetime::TIME BETWEEN '09:00:00' AND '11:30:00'
        OR a.datetime::TIME BETWEEN '13:00:00' AND '14:30:00'
    )
  order by a.datetime
"""

MATCHED_VOLUME_QUERY = """
  select m.datetime, m.price
  from quote.matched m join quote.matchedvolume v on m.datetime = v.datetime and m.tickersymbol = v.tickersymbol
  join quote.futurecontractcode fc on date(m.datetime) = fc.datetime and fc.tickersymbol = m.tickersymbol
  where fc.futurecode = 'VN30F1M'
    and m.datetime between %s and %s
    and (
        m.datetime::TIME BETWEEN '09:00:00' AND '11:30:00'
        OR m.datetime::TIME BETWEEN '13:00:00' AND '14:30:00'
    )
  order by m.datetime
"""


def execute_query(query, start_date, end_date):
    connection = psycopg2.connect(**DB_PARAMS)
    cursor = connection.cursor()
    try:
        cursor.execute(query, (start_date, end_date))
        result = cursor.fetchall()

        cursor.close()
        connection.close()
        return result

    except Exception as e:
        print(f"Error: {e}")


def get_bid_data(start_date, end_date):
    print("Loading bid data")
    columns = ["datetime", "tickersymbol", "quantity", "depth"]
    dfb = pd.DataFrame(execute_query(
        BIDSIZE_QUERY, start_date, end_date), columns=columns)
    print("Loaded bid data")
    print(dfb)

    dfb = dfb.pivot(
        index='datetime', columns='depth', values='quantity').reset_index()
    dfb.columns = ['datetime', 'bidsize1', 'bidsize2', 'bidsize3']
    dfb = dfb.fillna(method='ffill')
    print("Pivoted bid data")
    print(dfb)

    # Create a new column with the weighted quantity
    dfb['weighted_bid'] = dfb['bidsize1'] * WEIGHTS[1] + \
        dfb['bidsize2'] * WEIGHTS[2] + dfb['bidsize3'] * WEIGHTS[3]
    result_bidz = dfb[['datetime', 'weighted_bid']]
    print("Final bid data")
    print(result_bidz)
    return result_bidz


def get_ask_data(start_date, end_date):
    print("Loading ask data")
    columns = ["datetime", "tickersymbol", "quantity", "depth"]
    dfa = pd.DataFrame(execute_query(
        ASKSIZE_QUERY, start_date, end_date), columns=columns)
    print("Loaded ask data")
    print(dfa)

    dfa = dfa.pivot(
        index='datetime', columns='depth', values='quantity').reset_index()
    dfa.columns = ['datetime', 'asksize1', 'asksize2', 'asksize3']
    dfa = dfa.fillna(method='ffill')
    print("Pivoted ask data")
    print(dfa)

    # Create a new column with the weighted quantity
    dfa['weighted_ask'] = dfa['asksize1'] * WEIGHTS[1] + \
        dfa['asksize2'] * WEIGHTS[2] + dfa['asksize3'] * WEIGHTS[3]
    result_askz = dfa[['datetime', 'weighted_ask']]
    print("Final ask data")
    print(result_askz)
    return result_askz


def get_matched_data(start_date, end_date):
    print("Loading matched data")
    columns = ["datetime", "Price"]
    matched_data = pd.DataFrame(execute_query(
        MATCHED_VOLUME_QUERY, start_date, end_date), columns=columns)
    matched_data = matched_data.astype({"Price": float})
    print("Loaded matched data")
    print(matched_data)
    return matched_data.dropna()


def merge(bid, ask, matched):
    merged_data = pd.merge(bid, ask,
                           on="datetime", how="outer")
    print("Merged bid & ask data")
    print(merged_data)

    merged_data = matched.merge(merged_data, on="datetime", how="outer")
    merged_data = merged_data.fillna(method='ffill')
    print("Merged matched data")
    print(merged_data)

    merged_data['imbalance'] = (merged_data['weighted_bid'] - merged_data['weighted_ask']) / \
        (merged_data['weighted_bid'] + merged_data['weighted_ask'])
    print("Merged data")
    print(merged_data)
    return merged_data

def load_data(start_date, end_date):
    bid = get_bid_data(start_date, end_date)
    ask = get_ask_data(start_date, end_date)
    matched = get_matched_data(start_date, end_date)
    return merge(bid, ask, matched)


def backtesting(data, price_sma_gap, imbalance, take_profit_threshold,
                cut_loss_threshold, sma_window_length, short_window, long_window, signal_window, asset_value=1000):
    trading_data = data.copy()
    trading_data['SMA'] = trading_data['Price'].rolling(
        sma_window_length).mean()
    trading_data['price/sma'] = trading_data['Price'] / trading_data['SMA']
    trading_data['EMA_short_window'] = trading_data['Price'].ewm(span=short_window).mean()
    trading_data['EMA_long_window'] = trading_data['Price'].ewm(span=long_window).mean()
    trading_data['MACD'] = trading_data['EMA_short_window'] - trading_data['EMA_long_window']
    trading_data['signal_line'] = trading_data['MACD'].ewm(span=signal_window).mean()

    holdings = []
    asset_value = asset_value

    cumulative_pnl = 0
    prices = trading_data['Price'].to_numpy()
    price_sma_ratios = trading_data['price/sma'].to_numpy()
    imbalances = trading_data['imbalance'].to_numpy()


    # Preallocate columns for performance
    trading_data['Asset'] = asset_value
    trading_data['PNL'] = 0
    trading_data['Cumulative PNL'] = 0
    trading_data['Position'] = None
    trading_data['Entry Price'] = None

    asset_history = []
    pnl_history = []
    cumulative_pnl_history = []
    
    # loop through data rows
    for i in tqdm(range(len(trading_data))):
        total_realized_pnl = 0
        cur_price = prices[i]
        cur_imbalance = imbalances[i]
        cur_price_sma = price_sma_ratios[i]
        cur_MACD = trading_data['MACD'][i]
        cur_signal_line = trading_data['signal_line'][i]
        # get previous MACD and signal line
        if i == 0:
            cur_MACD_prev = 0
            cur_signal_line_prev = 0
        else:
            cur_MACD_prev = trading_data['MACD'][i-1]
            cur_signal_line_prev = trading_data['signal_line'][i-1]

        # close a LONG position
        if holdings and holdings[0][0] == 'LONG' \
                and (cur_price > holdings[0][1] + take_profit_threshold
                     or cur_price < holdings[0][1] - cut_loss_threshold):
            holdings, total_realized_pnl = close_positions(cur_price, holdings)

        # close a SHORT position
        if holdings and holdings[0][0] == 'SHORT' \
                and (cur_price < holdings[0][1] - take_profit_threshold
                     or cur_price > holdings[0][1] + cut_loss_threshold):
            holdings, total_realized_pnl = close_positions(cur_price, holdings)
        

        # Update asset value
        asset_value += total_realized_pnl
        cumulative_pnl += total_realized_pnl

        asset_history.append(asset_value)
        pnl_history.append(total_realized_pnl)
        cumulative_pnl_history.append(cumulative_pnl)

        # NOTE: open 1 contract only
        if holdings:
            continue

        # open a LONG position
        if cur_imbalance > imbalance and (cur_MACD > cur_signal_line) & (cur_MACD_prev <= cur_signal_line_prev):
            holdings = open_position('LONG', cur_price, holdings)
         

        # open a SHORT position
        if cur_imbalance < -imbalance and (cur_MACD < cur_signal_line) & (cur_MACD_prev >= cur_signal_line_prev):
            holdings = open_position('SHORT', cur_price, holdings)

        # update position history
        if holdings:
            trading_data.at[i, 'Position'] = holdings[0][0]
            trading_data.at[i, 'Entry Price'] = holdings[0][1]

    # Assign precomputed histories to the dataframe
    trading_data['Asset'] = asset_history
    trading_data['PNL'] = pnl_history
    trading_data['Cumulative PNL'] = cumulative_pnl_history
    trading_data['datetime'] = pd.to_datetime(trading_data['datetime'])

    return trading_data


# holdings is a list of on-hold positions
# holdings = [[position_type, price_point], ...]
# e.g. holdings = [['SHORT', 1300.0], ['LONG', 1400.0]]
# open position when there is trading signal. add postion to holdings.
# entry point is the price point at which a position is open.
def open_position(position_type, entry_point, holdings):
    # position-entry-point
    holdings.append([position_type, entry_point])
    return holdings


# close position when there is trading signal. remove postion out of holdings.
def close_positions(cur_price, holdings):
    total_realized_pnl = 0
    cost = TRADING_FEE

    for position_type, entry_point in holdings[:]:
        if position_type == 'LONG':
            realized_pnl = (cur_price - entry_point)

        if position_type == 'SHORT':
            realized_pnl = -(cur_price - entry_point)
        total_realized_pnl += realized_pnl - cost
        holdings.remove([position_type, entry_point])

    # position-exit-point
    return holdings, total_realized_pnl


if __name__ == "__main__":
    from_date = "2023-12-01"
    to_date = "2024-01-01"
    get_bid_data(from_date, to_date)
