# Deploy de Modelo de ML: 3 Abordagens

Projeto da live sobre colocar um modelo de Machine Learning em produção.

O mesmo modelo (`shopping_preference_model.pkl`) é publicado de três formas diferentes, para mostrar que "colocar em produção" não significa uma coisa só.

| Deploy | Abordagem | Onde roda | Status |
|---|---|---|---|
| 1 | Pipeline batch agendado | Databricks | Documentado abaixo |
| 2 | API + interface em container | Máquina local e Render | Documentado abaixo |
| 3 | Função serverless | Azure Functions | Documentado abaixo |

Aplicação publicada: **https://deploy2-onpremise.onrender.com**

---

## O modelo

`shopping_preference_model.pkl` prevê se um cliente prefere comprar **Online** (1) ou em **Loja física** (0).

É um `Pipeline` do Scikit-learn, não apenas o classificador:

```
DataFrame (24 colunas)
        |
        v
ColumnTransformer
        |
        +-- 22 numéricas  ⭢ passthrough
        |
        `-- 2 categóricas ⭢ TargetEncoder
        |
        v
LGBMClassifier
        |
        v
Predição
```

Isso importa para o deploy: o pré-processamento está **dentro do PKL**. Não é preciso reimplementar encoding na aplicação. Basta entregar o DataFrame com as 24 colunas e chamar `predict`.

### Versões do treino

O modelo foi serializado neste ambiente:

```
python        3.10.18
scikit-learn  1.7.1
lightgbm      4.6.0
pandas        2.2.3
numpy         2.2.6
joblib        1.5.1
```

Quanto mais distante o ambiente de produção estiver disso, maior o risco de `InconsistentVersionWarning` ou falha na desserialização. É o problema mais chato de deploy de ML, porque só aparece no `joblib.load`, já em produção.

---
## Ambiente virtual

Antes de qualquer coisa, crie um ambiente virtual. Ele isola as bibliotecas deste projeto das que estão instaladas no seu Python global, evitando que a versão do `scikit-learn` de um projeto quebre o `.pkl` de outro. Neste projeto isso é ainda mais importante, porque as versões precisam bater com as do treino do modelo.

### Criando

```powershell
py -3.10 -m venv .venv
```

No Linux ou Mac:

```bash
python3.10 -m venv .venv
```

O `py -3.10` é o launcher do Windows escolhendo a versão. Se o Python 3.10 não estiver instalado, o comando falha, e vale instalar antes em vez de cair em outra versão.

### Ativando

O caminho do script de ativação depende de onde a pasta está e de qual terminal você usa.

**Windows, `.venv` na pasta atual:**

```powershell
.\.venv\Scripts\activate
```

**Windows, `.venv` em outra pasta:**

```powershell
C:\Users\SeuUsuario\projetos\meu_projeto\.venv\Scripts\activate
```

Ou, se o caminho for relativo à pasta em que você está:

```powershell
..\.venv\Scripts\activate
..\..\outro_projeto\.venv\Scripts\activate
```

**Windows, no CMD em vez do PowerShell:**

```cmd
.venv\Scripts\activate.bat
```

**Windows, Git Bash:**

```bash
source .venv/Scripts/activate
```

**Linux ou Mac:**

```bash
source .venv/bin/activate
source /caminho/completo/para/.venv/bin/activate
```

### Se o PowerShell bloquear

Libere apenas para a sessão atual, o que não altera a política da máquina:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### Confirmando que deu certo

Depois de ativar, o terminal passa a exibir `(.venv)` no início da linha. Para ter certeza de que é o ambiente certo, e não o Python do sistema:

```powershell
python -c "import sys; print(sys.executable)"
```

O caminho impresso precisa apontar para dentro da sua pasta `.venv`.

### Instalando as dependências

```powershell
python -m pip install -r requirements.txt
```

O `python -m pip` em vez de `pip` direto garante que o pip usado é o do ambiente ativo. Quando existem várias instalações de Python na máquina, o `pip` solto às vezes aponta para outra.

### Sem ativar

Também dá para usar o ambiente sem ativar, chamando o executável direto. Útil em scripts e agendadores:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

### Desativando

```powershell
deactivate
```

A pasta `.venv` é local e não vai para o Git nem para a imagem Docker: ela está listada no `.gitignore` e no `.dockerignore`.
---

# Deploy 1: Pipeline Batch no Databricks

Pontuação em lote. Nada de API, nada de tempo real. Um job lê registros do banco, roda o modelo e grava as predições de volta.

É o formato mais comum de deploy de ML no mundo corporativo e quase nunca é o que aparece em tutorial.

## Arquitetura

```
generate_data.py            inference.py
      |                          |
      v                          v
  gera dados              lê a tabela de entrada
  sintéticos                     |
      |                          v
      v                    joblib.load(PKL)
 tabela de entrada               |
 (consumer_shopping_input) ⭢    v
                             predict
                                 |
                                 v
                          tabela de resultados
                          (shopping_preference_predictions)
```

## Estrutura

```
Live_13_deploy/
|
|-- generate_data.py                            # gera e carrega dados de entrada
|-- inference.py                                # lê, pontua e grava resultado
|-- shopping_preference_model.pkl               # modelo treinado
|-- schema.sql                                  # DDL das tabelas
`-- .env                                        # credenciais do banco
```

Tudo na mesma pasta, sem subpastas. O PKL precisa ficar ao lado dos notebooks no Workspace do Databricks.

---

## Passo 1: Banco de dados

Foi usado PostgreSQL no [Render](https://render.com) (plano free).

No dashboard, em **Postgres > Info**, os campos necessários são: Hostname, Port, Database, Username e Password.

Atenção ao hostname: a tela mostra o **interno**, que só funciona dentro do Render. Para acessar de fora (DBeaver, Databricks) é preciso o **externo**, que aparece na *External Database URL* e tem o sufixo da região:

```
dpg-xxxxxxxxx-a.oregon-postgres.render.com
```

### .env

```
# Conexão do banco (PostgreSQL no Render)
DB_HOST=dpg-xxxxxxxxx-a.oregon-postgres.render.com
DB_PORT=5432
DB_NAME=seu_banco
DB_USER=seu_usuario
DB_PASSWORD=sua_senha

INPUT_TABLE=consumer_shopping_input
OUTPUT_TABLE=shopping_preference_predictions
```

O `.env` sobe na mesma pasta do notebook no Workspace do Databricks. Adicione ele ao `.gitignore` antes do primeiro commit.

### Conectando no DBeaver

Database > New Connection > PostgreSQL, preenchendo Host, Port, Database, Username e Password. Na aba **SSL**, marque `Use SSL` com mode `require`. O Render recusa conexão externa sem TLS, e sem isso o erro não explica o motivo.

---

## Passo 2: Criar as tabelas

Execute o `schema.sql` no DBeaver ou no console do Render.

```sql
CREATE TABLE consumer_shopping_input (
    customer_id                  TEXT PRIMARY KEY,
    batch_id                     TEXT,
    age                          INTEGER,
    monthly_income               INTEGER,
    daily_internet_hours         REAL,
    smartphone_usage_years       INTEGER,
    social_media_hours           REAL,
    online_payment_trust_score   INTEGER,
    tech_savvy_score             INTEGER,
    monthly_online_orders        INTEGER,
    monthly_store_visits         INTEGER,
    avg_online_spend             INTEGER,
    avg_store_spend              INTEGER,
    discount_sensitivity         INTEGER,
    return_frequency             INTEGER,
    avg_delivery_days            INTEGER,
    delivery_fee_sensitivity     INTEGER,
    free_return_importance       INTEGER,
    product_availability_online  INTEGER,
    impulse_buying_score         INTEGER,
    need_touch_feel_score        INTEGER,
    brand_loyalty_score          INTEGER,
    environmental_awareness      INTEGER,
    time_pressure_level          INTEGER,
    gender                       TEXT,
    city_tier                    TEXT
);

CREATE TABLE shopping_preference_predictions (
    customer_id         TEXT PRIMARY KEY,
    batch_id            TEXT,
    prediction          INTEGER,
    label               TEXT,
    probability_online  REAL,
    scored_at           TIMESTAMP DEFAULT NOW()
);
```

Duas tabelas separadas de propósito. A de entrada é o que o negócio produz. A de resultado é o que o modelo produz.

---

## Passo 3: Gerar os dados de entrada

`generate_data.py` cria registros sintéticos com a mesma distribuição da base original e grava na tabela de entrada. Simula a chegada de clientes novos que ainda não têm predição.

```python
# generate_data.py

import os
import uuid
from datetime import datetime

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

OPTIONS = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

N = 500
rng = np.random.default_rng()

df = pd.DataFrame({
    "customer_id": [str(uuid.uuid4()) for _ in range(N)],
    "batch_id": datetime.now().strftime("batch_%Y%m%d_%H%M%S"),
    "age": rng.integers(18, 80, N),
    "monthly_income": rng.integers(15005, 249990, N),
    "daily_internet_hours": rng.normal(6.0, 2.0, N).clip(1, 12).round(1),
    "smartphone_usage_years": rng.integers(1, 15, N),
    "social_media_hours": rng.normal(2.5, 1.3, N).clip(0, 6).round(1),
    "online_payment_trust_score": rng.integers(1, 11, N),
    "tech_savvy_score": rng.integers(1, 11, N),
    "monthly_online_orders": rng.integers(0, 50, N),
    "monthly_store_visits": rng.integers(0, 20, N),
    "avg_online_spend": rng.integers(523, 149997, N),
    "avg_store_spend": rng.integers(542, 149973, N),
    "discount_sensitivity": rng.integers(1, 11, N),
    "return_frequency": rng.integers(0, 10, N),
    "avg_delivery_days": rng.integers(1, 8, N),
    "delivery_fee_sensitivity": rng.integers(1, 11, N),
    "free_return_importance": rng.integers(1, 11, N),
    "product_availability_online": rng.integers(1, 11, N),
    "impulse_buying_score": rng.integers(1, 11, N),
    "need_touch_feel_score": rng.integers(1, 11, N),
    "brand_loyalty_score": rng.integers(1, 11, N),
    "environmental_awareness": rng.integers(1, 11, N),
    "time_pressure_level": rng.integers(1, 11, N),
    "gender": rng.choice(["Female", "Male", "Other"], N),
    "city_tier": rng.choice(["Tier 1", "Tier 2", "Tier 3"], N),
})

(
    spark.createDataFrame(df).write.format("postgresql")
    .options(**OPTIONS)
    .option("dbtable", os.getenv("INPUT_TABLE"))
    .mode("append")
    .save()
)

print(f"{len(df)} registros inseridos. Lote: {df['batch_id'][0]}")
```

Duas features usam distribuição normal em vez de uniforme (`daily_internet_hours` e `social_media_hours`), porque é assim que elas se comportam na base original. Se virarem uniformes, os dados sintéticos ficam visivelmente diferentes do que o modelo viu no treino.

O `batch_id` identifica a leva. Serve para saber qual execução gerou quais registros.

---

## Passo 4: Inferência

`inference.py` lê a tabela de entrada, carrega o PKL, roda o modelo e grava o resultado.

```python
# inference.py

import os

import joblib
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

OPTIONS = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

COLUNAS = [
    "age", "monthly_income", "daily_internet_hours", "smartphone_usage_years",
    "social_media_hours", "online_payment_trust_score", "tech_savvy_score",
    "monthly_online_orders", "monthly_store_visits", "avg_online_spend",
    "avg_store_spend", "discount_sensitivity", "return_frequency",
    "avg_delivery_days", "delivery_fee_sensitivity", "free_return_importance",
    "product_availability_online", "impulse_buying_score", "need_touch_feel_score",
    "brand_loyalty_score", "environmental_awareness", "time_pressure_level",
    "gender", "city_tier",
]

df = (
    spark.read.format("postgresql")
    .options(**OPTIONS)
    .option("dbtable", os.getenv("INPUT_TABLE"))
    .load()
    .toPandas()
)

modelo = joblib.load("shopping_preference_model.pkl")

X = df[COLUNAS]

resultado = pd.DataFrame({
    "customer_id": df["customer_id"],
    "batch_id": df["batch_id"],
    "prediction": modelo.predict(X),
    "probability_online": modelo.predict_proba(X)[:, 1],
})
resultado["label"] = resultado["prediction"].map({0: "Store", 1: "Online"})

(
    spark.createDataFrame(resultado).write.format("postgresql")
    .options(**OPTIONS)
    .option("dbtable", os.getenv("OUTPUT_TABLE"))
    .mode("append")
    .save()
)

print(f"{len(resultado)} predições salvas")
print(resultado["label"].value_counts().to_dict())
```

Pontos do código:

`COLUNAS` reproduz a ordem exata das features do treino. O `ColumnTransformer` seleciona por nome, mas manter a ordem evita divergência silenciosa.

`predict_proba(X)[:, 1]` pega a probabilidade da classe positiva (Online). O `:` seleciona todas as linhas e o `1` a segunda coluna.

Não existe nenhum `StandardScaler` ou `OneHotEncoder` aqui. Está tudo dentro do PKL.

---

## Instalação das dependências no cluster

Célula 1, sozinha:

```
%pip install lightgbm==4.6.0 python-dotenv
```

Célula 2, sozinha:

```python
dbutils.library.restartPython()
```

Célula 3 em diante: o código.

O `%pip` consome a linha inteira. Se houver qualquer código na mesma célula, ele vira argumento do pip e o comando quebra. O `restartPython()` apaga todas as variáveis do notebook, então precisa vir antes de tudo.

---

## Armadilhas do Databricks Serverless

Três problemas encontrados na prática, todos específicos do compute serverless.

**`psycopg2` derruba o kernel.** O import da extensão C aborta o processo com `SIGABRT` (exit code 134), sem traceback Python. A solução é não usar driver Python de banco e sim o conector nativo do Spark.

**`.write.jdbc()` é bloqueado.** Retorna `UNSUPPORTED_DATA_SOURCE_WRITE`. O serverless só aceita fontes de dados de uma lista fechada, e o JDBC genérico não está nela.

**`.format("postgresql")` funciona.** É o caminho suportado, e não exige instalar nada. Vale tanto para leitura quanto para escrita.

```python
spark.read.format("postgresql").options(**OPTIONS).option("dbtable", tabela).load()
spark.createDataFrame(df).write.format("postgresql").options(**OPTIONS).option("dbtable", tabela).mode("append").save()
```

---

## Passo 5: Agendar o job para rodar todo dia

Até aqui o pipeline roda quando alguém clica. Deploy de verdade é quando ele roda sozinho.

### Pela interface

1. No menu lateral, **Jobs & Pipelines > Create > Job**
2. Nomeie o job, por exemplo `pipeline_shopping_preference`

**Task 1: geração dos dados**

| Campo | Valor |
|---|---|
| Task name | `gerar_dados` |
| Type | Notebook |
| Source | Workspace |
| Path | caminho do `generate_data` |
| Compute | Serverless |

**Task 2: inferência**

Clique em **Add task** e configure:

| Campo | Valor |
|---|---|
| Task name | `inferencia` |
| Type | Notebook |
| Path | caminho do `inference` |
| Compute | Serverless |
| Depends on | `gerar_dados` |

O `Depends on` é o que garante a ordem. Sem ele, as duas tasks rodam em paralelo e a inferência pode executar antes dos dados existirem.

**Dependências Python**

Na task de inferência, em **Dependent libraries > Add**, inclua `lightgbm==4.6.0` e `python-dotenv`. Assim o job não depende do `%pip install` no notebook.

**Agendamento**

No painel lateral, em **Schedules & Triggers > Add trigger**:

- Trigger type: `Scheduled`
- Schedule type: `Simple` para uma execução diária, ou `Advanced` para expressão cron
- Horário: por exemplo 06:00
- Timezone: `America/Sao_Paulo`

Em modo Advanced, a expressão para todo dia às 6h é:

```
0 0 6 * * ?
```

O cron do Databricks usa formato Quartz, com segundos no primeiro campo. Cron de Linux com 5 campos não funciona.

**Notificações**

Em **Notifications**, adicione um e-mail para `Failure`. Um job agendado que falha em silêncio é pior que job nenhum, porque a tabela de resultados fica desatualizada sem ninguém perceber.

### Pela CLI

Alternativa ao clique, útil para versionar o job junto com o código.

```json
{
  "name": "pipeline_shopping_preference",
  "tasks": [
    {
      "task_key": "gerar_dados",
      "notebook_task": {
        "notebook_path": "/Workspace/Users/SEU_EMAIL/Live_13_deploy/generate_data"
      }
    },
    {
      "task_key": "inferencia",
      "depends_on": [{ "task_key": "gerar_dados" }],
      "notebook_task": {
        "notebook_path": "/Workspace/Users/SEU_EMAIL/Live_13_deploy/inference"
      },
      "libraries": [
        { "pypi": { "package": "lightgbm==4.6.0" } },
        { "pypi": { "package": "python-dotenv" } }
      ]
    }
  ],
  "schedule": {
    "quartz_cron_expression": "0 0 6 * * ?",
    "timezone_id": "America/Sao_Paulo",
    "pause_status": "UNPAUSED"
  }
}
```

```bash
databricks jobs create --json @job.json
```

---

## Conferindo o resultado

```sql
SELECT label, COUNT(*) AS total
FROM shopping_preference_predictions
GROUP BY label;
```

```sql
SELECT p.customer_id, p.label, ROUND(p.probability_online::numeric, 4) AS prob,
       i.avg_store_spend, i.monthly_online_orders
FROM shopping_preference_predictions p
JOIN consumer_shopping_input i ON i.customer_id = p.customer_id
ORDER BY p.probability_online DESC
LIMIT 20;
```

---

## O conceito

Treinar um modelo e colocar um modelo em produção são problemas diferentes.

```
Antes:                    Depois:

Notebook                  Agendador
   |                         |
   v                         v
Modelo                    Pipeline
                             |
                             v
                          Modelo
                             |
                             v
                          Banco
```

No batch, o modelo não espera ninguém pedir. Ele roda por conta própria, no horário combinado, e deixa o resultado onde o negócio já sabe procurar.

---

# Deploy 2: API + Interface em Container (On Premise)

No Deploy 1 o modelo rodava sozinho, no horário marcado, sem ninguém pedir. Aqui é o oposto: o modelo fica de pé esperando, e responde quando alguém chama.

Toda a aplicação é empacotada em **uma imagem Docker** que roda em qualquer lugar: no seu notebook, num servidor da empresa, numa VM. É o que se chama de deploy on premise, quando a aplicação vive na infraestrutura da própria organização, e não numa nuvem pública.

Na aula ele roda na máquina local, mas o ponto é justamente esse: a imagem não sabe onde está. O que muda é apenas onde o `docker run` é executado.

## Por que on premise ainda importa

Não é só nostalgia. Existem casos em que a nuvem não é uma escolha:

- dado que não pode sair da rede da empresa por exigência regulatória
- ambiente sem conexão externa (chão de fábrica, unidade remota)
- custo previsível em cima de hardware que já foi comprado
- latência: o modelo precisa estar perto de quem consome

## Arquitetura

```
        Navegador
            |
            v
    STREAMLIT :8501
    formulário e interface
            |
            | POST /predict + JSON
            v
    FASTAPI :8000
    validação com Pydantic
            |
            v
    PANDAS DATAFRAME
            |
            v
    PIPELINE SCIKIT-LEARN
    TargetEncoder + LGBMClassifier
            |
            v
        Predição
            |
            v
    FASTAPI retorna JSON
            |
            v
    STREAMLIT exibe o resultado
```

Repare que o Streamlit **não** carrega o PKL. Ele conhece apenas o endereço da API. Essa separação é o coração do Deploy 2: amanhã um app mobile, um ERP ou uma planilha podem consumir a mesma API sem saber que existe um arquivo `.pkl` em algum lugar.

## Estrutura

```
deploy2_onpremise/
|
|-- app.py                            # API FastAPI
|-- streamlit_app.py                  # interface que consome a API
|-- shopping_preference_model.pkl     # modelo treinado
|-- requirements.txt                  # dependências Python
|-- Dockerfile                        # receita da imagem
`-- .dockerignore                     # o que não entra na imagem
```

---

## Passo 1: A API com FastAPI

O `app.py` transforma o modelo em serviço HTTP.

### 1.1 Imports e criação da aplicação

```python
import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Shopping Preference API", version="1.0.0")

modelo = joblib.load("shopping_preference_model.pkl")
```

O `joblib.load` fica no **escopo do módulo**, fora de qualquer função. Isso é proposital: o modelo é carregado uma vez, quando a aplicação sobe, e fica residente em memória. Carregar o PKL dentro do endpoint significaria ler 900 KB do disco a cada requisição. É o erro de deploy mais comum e o mais fácil de evitar.

O `title` e a `version` alimentam a documentação automática que o FastAPI gera em `/docs`.

### 1.2 O contrato de entrada

```python
class Cliente(BaseModel):
    age: int
    monthly_income: int
    daily_internet_hours: float
    smartphone_usage_years: int
    social_media_hours: float
    online_payment_trust_score: int
    tech_savvy_score: int
    monthly_online_orders: int
    monthly_store_visits: int
    avg_online_spend: int
    avg_store_spend: int
    discount_sensitivity: int
    return_frequency: int
    avg_delivery_days: int
    delivery_fee_sensitivity: int
    free_return_importance: int
    product_availability_online: int
    impulse_buying_score: int
    need_touch_feel_score: int
    brand_loyalty_score: int
    environmental_awareness: int
    time_pressure_level: int
    gender: str
    city_tier: str
```

Essa classe é o **contrato** entre quem chama e a API. O Pydantic valida cada requisição contra ele automaticamente. Se faltar um campo ou vier texto onde deveria vir número, a API devolve HTTP 422 com a explicação, e o modelo nunca chega a ser chamado.

Sem isso, um payload malformado só quebraria lá dentro do Scikit-learn, com uma mensagem que ninguém entende.

São as mesmas 24 features do treino, com os mesmos nomes. Nome de coluna diferente do treino quebra o `ColumnTransformer`.

### 1.3 Health check

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

Um endpoint bobo, de duas linhas, que responde uma pergunta essencial: a aplicação está viva?

Não é enfeite. Orquestradores (Docker, Kubernetes, Azure, Render) usam esse endereço para decidir se o container está saudável e se deve receber tráfego. E, na prática da aula, é o que separa "a API está no ar" de "a interface está no ar".

### 1.4 O endpoint de predição

```python
@app.post("/predict")
def predict(cliente: Cliente):
    df = pd.DataFrame([cliente.model_dump()])

    prediction = int(modelo.predict(df)[0])
    probability = float(modelo.predict_proba(df)[0][1])

    return {
        "prediction": prediction,
        "label": "Online" if prediction == 1 else "Store",
        "probability_online": probability,
    }
```

Linha a linha:

`cliente: Cliente` faz o FastAPI validar o JSON recebido antes de executar o corpo da função.

`cliente.model_dump()` converte o objeto Pydantic em dicionário Python.

`pd.DataFrame([...])` envolve o dicionário em lista para virar uma linha de tabela. O Scikit-learn espera dados tabulares, não um dicionário solto.

`modelo.predict(df)[0]` roda o pipeline inteiro, encoding incluído, e pega a primeira (única) predição.

`modelo.predict_proba(df)[0][1]` pega a probabilidade da classe positiva. O `[0]` é a primeira linha, o `[1]` é a segunda coluna, que corresponde a Online.

`int()` e `float()` convertem tipos do NumPy para tipos nativos do Python. Sem isso, o FastAPI não consegue serializar a resposta em JSON.

Note o que **não** está aqui: nenhum `StandardScaler`, nenhum `OneHotEncoder`, nenhum tratamento de categoria. Está tudo dentro do PKL.

### 1.5 Testando só a API

```powershell
uvicorn app:app --reload
```

O primeiro `app` é o arquivo `app.py`. O segundo é a variável `app = FastAPI(...)`. O `--reload` reinicia o servidor a cada alteração no código, útil em desenvolvimento e desnecessário em produção.

Abra `http://127.0.0.1:8000/docs`. O FastAPI gera o Swagger sozinho, a partir da classe `Cliente`. Dá para testar o `POST /predict` ali mesmo, antes de existir qualquer interface.

---

## Passo 2: A interface com Streamlit

O `streamlit_app.py` é uma aplicação **cliente**. Ela não sabe nada sobre Machine Learning, apenas preenche um JSON e faz um POST.

### 2.1 Endereço da API

```python
import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000") + "/predict"
```

O endereço vem de variável de ambiente, com o local como padrão. Isso é o que permite a mesma imagem rodar sem alteração na máquina local e depois em qualquer outro lugar, apontando para outra API. Endereço fixo no código é o que obriga a reconstruir a imagem a cada mudança de ambiente.

### 2.2 Layout e widgets

```python
st.set_page_config(page_title="Shopping Preference", layout="wide")
st.title("Shopping Preference")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Perfil")
    age = st.number_input("Idade", 18, 79, 45)
    gender = st.selectbox("Gênero", ["Female", "Male", "Other"])
    daily_internet_hours = st.slider("Horas de internet por dia", 1.0, 12.0, 6.0)
```

São 24 campos, divididos em três colunas para caber na tela: Perfil, Consumo e Preferências.

Repare nos limites dos widgets. Eles não são arbitrários: são os valores mínimo e máximo vistos na base de treino. `age` vai de 18 a 79, `avg_store_spend` de 542 a 149972, e assim por diante.

Isso é uma decisão de projeto. O LightGBM extrapola sem reclamar: se você mandar idade 200, ele devolve uma predição com toda a confiança do mundo, e essa predição não tem lastro nenhum. Travar a faixa na interface impede o usuário de sair do domínio onde o modelo realmente aprendeu.

O `selectbox` faz o mesmo com as categóricas. O `TargetEncoder` aceita categoria desconhecida em silêncio, aplicando a média global do target, então restringir às três opções conhecidas evita uma predição sem sentido.

### 2.3 Montando o payload

```python
if st.button("Realizar previsão", type="primary"):
    payload = {
        "age": age,
        "monthly_income": monthly_income,
        # ... os 24 campos
        "gender": gender,
        "city_tier": city_tier,
    }
```

As chaves do payload precisam bater **exatamente** com os campos da classe `Cliente` na API. Um nome divergente aqui produz um 422, e o erro só aparece em tempo de execução.

### 2.4 A chamada HTTP

```python
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
        resultado = response.json()
```

`json=payload` serializa o dicionário e já ajusta o cabeçalho `Content-Type`.

`timeout=30` impede a interface de ficar pendurada para sempre se a API não responder. Sem timeout, uma API travada trava a interface junto.

`raise_for_status()` transforma respostas de erro (4xx, 5xx) em exceção Python, para cair no `except`.

### 2.5 Exibindo o resultado

```python
        if resultado["label"] == "Online":
            st.success("Cliente com perfil de compra Online")
        else:
            st.info("Cliente com perfil de compra em Loja física")

        st.metric("Probabilidade de compra online", f"{resultado['probability_online']:.2%}")
        st.json(resultado)
```

Aqui a saída técnica vira informação legível. O formato `:.2%` transforma `0.8235` em `82.35%`.

O `st.json` mostra a resposta bruta da API. Numa demonstração isso vale muito: deixa visível que existe um serviço HTTP do outro lado, e não uma função Python escondida.

### 2.6 Tratamento de erro

```python
    except requests.exceptions.ConnectionError:
        st.error("Não foi possível conectar na API. Verifique se o FastAPI está rodando.")
    except requests.exceptions.RequestException as erro:
        st.error(f"Erro ao consultar a API: {erro}")
```

Duas camadas: falha de conexão (API desligada) e qualquer outro erro de comunicação.

Sem isso, a interface simplesmente quebraria com um traceback na tela. Numa aplicação distribuída, a rede falhar não é exceção, é rotina.

### 2.7 Testando os dois juntos, ainda sem Docker

Terminal 1:

```powershell
uvicorn app:app --reload
```

Terminal 2:

```powershell
streamlit run streamlit_app.py
```

Dois terminais, dois processos, duas portas. Funciona, e é justamente o incômodo que o Docker vai resolver.

---

## Passo 3: requirements.txt

```
# núcleo do modelo (versões do treino)
numpy==2.2.6
pandas==2.2.3
scikit-learn==1.7.1
lightgbm==4.6.0
joblib==1.5.1

# API
fastapi~=0.115
uvicorn[standard]~=0.30
pydantic~=2.10

# interface
streamlit~=1.40
requests~=2.32
```

As cinco primeiras estão **pinadas em versão exata**, e são exatamente as do ambiente de treino. É o grupo que toca no PKL: se qualquer uma divergir, o `joblib.load` pode disparar `InconsistentVersionWarning` ou falhar na desserialização.

Esse é um contraste interessante com o Deploy 1. No Databricks o runtime é fixo e você convive com a divergência. Aqui você controla a imagem inteira, então dá para reproduzir o ambiente de treino ao pé da letra. É uma das grandes vantagens do container em deploy de ML.

As demais usam `~=`, que aceita correções de patch mas trava a subida de versão minor. Nelas não existe risco de pickle, então pinar exato só criaria trabalho de manutenção.

---

## Passo 4: O Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py streamlit_app.py shopping_preference_model.pkl ./

EXPOSE 8000 8501

CMD uvicorn app:app --host 0.0.0.0 --port 8000 & \
    streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

Linha por linha:

**`FROM python:3.10-slim`** define a imagem base. O 3.10 não é escolha aleatória: é a versão do Python em que o modelo foi treinado. O `slim` é uma variante enxuta, bem menor que a completa.

**`ENV PYTHONUNBUFFERED=1`** desliga o buffer do stdout. Sem isso, `print` e traceback ficam presos no buffer e aparecem atrasados nos logs do container, ou não aparecem. Em container, log é a única janela para dentro.

**`RUN apt-get install libgomp1`** instala o runtime do OpenMP, que o LightGBM usa para paralelizar. A imagem `slim` não traz.

Vale parar aqui na aula. Essa linha é a que ensina por que Docker existe. O `requirements.txt` estava completo e correto, todas as dependências Python instaladas, e mesmo assim a aplicação quebrava com:

```
OSError: libgomp.so.1: cannot open shared object file
```

Porque a dependência que faltava não era do Python, era do **sistema operacional**. Num deploy direto em servidor, você descobriria isso do mesmo jeito, só que em produção e sem saber onde procurar. A imagem congela o sistema operacional junto com o código.

**A ordem dos `COPY`** é otimização de cache. O `requirements.txt` é copiado e instalado antes do código da aplicação, porque o Docker reaproveita camadas que não mudaram. Assim, alterar o `app.py` não refaz a instalação das dependências, que é a parte lenta.

**`COPY app.py streamlit_app.py shopping_preference_model.pkl ./`** copia apenas o necessário. O PKL entra na imagem, ele é o artefato do deploy.

**`EXPOSE 8000 8501`** é documentação. Não abre porta nenhuma sozinho, só declara a intenção. Quem publica de fato é o `-p` do `docker run`.

**O `CMD`** sobe os dois processos: `uvicorn` em segundo plano com `&` e `streamlit` em primeiro plano.

Aqui vale a honestidade técnica: **isso é uma simplificação didática.** O `&` mantém o container vivo enquanto o Streamlit estiver de pé, mesmo que a API tenha morrido. Foi exatamente o que aconteceu quando faltava o `libgomp1`: a interface subiu bonita, o container ficou "no ar", e o botão de previsão dava erro de conexão, porque a API nunca existiu.

Em produção séria isso vira dois containers separados, ou um supervisor de processos como o `supervisord`. Para uma aula, um container só deixa a demonstração mais direta.

### .dockerignore

```
.venv
__pycache__
.env
*.ipynb
```

Impede que ambiente virtual, cache e credenciais entrem na imagem. O `.env` nessa lista não é detalhe: imagem Docker circula, e credencial dentro dela circula junto.

---

## Passo 5: Build e execução

```powershell
docker build -t shopping-preference .
```

O `-t` nomeia a imagem e o `.` indica que o contexto de build é a pasta atual.

```powershell
docker run --rm -p 8000:8000 -p 8501:8501 shopping-preference
```

O `-p host:container` publica as portas. O `--rm` remove o container quando ele encerra, evitando acúmulo de containers parados a cada teste.

Confirme que a API subiu **antes** de abrir a interface:

```powershell
curl http://localhost:8000/health
```

Resposta esperada: `{"status":"ok"}`. Se vier isso, o modelo carregou.

| Serviço | Endereço |
|---|---|
| API (Swagger) | http://localhost:8000/docs |
| Interface | http://localhost:8501 |

### Se a porta estiver ocupada

```
Bind for 0.0.0.0:8000 failed: port is already allocated
```

Significa que outro container já está usando a porta. Verifique e derrube:

```powershell
docker ps
docker stop ID_DO_CONTAINER
```

Ou simplesmente publique em outra porta do host:

```powershell
docker run --rm -p 8010:8000 -p 8511:8501 shopping-preference
```

O lado do container não muda, então o Streamlit continua falando com a API em `127.0.0.1:8000` normalmente.

No PowerShell, o atalho `docker stop $(docker ps -q)` do bash não funciona. O equivalente é:

```powershell
docker ps -q | ForEach-Object { docker stop $_ }
```

---

## Do notebook ao servidor

O argumento que fecha o Deploy 2: essa mesma imagem, sem uma linha alterada, roda em qualquer um destes lugares.

```
   docker run
        |
        +-- notebook do desenvolvedor
        +-- servidor da empresa
        +-- VM (Azure, AWS, GCP)
        +-- Kubernetes
        `-- nuvem gerenciada (Container Apps, Cloud Run)
```

O que muda é **onde** o comando é executado, não o artefato. É por isso que container virou o formato padrão de entrega de software, e é o contraste direto com o Deploy 1, onde o código estava amarrado ao Databricks e não rodava em outro lugar.

O que muda ao sair da máquina local:

- **uma porta só fica exposta** na maioria dos serviços gerenciados, então o Streamlit fica público e a API interna
- **escalar exige separar os containers**, porque duas réplicas de um container com dois processos significam duas APIs e dois Streamlits
- **o health check passa a ser levado a sério** pela plataforma, e o problema do `&` deixa de ser teórico

---

## Passo 6: A mesma imagem na nuvem (Render)

Até aqui a aplicação roda na máquina local. O argumento da seção anterior era que a imagem não sabe onde está. Agora vamos provar isso na prática: a mesma imagem, com um ajuste de uma linha, ganha uma URL pública.

Aplicação no ar: **https://deploy2-onpremise.onrender.com**

### 6.1 O ajuste: porta variável

Serviços gerenciados (Render, Cloud Run, Container Apps) não deixam você escolher a porta. Eles atribuem uma e informam por variável de ambiente. Por isso a porta do Streamlit deixa de ser fixa:

```dockerfile
ENV PYTHONUNBUFFERED=1 PORT=8501
```

```dockerfile
CMD uvicorn app:app --host 0.0.0.0 --port 8000 & \
    streamlit run streamlit_app.py --server.port ${PORT} --server.address 0.0.0.0 --server.headless true
```

O `ENV PORT=8501` é o valor padrão, usado quando ninguém define nada. Ou seja, na sua máquina o comportamento é exatamente o mesmo de antes. Na nuvem, a plataforma sobrescreve.

Esse é o padrão que vale para qualquer lugar: **nunca fixe porta ou endereço no código**. Leia do ambiente, com um padrão sensato para desenvolvimento. É a mesma lógica do `API_URL` no `streamlit_app.py`.

Para conferir que a variável funciona antes de subir:

```powershell
docker run --rm -p 9000:9000 -e PORT=9000 shopping-preference
```

Se a interface abrir em `localhost:9000`, o comportamento na nuvem será o mesmo.

### 6.2 O código no GitHub

O Render constrói a imagem a partir de um repositório Git. Ele não aceita upload de imagem pronta no plano free.

```powershell
git init
git add .
git commit -m "deploy inicial"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPO.git
git push -u origin main
```

O `.pkl` tem cerca de 900 KB e passa no GitHub sem Git LFS.

### 6.3 Criando o Web Service

No dashboard do Render: **New > Web Service**, conecta o GitHub e escolhe o repositório.

| Campo | Valor |
|---|---|
| Language | Docker |
| Branch | `main` |
| Region | Oregon |
| Instance Type | Free |

Build Command e Start Command ficam **em branco**. Com Docker, quem manda é o Dockerfile.

O build começa sozinho ao criar o serviço, e os logs aparecem na tela. Quando surgir `Your service is live`, a URL no topo da página é pública.

Todo `git push` na branch `main` dispara um novo deploy automaticamente.

### 6.4 O que muda ao sair da máquina

**Só uma porta fica exposta.** O Render publica apenas a `$PORT`. Como a API escuta na 8000 interna, o `/docs` deixa de ser acessível de fora. A interface funciona normalmente, porque a conversa entre Streamlit e API acontece dentro do container. Para deixar o Swagger público, seria preciso um segundo serviço só com a API.

**A aplicação hiberna.** No plano free, o serviço dorme após cerca de 15 minutos sem acesso e leva 50 segundos ou mais para acordar. Numa demonstração ao vivo isso é fatal: abra a URL alguns minutos antes de começar.

**Memória é limitada.** São 512 MB no free, e pandas, scikit-learn e lightgbm carregados ocupam boa parte disso.

### 6.5 Sobre o Hugging Face Spaces

O Hugging Face Spaces era a alternativa mais simples para publicar container, sem cartão de crédito e sem CLI. Em julho de 2026 isso mudou: **apenas Spaces estáticos continuam gratuitos**. Os SDKs Docker e Gradio passaram a exigir plano pago, PRO para contas pessoais.

Fica o registro porque é um bom exemplo de algo que todo material sobre deploy precisa encarar: a plataforma muda, e o tutorial de ontem não roda hoje. O que não muda é a imagem Docker. Ela continua a mesma para Render, Cloud Run, Container Apps ou um servidor da empresa.

---

## O conceito do Deploy 2

Treinar um modelo e servir um modelo são problemas diferentes.

```
Antes:                Depois:

Notebook              Usuário
   |                     |
   v                     v
Modelo               Aplicação
                        |
                        v
                       API
                        |
                        v
                     Modelo
```

O modelo deixa de ser um arquivo que alguém abre num notebook e vira um serviço com endereço, contrato e disponibilidade. Qualquer sistema que fale HTTP passa a poder consumi-lo, sem conhecer Python, Scikit-learn ou a existência do arquivo `.pkl`.

E a mesma imagem que roda no seu notebook rodou na nuvem sem alteração de código. Essa é a promessa do container, e ela se cumpriu com uma variável de ambiente de diferença.

---

# Deploy 3: Serverless (Azure Functions)

Nos deploys 1 e 2, alguma coisa estava sempre ligada: o cluster no horário do job, o container esperando requisição. No serverless não existe processo em espera. A função só existe quando alguém chama, e o custo acompanha isso.

Aqui a API vai para o Azure Functions e a interface Streamlit continua rodando na máquina local, apontando para a API na nuvem. Essa separação é proposital: mostra que o cliente e o serviço não precisam morar no mesmo lugar.

## O que muda em relação ao Deploy 2

| | Deploy 2 (container) | Deploy 3 (serverless) |
|---|---|---|
| Processo | sempre de pé, esperando | só existe durante a chamada |
| Você gerencia | a imagem inteira, incluindo o SO | apenas o código |
| Custo parado | paga a instância ligada | praticamente zero |
| Primeira chamada | imediata | lenta (cold start) |
| Controle do ambiente | total (Dockerfile) | limitado ao runtime oferecido |

A troca é direta: você abre mão de controle e ganha simplicidade e custo. E paga em latência na primeira requisição.

## Arquitetura

```
    Máquina local                      Azure
    -------------                      -----
      STREAMLIT                    AZURE FUNCTION
      interface                    FastAPI + modelo
          |                              ^
          |    POST /predict + JSON      |
          +------------- HTTPS ----------+
```

O Streamlit não sabe que do outro lado existe uma função serverless. Para ele é apenas uma URL. É a mesma propriedade que fez a interface funcionar sem alteração no Deploy 2: o cliente conhece o endereço, não a implementação.

## Estrutura

```
deploy3_azure/
|
|-- function_app.py                   # a API, agora como Azure Function
|-- host.json                         # configuração do runtime
|-- requirements.txt                  # dependências
|-- local.settings.json               # configuração local (não sobe)
|-- .funcignore                       # o que não vai para a nuvem
|-- shopping_preference_model.pkl     # modelo treinado
`-- streamlit_app.py                  # interface local
```

Não existe Dockerfile. O runtime é gerenciado pela Microsoft, e essa é justamente a diferença.

---

## Passo 1: A API como Azure Function

A boa notícia é que **quase nada do FastAPI muda**. O pacote `azure-functions` oferece o `AsgiFunctionApp`, que envolve uma aplicação ASGI e a serve como Function.

```python
# function_app.py

import azure.functions as func
import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

fast_app = FastAPI(title="Shopping Preference API", version="1.0.0")

modelo = joblib.load("shopping_preference_model.pkl")
```

Duas diferenças em relação ao `app.py` do Deploy 2:

O `import azure.functions as func` é novo.

A variável do FastAPI passou a se chamar `fast_app`. O nome `app` fica reservado para a Function em si, que é o que o runtime da Azure procura no arquivo.

O `joblib.load` continua no escopo do módulo, e aqui isso importa ainda mais. Em serverless, o código de inicialização roda uma vez por instância, não uma vez por requisição. Carregar o PKL dentro da função significaria pagar o carregamento a cada chamada.

A classe `Cliente` e os endpoints `/health` e `/predict` são **idênticos** ao Deploy 2. O que muda é só a última linha do arquivo:

```python
app = func.AsgiFunctionApp(app=fast_app, http_auth_level=func.AuthLevel.ANONYMOUS)
```

`AsgiFunctionApp` faz a ponte entre o protocolo ASGI (que o FastAPI fala) e o modelo de execução do Azure Functions.

`http_auth_level=ANONYMOUS` permite chamar a API sem chave. O padrão é `FUNCTION`, que exigiria um `?code=...` em toda requisição. Para uma demonstração pública, anônimo. Numa API real com dado sensível, o padrão é o certo.

### host.json

```json
{
  "version": "2.0",
  "extensions": {
    "http": {
      "routePrefix": ""
    }
  }
}
```

O `routePrefix` vazio é um detalhe que vale explicar. Por padrão, o Azure Functions prefixa toda rota HTTP com `/api`, e os endpoints virariam `/api/predict` e `/api/health`. Zerando o prefixo, as rotas ficam iguais às do Deploy 2, e o `streamlit_app.py` funciona sem nenhuma alteração apontando para qualquer um dos dois.

### requirements.txt

```
azure-functions

numpy==2.2.6
pandas==2.2.3
scikit-learn==1.7.1
lightgbm==4.6.0
joblib==1.5.1

fastapi~=0.115
pydantic~=2.10
```

O `azure-functions` entra. O `uvicorn` sai: quem serve HTTP agora é o runtime da Azure, não um servidor ASGI seu. O `streamlit` e o `requests` também saem, porque a interface roda na sua máquina, fora da Function.

As cinco versões pinadas continuam iguais. Elas acompanham o PKL, não a plataforma.

### local.settings.json

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python"
  }
}
```

Configuração apenas local, listada no `.funcignore` para nunca subir. Em produção, essas configurações vivem em Application Settings, no portal.

---

## Passo 2: Rodando local

O Azure Functions Core Tools roda o mesmo runtime da nuvem na sua máquina.

```powershell
winget install Microsoft.Azure.FunctionsCoreTools
```

```powershell
cd deploy3_azure

py -3.10 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

func start
```

A API sobe em `http://localhost:7071`. Repare na porta: não é a 8000 do uvicorn, é a porta padrão das Core Tools.

```powershell
curl http://localhost:7071/health
```

Testar local antes de publicar não é preciosismo. Deploy na nuvem leva minutos e o log é mais difícil de ler; erro de sintaxe ou dependência faltando é muito mais barato de descobrir aqui.

---

## Passo 3: Criando a Function App no portal

**Create a resource** ⭢ **Function App** ⭢ Create.

Na primeira tela, escolha **Consumption**. É o plano serverless clássico, o que escala a zero e cobra por execução. É ele que produz o cold start, e o cold start é o assunto desta aula.

| Campo | Valor |
|---|---|
| Resource Group | `rg-live-deploy` |
| Function App name | nome único global, vira a URL |
| Runtime stack | Python |
| Version | **3.10** |
| Region | Brazil South |
| Operating System | Linux |

O Python 3.10 não é detalhe: é a versão em que o modelo foi treinado. Aqui você não controla o sistema operacional como no Dockerfile, mas ainda escolhe a versão do runtime.

O provisionamento leva alguns minutos. Se aparecer `StorageAccountOperationInProgress`, é operação concorrente na storage account, e resolve sozinho esperando um pouco. Vale notar o contraste: provisionamento em nuvem é assíncrono, diferente do `docker run`, que funciona ou falha na hora.

---

## Passo 4: Publicando pelo VS Code

Instale a extensão **Azure Functions**, da Microsoft.

1. Ícone da Azure na barra lateral ⭢ **Sign in to Azure**
2. Abra a pasta `deploy3_azure`
3. `Ctrl+Shift+P` ⭢ **Azure Functions: Deploy to Function App**
4. Escolha a assinatura e a Function App criada
5. Confirme a sobrescrita

Se ele perguntar sobre **remote build**, aceite. Sem isso, o VS Code empacota as dependências instaladas no seu Windows, e `lightgbm` e `scikit-learn` têm binários específicos de sistema operacional que não funcionam no Linux da Azure.

---

## Passo 5: Testando na nuvem

A URL fica no Overview da Function App, campo **Default domain**. O formato atual inclui um sufixo aleatório e a região:

```
https://SEU-APP-xxxxxxxx.brazilsouth-01.azurewebsites.net
```

URL de nuvem não é adivinhável. Sempre copie do portal.

**Verificar se está viva:**

```powershell
Invoke-RestMethod https://SUA_URL/health
```

**Verificar se o modelo carregou:**

O `/health` responde mesmo que o `joblib.load` tenha falhado, então abra o Swagger e faça uma previsão de verdade:

```
https://SUA_URL/docs
```

**A interface local consumindo a nuvem:**

```powershell
$env:API_URL = "https://SUA_URL"
streamlit run streamlit_app.py
```

Esse é o momento da aula: a interface roda na sua máquina, o modelo roda na Azure, e **nenhuma linha do `streamlit_app.py` mudou**. Só a variável de ambiente.

É a terceira vez que essa propriedade aparece no projeto: o `API_URL` no Deploy 2, a `$PORT` no Render, e agora aqui. Configuração no ambiente, não no código.

---

## Cold start: o preço do serverless

Faça este teste ao vivo, cronometrando.

**Primeira chamada** depois de um tempo parado: leva vários segundos. A Azure precisa alocar uma instância, iniciar o Python, importar pandas, scikit-learn e lightgbm, e desserializar o PKL.

**Segunda chamada**, logo em seguida: praticamente instantânea. A instância já está de pé e o modelo já está em memória.

Depois de alguns minutos sem tráfego, a instância é desligada e o ciclo recomeça.

Esse é o custo real do serverless, e ele é maior em Machine Learning do que em uma API comum, porque as bibliotecas são pesadas e o modelo precisa ser carregado.

Quando serverless compensa:

- tráfego irregular ou imprevisível
- volume baixo, onde manter um container ligado sairia mais caro que as execuções
- picos ocasionais, deixando a plataforma escalar sozinha

Quando não compensa:

- latência importa na primeira chamada
- tráfego constante, onde a instância nunca chega a dormir e você paga o mesmo sem o controle do container
- modelos grandes, cujo carregamento domina o tempo de resposta

---

## O conceito do Deploy 3

```
Deploy 1          Deploy 2           Deploy 3
--------          --------           --------
Cluster           Container          Função
agendado          sempre ligado      sob demanda
   |                  |                  |
roda no           responde           existe apenas
horário           sempre             durante a chamada
```

A mesma pergunta, três respostas diferentes: **quando o modelo precisa estar disponível?**

Se a resposta é "uma vez por dia", batch. Se é "sempre, com latência previsível", container. Se é "quando alguém chamar, e isso é raro", serverless.

Nenhuma das três é a resposta certa. A escolha vem do padrão de uso, do orçamento e do quanto de infraestrutura a equipe quer administrar.

---

# Fechamento

Um modelo. Três deploys. Nenhuma linha do modelo alterada.

| | Deploy 1 | Deploy 2 | Deploy 3 |
|---|---|---|---|
| Formato | Batch | API + interface | Função serverless |
| Plataforma | Databricks | Docker (local e Render) | Azure Functions |
| Disparo | Agendador | Requisição HTTP | Requisição HTTP |
| Estado | Cluster sob demanda | Processo sempre ligado | Sem processo em espera |
| Você gerencia | O notebook | A imagem inteira | Apenas o código |

O que se repetiu nos três:

**O PKL é o artefato.** Ele viajou intacto por Databricks, container e serverless. Treinar acontece uma vez; servir acontece de muitas formas.

**Versão de biblioteca é o inimigo silencioso.** O erro aparece no `joblib.load`, sempre longe de onde foi causado.

**Configuração vem do ambiente.** `API_URL`, `$PORT`, credenciais de banco. Endereço fixo no código obriga a reconstruir tudo a cada mudança de ambiente.

**O que quebra o deploy raramente é o modelo.** Foi biblioteca de sistema faltando, porta ocupada, permissão de usuário, política de repositório, versão de Python. O modelo funcionou desde o primeiro teste.

Treinar um modelo e colocar um modelo em produção são problemas diferentes.
