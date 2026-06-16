import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import datetime
import calendar
import plotly.graph_objects as go
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import os

# 1. CONFIGURAÇÃO DO LAYOUT E MARCA DA EMPRESA
st.set_page_config(
    page_title="MKN Comercial - Sistema de Metas",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Identidade Visual baseada na Logo (Verde Mikonos)
COR_PRIMARIA = "#008a70"
st.markdown(f"""
    <style>
        .stButton>button {{
            background-color: {COR_PRIMARIA} !important;
            color: white !important;
            border-radius: 6px;
        }}
        .stFormSubmitButton>button {{
            background-color: {COR_PRIMARIA} !important;
            color: white !important;
            border-radius: 6px;
            width: 100%;
        }}
        h1, h2, h3, .stTabs [data-baseweb="tab"] {{
            color: {COR_PRIMARIA} !important;
        }}
    </style>
""", unsafe_allow_html=True)

# DICIONÁRIO DE METAS ATUALIZADO
DADOS_METAS = {
    "Cenário 1 (+30%)": {
        "Anual": 28649400.00,
        "Junho": {"Total": 2206317.07, "Loja": 695560.24, "Whats": 1510756.83},
        "Julho": {"Total": 3210706.05, "Loja": 695560.24, "Whats": 2515145.81},
        "Agosto": {"Total": 2837885.76, "Loja": 639915.42, "Whats": 2197970.35},
        "Setembro": {"Total": 2817018.96, "Loja": 528625.78, "Whats": 2288393.18},
        "Outubro": {"Total": 3317822.33, "Loja": 876405.90, "Whats": 2441416.43},
        "Novembro": {"Total": 3185665.88, "Loja": 723382.65, "Whats": 2462283.24},
        "Dezembro": {"Total": 2462283.24, "Loja": 639915.42, "Whats": 1822367.82}
    },
    "Cenário 2 (+40%)": {
        "Anual": 30853200.00,
        "Junho": {"Total": 2448973.75, "Loja": 772059.82, "Whats": 1676913.93},
        "Julho": {"Total": 3563828.13, "Loja": 772059.82, "Whats": 2791768.31},
        "Agosto": {"Total": 3150004.06, "Loja": 710295.03, "Whats": 2439709.03},
        "Setembro": {"Total": 3126842.27, "Loja": 586765.46, "Whats": 2540076.81},
        "Outubro": {"Total": 3682725.34, "Loja": 972795.37, "Whats": 2709929.97},
        "Novembro": {"Total": 3536033.97, "Loja": 802942.21, "Whats": 2733091.76},
        "Dezembro": {"Total": 2733091.76, "Loja": 710295.03, "Whats": 2022796.73}
    },
    "Cenário 3 (+50%)": {
        "Anual": 33057000.00,
        "Junho": {"Total": 2691630.43, "Loja": 848559.41, "Whats": 1843071.02},
        "Julho": {"Total": 3916950.20, "Loja": 848559.41, "Whats": 3068390.80},
        "Agosto": {"Total": 3462122.36, "Loja": 780674.65, "Whats": 2681447.71},
        "Setembro": {"Total": 3436665.59, "Loja": 644905.15, "Whats": 2791760.44},
        "Outubro": {"Total": 4047628.36, "Loja": 1069184.85, "Whats": 2978443.51},
        "Novembro": {"Total": 3886402.06, "Loja": 882501.78, "Whats": 3003900.28},
        "Dezembro": {"Total": 3003900.29, "Loja": 780674.65, "Whats": 2223225.64}
    }
}

MESES_LISTA = ["Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
CORES_PILOTOS = [COR_PRIMARIA, "#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4", "#14B8A6"]

# BANCO DE DADOS INTELIGENTE COM ATUALIZAÇÃO SUCESSIVA DE COLUNAS (EVITA ERROS DE TABELA)
def init_db():
    conn = sqlite3.connect("mkn_comercial_v6.db")
    c = conn.cursor()
    
    # Criação base das tabelas se não existirem
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (username TEXT PRIMARY KEY, nome TEXT, senha TEXT, tipo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS empresas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendedores 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, tipo_canal TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS lancamentos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, dia INTEGER, mes TEXT, empresa TEXT, 
                  vendedor TEXT, valor REAL, vendas INTEGER, atendimentos INTEGER)''')
    
    # 🔎 SCRIPT DE MIGRAÇÃO: Verifica e adiciona colunas que estavam faltando sem quebrar nada
    # Para a tabela de usuários
    c.execute("PRAGMA table_info(usuarios)")
    colunas_usuarios = [col[1] for col in c.fetchall()]
    if 'criado_por' not in colunas_usuarios:
        c.execute("ALTER TABLE usuarios ADD COLUMN criado_por TEXT DEFAULT 'Sistema'")
    if 'data_cadastro' not in colunas_usuarios:
        c.execute("ALTER TABLE usuarios ADD COLUMN data_cadastro TEXT DEFAULT '-'")
        
    # Para a tabela de lançamentos
    c.execute("PRAGMA table_info(lancamentos)")
    colunas_lancamentos = [col[1] for col in c.fetchall()]
    if 'criado_por' not in colunas_lancamentos:
        c.execute("ALTER TABLE lancamentos ADD COLUMN criado_por TEXT DEFAULT 'Desconhecido'")
    if 'data_registro' not in colunas_lancamentos:
        c.execute("ALTER TABLE lancamentos ADD COLUMN data_registro TEXT DEFAULT '-'")

    # Garantir conta padrão Admin da Carla
    c.execute("SELECT * FROM usuarios WHERE username='carla.castro'")
    if not c.fetchone():
        assinatura_nova_senha = hashlib.sha256("123mudar@".encode()).hexdigest()
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        c.execute("INSERT INTO usuarios VALUES ('carla.castro', 'Carla Castro', ?, 'Admin', 'Sistema', ?)", (assinatura_nova_senha, agora))
        
    vendedores_padrao = [
        ("Pedro", "WhatsApp"), ("Gabriel", "Loja"), ("Jailson", "Loja"),
        ("Angelo", "WhatsApp"), ("Gustavo", "WhatsApp")
    ]
    for v, t in vendedores_padrao:
        c.execute("INSERT OR IGNORE INTO vendedores (nome, tipo_canal) VALUES (?, ?)", (v, t))
        
    if c.execute("SELECT COUNT(*) FROM empresas").fetchone()[0] == 0:
        c.execute("INSERT INTO empresas (nome) VALUES ('MKN Camisetas')")
        
    conn.commit()
    conn.close()

init_db()

# CONTROLE DE SESSÃO PERMANENTE
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.user = None
    st.session_state.username = None
    st.session_state.tipo_user = None

# --- ESTRUTURA DA TELA DE LOGIN ---
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        if os.path.exists("Logo Mikonos 1.PNG"):
            st.image("Logo Mikonos 1.PNG", width=200)
        else:
            st.markdown(f"<h2 style='text-align: center; color: {COR_PRIMARIA};'>🏁 MKN Camisetas</h2>", unsafe_allow_html=True)
            
        with st.form("login_form"):
            st.subheader("Login do Sistema")
            user_input = st.text_input("Usuário / Login").strip()
            pass_input = st.text_input("Senha Corporativa", type="password")
            btn_login = st.form_submit_button("Acessar Painel")
            
            if btn_login:
                hash_input = hashlib.sha256(pass_input.encode()).hexdigest()
                conn = sqlite3.connect("mkn_comercial_v6.db")
                res = conn.execute("SELECT nome, tipo, username FROM usuarios WHERE username=? AND senha=?", (user_input, hash_input)).fetchone()
                conn.close()
                if res:
                    st.session_state.autenticado = True
                    st.session_state.user = res[0]
                    st.session_state.tipo_user = res[1]
                    st.session_state.username = res[2]
                    st.rerun()
                else:
                    st.error("🔒 Credenciais incorretas ou usuário inexistente.")
                    
        st.markdown("---")
        with st.expander("Esqueceu sua senha? Clique aqui para redefinir"):
            user_reset = st.text_input("Digite o Login do usuário para resetar:", key="reset_field").strip()
            if st.button("Aplicar Senha Padrão"):
                if user_reset:
                    conn = sqlite3.connect("mkn_comercial_v6.db")
                    c = conn.cursor()
                    c.execute("SELECT username FROM usuarios WHERE username=?", (user_reset,))
                    if c.fetchone():
                        nova_senha_padrao = hashlib.sha256("123senha@".encode()).hexdigest()
                        c.execute("UPDATE usuarios SET senha=? WHERE username=?", (nova_senha_padrao, user_reset))
                        conn.commit()
                        st.success(f"🔑 Sucesso! A nova credencial de '{user_reset}' é: **123senha@**")
                    else:
                        st.error("Usuário não cadastrado no banco de dados.")
                    conn.close()
    st.stop()

# --- SIDEBAR (BARRA LATERAL) ---
st.sidebar.title(f"👤 {st.session_state.user}")
st.sidebar.write(f"Perfil: **{st.session_state.tipo_user}**")

if st.sidebar.button("Desconectar do Sistema"):
    st.session_state.autenticado = False
    st.rerun()

with st.sidebar.expander("🔒 Alterar Minha Senha"):
    senha_atual = st.text_input("Senha Atual", type="password", key="side_pass_now")
    nova_senha = st.text_input("Nova Senha", type="password", key="side_pass_next")
    if st.button("Confirmar Nova Senha"):
        hash_atual = hashlib.sha256(senha_atual.encode()).hexdigest()
        conn = sqlite3.connect("mkn_comercial_v6.db")
        c = conn.cursor()
        c.execute("SELECT senha FROM usuarios WHERE username=?", (st.session_state.username,))
        if hash_atual == c.fetchone()[0]:
            hash_nova = hashlib.sha256(nova_senha.encode()).hexdigest()
            c.execute("UPDATE usuarios SET senha=? WHERE username=?", (hash_nova, st.session_state.username))
            conn.commit()
            st.success("Senha alterada com sucesso!")
        else:
            st.error("Senha atual incorreta.")
        conn.close()

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Filtros de Competência")
cenario_sel = st.sidebar.selectbox("Cenário de Metas Ativo", list(DADOS_METAS.keys()))
mes_sel = st.sidebar.selectbox("Mês de Referência", MESES_LISTA)

menu = ["🏎️ Grande Prêmio (Painel Visual)", "📊 Dashboard Geral por Vendedor", "✍️ Lançamento de Métricas"]
if st.session_state.tipo_user == "Admin":
    menu.append("🛡️ Painel Administrativo")
opcao_menu = st.sidebar.radio("Navegar por:", menu)

def carregar_listas():
    conn = sqlite3.connect("mkn_comercial_v6.db")
    vendedores = [r[0] for r in conn.execute("SELECT nome FROM vendedores ORDER BY nome ASC").fetchall()]
    empresas = [r[0] for r in conn.execute("SELECT nome FROM empresas ORDER BY nome ASC").fetchall()]
    conn.close()
    return vendedores, empresas

lista_vendedores, lista_empresas = carregar_listas()

def calcular_metricas_comerciais(cenario, mes):
    meta_mês = DADOS_METAS[cenario][mes]
    vendedores_loja = []
    vendedores_whats = []
    
    conn = sqlite3.connect("mkn_comercial_v6.db")
    for row in conn.execute("SELECT nome, tipo_canal FROM vendedores").fetchall():
        if row[1] == "Loja": vendedores_loja.append(row[0])
        else: vendedores_whats.append(row[0])
        
    df_vendas_mes = pd.read_sql_query(
        "SELECT vendedor, SUM(valor) as faturado, SUM(vendas) as qtd_vendas, SUM(atendimentos) as qtd_atend FROM lancamentos WHERE mes=? GROUP BY vendedor", 
        conn, params=(mes,)
    )
    conn.close()
    
    meta_loja_ind = (meta_mês["Loja"] / len(vendedores_loja)) if len(vendedores_loja) > 0 else 0
    meta_whats_ind = (meta_mês["Whats"] / len(vendedores_whats)) if len(vendedores_whats) > 0 else 0
    
    dict_faturado = df_vendas_mes.set_index('vendedor').to_dict('index')
    dados_ranking = []
    
    for idx, vend in enumerate(lista_vendedores):
        meta_individual = meta_loja_ind if vend in vendedores_loja else meta_whats_ind
        realizado = dict_faturado.get(vend, {}).get('faturado', 0.0)
        vendas_qtd = dict_faturado.get(vend, {}).get('qtd_vendas', 0)
        atend_qtd = dict_faturado.get(vend, {}).get('qtd_atend', 0)
        
        ano_atual = 2026
        mes_num = MESES_LISTA.index(mes) + 6
        dias_mes = calendar.monthrange(ano_atual, mes_num)[1]
        
        precisa_vender_dia = max((meta_individual - realizado), 0.0) / max((dias_mes - datetime.datetime.now().day if mes == "Junho" else dias_mes), 1)
        pct_atingido = (realizado / meta_individual * 100) if meta_individual > 0 else 0.0
        
        if realizado >= meta_individual:
            status_meta = "Atingida"
            porcentagem_saldo = ((realizado - meta_individual) / meta_individual) * 100 if meta_individual > 0 else 100.0
            falta_atingir_mes = 0.0
        else:
            status_meta = "Faltando"
            porcentagem_saldo = ((meta_individual - realizado) / meta_individual) * 100 if meta_individual > 0 else 0.0
            falta_atingir_mes = meta_individual - realizado
            
        ticket_vendedor = (realizado / vendas_qtd) if vendas_qtd > 0 else 0.0
        taxa_conversao = (vendas_qtd / atend_qtd * 100) if atend_qtd > 0 else 0.0
        
        dados_ranking.append({
            "Piloto": vend, "Meta Mês": meta_individual, "Já Atingiu": realizado,
            "Pct": pct_atingido, "Falta Mês": falta_atingir_mes, "Status Meta": status_meta,
            "Porcentagem Saldo": porcentagem_saldo, "Diário Necessário": precisa_vender_dia,
            "Atendimentos Mês": atend_qtd, "Vendas Mês": vendas_qtd,
            "Ticket Médio": ticket_vendedor, "Conversão": taxa_conversao, "Cor": CORES_PILOTOS[idx % len(CORES_PILOTOS)]
        })
        
    return pd.DataFrame(dados_ranking), meta_mês

# --- NAVEGAÇÃO DOS MENUS ---
if opcao_menu == "🏎️ Grande Prêmio (Painel Visual)":
    st.title(f"🏎️ Pista de Corrida - GP MKN ({mes_sel})")
    df_ranking, meta_mês = calcular_metricas_comerciais(cenario_sel, mes_sel)
    total_faturamento_empresa = df_ranking["Já Atingiu"].sum()
    total_vendas_empresa = df_ranking["Vendas Mês"].sum()
    ticket_medio_geral = (total_faturamento_empresa / total_vendas_empresa) if total_vendas_empresa > 0 else 0.0
    
    fig = go.Figure()
    for _, item in df_ranking.iterrows():
        fig.add_trace(go.Bar(
            y=[item["Piloto"]], x=[min(item["Pct"], 100.0)], orientation='h',
            name=item["Piloto"], marker=dict(color=item["Cor"]),
            text=f" 🏎️ {item['Pct']:.1f}%", textposition='outside'
        ))
    fig.update_layout(
        xaxis=dict(range=[0, 115], title="Meta Batida (%)"),
        showlegend=False, height=380, margin=dict(l=150, r=20, t=40, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento Unificado MKN", f"R$ {total_faturamento_empresa:,.2f}")
    c2.metric("Meta Global do Mês", f"R$ {meta_mês['Total']:,.2f}")
    c3.metric("Ticket Médio Geral", f"R$ {ticket_medio_geral:,.2f}")

elif opcao_menu == "📊 Dashboard Geral por Vendedor":
    st.title(f"📊 Dashboard Consolidado de Performance ({mes_sel})")
    df_ranking, meta_mês = calcular_metricas_comerciais(cenario_sel, mes_sel)
    
    st.subheader("Análise Detalhada por Profissional")
    for _, r in df_ranking.sort_values(by="Já Atingiu", ascending=False).iterrows():
        with st.expander(f"👤 Piloto: {r['Piloto']} | Progresso: {r['Pct']:.1f}%"):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Valor Vendido", f"R$ {r['Já Atingiu']:,.2f}")
            col2.metric("Meta Individual", f"R$ {r['Meta Mês']:,.2f}")
            col3.metric("Atendimentos", f"{int(r['Atendimentos Mês'])}")
            col4.metric("Vendas", f"{int(r['Vendas Mês'])}")

elif opcao_menu == "✍️ Lançamento de Métricas":
    st.title("✍️ Input Operacional de Resultados")
    if len(lista_vendedores) == 0:
        st.warning("⚠️ Adicione vendedores no Painel Administrativo antes de prosseguir.")
    else:
        with st.form("form_lancamento", clear_on_submit=True):
            st.subheader("Formulário de Entrada de Dados")
            c1, c2, c3 = st.columns(3)
            dia = c1.number_input("Dia do Lançamento", min_value=1, max_value=31, value=datetime.datetime.now().day)
            empresa = c2.selectbox("Empresa Destino", lista_empresas)
            vendedor = c3.selectbox("Profissional / Vendedor", lista_vendedores)
            
            c4, c5, c6 = st.columns(3)
            valor_vendido = c4.number_input("Valor Bruto Comercial (R$)", min_value=0.0, step=100.0)
            vendas_qtd = c5.number_input("Qtd de Vendas Efetuadas", min_value=0, step=1)
            atend_qtd_input = c6.number_input("Fluxo de Atendimentos Realizados", min_value=0, step=1)
            
            if st.form_submit_button("Registrar e Atualizar Pista"):
                if atend_qtd_input < vendas_qtd:
                    st.error("Erro: Atendimentos menores que as vendas.")
                elif atend_qtd_input == 0 and vendas_qtd > 0:
                    st.error("Erro: Lançamento inconsistente.")
                else:
                    agora_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                    conn = sqlite3.connect("mkn_comercial_v6.db")
                    try:
                        conn.execute("""INSERT INTO lancamentos (dia, mes, empresa, vendedor, valor, vendas, atendimentos, criado_por, data_registro) 
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                                     (dia, mes_sel, empresa, vendedor, valor_vendido, vendas_qtd, atend_qtd_input, st.session_state.username, agora_str))
                        conn.commit()
                        st.success(f"📈 Métricas salvas com sucesso no histórico permanente!")
                    except Exception as e:
                        st.error(f"Erro ao salvar dados: {e}")
                    finally:
                        conn.close()

# --- PAINEL ADMINISTRATIVO ATUALIZADO SEM ERROS ---
elif opcao_menu == "🛡️ Painel Administrativo" and st.session_state.tipo_user == "Admin":
    st.title("🛡️ Painel Governança Executiva")
    t1, t2, t3, t4 = st.tabs(["👤 Vendedores", "🏢 Empresas", "🔒 Contas de Operadores", "📋 Histórico Geral de Auditoria"])
    
    with t1:
        st.subheader("Cadastrar Vendedor")
        with st.form("form_vendedor", clear_on_submit=True):
            nome_v = st.text_input("Nome do Vendedor")
            canal = st.selectbox("Canal Comercial", ["Loja", "WhatsApp"])
            if st.form_submit_button("Salvar"):
                if nome_v.strip():
                    conn = sqlite3.connect("mkn_comercial_v6.db")
                    try:
                        conn.execute("INSERT INTO vendedores (nome, tipo_canal) VALUES (?, ?)", (nome_v.strip(), canal))
                        conn.commit()
                        st.success("Vendedor salvo permanentemente!")
                    except sqlite3.IntegrityError: st.error("Este vendedor já existe.")
                    finally: conn.close()
                    st.rerun()

    with t3:
        st.subheader("Criar conta para Colaborador / Operador")
        with st.form("add_user_form", clear_on_submit=True):
            new_user = st.text_input("ID de Usuário / Login (Ex: joao.mkn)").strip()
            new_nome = st.text_input("Nome Completo")
            new_pass = st.text_input("Senha Inicial", type="password")
            new_tipo = st.selectbox("Perfil de Acesso", ["Operador", "Admin"])
            if st.form_submit_button("Gerar e Salvar Credenciais"):
                if new_user and new_pass:
                    hash_new = hashlib.sha256(new_pass.encode()).hexdigest()
                    agora_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                    conn = sqlite3.connect("mkn_comercial_v6.db")
                    try:
                        conn.execute("INSERT INTO usuarios VALUES (?, ?, ?, ?, ?, ?)", 
                                     (new_user, new_nome.strip(), hash_new, new_tipo, st.session_state.username, agora_str))
                        conn.commit()
                        st.success(f"✔️ Operador '{new_user}' salvo com sucesso!")
                    except sqlite3.IntegrityError: 
                        st.error("Este login já está em uso por outra pessoa.")
                    finally: 
                        conn.close()
                    st.rerun()
                    
    with t4:
        st.subheader("📋 Auditoria de Modificações e Registros")
        conn = sqlite3.connect("mkn_comercial_v6.db")
        
        st.markdown("#### 1. Histórico de Lançamento de Métricas (Vendas)")
        df_audit_lancamentos = pd.read_sql_query("""
            SELECT dia as 'Dia', mes as 'Mês', empresa as 'Empresa', vendedor as 'Vendedor', 
                   valor as 'Faturamento (R$)', vendas as 'Vendas', atendimentos as 'Atend.', 
                   criado_por as 'Registrado Por (Login)', data_registro as 'Data/Hora Reg.' 
            FROM lancamentos ORDER BY id DESC
        """, conn)
        st.dataframe(df_audit_lancamentos, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### 2. Quem Cadastrou quem (Contas e Logins Ativos)")
        df_audit_usuarios = pd.read_sql_query("""
            SELECT username as 'Login', nome as 'Nome Completo', tipo as 'Perfil', 
                   criado_por as 'Criado Por (Admin)', data_cadastro as 'Data/Hora Criação' 
            FROM usuarios ORDER BY data_cadastro DESC
        """, conn)
        st.dataframe(df_audit_usuarios, use_container_width=True, hide_index=True)
        conn.close()
