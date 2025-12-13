import pandas as pd
import os

FICHEIROS_PARA_ORGANIZAR = [
    "csv_analisados_desorganizados/resultado_analise_reddit.csv", 
    "csv_analisados_desorganizados/resultado_analise_youtube.csv"
]

ORDEM_PERSONALIZADA = [
    "Ódio de Identidade (Racismo/Xenofobia/etc)",  #1. Mais grave
    "Ameaça Violenta",                             
    "Toxicidade Extrema",                          
    "Insulto",                                     
    "Tóxico Geral",                                
    "Neutro/Seguro"                                #6. Menos grave
]


print("="*60)
print("   ORGANIZADOR DE CSV POR CATEGORIA")
print("="*60)

for arquivo in FICHEIROS_PARA_ORGANIZAR:
    if not os.path.exists(arquivo):
        print(f"\n[AVISO] O ficheiro '{arquivo}' não foi encontrado. Saltando...")
        continue

    print(f"\n-> A processar: {arquivo}...")
    
    try:
        # Tenta ler (suporta UTF-8 e Latin-1)
        try:
            df = pd.read_csv(arquivo, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(arquivo, encoding='latin-1')

        # Verifica se a coluna existe
        if 'Categoria_Final' not in df.columns:
            print("   [ERRO] Este ficheiro não tem a coluna 'Categoria_Final'.")
            continue

        # TRUQUE MÁGICO DO PANDAS:
        # Transforma a coluna de texto numa categoria matemática com ordem definida
        df['Categoria_Final'] = pd.Categorical(
            df['Categoria_Final'], 
            categories=ORDEM_PERSONALIZADA, 
            ordered=True
        )

        # Ordena baseando-se na lista personalizada (não alfabética)
        df_ordenado = df.sort_values('Categoria_Final')

        # Salva num novo ficheiro para segurança
        nome_saida = arquivo.replace(".csv", "_organizado.csv")
        df_ordenado.to_csv(nome_saida, index=False, encoding='utf-8')
        
        print(f"   [SUCESSO] Linhas reordenadas.")
        print(f"   Salvo como: {nome_saida}")
        
        # Mostra uma amostra das primeiras 5 linhas para confirmar
        print("   Primeiras 5 categorias no topo do ficheiro:")
        print(df_ordenado['Categoria_Final'].head(5).to_string(index=False))

    except Exception as e:
        print(f"   [ERRO] Algo correu mal: {e}")

print("\n" + "="*60)
input("Pressione ENTER para sair...")