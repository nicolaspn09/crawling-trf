import pendulum
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta

# Definindo a DAG
default_args = {
    'owner': 'rpa',
    'start_date': pendulum.datetime(2025, 12, 1, tz="America/Sao_Paulo"),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'rpa_robo_trf',
    default_args=default_args,
    description='DAG para o processo de CI/CD do GitHub e execução do Robô TRF todos os dias',
    schedule_interval='0 6 * * *',  # Executa todos os dias às 06:00
    catchup=False,
    max_active_runs=1,
    tags=['rpa', 'trf', 'github', 'prod']
)

# Como o repositório é público, NÃO precisamos de token nenhum!
url_git = "https://github.com/nicolaspn09/crawling-trf.git"

# Pasta de destino oficial do projeto
destino_pasta = "/home/codigos_airflow/lodetti-silveira-crawling-trf"
# Caminho do script de CI/CD
caminho_script_cicd = "/home/codigos_airflow/lodetti-silveira-crawling-trf/Baixa Arquivos Github/baixaArquivosGithub.py"

# Tarefa para executar o script baixaArquivosGithub.py via SSH no Windows
executa_baixar_arquivos = SSHOperator(
    task_id='ssh-executa_baixar_arquivos_github',
    ssh_conn_id='rpa_vps_host',  # O ID da conexão SSH configurada no seu Airflow (mesmo do GitLab)
    command=f'python3 "{caminho_script_cicd}" --url_git "{url_git}" --destino_pasta "{destino_pasta}"',
    dag=dag,
    trigger_rule='all_success'
)

# Caminho do robô principal TRF
caminho_script_robo = "/home/codigos_airflow/lodetti-silveira-crawling-trf/main_robo.py"

# Tarefa para executar o Robô TRF
executa_robo_trf = SSHOperator(
    task_id='ssh-executa_robo_trf',
    ssh_conn_id='rpa_vps_host',
    command=f'python3 "{caminho_script_robo}"',
    dag=dag,
    trigger_rule='all_success'
)

# Definindo o início e o fim
inicio = EmptyOperator(
    task_id='inicio',
    dag=dag,
)

fim = EmptyOperator(
    task_id='fim',
    dag=dag,
)

# Definindo a ordem das tarefas
inicio >> executa_baixar_arquivos >> executa_robo_trf >> fim
