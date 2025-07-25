Equipe:

Bruno Rodrigues;
Filipe de Oliveira;
Kátia Acioli;
Neusa Angélica Goiana


# Chat Redis - Sistema de Chat em Tempo Real

Um sistema de chat em tempo real usando Python, Redis Streams e Textual para a interface de usuário.

## Funcionalidades

- ✅ **Múltiplos canais**: Suporte a vários canais de chat
- ✅ **Tempo real**: Mensagens aparecem instantaneamente
- ✅ **Histórico**: Mensagens são persistidas no Redis
- ✅ **Interface amigável**: Interface baseada em terminal usando Textual
- ✅ **Criação dinâmica**: Crie novos canais em tempo real

## Pré-requisitos

- Python 3.12+
- Docker e Docker Compose (para Redis)
- UV (gerenciador de pacotes Python)

## Instalação e Configuração

### 1. Instalar dependências

```bash
uv sync
```

### 2. Iniciar o Redis

```bash
docker compose up -d
```

### 3. Executar o chat

```bash
uv run python main.py
```

## Como usar

### Interface

O chat possui duas áreas principais:

1. **Sidebar (esquerda)**:
   - Lista de canais disponíveis
   - Campo para criar novos canais
   - Campo para definir seu nome de usuário

2. **Área principal (direita)**:
   - Histórico de mensagens do canal selecionado
   - Campo de entrada para digitar mensagens

### Controles

- **Selecionar canal**: Clique em um canal na lista lateral
- **Criar canal**: Digite o nome e clique em "Criar Canal"
- **Enviar mensagem**: Digite a mensagem e pressione Enter ou clique "Enviar"
- **Atualizar canais**: Pressione `r`
- **Sair**: Pressione `q`

### Canais padrão

O sistema vem com dois canais pré-criados:
- `geral` - Para conversas gerais
- `random` - Para tópicos aleatórios

## Arquitetura Técnica

### Redis Streams

O sistema utiliza Redis Streams para:
- **Persistência**: Mensagens são armazenadas no Redis
- **Tempo real**: Escuta por novas mensagens usando `XREAD`
- **Escalabilidade**: Suporte a múltiplos consumidores
- **Ordem**: Mensagens são ordenadas por timestamp

### Estrutura de dados

Cada canal é um Redis Stream com chave `chat:{nome_do_canal}`:

```json
{
  "type": "message",
  "username": "usuario",
  "message": "conteúdo da mensagem",
  "timestamp": 1642694400.0
}
```

### Componentes principais

1. **ChatRedisClient**: Gerencia conexão e operações com Redis
2. **ChatApp**: Interface Textual com componentes reativos
3. **Workers**: Escutam por novas mensagens em background

## Desenvolvimento

### Estrutura do projeto

```
chat-redis/
├── main.py           # Aplicação principal
├── pyproject.toml    # Dependências Python
├── compose.yml       # Configuração Redis
├── README.md         # Documentação
└── uv.lock          # Lock file das dependências
```

### Logs e Debug

Para debug, você pode verificar os logs do Redis:

```bash
docker compose logs -f redis
```

## Possíveis melhorias

- [ ] Autenticação de usuários
- [ ] Canais privados/protegidos por senha
- [ ] Notificações para mentions (@usuario)
- [ ] Histórico de mensagens com paginação
- [ ] Emojis e formatação de texto
- [ ] Status online/offline dos usuários
- [ ] Mensagens privadas (DM)

## Troubleshooting

### Redis não conecta
1. Verifique se o Docker está rodando: `docker ps`
2. Reinicie o Redis: `docker compose restart redis`

### Erro de dependências
1. Limpe o cache: `uv cache clean`
2. Reinstale: `uv sync --reinstall`

### Interface não atualiza
1. Pressione `r` para atualizar canais
2. Reselecione o canal atual
