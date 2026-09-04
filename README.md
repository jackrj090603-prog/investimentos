# Ceará Finance — Plataforma Integrada de Valuations & Equity Research

Plataforma quantitativa e fundamentalista desenvolvida para análise de mercado de capitais, automação de equity research, monitoramento de comunicados da CVM e estratégias sistemáticas de backtest (B3 vs CDI).

---

## 🏛️ Arquitetura Modular Multi-Sites (Alta Performance)

O sistema opera de forma descentralizada em micro-dashboards independentes com cache em RAM dedicado, eliminando gargalos de processamento e travamentos de interface:

| Aplicação | Porta Local | Descrição |
| :--- | :---: | :--- |
| 🌐 **Portal Central (Hub)** | `8000` | Landing page institucional com acesso rápido, identidade visual oficial e status dos serviços. |
| 🤖 **Alertas & Consultas CVM** | `8001` | Monitoramento regulatório em tempo real via SQLite (Fatos Relevantes, Comunicados ao Mercado e DFP/ITR). |
| 📊 **Monitor de Valuation (Mira)** | `8002` | Planilha interativa com cache em memória RAM e filtros dinâmicos estilo Excel (Graham, Bazin, P/L, ROE, DY). |
| 📋 **Equity Research & Demonstrativos** | `8003` | Lâminas de tese no modelo Poli USP e séries financeiras históricas de 5 anos (DRE, Balanço BPA/BPP e DFC). |
| 🏛️ **Workstation Gregori Markets** | `8004` | Terminal quantitativo e interface analítica de mercado financeiro integrada. |
| ⚙️ **CF Tech Valuation Pipelines** | `8005` | Motor de WACC Beta OLS, DCF com crescimento perpétuo, simulação de Monte Carlo vetorial e auditoria de riscos via IA. |
| 🛡️ **Aegis Momentum Backtest** | `8501` | Laboratório Streamlit de estratégias quantitativas Momentum Long-Short comparadas contra o CDI. |

---

## 🚀 Como Executar o Ecossistema

### 1. Pré-requisitos
- Python 3.10 ou superior instalado no Windows.
- Dependências instaladas:
```bash
pip install pandas numpy yfinance matplotlib seaborn streamlit requests beautifulsoup4 openpyxl lxml markdown telethon pyyaml pyarrow tabulate
```

### 2. Configuração de Variáveis de Ambiente
Copie o modelo de configuração e adicione suas credenciais:
```bash
cp agente_cvm/.env.example agente_cvm/.env
```
Edite o arquivo `agente_cvm/.env` com:
- `GEMINI_API_KEY`: Sua chave de API do Google AI Studio.
- `TELEGRAM_BOT_TOKEN`: Token do bot criado via BotFather.
- `TELEGRAM_CHAT_ID_ALERTAS`: ID do canal do Telegram para notificações de fatos relevantes.

### 3. Inicialização Rápida
- **Opção 1 (Duplo Clique no Windows)**: Execute o arquivo `iniciar_sistema.bat`.
- **Opção 2 (Via Terminal)**:
```bash
python iniciar_todos_sites.py
```
O script fará a liberação de portas, iniciará todos os 7 servidores e exibirá o status de conexão. Em seguida, acesse:
👉 **[http://localhost:8000](http://localhost:8000)**

### 4. Parar Todos os Serviços
Para finalizar todos os processos de background e liberar as portas:
```bash
python parar_todos_sites.py
```

---

## 📈 Metodologias e Modelagem Financeira

1. **Custo de Capital Próprio e de Terceiros (WACC)**:
   - Beta alavancado e desalavancado via OLS contra o Ibovespa (`^BVSP`).
   - Custo de capital próprio via CAPM com Prêmio de Risco de Mercado (MRP).
   - Ajuste de benefício fiscal do imposto de renda e contribuição social (34%).

2. **Fluxo de Caixa Descontado (DCF)**:
   - Projeções explícitas de 5 anos a partir do histórico LTM consolidado CVM.
   - Valor terminal estimado pelo método de crescimento perpétuo de Gordon.

3. **Simulação de Monte Carlo**:
   - 10.000 iterações com distribuições estocásticas nas variáveis-chave (crescimento de receita, margem EBIT e WACC).
   - Cálculo de intervalos de confiança (P10, P50, P90) e probabilidade de upside.

4. **Modelos Clássicos de Preço-Teto**:
   - **Fórmula de Graham**: $V = \sqrt{22.5 \times LPA \times VPA}$
   - **Método de Décio Bazin**: Preço Teto para rendimento mínimo de dividendos de 6% ao ano ($DPA / 0.06$).

5. **Aegis Momentum Long-Short**:
   - Seleção de carteira comprada nos maiores momentum de 12 meses e vendida nos menores momentum da B3.
   - Rebalanceamento periódico com cálculo de Sharpe Ratio, Maximum Drawdown e Alfa vs CDI.

---

## 🛡️ Segurança & Boas Práticas
- Arquivos sensíveis como `.env`, bases de dados locais `.db` e sessões do Telegram (`*.session`) estão configurados no `.gitignore` para não serem rastreados nem enviados ao repositório público.

---

## 👥 Realização
**Ceará Finance** • Liga Acadêmica de Mercado Financeiro da UFC
