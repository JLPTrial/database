# Módulo do Banco de Dados

Este módulo foi feito para separar as atualizações do aplicativo da WEB e do banco de dados que este irá utilizar.

Aqui você encontrará as configurações e a base de questões do banco de dados SQLite que você poderá modificar facilmente caso precise/queira.

## Estrutura

- `data/` - Modelos de questões em JSON
- `schemas/` - Definição das tabelas
- `scripts/` - Conversão dos JSON para bancos de dados SQLite
- `outputs/` - Bancos de dados gerados em cada nível (criado na execução do script)

## Como usar este banco de dados no App

Antes do processo de Build do app, ele próprio se encarregará de construir o banco de dados no processo, e em seguida, copiar os dados necessários para `app/src/database`, estes que serão aproveitados durante a build, e permanecerão nesta pasta.

## Como usar este banco de dados no Servidor/WEB

Para o caso do servidor, no momento em que este for ir ao ar usando dos comandos do `devbox`, o próprio script de inicialização cuidará de iniciar os bancos de dados necessários e em seguida, copiá-los para a pasta `data/` dentro do servidor.