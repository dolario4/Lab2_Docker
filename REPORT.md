# Лабораторная работа №2
## Тема
**Развертывание системы мониторинга технологических данных с использованием Docker, MQTT, InfluxDB, Telegraf и Grafana.**

## Цель работы
Развернуть распределённую систему из трёх виртуальных машин Linux, в которой контейнеры-симуляторы датчиков публикуют сообщения в MQTT-брокер, Telegraf сохраняет эти сообщения в InfluxDB, а Grafana визуализирует текущие и агрегированные значения датчиков.

---

## 1. Архитектура решения

В работе использованы три виртуальные машины:

- **Linux A** — контейнеры-симуляторы датчиков
- **Linux B** — MQTT-брокер Mosquitto
- **Linux C** — InfluxDB 1.8, Telegraf и Grafana

Схема взаимодействия сервисов:

`Sensor containers -> Mosquitto -> Telegraf -> InfluxDB -> Grafana`

### Логика работы
1. Контейнеры датчиков на Linux A генерируют значения температуры, давления, тока и влажности.
2. Датчики публикуют сообщения в MQTT-брокер Mosquitto на Linux B.
3. Telegraf на Linux C подписывается на MQTT-топики и получает сообщения.
4. Telegraf записывает данные в базу временных рядов InfluxDB.
5. Grafana подключается к InfluxDB и отображает дашборд с текущими и средними значениями датчиков.

---

## 2. Используемые виртуальные машины

| ВМ | Назначение | Основной IP | Доп. IP / Host-Only |
|---|---|---:|---:|
| Linux A | Симуляторы датчиков | `<ip_linux_a_internal>` | `<ip_linux_a_host_only>` |
| Linux B | Mosquitto | `<ip_linux_b_net_a>` / `<ip_linux_b_net_c>` | `<ip_linux_b_host_only>` |
| Linux C | InfluxDB, Telegraf, Grafana | `<ip_linux_c_internal>` | `<ip_linux_c_host_only>` |

### Пример из моей конфигурации
- Linux B:
  - `192.168.4.1` — сеть с Linux A
  - `192.168.9.10` — сеть с Linux C
  - `192.168.56.20` — host-only для доступа с хоста

---

## 3. Подготовка окружения

На всех трёх виртуальных машинах был установлен Docker Engine и Docker Compose plugin.

Проверка установки:

```bash
docker --version
docker compose version
sudo systemctl status docker --no-pager
```
## 4. Linux B

В каталоге `~/lab2/vms/gateway/mosquitto` создаем конфигурационный файл `mosquitto.conf`

```bash
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest stdout
```
### Произвоим запуск контейнера Mosquitto
```bash
docker run -d \
  --name mosquitto \
  --restart unless-stopped \
  -p 1883:1883 \
  -v $(pwd)/mosquitto.conf:/mosquitto/config/mosquitto.conf \
  -v mosquitto_data:/mosquitto/data \
  eclipse-mosquitto:2
  ```
Следом проводим открытие порта в Firewall
  
  ```bash
  sudo ufw allow 1883/tcp
  sudo ufw status
  ```
  ## 5. Linux C
  В каталоге `~/lab2/vms/server` создаем 3 директории для хранения конфигурационных файлов - `grafana/`, `telegraf/` , `influxdb/`
  \
  Файл `docker-compose.yml` содержит в себе:

  ```yaml
  services:
  influxdb:
    image: influxdb:1.8
    container_name: influxdb
    restart: unless-stopped
    ports:
      - "8086:8086"
    volumes:
      - influxdb_data:/var/lib/influxdb
    networks:
      monitor_net:
        aliases:
          - influxdb

  telegraf:
    image: telegraf:1.30
    container_name: telegraf
    restart: unless-stopped
    depends_on:
      - influxdb
    volumes:
      - ./telegraf/telegraf.conf:/etc/telegraf/telegraf.conf:ro
    networks:
      - monitor_net

  grafana:
    image: grafana/grafana
    container_name: grafana
    restart: unless-stopped
    depends_on:
      - influxdb
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      monitor_net:
        aliases:
          - grafana

volumes:
  influxdb_data:
  grafana_data:

networks:
  monitor_net:
    driver: bridge
```
`telegraf.conf` :

```yaml
[agent]
  interval = "5s"
  round_interval = true
  metric_batch_size = 1000
  metric_buffer_limit = 10000
  flush_interval = "5s"
  flush_jitter = "0s"
  precision = ""
  hostname = "linux-c-telegraf"
  omit_hostname = false

[[inputs.mqtt_consumer]]
  servers = ["tcp://<ip_linux_b_net_c>:1883"]
  topics = ["sensors/#"]
  qos = 0
  connection_timeout = "30s"
  client_id = "telegraf_linux_c"
  data_format = "influx"

[[outputs.influxdb]]
  urls = ["http://influxdb:8086"]
  database = "sensors"
  skip_database_creation = true
  username = "telegraf"
  password = "telegraf"
```
Поднимаем контейнеры
```bash
docker compose up -d
```
![Дашборд Grafana](assets/images/compose%20ps%20grafana%20influxdb%20telegraf.png)

В InfluxDB создаем базу данных и пользователя
```SQL
create database sensors
create user telegraf with password 'telegraf'
grant all on sensors to telegraf
show databases
show users
exit
```
# 6. Linux A - симуляторы датчиков
На Linux A был разработан симулятор технологических данных. Был реализован базовый класс Sensor и его наследники.

## Реализованные типы датчиков
- TemperatureSensor
- PressureSensor
- CurrentSensor
- HumiditySensor

Содержимое `requirements.txt`
```txt
paho-mqtt==1.6.1
```
Содержимое Dockerfile 
```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```
Проверка одиночного контейнера 
```bash
docker run --rm \
  -e SENSOR_TYPE=temperature \
  -e SENSOR_NAME=temp1 \
  -e PUBLISH_INTERVAL=3 \
  -e MQTT_HOST=192.168.4.1 \
  -e MQTT_PORT=1883 \
  -e MQTT_TOPIC=sensors/temperature \
  -e BIRTH_DAY=4 \
  -e BIRTH_MONTH=9 \
  -e BIRTH_YEAR=2003 \
  sensor-simulator:latest
```
Содержимое `docker-compose.yml`
```yaml
services:
  temp1:
    image: sensor-simulator:latest
    container_name: temp1
    restart: unless-stopped
    environment:
      SENSOR_TYPE: temperature
      SENSOR_NAME: temp1
      PUBLISH_INTERVAL: 3
      MQTT_HOST: 192.168.4.1
      MQTT_PORT: 1883
      MQTT_TOPIC: sensors/temperature
      BIRTH_DAY: 4
      BIRTH_MONTH: 9
      BIRTH_YEAR: 2003

  temp2:
    image: sensor-simulator:latest
    container_name: temp2
    restart: unless-stopped
    environment:
      SENSOR_TYPE: temperature
      SENSOR_NAME: temp2
      PUBLISH_INTERVAL: 5
      MQTT_HOST: 192.168.4.1
      MQTT_PORT: 1883
      MQTT_TOPIC: sensors/temperature
      BIRTH_DAY: 4
      BIRTH_MONTH: 9
      BIRTH_YEAR: 2003

  pressure1:
    image: sensor-simulator:latest
    container_name: pressure1
    restart: unless-stopped
    environment:
      SENSOR_TYPE: pressure
      SENSOR_NAME: pressure1
      PUBLISH_INTERVAL: 4
      MQTT_HOST: 192.168.4.1
      MQTT_PORT: 1883
      MQTT_TOPIC: sensors/pressure
      BIRTH_DAY: 4
      BIRTH_MONTH: 9
      BIRTH_YEAR: 2003

  pressure2:
    image: sensor-simulator:latest
    container_name: pressure2
    restart: unless-stopped
    environment:
      SENSOR_TYPE: pressure
      SENSOR_NAME: pressure2
      PUBLISH_INTERVAL: 6
      MQTT_HOST: 192.168.4.1
      MQTT_PORT: 1883
      MQTT_TOPIC: sensors/pressure
      BIRTH_DAY: 4
      BIRTH_MONTH: 9
      BIRTH_YEAR: 2003

  current1:
    image: sensor-simulator:latest
    container_name: current1
    restart: unless-stopped
    environment:
      SENSOR_TYPE: current
      SENSOR_NAME: current1
      PUBLISH_INTERVAL: 4
      MQTT_HOST: 192.168.4.1
      MQTT_PORT: 1883
      MQTT_TOPIC: sensors/current
      BIRTH_DAY: 4
      BIRTH_MONTH: 9
      BIRTH_YEAR: 2003

  humidity1:
    image: sensor-simulator:latest
    container_name: humidity1
    restart: unless-stopped
    environment:
      SENSOR_TYPE: humidity
      SENSOR_NAME: humidity1
      PUBLISH_INTERVAL: 7
      MQTT_HOST: 192.168.4.1
      MQTT_PORT: 1883
      MQTT_TOPIC: sensors/humidity
      BIRTH_DAY: 4
      BIRTH_MONTH: 9
      BIRTH_YEAR: 2003
```
![Дашборд Grafana](assets/images/compose%20ps%20sensors%20full.png)

# 7. Настройка Grafana
Grafana доступна по адресу: `http://192.168.56.30:3000/`

![Grafana](assets/images/Grafana%20save&test.png)

## Созданный дашбоард

Текущие значения
- Current Temperature
- Current Pressure
- Current Humidity
- Current Current

Средние значения
- Mean Temperature
- Mean Pressure
- Mean Humidity
- Mean Current

Графики
- Temperature Over Time
- Pressure Over Time
- Humidity Over Time
- Current Over Time

  ![Дашборд Grafana](assets/images/Final%20Grafana.png)
