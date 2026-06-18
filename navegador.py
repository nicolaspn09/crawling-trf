import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

class NavegadorPy:
    def __init__(self, navegador):
        self.navegador = navegador

    def _obter_elemento(self, tipo_dado, elemento, timer):
        """Método auxiliar interno para evitar repetição de código (DRY)"""
        by_map = {
            "xpath": By.XPATH,
            "id": By.ID,
            "class": By.CLASS_NAME
        }
        if tipo_dado not in by_map:
            raise ValueError(f"Tipo de dado inválido: {tipo_dado}")
            
        return WebDriverWait(self.navegador, timer).until(
            EC.presence_of_element_located((by_map[tipo_dado], elemento))
        )

    def clicar(self, tipo_dado, elemento, timer=60):
        elemento_pagina = self._obter_elemento(tipo_dado, elemento, timer)
        
        # Move o mouse simulado até o elemento com um pequeno offset randômico para mimetizar humanos
        actions = ActionChains(self.navegador)
        actions.move_to_element(elemento_pagina).perform()
        time.sleep(random.uniform(0.15, 0.4))
        
        # Executa o clique nativo via driver (Gera evento isTrusted = true)
        elemento_pagina.click()

    def obtem_informacao(self, tipo_dado, elemento, timer=60):
        elemento_pagina = self._obter_elemento(tipo_dado, elemento, timer)
        return elemento_pagina.text

    def obter_informacao_atributo(self, tipo_dado, elemento, atributo, timer=60):
        elemento_pagina = self._obter_elemento(tipo_dado, elemento, timer)
        return elemento_pagina.get_attribute(atributo)

    def combobox(self, tipo_dado, elemento, index, timer=60):
        combobox = self._obter_elemento(tipo_dado, elemento, timer)
        
        # Move até o combobox antes de interagir
        actions = ActionChains(self.navegador)
        actions.move_to_element(combobox).perform()
        time.sleep(random.uniform(0.2, 0.5))
        
        select = Select(combobox)
        select.select_by_index(index)

    def adicionar_informacao(self, tipo_dado, elemento, valor, timer=60):
        elemento_pagina = self._obter_elemento(tipo_dado, elemento, timer)
        
        # Foca no campo de forma nativa
        actions = ActionChains(self.navegador)
        actions.move_to_element(elemento_pagina).click().perform()
        time.sleep(random.uniform(0.1, 0.3))
        
        # Limpa o campo se houver lixo residual de forma segura
        elemento_pagina.clear()
        time.sleep(0.1)
        
        # Digitação humanizada: insere caractere por caractere com intervalo variável
        for caractere in valor:
            elemento_pagina.send_keys(caractere)
            time.sleep(random.uniform(0.05, 0.15))

    def aguardar_sucesso_cloudflare(self, timeout_captcha=30):
        """
        Detecta o iframe do Cloudflare Turnstile, aguarda a validação passiva
        ficar verde ('Sucesso!') e retorna o controle para a página principal.
        """
        # 1. Procura o iframe do Cloudflare instalado na página
        try:
            iframe_cloudflare = WebDriverWait(self.navegador, 10).until(
                EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'cloudflare')]"))
            )
            # Alterna o foco do driver para dentro do iframe
            self.navegador.switch_to.frame(iframe_cloudflare)
        except Exception:
            # Se não achar o iframe, pode ser que o Cloudflare não tenha disparado nesta requisição
            return

        # 2. Aguarda até que o elemento com id 'success-text' contenha a palavra 'Sucesso!'
        try:
            WebDriverWait(self.navegador, timeout_captcha).until(
                EC.text_to_be_present_in_element((By.ID, "success-text"), "Sucesso!")
            )
            print("[INFO] Cloudflare Turnstile validado com sucesso!")
        except Exception:
            raise TimeoutError("O Cloudflare não validou o acesso dentro do tempo limite.")
        finally:
            # 3. CRÍTICO: Retorna o foco do driver para a página principal (fora do iframe)
            self.navegador.switch_to.default_content()

    def obter_links_da_lista(self):
        """
        Coleta dinamicamente os links dos processos baseando-se na árvore real do DOM
        identificada nos prints image_3cf4cc.png e image_3cf4c3.png.
        """
        # Elemento pai real identificado no console do desenvolvedor dos prints
        elementos = self.navegador.find_elements(By.XPATH, "//div[@id='divConteudo']/a")
        
        dados_processos = []
        for el in elementos:
            href = el.get_attribute("href")
            texto = el.text
            
            # Valida se o link possui o parâmetro de pesquisa e ignora o botão 'Nova Consulta'
            if href and "txtValor=" in href and "Nova Consulta" not in texto:
                dados_processos.append({"titulo": texto, "url": href})
                
        return dados_processos

    def analisar_conteudo_processo(self, url_processo):
        """
        Abre o href do processo em uma nova aba nativa para preservar a tela de listagem,
        extrai o conteúdo textual e retorna para a aba de origem de forma segura.
        """
        # 1. Salva o identificador único da aba atual (a lista de processos)
        aba_principal = self.navegador.current_window_handle
        
        # 2. Cria uma nova aba de forma nativa. 
        # O Selenium abre a aba E já muda o foco do robô para ela automaticamente.
        self.navegador.switch_to.new_window('tab')
        
        # 3. Navega na URL do processo dentro da nova aba isolada
        self.navegador.get(url_processo)
        
        # Tempo de segurança para o carregamento dos dados internos do processo/eproc
        time.sleep(random.uniform(2.0, 3.5)) 
        
        # Captura o corpo de texto completo da página do processo para a varredura
        texto_pagina = self.navegador.find_element(By.TAG_NAME, "body").text.upper()
        
        # 4. Fecha apenas a aba atual de análise
        self.navegador.close()
        
        # 5. CRÍTICO: Devolve o foco do driver explicitamente para a listagem principal
        self.navegador.switch_to.window(aba_principal)
        
        return texto_pagina