# Инструкция по запуску лабораторной работы №2

## Назначение

Данная инструкция описывает порядок запуска системы мониторинга технологических данных на трёх виртуальных машинах Linux.

Система состоит из следующих частей:

- **Linux A** — контейнеры-симуляторы датчиков
- **Linux B** — MQTT-брокер Mosquitto
- **Linux C** — InfluxDB, Telegraf и Grafana

Общая схема работы:

```text
Sensor containers -> Mosquitto -> Telegraf -> InfluxDB -> Grafana
```

Симуляторы датчиков публикуют сообщения в MQTT-брокер.  
Telegraf подписывается на MQTT-топики и сохраняет данные в InfluxDB.  
Grafana читает данные из InfluxDB и отображает дашборд.

---

## 1. Требования перед запуском

На всех трёх виртуальных машинах должны быть установлены:

- Docker
- Docker Compose plugin

Проверка:

```bash
docker --version
docker compose version
```

Также между виртуальными машинами должна быть настроена сеть:

| ВМ | Назначение | IP |
|---|---|---|
| Linux A | Симуляторы датчиков | `<ip_linux_a>` |
| Linux B | MQTT-брокер Mosquitto | `192.168.4.1`, `192.168.9.10` |
| Linux C | InfluxDB, Telegraf, Grafana | `<ip_linux_c>` |

В данной работе использовались адреса Linux B:

```text
192.168.4.1  — адрес Linux B со стороны Linux A
192.168.9.10 — адрес Linux B со стороны Linux C
```

---

## 2. Запуск Linux B — Mosquitto

Перейти в каталог с конфигурацией Mosquitto:

```bash
cd vms/gateway/mosquitto
```

Проверить наличие файлов:

```bash
ls -l
```

В каталоге должны быть файлы:

```text
mosquitto.conf
docker-compose.yml
run.sh
```

Запустить MQTT-брокер:

```bash
docker compose up -d
```

Проверить, что контейнер запущен:

```bash
docker compose ps
docker logs mosquitto --tail 50
```

Открыть порт 1883 в firewall:

```bash
sudo ufw allow 1883/tcp
sudo ufw status
```

Проверить доступность порта с Linux A:

```bash
nc -zv 192.168.4.1 1883
```

Проверить доступность порта с Linux C:

```bash
nc -zv 192.168.9.10 1883
```

---

## 3. Проверка Mosquitto

На Linux B можно проверить работу MQTT-брокера через publish/subscribe.

В первом терминале выполнить:

```bash
docker exec -it mosquitto mosquitto_sub -t test/topic
```

Во втором терминале выполнить:

```bash
docker exec -it mosquitto mosquitto_pub -t test/topic -m "hello"
```

Если в первом терминале появилось сообщение:

```text
hello
```

значит Mosquitto работает корректно.

---

## 4. Запуск Linux C — InfluxDB, Telegraf, Grafana

Перейти в каталог серверной части:

```bash
cd vms/server
```

Проверить наличие структуры:

```bash
ls -l
```

В каталоге должны быть:

```text
docker-compose.yml
grafana/
influxdb/
telegraf/
```

Запустить сервисы:

```bash
docker compose up -d
```

Проверить статус контейнеров:

```bash
docker compose ps
```

Должны быть запущены контейнеры:

```text
influxdb
telegraf
grafana
```

Проверить логи:

```bash
docker logs influxdb --tail 50
docker logs telegraf --tail 50
docker logs grafana --tail 50
```

---

## 5. Создание базы данных InfluxDB

При первом запуске необходимо создать базу данных `sensors` и пользователя `telegraf`.

Войти в контейнер InfluxDB:

```bash
docker exec -it influxdb influx
```

Внутри InfluxDB shell выполнить:

```sql
create database sensors
create user telegraf with password 'telegraf'
grant all on sensors to telegraf
show databases
show users
exit
```

После этого перезапустить Telegraf:

```bash
docker compose restart telegraf
```

Проверить логи Telegraf:

```bash
docker logs telegraf --tail 50
```

---

## 6. Проверка связки Mosquitto -> Telegraf -> InfluxDB

На Linux B отправить тестовое MQTT-сообщение:

```bash
docker exec -it mosquitto mosquitto_pub -h 127.0.0.1 -t sensors/temperature -m 'temperature,name=temp1 value=23.5'
```

На Linux C проверить, что данные появились в InfluxDB:

```bash
docker exec -it influxdb influx
```

Внутри shell:

```sql
use sensors
show measurements
select * from temperature limit 5
```

Если появился measurement `temperature` и строка со значением `23.5`, значит связка работает.

---

## 7. Запуск Linux A — симуляторы датчиков

Перейти в каталог симулятора:

```bash
cd vms/client/simulator
```

Проверить наличие файлов:

```bash
ls -l
```

В каталоге должны быть:

```text
main.py
sensor.py
requirements.txt
Dockerfile
docker-compose.yml
.env.example
```

В данной работе используется публичный Docker Hub образ:

```text
dolario4/sensor-simulator:latest
```

Запустить контейнеры датчиков:

```bash
docker compose up -d
```

Проверить, что контейнеры запущены:

```bash
docker compose ps
```

Должны быть запущены 6 контейнеров:

```text
temp1
temp2
pressure1
pressure2
current1
humidity1
```

Проверить логи генерации данных:

```bash
docker compose logs --tail 50
```

В логах должны отображаться сообщения вида:

```text
[temp1] topic=sensors/temperature message=temperature,name=temp1 value=22.31
[pressure1] topic=sensors/pressure message=pressure,name=pressure1 value=1.18
[current1] topic=sensors/current message=current,name=current1 value=8.24
[humidity1] topic=sensors/humidity message=humidity,name=humidity1 value=56.7
```

---

## 8. Проверка данных в InfluxDB

На Linux C выполнить:

```bash
docker exec -it influxdb influx
```

Внутри shell:

```sql
use sensors
show measurements
```

Должны появиться measurements:

```text
temperature
pressure
current
humidity
```

Проверить данные по каждому типу датчиков:

```sql
select * from temperature limit 5
select * from pressure limit 5
select * from current limit 5
select * from humidity limit 5
```

---

## 9. Открытие Grafana

Grafana доступна по адресу:

```text
http://<ip_linux_c_host_only>:3000
```

Например:

```text
http://192.168.56.X:3000
```

Логин и пароль:

```text
admin / admin
```

---

## 10. Проверка Grafana

В Grafana должен быть доступен дашборд:

```text
Sensor Monitoring Dashboard
```

На дашборде должны отображаться:

### Текущие значения

- Current Temperature
- Current Pressure
- Current Humidity
- Current Current

### Средние значения

- Average Temperature
- Average Pressure
- Average Humidity
- Average Current

### Графики во времени

- Temperature Over Time
- Pressure Over Time
- Humidity Over Time
- Current Over Time

Если данных нет, необходимо проверить:

1. запущены ли контейнеры датчиков на Linux A;
2. работает ли Mosquitto на Linux B;
3. нет ли ошибок в логах Telegraf;
4. есть ли данные в InfluxDB;
5. выбран ли в Grafana диапазон времени `Last 24 hours`.

---

## 11. Перезапуск системы

### Перезапуск Mosquitto на Linux B

```bash
cd vms/gateway/mosquitto
docker compose restart
```

### Перезапуск серверной части на Linux C

```bash
cd vms/server
docker compose restart
```

### Перезапуск датчиков на Linux A

```bash
cd vms/client/simulator
docker compose restart
```

---

## 12. Полная остановка системы

### Linux A

```bash
cd vms/client/simulator
docker compose down
```

### Linux B

```bash
cd vms/gateway/mosquitto
docker compose down
```

### Linux C

```bash
cd vms/server
docker compose down
```

Важно: не использовать команду:

```bash
docker compose down -v
```

если не нужно удалять volumes и сохранённые данные.

---

## 13. Очистка данных InfluxDB

Если нужно начать сбор данных заново, на Linux C выполнить:

```bash
docker exec -it influxdb influx
```

Внутри shell:

```sql
use sensors
drop measurement temperature
drop measurement pressure
drop measurement current
drop measurement humidity
exit
```

После этого перезапустить датчики на Linux A:

```bash
cd vms/client/simulator
docker compose restart
```

---

## 14. Docker Hub

Образ симулятора опубликован в Docker Hub:

```text
dolario4/sensor-simulator:latest
```

Проверка загрузки образа:

```bash
docker pull dolario4/sensor-simulator:latest
```

Для ручной сборки образа из исходного кода:

```bash
cd vms/client/simulator
docker build -t sensor-simulator:latest .
```

Для загрузки образа в Docker Hub:

```bash
docker login
docker tag sensor-simulator:latest dolario4/sensor-simulator:latest
docker push dolario4/sensor-simulator:latest
```

---

## 15. Проверочный сценарий для преподавателя

Для проверки работы необходимо выполнить следующие действия:

1. На Linux B запустить Mosquitto:

```bash
cd vms/gateway/mosquitto
docker compose up -d
```

2. На Linux C запустить InfluxDB, Telegraf и Grafana:

```bash
cd vms/server
docker compose up -d
```

3. При первом запуске создать базу данных:

```bash
docker exec -it influxdb influx
```

```sql
create database sensors
create user telegraf with password 'telegraf'
grant all on sensors to telegraf
exit
```

4. На Linux A запустить симуляторы:

```bash
cd vms/client/simulator
docker compose up -d
```

5. Проверить данные в InfluxDB:

```bash
docker exec -it influxdb influx
```

```sql
use sensors
show measurements
```

6. Открыть Grafana:

```text
http://<ip_linux_c_host_only>:3000
```

7. Убедиться, что на дашборде отображаются текущие и средние значения датчиков.

---

## 16. Возможные проблемы

### Ошибка: `connection refused` при подключении к Mosquitto

Проверить, запущен ли контейнер на Linux B:

```bash
docker ps
docker logs mosquitto
```

Проверить порт:

```bash
nc -zv 192.168.4.1 1883
nc -zv 192.168.9.10 1883
```

### Ошибка Telegraf при записи в InfluxDB

Проверить логи:

```bash
docker logs telegraf --tail 100
```

Проверить, создана ли база:

```bash
docker exec -it influxdb influx
```

```sql
show databases
show users
```

### В Grafana нет данных

Проверить:

```bash
docker exec -it influxdb influx
```

```sql
use sensors
show measurements
select * from temperature limit 5
```

Также в Grafana поставить диапазон времени:

```text
Last 24 hours
```

### Контейнер с датчиком не запускается

Проверить логи:

```bash
cd vms/client/simulator
docker compose logs --tail 100
```

Проверить доступность MQTT-брокера:

```bash
nc -zv 192.168.4.1 1883
```

---

## 17. Итог

После выполнения инструкции система должна работать следующим образом:

1. 6 контейнеров датчиков на Linux A постоянно генерируют значения.
2. Данные публикуются в MQTT-брокер Mosquitto на Linux B.
3. Telegraf на Linux C получает сообщения из MQTT.
4. InfluxDB сохраняет значения в базе `sensors`.
5. Grafana отображает текущие значения, средние значения и графики изменения параметров.
