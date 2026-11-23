#!/usr/bin/env bash
# =====================================================================
# Encerra qualquer bateria de testes em andamento e limpa o lock.
#
# Necessario porque matar o terminal NAO mata o runner no Windows/Git Bash:
# um runner orfao continua disparando k6 e, se uma nova bateria comecar,
# as duas se contaminam.
# =====================================================================
export MSYS_NO_PATHCONV=1  # evita o Git Bash converter /PID e /c em caminhos
cd "$(dirname "$0")/.."

echo ">> encerrando runners..."
for p in $(ps -ef 2>/dev/null | grep "[r]un-all-tests" | awk '{print $2}'); do
  taskkill /PID "$p" /F >/dev/null 2>&1 || kill -9 "$p" 2>/dev/null
done

echo ">> encerrando k6..."
taskkill /IM k6.exe /F >/dev/null 2>&1

rm -f results/.run-all.lock
sleep 2

echo ">> restantes: runners=$(ps -ef 2>/dev/null | grep -c '[r]un-all-tests') k6=$(tasklist 2>/dev/null | grep -ci 'k6.exe')"
echo ">> ok. Agora e seguro iniciar uma nova bateria."
