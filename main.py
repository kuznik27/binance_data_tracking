import asyncio
import websockets
import json
import time
import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import f_oneway, levene
from collections import defaultdict


async def subscribe_to_stream(uri, messages, stop_event):
    async with websockets.connect(uri) as websocket:
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": ["btcusdt@bookTicker"],
            "id": 1
        }
        await websocket.send(json.dumps(subscribe_message))

        while not stop_event.is_set():
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                message = json.loads(response)
                if 'u' in message:
                    print(message)
                    current_time = time.time()
                    messages.append((message, current_time))
            except asyncio.TimeoutError:
                continue


async def collect_data():
    uri = "wss://fstream.binance.com/ws"
    num_connections = 5
    messages = [[] for _ in range(num_connections)]
    stop_event = asyncio.Event()

    tasks = [subscribe_to_stream(uri, messages[i], stop_event) for i in range(num_connections)]

    # Запускаем задачи
    running_tasks = [asyncio.create_task(task) for task in tasks]

    # Ждем 60 секунд
    await asyncio.sleep(60)

    # Устанавливаем событие остановки
    stop_event.set()

    # Ожидаем завершения всех задач
    await asyncio.gather(*running_tasks, return_exceptions=True)

    return messages


data = asyncio.run(collect_data())


def calculate_delays(messages):
    delays = []
    for conn_messages in messages:
        conn_delays = [(recv_time - msg['E'] / 1000) for msg, recv_time in conn_messages]
        delays.append(conn_delays)
    return delays


def calculate_fast_updates(messages):
    update_id_tracker = defaultdict(list)
    for conn_index, conn_messages in enumerate(messages):
        for msg, recv_time in conn_messages:
            update_id = msg['u']
            update_id_tracker[update_id].append((recv_time, conn_index))

    first_update_counts = [0] * len(messages)
    for update_id, recv_times in update_id_tracker.items():
        first_update = min(recv_times, key=lambda x: x[0])
        first_update_counts[first_update[1]] += 1

    total_updates = sum(first_update_counts)
    fast_update_ratios = [count / total_updates for count in first_update_counts]

    return fast_update_ratios


def plot_delays(delays):
    plt.figure(figsize=(14, 7))
    colors = ['b', 'g', 'r', 'c', 'm']  # список цветов для каждого коннекшена

    for i, conn_delays in enumerate(delays):
        plt.hist(conn_delays, bins=50, alpha=0.5, label=f'Connection {i + 1}', color=colors[i])

    plt.xlabel('Delay (seconds)')
    plt.ylabel('Frequency')
    plt.legend()
    plt.title('Distribution of Delays for Each Connection')
    plt.show()


delays = calculate_delays(data)
plot_delays(delays)


def analyze_delays(delays):
    means = [np.mean(conn_delays) for conn_delays in delays]
    stds = [np.std(conn_delays) for conn_delays in delays]
    print("Means of delays:", means)
    print("Standard deviations of delays:", stds)

    # ANOVA test
    f_stat, p_val = f_oneway(*delays)
    print(f'ANOVA test: f-stat={f_stat}, p-value={p_val}')

    # Levene test
    w_stat, p_val = levene(*delays)
    print(f'Levene test: w-stat={w_stat}, p-value={p_val}')


analyze_delays(delays)

fast_update_ratios = calculate_fast_updates(data)
print("Fast update ratios for each connection:", fast_update_ratios)