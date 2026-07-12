import sys
import psutil
import undetected_chromedriver as uc
import platform

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
        else:
            navegador = uc.Chrome(options=options, headless=True, use_subprocess=True)

        # Captura os PIDs para manter o seu controle de encerramento
        driver_pid = navegador.browser_pid
        chrome_pids = self.find_chrome_processes(driver_pid)

        return navegador, chrome_pids

if __name__ == "__main__":
    manager = ChromeStealthManager()
    navegador, chrome_pids = manager.acessa_navegador()
    print(f"Navegador oculto aberto. PIDs: {chrome_pids}")