import sys
import os
import json
import psutil
import random
import string
import socket
import select
import base64
import threading
import socketserver
import undetected_chromedriver as uc
import platform
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# LOCAL PROXY FORWARDER (stdlib puro, zero dependências externas)
#
# Histórico de falhas ao tentar proxy no Chrome:
# 1. add_extension(.zip MV2) → Ignorado silenciosamente pelo UC
# 2. selenium-wire → Incompatível com Python 3.12 (pyOpenSSL)
# 3. --load-extension (MV3) → Extensão carrega mas NÃO aplica proxy (IP=VPS)
#
# Solução definitiva: proxy local em 127.0.0.1 que faz relay autenticado.
# Chrome conecta em localhost (sem auth) → ForwardProxy injeta auth → IPRoyal
# =============================================================================

class _ProxyHandler(socketserver.BaseRequestHandler):
    """Handler que recebe conexões do Chrome e injeta auth no upstream."""
    
    upstream_host = ''
    upstream_port = 0
    upstream_auth_header = b''  # Proxy-Authorization: Basic xxx

    def handle(self):
        try:
            client = self.request
            client.settimeout(90)
            
            # Lê a primeira requisição do Chrome (ex: "CONNECT google.com:443 HTTP/1.1\r\n")
            data = b''
            while b'\r\n\r\n' not in data:
                chunk = client.recv(8192)
                if not chunk:
                    return
                data += chunk

            # Separa a primeira linha das headers
            header_end = data.index(b'\r\n\r\n')
            request_headers = data[:header_end]
            request_body = data[header_end + 4:]
            
            lines = request_headers.split(b'\r\n')
            first_line = lines[0]  # Ex: "CONNECT google.com:443 HTTP/1.1"
            
            # Conecta no proxy upstream (IPRoyal)
            upstream = socket.create_connection(
                (self.upstream_host, self.upstream_port), timeout=30
            )
            upstream.settimeout(90)
            
            # Reconstrói as headers INJETANDO a autenticação do proxy
            new_headers = [first_line, self.upstream_auth_header]
            for line in lines[1:]:
                # Remove qualquer auth existente pra evitar duplicação
                if not line.lower().startswith(b'proxy-authorization'):
                    new_headers.append(line)
            
            upstream.sendall(b'\r\n'.join(new_headers) + b'\r\n\r\n' + request_body)
            
            if first_line.startswith(b'CONNECT'):
                # HTTPS: Lê resposta do upstream, envia "200" pro Chrome, e faz tunnel
                response = b''
                while b'\r\n\r\n' not in response:
                    chunk = upstream.recv(4096)
                    if not chunk:
                        return
                    response += chunk
                
                status_line = response.split(b'\r\n')[0]
                if b'200' in status_line:
                    client.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
                    self._tunnel(client, upstream)
                else:
                    # Upstream negou a conexão (403 etc)
                    print(f"[FORWARDER ERRO] Upstream negou a conexao para {first_line}: {response}")
                    client.sendall(response)
            else:
                # HTTP: Relay simples da resposta
                while True:
                    chunk = upstream.recv(16384)
                    if not chunk:
                        break
                    client.sendall(chunk)
            
            upstream.close()
        except Exception:
            pass

    def _tunnel(self, client, upstream):
        """Relay bidirecional de bytes (tunnel TCP transparente)."""
        sockets = [client, upstream]
        while True:
            try:
                readable, _, errors = select.select(sockets, [], sockets, 60)
                if errors or not readable:
                    break
                for s in readable:
                    data = s.recv(16384)
                    if not data:
                        return
                    target = upstream if s is client else client
                    target.sendall(data)
            except Exception:
                break


class _ThreadedProxyServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class LocalProxyForwarder:
    """
    Inicia um proxy HTTP local (127.0.0.1) que repassa todo tráfego
    para o proxy upstream autenticado (IPRoyal).
    
    Chrome conecta aqui sem auth → este servidor injeta Proxy-Authorization
    → encaminha para geo.iproyal.com:12321.
    """
    def __init__(self, upstream_host, upstream_port, upstream_user, upstream_pass):
        auth_b64 = base64.b64encode(f"{upstream_user}:{upstream_pass}".encode()).decode()
        
        # Cria handler com os dados do upstream
        handler = type('ProxyHandler', (_ProxyHandler,), {
            'upstream_host': upstream_host,
            'upstream_port': int(upstream_port),
            'upstream_auth_header': f'Proxy-Authorization: Basic {auth_b64}'.encode(),
        })
        
        # Bind em porta aleatória
        self.server = _ThreadedProxyServer(('127.0.0.1', 0), handler)
        self.port = self.server.server_address[1]
        
        # Roda em thread daemon (morre junto com o processo principal)
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        
        print(f"[PROXY] Forwarder local iniciado em 127.0.0.1:{self.port}")
    
    def stop(self):
        self.server.shutdown()


class ChromeStealthManager:
    def __init__(self, caminho_arquivo=None):
        self.caminho_arquivo = caminho_arquivo
        self._proxy_forwarder = None

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
        
        # =====================================================================
        # PROXY VIA FORWARDER LOCAL (100% confiável, sem extensão)
        #
        # Fluxo: Chrome → 127.0.0.1:PORTA (sem auth) → Forwarder injeta
        #         Proxy-Authorization → geo.iproyal.com:12321 (com auth)
        #
        # Por que não usar extensão?
        #   - add_extension(.zip) é ignorado pelo UC
        #   - --load-extension + MV3 carrega mas NÃO aplica proxy (IP=VPS)
        #   - selenium-wire é incompatível com Python 3.12
        # =====================================================================
        proxy_host = None # Removido o proxy para rodar gratis no IP da VPS!
        # proxy_host = os.environ.get("PROXY_HOST")
        proxy_port = os.environ.get("PROXY_PORT")
        proxy_user = os.environ.get("PROXY_USER")
        proxy_pass = os.environ.get("PROXY_PASS")

        if proxy_host and proxy_port and proxy_user and proxy_pass:
            # IPRoyal Residential: Para evitar que o IP mude a cada conexao TCP (o que quebra
            # a validacao do Cloudflare e causa ERR_TUNNEL_CONNECTION_FAILED),
            # precisamos fixar a sessao anexando '_session-xyz' na senha.
            if "iproyal" in proxy_host.lower() and "_session-" not in proxy_pass:
                import random
                import string
                session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                proxy_pass = f"{proxy_pass}_session-{session_id}"
                print(f"[PROXY] Fixando Sessao IPRoyal: {session_id} para evitar ERR_TUNNEL_CONNECTION_FAILED")

            print(f"[PROXY] Upstream: {proxy_host}:{proxy_port}")
            print(f"[PROXY] User: {proxy_user}, Pass: {proxy_pass[:4]}***")
            
            # Inicia o forwarder local (thread daemon)
            self._proxy_forwarder = LocalProxyForwarder(
                upstream_host=proxy_host,
                upstream_port=proxy_port,
                upstream_user=proxy_user,
                upstream_pass=proxy_pass,
            )
            
            # Chrome aponta pro proxy local (sem auth, sem extensão)
            local_proxy = f"http://127.0.0.1:{self._proxy_forwarder.port}"
            options.add_argument(f'--proxy-server={local_proxy}')
            print(f"[PROXY] Chrome configurado para usar: {local_proxy}")
            
        elif proxy_host and proxy_port:
            # Proxy sem autenticação (direto)
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

        # [ECONOMIA DE BANDA] Desativado temporariamente pois o Cloudflare Turnstile exige imagens ativas para validar
        # prefs = {
        #     "profile.managed_default_content_settings.images": 2,
        # }
        # options.add_experimental_option("prefs", prefs)

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
            navegador = uc.Chrome(options=options, headless=False, use_subprocess=True, version_main=150)
            navegador.maximize_window()

        # Validação: Verifica o IP de saída para confirmar se o proxy está ativo
        if proxy_host and proxy_port:
            try:
                import time
                time.sleep(2)  # Dá tempo pro Chrome carregar
                navegador.get('https://ipv4.icanhazip.com')
                time.sleep(3)
                from selenium.webdriver.common.by import By
                ip_texto = navegador.find_element(By.TAG_NAME, "body").text.strip()
                
                # Compara com o IP da VPS pra confirmar que o proxy está funcionando
                vps_ip = os.environ.get("DB_HOST", "desconhecido")
                if ip_texto == vps_ip:
                    print(f"[PROXY] ⚠️ ALERTA: IP de saída ({ip_texto}) É IGUAL ao IP da VPS ({vps_ip})!")
                    print(f"[PROXY] ⚠️ O proxy NÃO está funcionando! Chrome está indo direto.")
                else:
                    print(f"[PROXY] ✅ IP de saída confirmado: {ip_texto} (VPS: {vps_ip})")
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
    input("Pressione Enter para fechar...")