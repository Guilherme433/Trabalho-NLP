import praw
import csv
import time
import sys
import os
from langdetect import detect, LangDetectException

CLIENT_ID = "wwYl1tcfkutxLh_XOAo1gw"
CLIENT_SECRET = "JPAJGyUZQHMENULKTx2pDaR1JYIDjg"
USER_AGENT = "python:analise discurso odio (by /u/No-Consideration6753)" 

# Para Biden: "Biden" em "JoeBiden+democrats+politics"
# Para Trump: "Trump" em "conservative+Republican+politics"

SEARCH_QUERY = "Biden"     
SUBREDDITS = "JoeBiden+Democrats+politics+DarkBRANDON+WhitePeopleTwitter+Liberal+WhatBidenHasDone+VoteDEM+Trumpvirus+Presidents+FriendsofthePod+inthenews"

MAX_POSTS = 1000
MAX_COMMENTS_PER_POST = 100    
OUTPUT_FILE = "reddit_comments_filtered.csv" 

print("="*50)
print("   EXTRATOR DE COMENTÁRIOS REDDIT")
print("="*50)

try:
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT
    )
    print(f"Status da Conexão: OK (Modo Leitura: {reddit.read_only})")

except Exception as e:
    print(f"Erro ao conectar com o Reddit: {e}")
    input("Pressione ENTER para sair...")
    sys.exit(1)

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

existing_ids = load_existing_ids(OUTPUT_FILE)
new_data = []
posts_processed = 0
total_comments_found = 0

print(f"\nA iniciar pesquisa por '{SEARCH_QUERY}' em r/{SUBREDDITS}...")
print(f"Configuração: Máx {MAX_POSTS} posts, até {MAX_COMMENTS_PER_POST} comentários cada.\n")

try:
    subreddit_obj = reddit.subreddit(SUBREDDITS)
    
    search_results = subreddit_obj.search(SEARCH_QUERY, sort='relevance', limit=MAX_POSTS)

    for post in search_results:
        print(f"-> A processar Post: {post.title[:60]}... (ID: {post.id})")
        
        post.comments.replace_more(limit=0) 
        
        comments_in_this_post = 0
        
        for comment in post.comments.list():
            if comments_in_this_post >= MAX_COMMENTS_PER_POST:
                break
            
            if comment.id in existing_ids:
                continue

            if not comment.body or comment.body in ["[deleted]", "[removed]"]:
                continue

            try:
                if detect(comment.body) == 'en':
                    new_data.append({
                        "comment_id": comment.id,
                        "parent_id": comment.parent_id,
                        "type": "comment", 
                        "author": str(comment.author),
                        "text": comment.body.replace("\n", " "), 
                        "like_count": comment.score, 
                        "source_video_id": f"REDDIT_{post.id}", 
                        "subreddit": str(comment.subreddit)
                    })
                    
                    existing_ids.add(comment.id)
                    comments_in_this_post += 1
                    total_comments_found += 1
            
            except LangDetectException:
                pass 
            except Exception:
                pass 
        
        posts_processed += 1
        print(f"   [OK] Extraídos {comments_in_this_post} comentários novos.")
        
        time.sleep(1) 

except Exception as e:
    print(f"\nERRO DURANTE A EXTRAÇÃO: {e}")

print("-" * 50)
print(f"PROCESSO CONCLUÍDO.")
print(f"Posts analisados: {posts_processed}")
print(f"Total de novos comentários recolhidos: {len(new_data)}")
print("-" * 50)

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

print("\n" + "="*50)
print("Pode fechar esta janela.")
print("="*50)
input("Pressione a tecla ENTER para sair...")
sys.exit(0)
