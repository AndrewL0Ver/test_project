import grpc
from concurrent import futures
import time
import json
import psycopg2
from datetime import datetime
import threading
from google.protobuf import empty_pb2
import grpc_demo_pb2 as data_pb2
import grpc_demo_pb2_grpc as data_pb2_grpc
# Конфигурация сервера
server_config = {
    "gRPCServerPort": 50051
}

# Конфигурация клиента
client_config = {
    "TotalPackets": 10,
    "RecordsInPacket": 5,
    "TimeInterval": 2,
    "gRPCServerAddr": "localhost",
    "gRPCServerPort": 50051
}

# Определяем класс сервиса gRPC для сервера
class DataServiceServicer(data_pb2_grpc.DataServiceServicer):
    def init(self):
        # Подключение к БД PostgreSQL
        self.conn = psycopg2.connect(
            dbname="grpc_db",
            user="postgres",
            password="password",
            host="localhost"
        )
        self.cursor = self.conn.cursor()

    def SendData(self, request, context):
        packet_seq_num = request.PacketSeqNum
        packet_timestamp = request.PacketTimestamp
        packet_data = request.PacketData

        # Сохраняем данные в БД
        for i, record in enumerate(packet_data):
            self.cursor.execute(
                "INSERT INTO grpc_data (PacketSeqNum, RecordSeqNum, PacketTimestamp, Decimal1, Decimal2, Decimal3, Decimal4, RecordTimestamp) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (packet_seq_num, i + 1, packet_timestamp, record.Decimal1, record.Decimal2, record.Decimal3, record.Decimal4, record.RecordTimestamp)
            )
        self.conn.commit()
        return empty_pb2.Empty()

# Функция для запуска gRPC сервера
def run_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    data_pb2_grpc.add_DataServiceServicer_to_server(DataServiceServicer(), server)
    server.add_insecure_port(f'[::]:{server_config["gRPCServerPort"]}')
    server.start()
    print(f'Server started on port {server_config["gRPCServerPort"]}')
    server.wait_for_termination()

# Клиентская функция для отправки данных
def generate_data_packet(seq_num, records_count):
    # Генерация пакета данных
    data_packet = data_pb2.DataPacket(
        PacketTimestamp=datetime.now().isoformat(),
        PacketSeqNum=seq_num,
        NRecords=records_count,
    )
    
    for _ in range(records_count):
        data_packet.PacketData.append(data_pb2.Data(
            Decimal1=1.23,
            Decimal2=2.34,
            Decimal3=3.45,
            Decimal4=4.56,
            RecordTimestamp=datetime.now().isoformat()
        ))
    
    return data_packet

def run_client():
    # Устанавливаем соединение с сервером
    channel = grpc.insecure_channel(f'{client_config["gRPCServerAddr"]}:{client_config["gRPCServerPort"]}')
    stub = data_pb2_grpc.DataServiceStub(channel)

    for seq_num in range(1, client_config["TotalPackets"] + 1):
        packet = generate_data_packet(seq_num, client_config["RecordsInPacket"])
        stub.SendData(packet)
        print(f"Sent packet {seq_num}")
        time.sleep(client_config["TimeInterval"])

# Запуск сервера в отдельном потоке
server_thread = threading.Thread(target=run_server)
server_thread.start()

# Даем серверу немного времени для запуска
time.sleep(2)
# Запуск клиента
run_client()

# Завершение работы сервера после клиента
server_thread.join()
CREATE TABLE grpc_data (
    PacketSeqNum INT,
    RecordSeqNum INT,
    PacketTimestamp TIMESTAMP,
    Decimal1 DOUBLE PRECISION,
    Decimal2 DOUBLE PRECISION,
    Decimal3 DOUBLE PRECISION,
    Decimal4 DOUBLE PRECISION,
    RecordTimestamp TIMESTAMP,
    PRIMARY KEY (PacketSeqNum, RecordSeqNum)
);
# Используем базовый образ Python
FROM python:3.10-slim

# Копируем файлы
WORKDIR /app
COPY server.py .
COPY data.proto .

# Устанавливаем зависимости
RUN pip install grpcio grpcio-tools psycopg2-binary

# Компилируем gRPC код
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. data.proto

# Запускаем сервер
CMD ["python", "server.py"]
# Используем базовый образ Python
FROM python:3.10-slim

# Копируем файлы
WORKDIR /app
COPY client.py .
COPY data.proto .

# Устанавливаем зависимости
RUN pip install grpcio grpcio-tools

# Компилируем gRPC код
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. data.proto

# Запускаем клиента
CMD ["python", "client.py"]
version: '3.7'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: grpc_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - grpc_network

  server:
    build: ./server
    depends_on:
      - db
    networks:
      - grpc_network

  client:
    build: ./client
    depends_on:
      - server
    networks:
      - grpc_network

networks:
  grpc_network:

volumes:
  postgres_data:
/grpc_docker_project
    ├── server
    │   ├── Dockerfile
    │   ├── server.py
    │   └── data.proto
    ├── client
    │   ├── Dockerfile
    │   ├── client.py
    └── docker-compose.yml
syntax = "proto3";

message Data {
    float Decimal1 = 1;
    float Decimal2 = 2;
    float Decimal3 = 3;
    float Decimal4 = 4;
    string RecordTimestamp = 5;
}

message DataPacket {
    string PacketTimestamp = 1;
    int32 PacketSeqNum = 2;
    int32 NRecords = 3;
    repeated Data PacketData = 4;
}

service DataService {
    rpc SendData (DataPacket) returns (google.protobuf.Empty);
}

import "google/protobuf/empty.proto";
