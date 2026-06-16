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

# 1. CONFIGURAÇÃO DE LAYOUT E CORES DA EMPRESA (VERDE MIKONOS)
st.set_page_config(
    page_title="MKN Comercial",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injeção de CSS para customizar botões e elementos com a cor da empresa
st.markdown("""
    <style>
        .stButton>button {
            background-color: #008a70 !important;
            color: white !important;
            border-radius: 6px;
        }
        .stFormSubmitButton>button {
            background-color: #008a70 !important;
            color: white !important;
            border-radius: 6px;
            width: 100%;
        }
        h2, h3 {
            color: #008a70 !important;
        }
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
CORES_PILOTOS = ["#008a70", "#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4", "#14B8A6"]

def init_db():
    conn = sqlite3.connect("mkn_comercial_v6.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (username TEXT PRIMARY KEY, nome TEXT, senha TEXT, tipo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS empresas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vendedores 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, tipo_canal TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS lancamentos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, dia INTEGER, mes TEXT, empresa TEXT, 
                  vendedor TEXT, valor REAL, vendas INTEGER, atendimentos INTEGER)''')
    
    c.execute("SELECT * FROM usuarios WHERE username='carla.castro'")
    if not c.fetchone():
        assinatura_nova_senha = hashlib.sha256("123mudar@".encode()).hexdigest()
        c.execute("INSERT INTO usuarios VALUES ('carla.castro', 'Carla Castro', ?, 'Admin')", (assinatura_nova_senha,))
        
    vendedores_padrao = [
        ("Pedro", "WhatsApp"), 
        ("Gabriel", "Loja"), 
        ("Jailson", "Loja"),
        ("Angelo", "WhatsApp"), 
        ("Gustavo", "WhatsApp")
    ]
    for v, t in vendedores_padrao:
        c.execute("INSERT OR IGNORE INTO vendedores (nome, tipo_canal) VALUES (?, ?)", (v, t))
        
    if c.execute("SELECT COUNT(*) FROM empresas").fetchone()[0] == 0:
        c.execute("INSERT INTO empresas (nome) VALUES ('MKN Camisetas')")
        
    conn.commit()
    conn.close()

init_db()

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.user = None
    st.session_state.username = None
    st.session_state.tipo_user = None

# TELA DE LOGIN
if not st.session_state.autenticado:
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        # Exibe a logo se ela existir no diretório do script
        if os.path.exists("Logo Mikonos 1.PNG"):
            st.image("Logo Mikonos 1.PNG", width=180)
        else:
            st.markdown("<h2 style='text-align: center;'>🏁 MKN Camisetas</h2>", unsafe_allow_html=True)
            
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
                    st.error("Credenciais incorretas ou usuário inexistente.")
                    
        # SISTEMA DE ESQUECEU A SENHA REFORMULADO
        st.markdown("---")
        with st.expander("Esqueceu sua senha? Clique aqui para resetar"):
            user_reset = st.text_input("Digite o ID do Usuário para resetar:", key="reset_user").strip()
            if st.button("Resetar para Senha Padrão"):
                if user_reset:
                    conn = sqlite3.connect("mkn_comercial_v6.db")
                    c = conn.cursor()
                    c.execute("SELECT username FROM usuarios WHERE username=?", (user_reset,))
                    if c.fetchone():
                        nova_senha_padrao = hashlib.sha256("123senha@".encode()).hexdigest()
                        c.execute("UPDATE usuarios SET senha=? WHERE username=?", (nova_senha_padrao, user_reset))
                        conn.commit()
                        st.success(f"🔑 Sucesso! A senha do usuário '{user_reset}' foi redefinida para: **123senha@**")
                    else:
                        st.error("Usuário não encontrado no banco de dados.")
                    conn.close()
                else:
                    st.warning("Por favor, digite o ID do usuário.")
    st.stop()

# APÓS AUTENTICAÇÃO - SIDEBAR
st.sidebar.title(f"👤 {st.session_state.user}")
st.sidebar.write(f"Perfil: **{st.session_state.tipo_user}**")

if st.sidebar.button("Desconectar do Sistema"):
    st.session_state.autenticado = False
    st.rerun()

# ABA INTERNA DE MUDAR A PRÓPRIA SENHA
st.sidebar.markdown("---")
with st.sidebar.expander("🔒 Alterar Minha Senha"):
    senha_atual = st.text_input("Senha Atual", type="password", key="alterar_atual")
    nova_senha = st.text_input("Nova Senha", type="password", key="alterar_nova")
    if st.button("Confirmar Nova Senha"):
        hash_atual = hashlib.sha256(senha_atual.encode()).hexdigest()
        conn = sqlite3.connect("mkn_comercial_v6.db")
        c = conn.cursor()
        c.execute("SELECT senha FROM usuarios WHERE username=?", (st.session_state.username,))
        senha_banco = c.fetchone()[0]
        
        if hash_atual == senha_banco:
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

# --- FUNÇÕES SUPORTE ---
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

# --- PÁGINAS DO MENU ---
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
    total_faturamento_empresa = df_ranking["Já Atingiu"].sum()
    total_vendas_empresa = df_ranking["Vendas Mês"].sum()
    ticket_medio_geral = (total_faturamento_empresa / total_vendas_empresa) if total_vendas_empresa > 0 else 0.0
    
    st.subheader("Análise Detalhada por Profissional")
    for _, r in df_ranking.sort_values(by="Já Atingiu", ascending=False).iterrows():
        with st.expander(f"👤 Piloto: {r['Piloto']} | Progresso: {r['Pct']:.1f}%"):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Valor Vendido", f"R$ {r['Já Atingiu']:,.2f}")
            col2.metric("Meta Individual", f"R$ {r['Meta Mês']:,.2f}")
            col3.metric("Atendimentos", f"{int(r['Atendimentos Mês'])}")
            col4.metric("Vendas", f"{int(r['Vendas Mês'])}")
            
            col5, col6, col7 = st.columns(3)
            col5.metric("Ticket Médio", f"R$ {r['Ticket Médio']:,.2f}")
            col6.metric("Conversão", f"{r['Conversão']:.1f}%")
            if r['Status Meta'] == "Atingida":
                col7.metric("Meta do Mês", "🏆 ULTRAPASSADA!", f"+{r['Porcentagem Saldo']:.1f}%")
            else:
                col7.metric("Meta do Mês", "Faltando Saldo", f"-{r['Porcentagem Saldo']:.1f}%", delta_color="inverse")

    st.markdown("---")
    st.subheader("📄 Espaço do Relatório Mensal Executivo")
    
    def gerar_pdf_executivo():
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, leading=20, textColor=colors.HexColor('#008a70'), alignment=1)
        style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9, leading=11, alignment=1)
        
        story.append(Paragraph(f"RELATÓRIO EXECUTIVO DE PERFORMANCE COMERCIAL", style_title))
        story.append(Paragraph(f"Competência: {mes_sel} de 2026 | Referência: {cenario_sel}", styles['Normal']))
        story.append(Spacer(1, 15))
        
        vendedor_campeao = df_ranking.sort_values(by="Conversão", ascending=False).iloc[0]["Piloto"] if not df_ranking.empty else "Nenhum"
        scorecard_data = [
            [Paragraph("<b>Faturamento Total</b>", style_cell), Paragraph("<b>Meta Alvo Mês</b>", style_cell), Paragraph("<b>Líder de Conversão</b>", style_cell), Paragraph("<b>Ticket Geral</b>", style_cell)],
            [f"R$ {total_faturamento_empresa:,.2f}", f"R$ {meta_mês['Total']:,.2f}", vendedor_campeao, f"R$ {ticket_medio_geral:,.2f}"]
        ]
        sc_table = Table(scorecard_data, colWidths=[130, 130, 130, 130])
        sc_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F3F4F6')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#E5E7EB')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(sc_table)
        story.append(Spacer(1, 20))
        
        pdf_table_data = [["Piloto", "Meta", "Realizado", "Progresso", "Saldo", "Ticket Médio", "Conversão"]]
        for _, r in df_ranking.sort_values(by="Já Atingiu", ascending=False).iterrows():
            txt_saldo = f"+{r['Porcentagem Saldo']:.1f}%" if r['Status Meta'] == "Atingida" else f"-{r['Porcentagem Saldo']:.1f}%"
            pdf_table_data.append([r["Piloto"], f"R$ {r['Meta Mês']:,.2f}", f"R$ {r['Já Atingiu']:,.2f}", f"{r['Pct']:.1f}%", txt_saldo, f"R$ {r['Ticket Médio']:,.2f}", f"{r['Conversão']:.1f}%"])
            
        det_table = Table(pdf_table_data, colWidths=[110, 75, 75, 60, 75, 75, 60])
        det_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#008a70')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#9CA3AF')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F9FAFB')]),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        story.append(det_table)
        doc.build(story)
        buffer.seek(0)
        return buffer

    st.download_button("📄 Emitir e Baixar Relatório Executivo (PDF)", data=gerar_pdf_executivo(), file_name=f"Executivo_MKN_{mes_sel}_2026.pdf", mime="application/pdf")

elif opcao_menu == "✍️ Lançamento de Métricas":
    st.title("✍️ Input Operacional de Resultados")
    if len(lista_vendedores) == 0:
        st.warning("⚠️ Nenhum vendedor cadastrado no sistema. Acesse o Painel Administrativo.")
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
                    st.error("Erro: Atendimentos não podem ser menores que as vendas.")
                elif atend_qtd_input == 0 and vendas_qtd > 0:
                    st.error("Erro: Impossível registrar vendas com zero atendimentos.")
                else:
                    conversao_dia = (vendas_qtd / atend_qtd_input * 100) if atend_qtd_input > 0 else 0.0
                    conn = sqlite3.connect("mkn_comercial_v6.db")
                    conn.execute("INSERT INTO lancamentos (dia, mes, empresa, vendedor, valor, vendas, atendimentos) VALUES (?, ?, ?, ?, ?, ?, ?)", (dia, mes_sel, empresa, vendedor, valor_vendido, vendas_qtd, atend_qtd_input))
                    conn.commit()
                    conn.close()
                    st.success(f"📈 Lançamento gravado com sucesso no histórico!")

elif opcao_menu == "🛡️ Painel Administrativo" and st.session_state.tipo_user == "Admin":
    st.title("🛡️ Painel Advanced de Governança")
    t1, t2, t3 = st.tabs(["👤 Cadastro de Vendedores", "🏢 Organização de Empresas", "🔒 Contas de Operadores"])
    
    with t1:
        st.subheader("Cadastrar Novo Profissional")
        with st.form("form_cadastro_vendedor", clear_on_submit=True):
            nome_novo_vendedor = st.text_input("Nome Completo do Vendedor")
            canal_atuacao = st.selectbox("Canal Comercial", ["Loja", "WhatsApp"])
            if st.form_submit_button("Salvar Vendedor"):
                if nome_novo_vendedor.strip():
                    conn = sqlite3.connect("mkn_comercial_v6.db")
                    try:
                        conn.execute("INSERT INTO vendedores (nome, tipo_canal) VALUES (?, ?)", (nome_novo_vendedor.strip(), canal_atuacao))
                        conn.commit()
                        st.success("Vendedor cadastrado!")
                        st.rerun()
                    except sqlite3.IntegrityError: st.error("Vendedor já existe.")
                    finally: conn.close()
        
        conn = sqlite3.connect("mkn_comercial_v6.db")
        df_v = pd.read_sql_query("SELECT id as ID, nome as 'Nome', tipo_canal as 'Canal Comercial' FROM vendedores ORDER BY nome ASC", conn)
        conn.close()
        st.dataframe(df_v, use_container_width=True, hide_index=True)
                        
    with t2:
        st.subheader("Inclusão de Empresas")
        with st.form("form_cadastro_empresa", clear_on_submit=True):
            new_emp = st.text_input("Nome da Nova Empresa / Filial")
            if st.form_submit_button("Salvar Empresa"):
                if new_emp.strip():
                    conn = sqlite3.connect("mkn_comercial_v6.db")
                    try:
                        conn.execute("INSERT INTO empresas (nome) VALUES (?)", (new_emp.strip(),))
                        conn.commit()
                        st.success("Empresa adicionada!")
                    except sqlite3.IntegrityError: st.error("Empresa já existe.")
                    finally: conn.close()
                        
    with t3:
        st.subheader("Criar novo Login de Alimentação")
        with st.form("add_user_form", clear_on_submit=True):
            new_user = st.text_input("ID de Usuário / Login")
            new_nome = st.text_input("Nome Completo")
            new_pass = st.text_input("Senha Inicial", type="password")
            new_tipo = st.selectbox("Perfil", ["Operador", "Admin"])
            if st.form_submit_button("Gerar Credenciais"):
                if new_user and new_pass:
                    hash_new = hashlib.sha256(new_pass.encode()).hexdigest()
                    conn = sqlite3.connect("mkn_comercial_v6.db")
                    try:
                        conn.execute("INSERT INTO usuarios VALUES (?, ?, ?, ?)", (new_user.strip(), new_nome.strip(), hash_new, new_tipo))
                        conn.commit()
                        st.success("Credenciais criadas e salvas com sucesso no banco!")
                    except sqlite3.IntegrityError: st.error("Usuário indisponível.")
                    finally: conn.close()
