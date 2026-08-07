import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

class ChartCollector:
    """
    Сборщик данных для графиков (зрители, подписчики и т.п.)
    """
    def __init__(self, get_value_func, socketio, interval=10, max_points=200, event_name='chart_update'):
        self.get_value_func = get_value_func
        self.socketio = socketio
        self.interval = interval
        self.max_points = max_points
        self.event_name = event_name
        self.data = []  # list of {'timestamp': str, 'value': int}
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._collect, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None

    def set_interval(self, interval):
        if interval != self.interval:
            self.interval = interval
            if self.running:
                self.stop()
                self.start()

    def _collect(self):
        while self.running:
            try:
                value = self.get_value_func()
            except Exception:
                value = 0
            point = {
                'timestamp': datetime.now().isoformat(),
                'value': value
            }
            self.data.append(point)
            if len(self.data) > self.max_points:
                self.data = self.data[-self.max_points:]
            if self.socketio:
                self.socketio.emit(self.event_name, point)
            time.sleep(self.interval)

    def get_data(self):
        return self.data

    def clear(self):
        self.data.clear()