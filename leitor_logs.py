import pandas as pd
import os
import re
from collections import defaultdict
import datetime as dt
import time


def ler_oferta(arquivo_dados, header: str) -> dict:
    """dado um header, lê as linhas seguintes e retorna as informações da oferta"""

    tipo_oferta = 1 if 'Compra' in header or 'compra' in header else 2
    id_oferta = str(arquivo_dados.readline().split(':')[1].rstrip('\n'))
    comprador = int(arquivo_dados.readline().split(':')[1].rstrip('\n'))
    vendedor = int(arquivo_dados.readline().split(':')[1].rstrip('\n'))
    preco = float(arquivo_dados.readline().split(':')[1])
    volume = float(arquivo_dados.readline().split(':')[1])
    arquivo_dados.readline()  # pulando timestamp
    produto = str(arquivo_dados.readline().split(': ')[1].rstrip('\n'))
    arquivo_dados.readline()  # pulando fechamento das chaves
    preco_forward = float(arquivo_dados.readline().split(':')[1].rstrip('\n')) if 'Avaliando' in header else 0
    params = arquivo_dados.readline() if 'Avaliando' in header else False
    avaliacao_oferta = arquivo_dados.readline() if 'Avaliando' in header else False

    return {'id_oferta': id_oferta,
            'tipo_oferta': tipo_oferta,
            'comprador': comprador,
            'vendedor': vendedor,
            'volume': volume,
            'preco': preco,
            'preco_forward': preco_forward,
            'produto': produto,
            'params': params,
            'avaliacao': avaliacao_oferta}


def editar_oferta(oferta: dict, etapa: int, etapas_periodo: int, recebedor: int):
    """manipula os dados da oferta para adicionar novas informações"""

    if oferta['params']:
        margens = re.split("'percentual': |, 'cps'", oferta['params'])
        margem = -float(margens[1]) if oferta['tipo_oferta'] == 0 else float(margens[3])
    else:
        margem = 0

    oferta['preco_margem'] = oferta['preco_forward'] * (1 + margem)

    if isinstance(oferta['avaliacao'], str) and 'não' not in oferta['avaliacao']:
        avaliacao_oferta = 0  # aceita
    elif isinstance(oferta['avaliacao'], str) and 'não' in oferta['avaliacao']:
        avaliacao_oferta = 1  # recusada
    else:
        avaliacao_oferta = 2  # descartada

    if oferta['tipo_oferta'] == 2:  # oferta de venda
        if oferta['preco_forward'] < oferta['preco'] and avaliacao_oferta == 0:
            status = 1  # aceita por preço
        elif oferta['preco_forward'] > oferta['preco'] and avaliacao_oferta == 0:
            status = 2  # aceita por bonificação
        elif oferta['preco_forward'] > oferta['preco'] and avaliacao_oferta == 1:
            status = 3  # recusada por preço
        elif oferta['preco_forward'] < oferta['preco'] and avaliacao_oferta == 1:
            status = 4  # recusada por penalidade
        else:
            status = 5  # descartada

    else:
        if oferta['preco_forward'] > oferta['preco'] and avaliacao_oferta == 0:
            status = 1
        elif oferta['preco_forward'] < oferta['preco'] and avaliacao_oferta == 0:
            status = 2
        elif oferta['preco_forward'] < oferta['preco'] and avaliacao_oferta == 1:
            status = 3
        elif oferta['preco_forward'] > oferta['preco'] and avaliacao_oferta == 1:
            status = 4
        else:
            status = 5

    oferta['recebedor'] = recebedor

    if oferta['tipo_oferta'] == 1:
        oferta['emissor'] = oferta['comprador'] if oferta['comprador'] != recebedor else oferta['vendedor']
    else:
        oferta['emissor'] = oferta['vendedor'] if oferta['vendedor'] != recebedor else oferta['comprador']

    oferta['status'] = status
    oferta['etapa'] = etapa
    oferta['periodo'] = int(etapa/etapas_periodo) if etapa % etapas_periodo == 0 else int(etapa/etapas_periodo + 1)

    del oferta['avaliacao'], oferta['comprador'], oferta['vendedor'], oferta['params']

    return oferta


def ler_log_modelo(log) -> tuple:
    """lê o log de informações (.txt) da run do modelo e retorna suas datas e número de etapas por período"""

    file = open(log, mode='r', encoding='UTF-8')

    datas = {}
    dia = 1
    num_dias = 1
    etapas_periodo = 2

    line = file.readline()

    while line:
        if line.startswith('Numero dias'):
            num_dias = int(line.split(':')[1].rstrip('\n'))

        if line.startswith('Etapas'):
            etapas_periodo = int(line.split(':')[1].rstrip('\n'))

        if line.startswith('Data Atual'):
            data_atual = line.split(': ')[1].rstrip('\n')
            datas[dia] = data_atual
            dia += num_dias

        line = file.readline()

    return datas, etapas_periodo


def ler_log_agente(log, etapas_periodo: int) -> list:
    """lê o log inteiro (.txt) de um agente e retorna a lista de ofertas dele"""

    file = open(log, mode='r', encoding='UTF-8')
    id_agente = log.rsplit('_', 1)
    id_agente = id_agente[1].rsplit('.')

    lista_ofertas = []
    etapa_atual = 1

    line = file.readline()

    while line:
        if line.startswith('Oferta de') and 'recebida' in line or line.startswith('Avaliando') and 'None' not in line:
            oferta = ler_oferta(file, line)
            oferta = editar_oferta(oferta, etapa_atual, etapas_periodo, id_agente[0])
            lista_ofertas.append(oferta)

        if line.startswith('Fim da etapa'):
            etapa_atual += 1

        line = file.readline()

    file.close()

    return lista_ofertas


def ler_diretorio(pasta) -> tuple:
    """lê o diretório a partir do qual será criado o banco de dados e retorna os arquivos a serem lidos"""

    lista_nomes = os.listdir(pasta)
    logs_agentes, log_modelo = [], []

    for log in lista_nomes:
        if not re.search('model', log):
            logs_agentes.append(pasta + '\\' + log)
        else:
            log_modelo = pasta + '\\' + log

    return logs_agentes, log_modelo


def ler_logs(pasta) -> tuple:
    """lê todos os arquivos necessários do diretório especificado e retorna todas as ofertas"""

    lista_todas_ofertas = []

    lista_logs = ler_diretorio(pasta)[0]
    log_modelo = ler_log_modelo(ler_diretorio(pasta)[1])
    etapas = log_modelo[1]

    for log in lista_logs:
        lista_ofertas = ler_log_agente(log, etapas)

        for oferta in lista_ofertas:
            lista_todas_ofertas.append(oferta)

    return lista_todas_ofertas, log_modelo[0]


def criar_gabarito(pasta):
    """adiciona novas informações ao log do modelo que podem ser usadas na hora de gerar visualizações de dados"""

    log_modelo = ler_diretorio(pasta)[1]
    gabarito = ler_log_modelo(log_modelo)

    return gabarito


def criar_df_ofertas(pasta, path_saida=None):
    """cria um dataframe a partir da lista de ofertas e também cria um csv"""

    inicio = time.perf_counter()

    dict_final = defaultdict(list)
    lista_dicts = ler_logs(pasta)[0]

    for ofertas in lista_dicts:
        for key, value in ofertas.items():
            dict_final[key].append(value)

    df_final = pd.DataFrame.from_dict(dict_final).drop_duplicates(['id_oferta'], keep='last')
    del df_final['id_oferta']
    datas = pd.DataFrame(criar_gabarito(pasta)[0].items(), columns=['periodo', 'data']).set_index('periodo')

    if path_saida:
        pasta_saida = pasta.rsplit('reports\\')[-1]
        pasta_saida = fr'{path_saida}\{pasta_saida}'

        if not os.path.exists(pasta_saida):
            os.mkdir(pasta_saida)

        path_ofertas = fr'{pasta_saida}\ofertas.csv'
        df_final.to_csv(path_ofertas)

        path_datas = fr'{pasta_saida}\datas.csv'
        datas.to_csv(path_datas)

    fim = time.perf_counter()
    duracao = round(fim - inicio, 2)

    print(f"""
            Tabela criada,
            data inicial = {datas.iloc[0]['data']},
            data final = {datas.iloc[-1]['data']},
            número de dias = {datas.index[-1]},
            número de ofertas = {len(df_final)},
            arquivos de saída = {path_saida},
            tempo de execução = {dt.timedelta(seconds=duracao)}.""")

    return {'ofertas': df_final, 'gabarito': datas}


def filtrar_dataframe(df,
                      tipo_oferta: int = None,
                      range_volume: range = None,
                      range_preco_oferta: range = None,
                      range_preco_forward: range = None,
                      range_preco_margem: range = None,
                      lista_emissores: list = None,
                      lista_recebedores: list = None,
                      lista_produtos: list = None,
                      range_periodo: range = None,
                      lista_status: list = None):
    """"aplica todos os filtros no dataframe em questão"""

    if tipo_oferta:
        df = df[df['tipo_oferta'] == tipo_oferta]

    if range_volume:
        df = df[df['volume'].isin(range_volume)]

    if range_preco_oferta:
        df = df[df['preco'].isin(range_preco_oferta)]

    if range_preco_forward:
        df = df[df['preco_forward'].isin(range_preco_forward)]

    if range_preco_margem:
        df = df[df['preco_margem'].isin(range_preco_margem)]

    if lista_emissores:
        df = df[df['emissor'].isin(lista_emissores)]

    if lista_recebedores:
        df = df[df['recebedor'].isin(lista_recebedores)]

    if lista_produtos:
        pattern = '|'.join(lista_produtos)
        df = df[df['produto'].str.contains(pattern)]

    if range_periodo:
        df = df[df['periodo'].isin(range_periodo)]

    if lista_status:
        df = df[df['status'].isin(lista_status)]

    return df


def carregar_dataframe(pasta):
    """carrega df de ofertas e de dias para traduzir os períodos"""
    ofertas = pd.read_csv(fr'{pasta}\ofertas.csv', index_col=[0]).reset_index(drop=True)
    dias = pd.read_csv(fr'{pasta}\datas.csv').set_index('periodo')

    return {'ofertas': ofertas, 'dias': dias}


if __name__ == '__main__':
    path_logs = r'path_logs'
    path_resultado = r'path_resultado'

    test = criar_df_ofertas(path_logs, path_resultado)
