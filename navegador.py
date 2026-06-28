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
            iframe_cloudflare = WebDriverWait(self.navegador, timeout_captcha).until(
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
        Coleta dinamicamente os links dos processos baseando-se na árvore real do DOM.
        """
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
        Abre o href do processo em uma nova aba nativa, extrai os detalhes chave (strong[1], [2], [3], [8]),
        clica para mostrar todas as fases, aguarda e extrai a tabela de fases do processo (seq, data, movimento, documentos),
        e retorna as informações de forma estruturada.
        """
        # 1. Salva o identificador único da aba atual (a lista de processos)
        aba_principal = self.navegador.current_window_handle
        
        # 2. Cria uma nova aba de forma nativa e muda o foco para ela
        self.navegador.switch_to.new_window('tab')
        
        # 3. Navega na URL do processo dentro da nova aba isolada
        self.navegador.get(url_processo)
        
        # Tempo de segurança para o carregamento
        time.sleep(random.uniform(2.0, 3.5)) 
        
        # 4. Coleta de forma dinâmica todos os elementos strong no container de detalhes
        dados_principais = {}
        try:
            elementos_strong = self.navegador.find_elements(By.XPATH, "/html/body/div[1]/section/div[7]/div/strong")
            for idx, elemento_strong in enumerate(elementos_strong, start=1):
                try:
                    label = elemento_strong.text.strip().replace(":", "")
                    if not label:
                        label = f"Campo_{idx}"
                    
                    # Executa JS para obter todo o texto imediatamente a seguir do strong (nó irmão de texto)
                    valor = self.navegador.execute_script(
                        "var node = arguments[0].nextSibling; "
                        "var text = ''; "
                        "while (node && node.nodeType === 3) { "
                        "    text += node.textContent; "
                        "    node = node.nextSibling; "
                        "} "
                        "return text.trim();", 
                        elemento_strong
                    )
                    dados_principais[label] = valor
                except Exception:
                    pass
        except Exception as e:
            print(f"[Erro] Falha ao coletar dados principais dinamicamente: {e}")

        # 5. Clica no link "Clique aqui para mostrar todas as fases"
        # Normalmente no XPath: /html/body/div[1]/section/div[7]/div/a[3]
        try:
            link_fases = WebDriverWait(self.navegador, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/section/div[7]/div/a[3]"))
            )
            self.navegador.execute_script("arguments[0].click();", link_fases)
        except Exception:
            # Alternativa amigável baseada no texto do elemento se o XPath mudar
            try:
                link_fases = WebDriverWait(self.navegador, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'mostrar todas as fases') or contains(text(), 'Mostrar todas as fases')]"))
                )
                self.navegador.execute_script("arguments[0].click();", link_fases)
            except Exception as ex:
                print(f"[Aviso] Link 'Clique aqui para mostrar todas as fases' não localizado: {ex}")

        # Aguarda um pequeno momento para o carregamento das fases na tela
        time.sleep(random.uniform(1.0, 2.0))

        # 6. Aguarda e parseia a tabela de fases (/html/body/div[1]/section/div[7]/div/table)
        lista_fases = []
        try:
            tabela = WebDriverWait(self.navegador, 15).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/section/div[7]/div/table"))
            )
            
            linhas = tabela.find_elements(By.TAG_NAME, "tr")
            for linha in linhas:
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if not colunas:
                    continue # Ignora a linha de cabeçalho
                
                seq = colunas[0].text.strip() if len(colunas) > 0 else ""
                data = colunas[1].text.strip() if len(colunas) > 1 else ""
                movimento = colunas[2].text.strip() if len(colunas) > 2 else ""
                
                # Quarta coluna: 'documentos'
                doc_links = []
                if len(colunas) > 3:
                    links_elementos = colunas[3].find_elements(By.TAG_NAME, "a")
                    for link_el in links_elementos:
                        href = link_el.get_attribute("href")
                        texto_link = link_el.text.strip()
                        if href:
                            doc_links.append({"texto": texto_link, "url": href})
                
                lista_fases.append({
                    "seq": seq,
                    "data": data,
                    "movimento": movimento,
                    "documentos": doc_links
                })
        except Exception as e:
            print(f"[Erro] Falha ao extrair tabela de fases do processo: {e}")

        # 7. Fecha apenas a aba atual de análise
        self.navegador.close()
        
        # 8. Devolve o foco do driver explicitamente para a listagem principal
        self.navegador.switch_to.window(aba_principal)
        
        return dados_principais, lista_fases
