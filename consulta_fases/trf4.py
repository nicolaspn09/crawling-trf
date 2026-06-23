import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from acessaSite import AcessaSite
from conectaChrome import ChromeStealthManager
from conectaFirefox import FirefoxSeleniumManager
from navegador import NavegadorPy


def inicia_navegador():
    navegador, firefox_pids = ChromeStealthManager().acessa_navegador()
    return navegador, firefox_pids


def acessa_site(navegador):
    url = AcessaSite().site("sc")
    navegador.get(url)


def tratar_alerta_popup(navegador, timeout=3):
    """
    Verifica se ha um alerta (popup) presente no navegador.
    Se houver, captura o texto, aceita o alerta e retorna (True, texto).
    Caso contrario, retorna (False, None).
    """
    try:
        alert = WebDriverWait(navegador, timeout).until(EC.alert_is_present())
        texto_alerta = alert.text
        alert.accept()
        return True, texto_alerta
    except Exception:
        return False, None


def consultar_cpf(navegador, acoes, cpf):
    print("\n" + "#"*80)
    print(f"[CONSULTA] Iniciando busca para o CPF: {cpf}")
    print("#"*80)

    # Acessa o site para iniciar uma nova consulta limpa
    acessa_site(navegador=navegador)
    
    # Pausa inicial para simular a leitura humana da pagina inicial
    time.sleep(random.uniform(1.0, 1.8))
    
    # 2. Seleciona ComboBox Forma
    acoes.combobox(elemento="selForma", tipo_dado="id", timer=20, index=3)
    time.sleep(random.uniform(0.6, 1.2))
    
    # 3. Seleciona ComboBox Origem
    acoes.combobox(elemento="selOrigem", tipo_dado="id", timer=20, index=2)
    time.sleep(random.uniform(0.5, 1.0))
    
    # 4. Input com digitacao humana (caractere por caractere via navegador.py)
    acoes.adicionar_informacao(elemento="txtValor", tipo_dado="id", valor=cpf, timer=20)
    time.sleep(random.uniform(0.2, 0.5))
    
    # 5. Checkbox
    acoes.clicar(elemento="chkMostrarBaixados", tipo_dado="id", timer=20)
    time.sleep(random.uniform(0.8, 1.5))
    
    # 6. Botao Enviar de forma limpa
    acoes.clicar(elemento="botaoEnviar", tipo_dado="id", timer=20)
    time.sleep(random.uniform(0.8, 1.5))

    # --- BLOCO DE INTERCEPTACAO DO CAPTCHA ---
    # Aguarda o Cloudflare Turnstile (sera validado instantaneamente se o cookie de clearance estiver ativo)
    acoes.aguardar_sucesso_cloudflare(timeout_captcha=30)
    time.sleep(random.uniform(0.5, 1.2))
    
    # 6. Botao Continuar/Enviar final (Tenta clicar se estiver na tela intermediaria)
    try:
        acoes.clicar(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=5)
        time.sleep(random.uniform(1.0, 2.0))
    except Exception:
        # Se nao estiver presente (ex: redirecionado diretamente), prossegue
        pass

    # --- VERIFICACAO DE POPUP (ALERTA DE NAO ENCONTRADO) ---
    tem_alerta, texto_alerta = tratar_alerta_popup(navegador, timeout=3)
    if tem_alerta:
        print(f"[RESULTADO] CPF {cpf}: Nao foi encontrado. (Alerta: {texto_alerta})")
        return "Nao foi encontrado"

    # --- INICIO DA ETAPA DE CONSULTA DE FASES ---
    print("[INFO] Coletando lista de processos carregados...")
    lista_processos = acoes.obter_links_da_lista()
    
    if not lista_processos:
        print(f"[AVISO] Nenhum processo foi encontrado para o CPF {cpf}.")
        return "Nao foi encontrado"

    print(f"[INFO] Mapeamento iniciado para todos os {len(lista_processos)} processos.")

    for idx, proc in enumerate(lista_processos, start=1):
        print("\n" + "="*80)
        print(f"[PROCESSO {idx}/{len(lista_processos)}] Identificador: {proc['titulo']}")
        print(f"Link de Acesso: {proc['url']}")
        
        # Executa a navegacao isolada em outra guia e faz a varredura completa das fases
        dados_principais, lista_fases = acoes.analisar_conteudo_processo(proc['url'])
        
        print("\n--- DADOS DETALHADOS (CAMPOS CHAVE) ---")
        for campo, valor in dados_principais.items():
            print(f"  {campo}: {valor}")
            
        print("\n--- LISTA DE FASES ---")
        if not lista_fases:
            print("  Nenhuma fase encontrada ou falha ao carregar a tabela.")
        else:
            for fase in lista_fases:
                print(f"  Seq: {fase['seq']} | Data: {fase['data']} | Movimento: {fase['movimento']}")
                if fase['documentos']:
                    print("    Documentos anexos:")
                    for doc in fase['documentos']:
                        print(f"      - {doc['texto']}: {doc['url']}")
        
        print("="*80)
        time.sleep(random.uniform(1.0, 2.0))

    return f"Encontrado ({len(lista_processos)} processos)"


if __name__ == "__main__":
    lista_cpfs = [
        "015.850.739-89",
        "383.720.889-34",
        "903.145.069-34",
        "465.648.539-04",
        "201.815.159-20",
        "164.625.868-18"
    ]

    navegador, firefox_pids = inicia_navegador()
    acoes = NavegadorPy(navegador=navegador)

    resultados_finais = {}

    try:
        for idx, cpf in enumerate(lista_cpfs):
            status = consultar_cpf(navegador, acoes, cpf)
            resultados_finais[cpf] = status if status else "Erro ou nao finalizado"
            # Pequeno intervalo entre consultas de CPFs
            time.sleep(random.uniform(1.5, 3.0))
            
    finally:
        print("\n" + "="*80)
        print("RELATORIO FINAL DA CONSULTA DOS CPFS:")
        print("="*80)
        for cpf, res in resultados_finais.items():
            print(f"CPF: {cpf} -> {res}")
        print("="*80)
        
        navegador.quit()
