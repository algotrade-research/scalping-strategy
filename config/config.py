import json

DB_PARAMS = {
    "host": "api.algotrade.vn",
    "port": 5432,
    "database": "algotradeDB",
    "user": "intern_read_only",
    "password": "ZmDaLzFf8pg5"
}


VN30 = {
    "auth_type": "Bearer",
    "consumerID": "0",
    "consumerSecret": "0",
    "url": "https://fc-data.ssi.com.vn/",
    "stream_url": "https://fc-datahub.ssi.com.vn/"
}

optimization_params = {}
with open("optimization/best_params.json", "r") as of:
    optimization_params = json.load(of)