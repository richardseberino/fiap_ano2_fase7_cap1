# Como importar o assistente no IBM Watson Assistant / watsonx Assistant

Neste diretório você tem o arquivo com as definções de skilss do nossos assistente compatível com o Watsonx Assistent V2, porém na versão classica (a nova é baseada em inteções e ações). 

Esta estapa é opcional dado que o assistente possui uma versão off line que não depende de serviços externos. Caso queria experimentar o assistente integrado ao Watsonx Assistent da IBM siga os passos abaixo:

## 1.0 Conta na IBM Cloud

Você vai precisar de uma conta na IBM Cloud para instanciar uma cópia do serviço. Mas não se preocupe, apesar de pedir cartão de crédito no cadastro o serviços que vamos usar para este estudo é gratuíto;

Entre na URL abaixo e siga os passos para o seu cadastro:
<a href="https://cloud.ibm.com" > IBM Cloud </a>

## 2.0 Cria uma instancia do Serviço Watsonx Assistent

Depois de autenticado siga os passos abaixo para criar nossa instancia do assitente.

### 2.1 - Criando o serviço

a) Pesquise na barra superior o serviço pelo nome "Watsonx Assistent" e clique na primeira opção como na imagem a seguir.

<img src="./assets/ibm-cloud1.png" alt="Pesquida pelo Assistente" width="700"> 

b) Nesta tela teremos algumas ações para fazer:
- Selecione a região, escolhi a de Dallas por ser a mais perto do Brasil, o serviço não esta (pelo menos na minha conta tryal) disponível na região do Brasil. 
- Deixe marcado a opção "Lite" que é a versão gratuíta do serviço que nos dará todos os recursos necessários para este teste.
- Marque a caixa "I have read angree to the following license aggrements:
- Confirme a operação clicando no botão "Create"

<img src="./assets/ibm-cloud2.png" alt="Selecionando região e plano" width="700"> 

### 2.2 - Configurando o agente

a) Nesta tela que abrir copie o "API Key" e guarde em algum lugar para uso mais pra frente

<img src="./assets/ibm-cloud3.png" alt="Copiando a API Key" width="500"> 

b) Troca para a interface Classica, clicando no ícone do seu perfil no canto superior direto, e indo na opção "sitch to classic expience"

<img src="./assets/ibm-cloud4.png" alt="Alternando para a visão classica" width="200"> 

### 2.3 - Criando nosso agente

a) Nesta etapa clique no Botão "Create Assistant" para criar nosso assistant

<img src="./assets/ibm-cloud5.png" alt="Inciando o wizzard para criação de novo assistente" width="300"> 

b) De um nome amigável para o seu assistente e confirme no botão "Create Assistant"

<img src="./assets/ibm-cloud6.png" alt="Definindo o nome" width="500"> 

### 2.4 - Importando os skilss e dialogo

a) Agora com o assistente criado precisamos importar as skilss. Clique na opção "Add dialog Skill"

<img src="./assets/ibm-cloud7.png" alt="Configurando os dialogs e Skills" width="500"> 

b) Siga as etapas abaixo para fazer a importação: 
- Clique na terceira aba "Upload skill"
- arraste para a área indicada o arquivo skill-assistente-cardiologico.json
- clique no botão "Upload"

<img src="./assets/ibm-cloud8.png" alt="Importando configurações" width="500"> 

### 2.5 - Testando nosso agente

a) Ainda na própria interface do Watsonx, clique no botão "Preview"

<img src="./assets/ibm-cloud9.png" alt="Testando nosso agente" width="500"> 

b) Faça algumas perguntas, como dor no peito, e seja guiado pelo fluxo. 

<img src="./assets/ibm-cloud10.png" alt="Navegando pelo agente" width="500"> 

### 2.6 - COnfigurando o App para usar o Watsonx

a) Clique na aba lateral escolhendo o item "Assistentes", selecione os três pontos ao final da caixa com o nosso assistente e escolha a opção "Settings"

<img src="./assets/ibm-cloud11.png" alt="Recuperando dados da nossa instancia" width="700"> 

b) Copie os valores de "Assistant ID" e do "Assisant URL" que vamos usar mais pra frente

<img src="./assets/ibm-cloud12.png" alt="Recuperando dados da nossa instancia" width="700"> 

### 2.7 - Edidanto arquivo de configurações de ambiente do projeto

a) Abra com seu editor favorito o arquivo .env que esta na  raíz do projeto e coloque os dados conforme abaixo (caso o arquivo não existir renomeie o arquivo .env.example para o nomne .env):

- Variável USE_WATSON=true
- Variável WATSON_APIKEY=<valor que voce copiou na etapa 2.2 a)>
- Variável WATSON_URL=<valor copiado na etapa 2.6 b), remova o final da URL mantendo só a base do servidor>

b) Confira se seu arquivo esta similar ao exemplo abaixo

<img src="./assets/ibm-cloud13.png" alt="Verificando o arquivo de configuração" width="700"> 

PS: Não use as configurações do Watson printadas aqui, ela não estará funcional quando voce seguir esse tutoria. Use as suas próprias. 

### 3.0 Testando a solução

a) Agora com tudo criado e configurado, inicie a aplicação normalmente com o commando abaixo, e você já perceber que o motor vem marcado como Watson

```
python run.py
```

b) Abra seu navegador na URL <a href="http://localhost:5000">Assistente de Cardiológia</a>

* note que o motor já vem marcado como "Watson"

<img src="./assets/assistente1.png" alt="Abrindo o assistente" width="400"> 

c) Interaja, com ele, faça perguntas e siga o fluxo

<img src="./assets/assistente2.png" alt="Testando o assistente" width="400"> 

