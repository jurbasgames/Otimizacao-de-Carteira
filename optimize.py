import pandas as pd
from pulp import LpMaximize, LpProblem, LpVariable, lpSum, LpStatus, LpContinuous, PULP_CBC_CMD


def main():

    caminho_csv = 'dados_fundamentus.csv'
    df = pd.read_csv(caminho_csv, sep=';')

    df_clean = df.dropna()

    df_clean = df_clean[(df_clean['ROE'] >= 0) & (df_clean['P/L'] >= 0)]

    df_clean = df_clean[df_clean['Rendimento_12m'] <= 100]

    print("\nDados após limpeza:")
    print(df_clean.describe())

    prob = LpProblem("Selecao_de_Portfolio", LpMaximize)

    tickers = df_clean['Ticker'].tolist()

    x = LpVariable.dicts('Proporcao', tickers, lowBound=0,
                         upBound=0.2, cat=LpContinuous)

    prob += lpSum([df_clean.loc[df_clean['Ticker'] == ticker, 'Rendimento_12m'].values[0]
                  * x[ticker] for ticker in tickers]), "Rendimento_Total"

    prob += lpSum([x[ticker] for ticker in tickers]) == 1, "Soma_Proporcoes"

    prob += lpSum([df_clean.loc[df_clean['Ticker'] == ticker, 'ROE'].values[0]
                  * x[ticker] for ticker in tickers]) >= 6, "ROE_Minimo"

    prob += lpSum([df_clean.loc[df_clean['Ticker'] == ticker, 'P/L'].values[0]
                  * x[ticker] for ticker in tickers]) <= 12, "PL_Maximo"

    prob += lpSum([df_clean.loc[df_clean['Ticker'] == ticker, 'Dividend_Yield'].values[0]
                  * x[ticker] for ticker in tickers]) >= 18, "Dividend_Yield_Minimo"

    prob.solve(PULP_CBC_CMD(msg=True))

    print(f"Status da Solução: {LpStatus[prob.status]}")

    if LpStatus[prob.status] == 'Optimal':

        acoes_selecionadas = [
            ticker for ticker in tickers if x[ticker].varValue > 0]

        df_selecionadas = df_clean[df_clean['Ticker'].isin(
            acoes_selecionadas)].copy()

        df_selecionadas['Proporcao'] = df_selecionadas['Ticker'].apply(
            lambda ticker: x[ticker].varValue)

        print("\n")
        print(df_selecionadas[['Ticker', 'Proporcao', 'ROE',
              'P/L', 'Dividend_Yield', 'Rendimento_12m']])

        total_roe = sum(df_selecionadas['ROE'] * df_selecionadas['Proporcao'])
        total_pl = sum(df_selecionadas['P/L'] * df_selecionadas['Proporcao'])
        total_dividend_yield = sum(
            df_selecionadas['Dividend_Yield'] * df_selecionadas['Proporcao'])
        total_rendimento = sum(
            df_selecionadas['Rendimento_12m'] * df_selecionadas['Proporcao'])

        print("\nTotais da Carteira:")
        print(f"ROE Total: {total_roe:.2f}%")
        print(f"P/L Total: {total_pl:.2f}")
        print(f"Dividend Yield Total: {total_dividend_yield:.2f}%")
        print(f"Rendimento Total: {total_rendimento:.2f}%")

        output_excel = 'acoes_selecionadas_portfolio.xlsx'
        df_selecionadas.to_excel(output_excel, index=False)
        print(f"\nAções selecionadas foram exportadas para '{output_excel}'.")
    else:
        print("A solução não é ótima. Verifique as restrições e os dados.")


if __name__ == "__main__":
    main()
