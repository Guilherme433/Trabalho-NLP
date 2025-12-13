import praw
import csv
import time
import sys
import os
from langdetect import detect, LangDetectException

# ==========================================
# 1. CONFIGURAÇÃO DA API DO REDDIT
# ==========================================
# Substitua os valores abaixo pelas chaves da sua aplicação Reddit
# Se não tiver criado a app, veja o guia anterior.
CLIENT_ID = "wwYl1tcfkutxLh_XOAo1gw"
CLIENT_SECRET = "JPAJGyUZQHMENULKTx2pDaR1JYIDjg"
USER_AGENT = "python:analise discurso odio (by /u/No-Consideration6753)" 

# ==========================================
# 2. CONFIGURAÇÃO DA PESQUISA
# ==========================================
# Escolha o tema e os subreddits. 
# Exemplo para Biden: "Biden" em "JoeBiden+democrats+politics"
# Exemplo para Trump: "Trump" em "conservative+Republican+politics"

SEARCH_QUERY = "Biden"                 # O termo a pesquisar nos posts
# Mistura de conservadores, apoiantes diretos e política geral
SUBREDDITS = "JoeBiden+Democrats+politics+DarkBRANDON+WhitePeopleTwitter+Liberal+WhatBidenHasDone+VoteDEM+Trumpvirus+Presidents+FriendsofthePod+inthenews"

MAX_POSTS = 1000              # Número máximo de posts a analisar
MAX_COMMENTS_PER_POST = 100    # Limite de comentários por post para não demorar muito
OUTPUT_FILE = "reddit_comments_filtered.csv" # Nome do ficheiro final

# ==========================================
# 3. INICIALIZAÇÃO E CONEXÃO
# ==========================================

print("="*50)
print("   EXTRATOR DE COMENTÁRIOS REDDIT")
print("="*50)

try:
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT
    )
    # Testa a conexão lendo o nome do utilizador (se for apenas leitura, retorna None, mas não dá erro)
    print(f"Status da Conexão: OK (Modo Leitura: {reddit.read_only})")

except Exception as e:
    print(f"Erro ao conectar com o Reddit: {e}")
    input("Pressione ENTER para sair...")
    sys.exit(1)

# ==========================================
# 4. FUNÇÕES UTILITÁRIAS
# ==========================================

def load_existing_ids(filename):
    """Lê o CSV e retorna um conjunto com todos os comment_id já salvos para evitar duplicados."""
    existing_ids = set()
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "comment_id" in row:
                        existing_ids.add(row["comment_id"])
            print(f"INFO: Base de dados carregada. {len(existing_ids)} comentários já existentes ignorados.")
        except Exception as e:
            print(f"AVISO: Não foi possível ler o ficheiro existente: {e}")
    return existing_ids

# ==========================================
# 5. LÓGICA DE EXTRAÇÃO PRINCIPAL
# ==========================================

existing_ids = load_existing_ids(OUTPUT_FILE)
new_data = []
posts_processed = 0
total_comments_found = 0

print(f"\nA iniciar pesquisa por '{SEARCH_QUERY}' em r/{SUBREDDITS}...")
print(f"Configuração: Máx {MAX_POSTS} posts, até {MAX_COMMENTS_PER_POST} comentários cada.\n")

try:
    subreddit_obj = reddit.subreddit(SUBREDDITS)
    
    # Procura posts relevantes. 
    # Dica: Pode trocar .search(...) por .hot(limit=MAX_POSTS) se quiser apenas os posts mais populares do momento sem pesquisa.
    search_results = subreddit_obj.search(SEARCH_QUERY, sort='relevance', limit=MAX_POSTS)

    for post in search_results:
        print(f"-> A processar Post: {post.title[:60]}... (ID: {post.id})")
        
        # Este comando é essencial: ele expande a árvore de comentários
        post.comments.replace_more(limit=0) 
        
        comments_in_this_post = 0
        
        # post.comments.list() devolve todos os comentários numa lista plana (flat)
        for comment in post.comments.list():
            if comments_in_this_post >= MAX_COMMENTS_PER_POST:
                break
            
            # 1. Verificar duplicado
            if comment.id in existing_ids:
                continue

            # 2. Verificar conteúdo válido
            if not comment.body or comment.body in ["[deleted]", "[removed]"]:
                continue

            try:
                # 3. Filtrar por idioma (Inglês)
                if detect(comment.body) == 'en':
                    new_data.append({
                        "comment_id": comment.id,
                        "parent_id": comment.parent_id,
                        "type": "comment", 
                        "author": str(comment.author),
                        "text": comment.body.replace("\n", " "), # Remove quebras de linha para limpar CSV
                        "like_count": comment.score, 
                        "source_video_id": f"REDDIT_{post.id}", # Identificador único do post
                        "subreddit": str(comment.subreddit)
                    })
                    
                    # Adiciona ao set temporário para não duplicar na mesma execução
                    existing_ids.add(comment.id)
                    comments_in_this_post += 1
                    total_comments_found += 1
            
            except LangDetectException:
                pass # Ignora se não conseguir detetar o idioma
            except Exception:
                pass # Ignora erros pontuais
        
        posts_processed += 1
        print(f"   [OK] Extraídos {comments_in_this_post} comentários novos.")
        
        # Pausa curta para respeitar a API
        time.sleep(1) 

except Exception as e:
    print(f"\nERRO DURANTE A EXTRAÇÃO: {e}")

# ==========================================
# 6. GUARDAR DADOS
# ==========================================

print("-" * 50)
print(f"PROCESSO CONCLUÍDO.")
print(f"Posts analisados: {posts_processed}")
print(f"Total de novos comentários recolhidos: {len(new_data)}")
print("-" * 50)

# Campos do CSV
fieldnames = ["comment_id", "parent_id", "type", "author", "text", "like_count", "source_video_id", "subreddit"]
file_exists = os.path.exists(OUTPUT_FILE)

if len(new_data) > 0:
    try:
        with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as csvfile: 
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            
            if not file_exists:
                writer.writeheader()
            
            for entry in new_data:
                writer.writerow(entry)
        print(f"SUCESSO! Os dados foram guardados em: {OUTPUT_FILE}")
    except Exception as e:
        print(f"Erro ao gravar o ficheiro CSV: {e}")
else:
    print("Nenhum comentário novo encontrado para guardar.")

# ==========================================
# 7. BLOQUEIO FINAL
# ==========================================
print("\n" + "="*50)
print("Pode fechar esta janela.")
print("="*50)
input("Pressione a tecla ENTER para sair...")
sys.exit(0)