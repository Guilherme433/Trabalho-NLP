from ntscraper import Nitter
import csv
import time
import sys
import os
import random
from langdetect import detect, LangDetectException

SEARCH_QUERY = "Biden"       
NUMBER_OF_TWEETS = 100       
OUTPUT_FILE = "twitter_comments_filtered.csv"

NITTER_INSTANCES = [
    "https://nitter.privacydev.net",
    "https://nitter.bird.gardens.link",
    "https://nitter.eu.projectsegfau.lt",
    "https://nitter.soopy.moe",
    "https://nitter.qwik.space",
    "https://nitter.moomoo.me",
    "https://nitter.kavin.rocks",
    "https://nitter.uni-sonia.com",
    "https://nitter.tux.pizza",
    "https://nitter.ktachibana.party",
    "https://nitter.rawbit.ninja",
    "https://nitter.1d4.us",
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.lucabased.xyz"
]

random.shuffle(NITTER_INSTANCES)

def load_existing_ids(filename):
    existing_ids = set()
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "comment_id" in row:
                        existing_ids.add(row["comment_id"])
            print(f"INFO: Base de dados carregada. {len(existing_ids)} tweets já existentes ignorados.")
        except Exception as e:
            print(f"AVISO: Não foi possível ler o ficheiro existente: {e}")
    return existing_ids

print("="*50)
print("   EXTRATOR DE TWEETS (MODO RESILIENTE)")
print("="*50)

existing_ids = load_existing_ids(OUTPUT_FILE)
new_data = []

try:
    scraper = Nitter(log_level=1, skip_instance_check=True)
except Exception as e:
    print(f"Erro crítico ao iniciar Nitter: {e}")
    sys.exit(1)

success = False

print(f"\nA pesquisar por '{SEARCH_QUERY}'...")
print(f"Temos {len(NITTER_INSTANCES)} servidores disponíveis para testar.")

for i, instance in enumerate(NITTER_INSTANCES):
    print(f"\n[{i+1}/{len(NITTER_INSTANCES)}] A tentar servidor: {instance}")
    
    try:
        tweets_data = scraper.get_tweets(SEARCH_QUERY, mode='term', number=NUMBER_OF_TWEETS, instance=instance)
        
        final_tweets = tweets_data.get('tweets', [])
        
        if len(final_tweets) > 0:
            print(f"---> SUCESSO! Encontrados {len(final_tweets)} tweets. A processar...")
            
            count_processed = 0
            for k, tweet in enumerate(final_tweets):
                if k % 50 == 0:
                    sys.stdout.write(f"     A processar {k}...\r")
                    sys.stdout.flush()

                try:
                    tweet_id = tweet['link']
                    
                    if tweet_id in existing_ids:
                        continue

                    text_content = tweet['text']
                    if not text_content:
                        continue

                    if detect(text_content) == 'en':
                        new_data.append({
                            "comment_id": tweet_id,
                            "parent_id": "", 
                            "type": "tweet",
                            "author": tweet['user']['name'],
                            "text": text_content.replace("\n", " "),
                            "like_count": tweet['stats']['likes'],
                            "source_video_id": f"TWITTER_{SEARCH_QUERY}", 
                            "subreddit": "" 
                        })
                        existing_ids.add(tweet_id)
                        count_processed += 1
                except:
                    continue
            
            print(f"\n     Extraídos {count_processed} tweets válidos deste servidor.")
            success = True
            break
        else:
            print("     Falha: O servidor devolveu uma lista vazia (provavelmente bloqueado).")
            
    except Exception as e:
        print(f"     Erro de conexão: {e}")
        time.sleep(1)

if not success:
    print("\n" + "="*50)
    print("ERRO FATAL: Todos os servidores falharam.")
    print("Isto significa que o Twitter está a bloquear agressivamente todo o tráfego externo hoje.")
    print("Sugestão: Tente novamente amanhã ou foque a sua análise no YouTube/Reddit, que são estáveis.")
    print("="*50)
else:
    print("-" * 50)
    print(f"Total de novos tweets a gravar: {len(new_data)}")
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
        print("Nenhum tweet novo encontrado para guardar.")

print("\n" + "="*50)
input("Pressione a tecla ENTER para sair...")
sys.exit(0)
