import os
import sys
import requests
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv, find_dotenv

# Carrega configurações do .env do projeto
script_dir = os.path.dirname(os.path.abspath(__file__))
# Procura o .env no diretório pai (raiz do projeto)
dotenv_path = find_dotenv(os.path.join(script_dir, '..', '.env'))
load_dotenv(dotenv_path, override=True)

# Configurações do GitHub e Groq
REPO = "nicolaspn09/crawling-trf"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Configurações de SMTP para Envio de E-mail
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_DESTINATARIO = os.getenv("EMAIL_DESTINATARIO", "nicolaspn09@gmail.com")

def eh_arquivo_relevante(filename) -> bool:
    """Retorna True se o arquivo modificado fizer parte do core do robô ou CRM."""
    # Ignora documentação e arquivos auxiliares
    if filename.startswith("Base - Documentação/") or filename.startswith("scripts/"):
        return False
        
    ignored_files = [
        ".gitignore",
        "README.md",
        "test_repo.py",
        "check_db.py",
        "check_html.py",
        "check_groq_env.py",
        "test_groq_models.py",
        "test_all_groq_keys.py",
        "test_vps.py",
        "teste_local_sc.py",
        "teste_nome.py",
        "check_import_errors.py",
        "check_uptime.py",
        "check_vps_airflow.py",
        "check_vps_ports.py",
        "check_vps_ufw.py",
        "search_logs.py"
    ]
    if filename in ignored_files:
        return False
        
    # Relevante se for um script python core, migration ou código no CRM/Fases
    if filename.endswith(".py") or filename.endswith(".sql"):
        return True
    if filename.startswith("crm_backend/") or filename.startswith("consulta_fases/"):
        return True
    if filename.startswith("airflow_dag/"):
        return True
        
    return False

def obter_diff_snippet(patch) -> str:
    """Extrai as linhas adicionadas de um arquivo modificado."""
    if not patch:
        return ""
    added = [
        line[1:].strip()
        for line in patch.split("\n")
        if line.startswith("+") and not line.startswith("+++") and line[1:].strip()
    ]
    return " | ".join(added[:10])[:300]

def obter_commits_recentes(days=1, last_sha=None):
    """Busca os commits, filtra pelo último SHA processado e descarta arquivos irrelevantes."""
    since_dt = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    url = f"https://api.github.com/repos/{REPO}/commits?since={since_dt}"
    
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    
    git_token = os.getenv("GIT_TOKEN") or os.getenv("GIT_TOKEN_ROIT")
    if git_token:
        headers["Authorization"] = f"token {git_token}"

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            commits = res.json()
            if not commits:
                return [], None
            
            # Filtra os commits para pegar apenas os mais recentes que o último SHA processado
            if last_sha:
                index_ultimo = -1
                for idx, c in enumerate(commits):
                    if c['sha'] == last_sha:
                        index_ultimo = idx
                        break
                if index_ultimo != -1:
                    commits = commits[:index_ultimo]
            
            if not commits:
                return [], None

            # O SHA mais recente a ser guardado para a próxima execução
            novo_ultimo_sha = commits[0]['sha']
            commits_com_detalhes = []
            
            # Limita a análise nos últimos 10 commits para evitar prompts gigantes
            for c in commits[:10]:
                sha = c['sha']
                msg = c['commit']['message'].strip()
                author = c['commit']['author']['name']
                
                if msg.startswith("Merge branch") or msg.startswith("Merge pull request"):
                    continue
                
                # Para cada commit, busca os arquivos alterados e os patches de diff
                detail_url = f"https://api.github.com/repos/{REPO}/commits/{sha}"
                detail_res = requests.get(detail_url, headers=headers, timeout=10)
                
                if detail_res.status_code == 200:
                    detail_data = detail_res.json()
                    files_context = []
                    any_relevant = False
                    
                    for f in detail_data.get('files', []):
                        filename = f.get('filename')
                        
                        # Filtra apenas modificações de arquivos relevantes
                        if not eh_arquivo_relevante(filename):
                            continue
                            
                        any_relevant = True
                        status = f.get('status')
                        patch = f.get('patch', '')
                        diff_snippet = obter_diff_snippet(patch)
                        
                        if diff_snippet:
                            files_context.append(f"  - Arquivo: {filename} ({status})\n    Adições: {diff_snippet}")
                        else:
                            files_context.append(f"  - Arquivo: {filename} ({status})")
                    
                    # Se nenhuma alteração no commit for relevante para o CRM ou TRF, ignora
                    if not any_relevant:
                        continue
                        
                    commit_info = f"Commit por {author}: {msg}\n"
                    if files_context:
                        commit_info += "Alterações no código:\n" + "\n".join(files_context)
                    
                    commits_com_detalhes.append(commit_info)
                
            return commits_com_detalhes, novo_ultimo_sha
        else:
            print(f"[AVISO] Erro ao acessar GitHub API: {res.status_code} - {res.text}")
            return [], None
    except Exception as e:
        print(f"[ERRO] Falha de conexão com GitHub: {e}")
        return [], None

def gerar_resumo_humano(lista_commits):
    """Envia os commits detalhados para o Groq para gerar o resumo humanizado."""
    if not GROQ_API_KEY:
        print("[AVISO] GROQ_API_KEY não encontrada no .env. Impossível gerar resumo por IA.")
        return None

    commits_text = "\n\n".join(lista_commits)
    
    prompt = (
        "Você é um desenvolvedor de software sênior da Nexus Systems, focado em RPA e automação.\n"
        "Seu objetivo é resumir as atualizações diárias de um robô de consulta processual (eproc/TRF4) "
        "em uma mensagem curta, direta e com tom extremamente amigável, natural e informal, pronta para ser enviada para a equipe e parceiros no WhatsApp.\n\n"
        f"Aqui está a lista de commits de hoje com as alterações detalhadas nos arquivos de código:\n{commits_text}\n\n"
        "Diretrizes da Mensagem:\n"
        "1. SEM EMOJIS: É estritamente proibido usar emojis no texto. Não adicione nenhum emoji.\n"
        "2. SAUDAÇÃO AMIGÁVEL E NATURAL (ENTRADA): Comece sempre a mensagem com uma saudação calorosa, informal e natural direcionada à equipe (ex: 'Fala pessoal, tudo bem? Passando para compartilhar as novidades que subiram hoje no robô:' ou 'Fala galera, beleza? Segue o resumo das atualizações de hoje no robô processual:'). Evite entradas secas ou frias como 'Olha, hoje...'.\n"
        "3. TOM EXTREMAMENTE HUMANO E DIRETO: Escreva de forma espontânea, como se você estivesse contando as novidades para um colega próximo de trabalho no WhatsApp. Não use termos corporativos rígidos ou formais.\n"
        "4. ESPECIFICIDADE MÁXIMA (NÃO SEJA GENÉRICO): Explique exatamente o que o robô faz agora na prática (ex: se adicionamos suporte a novas teses como Tema 322, Emendas Constitucionais e Buraco Negro, mencione-as diretamente e explique como o robô agora as detecta e grava nas respectivas colunas no banco de dados).\n"
        "5. LINGUAGEM PRÁTICA: Em vez de dizer 'melhoramos o processamento', descreva o comportamento final: 'O robô agora lê a sentença buscando as palavras-chave do Tema 322, Emendas e Buraco Negro, e atualiza a coluna correspondente no banco'.\n"
        "6. QUEBRAS DE LINHA E ESPAÇAMENTO (OBRIGATÓRIO): Não escreva em um parágrafo corrido. Use quebras de linha duplas (\\n\\n) para separar a saudação inicial, cada um dos tópicos de atualização (que devem usar hífen '-') e a mensagem de encerramento. O texto deve ter bastante espaçamento vertical para ser legível no celular.\n"
        "7. Se as alterações forem puramente internas sem impacto perceptível no uso, retorne:\n"
        "'Fala pessoal!\n\nHoje as atualizações foram apenas internas na estrutura do código, sem mudanças no funcionamento do robô.'\n"
    )

    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        json_data = {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}]
        }
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=json_data, timeout=30)
        
        if res.status_code == 200:
            res_json = res.json()
            return res_json['choices'][0]['message']['content'].strip()
        else:
            print(f"[AVISO] Erro no Groq: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        print(f"[ERRO] Falha ao chamar Groq: {e}")
        return None

def enviar_email(assunto, corpo):
    """Envia o e-mail usando o servidor SMTP configurado para múltiplos destinatários."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print("\n[AVISO] Credenciais SMTP_USER ou SMTP_PASSWORD não configuradas no .env.")
        print("E-mail não pôde ser enviado automaticamente.")
        return False

    destinatarios = [email.strip() for email in EMAIL_DESTINATARIO.split(',') if email.strip()]
    if not destinatarios:
        print("[AVISO] Nenhum destinatário válido configurado em EMAIL_DESTINATARIO.")
        return False

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        for dest in destinatarios:
            msg = MIMEMultipart()
            msg['From'] = SMTP_USER
            msg['To'] = dest
            msg['Subject'] = assunto
            msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
            server.sendmail(SMTP_USER, dest, msg.as_string())
            print(f"[OK] E-mail enviado com sucesso para {dest}!")
            
        server.quit()
        return True
    except Exception as e:
        print(f"[ERRO] Erro ao enviar e-mail por SMTP: {e}")
        return False

def main():
    # Parâmetro opcional de dias de retrospectiva
    dias = 1
    for i, arg in enumerate(sys.argv):
        if arg == "--days" and i + 1 < len(sys.argv):
            dias = int(sys.argv[i + 1])

    # 1. Recupera o último commit SHA processado
    path_ultimo = os.path.join(script_dir, "ultimo_commit.txt")
    last_sha = None
    if os.path.exists(path_ultimo):
        try:
            with open(path_ultimo, "r") as f:
                last_sha = f.read().strip()
            print(f"[INFO] Último commit processado anteriormente: {last_sha}")
        except Exception as e:
            print(f"[AVISO] Não foi possível ler ultimo_commit.txt: {e}")

    print(f"[INFO] Coletando commits das últimas {dias*24} horas no repositório {REPO}...")
    commits, novo_ultimo_sha = obter_commits_recentes(days=dias, last_sha=last_sha)

    if not commits:
        print("[INFO] Nenhum commit novo e relevante para o CRM/TRF encontrado no período.")
        # Se achou novos commits no GitHub mas nenhum era relevante, atualiza o SHA do mesmo jeito
        if novo_ultimo_sha:
            try:
                with open(path_ultimo, "w") as f:
                    f.write(novo_ultimo_sha)
                print(f"[INFO] Guardado SHA {novo_ultimo_sha} como processado.")
            except Exception as e:
                print(f"[AVISO] Falha ao atualizar ultimo_commit.txt: {e}")
        sys.exit(0)

    print(f"[INFO] {len(commits)} commits relevantes coletados com detalhes de modificação.")
    print("[INFO] Gerando resumo humanizado via inteligência artificial (Groq)...")
    resumo = gerar_resumo_humano(commits)

    if not resumo:
        print("[ERRO] Não foi possível gerar o resumo por IA.")
        sys.exit(1)

    print("\n--- RESUMO DIARIO GERADO ---")
    try:
        print(resumo)
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write(resumo.encode(sys.stdout.encoding or 'utf-8', errors='replace'))
            print()
        except Exception:
            print(resumo.encode('ascii', errors='ignore').decode('ascii'))
    print("----------------------------\n")

    # Envia e-mail
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    assunto_email = f"Atualizações do Robô TRF4 - {data_hoje}"
    email_sucesso = enviar_email(assunto_email, resumo)

    # 2. Se o envio foi feito ou se concluímos o resumo, salva o SHA do commit mais recente processado
    if email_sucesso and novo_ultimo_sha:
        try:
            with open(path_ultimo, "w") as f:
                f.write(novo_ultimo_sha)
            print(f"[INFO] Atualizado ultimo_commit.txt com o SHA {novo_ultimo_sha}.")
        except Exception as e:
            print(f"[AVISO] Falha ao gravar ultimo_commit.txt: {e}")

if __name__ == "__main__":
    main()
