import os
import re
import sys
import psutil
import shutil
import requests
import subprocess
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions


class FirefoxSeleniumManager:
    def __init__(self, caminho_arquivo=None):
        """
        Inicializa a classe com a configuração necessária.
        """
        self.caminho_arquivo = caminho_arquivo
        self.selenium_firefox_dir = r"C:\Firefox_Selenium"
        self.firefox_install_dir = r"C:\Program Files\Mozilla Firefox"
    
    def find_firefox_processes(self, ppid):
        """ Encontra subprocessos do Geckodriver. """
        firefox_pids = []
        for proc in psutil.process_iter(['pid', 'ppid', 'name']):
            try:
                if proc.info['ppid'] == ppid and proc.info['name'].lower() in ['firefox_selenium', 'firefox_selenium.exe']:
                    firefox_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return firefox_pids

    def get_firefox_version(self, directory, executable_name):
        """
        Obtém a versão do Firefox a partir do arquivo `firefox.exe` no diretório especificado.
        """
        try:
            firefox_executable = os.path.join(directory, executable_name)
            if not os.path.exists(firefox_executable):
                return None
            result = subprocess.run(
                [firefox_executable, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            version_match = re.search(r"Mozilla Firefox (\d+\.\d+)", result.stdout)
            if version_match:
                return version_match.group(1)
        except Exception as e:
            print(f"Erro ao obter versão do Firefox no diretório '{directory}': {e}")
        return None

    def get_geckodriver(self):
        """
        Faz o download do GeckoDriver mais recente e extrai para C:\Firefox_Selenium se ainda não existir.
        """
        geckodriver_path = os.path.join(self.selenium_firefox_dir, "geckodriver.exe")
        
        return geckodriver_path

    def acessa_navegador(self):
        """
        Acessa o navegador com as configurações necessárias.
        """
        # Obtém o local do geckodriver
        geckodriver_path = self.get_geckodriver()

        # Configurações para o Firefox
        options = FirefoxOptions()
        options.binary_location = os.path.join(self.selenium_firefox_dir, "firefox_selenium.exe")  # Especifica o executável renomeado do Firefox

        sys.stdout = open(self.caminho_arquivo, 'w') if self.caminho_arquivo else sys.stdout  # Ajusta a saída
        # user_agent = ("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.182 Safari/537.36")
        # options.add_argument('--headless')  # Executa o Firefox em modo headless (sem interface gráfica)
        options.add_argument("--width=1920")  # Define a largura da janela
        options.add_argument("--height=1080")  # Define a altura da janela
        options.add_argument("--disable-gpu")
        # options.add_argument(user_agent)  # Define o user-agent para o Firefox
        options.add_argument('--ignore-certificate-errors')  # Desabilita a verificação de certificado SSL

        # --- PREFERÊNCIAS CRÍTICAS PARA EVASÃO (ANTIBOT) ---
        # Esconde a flag basica do webdriver
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        
        # Evita vazamento de assinaturas de testes do gckdriver
        options.set_preference("marionette.enabled", False) 
        
        # Força o Firefox a fingir um perfil regular de usuário estável
        options.set_preference("privacy.trackingprotection.enabled", False)
        options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0")

        servico = FirefoxService(executable_path=geckodriver_path)
        navegador = webdriver.Firefox(options=options, service=servico)

        # Maximiza o navegador
        navegador.maximize_window()

        # Obtém o PID do processo do GeckoDriver
        geckodriver_pid = servico.process.pid

        # Encontra subprocessos do GeckoDriver
        firefox_pids = self.find_firefox_processes(geckodriver_pid)

        return navegador, firefox_pids


if __name__ == "__main__":
    manager = FirefoxSeleniumManager()
    navegador, firefox_pids = manager.acessa_navegador()
    print(f"Navegador aberto com PID do GeckoDriver: {firefox_pids}")
