import sys
import os
import psutil
import platform
from dotenv import load_dotenv

load_dotenv()

class ChromeStealthManager:
    def __init__(self, caminho_arquivo=None):
        self.caminho_arquivo = caminho_arquivo

    def find_chrome_processes(self, ppid):
        """Encontra subprocessos do Chrome disparados pelo driver."""
        chrome_pids = []
        for proc in psutil.process_iter(['pid', 'ppid', 'name']):
            try:
                if proc.info['ppid'] == ppid and 'chrome' in proc.info['name'].lower():
                    chrome_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return chrome_pids

    def acessa_navegador(self):
        if self.caminho_arquivo:
            sys.stdout = open(self.caminho_arquivo, 'w')

        # =====================================================================
        # PROXY AUTENTICADO VIA SELENIUM-WIRE
        # O undetected_chromedriver NÃO suporta extensões de proxy via
        # add_extension (são silenciosamente ignoradas). Além disso, Manifest V2
        # foi removido do Chrome 127+.
        # A solução é usar selenium-wire, que cria um proxy local intermediário
        # e injeta a autenticação de forma transparente, sem extensão nenhuma.
        # =====================================================================
        proxy_host = os.environ.get("PROXY_HOST")
        proxy_port = os.environ.get("PROXY_PORT")
        proxy_user = os.environ.get("PROXY_USER")
        proxy_pass = os.environ.get("PROXY_PASS")

        seleniumwire_options = {}
        usar_seleniumwire = False

        if proxy_host and proxy_port:
            proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}" if proxy_user and proxy_pass else f"http://{proxy_host}:{proxy_port}"
            print(f"[PROXY] Configurando proxy via selenium-wire: {proxy_host}:{proxy_port}")
            seleniumwire_options = {
                'proxy': {
                    'http': proxy_url,
                    'https': proxy_url,
                    'no_proxy': 'localhost,127.0.0.1'
                }
            }
            usar_seleniumwire = True

        # Importa o driver correto baseado na disponibilidade do proxy
        if usar_seleniumwire:
            from seleniumwire import undetected_chromedriver as uc
        else:
            import undetected_chromedriver as uc

        options = uc.ChromeOptions()

        # Argumentos essenciais para passar pelo Cloudflare Turnstile
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Desativa detecções comuns de automação via flags do Chrome
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Inicializa o driver (No Linux, usa monitor virtual para enganar o Cloudflare)
        if platform.system() == "Linux":
            try:
                from pyvirtualdisplay import Display
                self.display = Display(visible=0, size=(1920, 1080))
                self.display.start()
            except ImportError:
                print("[AVISO] pacote pyvirtualdisplay não encontrado. Rode: pip3 install pyvirtualdisplay")
                
            # No Linux, tiramos o headless=True e deixamos o Xvfb (Display) fazer o trabalho de esconder a tela.
            if usar_seleniumwire:
                navegador = uc.Chrome(
                    options=options,
                    headless=False,
                    browser_executable_path='/usr/bin/google-chrome',
                    use_subprocess=True,
                    version_main=150,
                    seleniumwire_options=seleniumwire_options
                )
            else:
                navegador = uc.Chrome(
                    options=options,
                    headless=False,
                    browser_executable_path='/usr/bin/google-chrome',
                    use_subprocess=True,
                    version_main=150
                )
            
            # Salva a referencia do display dentro do navegador para o Python nao matar o Xvfb (Garbage Collection)
            if hasattr(self, 'display'):
                navegador.xvfb_display = self.display
        else:
            if usar_seleniumwire:
                navegador = uc.Chrome(
                    options=options,
                    headless=False,
                    use_subprocess=True,
                    seleniumwire_options=seleniumwire_options
                )
            else:
                navegador = uc.Chrome(options=options, headless=False, use_subprocess=True)
            navegador.maximize_window()

        # Validação: Confirma se o proxy está de fato ativo testando o IP de saída
        if usar_seleniumwire:
            try:
                import requests
                test_proxy = {
                    'http': seleniumwire_options['proxy']['http'],
                    'https': seleniumwire_options['proxy']['https']
                }
                resp = requests.get('https://ipv4.icanhazip.com', proxies=test_proxy, timeout=10)
                print(f"[PROXY] IP de saída confirmado via proxy: {resp.text.strip()}")
            except Exception as e:
                print(f"[PROXY] AVISO - Falha ao validar IP de saída do proxy: {e}")

        # Captura os PIDs para manter o seu controle de encerramento
        driver_pid = navegador.browser_pid
        chrome_pids = self.find_chrome_processes(driver_pid)

        return navegador, chrome_pids

if __name__ == "__main__":
    manager = ChromeStealthManager()
    navegador, chrome_pids = manager.acessa_navegador()
    print(f"Navegador oculto aberto. PIDs: {chrome_pids}")