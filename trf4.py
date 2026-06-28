import os
import time
import random
from pathlib import Path
from acessaSite import AcessaSite
from conectaChrome import ChromeStealthManager
from conectaFirefox import FirefoxSeleniumManager
from navegador import NavegadorPy
from GoogleSheets import GoogleSheets

def inicia_navegador():
    navegador, firefox_pids = ChromeStealthManager().acessa_navegador()

    return navegador, firefox_pids


def acessa_site(navegador):
    url = AcessaSite().site("sc")
    navegador.get(url)

def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma * 10 % 11) % 10

    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma * 10 % 11) % 10

    return cpf[-2:] == f"{dig1}{dig2}"


if __name__ == "__main__":

    BASE_DIR = Path(__file__).resolve().parent
    credenciais = BASE_DIR / "credentials.json"
    
    # Obtém planilha do Google Planilhas com os CPFs a serem consultados
    tabela_sheets = GoogleSheets("1gdppEm4CdytUNfxotvBuHUqWdTdoU8NfBC43cGm_Qh8", "Geral", credenciais)
    guia_sheets = tabela_sheets.solicita_tabela()

    # Abre navegador
    navegador, firefox_pids = inicia_navegador()
    
    for indice, linha in enumerate(guia_sheets[1:], start=2):
        
        # Extrai o CPF da linha atual e remove espaços em branco
        cpf = linha[0].strip()
        # Valida o CPF antes de prosseguir
        if not validar_cpf(cpf):
            print(f"[AVISO] CPF inválido: {cpf}")
            tabela_sheets.atualizar_celula(f"L{indice}", "CPF INVÁLIDO")
            continue
        
        # Acessa site
        acessa_site(navegador=navegador)

        # Pausa inicial para simular a leitura humana da página inicial
        time.sleep(random.uniform(1.0, 1.8))
        
        acoes = NavegadorPy(navegador=navegador)
        
        # 2. Seleciona ComboBox Forma
        acoes.combobox(elemento="selForma", tipo_dado="id", timer=20, index=3)
        time.sleep(random.uniform(0.6, 1.2))
        
        # 3. Seleciona ComboBox Origem
        acoes.combobox(elemento="selOrigem", tipo_dado="id", timer=20, index=2)
        time.sleep(random.uniform(0.5, 1.0))
        
        # 4. Input com digitação humana (caractere por caractere via navegador.py)
        acoes.adicionar_informacao(elemento="txtValor", tipo_dado="id", valor=cpf, timer=20)
        time.sleep(random.uniform(0.2, 0.5))
        
        # 5. Checkbox
        acoes.clicar(elemento="chkMostrarBaixados", tipo_dado="id", timer=20)
        time.sleep(random.uniform(0.8, 1.5))
        
        # 6. Botão Enviar de forma limpa
        acoes.clicar(elemento="botaoEnviar", tipo_dado="id", timer=20)
        time.sleep(random.uniform(0.8, 1.5))

        # 7. Verifica se o Cloudflare Turnstile está presente e aguarda a validação passiva
        cloudflare = acoes._obter_elemento(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=20)
        print(cloudflare)
        if cloudflare is not None:
            # --- BLOCO DE INTERCEPTAÇÃO DO CAPTCHA ---
            # O script faz uma pausa e aguarda o selo de sucesso aparecer dentro do iframe
            acoes.aguardar_sucesso_cloudflare(timeout_captcha=30)
            time.sleep(random.uniform(0.5, 1.2))
        
            # 6. Botão Continuar/Enviar final (Usando o XPath mapeado por você)
            acoes.clicar(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=20)

            time.sleep(random.uniform(0.8, 1.5)) # Aguarda abrir a tela de resultados (image_3d07ce.png)

        # --- INÍCIO DA ETAPA DA POC ENVIADA ---
        print("[INFO] Coletando lista de processos carregados...")
        lista_processos = acoes.obter_links_da_lista()
        
        if not lista_processos:
            print("[AVISO] Nenhum processo foi encontrado para este CPF.")
            tabela_sheets.atualizar_celula(f"L{indice}", "BRANCO - SEM PROCESSO")
            continue

        # Limitador do escopo da POC: Executa o ciclo completo nos 2 primeiros da lista
        processos_poc = lista_processos[:2]
        print(f"[INFO] Iniciando varredura da POC em {len(processos_poc)} processos principais.")

        for idx, proc in enumerate(processos_poc, start=1):
            print(f"\n[CONFERÊNCIA {idx}] Acessando link: {proc['titulo']}")
            
            # Executa a navegação isolada em outra guia
            texto_processo = acoes.analisar_conteudo_processo(proc['url'])
            
            # VALIDAÇÃO 1: O polo passivo obrigatoriamente precisa ser o INSS
            if "INSS" not in texto_processo and "INSTITUTO NACIONAL DO SEGURO SOCIAL" not in texto_processo:
                print("-> Cor Planilha: BRANCO (Motivo: Não é uma ação movida contra o INSS)")
                tabela_sheets.atualizar_celula(f"L{indice}", "BRANCO")
                continue
                
            # VALIDAÇÃO 2: Verificação do assunto / tese de Atividade Concomitante
            termos_tese = ["CONCOMITANTE", "ART. 32", "LEI 8.213", "TEMA 1070"]
            possui_tese = any(termo in texto_processo for termo in termos_tese)
            
            if not possui_tese:
                print("-> Cor Planilha: BRANCO (Motivo: Ação contra o INSS, mas trata de outra tese jurídica)")
                tabela_sheets.atualizar_celula(f"L{indice}", "BRANCO")
                continue
                
            # VALIDAÇÃO 3: Análise do dispositivo da Sentença/Decisão
            # Indicadores de Sentença SEM Resolução de Mérito
            termos_sem_merito = ["SEM RESOLUÇÃO", "SEM JULGAMENTO DO MÉRITO", "DESISTÊNCIA", "EXTINGO SEM", "ART. 485"]
            # Indicadores de Sentença COM Resolução de Mérito
            termos_com_merito = ["PROCEDENTE", "IMPROCEDENTE", "PARCIAL PROCEDÊNCIA", "DECADÊNCIA", "PRESCRIÇÃO", "ART. 487"]

            if any(termo in texto_processo for termo in termos_sem_merito):
                print("-> Cor Planilha: AMARELO (Motivo: Tese encontrada, mas extinta SEM resolução de mérito. Viável ajuizar novamente)")
                tabela_sheets.atualizar_celula(f"L{indice}", "AMARELO")
            elif any(termo in texto_processo for termo in termos_com_merito):
                print("-> Cor Planilha: CINZA (Motivo: Descartado. Já possui sentença definitiva COM resolução de mérito)")
                tabela_sheets.atualizar_celula(f"L{indice}", "CINZA")
            else:
                print("-> Cor Planilha: BRANCO / ALERTA (Motivo: Tese localizada, mas a estrutura da decisão exige revisão manual)")
                tabela_sheets.atualizar_celula(f"L{indice}", "BRANCO")

            time.sleep(random.uniform(1.0, 2.0))


    print("\n[POC STATUS] Execução finalizada. Resultados gerados no console.")
    navegador.quit()