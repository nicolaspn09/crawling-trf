import sys
import os
import json
import psutil
import tempfile
import random
import string
import undetected_chromedriver as uc
import platform
from dotenv import load_dotenv

load_dotenv()

class ChromeStealthManager:
    def __init__(self, caminho_arquivo=None):
        self.caminho_arquivo = caminho_arquivo
        self._proxy_ext_dir = None

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

    def _criar_extensao_proxy(self, host, port, user, password):
        """
        Cria uma extensão Chrome DESCOMPACTADA (Manifest V3) para autenticação de proxy.
        
        Diferente do add_extension() que é ignorado pelo undetected_chromedriver,
        o --load-extension com diretório descompactado funciona porque é apenas
        uma flag nativa do Chrome, sem interferência do patching do UC.
        """
        ext_dir = tempfile.mkdtemp(prefix='proxy_ext_')
        self._proxy_ext_dir = ext_dir

        manifest = {
            "version": "1.0.0",
            "manifest_version": 3,
            "name": "Proxy Auth Helper",
            "permissions": ["proxy", "webRequest", "webRequestAuthProvider"],
            "host_permissions": ["<all_urls>"],
            "background": {
                "service_worker": "background.js"
            },
            "minimum_chrome_version": "108"
        }

        background_js = """
// Configura o proxy
chrome.proxy.settings.set({
    value: {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: %s
            },
            bypassList: ["localhost", "127.0.0.1"]
        }
    },
    scope: "regular"
});

// Intercepta requisições de autenticação do proxy e injeta credenciais
chrome.webRequest.onAuthRequired.addListener(
    (details, callback) => {
        callback({
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        });
    },
    { urls: ["<all_urls>"] },
    ["asyncBlocking"]
);
""" % (host, port, user, password)

        with open(os.path.join(ext_dir, 'manifest.json'), 'w') as f:
            json.dump(manifest, f, indent=2)

        with open(os.path.join(ext_dir, 'background.js'), 'w') as f:
            f.write(background_js)

        print(f"[PROXY] Extensão MV3 criada em: {ext_dir}")
        return ext_dir

    def acessa_navegador(self):
        if self.caminho_arquivo:
            sys.stdout = open(self.caminho_arquivo, 'w')

        options = uc.ChromeOptions()
        
        # =====================================================================
        # PROXY AUTENTICADO VIA EXTENSÃO DESCOMPACTADA (Manifest V3)
        #
        # Histórico de falhas:
        # 1. add_extension(.zip) -> Silenciosamente ignorado pelo UC
        # 2. selenium-wire -> Incompatível com pyOpenSSL moderno (Python 3.12)
        #
        # Solução: --load-extension com diretório descompactado
        # Funciona porque é uma flag nativa do Chrome, não interceptada pelo UC.
        # =====================================================================
        proxy_host = os.environ.get("PROXY_HOST")
        proxy_port = os.environ.get("PROXY_PORT")
        proxy_user = os.environ.get("PROXY_USER")
        proxy_pass = os.environ.get("PROXY_PASS")

        if proxy_host and proxy_port and proxy_user and proxy_pass:
            # =====================================================================
            # ROTAÇÃO DE IP: Gera um session_id aleatório a cada browser novo.
            # IPRoyal usa o formato: user_session-XXXXX para criar sessões sticky
            # únicas. Sem isso, o mesmo IP é reutilizado indefinidamente.
            # =====================================================================
            session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            proxy_user_rotated = f"{proxy_user}_session-{session_id}"
            print(f"[PROXY] Configurando proxy: {proxy_host}:{proxy_port} (sessão: {session_id})")
            ext_dir = self._criar_extensao_proxy(proxy_host, proxy_port, proxy_user_rotated, proxy_pass)
            options.add_argument(f'--load-extension={ext_dir}')
        elif proxy_host and proxy_port:
            # Proxy sem autenticação (não precisa de extensão)
            print(f"[PROXY] Configurando proxy sem auth: {proxy_host}:{proxy_port}")
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
            navegador = uc.Chrome(options=options, headless=False, browser_executable_path='/usr/bin/google-chrome', use_subprocess=True, version_main=150)
            
            # Salva a referencia do display dentro do navegador para o Python nao matar o Xvfb (Garbage Collection)
            if hasattr(self, 'display'):
                navegador.xvfb_display = self.display
        else:
            navegador = uc.Chrome(options=options, headless=False, use_subprocess=True)
            navegador.maximize_window()

        # Validação: Verifica o IP de saída para confirmar se o proxy está ativo
        if proxy_host and proxy_port:
            try:
                import time
                time.sleep(2)  # Dá tempo pro Chrome carregar a extensão
                navegador.get('https://ipv4.icanhazip.com')
                time.sleep(3)
                from selenium.webdriver.common.by import By
                ip_texto = navegador.find_element(By.TAG_NAME, "body").text.strip()
                print(f"[PROXY] IP de saída confirmado: {ip_texto}")
            except Exception as e:
                print(f"[PROXY] AVISO - Falha ao validar IP de saída: {e}")

        # Captura os PIDs para manter o seu controle de encerramento
        driver_pid = navegador.browser_pid
        chrome_pids = self.find_chrome_processes(driver_pid)

        return navegador, chrome_pids

if __name__ == "__main__":
    manager = ChromeStealthManager()
    navegador, chrome_pids = manager.acessa_navegador()
    print(f"Navegador oculto aberto. PIDs: {chrome_pids}")