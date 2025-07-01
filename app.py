import os
import shutil
import sys
import logging
from glob import glob
from datetime import datetime
import hashlib
from io import StringIO
import time

import pandas as pd
import yfinance as yf
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="📈 Análise de Momentum",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def check_authentication():
    """Verifica se o usuário está autenticado"""
    return st.session_state.get('authenticated', False)

def authenticate_user(username, password):
    """Autentica o usuário com credenciais do ambiente"""

    env_user = os.getenv('USER')
    env_password = os.getenv('PASSWORD')

    if not env_user or not env_password:
        st.error("❌ Credenciais não configuradas no servidor")
        return False
    
    return username == env_user and password == env_password

def show_login_form():
    """Exibe o formulário de login"""
    st.title("🔐 Login - Análise de Momentum")
    st.markdown("---")
    
    # Centralizar o formulário
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 👤 Acesso ao Sistema")
        
        with st.form("login_form"):
            username = st.text_input("👤 Usuário:", placeholder="Digite seu usuário")
            password = st.text_input("🔒 Senha:", type="password", placeholder="Digite sua senha")
            
            col_login1, col_login2, col_login3 = st.columns([1, 1, 1])
            
            with col_login2:
                login_button = st.form_submit_button("🚀 Entrar", use_container_width=True)
            
            if login_button:
                if not username or not password:
                    st.error("❌ Por favor, preencha todos os campos")
                elif authenticate_user(username, password):
                    st.session_state['authenticated'] = True
                    st.session_state['username'] = username
                    st.success("✅ Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Credenciais inválidas")
                    time.sleep(1)  # Pequena pausa de segurança

def show_logout_button():
    """Exibe botão de logout na sidebar"""
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        # Limpar session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# Configuração de logging customizado para Streamlit
class StreamlitLogHandler(logging.Handler):
    def __init__(self, log_container):
        super().__init__()
        self.log_container = log_container
        self.logs = []
    
    def emit(self, record):
        log_entry = self.format(record)
        
        # Adicionar emoji baseado no nível do log
        emoji_map = {
            'INFO': '📝',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'DEBUG': '🔍'
        }
        
        emoji = emoji_map.get(record.levelname, '📝')
        
        self.logs.append({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'level': record.levelname,
            'emoji': emoji,
            'message': record.getMessage()
        })
        
        # Atualizar o container de logs
        with self.log_container.container():
            for log in self.logs[-10:]:  # Mostrar apenas os últimos 10 logs
                # Usar markdown para formatação correta
                log_color = {
                    'INFO': '#1f77b4',
                    'WARNING': '#ff7f0e', 
                    'ERROR': '#d62728',
                    'DEBUG': '#2ca02c'
                }.get(log['level'], '#1f77b4')
                
                st.markdown(
                    f"""
                    <div style="padding: 2px 8px; margin: 1px 0; border-left: 3px solid {log_color}; background-color: rgba(0,0,0,0.05);">
                        <small style="color: gray;">[{log['timestamp']}]</small> 
                        {log['emoji']} <strong>{log['level']}</strong>: {log['message']}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

def setup_logging(log_container):
    """Configura o sistema de logging para Streamlit"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Limpar handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Adicionar handler customizado
    handler = StreamlitLogHandler(log_container)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

def extract_ibrx100(path: str) -> list:
    """Extrai tickers do IBRX100"""
    try:
        logging.info(f"Extraindo tickers do IBRX100: {path}")
        df = pd.read_csv(path, sep=';', skiprows=1, encoding='latin1')
        tickers = df[:-2].index.values.tolist()
        logging.info(f"✅ Extraídos {len(tickers)} tickers do IBRX100")
        return tickers
    except Exception as e:
        logging.error(f"Erro na extração IBRX100: {e}")
        st.error(f"❌ Erro ao extrair IBRX100: {e}")
        return []

def extract_sp500() -> list:
    """Extrai tickers do S&P500"""
    try:
        logging.info("Extraindo tickers do S&P500")
        url = "https://www.slickcharts.com/sp500"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        tickers = pd.read_html(StringIO(response.text), header=0)[0].Symbol.values
        logging.info(f"✅ Extraídos {len(tickers)} tickers do S&P500")
        return tickers.tolist()
    except Exception as e:
        logging.error(f"Erro na extração S&P500: {e}")
        st.error(f"❌ Erro ao extrair S&P500: {e}")
        return []

def extract_sp100() -> list:
    try:
        logging.info("Extraindo tickers do S&P100 (2024)")
        url = "https://en.wikipedia.org/w/index.php?title=S%26P_100&oldid=1260310089"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        tickers = pd.read_html(StringIO(response.text), header=0, match='Symbol')[0].Symbol.values
        logging.info(f"✅ Extraídos {len(tickers)} tickers do S&P100 (2024)")
        return tickers.tolist()
    except Exception as e:
        logging.error(f"Erro na extração S&P100 (2024): {e}")
        st.error(f"❌ Erro ao extrair S&P100 (2024): {e}")
        return []
    
def generate_temp_key() -> str:
    """Gera uma chave única para pasta temporária"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"temp_{timestamp}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:8]}"

def create_temp_path(temp_key: str, source: str) -> str:
    """Cria um caminho temporário"""
    path = f'./temp/{temp_key}/{source}'
    os.makedirs(path, exist_ok=True)
    logging.info(f"📁 Pasta temporária criada")
    return path

def cleanup_temp_folder(temp_key: str):
    """Remove pasta temporária após análise"""
    try:
        temp_path = f'./temp/{temp_key}'
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
            logging.info(f"🗑️ Pasta temporária removida")
    except Exception as e:
        logging.warning(f"⚠️ Erro ao remover pasta temporária: {e}")

def transform_tickers(tickers: list) -> list:
    """Transforma tickers para formato Yahoo Finance"""
    try:
        logging.info("🔄 Transformando tickers para formato Yahoo Finance")
        transformed = [f"{ticker}.SA" for ticker in tickers]
        return transformed
    except Exception as e:
        logging.error(f"Erro na transformação de tickers: {e}")
        return []

def extract_history_data(tickers: list, temp_key: str, source: str) -> bool:
    """Extrai dados históricos em pasta temporária"""
    path = create_temp_path(temp_key, source)
    
    try:
        logging.info(f"📊 Baixando histórico para {len(tickers)} tickers")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        success_count = 0
        for i, ticker in enumerate(tickers):
            try:
                status_text.text(f"📈 Baixando {ticker} ({i+1}/{len(tickers)})")
                
                file_path = f'{path}/{ticker.split(".")[0]}.csv'
                yf.Ticker(ticker).history(period='1y').to_csv(file_path)
                success_count += 1
                
                progress_bar.progress((i + 1) / len(tickers))
                
            except Exception as inner_e:
                logging.warning(f"⚠️ Erro ao baixar {ticker}: {inner_e}")
        
        progress_bar.empty()
        status_text.empty()
        logging.info(f"✅ Download concluído: {success_count} arquivos salvos")
        return True
        
    except Exception as e:
        logging.error(f"Erro na extração de dados: {e}")
        return False

def load_history_data(temp_key: str, source: str) -> list:
    """Carrega dados históricos da pasta temporária"""
    try:
        path = create_temp_path(temp_key, source)
        logging.info(f"📂 Carregando dados")
        
        csv_files = glob(f'{path}/*.csv')
        if not csv_files:
            logging.error("❌ Nenhum arquivo encontrado")
            return []
        
        history_list = []
        for file in csv_files:
            try:
                ticker = os.path.basename(file).replace('.csv', '')
                df = pd.read_csv(file, parse_dates=['Date'], index_col='Date')
                if not df.empty:
                    history_list.append({'ticker': ticker, 'data': df})
            except Exception as inner_e:
                logging.warning(f"⚠️ Erro ao ler {file}: {inner_e}")
        
        logging.info(f"✅ Carregados {len(history_list)} ativos")
        return history_list
        
    except Exception as e:
        logging.error(f"Erro no carregamento: {e}")
        return []

def calculate_metrics(history_data: list, params: dict) -> pd.DataFrame:
    """Calcula métricas de momentum e média móvel"""
    try:
        logging.info(f"🧮 Calculando métricas para {len(history_data)} ativos")
        metrics = []

        tail_momentum = 21 * params['momentum']
        tail_moving_average = 21 * params['moving_average']
    
        for item in history_data:
            ticker = item.get('ticker')
            try:
                df = item['data']
                df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)

                momentum_df = df.tail(tail_momentum)
                if len(momentum_df) < tail_momentum:
                    continue

                momentum = (momentum_df['Close'].iloc[-1] / momentum_df['Close'].iloc[0]) - 1

                moving_average_df = df.tail(tail_moving_average)
                if len(moving_average_df) < tail_moving_average:
                    continue

                moving_average = moving_average_df['Close'].rolling(window=tail_moving_average).mean().iloc[-1]

                metrics.append({
                    'ticker': ticker,
                    'current_day': df.index[-1].strftime('%Y-%m-%d'),
                    'current_price': df['Close'].iloc[-1],
                    'momentum': momentum,
                    'moving_average': moving_average,
                })

            except Exception as inner_e:
                logging.warning(f"⚠️ Erro ao processar {ticker}: {inner_e}")

        df_metrics = pd.DataFrame(metrics)
        logging.info(f"✅ Métricas calculadas: {len(df_metrics)} ativos")
        return df_metrics
        
    except Exception as e:
        logging.error(f"Erro no cálculo de métricas: {e}")
        return pd.DataFrame()

def main_app():
    """Aplicação principal após autenticação"""
    
    # Título da aplicação
    st.title("📈 Análise de Momentum e Média Móvel")
    st.markdown("---")
    
    # Sidebar para parâmetros
    st.sidebar.header("⚙️ Configurações")
    
    # Botão de logout
    show_logout_button()
    
    # Formulário de parâmetros
    with st.sidebar.form("parameters_form"):
        st.subheader("📊 Parâmetros de Análise")
        
        source = st.selectbox(
            "📈 Fonte de Dados:",
            options=['ibrx100', 'sp500 (hoje)', 'sp100 (2024)'],
            index=0,
            help="Escolha entre IBRX100 ou S&P500"
        )
        
        momentum_days = st.selectbox(
            "⚡ Período de Momentum (dias):",
            options=[30, 90, 180],
            index=2,
            help="Período para cálculo do momentum"
        )
        
        ma_days = st.selectbox(
            "📊 Período da Média Móvel (dias):",
            options=[30, 90, 180],
            index=2,
            help="Período para cálculo da média móvel"
        )
        
        wallet_size = st.selectbox(
            "👛 Tamanho da Carteira:",
            options=[5, 10, 15, 20],
            index=0,
            help="Quantidade de ativos na carteira final"
        )
        
        submitted = st.form_submit_button("🚀 Executar Análise")
    
    # Área principal
    col1, col2 = st.columns([5, 4])
    
    with col2:
        st.subheader("📋 Logs da Execução")
        log_container = st.empty()
    
    with col1:
        if submitted:
            # Configurar logging
            logger = setup_logging(log_container)
            
            # Início da análise
            logging.info("🚀 Iniciando análise de momentum")
            
            # Gerar chave única para pasta temporária
            temp_key = generate_temp_key()
            cache_key = f"{temp_key}_{source}_{momentum_days}_{ma_days}_{wallet_size}"
            
            # Extrair tickers
            if source == 'ibrx100':
                PATH_IBRX100 = './IBXXDia_20-06-25.csv'
                if not os.path.exists(PATH_IBRX100):
                    st.error(f"❌ Arquivo IBRX100 não encontrado: {PATH_IBRX100}")
                    st.stop()
                
                raw_tickers = extract_ibrx100(PATH_IBRX100)
                if not raw_tickers:
                    st.stop()
                tickers = transform_tickers(raw_tickers)
            elif source == 'sp100 (2024)':
                tickers = extract_sp100()
            else:
                tickers = extract_sp500()
                if not tickers:
                    st.stop()
            
            # Extrair dados históricos
            if extract_history_data(tickers, cache_key, source):
                # Carregar dados
                history_data = load_history_data(cache_key, source)
                
                if history_data:
                    # Calcular métricas
                    params = {
                        'momentum': momentum_days // 30,
                        'moving_average': ma_days // 30
                    }
                    
                    metrics_df = calculate_metrics(history_data, params)
                    
                    if not metrics_df.empty:
                        # Filtrar e ordenar
                        metrics_filter = metrics_df[metrics_df.current_price > metrics_df.moving_average]
                        metrics_sorted = metrics_filter.sort_values(by='momentum', ascending=False)
                        
                        if not metrics_sorted.empty:
                            st.subheader(f"🏆 Top {wallet_size} Ativos")
                            
                            # Resultados
                            top_assets = metrics_sorted.head(wallet_size)
                            
                            # Formatar DataFrame para exibição
                            display_df = top_assets.copy()
                            display_df['momentum'] = display_df['momentum'].apply(lambda x: f"{x:.2%}")
                            display_df['current_price'] = display_df['current_price'].apply(lambda x: f"{x:.2f}")
                            display_df['moving_average'] = display_df['moving_average'].apply(lambda x: f"{x:.2f}")
                            
                            # Renomear colunas
                            display_df.columns = ['Ticker', 'Data', 'Preço Atual', 'Momentum', 'Média Móvel']
                            
                            st.dataframe(display_df, use_container_width=True)
                            
                            # Lista de tickers
                            tickers_list = top_assets['ticker'].tolist()
                            st.subheader("📝 Lista de Tickers")
                            st.code(str(tickers_list))
                            
                            # Métricas resumo
                            col1_metrics, col2_metrics, col3_metrics = st.columns(3)
                            
                            with col1_metrics:
                                st.metric("📊 Total Analisado", len(metrics_df))
                            
                            with col2_metrics:
                                st.metric("✅ Acima da Média", len(metrics_filter))
                            
                            with col3_metrics:
                                avg_momentum = top_assets['momentum'].mean()
                                st.metric("⚡ Momentum Médio", f"{avg_momentum:.2%}")
                            
                            logging.info("✅ Análise concluída com sucesso!")
                            cleanup_temp_folder(cache_key)

                            
                        else:
                            st.warning("⚠️ Nenhum ativo passou no filtro de média móvel")
                    else:
                        st.error("❌ Erro no cálculo de métricas")
                else:
                    st.error("❌ Erro no carregamento dos dados")
            else:
                st.error("❌ Erro na extração dos dados históricos")
        else:
            st.info("👈 Configure os parâmetros na barra lateral e clique em 'Executar Análise'")
            
            # Mostrar informações sobre o cache
            st.subheader("🔍 Informações sobre o Cache")
            st.markdown("""
            **Cache Inteligente:**
            - 📁 Os dados são salvos em cache por fonte de dados
            - 🚀 Mudanças apenas nos parâmetros de análise não requerem novo download
            - 📊 Apenas mudanças na fonte (IBRX100 ↔ S&P500) forçam novo download
            - ⏰ Cache expira após 1 hora para garantir dados atualizados
            """)

def main():
    """Função principal que controla o fluxo da aplicação"""
    
    # Verificar se o usuário está autenticado
    if not check_authentication():
        show_login_form()
    else:
        main_app()

if __name__ == "__main__":
    main()
