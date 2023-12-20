# bbce_parser

Parser of BBCE (Brazilian Electricity Trading Agency) historical data, based on the [old API](https://www.bbce.com.br/dados_historicos_agente/) which exported data from energy trade offers in this format:

Trade offer from [REDACTED]: { <br>
Price: 380.07 <br>
id_1: 2 <br>
id_2: 300 <br>
Volume: 1 <br>
}

There were hundreds of .txt files (one per energy trading firm), each one with thousands of trade offers.

Unfortunately the API was changed and I forgot to save a sample to test the code, but hopefully the template helps you understand which problem was being solved.

The output was a dataframe which was loaded into a SQLite database.
