# pip install mysql-connector-python
# pip install streamlit -m run dash.py

import mysql.connector
import pandas as pd

def conexao(query):
    conn = mysql.connector.connect(
        host = "127.0.0.1",
        port = "3306",
        user = "root",
        password = "senai@134",
        db = "bd_medidor"
    )

    dataframe = pd.read_sql(query, conn)

    conn.close()

    return dataframe
