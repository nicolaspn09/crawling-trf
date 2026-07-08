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

    def executar(self, lista_dados, atualizar_status_callback=None):
        db = Database()
        navegador, firefox_pids = self._inicia_navegador()
        
        for indice, linha in enumerate(lista_dados, start=2):
            try:
                # Extrai os dados básicos com segurança (caso a linha não tenha todas as colunas)
                cpf = linha[0].strip() if len(linha) > 0 else ""

                # if "89254759953" not in str(cpf).replace("-", "").replace(".", ""):
                #     continue
                
                nome = linha[2].strip() if len(linha) > 2 else ""
                ddd = str(linha[13]).strip() if len(linha) > 13 else ""
                telefone = str(linha[14]).strip() if len(linha) > 14 else ""           
                telefone_completo = f"{ddd}{telefone}".strip()

                # Valida o CPF antes de prosseguir
                if not self._validar_cpf(cpf):
                    print(f"[AVISO] CPF inválido ou em branco: '{cpf}'. Pulando linha.")
                    continue

                # Limpa o CPF para manter padrão no banco de dados (apenas números)
                cpf_limpo = ''.join(filter(str.isdigit, cpf))

                # Obtém ou cria o cliente no banco para termos o cliente_id VERDADEIRO (ID numérico interno do Postgres)
                cliente_id = db.obter_ou_criar_cliente(cpf=cpf_limpo, nome=nome, telefone=telefone_completo)
                
                def fazer_pesquisa_eproc(valor_busca, indice_origem=3):
                    self._acessa_site(navegador=navegador)
                    time.sleep(random.uniform(0.5, 1.0))
                    
                    acoes = NavegadorPy(navegador=navegador)
                    
                    acoes.combobox(elemento="selForma", tipo_dado="id", timer=20, index=indice_origem)
                    time.sleep(random.uniform(0.2, 0.5))
                    
                    try:
                        acoes.combobox(elemento="selOrigem", tipo_dado="id", timer=5, index=2)
                        time.sleep(random.uniform(0.2, 0.4))
                    except Exception:
                        pass # O campo selOrigem não existe ou fica oculto quando a busca é pelo Nome
                    
                    acoes.adicionar_informacao(elemento="txtValor", tipo_dado="id", valor=valor_busca, timer=20)
                    time.sleep(random.uniform(0.1, 0.3))
                    
                    try:
                        acoes.clicar(elemento="chkMostrarBaixados", tipo_dado="id", timer=5)
                        time.sleep(random.uniform(0.1, 0.3))
                    except Exception:
                        pass
                    
                    acoes.clicar(elemento="botaoEnviar", tipo_dado="id", timer=20)
                    time.sleep(random.uniform(0.5, 1.0))
                    
                    return acoes

                print(f"\n[CONSULTA] Iniciando busca para o CPF: {cpf}")
                acoes = fazer_pesquisa_eproc(cpf, indice_origem=3)

                # Trata possíveis popups (ex: Nenhum processo encontrado) nativos do site
                tem_alerta, texto_alerta = self._tratar_alerta_popup(navegador, timeout=3)
                
                # Trata possível erro ao buscar o CPF 
                erro_site = acoes._obter_elemento(elemento="divInfraBarraLocalizacao", tipo_dado="id", timer=3)
                
                if not tem_alerta and not erro_site:
                    # Verifica Cloudflare
                    cloudflare = acoes._obter_elemento(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=5)
                    if cloudflare:
                        acoes.aguardar_sucesso_cloudflare(timeout_captcha=30)
                        time.sleep(random.uniform(0.5, 1.2))
                        try:
                            acoes.clicar(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=5)
                            time.sleep(random.uniform(0.8, 1.5))
                        except Exception:
                            pass
                
                lista_processos = []
                if not tem_alerta and not erro_site:
                    lista_processos = acoes.obter_links_da_lista()

                # DUPLA CHECAGEM: Se não encontrou pelo CPF, tenta pelo Nome
                if tem_alerta or not lista_processos:
                    print(f"[RESULTADO CPF] CPF {cpf}: Nada Consta. Tentando dupla checagem pelo NOME: {nome}")
                    acoes = fazer_pesquisa_eproc(nome, indice_origem=2)
                    
                    tem_alerta, texto_alerta = self._tratar_alerta_popup(navegador, timeout=3)
                    
                    if not tem_alerta and not erro_site:
                        cloudflare = acoes._obter_elemento(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=5)
                        if cloudflare:
                            acoes.aguardar_sucesso_cloudflare(timeout_captcha=30)
                            time.sleep(random.uniform(0.5, 1.2))
                            try:
                                acoes.clicar(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=5)
                                time.sleep(random.uniform(0.8, 1.5))
                            except Exception:
                                pass
                            
                    if not tem_alerta:
                        lista_processos_nome = []
                        
                        from selenium.webdriver.common.by import By
                        links_conteudo = navegador.find_elements(By.XPATH, "//div[@id='divConteudo']/a")
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
                            # Se não for a tela de homônimos, pega a lista direto
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
                    print("Site com erro na pesquisa de CPF e Nome! Aguardando para nova tentativa...")
                    time.sleep(random.uniform(5.0, 10.0))
                    continue

                if not lista_processos:
                    print(f"[AVISO FINAL] Nenhum processo foi encontrado para o CPF/NOME {cpf}.")
                    if atualizar_status_callback:
                        atualizar_status_callback(indice, "BRANCO - NADA CONSTA", "", "")
                    db.inserir_oportunidade(cliente_id, "BRANCO - NADA CONSTA", "Lista de processos vazia", "Descartado")
                    continue

                # Removemos o limitador da POC, varrendo TODOS os processos.
                processos = lista_processos
                print(f"[INFO] Iniciando varredura em {len(processos)} processos encontrados.")

                for idx, proc in enumerate(processos, start=1):
                    numero_processo = proc['titulo']
                    print(f"\n[CONFERÊNCIA {idx}] Acessando link: {numero_processo}")
                    
                    # Nova versão do analisar_conteudo_processo que retorna dados tabelados
                    dados_principais, lista_fases = acoes.analisar_conteudo_processo(proc['url'])
                    
                    # Transformamos os dicionários/listas em uma grande string para validar a lógica das palavras
                    texto_processo = str(dados_principais).upper() + " " + str(lista_fases).upper()
                    
                    # VALIDAÇÃO 1: O polo passivo obrigatoriamente precisa ser o INSS
                    polo_passivo = dados_principais.get('Réu', 'Desconhecido')
                    assunto_processo = dados_principais.get('Assuntos', dados_principais.get('Assunto', 'Não informado'))
                    is_contra_inss = ("INSS" in texto_processo) or ("INSTITUTO NACIONAL DO SEGURO SOCIAL" in texto_processo)
                    if is_contra_inss:
                        polo_passivo = "INSS"

                    if not is_contra_inss:
                        print("-> Cor Planilha: BRANCO (Motivo: Não é uma ação movida contra o INSS)")
                        if atualizar_status_callback:
                            atualizar_status_callback(indice, "BRANCO - Não movida contra o INSS", numero_processo, assunto_processo)
                        db.inserir_processo(cliente_id, numero_processo, link_processo=proc['url'], polo_passivo=polo_passivo, tem_tese_concomitante=False, status_merito="Descartado", assunto=assunto_processo)
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
                        
                        termos_tese = ["ATIVIDADE CONCOMITANTE", "ATIVIDADES CONCOMITANTES", "CONCOMITANTE", "CONCOMITANTES", "MULTIPLICADOR", "CONCOMITÂNCIA"]
                        
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
                            atualizar_status_callback(indice, "BRANCO - Outra tese jurídica", numero_processo, assunto_processo)
                        db.inserir_processo(cliente_id, numero_processo, link_processo=proc['url'], polo_passivo=polo_passivo, tem_tese_concomitante=False, status_merito="Descartado", link_sentenca=link_principal, assunto=assunto_processo)
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
                        atualizar_status_callback(indice, status_rpa, numero_processo, assunto_processo)
                    db.inserir_processo(cliente_id, numero_processo, link_processo=proc['url'], polo_passivo=polo_passivo, tem_tese_concomitante=True, status_merito=status_merito, link_sentenca=link_principal, assunto=assunto_processo)
                    db.inserir_oportunidade(cliente_id, status_rpa, motivo, fase_oportunidade)

                    time.sleep(random.uniform(1.0, 2.0))
                    
                    # Como a tese FOI localizada (seja amarelo, cinza ou branco alerta),
                    # quebramos o loop para não processar os demais processos deste CPF!
                    print(f"       -> Tese localizada! Parando de analisar processos para o CPF {cpf}.")
                    break

            except Exception as e:
                print(f"[ERRO CPF] Falha no índice {indice} (Linha {indice}): {e}")
                continue

        print("\n[POC STATUS] Execução finalizada. Banco atualizado.")
        db.fechar_conexao()
        navegador.quit()

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