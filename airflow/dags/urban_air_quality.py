from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from src.pipeline import run

with DAG(
    dag_id="urban_air_quality_etl",
    start_date=datetime(2025, 1, 1),
    schedule="0 3 * * *",
    catchup=False,
    default_args={"owner": "data-platform", "retries": 3, "retry_delay": timedelta(minutes=5)},
    tags=["air-quality", "etl"],
) as dag:
    extract_validate_transform_load = PythonOperator(task_id="extract_validate_transform_load", python_callable=run)
    dbt_build_and_test = BashOperator(task_id="dbt_build_and_test", bash_command="dbt build --project-dir /app/dbt --profiles-dir /app/dbt")
    extract_validate_transform_load >> dbt_build_and_test
