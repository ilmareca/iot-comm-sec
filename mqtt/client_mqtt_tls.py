import paho.mqtt.client as mqtt
import time
import psutil
import statistics
import tracemalloc
import os
import threading

NUM_MESSAGES = 100
BROKER = "127.0.0.1"
PORT = 8883  # Usa 1883 para sin TLS
TOPIC = "hola"
USE_TLS = True  # Cambia a False si quieres sin TLS
CA_CERT = r"C:\Users\inesl\OneDrive\Escritorio\MASTER\TFM-IOT\iot-comm-sec\mqtt\certs\ca.crt"

latencies = []
timestamps = []

def on_message(client, userdata, msg):
    recv_time = time.perf_counter()
    if msg.payload.decode() == "Hola desde el cliente MQTT":
        latency = (recv_time - timestamps.pop(0)) * 1000  # ms
        latencies.append(latency)

def mqtt_subscriber():
    client = mqtt.Client()
    client.on_message = on_message
    if USE_TLS:
        client.tls_set(ca_certs=CA_CERT)
        client.tls_insecure_set(True)
    client.connect(BROKER, PORT, 60)
    client.subscribe(TOPIC)
    client.loop_forever()

def main():
    process = psutil.Process(os.getpid())
    cpu_start = process.cpu_times()
    io_start = process.io_counters()
    tracemalloc.start()

    sub_thread = threading.Thread(target=mqtt_subscriber)
    sub_thread.daemon = True
    sub_thread.start()
    time.sleep(1)  # Espera a que el subscriptor esté activo

    pub_client = mqtt.Client()
    if USE_TLS:
        pub_client.tls_set(ca_certs=CA_CERT)
        pub_client.tls_insecure_set(True)
    pub_client.connect(BROKER, PORT, 60)

    for _ in range(NUM_MESSAGES):
        timestamps.append(time.perf_counter())
        pub_client.publish(TOPIC, "Hola desde el cliente MQTT")
        time.sleep(0.01)  # envío cada 10ms

    time.sleep(2)  # espera para asegurar recepción

    cpu_end = process.cpu_times()
    io_end = process.io_counters()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\n--- Resultados ---")
    print(f"Número de mensajes recibidos: {len(latencies)}")
    print(f"Latencia media: {statistics.mean(latencies):.2f} ms")
    print(f"Desviación estándar: {statistics.stdev(latencies):.2f} ms")
    print(f"CPU modo usuario: {cpu_end.user - cpu_start.user:.2f} s")
    print(f"CPU modo sistema: {cpu_end.system - cpu_start.system:.2f} s")
    print(f"Lecturas de disco: {io_end.read_count - io_start.read_count}")
    print(f"Escrituras de disco: {io_end.write_count - io_start.write_count}")
    print(f"Memoria pico usada (Python): {peak / 1024:.2f} KB")
    print(f"Memoria residente total (RSS): {process.memory_info().rss / 1024:.2f} KB")

if __name__ == "__main__":
    main()
