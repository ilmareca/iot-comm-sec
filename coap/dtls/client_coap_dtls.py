import asyncio
import time
import statistics
import psutil
from aiocoap import *

async def main():
    NUM_REQUESTS = 100
    latencias = []

    process = psutil.Process()

    # Medidas antes de comenzar
    cpu_user_start = process.cpu_times().user
    cpu_sys_start = process.cpu_times().system
    mem_info_start = process.memory_info()
    io_start = process.io_counters()

    protocol = await Context.create_client_context()

    await asyncio.sleep(1)  # Da tiempo a establecer el contexto

    for _ in range(NUM_REQUESTS):
        request = Message(code=GET, uri='coap://127.0.0.1:5684/hola')
        start = time.perf_counter()
        try:
            response = await protocol.request(request).response
            end = time.perf_counter()
            latencias.append((end - start) * 1000)  # ms
        except Exception as e:
            print("Error en la solicitud:", e)

    # Medidas después de las solicitudes
    cpu_user_end = process.cpu_times().user
    cpu_sys_end = process.cpu_times().system
    mem_info_end = process.memory_info()
    io_end = process.io_counters()

    print("\n--- Resultados ---")
    print(f"Número de solicitudes: {len(latencias)}")
    print(f"Latencia media: {statistics.mean(latencias):.2f} ms")
    print(f"Desviación estándar: {statistics.stdev(latencias):.2f} ms")
    print(f"CPU modo usuario: {cpu_user_end - cpu_user_start:.2f} s")
    print(f"CPU modo sistema: {cpu_sys_end - cpu_sys_start:.2f} s")
    print(f"Lecturas de disco: {io_end.read_count - io_start.read_count}")
    print(f"Escrituras de disco: {io_end.write_count - io_start.write_count}")
    print(f"Memoria pico usada (Python): {(mem_info_end.vms - mem_info_start.vms)/1024:.2f} KB")
    print(f"Memoria residente total (RSS): {mem_info_end.rss / 1024:.2f} KB")

if __name__ == "__main__":
    asyncio.run(main())
