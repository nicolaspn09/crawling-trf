import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

class GoogleSheets:
    def __init__(self, id_planilha, range_dados, diretorio_json):
        self.id_planilha = id_planilha
        self.range_dados = range_dados
        self.diretorio_json = diretorio_json

    # Função que obtém a margem informada pelo usuário
    def solicita_tabela(self):
        """
        Solicita as informações do Google Sheet, guia de margens

        Returns:
        Valores: collection
        """
        # If modifying these scopes, delete the file token.json.
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"] #Acessa o google sheets

        # The ID and range of a sample spreadsheet.
        SAMPLE_SPREADSHEET_ID = self.id_planilha
        SAMPLE_RANGE_NAME = self.range_dados

        creds = None

        # Faz o login da API do Google
        if os.path.exists(self.diretorio_json):
            creds = Credentials.from_authorized_user_file(self.diretorio_json, SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.diretorio_json, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.diretorio_json, 'w') as token:
                token.write(creds.to_json())

        # Faz a leitura e edição da planilha
        #try:
        service = build('sheets', 'v4', credentials=creds)

        # Lê os dados da planilha com a opção para incluir colunas vazias
        sheet = service.spreadsheets()
        
        # Lê a planilha através do .get, o .update altera informações
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()        
        valores = result.get('values', [])

        # Se necessário, preenche as colunas vazias com um valor padrão (ex: None ou "")
        max_colunas = max(len(linha) for linha in valores) if valores else 0
        for linha in valores:
            while len(linha) < max_colunas:
                linha.append("")

        return valores
    

    def solicita_tabela_guia_especifica(self, nome_guia, range_celulas="A1:Z"):
        """
        Solicita as informações de uma guia específica do Google Sheet
        
        Args:
        nome_guia: Nome da guia/aba do Google Sheets
        range_celulas: Range de células a ser lido (padrão: A1:Z para ler todas as colunas)
        
        Returns:
        Valores: collection
        """
        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
        SAMPLE_SPREADSHEET_ID = self.id_planilha
        SAMPLE_RANGE_NAME = f"{nome_guia}!{range_celulas}"

        creds = None

        if os.path.exists(self.diretorio_json):
            creds = Credentials.from_authorized_user_file(self.diretorio_json, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.diretorio_json, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.diretorio_json, 'w') as token:
                token.write(creds.to_json())

        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        
        result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()        
        valores = result.get('values', [])

        max_colunas = max(len(linha) for linha in valores) if valores else 0
        for linha in valores:
            while len(linha) < max_colunas:
                linha.append("")

        return valores