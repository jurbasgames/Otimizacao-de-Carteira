import pandas as pd
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpBinary, PULP_CBC_CMD, LpStatus


def main():
    # Carregar os dados
    caminho_csv = 'dados_fundamentus.csv'
    df = pd.read_csv(caminho_csv, sep=';')

    # Limpar os dados: remover linhas com dados faltantes
    df_clean = df.dropna()

    # Filtrar ações com ROE e P/L positivos
    df_clean = df_clean[(df_clean['ROE'] >= 0) & (df_clean['P/L'] >= 0)]

    # Opcional: Remover ações com Rendimento_12m acima de 100%
    df_clean = df_clean[df_clean['Rendimento_12m'] <= 100]

    # Verificar novamente
    print("\nDados após limpeza:")
    print(df_clean.describe())

    # Definir o problema de otimização
    prob = LpProblem("Selecao_de_Portfolio", LpMaximize)

    # Lista de tickers
    tickers = df_clean['Ticker'].tolist()

    # Criação das variáveis de decisão (0 ou 1)
    x = LpVariable.dicts('Selecionar', tickers, cat=LpBinary)

    # Definir o rendimento esperado (objetivo)
    prob += lpSum([df_clean.loc[df_clean['Ticker'] == ticker, 'Rendimento_12m'].values[0]
                  * x[ticker] for ticker in tickers]), "Rendimento_Total"

    # Restrições

    # 1. Selecionar exatamente 10 ações
    prob += lpSum([x[ticker] for ticker in tickers]
                  ) <= 20, "Numero_Total_de_Acoes"

    # 2. Soma dos ROEs das ações selecionadas ≥ 6%
    prob += lpSum([df_clean.loc[df_clean['Ticker'] == ticker, 'ROE'].values[0]
                  * x[ticker] for ticker in tickers]) >= 6, "ROE_Minimo"

    # 3. Soma dos P/Ls das ações selecionadas ≤ 40
    prob += lpSum([df_clean.loc[df_clean['Ticker'] == ticker, 'P/L'].values[0]
                  * x[ticker] for ticker in tickers]) <= 40, "PL_Maximo"

    # 4. Soma dos Dividend Yields das ações selecionadas ≥ 3%
    prob += lpSum([df_clean.loc[df_clean['Ticker'] == ticker, 'Dividend_Yield'].values[0]
                  * x[ticker] for ticker in tickers]) >= 3, "Dividend_Yield_Minimo"

    # Resolver o problema
    prob.solve(PULP_CBC_CMD(msg=True))

    # Verificar o status da solução
    print(f"Status da Solução: {LpStatus[prob.status]}")

    if LpStatus[prob.status] == 'Optimal':
        # Lista das ações selecionadas
        acoes_selecionadas = [
            ticker for ticker in tickers if x[ticker].varValue == 1]

        # Filtrar o DataFrame para mostrar apenas as ações selecionadas
        df_selecionadas = df_clean[df_clean['Ticker'].isin(acoes_selecionadas)]

        # Exibir as ações selecionadas
        print("\nAções Selecionadas para a Carteira:")
        print(df_selecionadas[['Ticker', 'ROE', 'P/L',
              'Dividend_Yield', 'Rendimento_12m']])

        # Calcular o rendimento total da carteira
        rendimento_total = df_selecionadas['Rendimento_12m'].sum()
        print(f"\nRendimento Total da Carteira: {rendimento_total}%")

        # Exportar as ações selecionadas para um arquivo Excel
        output_excel = 'acoes_selecionadas_portfolio.xlsx'
        df_selecionadas.to_excel(output_excel, index=False)
        print(f"\nAções selecionadas foram exportadas para '{output_excel}'.")
    else:
        print("A solução não é ótima. Verifique as restrições e os dados.")


if __name__ == "__main__":
    main()
