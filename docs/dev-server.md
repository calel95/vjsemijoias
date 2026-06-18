# Servidor local de desenvolvimento

Use este script para evitar servidores antigos na porta 5000 usando variaveis
de ambiente velhas:

```powershell
powershell -ExecutionPolicy Bypass -File tools/dev_server.ps1
```

Ele faz o fluxo seguro para desenvolvimento local:

1. Para qualquer processo ouvindo na porta 5000.
2. Remove `DATABASE_URL` herdado do terminal, para `backend/.env` ser a fonte.
3. Aplica migrations com Alembic.
4. Mostra a URL de banco efetiva que o app vai usar.
5. Sobe `uvicorn backend.app:app` em primeiro plano.

Opcoes uteis:

```powershell
# Subir com reload automatico
powershell -ExecutionPolicy Bypass -File tools/dev_server.ps1 -Reload

# Apenas parar servidores antigos
powershell -ExecutionPolicy Bypass -File tools/dev_server.ps1 -StopOnly

# Subir em outra porta
powershell -ExecutionPolicy Bypass -File tools/dev_server.ps1 -Port 5001

# Forcar uma DATABASE_URL especifica para esta execucao
powershell -ExecutionPolicy Bypass -File tools/dev_server.ps1 -DatabaseUrl "sqlite:///vjsemijoias.db"
```

Evite iniciar o app manualmente com varios comandos diferentes de `uvicorn`.
Isso costuma deixar processos antigos vivos, especialmente quando `--reload`
cria processo pai e filho no Windows.
