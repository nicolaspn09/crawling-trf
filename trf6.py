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

class BotTRF6:
    def __init__(self):
        # A inicialização do banco não deve ocorrer no loop, mas sim na classe
        pass
        
    def _inicia_navegador(self):
        navegador, firefox_pids = ChromeStealthManager().acessa_navegador()
        return navegador, firefox_pids

    def _acessa_site(self, navegador):
        url = AcessaSite().site("mg")
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
        
        try:
            for indice, linha in enumerate(lista_dados, start=2):
                
                # Extrai os dados básicos com segurança (caso a linha não tenha todas as colunas)
                cpf = linha[0].strip() if len(linha) > 0 else ""
                nome = linha[2].strip() if len(linha) > 2 else ""
                ddd = linha[13].strip() if len(linha) > 13 else ""
                telefone = linha[14].strip() if len(linha) > 14 else ""           
                telefone_completo = f"{ddd}{telefone}".strip()

                # Valida o CPF antes de prosseguir
                if not self._validar_cpf(cpf):
                    print(f"[AVISO] CPF inválido, nome ou em branco: '{cpf}'")
                    if atualizar_status_callback:
                        atualizar_status_callback(indice, "CPF INVÁLIDO")
                    # Como não é um CPF válido, pulamos para a próxima linha SEM sujar o Banco de Dados
                    continue

                # Limpa o CPF para manter padrão no banco de dados (apenas números)
                cpf_limpo = ''.join(filter(str.isdigit, cpf))

                # Obtém ou cria o cliente no banco para termos o cliente_id VERDADEIRO (ID numérico interno do Postgres)
                cliente_id = db.obter_ou_criar_cliente(cpf=cpf_limpo, nome=nome, telefone=telefone_completo)
                
                print(f"\n[CONSULTA] Iniciando busca para o CPF: {cpf}")
                self._acessa_site(navegador=navegador)
                time.sleep(random.uniform(1.0, 1.8))
                
                acoes = NavegadorPy(navegador=navegador)
                
                acoes.combobox(elemento="   ", tipo_dado="id", timer=20, index=3)
                time.sleep(random.uniform(0.6, 1.2))
                
                acoes.adicionar_informacao(elemento="fPP:dpDec:documentoParte", tipo_dado="id", valor=cpf, timer=20)
                time.sleep(random.uniform(0.2, 0.5))
                
                acoes.clicar(elemento="fPP:searchProcessos", tipo_dado="id", timer=20)
                time.sleep(random.uniform(0.8, 1.5))

                info_login = acoes.obtem_informacao(elemento="fPP:j_id230", tipo_dado="id", timer=20)
                time.sleep(random.uniform(0.8, 1.5))

                if "não encontrou nenhum processo" in info_login:
                    print(f"[RESULTADO] CPF {cpf}: A pesquisa não encontrou nenhum processo disponível.)")

                    acoes = NavegadorPy(navegador=navegador)
                    
                    acoes.combobox(elemento="   ", tipo_dado="id", timer=20, index=3)
                    time.sleep(random.uniform(0.6, 1.2))

                    acoes.adicionar_informacao(elemento="fPP:dnp:nomeParte", tipo_dado="id", valor=nome, timer=20)
                    time.sleep(random.uniform(0.2, 0.5))
                    
                    acoes.clicar(elemento="fPP:searchProcessos", tipo_dado="id", timer=20)
                    time.sleep(random.uniform(0.8, 1.5))

                    info_login = acoes.obtem_informacao(elemento="fPP:j_id230", tipo_dado="id", timer=20)
                    time.sleep(random.uniform(0.8, 1.5))

                    if "não encontrou nenhum processo" in info_login:
                        if atualizar_status_callback:
                            atualizar_status_callback(indice, "BRANCO - SEM PROCESSO")
                        db.inserir_oportunidade(cliente_id, "BRANCO - SEM PROCESSO", f"Alerta do tribunal:  A pesquisa não encontrou nenhum processo disponível.", "Descartado")
                        continue
                    
                    acoes.clicar(elemento="/html/body/div[6]/div/div/div/div[2]/form/div[2]/div/table/tbody/tr/td[1]/a", tipo_dado="xpath", timer=20)
                    time.sleep(random.uniform(0.8, 1.5))


                """# Trata possível erro ao buscar o CPF 
                erro_site = acoes._obter_elemento(elemento="divInfraBarraLocalizacao", tipo_dado="id", timer=3)
                if erro_site:
                    print("Site com erro! Aguardando para iniciar nova tentativa de extração")
                    time.sleep(random.uniform(5.0, 10.0))
                    continue

                # Verifica Cloudflare
                cloudflare = acoes._obter_elemento(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=5)
                if cloudflare:
                    acoes.aguardar_sucesso_cloudflare(timeout_captcha=30)
                    time.sleep(random.uniform(0.5, 1.2))
                    try:
                        acoes.clicar(elemento="/html/body/div[1]/section/div[7]/div/form/input[1]", tipo_dado="xpath", timer=5)
                        time.sleep(random.uniform(0.8, 1.5))
                    except Exception:
                        pass"""
                
                print("[INFO] Coletando lista de processos carregados...")
                lista_processos = acoes.obter_links_da_lista()
                
                if not lista_processos:
                    print(f"[AVISO] Nenhum processo foi encontrado para o CPF {cpf}.")
                    if atualizar_status_callback:
                        atualizar_status_callback(indice, "BRANCO - SEM PROCESSO")
                    db.inserir_oportunidade(cliente_id, "BRANCO - SEM PROCESSO", "Lista de processos vazia", "Descartado")
                    continue

                # Limitador do escopo da POC: Executa o ciclo completo nos 2 primeiros da lista
                processos_poc = lista_processos[:2]
                print(f"[INFO] Iniciando varredura da POC em {len(processos_poc)} processos principais.")

                for idx, proc in enumerate(processos_poc, start=1):
                    numero_processo = proc['titulo']
                    print(f"\n[CONFERÊNCIA {idx}] Acessando link: {numero_processo}")
                    
                    # Nova versão do analisar_conteudo_processo que retorna dados tabelados
                    dados_principais, lista_fases = acoes.analisar_conteudo_processo(proc['url'])
                    
                    # Transformamos os dicionários/listas em uma grande string para validar a lógica das palavras
                    texto_processo = str(dados_principais).upper() + " " + str(lista_fases).upper()
                    
                    # VALIDAÇÃO 1: O polo passivo obrigatoriamente precisa ser o INSS
                    polo_passivo = "Desconhecido"
                    is_contra_inss = ("INSS" in texto_processo) or ("INSTITUTO NACIONAL DO SEGURO SOCIAL" in texto_processo)
                    if is_contra_inss:
                        polo_passivo = "INSS"

                    if not is_contra_inss:
                        print("-> Cor Planilha: BRANCO (Motivo: Não é uma ação movida contra o INSS)")
                        if atualizar_status_callback:
                            atualizar_status_callback(indice, "BRANCO")
                        db.inserir_processo(cliente_id, numero_processo, link_processo=proc['url'], polo_passivo=polo_passivo, tem_tese_concomitante=False, status_merito="Descartado")
                        db.inserir_oportunidade(cliente_id, "BRANCO", "Não é ação contra INSS", "Descartado")
                        continue
                        
                    # VALIDAÇÃO 2: Verificação do assunto / tese de Atividade Concomitante
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
                    possui_tese = any(termo in texto_processo for termo in termos_tese)
                    
                    if not possui_tese:
                        print("-> Cor Planilha: BRANCO (Motivo: Ação contra o INSS, mas trata de outra tese jurídica)")
                        if atualizar_status_callback:
                            atualizar_status_callback(indice, "BRANCO")
                        db.inserir_processo(cliente_id, numero_processo, link_processo=proc['url'], polo_passivo=polo_passivo, tem_tese_concomitante=False, status_merito="Descartado")
                        db.inserir_oportunidade(cliente_id, "BRANCO", "Ação contra o INSS, mas trata de outra tese jurídica", "Descartado")
                        continue
                        
                    # VALIDAÇÃO 3: Análise do dispositivo da Sentença/Decisão
                    termos_sem_merito = ["SEM RESOLUÇÃO", "SEM JULGAMENTO DO MÉRITO", "DESISTÊNCIA", "EXTINGO SEM", "ART. 485"]
                    termos_com_merito = ["PROCEDENTE", "IMPROCEDENTE", "PARCIAL PROCEDÊNCIA", "DECADÊNCIA", "PRESCRIÇÃO", "ART. 487"]

                    status_rpa = "BRANCO"
                    motivo = ""
                    fase = "Nova Oportunidade"
                    status_merito = "NÃO IDENTIFICADO"

                    if any(termo in texto_processo for termo in termos_sem_merito):
                        print("-> Cor Planilha: AMARELO (Motivo: Tese encontrada, mas extinta SEM resolução de mérito. Viável ajuizar novamente)")
                        status_rpa = "AMARELO"
                        motivo = "Tese encontrada, mas extinta SEM resolução de mérito. Viável ajuizar novamente."
                        status_merito = "SEM RESOLUÇÃO"
                    elif any(termo in texto_processo for termo in termos_com_merito):
                        print("-> Cor Planilha: CINZA (Motivo: Descartado. Já possui sentença definitiva COM resolução de mérito)")
                        status_rpa = "CINZA"
                        motivo = "Descartado. Já possui sentença definitiva COM resolução de mérito."
                        status_merito = "COM RESOLUÇÃO"
                        fase = "Descartado"
                    else:
                        print("-> Cor Planilha: BRANCO / ALERTA (Motivo: Tese localizada, mas a estrutura da decisão exige revisão manual)")
                        status_rpa = "BRANCO"
                        motivo = "Tese localizada, mas a estrutura da decisão exige revisão manual."
                        fase = "Revisão Manual"

                    if atualizar_status_callback:
                        atualizar_status_callback(indice, status_rpa)
                    db.inserir_processo(cliente_id, numero_processo, link_processo=proc['url'], polo_passivo=polo_passivo, tem_tese_concomitante=True, status_merito=status_merito)
                    db.inserir_oportunidade(cliente_id, status_rpa, motivo, fase)

                    time.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            print(e)

        finally:
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