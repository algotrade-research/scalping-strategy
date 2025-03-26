import psycopg2
import pandas as pd
from data.query import MATCHED_VOLUME_QUERY
# from config import config
from ssi_fc_data import fc_md_client, model
from config.config import *
from config import config_vn30_data as config
from datetime import datetime

def test():
    print("Test successful")

class DataService:
    def __init__(self) -> None:
        # Initialize the database connection if parameters are provided.
        try:
            self.connection = psycopg2.connect(**DB_PARAMS)
            self.is_file = False
        except Exception as e:
            print(f"Database connection failed: {e}")
            self.connection = None
            self.is_file = True
        
        # Instantiate the market data client for VN30 data.
        self.vn30_client = fc_md_client.MarketDataClient(config)
        print("DataService initialized")

    def get_vn30_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch VN30 intraday OHLC data for the period between start_date and end_date.
        The start_date and end_date should be strings in "dd/mm/yyyy" format.
        
        The function splits the overall period by month (using fixed rules for month-end days)
        and then concatenates the data from each segment.
        """
        
        # Convert input strings from "yyyy-mm-dd" to "dd/mm/yyyy".
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").strftime("%d/%m/%Y")
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        data_list = []

        # Iterate from the starting month/year to the ending month/year.
        current_year = start_dt.year
        current_month = start_dt.month

        while (current_year < end_dt.year) or (current_year == end_dt.year and current_month <= end_dt.month):
            # Determine the starting day for the current segment.
            day_start = start_dt.day if (current_year == start_dt.year and current_month == start_dt.month) else 1

            # Set the month's maximum day based on fixed rules.
            if current_month == 2:
                max_day = 28
            elif current_month in [4, 6, 9, 11]:
                max_day = 30
            else:
                max_day = 31

            # If this is the ending month, adjust the end day.
            day_end = end_dt.day if (current_year == end_dt.year and current_month == end_dt.month) else max_day

            # Format the date strings in "dd/mm/yyyy".
            month_str = str(current_month).zfill(2)
            seg_start_date = f"{str(day_start).zfill(2)}/{month_str}/{current_year}"
            seg_end_date = f"{str(day_end).zfill(2)}/{month_str}/{current_year}"

            # Fetch the VN30 data for this monthly segment.
            result = self.vn30_client.intraday_ohlc(
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
                
        
        vn30 = pd.concat(data_list, ignore_index=True)
                
        #combine TradingDate and Time to datetime
        vn30['datetime'] = pd.to_datetime(vn30['TradingDate'] + ' ' + vn30['Time'], format='%d/%m/%Y %H:%M:%S')
        vn30 = vn30.set_index('datetime')
        vn30 = vn30.drop(['TradingDate', 'Time'], axis=1)
        vn30_data = pd.DataFrame(vn30['Value'])
        # Round the datetime to set the seconds to 0
        vn30_data.index = vn30_data.index.round('1T')

        # Concatenate all segments into a single DataFrame.
        return vn30_data
    
    def execute_query(self, query: str, start_date: str, end_date: str):
        """
        Executes the provided SQL query with start_date and end_date as parameters.
        """
        if self.is_file:
            print("Database connection not available.")
            return None

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, (start_date, end_date))
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            print(f"Error executing query: {e}")
            cursor.close()
            return None

    def get_matched_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Loads matched volume data between start_date and end_date,
        converts it to a DataFrame, and resamples the data to a 1-minute scale.
        """
        print("Loading matched data")
        columns = ["datetime", "Price", "Quantity"]
        query_result = self.execute_query(MATCHED_VOLUME_QUERY, start_date, end_date)
        if query_result is None:
            return pd.DataFrame()  # Return an empty DataFrame if the query fails

        matched_data = pd.DataFrame(query_result, columns=columns)
        matched_data = matched_data.astype({"Price": float})
        print("Loaded matched data")
        
        matched_data['datetime'] = pd.to_datetime(matched_data['datetime'])
        matched_data = matched_data.set_index('datetime')
        matched_data.dropna(inplace=True)
        
        # Resample Price to 1-minute OHLC and Quantity to 1-minute sum.
        price = matched_data['Price'].resample('1T').ohlc().dropna()
        volume = matched_data['Quantity'].resample('1T').sum().dropna()
        data = pd.concat([price, volume], axis=1)
        return data.dropna()

    def get_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Merges the matched volume data with the VN30 data based on their datetime indexes.
        """
        matched_data = self.get_matched_data(start_date, end_date)
        vn30_data = self.get_vn30_data(start_date, end_date)
        # Merge the two dataframes by left join
        data = pd.merge(matched_data, vn30_data, how='left', left_index=True, right_index=True)
        # Rename the columns
        data.columns = ['open', 'high', 'low', 'close', 'volume', 'vn30']
        data.dropna(inplace=True)
        return data
# Instantiate the DataService.
data_service = DataService()

