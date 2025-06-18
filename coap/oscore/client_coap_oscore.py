import asyncio
import time
import statistics
import psutil
import os
import json
from aiocoap import Context, Message, GET
from aiocoap.credentials import CredentialsMap

async def run_requests():
    latencias = []

    process = psutil.Process(os.getpid())
    cpu_user_start, cpu_sys_start = process.cpu_times().user, process.cpu_times().system
    io_start = process.io_counters()
    mem_info_start = process.memory_info()

    # Cargar credenciales OSCORE
    with open("client.json") as f:
        cred_data = json.load(f)
    credentials = CredentialsMap()
    credentials.load_from_dict(cred_data)

    context = await Context.create_client_context()
    context.client_credentials = credentials  # 🔑 Importante: se asignan

    for _ in range(100):
        t1 = time.perf_counter()

        request = Message(code=GET, uri='coap://127.0.0.1/hola')
        try:
            response = await context.request(request).response
            # print(response.payload)  # opcional
        except Exception as e:
            print("Error:", e)
            continue

        t2 = time.perf_counter()
        latencias.append(t2 - t1)
        await asyncio.sleep(0.05)

    cpu_user_end, cpu_sys_end = process.cpu_times().user, process.cpu_times().system
    io_end = process.io_counters()
    mem_info_end = process.memory_info()

    print("\n--- Resultados ---")
    print(f"Número de solicitudes: {len(latencias)}")
    print(f"Latencia media: {statistics.mean(latencias):.4f} s")
    print(f"Desviación estándar: {statistics.stdev(latencias):.4f} s")
    print(f"CPU modo usuario: {cpu_user_end - cpu_user_start:.4f} s")
    print(f"CPU modo sistema: {cpu_sys_end - cpu_sys_start:.4f} s")
    print(f"Lecturas de disco: {io_end.read_count - io_start.read_count}")
    print(f"Escrituras de disco: {io_end.write_count - io_start.write_count}")
    print(f"Memoria residente total (RSS): {mem_info_end.rss / 1024**2:.2f} MB")

asyncio.run(run_requests())
