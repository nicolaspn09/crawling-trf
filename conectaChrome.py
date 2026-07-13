import sys
import psutil
import platform
from seleniumbase import Driver

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

        # No Linux, ainda usamos Xvfb pois UC mode no Linux requer headed mode para passar no Turnstile
        if platform.system() == "Linux":
            try:
                from pyvirtualdisplay import Display
                self.display = Display(visible=0, size=(1920, 1080))
                self.display.start()
            except ImportError:
                print("[AVISO] pacote pyvirtualdisplay não encontrado. Rode: pip3 install pyvirtualdisplay")
                
        print("[INFO] Iniciando Chrome pelo SeleniumBase (Modo UC)...")
        # Inicia o SeleniumBase com UC (Undetected Chromedriver) Mode habilitado
        navegador = Driver(
            uc=True,
            headless=False,
            browser="chrome",
            binary_location="/usr/bin/google-chrome" if platform.system() == "Linux" else None,
            no_sandbox=True,
            disable_gpu=True,
            window_size="1920,1080"
        )
        
        # Salva a referência do display dentro do navegador para o Python não matar o Xvfb (Garbage Collection)
        if hasattr(self, 'display'):
            navegador.xvfb_display = self.display

        # O SeleniumBase UC mode pode bugar se usar maximize_window(), então definimos o window_size acima.
        
        # Captura os PIDs para manter o seu controle de encerramento (opcional no SB, mas mantido por segurança)
        try:
            driver_pid = navegador.service.process.pid
            chrome_pids = self.find_chrome_processes(driver_pid)
        except Exception:
            chrome_pids = []

        return navegador, chrome_pids

if __name__ == "__main__":
    manager = ChromeStealthManager()
    navegador, chrome_pids = manager.acessa_navegador()
    print(f"Navegador oculto aberto. PIDs: {chrome_pids}")