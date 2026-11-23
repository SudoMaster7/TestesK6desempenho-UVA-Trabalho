#!/usr/bin/env bash
# Sobe (ou reinicia) a aplicacao Spring Boot em background e espera ficar pronta.
# Uso: scripts/app-restart.sh [profile]
set -euo pipefail
cd "$(dirname "$0")/.."
PROFILE="${1:-}"
JAVA_HOME_WIN='C:\Program Files\Microsoft\jdk-21.0.13.102-hotspot'

echo ">> matando instancia anterior na porta 8080 (se houver)"
# netstat lista a porta em IPv4 e IPv6 -> pode haver PIDs repetidos; sort -u evita
# matar duas vezes. Sem isso, uma instancia antiga continua respondendo e os
# testes medem o codigo ANTIGO (erro silencioso e dificil de perceber).
# ATENCAO: use /PID (uma barra). O `//PID` do idioma MSYS NAO funciona aqui,
# porque a conversao de caminhos esta desabilitada nesta maquina.
for PID in $(netstat -ano 2>/dev/null | grep LISTENING | grep ':8080' | awk '{print $NF}' | sort -u); do
  echo "   matando PID $PID"
  taskkill /PID "$PID" /F >/dev/null 2>&1 || true
done
sleep 4
if netstat -ano 2>/dev/null | grep LISTENING | grep -q ':8080'; then
  echo ">> ERRO: porta 8080 ainda ocupada"; exit 1
fi

ARGS=""
if [ -n "$PROFILE" ]; then
  ARGS="-Dspring-boot.run.profiles=$PROFILE"
  echo ">> profile: $PROFILE"
fi

cd app
nohup cmd.exe /c "set JAVA_HOME=$JAVA_HOME_WIN&& mvnw.cmd -B -DskipTests $ARGS spring-boot:run" \
  > ../results/app.log 2>&1 &

echo ">> aguardando /actuator/health"
for _ in $(seq 1 60); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/actuator/health || true)" = "200" ]; then
    echo ">> aplicacao PRONTA"
    exit 0
  fi
  sleep 3
done
echo ">> ERRO: aplicacao nao subiu. Veja results/app.log"
tail -40 ../results/app.log
exit 1
