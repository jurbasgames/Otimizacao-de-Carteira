import csv
import logging
import time
from bs4 import BeautifulSoup
import requests
import pandas as pd


def ler_acoes_csv(caminho_arquivo='IBXXDia_12-11-24.csv'):
    """Lê o arquivo CSV e retorna uma lista de ações."""
    acoes = []
    with open(caminho_arquivo, newline='', encoding='latin-1') as arquivo_csv:
        leitor_csv = csv.reader(arquivo_csv, delimiter=';')
        for indice, linha in enumerate(leitor_csv):
            if indice >= 2 and indice < 102:
                print(linha[0])
                acoes.append(linha[0])
    return acoes


def converter_valor(valor):
    """Converte string para float, removendo símbolos e ajustando formatação."""
    if valor is None:
        return None
    valor = valor.replace('%', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(valor)
    except ValueError:
        return None


def coletar_dados_fundamentus(acao):
    url = f'https://www.fundamentus.com.br/detalhes.php?papel={acao}'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
                      'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                      'Chrome/58.0.3029.110 Safari/537.3'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao acessar a URL para a ação {acao}: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    tabelas = soup.find_all('table')

    if len(tabelas) < 3:
        logging.warning(f"Menos de 3 tabelas encontradas para a ação {acao}.")
        return None

    terceira_tabela = tabelas[2]

    dados = {}

    for tr in terceira_tabela.find_all('tr'):
        tds = tr.find_all('td')
        for i in range(0, len(tds), 2):
            if i+1 >= len(tds):
                continue
            label_td = tds[i]
            data_td = tds[i+1]

            label_span = label_td.find('span', class_='txt')
            if label_span:
                label = label_span.text.strip().lower()
            else:
                label = label_td.text.strip().lower()

            data_span = data_td.find('span', class_='txt')
            if data_span:
                valor = data_span.text.strip()
            else:
                valor = data_td.text.strip()

            if label == 'roe':
                dados['ROE'] = converter_valor(valor)
            elif label == 'p/l':
                dados['P/L'] = converter_valor(valor)
            elif 'div. yield' in label:
                dados['Dividend_Yield'] = converter_valor(valor)
            elif '12 meses' in label:
                dados['Rendimento_12m'] = converter_valor(valor)

    campos_necessarios = ['ROE', 'P/L', 'Dividend_Yield', 'Rendimento_12m']
    for campo in campos_necessarios:
        if campo not in dados:
            dados[campo] = None
            logging.warning(
                f"Campo '{campo}' não encontrado para a ação {acao}.")

    if not all(key in dados and dados[key] is not None for key in campos_necessarios):
        logging.info(
            f"Nem todos os dados foram encontrados para a ação {acao}. Dados encontrados: {dados}")

    return dados


def coletar_dados_com_retry(acao, tempo_total=300, intervalo=5):
    """
    Coleta dados para uma ação com retries até um tempo total de 5 minutos.

    Parâmetros:
    - acao (str): Código da ação.
    - tempo_total (int): Tempo máximo de espera em segundos (default: 300 segundos).
    - intervalo (int): Intervalo entre tentativas em segundos (default: 5 segundos).

    Retorna:
    - dict: Dados coletados ou None em caso de falha.
    """
    inicio = time.time()
    while time.time() - inicio < tempo_total:
        dados = coletar_dados_fundamentus(acao)
        if dados:
            return dados
        else:
            logging.info(
                f"Tentativa falhou para a ação {acao}. Tentando novamente em {intervalo} segundos...")
            time.sleep(intervalo)
    logging.error(
        f"Falha na coleta dos dados para a ação {acao} após {tempo_total} segundos.")
    raise TimeoutError(
        f"Falha na coleta dos dados para a ação {acao} após {tempo_total} segundos.")


def coletar_dados_para_muitos_tickers(lista_tickers, pausa=1):
    """
    Coleta dados para uma lista de tickers.

    Parâmetros:
    - lista_tickers (list): Lista de códigos de ações.
    - pausa (int): Tempo de pausa em segundos entre requisições.

    Retorna:
    - list: Lista de dicionários contendo os dados coletados.
    """
    resultados = []
    erros = []
    for acao in lista_tickers:
        try:
            logging.info(f"Iniciando coleta para {acao}...")
            dados = coletar_dados_com_retry(acao)
            if dados:
                dados['Ticker'] = acao
                resultados.append(dados)
                logging.info(
                    f"Dados coletados com sucesso para a ação {acao}.")
        except TimeoutError as e:
            erros.append({'Ticker': acao, 'Erro': str(e)})
            logging.error(f"Erro ao coletar dados para a ação {acao}: {e}")

        time.sleep(pausa)
    return resultados, erros


def main():
    logging.basicConfig(
        filename='scraping_fundamentus.log',
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s'
    )

    caminho_csv = 'IBXXDia_12-11-24.csv'
    acoes = ler_acoes_csv(caminho_csv)
    logging.info(f"Total de ações lidas: {len(acoes)}")

    resultados, erros = coletar_dados_para_muitos_tickers(acoes, pausa=1)

    df_resultados = pd.DataFrame(resultados)

    colunas = ['Ticker', 'ROE', 'P/L', 'Dividend_Yield', 'Rendimento_12m']
    df_resultados = df_resultados[colunas]

    nome_arquivo = 'dados_fundamentus.csv'
    df_resultados.to_csv(nome_arquivo, index=False,
                         encoding='utf-8-sig', sep=';')
    logging.info(f"Dados exportados para '{nome_arquivo}'.")

    if erros:
        df_erros = pd.DataFrame(erros)
        nome_arquivo_erros = 'erros_coleta_fundamentus.csv'
        df_erros.to_csv(nome_arquivo_erros, index=False, encoding='utf-8-sig')
        logging.info(f"Erros registrados em '{nome_arquivo_erros}'.")
        print(
            f"Algumas ações não tiveram seus dados coletados. Veja '{nome_arquivo_erros}' para detalhes.")
    else:
        print("Todos os dados foram coletados com sucesso.")

    print(f"Dados coletados e salvos em '{nome_arquivo}'.")


if __name__ == "__main__":
    main()
