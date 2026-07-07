import os
from GoogleDrive import GoogleDriveManager
from trf4 import processar_lista_cpfs
import pandas as pd

# URL: https://drive.google.com/drive/u/0/folders/12wtexdXWnh8bndlSYBcDKbpXbejpjldz
# Folder ID is 12wtexdXWnh8bndlSYBcDKbpXbejpjldz
PARENT_FOLDER_ID = "12wtexdXWnh8bndlSYBcDKbpXbejpjldz"
TESE_ATUAIS = ["TESE - ATIVIDADES CONCOMITANTES"]
ESTADO_ATUAL = "SANTA CATARINA"

def main():
    # Precisamos do caminho do JSON do Google
    # Assumindo que usa o mesmo json do GoogleSheets.py
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    # Encontre seu arquivo json de secret
    json_path = None
    for file in os.listdir(diretorio_atual):
        if file.startswith('client_secret_') and file.endswith('.json'):
            json_path = os.path.join(diretorio_atual, file)
            break
            
    if not json_path:
        print("Arquivo client_secret não encontrado!")
        return

    drive = GoogleDriveManager(json_path)

    print(f"Listando pastas na raiz ({PARENT_FOLDER_ID})...")
    pastas_raiz = drive.listar_arquivos(PARENT_FOLDER_ID, mime_type='application/vnd.google-apps.folder')
    
    for pasta_tese in pastas_raiz:
        if pasta_tese['name'] in TESE_ATUAIS:
            print(f"Encontrada tese: {pasta_tese['name']}")
            
            pastas_tese = drive.listar_arquivos(pasta_tese['id'], mime_type='application/vnd.google-apps.folder')
            pasta_estados = next((p for p in pastas_tese if p['name'].upper() == "ESTADOS"), None)
            
            if pasta_estados:
                print("Encontrada pasta ESTADOS")
                pastas_estados_ufs = drive.listar_arquivos(pasta_estados['id'], mime_type='application/vnd.google-apps.folder')
                pasta_sc = next((p for p in pastas_estados_ufs if p['name'].upper() == ESTADO_ATUAL), None)
                
                if pasta_sc:
                    print(f"Encontrada pasta do estado: {ESTADO_ATUAL}")
                    
                    # Garantir que a pasta ANALISADO existe
                    analisado_folder_id = drive.buscar_ou_criar_pasta("ANALISADO", pasta_sc['id'])
                    
                    # Buscar arquivos para processar
                    arquivos = drive.listar_arquivos(pasta_sc['id'])
                    
                    for arquivo in arquivos:
                        # Ignorar pastas
                        if arquivo['mimeType'] == 'application/vnd.google-apps.folder':
                            continue
                            
                        print(f"Processando arquivo: {arquivo['name']} ({arquivo['mimeType']})")
                        
                        # 1. Baixar/Ler arquivo
                        file_stream, nome_arquivo = drive.baixar_arquivo(arquivo['id'], arquivo['name'], arquivo['mimeType'])
                        
                        # 2. Validar
                        is_valid, dados = drive.validar_arquivo(file_stream, arquivo['name'])
                        
                        if not is_valid:
                            print(f"ALERTA: O arquivo {arquivo['name']} NÃO está no formato mapeado. Motivo: {dados}")
                            continue
                            
                        print(f"Arquivo {arquivo['name']} validado com sucesso!")
                        
                        # 3. Processar
                        print("Iniciando fluxo TRF4 para esta planilha...")
                        
                        # Transforma o dataframe em uma lista de listas para simular a saída do Google Sheets (onde a linha 0 é o cabeçalho)
                        # Então os dados começam do índice 0 da lista (que no sheets seria a linha 2, por isso o trf4 faz enumerate(..., start=2))
                        # Para não quebrar o trf4.py que espera `linha[0]`, `linha[2]`, `linha[13]`, `linha[14]`, precisamos garantir que o DF tenha essas colunas.
                        df = dados
                        
                        # Converte df para lista de listas (substituindo NaN por string vazia)
                        df = df.fillna("")
                        lista_dados = df.values.tolist()
                        
                        # Definimos um callback para atualizar o excel. Como o arquivo será movido para ANALISADO, podemos salvar localmente e fazer upload.
                        # Por ora, como é uma POC, vamos rodar e os status serão printados e salvos no Banco. 
                        # TODO: Se precisar escrever no Excel e fazer upload, podemos implementar.
                        def meu_callback(indice, status):
                            print(f"Planilha Linha {indice} -> Status {status}")

                        processar_lista_cpfs(lista_dados, atualizar_status_callback=meu_callback)
                        
                        # 4. Mover para a pasta ANALISADO
                        print(f"Movendo {arquivo['name']} para a pasta ANALISADO...")
                        drive.mover_arquivo(arquivo['id'], pasta_sc['id'], analisado_folder_id)
                        print("Movido com sucesso!\n")
                        
            else:
                print("Pasta ESTADOS não encontrada!")

if __name__ == "__main__":
    main()
