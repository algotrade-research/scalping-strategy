from ssi_fc_data import fc_md_client , model
import config.config as config
import pandas as pd
from datetime import datetime

def get_vn30_data(start_date, end_date):
    """
    Fetch VN30 intraday OHLC data for the period between start_date and end_date.
    The start_date and end_date should be strings in "dd/mm/yyyy" format.
    
    The function splits the overall period by month (using fixed rules for month-end days,
    e.g. February is forced to 28 days, and April, June, September, and November to 30 days)
    and then concatenates the data from each segment.
    """

    # Instantiate the client (assumes config and model are available in scope)
    client = fc_md_client.MarketDataClient(config)
    
    # Convert the input strings to datetime objects.
    start_dt = datetime.strptime(start_date, "%d/%m/%Y")
    end_dt = datetime.strptime(end_date, "%d/%m/%Y")
    
    data_list = []
    
    # Start iteration from the month/year of start_dt to the month/year of end_dt.
    current_year = start_dt.year
    current_month = start_dt.month

    while (current_year < end_dt.year) or (current_year == end_dt.year and current_month <= end_dt.month):
        # Determine the starting day for this month:
        if current_year == start_dt.year and current_month == start_dt.month:
            day_start = start_dt.day
        else:
            day_start = 1

        # By default, set the month's end day based on the original logic:
        # February -> 28, April/June/Sept/Nov -> 30, all others -> 31.
        if current_month == 2:
            max_day = 28
        elif current_month in [4, 6, 9, 11]:
            max_day = 30
        else:
            max_day = 31

        # If this is the ending month, adjust the end day to the provided end date.
        if current_year == end_dt.year and current_month == end_dt.month:
            day_end = end_dt.day
        else:
            day_end = max_day

        # Build the date strings in "dd/mm/yyyy" format.
        month_str = str(current_month).zfill(2)
        seg_start_date = f"{str(day_start).zfill(2)}/{month_str}/{current_year}"
        seg_end_date = f"{str(day_end).zfill(2)}/{month_str}/{current_year}"
        
        # Fetch data for this monthly segment.
        result = client.intraday_ohlc(
            config,
            model.intraday_ohlc('vn30', seg_start_date, seg_end_date, 1, 9999, True, 1)
        )
        df = pd.DataFrame(result['data'])
        data_list.append(df)
        
        # Move to the next month.
        if current_month == 12:
            current_month = 1
            current_year += 1
        else:
            current_month += 1

    # Concatenate all monthly DataFrames into a single DataFrame.
    data = pd.concat(data_list, ignore_index=True)
    return data
    