class AcessaSite:
    def __init__(self):
        pass


    def site(self, uf):
        if str(uf).lower() in ("ac", "ap", "am", "am", "ba", "go", "ma", "mt", "mg", "pa", "pi", "ro", "rr", "to", "df"):
            return "https://www.trf1.jus.br/trf1/processual/consulta-processual"

        if str(uf).lower() in ("rj", "es"):
            return "https://www.trf2.jus.br/jf2/acesso-aos-sistemas-processuais"
        
        if str(uf).lower() in ("sp", "ms"):
            return "https://www.trf3.jus.br/"
        
        if str(uf).lower() in ("rs", "pr", "sc"):
            return "https://www.trf4.jus.br/trf4/controlador.php?acao=principal&"
        
        if str(uf).lower() in ("al", "ce", "pb", "pe", "rn", "se"):
            return "https://www.trf5.jus.br/index.php/consulta-processual-fisico-e-eletronico"
        
        if str(uf).lower() in ("mg"):
            return "https://portal.trf6.jus.br/"