import asyncio
import time
import psutil
import statistics
import tracemalloc
import os

from aiocoap import *

NUM_REQUESTS = 100
RESOURCE_URI = "coap://127.0.0.1/hola"

async def main():
    protocol = await Context.create_client_context()
    latencies = []

    process = psutil.Process(os.getpid())
    cpu_start = process.cpu_times()
    io_start = process.io_counters()
    tracemalloc.start()

    for _ in range(NUM_REQUESTS):
        request = Message(code=GET, uri=RESOURCE_URI)
        start = time.perf_counter()
        try:
            response = await protocol.request(request).response
        except Exception as e:
            print(f"Error en solicitud: {e}")
            continue
        end = time.perf_counter()
        latencies.append((end - start) * 1000)  # ms

    cpu_end = process.cpu_times()
    io_end = process.io_counters()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print("\n--- Resultados ---")
    print(f"Número de solicitudes: {len(latencies)}")
    print(f"Latencia media: {statistics.mean(latencies):.2f} ms")
    print(f"Desviación estándar: {statistics.stdev(latencies):.2f} ms")
    print(f"CPU modo usuario: {cpu_end.user - cpu_start.user:.2f} s")
    print(f"CPU modo sistema: {cpu_end.system - cpu_start.system:.2f} s")
    print(f"Lecturas de disco: {io_end.read_count - io_start.read_count}")
    print(f"Escrituras de disco: {io_end.write_count - io_start.write_count}")
    print(f"Memoria pico usada (Python): {peak / 1024:.2f} KB")
    print(f"Memoria residente total (RSS): {process.memory_info().rss / 1024:.2f} KB")

if __name__ == "__main__":
    asyncio.run(main())