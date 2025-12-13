import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import sys
import os
import numpy as np

# Mudar o nome dos ficheiros de entrada e saída para obter o yt e redit
#Para yt
#ARQUIVO_ENTRADA = "csv_extraidos/youtube_comments_filtered.csv" 
#ARQUIVO_SAIDA = "csv_analisados_desorganizados/resultado_analise_youtube.csv"

ARQUIVO_ENTRADA = "csv_extraidos/reddit_comments_filtered.csv" 
ARQUIVO_SAIDA = "csv_analisados_desorganizados/resultado_analise_reddit.csv" 

# Modelo de LLM
NOME_MODELO = "unitary/toxic-bert"
TAMANHO_LOTE = 32 

print("A verificar bibliotecas e hardware")
try:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"-> Processamento será feito via: {str(device).upper()}")
    
    print("-> A carregar o modelo 'toxic-bert'... (pode demorar na primeira vez)")
    tokenizer = AutoTokenizer.from_pretrained(NOME_MODELO)
    model = AutoModelForSequenceClassification.from_pretrained(NOME_MODELO)
    model = model.to(device)
    print("-> Modelo carregado com sucesso!")

except Exception as e:
    print(f"\nERRO CRÍTICO ao carregar o modelo: {e}")
    input("Pressione ENTER para sair...")
    sys.exit(1)

def analisar_lote(textos, tokenizer, model, device):
    inputs = tokenizer(textos, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.sigmoid(outputs.logits)
    return probs.cpu().numpy()

def categorizar_final(linha):
    if linha['identity_hate'] > 0.5: return "Ódio de Identidade (Racismo/Xenofobia/etc)"
    elif linha['threat'] > 0.5: return "Ameaça Violenta"
    elif linha['severe_toxic'] > 0.5: return "Toxicidade Extrema"
    elif linha['insult'] > 0.5: return "Insulto"
    elif linha['toxic'] > 0.5: return "Tóxico Geral"
    else: return "Neutro/Seguro"

if not os.path.exists(ARQUIVO_ENTRADA):
    print(f"\nERRO: O ficheiro '{ARQUIVO_ENTRADA}' não foi encontrado.")
    input("Pressione ENTER para sair...")
    sys.exit(1)

print(f"-> A ler os dados de: {ARQUIVO_ENTRADA}...")

try:
    #Leitura Inteligente (UTF-8 ou Latin-1)
    try:
        df = pd.read_csv(ARQUIVO_ENTRADA, on_bad_lines='skip', encoding='utf-8')
    except UnicodeDecodeError:
        print("-> AVISO: Codificação UTF-8 falhou. A tentar Latin-1...")
        df = pd.read_csv(ARQUIVO_ENTRADA, on_bad_lines='skip', encoding='latin-1')
    
    print(f"   Linhas brutas lidas: {len(df)}")

    print("-> A limpar dados...")
    
    #Remove linhas onde o 'text' está vazio ou é NaN
    df = df.dropna(subset=['text'])
    df = df[df['text'].str.strip() != ""]
    
    #Remove duplicados baseados no ID do comentário (mantém apenas o primeiro)
    if 'comment_id' in df.columns:
        antes = len(df)
        df = df.drop_duplicates(subset=['comment_id'])
        depois = len(df)
        print(f"   Duplicados removidos: {antes - depois}")
    
    total_linhas = len(df)
    print(f"-> TOTAL REAL DE COMENTÁRIOS ÚNICOS A ANALISAR: {total_linhas}")
    
    #Verifica se ainda há dados
    if total_linhas == 0:
        print("ERRO: O ficheiro ficou vazio após a limpeza. Verifique o CSV.")
        sys.exit(1)

    # 3. Análise
    resultados_brutos = []
    textos_lista = df['text'].astype(str).tolist()

    print("\nInicio da análise")
    
    for i in range(0, total_linhas, TAMANHO_LOTE):
        lote_textos = textos_lista[i : i + TAMANHO_LOTE]
        probs = analisar_lote(lote_textos, tokenizer, model, device)
        resultados_brutos.extend(probs)
        
        percentagem = ((i + len(lote_textos)) / total_linhas) * 100
        sys.stdout.write(f"\r   Progresso: {percentagem:.1f}% ({i + len(lote_textos)}/{total_linhas})")
        sys.stdout.flush()

    print("\n\nA processar categorias finais:")

    colunas_modelo = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]
    array_resultados = np.array(resultados_brutos)
    
    for idx, col in enumerate(colunas_modelo):
        df[col] = array_resultados[:, idx]

    df['Categoria_Final'] = df.apply(categorizar_final, axis=1)

    df.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')
    
    print("-" * 60)
    print("sucesso!")
    print(f"Ficheiro salvo como: {ARQUIVO_SAIDA}")
    print("-" * 60)
    print(df['Categoria_Final'].value_counts())

except Exception as e:
    print(f"\nERRO INESPERADO: {e}")

print("\n" + "="*60)
input("Pressione a tecla ENTER para fechar")