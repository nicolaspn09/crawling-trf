import os
import time
import random
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from acessaSite import AcessaSite
from conectaChrome import ChromeStealthManager
from navegador import NavegadorPy
from GoogleSheets import GoogleSheets
from Database import Database

class BotTRF4:
    def __init__(self):
        # A inicialização do banco não deve ocorrer no loop, mas sim na classe
        pass
        
    def _inicia_navegador(self):
        navegador, firefox_pids = ChromeStealthManager().acessa_navegador()
        return navegador, firefox_pids

    def _acessa_site(self, navegador):
        url = AcessaSite().site("sc")
        # Força o recarregamento total da página saindo dela e voltando
        navegador.get("about:blank")
        time.sleep(0.1)
        navegador.get(url)

    def _validar_cpf(self, cpf):
        if "." in str(cpf) or "-" in str(cpf):
            cpf = str(cpf).replace(".", "").replace("-", "").strip()
        cpf = ''.join(filter(str.isdigit, cpf))
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        dig1 = (soma * 10 % 11) % 10
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        dig2 = (soma * 10 % 11) % 10
        return cpf[-2:] == f"{dig1}{dig2}"

    def _tratar_alerta_popup(self, navegador, timeout=3):
        try:
            alert = WebDriverWait(navegador, timeout).until(EC.alert_is_present())
            texto_alerta = alert.text
            alert.accept()
            return True, texto_alerta
        except Exception:
            return False, None

    def executar(self, lista_dados, atualizar_status_callback=None, estado="SC"):
        db = Database()
        navegador, firefox_pids = self._inicia_navegador()
        
        indice_atual = 2
        tentativas_cpf_global = 0
        
        while indice_atual < len(lista_dados) + 2:
            linha = lista_dados[indice_atual - 2]
            indice = indice_atual
            
            try:
                # Extrai os dados básicos com segurança (caso a linha não tenha todas as colunas)
                cpf = linha[0].strip() if len(linha) > 0 else ""

                # if "47556722953" not in str(cpf).replace("-", "").replace(".", "") or "44827229953" not in str(cpf).replace("-", "").replace(".", ""):
                #     continue
                
                nome = str(linha[2]).strip() if len(linha) > 2 and linha[2] is not None else ""
                ddd = str(linha[13]).strip() if len(linha) > 13 and linha[13] is not None else ""
                telefone = str(linha[14]).strip() if len(linha) > 14 and linha[14] is not None else ""           
                telefone_completo = f"{ddd}{telefone}".strip()

                # Valida o CPF antes de prosseguir
                if not self._validar_cpf(cpf):
                    print(f"[AVISO] CPF inválido ou em branco: '{cpf}'. Pulando linha.")
                    indice_atual += 1
                    tentativas_cpf_global = 0
                    continue

                # Limpa o CPF para manter padrão no banco de dados (apenas números)
                cpf_limpo = ''.join(filter(str.isdigit, cpf))

                # Obtém ou cria o cliente no banco para termos o cliente_id VERDADEIRO (ID numérico interno do Postgres)
                cliente_id = db.obter_ou_criar_cliente(cpf=cpf_limpo, nome=nome, telefone=telefone_completo)
                
                def fazer_pesquisa_eproc(valor_busca, indice_origem=3):
                    from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
                    
                    tentativas_globais = 0
                    while tentativas_globais < 8:
                        try:
                            self._acessa_site(navegador=navegador)
                            time.sleep(random.uniform(0.5, 1.0))
                            
                            acoes = NavegadorPy(navegador=navegador)
                            
                            acoes.combobox(elemento="selForma", tipo_dado="id", timer=20, index=indice_origem)
                            time.sleep(random.uniform(0.2, 0.5))
                            
                            try:
                                if estado == "SC":
                                    acoes.combobox(elemento="selOrigem", tipo_dado="id", timer=5, index=3)
                                elif estado == "RS":
                                    acoes.combobox(elemento="selOrigem", tipo_dado="id", timer=5, index=4)
                                elif estado == "PR":
                                    acoes.combobox(elemento="selOrigem", tipo_dado="id", timer=5, index=2)
                                time.sleep(random.uniform(0.2, 0.4))
                            except Exception:
                                pass # O campo selOrigem n\u00e3o existe ou fica oculto quando a busca \u00e9 pelo Nome
                            
                            acoes.adicionar_informacao(elemento="txtValor", tipo_dado="id", valor=valor_busca, timer=20)
                            time.sleep(random.uniform(0.1, 0.3))
                            
                            try:
                                acoes.clicar(elemento="chkMostrarBaixados", tipo_dado="id", timer=5)
                                time.sleep(random.uniform(0.1, 0.3))
                            except Exception:
                                pass
                            

                            alerta_texto_encontrado = ""
                            clicou_com_sucesso = False
                            
                            for tentativa_clique in range(6):
                                acoes.clicar(elemento="botaoEnviar", tipo_dado="id", timer=10)
                                
                                try:
                                    alerta = WebDriverWait(navegador, 10).until(EC.alert_is_present())
                                    texto = alerta.text
                                    if "captcha" in texto.lower() or "aguarde" in texto.lower():
                                        alerta.accept()
                                        time.sleep(4)
                                        print(f"    [Aviso] Aguardando captcha resolver sozinho... (Click {tentativa_clique+1}/6)")
                                        try:
                                            # Tenta interagir ativamente com o Cloudflare se houver checkbox na tela
                                            # IMPORTANTE: No eproc, quando dá esse alerta, a página atualiza pra uma página de captcha do Cloudflare
                                            acoes.aguardar_sucesso_cloudflare(timeout_captcha=20)
                                        except Exception:
                                            pass
                                        time.sleep(3)
                                        # NÃO usamos continue para o while principal, só volta o laço for
                                    else:
                                        alerta_texto_encontrado = texto
                                        alerta.accept()
                                        clicou_com_sucesso = True
                                        break
                                except Exception:
                                    # Se não houver alerta após o clique, deu tudo certo!
                                    clicou_com_sucesso = True
                                    break
                            
                            if not clicou_com_sucesso:
                                # Se tentou 6 vezes clicar e as 6 deu captcha, então sim a gente recarrega
                                tentativas_globais += 1
                                continue
                            
                            time.sleep(random.uniform(0.5, 1.0))
                            return acoes, alerta_texto_encontrado
                            
                        except Exception as e:
                            texto_inesperado = str(e)
                            texto_alerta_puro = ""
                            try:
                                alerta = navegador.switch_to.alert
                                texto_alerta_puro = alerta.text
                                texto_inesperado += " " + texto_alerta_puro
                                alerta.accept()
                            except Exception:
                                pass
                            
                            is_captcha = "captcha" in texto_inesperado.lower() or "aguarde" in texto_inesperado.lower()
                            is_alert = "alert" in texto_inesperado.lower() or texto_alerta_puro != ""

                            if is_captcha:
                                print(f"    [Aviso] Alerta de captcha bloqueou a página. Esperando 5s... (Tentativa {tentativas_globais+1}/8)")
                                time.sleep(5)
                                tentativas_globais += 1
                                continue
                            elif is_alert:
                                # Era um alerta diferente (ex: Nenhum processo encontrado)
                                return acoes, texto_alerta_puro if texto_alerta_puro else str(texto_inesperado)
                            else:
                                # Era uma exceção real (ex: Timeout, Elemento não encontrado) e não um alerta
                                raise e
                                
                    return acoes, ""

                print(f"\n[CONSULTA] Iniciando busca para o CPF: {cpf}")
                acoes, alerta_da_pesquisa = fazer_pesquisa_eproc(cpf, indice_origem=3)

                from selenium.webdriver.common.by import By
                from selenium.common.exceptions import UnexpectedAlertPresentException

                tem_alerta = False
                texto_alerta = alerta_da_pesquisa if alerta_da_pesquisa else ""
                erro_site = False
                lista_processos = []
                
                if alerta_da_pesquisa:
                    tem_alerta = True
                else:
                    # Espera ativa robusta para o resultado da pesquisa carregar
                    espera_resultado = 0
                    while espera_resultado < 25:
                        try:
                            # 1. Verifica se apareceu um alerta nativo de 'Nada Consta'
                            alert = navegador.switch_to.alert
                            texto_alerta = alert.text
                            alert.accept()
                            tem_alerta = True
                            break
                        except:
                            pass
                            
                        # 2. Verifica se a tabela de múltiplos processos carregou
                        if len(navegador.find_elements(By.XPATH, "//*[@id='divInfraAreaTabela']")) > 0:
                            break
                            
                        # 3. Verifica se o painel de detalhes carregou (redirecionamento direto para processo único)
                        if len(navegador.find_elements(By.XPATH, "//*[@id='divInfraAreaDadosProcesso']")) > 0:
                            break
                            
                        # 4. Verifica se a página parou num Cloudflare pós-pesquisa
                        if len(navegador.find_elements(By.XPATH, "//iframe[contains(@src, 'cloudflare')]")) > 0:
                            try:
                                print("    [ANTI-CAPTCHA] Cloudflare detectado aguardando resultado...")
                                acoes.aguardar_sucesso_cloudflare(timeout_captcha=20)
                            except:
                                pass
                                
                        time.sleep(1)
                        espera_resultado += 1
                        
                    if espera_resultado >= 25 and not tem_alerta:
                        print("    [ERRO] Timeout aguardando resultado da pesquisa do CPF.")
                        erro_site = True
                        try:
                            navegador.save_screenshot(f"/tmp/erro_site_{cpf_limpo}.png")
                        except:
                            pass

                if not tem_alerta and not erro_site:
                    lista_processos = acoes.obter_links_da_lista()
                    
                    # CORREÇÃO: Se E-proc redirecionou diretamente para os detalhes do processo (1 único resultado)
                    if not lista_processos:
                        try:
                            from selenium.webdriver.common.by import By
                            # Verifica se estamos na tela de detalhes do processo procurando pelo painel de ações ou capa
                            is_detalhes = len(navegador.find_elements(By.XPATH, "//a[contains(text(), 'mostrar todas as fases') or contains(text(), 'Mostrar todas as fases')]")) > 0
                            is_detalhes = is_detalhes or len(navegador.find_elements(By.XPATH, "//*[@id='divInfraAreaDadosProcesso']")) > 0
                            if is_detalhes:
                                print(f"    [INFO] Redirecionamento direto detectado para o processo único!")
                                numero_unico = "Processo Único"
                                try:
                                    # Tenta pegar o número do processo do topo da página se existir
                                    topo = navegador.find_elements(By.XPATH, "//*[@id='txtNumProcesso']")
                                    if topo and topo[0].text: numero_unico = topo[0].text
                                except: pass
                                lista_processos = [{'url': navegador.current_url, 'titulo': numero_unico}]
                        except:
                            pass

                # DUPLA CHECAGEM: Se não encontrou pelo CPF, tenta pelo Nome
                if tem_alerta or not lista_processos:
                    print(f"[RESULTADO CPF] CPF {cpf}: Nada Consta ({texto_alerta}). Tentando dupla checagem pelo NOME: {nome}")
                    # Delay anti-captcha: o Cloudflare do TRF4 bloqueia requisições
                    # em sequência rápida. Esperar entre 3-8s evita o rate-limiting.
                    delay = random.uniform(3.0, 8.0)
                    print(f"    [ANTI-CAPTCHA] Aguardando {delay:.1f}s antes da dupla checagem...")
                    time.sleep(delay)
                    acoes, alerta_nome = fazer_pesquisa_eproc(nome, indice_origem=2)
                    
                    tem_alerta = False
                    texto_alerta = alerta_nome if alerta_nome else ""
                    erro_site = False
                    lista_processos_nome = []
                    
                    if alerta_nome:
                        tem_alerta = True
                    else:
                        espera_resultado = 0
                        while espera_resultado < 25:
                            try:
                                alert = navegador.switch_to.alert
                                texto_alerta = alert.text
                                alert.accept()
                                tem_alerta = True
                                break
                            except:
                                pass
                                
                            if len(navegador.find_elements(By.XPATH, "//*[@id='divInfraAreaTabela']")) > 0:
                                break
                                
                            if len(navegador.find_elements(By.XPATH, "//*[@id='divInfraAreaDadosProcesso']")) > 0:
                                break
                                
                            if len(navegador.find_elements(By.XPATH, "//iframe[contains(@src, 'cloudflare')]")) > 0:
                                try:
                                    print("    [ANTI-CAPTCHA] Cloudflare detectado aguardando resultado Nome...")
                                    acoes.aguardar_sucesso_cloudflare(timeout_captcha=20)
                                except:
                                    pass
                                    
                            time.sleep(1)
                            espera_resultado += 1
                            
                        if espera_resultado >= 25 and not tem_alerta:
                            print("    [ERRO] Timeout aguardando resultado da pesquisa por Nome.")
                            erro_site = True
                            
                    if not tem_alerta and not erro_site:
                        from selenium.webdriver.common.by import By
                        from selenium.common.exceptions import UnexpectedAlertPresentException
                        
                        try:
                            links_conteudo = navegador.find_elements(By.XPATH, "//div[@id='divConteudo']/a")
                            
                            # CORREÇÃO: Se redirecionou direto para o processo único na pesquisa por NOME
                            if not links_conteudo:
                                try:
                                    is_detalhes = len(navegador.find_elements(By.XPATH, "//a[contains(text(), 'mostrar todas as fases') or contains(text(), 'Mostrar todas as fases')]")) > 0
                                    is_detalhes = is_detalhes or len(navegador.find_elements(By.XPATH, "//*[@id='divInfraAreaDadosProcesso']")) > 0
                                    if is_detalhes:
                                        print(f"    [INFO] Redirecionamento direto detectado para o processo único (Pesquisa por Nome)!")
                                        numero_unico = "Processo Único"
                                        try:
                                            topo = navegador.find_elements(By.XPATH, "//*[@id='txtNumProcesso']")
                                            if topo and topo[0].text: numero_unico = topo[0].text
                                        except: pass
                                        lista_processos_nome = [{'url': navegador.current_url, 'titulo': numero_unico}]
                                except:
                                    pass
                                
                        except UnexpectedAlertPresentException as e:
                            print(f"    [ERRO] Alerta inesperado detectado tardiamente durante varredura: {e.alert_text}")
                            
                            texto_alerta = str(e.alert_text).lower()
                            if "captcha" in texto_alerta or "aguarde" in texto_alerta:
                                print("    [DEBUG] Resolvendo captcha tardio do Cloudflare...")
                                try:
                                    navegador.switch_to.alert.accept()
                                except: pass
                                time.sleep(4)
                                acoes.aguardar_sucesso_cloudflare(timeout_captcha=20)
                                time.sleep(5)
                                # Tenta buscar os links novamente apos resolver o captcha
                                links_conteudo = navegador.find_elements(By.XPATH, "//div[@id='divConteudo']/a")
                            else:
                                try:
                                    import os
                                    script_dir = os.path.dirname(os.path.abspath(__file__))
                                    navegador.save_screenshot(os.path.join(script_dir, f"erro_captcha_{cpf_limpo}.png"))
                                except: pass
                                raise ValueError(f"Alerta tardio bloqueou a página: {e.alert_text}")
                            
                        is_homonimos = any("CPF/CNPJ:" in l.text for l in links_conteudo)
                        
                        if is_homonimos:
                            cpf_4_digitos = cpf_limpo[:4]
                            nome_buscado = nome.upper().strip()
                            link_processos_parte = None
                            
                            for hm in links_conteudo:
                                texto_hm = hm.text.upper()
                                if "CPF/CNPJ:" in texto_hm:
                                    # Valida Nome exato e os 4 primeiros dígitos do CPF mascarado
                                    if nome_buscado in texto_hm and cpf_4_digitos in texto_hm:
                                        link_processos_parte = hm.get_attribute("href")
                                        print(f"       -> Homônimo validado com sucesso: {texto_hm}")
                                        break
                                        
                            if link_processos_parte:
                                navegador.get(link_processos_parte)
                                time.sleep(random.uniform(0.5, 1.0))
                                lista_processos_nome = acoes.obter_links_da_lista()
                            else:
                                print(f"       -> Nome {nome}: Nenhum homônimo correspondente (Nome exato + 4 digitos CPF).")
                        else:
                            # Se não for a tela de homônimos, pega a lista direto (se já não foi preenchida pelo redirect direto)
                            if not lista_processos_nome:
                                lista_processos_nome = acoes.obter_links_da_lista()
                            
                        if lista_processos_nome:
                            print(f"       -> Dupla checagem encontrou processos pelo nome!")
                            lista_processos = lista_processos_nome
                        else:
                            print(f"       -> Nome {nome}: Nenhum processo encontrado na dupla checagem.")

                if tem_alerta and not lista_processos:
                    print(f"[RESULTADO FINAL] CPF {cpf} e NOME {nome}: Não foi encontrado. (Alerta: {texto_alerta})")
                    if atualizar_status_callback:
                        atualizar_status_callback(indice, "BRANCO - NADA CONSTA", "", "")
                    db.inserir_oportunidade(cliente_id, "BRANCO", "NADA CONSTA", "Descartado")
                    continue
                    
                if erro_site and not lista_processos:
                    tentativas_cpf_global += 1
                    if tentativas_cpf_global > 3:
                        print("    [AVISO] Muitas tentativas fracassadas. Assumindo Nada Consta e prosseguindo.")
                        # Trata como Nada Consta após 3 falhas para evitar loop infinito
                        lista_processos = []
                        erro_site = False
                    else:
                        print(f"Site com erro na pesquisa de CPF e Nome! Aguardando para nova tentativa... (Tentativa {tentativas_cpf_global}/3)")
                        time.sleep(random.uniform(5.0, 10.0))
                        continue

                if not lista_processos:
                    print(f"[AVISO FINAL] Nenhum processo foi encontrado para o CPF/NOME {cpf}.")
                    if atualizar_status_callback:
                        atualizar_status_callback(indice, "BRANCO - NADA CONSTA", "", "")
                    db.inserir_oportunidade(cliente_id, "BRANCO - NADA CONSTA", "Lista de processos vazia", "Descartado")
                    indice_atual += 1
                    tentativas_cpf_global = 0
                    continue

                # Removemos o limitador da POC, varrendo TODOS os processos.
                processos = lista_processos
                print(f"[INFO] Iniciando varredura em {len(processos)} processos encontrados.")

                for idx, proc in enumerate(processos, start=1):
                    numero_processo_bruto = proc['titulo']
                    import re
                    match_num = re.search(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}', numero_processo_bruto)
                    numero_processo_limpo = match_num.group(0) if match_num else numero_processo_bruto

                    print(f"\n[CONFERÊNCIA {idx}] Acessando link: {numero_processo_bruto}")
                    
                    # Nova versão do analisar_conteudo_processo que retorna dados tabelados
                    dados_principais, lista_fases = acoes.analisar_conteudo_processo(proc['url'])
                    
                    # Transformamos os dicionários/listas em uma grande string para validar a lógica das palavras
                    texto_processo = str(dados_principais).upper() + " " + str(lista_fases).upper()
                    
                    # VALIDAÇÃO 1: O polo passivo obrigatoriamente precisa ser o INSS
                    polo_passivo = dados_principais.get('Réu', 'Desconhecido')
                    assunto_processo = dados_principais.get('Assuntos', dados_principais.get('Assunto', ''))
                    if not assunto_processo.strip():
                        assunto_processo = "Não informado"
                        
                    is_contra_inss = ("INSS" in texto_processo) or ("INSTITUTO NACIONAL DO SEGURO SOCIAL" in texto_processo)
                    if is_contra_inss:
                        polo_passivo = "INSS"

                    if not is_contra_inss:
                        print("-> Cor Planilha: BRANCO (Motivo: Não é uma ação movida contra o INSS)")
                        if atualizar_status_callback:
                            atualizar_status_callback(indice, "BRANCO - Não movida contra o INSS", numero_processo_limpo, assunto_processo)
                        db.inserir_processo(cliente_id, numero_processo_limpo, link_processo=proc['url'], polo_passivo=polo_passivo, tem_tese_concomitante=False, status_merito="Descartado", assunto=assunto_processo)
                        db.inserir_oportunidade(cliente_id, "BRANCO", "Não é ação contra INSS", "Descartado")
                        continue
                        
                    # VALIDAÇÃO 2: Busca TODAS as URLs da sentença na coluna 4 daquela fase e entra nelas
                    links_sentencas = []
                    # Varre as fases de trás pra frente para pegar todas as decisões/sentenças
                    for fase in reversed(lista_fases):
                        mov = str(fase['movimento']).upper()
                        if "SENTENÇA" in mov or "DECISÃO" in mov:
                            if fase['documentos']:
                                for doc in fase['documentos']:
                                    links_sentencas.append(doc['url'])
                                # Removido o 'break' para não parar na primeira; coleta TODAS!
                    
                    possui_tese = False
                    link_principal = None
                    texto_sentenca = ""
                    texto_processo_capa = " ".join([str(f["movimento"]) for f in lista_fases]).upper()

                    if links_sentencas:
                        print(f"-> Acessando {len(links_sentencas)} link(s) da Sentença/Decisão para ler os textos originais...")
                        aba_processo = navegador.current_window_handle
                        navegador.switch_to.new_window('tab')
                        
                        termos_tese = [
                            "ATIVIDADES CONCOMITANTES", "CONTRIBUIÇÕES CONCOMITANTES", "ATIVIDADE PRINCIPAL", 
                            "ATIVIDADE SECUNDÁRIA", "EXERCÍCIO SIMULTÂNEO DE ATIVIDADES", "MÚLTIPLOS VÍNCULOS EMPREGATÍCIOS", 
                            "MÚLTIPLAS ATIVIDADES REMUNERADAS", "SALÁRIO DE CONTRIBUIÇÃO", "SOMA DOS SALÁRIOS DE CONTRIBUIÇÃO", 
                            "INCLUSÃO DE SALÁRIOS DE CONTRIBUIÇÃO", "CÔMPUTO DE CONTRIBUIÇÕES", "REVISÃO DE APOSENTADORIA", 
                            "REVISÃO DE BENEFÍCIO", "REVISÃO DA RMI", "RENDA MENSAL INICIAL (RMI)", "RECÁLCULO DA RMI", 
                            "RECÁLCULO DO BENEFÍCIO", "SALÁRIO DE BENEFÍCIO", "CÁLCULO DO BENEFÍCIO PREVIDENCIÁRIO", 
                            "REVISÃO DO CÁLCULO DA APOSENTADORIA", "ART. 32 DA LEI Nº 8.213/91", "REVISÃO PREVIDENCIÁRIA", 
                            "DIFERENÇAS VENCIDAS E VINCENDAS", "PAGAMENTO DE DIFERENÇAS DECORRENTES DA REVISÃO", 
                            "REFLEXOS FINANCEIROS DA REVISÃO", "REVISÃO DO BENEFÍCIO NB", "REVISÃO DE RENDA MENSAL INICIAL", 
                            "REVISÃO DE APOSENTADORIA", "CÁLCULO DE BENEFÍCIO PREVIDENCIÁRIO", "TEMPO DE CONTRIBUIÇÃO", 
                            "REAJUSTES E REVISÕES ESPECÍFICAS", "ALTERAÇÃO DO COEFICIENTE DE CÁLCULO", "BENEFÍCIOS EM ESPÉCIE", 
                            "DIREITO PREVIDENCIÁRIO"
                        ]
                        
                        for link in links_sentencas:
                            navegador.get(link)
                            time.sleep(random.uniform(1.0, 1.5))
                            try:
                                from selenium.webdriver.common.by import By
                                texto_extraido = str(navegador.find_element(By.TAG_NAME, "body").text).upper()
                                
                                # E-proc costuma esconder o texto do documento dentro de um iframe
                                iframes = navegador.find_elements(By.TAG_NAME, "iframe")
                                for iframe in iframes:
                                    navegador.switch_to.frame(iframe)
                                    texto_extraido += " " + str(navegador.find_element(By.TAG_NAME, "body").text).upper()
                                    navegador.switch_to.default_content()
                                
                                print(f"       -> Lidos {len(texto_extraido)} caracteres do documento.")
                                texto_sentenca += " " + texto_extraido
                                
                                # Valida se ESTE documento atual tem a tese. Se sim, marca ele como o documento correto.
                                if not possui_tese:
                                    if any(termo.upper() in texto_extraido for termo in termos_tese):
                                        possui_tese = True
                                        link_principal = link
                                        print(f"       -> Tese encontrada neste documento! Interrompendo busca em outras sentenças.")
                                        break
                            except Exception as ex:
                                print(f"       -> Erro ao ler documento: {ex}")
                                
                        navegador.close()
                        navegador.switch_to.window(aba_processo)
                        
                        if link_principal is None and links_sentencas:
                            link_principal = links_sentencas[0] # Fallback pro primeiro documento se nenhum tiver a tese
                    else:
                        print("-> Nenhuma sentença ou decisão com link encontrada nas fases.")
                        link_principal = None

                    if not possui_tese:
                        print("-> Cor Planilha: BRANCO (Motivo: Ação contra o INSS, mas NÃO encontrou a tese na sentença/decisão)")
                        if atualizar_status_callback:
                            atualizar_status_callback(indice, "BRANCO - Outra tese jurídica", numero_processo_limpo, assunto_processo)
                        db.inserir_processo(cliente_id, numero_processo_limpo, link_processo=proc['url'], polo_passivo=polo_passivo, tem_tese_concomitante=False, status_merito="Descartado", link_sentenca=link_principal, assunto=assunto_processo)
                        db.inserir_oportunidade(cliente_id, "BRANCO", "Ação contra o INSS, mas trata de outra tese jurídica", "Descartado")
                        continue
                        
                    # VALIDAÇÃO 3: Análise do dispositivo da Sentença/Decisão
                    termos_sem_merito = ["SEM RESOLUÇÃO", "SEM JULGAMENTO DO MÉRITO", "DESISTÊNCIA", "EXTINGO SEM", "ART. 485"]
                    termos_com_merito = ["PROCEDENTE", "IMPROCEDENTE", "PARCIAL PROCEDÊNCIA", "DECADÊNCIA", "PRESCRIÇÃO", "ART. 487"]

                    status_rpa = "BRANCO"
                    motivo = ""
                    fase_oportunidade = "Nova Oportunidade"
                    status_merito = "NÃO IDENTIFICADO"

                    # Checa o mérito tanto na capa do processo (movimentos) quanto no texto da sentença
                    texto_merito = texto_processo_capa + " " + texto_sentenca

                    if any(termo in texto_merito for termo in termos_sem_merito):
                        print("-> Cor Planilha: AMARELO (Motivo: Tese encontrada, mas extinta SEM resolução de mérito. Viável ajuizar novamente)")
                        status_rpa = "AMARELO - Tese localizada SEM resolução de mérito"
                        motivo = "Tese encontrada, mas extinta SEM resolução de mérito. Viável ajuizar novamente."
                        status_merito = "SEM RESOLUÇÃO"
                    elif any(termo in texto_merito for termo in termos_com_merito):
                        print("-> Cor Planilha: CINZA (Motivo: Descartado. Já possui sentença definitiva COM resolução de mérito)")
                        status_rpa = "CINZA - Descartado (Com resolução de mérito)"
                        motivo = "Descartado. Já possui sentença definitiva COM resolução de mérito."
                        status_merito = "COM RESOLUÇÃO"
                        fase_oportunidade = "Descartado"
                    else:
                        print("-> Cor Planilha: BRANCO / ALERTA (Motivo: Tese localizada, mas a estrutura da decisão exige revisão manual)")
                        status_rpa = "BRANCO - Tese localizada (Exige revisão manual)"
                        motivo = "Tese localizada, mas a estrutura da decisão exige revisão manual."
                        fase_oportunidade = "Revisão Manual"

                    if atualizar_status_callback:
                        atualizar_status_callback(indice, status_rpa, numero_processo_limpo, assunto_processo)
                    db.inserir_processo(cliente_id, numero_processo_limpo, link_processo=proc['url'], polo_passivo=polo_passivo, tem_tese_concomitante=True, status_merito=status_merito, link_sentenca=link_principal, assunto=assunto_processo)
                    db.inserir_oportunidade(cliente_id, status_rpa, motivo, fase_oportunidade)

                    time.sleep(random.uniform(1.0, 2.0))
                    
                    # Como a tese FOI localizada (seja amarelo, cinza ou branco alerta),
                    # quebramos o loop para não processar os demais processos deste CPF!
                    print(f"       -> Tese localizada! Parando de analisar processos para o CPF {cpf}.")
                    break
                    
                indice_atual += 1
                tentativas_cpf_global = 0
                continue

            except Exception as e:
                deve_quebrar_loop = False
                import traceback
                tb_str = traceback.format_exc()
                print(f"[ERRO CPF] Falha no índice {indice} (Linha {indice}): {e}")
                print(f"[PYTHON STACKTRACE]\n{tb_str}")
                
                err_msg = str(e).lower()
                if ('captcha' in err_msg or 'aguarde' in err_msg) and tentativas_cpf_global < 5:
                    tentativas_cpf_global += 1
                    print(f"    [RETRY] Tentativa {tentativas_cpf_global}/5 para o CPF {cpf}...")
                else:
                    deve_quebrar_loop = True
                    indice_atual += 1
                    tentativas_cpf_global = 0
                    if atualizar_status_callback:
                        atualizar_status_callback(indice, f"Erro na linha {indice}: {str(e)[:50]}")
                    status = f"Erro na linha {indice}: {str(e)}"

                # Resiliência Máxima: Se o script chegou aqui, o site pode estar com alertas presos
                # ou travado no Cloudflare. Para não estragar os próximos CPFs (efeito dominó),
                # nós matamos o navegador atual e abrimos um novinho em folha!
                try:
                    print(f"    [RESET] Reiniciando o navegador para limpar falhas e alertas residuais...")
                    try:
                        if hasattr(navegador, 'xvfb_display'):
                            navegador.xvfb_display.stop()
                    except:
                        pass
                    try:
                        navegador.quit()
                    except:
                        pass
                    try:
                        import os, signal
                        for pid in firefox_pids:
                            try:
                                os.kill(pid, signal.SIGKILL)
                            except:
                                pass
                    except:
                        pass
                    
                    time.sleep(2)
                    navegador, firefox_pids = self._inicia_navegador()
                except Exception as ex_reset:
                    print(f"    [AVISO] Falha ao tentar reiniciar o navegador: {ex_reset}")
                    
                if deve_quebrar_loop:
                    continue
        db.fechar_conexao()
        try:
            if hasattr(navegador, 'xvfb_display'):
                navegador.xvfb_display.stop()
        except:
            pass
        try:
            import os, signal
            for pid in firefox_pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except:
                    pass
        except:
            pass
        try:
            navegador.quit()
        except:
            pass

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    credenciais = BASE_DIR / "credentials.json"
    
    # Obtém planilha do Google Planilhas com os CPFs a serem consultados
    tabela_sheets = GoogleSheets("1gdppEm4CdytUNfxotvBuHUqWdTdoU8NfBC43cGm_Qh8", "Geral", credenciais)
    guia_sheets = tabela_sheets.solicita_tabela()
    
    def atualizar_google_sheets(indice, status):
        tabela_sheets.atualizar_celula(f"L{indice}", status)

    bot = BotTRF4()
    bot.executar(guia_sheets[1:], atualizar_status_callback=atualizar_google_sheets)