import googleapiclient.discovery
import csv
import time
import sys
import os 
from langdetect import detect, LangDetectException # Módulos para deteção de idioma

# 1. Configuração da API
# A usar a variável de ambiente ou string vazia conforme o seu código.
# COLOQUE A SUA CHAVE DENTRO DAS ASPAS ABAIXO SE NÃO USAR VARIÁVEL DE AMBIENTE
api_key = os.environ.get("YOUTUBE_API_KEY", "AIzaSyDPD993DBx3X1GjimFATPn7q-vHvOmsT5M") 

try:
    # A chave do Google Cloud é usada aqui como 'developerKey'
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
except Exception as e:
    print(f"Erro ao inicializar o serviço YouTube API: {e}")
    input("Pressione ENTER para sair...") # Pausa antes de sair em caso de erro
    sys.exit(1)


# 2. ID do vídeo
video_id = "wW1lY5jFNcQ" 

# 3. Constantes e Limites
MAX_THREADS = 109000        # Limite máximo de tópicos de comentários
MAX_REPLIES_PER_THREAD = 5  # Limite máximo de respostas por tópico
COMMENTS_PER_PAGE = 100     # Máximo permitido pela API

# Nome do ficheiro de saída
output_file = "english_only_filtered_com_id.csv" 

# Lista que irá armazenar os dados recolhidos APENAS para o vídeo atual
all_data = []
REQUEST_DELAY = 0.5 

# --- NOVA FUNÇÃO: Carregar IDs existentes ---
def load_existing_ids(filename):
    """Lê o CSV e retorna um conjunto (set) com todos os comment_id já salvos."""
    existing_ids = set()
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if "comment_id" in row:
                        existing_ids.add(row["comment_id"])
            print(f"INFO: Encontrados {len(existing_ids)} comentários já existentes no ficheiro '{filename}'.")
        except Exception as e:
            print(f"AVISO: Não foi possível ler o ficheiro existente: {e}")
    return existing_ids

# Carrega os IDs antes de começar
existing_comment_ids = load_existing_ids(output_file)

def fetch_all_replies(parent_comment_id, total_expected_replies, max_replies, existing_ids_set):
    """
    Recolhe respostas de um comentário pai, limita a um máximo e filtra por Inglês.
    """
    replies = []
    next_page_token = None
    
    # [PRINT RESTAURADO] Informação sobre a recolha de respostas
    print(f"    -> A recolher até {max_replies} respostas para o ID: {parent_comment_id} (total esperado: {total_expected_replies})")

    while True:
        if len(replies) >= max_replies:
            break

        results_needed = max_replies - len(replies)
        max_results_api = min(COMMENTS_PER_PAGE, results_needed)
        
        try:
            request = youtube.comments().list(
                part="snippet",
                parentId=parent_comment_id,
                maxResults=max_results_api, 
                pageToken=next_page_token
            )
            response = request.execute()
            time.sleep(REQUEST_DELAY)

            for item in response.get("items", []):
                if len(replies) >= max_replies:
                    break
                
                # VERIFICAÇÃO DE DUPLICADO (RESPOSTA)
                if item["id"] in existing_ids_set:
                    continue

                snippet = item["snippet"]
                text_to_check = snippet["textDisplay"]

                try:
                    if detect(text_to_check) == 'en':
                        replies.append({
                            "comment_id": item["id"],
                            "parent_id": parent_comment_id,
                            "type": "reply",
                            "author": snippet["authorDisplayName"],
                            "text": text_to_check,
                            "like_count": snippet["likeCount"],
                            "source_video_id": video_id 
                        })
                    
                except LangDetectException:
                    pass

            next_page_token = response.get("nextPageToken")
            
            if not next_page_token or len(replies) >= max_replies:
                break
                
        except Exception as e:
            print(f"Erro ao buscar respostas para {parent_comment_id}: {e}", file=sys.stderr)
            break

    return replies


# 4. Recolha dos comentários principais (threads)
next_page_token = None
threads_count = 0
english_threads_collected = 0
skipped_duplicates_count = 0

print(f"Iniciando a recolha de threads de comentários (máx. {MAX_THREADS}) para o vídeo: {video_id}...")
print(f"O ficheiro de saída será: {output_file}")

while True:
    if threads_count >= MAX_THREADS:
        break

    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=COMMENTS_PER_PAGE,
            pageToken=next_page_token
        )
        response = request.execute()
        time.sleep(REQUEST_DELAY)

        for item in response.get("items", []):
            if threads_count >= MAX_THREADS:
                break

            thread_id = item["id"]
            
            # VERIFICAÇÃO DE DUPLICADO (COMENTÁRIO PRINCIPAL)
            if thread_id in existing_comment_ids:
                skipped_duplicates_count += 1
                # Se o comentário principal já existe, verificamos se precisamos buscar respostas novas,
                # mas para simplificar e evitar duplicados, geralmente saltamos o thread.
                # Se quiser verificar respostas de threads antigos, a lógica seria mais complexa.
                # Aqui, assumimos: se o pai já existe, não adicionamos de novo.
                continue

            comment_snippet = item["snippet"]["topLevelComment"]["snippet"]
            text_to_check = comment_snippet["textDisplay"]

            threads_count += 1 

            try:
                # FILTRAGEM DE IDIOMA
                if detect(text_to_check) == 'en':
                    
                    top_comment = {
                        "comment_id": thread_id,
                        "parent_id": "", 
                        "type": "comment",
                        "author": comment_snippet["authorDisplayName"],
                        "text": text_to_check,
                        "like_count": comment_snippet["likeCount"],
                        "source_video_id": video_id 
                    }
                    all_data.append(top_comment)
                    english_threads_collected += 1
                    
                    total_replies = item["snippet"].get("totalReplyCount", 0)
                    if total_replies > 0:
                        # Passamos a lista de IDs existentes para a função de respostas também
                        replies = fetch_all_replies(thread_id, total_replies, MAX_REPLIES_PER_THREAD, existing_comment_ids)
                        all_data.extend(replies)

            except LangDetectException:
                pass

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    except Exception as e:
        print(f"Ocorreu um erro na recolha de threads: {e}", file=sys.stderr)
        break


print("-" * 50)
print(f"Recolha concluída.")
print(f"Novas entradas em Inglês recolhidas: {len(all_data)}")
print(f"Comentários ignorados por já existirem no dataset: {skipped_duplicates_count}")
print("-" * 50)

# 5. Guardar num CSV
fieldnames = ["comment_id", "parent_id", "type", "author", "text", "like_count", "source_video_id"]
file_exists = os.path.exists(output_file)

try:
    # Só abre o arquivo para escrita se houver dados novos
    if len(all_data) > 0:
        with open(output_file, "a", newline="", encoding="utf-8") as csvfile: 
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

            if not file_exists:
                writer.writeheader()

            for entry in all_data:
                writer.writerow(entry)

        print(f"Dados (comentários e respostas) adicionados com sucesso ao ficheiro: {output_file}")
    else:
        print("Nenhum dado novo para adicionar ao ficheiro.")

    # [PRINT RESTAURADO] Sugestão para o próximo vídeo
    print(f"SUGESTÃO: Para o próximo vídeo, altere apenas o 'video_id' e execute novamente. O ficheiro irá acumular os dados.")
    
except Exception as e:
    print(f"Erro ao guardar o ficheiro CSV: {e}", file=sys.stderr)

# BLOQUEIO FINAL: Impede o reinício automático
print("\n" + "="*50)
print("PROCESSO TERMINADO COM SUCESSO.")
print("="*50)
input("Pressione a tecla ENTER para fechar esta janela...")
sys.exit(0)