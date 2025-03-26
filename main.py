from data.service import *

# Instantiate the DataService.
data_service = DataService()
print(data_service.get_data('2023-01-01', '2023-12-31'))

