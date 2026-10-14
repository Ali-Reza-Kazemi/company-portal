#!/usr/bin/env bash
set -euo pipefail
printf '\nCPU and RAM\n'
lscpu
free -h
printf '\nDisk\n'
df -h / /opt
printf '\nListeners\n'
ss -lnt
printf '\nExisting containers and networks\n'
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
docker network ls
printf '\nDocker storage\n'
docker system df
