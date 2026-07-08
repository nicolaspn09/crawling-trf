import os
import io
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import pandas as pd

class GoogleDriveManager:
    def __init__(self, diretorio_json):
        self.diretorio_json = diretorio_json
        self.arquivo_token = os.path.join(
            os.path.dirname(self.diretorio_json),
            "token_drive.json"
        )
        self.scopes = ["https://www.googleapis.com/auth/drive"]
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists(self.arquivo_token):
            creds = Credentials.from_authorized_user_file(self.arquivo_token, self.scopes)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.diretorio_json, self.scopes)
                creds = flow.run_local_server(port=0)
            
            with open(self.arquivo_token, 'w') as token:
                token.write(creds.to_json())

        return build('drive', 'v3', credentials=creds)

    def listar_arquivos(self, folder_id, mime_type=None):
        """
        Lista arquivos/pastas dentro de uma pasta específica no Google Drive.
        Se mime_type for especificado (ex: 'application/vnd.google-apps.folder'), filtra por tipo.
        """
        query = f"'{folder_id}' in parents and trashed = false"
        if mime_type:
            query += f" and mimeType = '{mime_type}'"
            
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='nextPageToken, files(id, name, mimeType)',
            pageSize=1000
        ).execute()
        
        return results.get('files', [])

    def criar_pasta(self, nome_pasta, parent_folder_id):
        """
        Cria uma nova pasta dentro de parent_folder_id.
        """
        file_metadata = {
            'name': nome_pasta,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        pasta = self.service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        return pasta.get('id')

    def buscar_ou_criar_pasta(self, nome_pasta, parent_folder_id):
        """
        Verifica se a pasta já existe. Se não, cria a pasta.
        """
        pastas = self.listar_arquivos(parent_folder_id, mime_type='application/vnd.google-apps.folder')
        for p in pastas:
            if p['name'].lower() == nome_pasta.lower():
                return p['id']
        
        return self.criar_pasta(nome_pasta, parent_folder_id)

    def mover_arquivo(self, file_id, atual_parent_id, novo_parent_id):
        """
        Move um arquivo para uma nova pasta.
        """
        file = self.service.files().update(
            fileId=file_id,
            addParents=novo_parent_id,
            removeParents=atual_parent_id,
            fields='id, parents'
        ).execute()
        return file

    def atualizar_arquivo_local(self, file_id, caminho_local):
        """
        Sobrescreve o conteúdo do arquivo no Drive com o arquivo local.
        """
        media = MediaFileUpload(caminho_local, resumable=True)
        updated_file = self.service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        return updated_file

    def baixar_arquivo(self, file_id, file_name, mime_type):
        """
        Baixa o arquivo para poder analisar localmente (csv, xls, xlsx).
        Se for google sheets, precisamos exportar.
        """
        if mime_type == 'application/vnd.google-apps.spreadsheet':
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            file_name += '.xlsx'
        else:
            request = self.service.files().get_media(fileId=file_id)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        fh.seek(0)
        return fh, file_name

    def validar_arquivo(self, file_stream, extensao):
        """
        Lógica para validar o formato da planilha (A SER PREENCHIDO COM A REGRA DE NEGÓCIO).
        """
        try:
            if extensao.endswith('.csv'):
                df = pd.read_csv(file_stream)
            else:
                df = pd.read_excel(file_stream)
                
            # AQUI ENTRA A VALIDAÇÃO DO FORMATO MAPEADO
            # O trf4.py espera acessar até o índice 14 (linha[14] - Telefone),
            # então precisamos garantir que a planilha tenha pelo menos 15 colunas.
            if len(df.columns) < 15:
                return False, f"Formato incorreto: a planilha possui apenas {len(df.columns)} colunas, eram esperadas no mínimo 15."
            
            return True, df
        except Exception as e:
            return False, f"Erro ao ler arquivo: {str(e)}"
