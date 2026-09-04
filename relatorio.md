# 🛡️ Relatório Técnico: Aegis Momentum Long-Short na B3

**Time de Tecnologia e Quant — Ceará Finance (UFC)**  
**Estratégia:** Aegis Momentum LS  
**Benchmark:** CDI (100%)  
**Período de Análise:** 2016 – 2026  

---

## 1. Resumo Executivo
Este relatório apresenta os resultados empíricos da estratégia quantitativa de momentum long-short aplicada a ações da B3 (mercado de capitais brasileiro) entre os anos de 2016 e 2026. O objetivo principal do modelo "Aegis Momentum LS" é capturar retornos anômalos persistentes em ativos de média e grande capitalização, utilizando uma perna comprada (Long) nos ativos vencedores e uma perna vendida (Short) nos ativos perdedores, mantendo a neutralidade em caixa colateralizado que rende a taxa diária do CDI.

Após custos de corretagem parametrizados em 10 bps e taxa de aluguel de ações (BTC) de 2% a.a. na perna Short, os resultados revelam que a estratégia gerou retornos acumulados consistentes e estatisticamente superiores ao CDI, com métricas de Sharpe ajustadas ao risco de forma satisfatória e controle rigoroso de rebaixamento pico a vale (drawdown).

---

## 2. Hipótese e Fundamentação Teórica
A anomalia de momentum baseia-se na constatação de que ativos com performance superior nos últimos meses tendem a continuar performando acima da média no curto prazo (3 a 12 meses), enquanto ativos com performance inferior continuam a declinar.

*   **Jegadeesh & Titman (1993):** Em seu artigo pioneiro *"Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency"*, os autores demonstraram que comprar ações com bom desempenho recente e vender ações com mau desempenho gera retornos anômalos (Alpha) estatisticamente significativos no mercado norte-americano. Eles atribuem essa anomalia a fatores comportamentais, como a reação tardia dos investidores a novas informações (underreaction).
*   **NEFIN-USP (Núcleo de Pesquisa em Economia Financeira da USP):** No Brasil, o NEFIN documenta sistematicamente os fatores de risco (Tamanho, Valor, Momentum e Liquidez) para o mercado local. Os dados históricos mostram que, embora o fator momentum na B3 apresente alta volatilidade, ele é um gerador resiliente de excesso de retorno de longo prazo quando exposto de forma Long-Short neutra.

---

## 3. Metodologia Detalhada
O backtest é estruturado com as seguintes regras operacionais:
1.  **Lookback do Sinal:** Período de retorno acumulado de 12 meses (Lookback = 12).
2.  **Defasagem (Lag):** AJanela de sinal termina no mês $t-1$ e o portfólio vigora no mês $t$, prevenindo qualquer viés de antecipação (look-ahead bias) ou utilização de preços simultâneos ao rebalanceamento.
3.  **Composição do Universo:** Reconstruído mensalmente com base na lista de ativos elegíveis do Ibovespa para evitar o viés de sobrevivência.
4.  **Seleção e Pesos:**
    *   **Perna Long:** Top 10 ativos com maior momentum ($1/N$ cada).
    *   **Perna Short:** Bottom 10 ativos com menor momentum ($-1/N$ cada).
5.  **Caixa Colateral:** 100% dos recursos em garantia rendendo a taxa Selic/CDI diária acumulada.
6.  **Custos Friccionais:** Desconto de 10 bps (0.10%) sobre o giro (turnover) total de rebalanceamento mensal e desconto diário equivalente a 2% a.a. na perna Short (BTC).

---

## 4. Vieses e Cuidados
O backtest quantitativo foi construído sob severo rigor para evitar armadilhas comuns:
*   **Sem Look-ahead Bias:** Todas as variáveis de sinal são computadas usando apenas dados estritamente passados em relação à data do rebalanceamento.
*   **Viés de Sobrevivência (Survivorship Bias):** Se a estratégia fosse testada apenas com ativos que compõem o Ibovespa hoje, haveria um viés artificial positivo (pois excluiríamos empresas que faliram ou saíram do índice ao longo dos últimos 10 anos). O script utiliza o histórico mensal de tickers para neutralizar essa distorção.
*   **Custos de Transação e BTC:** O momentum exige rebalanceamentos frequentes. Ignorar custos operacionais causaria um viés de performance irrealista. Incluímos custos de giro e taxa de aluguel no modelo.

---

## 5. Interpretação de Métricas
*   **Alpha Anualizado:** O retorno excedente gerado pela estratégia em relação ao CDI, anualizado. Indica a habilidade do modelo em gerar valor acima do retorno de renda fixa.
*   **Índice Sharpe:** Calculado como:
    $$Sharpe = \frac{E(R_p - R_f)}{\sigma_p}$$
    Onde $R_f$ é a taxa diária do CDI e $\sigma_p$ é o desvio padrão anualizado dos retornos diários do portfólio.
*   **Máximo Drawdown:** A maior queda acumulada do topo ao fundo em toda a série de capital. Essencial para avaliar a tolerância ao risco do investidor.
*   **Teste-T de Student no Alpha:** Avalia a hipótese nula de que o Alpha médio mensal é igual a zero. Um $p$-valor inferior a 5% ($p < 0.05$) rejeita a hipótese nula, comprovando que o excesso de retorno é estatisticamente significante e não fruto do acaso.

---

## 6. Resultados e Análises
A grade de otimização testou múltiplas combinações na base histórica. A rodada padrão ($L=12$ meses, $N=10$ ativos, Long-Short, com custos) apresentou:
- **Retorno Anualizado da Estratégia:** Superior ao CDI de forma consistente.
- **Volatilidade:** Controlada, reflexo do hedge natural proporcionado pela neutralidade da perna Short.
- **Rigor Estatístico:** O teste-t indicou um p-valor menor que 0.05, confirmando a robustez da estratégia Momentum no Brasil.

---

## 7. Uso de IA Generativa no Projeto
A inteligência artificial foi empregada de forma assistiva para:
1.  Escrever o esqueleto de otimização e processamento de dados robusto no Pandas.
2.  Traduzir a complexidade de manipulação de regressões OLS e Hamada para um código modular inteligível.
3.  Auxiliar na formatação estética dos gráficos do matplotlib e do HTML que compila este relatório em PDF.

---

## 8. Limitações e Próximos Passo
*   **Liquidez dos Ativos:** Em períodos de estresse, ativos menores da B3 podem apresentar spreads elevados no book de ofertas, o que pode aumentar os custos friccionais reais acima dos 10 bps modelados.
*   **Custos de Aluguel Dinâmicos:** A taxa de BTC foi fixada em 2% a.a. No entanto, ações que entram em forte tendência de queda (alvos da perna Short) costumam ter suas taxas de aluguel disparadas no mercado de empréstimos.
*   **Próximos Passos:** Implementar filtros de liquidez diária mínima (ex: volume médio diário > R$ 5 mi) e limitar a exposição setorial máxima para evitar concentração excessiva em setores específicos (como commodities ou varejo).
