import time
import logging
import psutil
from collections import deque
from typing import Dict, List
import asyncio

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitors and tracks performance metrics for low-latency trading."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.tick_latencies = deque(maxlen=1000)  # Last 1000 tick latencies
        self.order_latencies = deque(maxlen=100)  # Last 100 order latencies
        self.tick_count = 0
        self.order_count = 0
        self.start_time = time.time()
        self.last_tick_time = time.time()
        
    def record_tick_latency(self, latency_ms: float):
        """Record tick processing latency in milliseconds."""
        if not self.enabled:
            return
        self.tick_latencies.append(latency_ms)
        self.tick_count += 1
        self.last_tick_time = time.time()
        
    def record_order_latency(self, latency_ms: float):
        """Record order execution latency in milliseconds."""
        if not self.enabled:
            return
        self.order_latencies.append(latency_ms)
        self.order_count += 1
        
    def get_tick_stats(self) -> Dict:
        """Get tick processing statistics."""
        if not self.tick_latencies:
            return {
                "avg_latency_ms": 0,
                "min_latency_ms": 0,
                "max_latency_ms": 0,
                "tick_rate": 0
            }
        
        latencies = list(self.tick_latencies)
        tick_rate = self.tick_count / max(1, time.time() - self.start_time)
        
        return {
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "tick_rate": tick_rate,
            "total_ticks": self.tick_count
        }
        
    def get_order_stats(self) -> Dict:
        """Get order execution statistics."""
        if not self.order_latencies:
            return {
                "avg_latency_ms": 0,
                "min_latency_ms": 0,
                "max_latency_ms": 0,
                "total_orders": 0
            }
        
        latencies = list(self.order_latencies)
        
        return {
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "total_orders": self.order_count
        }
        
    def get_system_stats(self) -> Dict:
        """Get system resource usage."""
        process = psutil.Process()
        
        return {
            "cpu_percent": process.cpu_percent(interval=0.1),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "threads": process.num_threads()
        }
        
    def get_all_metrics(self) -> Dict:
        """Get all performance metrics."""
        return {
            "tick_stats": self.get_tick_stats(),
            "order_stats": self.get_order_stats(),
            "system_stats": self.get_system_stats(),
            "uptime_seconds": time.time() - self.start_time
        }
        
    def log_metrics(self):
        """Log current performance metrics."""
        if not self.enabled:
            return
            
        metrics = self.get_all_metrics()
        logger.info(
            f"Performance Metrics - "
            f"Tick Avg: {metrics['tick_stats']['avg_latency_ms']:.2f}ms, "
            f"Order Avg: {metrics['order_stats']['avg_latency_ms']:.2f}ms, "
            f"CPU: {metrics['system_stats']['cpu_percent']:.1f}%, "
            f"Memory: {metrics['system_stats']['memory_mb']:.1f}MB"
        )
        
    async def periodic_logging(self, interval_seconds: int = 60):
        """Periodically log performance metrics."""
        while True:
            await asyncio.sleep(interval_seconds)
            self.log_metrics()

# Global instance
perf_monitor = PerformanceMonitor()
