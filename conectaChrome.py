import sys
import os
import psutil
import zipfile
import undetected_chromedriver as uc
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

        options = uc.ChromeOptions()
        
        proxy_host = os.environ.get("PROXY_HOST")
        proxy_port = os.environ.get("PROXY_PORT")
        proxy_user = os.environ.get("PROXY_USER")
        proxy_pass = os.environ.get("PROXY_PASS")

        if proxy_host and proxy_port:
            print(f"[PROXY] Configurando proxy: {proxy_host}:{proxy_port}")
            if proxy_user and proxy_pass:
                # Cria extensão dinâmica para injetar autenticação de proxy
                manifest_json = """
                {
                    "version": "1.0.0",
                    "manifest_version": 2,
                    "name": "Chrome Proxy",
                    "permissions": [
                        "proxy",
                        "tabs",
                        "unlimitedStorage",
                        "storage",
                        "<all_urls>",
                        "webRequest",
                        "webRequestBlocking"
                    ],
                    "background": {
                        "scripts": ["background.js"]
                    },
                    "minimum_chrome_version":"22.0.0"
                }
                """
                background_js = """
                var config = {
                        mode: "fixed_servers",
                        rules: {
                        singleProxy: {
                            scheme: "http",
                            host: "%s",
                            port: parseInt(%s)
                        },
                        bypassList: ["localhost"]
                        }
                    };

                chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

                function callbackFn(details) {
                    return {
                        authCredentials: {
                            username: "%s",
                            password: "%s"
                        }
                    };
                }

                chrome.webRequest.onAuthRequired.addListener(
                            callbackFn,
                            {urls: ["<all_urls>"]},
                            ['blocking']
                );
                """ % (proxy_host, proxy_port, proxy_user, proxy_pass)

                pluginfile = os.path.abspath('proxy_auth_plugin.zip')
                with zipfile.ZipFile(pluginfile, 'w') as zp:
                    zp.writestr("manifest.json", manifest_json)
                    zp.writestr("background.js", background_js)
                
                options.add_extension(pluginfile)
            else:
                # Proxy sem autenticação
                options.add_argument(f'--proxy-server=http://{proxy_host}:{proxy_port}')
        
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
            navegador = uc.Chrome(options=options, headless=False, browser_executable_path='/usr/bin/google-chrome', use_subprocess=True)
            
            # Salva a referencia do display dentro do navegador para o Python nao matar o Xvfb (Garbage Collection)
            if hasattr(self, 'display'):
                navegador.xvfb_display = self.display
        else:
            navegador = uc.Chrome(options=options, headless=False, use_subprocess=True)
            navegador.maximize_window()

        # Captura os PIDs para manter o seu controle de encerramento
        driver_pid = navegador.browser_pid
        chrome_pids = self.find_chrome_processes(driver_pid)

        return navegador, chrome_pids

if __name__ == "__main__":
    manager = ChromeStealthManager()
    navegador, chrome_pids = manager.acessa_navegador()
    print(f"Navegador oculto aberto. PIDs: {chrome_pids}")