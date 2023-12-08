# bbce_parser

Parser de logs txt. do BBCE, baseado na [antiga API](https://www.bbce.com.br/dados_historicos_agente/) que exportava dados em um template como:

Oferta de compra do agente 2: { <br>
Preco: 380.07 <br>
id_1: 2 <br>
id_2: 300 <br>
Volume: 1 <br>
}

Infelizmente a API não funciona mais e eu esqueci de salvar um sample enorme para testar o código, então espero que este template pelo menos ajude a entender qual o problema sendo resolvido. O output é um dataframe que era enviado para bancos de dados em SQLite.
