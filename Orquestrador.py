import os
import pandas as pd
import openpyxl
from GoogleDrive import GoogleDriveManager
from GoogleSheets import GoogleSheets

class OrquestradorDrive:
    def __init__(self, diretorio_json, map_estados_bots):
        """
        map_estados_bots: Dicionário que mapeia o nome da pasta do estado 
        para a classe/função responsável por processar os dados dele.
        Ex: {"SANTA CATARINA": BotTRF4().processar}
        """
        self.drive = GoogleDriveManager(diretorio_json)
        self.map_estados_bots = map_estados_bots
        # ID fixo da raiz conforme solicitado
        self.parent_folder_id = "12wtexdXWnh8bndlSYBcDKbpXbejpjldz"

    def executar_pipeline(self):
        print(f"Listando pastas na raiz ({self.parent_folder_id})...")
        pastas_raiz = self.drive.listar_arquivos(self.parent_folder_id, mime_type='application/vnd.google-apps.folder')
        
        for pasta_tese in pastas_raiz:
            if "CONCOMITANTE" not in pasta_tese['name'].upper():
                print(f"Ignorando tese (não é concomitante): {pasta_tese['name']}")
                continue
                
            print(f"Encontrada tese concomitante: {pasta_tese['name']}")
            
            pastas_tese = self.drive.listar_arquivos(pasta_tese['id'], mime_type='application/vnd.google-apps.folder')
            pasta_estados = next((p for p in pastas_tese if p['name'].upper() == "ESTADOS"), None)
            
            if pasta_estados:
                print(f"  -> Explorando pasta ESTADOS dentro de {pasta_tese['name']}")
                pastas_estados_ufs = self.drive.listar_arquivos(pasta_estados['id'], mime_type='application/vnd.google-apps.folder')
                
                for pasta_uf in pastas_estados_ufs:
                    nome_estado = pasta_uf['name'].strip().upper()
                    
                    if nome_estado in self.map_estados_bots:
                        print(f"    -> Encontrado estado mapeado: {nome_estado}")
                        self._processar_estado(pasta_uf, self.map_estados_bots[nome_estado])
                    else:
                        print(f"    -> Estado ignorado (sem bot mapeado): {nome_estado}")
            else:
                print(f"  -> Pasta ESTADOS não encontrada em {pasta_tese['name']}")

    def _processar_estado(self, pasta_uf, processador_bot):
        analisado_folder_id = self.drive.buscar_ou_criar_pasta("ANALISADO", pasta_uf['id'])
        arquivos = self.drive.listar_arquivos(pasta_uf['id'])
        
        for arquivo in arquivos:
            if arquivo['mimeType'] == 'application/vnd.google-apps.folder':
                continue
                
            print(f"      -> Processando arquivo: {arquivo['name']}")
            file_stream, nome_arquivo = self.drive.baixar_arquivo(arquivo['id'], arquivo['name'], arquivo['mimeType'])
            
            is_valid, df_ou_erro = self.drive.validar_arquivo(file_stream, arquivo['name'])
            
            if not is_valid:
                print(f"         [ALERTA] Arquivo {arquivo['name']} inválido. Motivo: {df_ou_erro}")
                continue
                
            print(f"         Arquivo {arquivo['name']} validado. Iniciando Bot.")
            
            # Preparar dados abstraídos do Pandas
            df = df_ou_erro.fillna("")
            lista_dados = df.values.tolist()
            
            # Inicializa a API do Sheets se for uma planilha do Google
            is_google_sheet = (arquivo['mimeType'] == 'application/vnd.google-apps.spreadsheet')
            is_excel = arquivo['name'].endswith('.xlsx')
            
            planilha_api = None
            wb = None
            ws = None
            
            if is_google_sheet:
                # Usa aba com nome "Geral" (padrão) ou pode adaptar se a aba tiver outro nome
                planilha_api = GoogleSheets(arquivo['id'], "Geral", self.drive.diretorio_json)
            elif is_excel:
                file_stream.seek(0)
                wb = openpyxl.load_workbook(file_stream)
                ws = wb.active
            
            def callback_status(indice, status, numero_processo="", assunto=""):
                if planilha_api:
                    try:
                        planilha_api.atualizar_celula(f"BT{indice}", numero_processo)
                        planilha_api.atualizar_celula(f"BU{indice}", assunto)
                        planilha_api.atualizar_celula(f"BV{indice}", status)
                        planilha_api.pintar_linha(indice, status)
                    except Exception as e:
                        # Fallback caso a aba não se chame "Geral"
                        try:
                            # Tenta sem o nome da aba (atualiza a primeira visível)
                            planilha_api.range_dados = ""
                            planilha_api.atualizar_celula(f"BT{indice}", numero_processo)
                            planilha_api.atualizar_celula(f"BU{indice}", assunto)
                            planilha_api.atualizar_celula(f"BV{indice}", status)
                            planilha_api.pintar_linha(indice, status)
                        except Exception as e2:
                            print(f"         [AVISO] Não foi possível pintar a linha {indice} no Google Sheets. Erro: {e2}")
                else:
                    if ws:
                        try:
                            ws[f"BT{indice}"] = numero_processo
                            ws[f"BU{indice}"] = assunto
                            ws[f"BV{indice}"] = status
                        except Exception:
                            pass
                    print(f"         Status (Offline/Excel): Linha {indice} -> {status} | Proc: {numero_processo} | Assunto: {assunto}")

            # Executa o bot com Single Responsibility
            # O bot processa e não precisa saber de onde vieram os dados
            try:
                processador_bot(lista_dados, atualizar_status_callback=callback_status)
                print(f"         Bot finalizou o processamento de {arquivo['name']}.")
            except Exception as e:
                print(f"         [ERRO] Falha ao rodar o bot para {arquivo['name']}: {str(e)}")
                continue
                
            if wb:
                temp_file = f"temp_{arquivo['name']}"
                wb.save(temp_file)
                print(f"         Fazendo upload das alterações no Excel para o Google Drive...")
                self.drive.atualizar_arquivo_local(arquivo['id'], temp_file)
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            # print(f"         Movendo {arquivo['name']} para ANALISADO...")
            # self.drive.mover_arquivo(arquivo['id'], pasta_uf['id'], analisado_folder_id)
            # print("         Movido com sucesso!")
