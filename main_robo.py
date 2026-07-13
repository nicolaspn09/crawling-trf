import os
from Orquestrador import OrquestradorDrive
from trf4 import BotTRF4

# Aqui configuramos quais estados (pastas) disparam quais robôs.
# No futuro, você pode importar BotTRF3, BotTRF1, etc.
MAPA_ESTADOS_BOTS = {
    "SANTA CATARINA": BotTRF4().executar,
    # "RIO GRANDE DO SUL": BotTRF4().executar,  # Removido temporariamente para testes
    # "PARANA": BotTRF4().executar              # Removido temporariamente para testes
}

def main():
    diretorio_atual = os.path.dirname(os.path.abspath(__file__))
    
    # Busca o token/json do Google na raiz
    json_path = None
    for file in os.listdir(diretorio_atual):
        if file.startswith('client_secret_') and file.endswith('.json'):
            json_path = os.path.join(diretorio_atual, file)
            break
            
    if not json_path:
        print("Arquivo client_secret não encontrado na raiz!")
        return
        
    print("Iniciando Orquestrador do Google Drive...")
    
    # Inicia o orquestrador passando o mapa de robôs
    orquestrador = OrquestradorDrive(
        diretorio_json=json_path,
        map_estados_bots=MAPA_ESTADOS_BOTS
    )
    
    # Executa a pipeline (Varre as teses -> estados -> arquivos -> executa bot -> move p/ ANALISADO)
    orquestrador.executar_pipeline()

if __name__ == "__main__":
    main()
