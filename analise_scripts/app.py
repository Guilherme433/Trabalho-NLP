import streamlit as st
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import altair as alt

# Configuração da Página
st.set_page_config(page_title="AI Moderator", page_icon="🛡️", layout="wide")

# Usamos @st.cache para carregar o modelo só uma vez e não ficar lento
@st.cache_resource
def load_model():
    model_name = "unitary/toxic-bert"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    return tokenizer, model

tokenizer, model = load_model()

def analyze_text(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.sigmoid(outputs.logits).numpy()[0]
    return probs


st.title("🛡️ AI Content Moderator: YouTube vs Reddit")
st.markdown("""
Esta aplicação utiliza um **LLM (Toxic-BERT)** para analisar toxicidade em redes sociais 
e auxiliar moderadores humanos na deteção de discurso de ódio.
""")

tab1, tab2 = st.tabs(["📊 Análise Comparativa (Dashboard)", "⚡ Teste em Tempo Real"])

with tab1:
    st.header("O Problema: Toxicidade nas redes sociais")
    
    # Carregar os teus CSVs organizados
    try:
        df_yt = pd.read_csv("csv_analise_final_organizados/resultado_analise_youtube_organizado.csv")
        df_rd = pd.read_csv("csv_analise_final_organizados/resultado_analise_reddit_organizado.csv")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("YouTube")
            # Calculo da percentagem ódio de identidade
            odio_yt = len(df_yt[df_yt['Categoria_Final'].str.contains("Ódio de Identidade")])
            pct_yt = (odio_yt / len(df_yt)) * 100
            st.metric("Taxa de Ódio de Identidade", f"{pct_yt:.2f}%")
            st.dataframe(df_yt[['text', 'Categoria_Final']].head(10), use_container_width=True)
            
        with col2:
            st.subheader("Reddit")
            odio_rd = len(df_rd[df_rd['Categoria_Final'].str.contains("Ódio de Identidade")])
            pct_rd = (odio_rd / len(df_rd)) * 100

            st.metric("Taxa de Ódio de Identidade", f"{pct_rd:.2f}%")
            
            st.dataframe(df_rd[['text', 'Categoria_Final']].head(10), use_container_width=True)

        st.markdown("---")
        st.subheader("Visualização Gráfica")
        
        #Preparar os dados para o gráfico
        df_chart = pd.concat([df_yt.assign(Plataforma='YouTube'), df_rd.assign(Plataforma='Reddit')])
        
        chart_data = df_chart.groupby(['Categoria_Final', 'Plataforma']).size().reset_index(name='Contagem')
        
        ordem_categorias = [
            "Ódio de Identidade (Racismo/Xenofobia/etc)",
            "Ameaça Violenta",
            "Toxicidade Extrema",
            "Insulto",
            "Tóxico Geral",
            "Neutro/Seguro"
        ]
        
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Contagem', title='Número de Comentários'),
            y=alt.Y('Categoria_Final', sort=ordem_categorias, title=None),
            color=alt.Color('Plataforma', 
                            scale=alt.Scale(domain=['YouTube', 'Reddit'], range=['#FF0000', '#FF4500']),
                            legend=alt.Legend(title="Plataforma")),
            tooltip=['Plataforma', 'Categoria_Final', 'Contagem'], 
            yOffset='Plataforma' 
        ).properties(
            height=500,
            title="Comparação de Toxicidade por Categoria"
        ).configure_axis(
            labelFontSize=12,
            titleFontSize=14
        )
        
        # Mostrar o gráfico no Streamlit
        st.altair_chart(chart, use_container_width=True)

    except FileNotFoundError:
        st.error("⚠️ Ficheiros CSV 'organizados' não encontrados. Por favor execute os scripts de análise primeiro.")

with tab2:
    st.header("Simulador de Moderação Automática")
    st.write("Teste o modelo de LLM com qualquer frase (em Inglês) para ver como ele classifica.")

    user_input = st.text_area("Digite um comentário para analisar:", "You are stupid but I respect your opinion.")
    
    if st.button("Analisar Comentário"):
        if user_input:
            with st.spinner("O BERT está a pensar..."):
                scores = analyze_text(user_input)
                
            labels = ["Tóxico", "Muito Tóxico", "Obsceno", "Ameaça", "Insulto", "Ódio de Identidade"]
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.subheader("Diagnóstico")
                max_score = max(scores)
                if scores[5] > 0.5: # Identity Hate
                    st.error("🚨 BLOQUEIO IMEDIATO: Discurso de Ódio detetado.")
                elif max_score > 0.5:
                    st.warning("⚠️ REVISÃO NECESSÁRIA: Conteúdo tóxico.")
                else:
                    st.success("✅ APROVADO: Comentário seguro.")
            
            with col_b:
                st.subheader("Detalhes do Modelo")
                for label, score in zip(labels, scores):
                    st.progress(float(score), text=f"{label}: {score:.1%}")