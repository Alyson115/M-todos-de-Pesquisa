import streamlit as st
import pandas as pd
from datetime import date, datetime
from io import BytesIO
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, Enum, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.exc import SQLAlchemyError

# ===================== CONFIGURAÇÃO INICIAL =====================
st.set_page_config(
    page_title="Apex Conglomerate – Fundo",
    page_icon="💰",
    layout="wide"
)

load_dotenv()

# ===================== BANCO DE DADOS =====================
DB_PATH = "fund.db"
Base = declarative_base()

class Participant(Base):
    __tablename__ = "participants"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150))
    discord_id = Column(String(50))
    created_at = Column(Date, default=date.today)
    transactions = relationship("Transaction", back_populates="participant")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    participant_id = Column(Integer, ForeignKey("participants.id"), nullable=False)
    type = Column(
        Enum("aporte", "lucro", "retirada", name="transaction_types"),
        nullable=False
    )
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    responsible = Column(String(100), nullable=False)
    description = Column(String(300))
    participant = relationship("Participant", back_populates="transactions")

@st.cache_resource
def get_engine():
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine

def get_session():
    return Session(bind=get_engine())

# ===================== FUNÇÕES AUXILIARES =====================
def calcular_saldo(participant_id: int, session: Session) -> float:
    transacoes = (
        session.query(Transaction)
        .filter(Transaction.participant_id == participant_id)
        .all()
    )
    saldo = 0.0
    for t in transacoes:
        if t.type == "retirada":
            saldo -= t.amount
        else:
            saldo += t.amount
    return saldo

def exibir_comprovante(trans: Transaction):
    """Exibe um comprovante estilizado da transação e oferece download."""
    tipo_label = {"aporte": "Aporte", "lucro": "Distribuição de Lucro", "retirada": "Retirada"}
    tipo = tipo_label.get(trans.type, trans.type.capitalize())
    valor = f"R$ {trans.amount:,.2f}"
    data = trans.date.strftime("%d/%m/%Y")
    responsavel = trans.responsible

    # Conteúdo do comprovante
    comprovante_txt = f"""
    COMPROVANTE DE TRANSAÇÃO
    -------------------------
    Nº Transação: {trans.id}
    Tipo: {tipo}
    Participante: {trans.participant.name}
    Valor: {valor}
    Data: {data}
    Responsável: {responsavel}
    Descrição: {trans.description or ''}
    """

    # Exibição visual
    st.success("✅ Transação registrada com sucesso!")
    with st.container(border=True):
        st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:20px; border-radius:10px; margin-bottom:15px">
            <h3 style="margin-top:0">🧾 Comprovante de Transação</h3>
            <table style="width:100%">
                <tr><td><strong>Nº Transação:</strong></td><td>{trans.id}</td></tr>
                <tr><td><strong>Tipo:</strong></td><td>{tipo}</td></tr>
                <tr><td><strong>Participante:</strong></td><td>{trans.participant.name}</td></tr>
                <tr><td><strong>Valor:</strong></td><td style="font-size:1.2em; font-weight:bold">{valor}</td></tr>
                <tr><td><strong>Data:</strong></td><td>{data}</td></tr>
                <tr><td><strong>Responsável:</strong></td><td>{responsavel}</td></tr>
                <tr><td><strong>Descrição:</strong></td><td>{trans.description or ''}</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    # Botão de download
    st.download_button(
        label="📥 Baixar comprovante (TXT)",
        data=comprovante_txt,
        file_name=f"comprovante_{trans.id}_{trans.date.isoformat()}.txt",
        mime="text/plain",
    )

# ===================== INTERFACE =====================
def pagina_cadastrar_participante():
    st.header("👤 Cadastrar Participante")
    with st.form("form_participante"):
        nome = st.text_input("Nome completo *")
        email = st.text_input("E-mail")
        discord_id = st.text_input("ID do Discord (opcional)")
        submitted = st.form_submit_button("Cadastrar")
        if submitted:
            if not nome.strip():
                st.error("Nome é obrigatório.")
            else:
                session = get_session()
                try:
                    novo = Participant(
                        name=nome.strip(),
                        email=email.strip() or None,
                        discord_id=discord_id.strip() or None,
                    )
                    session.add(novo)
                    session.commit()
                    st.success(f"Participante '{nome}' cadastrado com sucesso!")
                except SQLAlchemyError as e:
                    session.rollback()
                    st.error(f"Erro ao cadastrar: {e}")
                finally:
                    session.close()

# ... imports e definições até a função exibir_comprovante permanecem iguais ...

# ===================== FUNÇÃO AUXILIAR (comprovante fora do form) =====================
def exibir_comprovante_por_id(trans_id: int):
    """Busca a transação pelo ID e exibe o comprovante (tema adaptável)."""
    session = get_session()
    trans = session.query(Transaction).filter(Transaction.id == trans_id).first()
    if trans:
        tipo_label = {"aporte": "Aporte", "lucro": "Distribuição de Lucro", "retirada": "Retirada"}
        tipo = tipo_label.get(trans.type, trans.type.capitalize())
        valor = f"R$ {trans.amount:,.2f}"
        data = trans.date.strftime("%d/%m/%Y")
        responsavel = trans.responsible

        # Conteúdo do comprovante em formato TXT para download (mantido)
        comprovante_txt = f"""
        COMPROVANTE DE TRANSAÇÃO
        -------------------------
        Nº Transação: {trans.id}
        Tipo: {tipo}
        Participante: {trans.participant.name}
        Valor: {valor}
        Data: {data}
        Responsável: {responsavel}
        Descrição: {trans.description or ''}
        """

        st.success("✅ Transação registrada com sucesso!")
        with st.container(border=True):
            # Tabela markdown – adapta-se a light/dark mode
            st.markdown(f"""
| Campo               | Valor                    |
|---------------------|--------------------------|
| **Nº Transação**    | {trans.id}               |
| **Tipo**            | {tipo}                   |
| **Participante**    | {trans.participant.name} |
| **Valor**           | {valor}                  |
| **Data**            | {data}                   |
| **Responsável**     | {responsavel}            |
| **Descrição**       | {trans.description or ''}|
            """)

        st.download_button(
            label="📥 Baixar comprovante (TXT)",
            data=comprovante_txt,
            file_name=f"comprovante_{trans.id}_{trans.date.isoformat()}.txt",
            mime="text/plain",
        )
    session.close()
# ===================== PÁGINAS AJUSTADAS =====================
def pagina_registrar_aporte():
    st.header("💵 Registrar Aporte")
    session = get_session()
    participantes = session.query(Participant).order_by(Participant.name).all()
    if not participantes:
        st.warning("Nenhum participante cadastrado. Cadastre primeiro.")
        session.close()
        return

    nomes_participantes = {p.name: p.id for p in participantes}
    with st.form("form_aporte"):
        participante_nome = st.selectbox("Participante *", options=list(nomes_participantes.keys()))
        valor = st.number_input("Valor do aporte (R$) *", min_value=0.01, format="%.2f")
        data_aporte = st.date_input("Data *", value=date.today())
        responsavel = st.text_input("Responsável *", value="Admin")
        descricao = st.text_input("Descrição (opcional)")
        submitted = st.form_submit_button("Registrar")
        if submitted:
            if valor <= 0:
                st.error("Valor deve ser positivo.")
            elif not participante_nome:
                st.error("Selecione um participante.")
            elif not responsavel.strip():
                st.error("Informe o responsável.")
            else:
                try:
                    nova_trans = Transaction(
                        participant_id=nomes_participantes[participante_nome],
                        type="aporte",
                        amount=valor,
                        date=data_aporte,
                        responsible=responsavel.strip(),
                        description=descricao.strip() or None,
                    )
                    session.add(nova_trans)
                    session.commit()
                    session.refresh(nova_trans)
                    # Salva o ID na sessão para exibir depois
                    st.session_state["ultima_transacao_id"] = nova_trans.id
                    st.rerun()  # força rerun para sair do form e exibir comprovante
                except SQLAlchemyError as e:
                    session.rollback()
                    st.error(f"Erro ao registrar aporte: {e}")
                finally:
                    session.close()

    # Fora do form: verifica se há um comprovante pendente
    if "ultima_transacao_id" in st.session_state:
        exibir_comprovante_por_id(st.session_state["ultima_transacao_id"])
        del st.session_state["ultima_transacao_id"]  # remove para não repetir

def pagina_registrar_lucro():
    st.header("📈 Distribuir Lucro")
    session = get_session()
    participantes = session.query(Participant).order_by(Participant.name).all()
    if not participantes:
        st.warning("Nenhum participante cadastrado.")
        session.close()
        return

    nomes_participantes = {p.name: p.id for p in participantes}
    with st.form("form_lucro"):
        participante_nome = st.selectbox("Participante *", options=list(nomes_participantes.keys()))
        valor = st.number_input("Valor do lucro (R$) *", min_value=0.01, format="%.2f")
        data_lucro = st.date_input("Data *", value=date.today())
        responsavel = st.text_input("Responsável *", value="Admin")
        descricao = st.text_input("Descrição (opcional)")
        submitted = st.form_submit_button("Registrar")
        if submitted:
            if valor <= 0:
                st.error("Valor deve ser positivo.")
            elif not participante_nome:
                st.error("Selecione um participante.")
            elif not responsavel.strip():
                st.error("Informe o responsável.")
            else:
                try:
                    nova_trans = Transaction(
                        participant_id=nomes_participantes[participante_nome],
                        type="lucro",
                        amount=valor,
                        date=data_lucro,
                        responsible=responsavel.strip(),
                        description=descricao.strip() or None,
                    )
                    session.add(nova_trans)
                    session.commit()
                    session.refresh(nova_trans)
                    st.session_state["ultima_transacao_id"] = nova_trans.id
                    st.rerun()
                except SQLAlchemyError as e:
                    session.rollback()
                    st.error(f"Erro ao registrar lucro: {e}")
                finally:
                    session.close()

    if "ultima_transacao_id" in st.session_state:
        exibir_comprovante_por_id(st.session_state["ultima_transacao_id"])
        del st.session_state["ultima_transacao_id"]

def pagina_registrar_retirada():
    st.header("🏧 Registrar Retirada")
    session = get_session()
    participantes = session.query(Participant).order_by(Participant.name).all()
    if not participantes:
        st.warning("Nenhum participante cadastrado.")
        session.close()
        return

    nomes_participantes = {p.name: p.id for p in participantes}
    with st.form("form_retirada"):
        participante_nome = st.selectbox("Participante *", options=list(nomes_participantes.keys()))
        valor = st.number_input("Valor da retirada (R$) *", min_value=0.01, format="%.2f")
        data_retirada = st.date_input("Data *", value=date.today())
        responsavel = st.text_input("Responsável *", value="Admin")
        descricao = st.text_input("Descrição (opcional)")
        submitted = st.form_submit_button("Registrar")
        if submitted:
            if valor <= 0:
                st.error("Valor deve ser positivo.")
            elif not participante_nome:
                st.error("Selecione um participante.")
            elif not responsavel.strip():
                st.error("Informe o responsável.")
            else:
                try:
                    nova_trans = Transaction(
                        participant_id=nomes_participantes[participante_nome],
                        type="retirada",
                        amount=valor,
                        date=data_retirada,
                        responsible=responsavel.strip(),
                        description=descricao.strip() or None,
                    )
                    session.add(nova_trans)
                    session.commit()
                    session.refresh(nova_trans)
                    st.session_state["ultima_transacao_id"] = nova_trans.id
                    st.rerun()
                except SQLAlchemyError as e:
                    session.rollback()
                    st.error(f"Erro ao registrar retirada: {e}")
                finally:
                    session.close()

    if "ultima_transacao_id" in st.session_state:
        exibir_comprovante_por_id(st.session_state["ultima_transacao_id"])
        del st.session_state["ultima_transacao_id"]


      

def pagina_saldos():
    st.header("📊 Saldo Individual")
    session = get_session()
    participantes = session.query(Participant).order_by(Participant.name).all()
    if not participantes:
        st.info("Nenhum participante.")
        session.close()
        return

    dados = []
    for p in participantes:
        saldo = calcular_saldo(p.id, session)
        dados.append({
            "Participante": p.name,
            "E-mail": p.email or "",
            "Saldo (R$)": f"{saldo:,.2f}",
        })
    df = pd.DataFrame(dados)
    st.dataframe(df, use_container_width=True, hide_index=True)
    session.close()

def pagina_historico():
    st.header("📋 Histórico de Transações")
    session = get_session()

    col1, col2 = st.columns(2)
    with col1:
        busca = st.text_input("🔍 Buscar por nome, responsável ou descrição")
    with col2:
        intervalo = st.date_input("Filtrar por período", value=[])

    query = session.query(Transaction).join(Participant)
    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            (Participant.name.ilike(termo)) |
            (Transaction.responsible.ilike(termo)) |
            (Transaction.description.ilike(termo))
        )
    if intervalo and len(intervalo) == 2:
        data_inicio, data_fim = intervalo
        query = query.filter(Transaction.date.between(data_inicio, data_fim))

    transacoes = query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()

    if not transacoes:
        st.info("Nenhuma transação encontrada.")
        session.close()
        return

    dados = []
    for t in transacoes:
        valor_exibicao = f"R$ {t.amount:,.2f}" if t.type != "retirada" else f"-R$ {t.amount:,.2f}"
        dados.append({
            "ID": t.id,
            "Participante": t.participant.name,
            "Tipo": t.type.capitalize(),
            "Valor": valor_exibicao,
            "Data": t.date.strftime("%d/%m/%Y"),
            "Responsável": t.responsible,
            "Descrição": t.description or "",
        })
    df = pd.DataFrame(dados)
    st.dataframe(df, use_container_width=True, hide_index=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Transações")
    output.seek(0)
    st.download_button(
        label="📥 Exportar para Excel",
        data=output,
        file_name=f"transacoes_{date.today().isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    session.close()

def pagina_grafico():
    st.header("📈 Evolução do Fundo (saldo líquido)")
    session = get_session()
    transacoes = (
        session.query(Transaction)
        .order_by(Transaction.date)
        .all()
    )
    if not transacoes:
        st.info("Sem transações para exibir gráfico.")
        session.close()
        return

    registros = []
    for t in transacoes:
        if t.type == "retirada":
            registros.append({"date": t.date, "amount": -t.amount})
        else:
            registros.append({"date": t.date, "amount": t.amount})

    df = pd.DataFrame(registros)
    diario = df.groupby("date").sum().reset_index()
    diario["saldo_acumulado"] = diario["amount"].cumsum()
    diario = diario.rename(columns={"saldo_acumulado": "Valor Líquido do Fundo (R$)"})
    st.line_chart(diario.set_index("date"), use_container_width=True)
    session.close()

# ===================== MAIN =====================
def main():
    st.sidebar.title("Apex Conglomerate")
    st.sidebar.markdown("🔹 **Gestão de Fundo de Investimentos**")

    pagina = st.sidebar.radio(
        "Menu",
        [
            "Cadastrar Participante",
            "Registrar Aporte",
            "Distribuir Lucro",
            "Registrar Retirada",
            "Consultar Saldos",
            "Histórico / Busca",
            "Gráfico do Fundo",
        ]
    )

    if pagina == "Cadastrar Participante":
        pagina_cadastrar_participante()
    elif pagina == "Registrar Aporte":
        pagina_registrar_aporte()
    elif pagina == "Distribuir Lucro":
        pagina_registrar_lucro()
    elif pagina == "Registrar Retirada":
        pagina_registrar_retirada()
    elif pagina == "Consultar Saldos":
        pagina_saldos()
    elif pagina == "Histórico / Busca":
        pagina_historico()
    elif pagina == "Gráfico do Fundo":
        pagina_grafico()

if __name__ == "__main__":
    main()