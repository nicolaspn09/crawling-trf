import git
import os
import shutil
import tempfile
import argparse

def atualizar_arquivos(url_git, destino_pasta):
    # Cria uma pasta temporária para clonar o repositório
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Clonando repositório temporariamente em {temp_dir}...")
        try:
            git.Repo.clone_from(url_git, temp_dir)
            print("Repositório clonado com sucesso.")
        except Exception as e:
            print(f"Erro ao clonar repositório: {e}")
            print("Dica: Se o repositório for privado, lembre-se de usar um Personal Access Token (PAT) na URL.")
            print("Exemplo: https://<SEU_TOKEN>@github.com/usuario/repositorio.git")
            return

        # Copia os arquivos da pasta temporária para a pasta de destino
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".py"):  # Filtra apenas arquivos .py para duplicação
                    caminho_temp = os.path.join(root, file)
                    caminho_destino = os.path.join(destino_pasta, os.path.relpath(caminho_temp, temp_dir))
                    
                    # Cria as pastas no destino, se necessário
                    os.makedirs(os.path.dirname(caminho_destino), exist_ok=True)
                    
                    # Substitui o arquivo no destino
                    shutil.copy2(caminho_temp, caminho_destino)
                    print(f"Arquivo atualizado: {caminho_destino}")

                    # Duplicação do arquivo como .pyw
                    caminho_pyw = caminho_destino + "w"
                    shutil.copy2(caminho_temp, caminho_pyw)
                    print(f"Arquivo duplicado como: {caminho_pyw}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Atualiza arquivos de um repositório GitHub (CI/CD)")
    parser.add_argument("--url_git", required=True, help="URL do repositório GitHub (com token se for privado)")
    parser.add_argument("--destino_pasta", required=True, help="Diretório de destino para os arquivos")

    args = parser.parse_args()

    atualizar_arquivos(args.url_git, args.destino_pasta)
