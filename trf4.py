import time
import random
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




if __name__ == "__main__":
    navegador, firefox_pids = inicia_navegador()
    acessa_site(navegador=navegador)

    # Pausa inicial para simular a leitura humana da página inicial
    time.sleep(random.uniform(2.0, 3.5))
    
    acoes = NavegadorPy(navegador=navegador)
    
    # 1. Abre modal/consulta inicial
    acoes.clicar(elemento="/html/body/div[6]/div/div/a/img", tipo_dado="xpath", timer=20)
    time.sleep(random.uniform(1.0, 1.8))
    
    # 2. Seleciona ComboBox Forma
    acoes.combobox(elemento="selForma", tipo_dado="id", timer=20, index=3)
    time.sleep(random.uniform(0.6, 1.2))
    
    # 3. Seleciona ComboBox Origem
    acoes.combobox(elemento="selOrigem", tipo_dado="id", timer=20, index=2)
    time.sleep(random.uniform(0.5, 1.0))
    
    # 4. Input com digitação humana (caractere por caractere via navegador.py)
    acoes.adicionar_informacao(elemento="txtValor", tipo_dado="id", valor="312.748.119-53", timer=20)
    time.sleep(random.uniform(0.7, 1.4))
    
    # 5. Checkbox
    acoes.clicar(elemento="chkMostrarBaixados", tipo_dado="id", timer=20)
    time.sleep(random.uniform(0.8, 1.5))
    
    # 6. Botão Enviar de forma limpa
    acoes.clicar(elemento="botaoEnviar", tipo_dado="id", timer=20)

    # --- BLOCO DE INTERCEPTAÇÃO DO CAPTCHA ---
    # O script faz uma pausa e aguarda o selo de sucesso aparecer dentro do iframe
    acoes.aguardar_sucesso_cloudflare(timeout_captcha=30)
    time.sleep(random.uniform(0.5, 1.2))
    
    # 6. Botão Continuar/Enviar final (Usando o XPath mapeado por você)
    acoes.clicar(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=20)

    time.sleep(random.uniform(2.0, 3.5)) # Aguarda abrir a tela de resultados (image_3d07ce.png)

    # --- INÍCIO DA ETAPA DA POC ENVIADA ---
    print("[INFO] Coletando lista de processos carregados...")
    lista_processos = acoes.obter_links_da_lista()
    
    print("[INFO] Mapeando processos gerados pelo CPF...")
    lista_processos = acoes.obter_links_da_lista()
    
    if not lista_processos:
        print("[AVISO] Nenhum processo foi encontrado para este CPF.")
        navegador.quit()
        exit()

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
            continue
            
        # VALIDAÇÃO 2: Verificação do assunto / tese de Atividade Concomitante
        termos_tese = ["CONCOMITANTE", "ART. 32", "LEI 8.213", "TEMA 1070"]
        possui_tese = any(termo in texto_processo for termo in termos_tese)
        
        if not possui_tese:
            print("-> Cor Planilha: BRANCO (Motivo: Ação contra o INSS, mas trata de outra tese jurídica)")
            continue
            
        # VALIDAÇÃO 3: Análise do dispositivo da Sentença/Decisão
        # Indicadores de Sentença SEM Resolução de Mérito
        termos_sem_merito = ["SEM RESOLUÇÃO", "SEM JULGAMENTO DO MÉRITO", "DESISTÊNCIA", "EXTINGO SEM", "ART. 485"]
        # Indicadores de Sentença COM Resolução de Mérito
        termos_com_merito = ["PROCEDENTE", "IMPROCEDENTE", "PARCIAL PROCEDÊNCIA", "DECADÊNCIA", "PRESCRIÇÃO", "ART. 487"]

        if any(termo in texto_processo for termo in termos_sem_merito):
            print("-> Cor Planilha: AMARELO (Motivo: Tese encontrada, mas extinta SEM resolução de mérito. Viável ajuizar novamente)")
        elif any(termo in texto_processo for termo in termos_com_merito):
            print("-> Cor Planilha: CINZA (Motivo: Descartado. Já possui sentença definitiva COM resolução de mérito)")
        else:
            print("-> Cor Planilha: BRANCO / ALERTA (Motivo: Tese localizada, mas a estrutura da decisão exige revisão manual)")
            
        time.sleep(random.uniform(1.5, 2.5))

    print("\n[POC STATUS] Execução finalizada. Resultados gerados no console.")
    navegador.quit()