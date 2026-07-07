# RPA de Consulta e Triagem Processual - TRF4 (POC)

Este repositório contém uma solução avançada de **RPA (Robotic Process Automation)** desenvolvida em Python para automação de consultas, extração e triagem inteligente de processos jurídicos nos portais dos Tribunais Regionais Federais (TRF), com foco principal no **TRF4** (Região Sul: RS, PR, SC).

O objetivo principal desta Prova de Conceito (POC) é realizar a busca automatizada por CPF/CNPJ, contornar barreiras de segurança (como Cloudflare Turnstile) e analisar o teor das decisões judiciais para identificar oportunidades baseadas na tese de **Atividade Concomitante**.

---

## 🚀 Principais Funcionalidades

*   **Evasão Avançada Antibot (Stealth Modality):** Integração com `undetected-chromedriver` e customizações profundas no Firefox Selenium para ocultar propriedades de automação (`dom.webdriver.enabled`, flags de automação e assinaturas do WebDriver), simulando perfeitamente o comportamento de um usuário real.
*   **Interação Humana Mimetizada:** Cliques com deslocamento (*offset*) randômico e digitação humanizada (caractere por caractere com intervalos flutuantes de tempo).
*   **Intercepção de Captcha (Cloudflare Turnstile):** Gerenciamento inteligente e passivo de iframes, aguardando de forma dinâmica a validação automática antes de prosseguir com o fluxo de navegação.
*   **Navegação Multidocumento Segura:** Varredura em abas isoladas no e-Proc para extração de conteúdo textual completo, preservando o estado e o foco da listagem principal de processos.
*   **Triagem Jurídica Automatizada:** Análise heurística textual das decisões para classificar o potencial de ajuizamento de novas ações.

---

## 📁 Estrutura de Arquivos (Arquitetura Modular)

Seguindo o princípio de Responsabilidade Única (SRP), a aplicação está dividida em módulos abstraídos:

*   **`main_robo.py`:** Ponto de entrada oficial da aplicação. Configura o dicionário de mapeamento entre Estados e os seus respectivos robôs de processamento (ex: "SANTA CATARINA" -> `BotTRF4().executar`), orquestrando a pipeline de forma abstrata.
*   **`Orquestrador.py`:** Classe `OrquestradorDrive` responsável por realizar a navegação e leitura estruturada nas pastas da nuvem (Teses -> Estados -> Planilhas), acionar a validação do arquivo e delegar a execução ao Bot correto.
*   **`GoogleDrive.py`:** Classe `GoogleDriveManager` responsável exclusivamente pela comunicação com a API do Google Drive (listar, criar pastas, baixar `.xlsx`/`.csv` e mover arquivos validados para a pasta "ANALISADO").
*   **`trf4.py`:** Classe `BotTRF4`. Contém toda a lógica orientada a objetos para abrir o navegador, tratar captcha, coletar links e executar a triagem jurídica no site do TRF4. Totalmente desacoplada da fonte de dados originais.
*   **`Database.py`:** Classe responsável pela comunicação exclusiva com o banco de dados PostgreSQL.
*   **`navegador.py`:** Wrapper robusto (`NavegadorPy`) sobre a API do Selenium WebDriver. Centraliza funções reutilizáveis como cliques assistidos, digitação humanizada, gerenciamento de abas e detecção/foco no iframe do Cloudflare.
*   **`acessaSite.py`:** Módulo utilitário (`AcessaSite`) encarregado de mapear e retornar a URL correta do portal processual com base na Unidade Federativa (UF) informada.
*   **`conectaChrome.py` & `conectaFirefox.py`:** Módulos que configuram e inicializam os navegadores em modo furtivo utilizando técnicas de evasão antibot.

---

## ⚖️ Regras de Negócio e Classificação de Triagem

O robô avalia o texto integral extraído de cada processo e atribui uma classificação de cor para a planilha/console, baseando-se nos seguintes critérios sequenciais:

| Classificação / Cor | Motivo | Critério Técnico |
| :--- | :--- | :--- |
| **BRANCO** | Não elegível | O polo passivo da ação **não** contém "INSS" ou "INSTITUTO NACIONAL DO SEGURO SOCIAL". |
| **BRANCO** | Tese diferente | A ação é contra o INSS, mas **não** cita termos da tese ("CONCOMITANTE", "ART. 32", "LEI 8.213", "TEMA 1070"). |
| **AMARELO** | **Oportunidade Comercial** | Tese localizada, mas o processo foi extinto **sem resolução de mérito** ("SEM RESOLUÇÃO", "DESISTÊNCIA", "ART. 485"). **Viável propor nova ação jurídica.** |
| **CINZA** | Descartado | Processo com sentença definitiva **com resolução de mérito** ("PROCEDENTE", "IMPROCEDENTE", "ART. 487"). Coisa julgada. |
| **ALERTA / BRANCO** | Revisão Manual | A tese foi localizada, mas a estrutura da sentença foge do padrão esperado pelas palavras-chave. |

---

## 🛠️ Pré-requisitos e Configuração

### 1. Dependências do Sistema
*   Python 3.10 ou superior instalado.
*   Google Chrome ou Mozilla Firefox instalado.

### 2. Instalação das Bibliotecas Python
Instale os pacotes necessários através do terminal:

```bash
pip install selenium undetected-chromedriver psutil requests
```

> *Nota: Caso o projeto possua um arquivo `requirements.txt` na raiz principal, você também pode utilizar `pip install -r requirements.txt`.*

---

## 💻 Como Executar

Para iniciar a execução da automação (que varre o Google Drive, baixa as planilhas pendentes e ativa os robôs correspondentes parametrizados):

```bash
python main_robo.py
```

## ⚠️ Avisos e Boas Práticas

*   **Uso Ético:** Este robô foi desenvolvido para fins de otimização de consultas internas e triagem legítima de carteiras de clientes em conformidade com as diretrizes do e-Proc. Evite requisições massivas em curtos períodos de tempo para não sobrecarregar os servidores públicos.
*   **Manutenção de Seletores:** Mudanças estruturais na árvore do DOM dos portais do TRF podem exigir atualizações nos XPaths mapeados em `trf4.py` e `navegador.py`.
