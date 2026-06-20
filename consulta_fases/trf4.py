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
    time.sleep(random.uniform(1.0, 1.8))
    
    acoes = NavegadorPy(navegador=navegador)
    
    # 2. Seleciona ComboBox Forma
    acoes.combobox(elemento="selForma", tipo_dado="id", timer=20, index=3)
    time.sleep(random.uniform(0.6, 1.2))
    
    # 3. Seleciona ComboBox Origem
    acoes.combobox(elemento="selOrigem", tipo_dado="id", timer=20, index=2)
    time.sleep(random.uniform(0.5, 1.0))
    
    # 4. Input com digitação humana (caractere por caractere via navegador.py)
    acoes.adicionar_informacao(elemento="txtValor", tipo_dado="id", valor="312.748.119-53", timer=20)
    time.sleep(random.uniform(0.2, 0.5))
    
    # 5. Checkbox
    acoes.clicar(elemento="chkMostrarBaixados", tipo_dado="id", timer=20)
    time.sleep(random.uniform(0.8, 1.5))
    
    # 6. Botão Enviar de forma limpa
    acoes.clicar(elemento="botaoEnviar", tipo_dado="id", timer=20)

    time.sleep(random.uniform(0.8, 1.5))

    # --- BLOCO DE INTERCEPTAÇÃO DO CAPTCHA ---
    # O script faz uma pausa e aguarda o selo de sucesso aparecer dentro do iframe
    acoes.aguardar_sucesso_cloudflare(timeout_captcha=30)
    time.sleep(random.uniform(0.5, 1.2))
    
    # 6. Botão Continuar/Enviar final (Usando o XPath mapeado por você)
    acoes.clicar(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=20)

    time.sleep(random.uniform(0.8, 1.5)) # Aguarda abrir a tela de resultados (image_3d07ce.png)

    # --- INÍCIO DA ETAPA DE CONSUILTA DE FASES ---
    print("[INFO] Coletando lista de processos carregados...")
    lista_processos = acoes.obter_links_da_lista()
    
    if not lista_processos:
        print("[AVISO] Nenhum processo foi encontrado para este CPF.")
        navegador.quit()
        exit()

    print(f"[INFO] Mapeamento iniciado para todos os {len(lista_processos)} processos.")

    for idx, proc in enumerate(lista_processos, start=1):
        print("\n" + "="*80)
        print(f"[PROCESSO {idx}/{len(lista_processos)}] Identificador: {proc['titulo']}")
        print(f"Link de Acesso: {proc['url']}")
        
        # Executa a navegação isolada em outra guia e faz a varredura completa das fases
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

    print("\n[STATUS] Varredura concluída. Todos os processos e fases foram exibidos no console.")
    navegador.quit()
