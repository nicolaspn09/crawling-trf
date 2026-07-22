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
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

# Configurações de SMTP para Envio de E-mail
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_DESTINATARIO = os.getenv("EMAIL_DESTINATARIO", "nicolaspn09@gmail.com")

def obter_commits_recentes(days=1):
    """Busca os commits do repositório público nas últimas X horas."""
    since_dt = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    url = f"https://api.github.com/repos/{REPO}/commits?since={since_dt}"
    
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            commits = res.json()
            # Filtra commits de merge automáticos
            filtered_commits = []
            for c in commits:
                msg = c['commit']['message'].strip()
                author = c['commit']['author']['name']
                # Pula commits vazios ou de merge automáticos padrão
                if msg.startswith("Merge branch") or msg.startswith("Merge pull request"):
                    continue
                filtered_commits.append(f"- {msg} (por {author})")
            return filtered_commits
        else:
            print(f"[AVISO] Erro ao acessar GitHub API: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        print(f"[ERRO] Falha de conexão com GitHub: {e}")
        return None

def gerar_resumo_humano(lista_commits):
    """Envia os commits para o Groq para gerar o resumo humanizado."""
    if not GROQ_API_KEY:
        print("[AVISO] GROQ_API_KEY não encontrada no .env. Impossível gerar resumo por IA.")
        return None

    commits_text = "\n".join(lista_commits)
    
    prompt = (
        "Você é um desenvolvedor de software sênior da Nexus Systems, focado em RPA e automação.\n"
        "Seu objetivo é resumir os commits do dia de um robô de consulta processual (eproc/TRF4) "
        "em uma mensagem de WhatsApp curta, direta e com tom extremamente humano, natural e informal.\n\n"
        f"Aqui está a lista de commits de hoje:\n{commits_text}\n\n"
        "Diretrizes da Mensagem:\n"
        "1. Tom Extremamente Humano e Conversacional: Escreva como se um desenvolvedor estivesse contando as novidades "
        "do dia de forma espontânea no privado ou no grupo de WhatsApp. Não use termos corporativos ou formais rígidos "
        "(ex: 'Temos a satisfação de anunciar', 'Implementamos melhorias de performance'). Comece de forma amigável e direta.\n"
        "2. Linguagem Prática: Foque no benefício real e no que mudou no funcionamento do robô.\n"
        "3. Sem jargões técnicos excessivos (evite falar de logs, migrations, git, hooks, Vercel, docker, CI/CD, etc. a menos que seja algo crucial para explicar a alteração de forma simples).\n"
        "4. Formato curto e limpo: Use bullet points amigáveis e emojis moderados. Deve caber perfeitamente na tela de um celular sem exigir muita rolagem.\n"
        "5. Se as alterações forem puramente internas sem impacto perceptível no uso, retorne: "
        "'Hoje as atualizações foram apenas internas na estrutura do código, sem mudanças no funcionamento do robô.'\n"
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

    print(f"[INFO] Coletando commits das últimas {dias*24} horas no repositório {REPO}...")
    commits = obter_commits_recentes(days=dias)

    if not commits:
        print("[INFO] Nenhum commit novo encontrado no período.")
        sys.exit(0)

    print(f"[INFO] {len(commits)} commits coletados.")
    print("[INFO] Gerando resumo humanizado via inteligência artificial...")
    resumo = gerar_resumo_humano(commits)

    if not resumo:
        print("[ERRO] Não foi possível gerar o resumo por IA.")
        sys.exit(1)

    print("\n--- RESUMO DIARIO GERADO ---")
    try:
        print(resumo)
    except UnicodeEncodeError:
        # Envia como bytes codificados ou substitui caracteres incompatíveis para evitar quebras no console Windows
        try:
            sys.stdout.buffer.write(resumo.encode(sys.stdout.encoding or 'utf-8', errors='replace'))
            print()
        except Exception:
            print(resumo.encode('ascii', errors='ignore').decode('ascii'))
    print("----------------------------\n")

    # Envia e-mail
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    assunto_email = f"Atualizações do Robô TRF4 - {data_hoje}"
    enviar_email(assunto_email, resumo)

if __name__ == "__main__":
    main()
