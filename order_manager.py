import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Order:
    """Represents a single order."""
    order_id: str
    symbol: str
    transaction_type: str  # BUY or SELL
    quantity: int
    order_type: str  # MARKET or LIMIT
    status: str = "PENDING"  # PENDING, EXECUTED, REJECTED, CANCELLED
    executed_price: float = 0.0
    executed_quantity: int = 0
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    error_message: str = ""
    
class OrderManager:
    """Manages order lifecycle, tracking, and verification."""
    
    def __init__(self, dhan_client=None):
        self.dhan_client = dhan_client
        self.orders: Dict[str, Order] = {}  # order_id -> Order
        self.stock_orders: Dict[str, List[str]] = {}  # symbol -> [order_ids]
        self.max_retries = 3
        self.retry_delay_seconds = 1
        
    def create_order(self, symbol: str, transaction_type: str, quantity: int, 
                     order_type: str = "MARKET") -> Optional[Order]:
        """Create and track a new order."""
        try:
            # Generate temporary order ID (will be replaced with actual ID from Dhan)
            temp_order_id = f"TEMP_{symbol}_{int(time.time() * 1000)}"
            
            order = Order(
                order_id=temp_order_id,
                symbol=symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type
            )
            
            self.orders[temp_order_id] = order
            
            # Track by symbol
            if symbol not in self.stock_orders:
                self.stock_orders[symbol] = []
            self.stock_orders[symbol].append(temp_order_id)
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            return None
            
    def update_order_status(self, order_id: str, status: str, 
                           executed_price: float = 0.0, 
                           executed_quantity: int = 0,
                           error_message: str = ""):
        """Update order status after execution attempt."""
        if order_id in self.orders:
            order = self.orders[order_id]
            order.status = status
            order.executed_price = executed_price
            order.executed_quantity = executed_quantity
            order.error_message = error_message
            
            logger.info(f"Order {order_id} updated: {status}")
            
    def replace_order_id(self, temp_id: str, actual_id: str):
        """Replace temporary order ID with actual ID from broker."""
        if temp_id in self.orders:
            order = self.orders.pop(temp_id)
            order.order_id = actual_id
            self.orders[actual_id] = order
            
            # Update stock_orders mapping
            symbol = order.symbol
            if symbol in self.stock_orders and temp_id in self.stock_orders[symbol]:
                idx = self.stock_orders[symbol].index(temp_id)
                self.stock_orders[symbol][idx] = actual_id
                
    def get_stock_orders(self, symbol: str) -> List[Order]:
        """Get all orders for a specific stock."""
        if symbol not in self.stock_orders:
            return []
        
        order_ids = self.stock_orders[symbol]
        return [self.orders[oid] for oid in order_ids if oid in self.orders]
        
    def get_executed_orders(self, symbol: str) -> List[Order]:
        """Get executed orders for a stock."""
        orders = self.get_stock_orders(symbol)
        return [o for o in orders if o.status == "EXECUTED"]
        
    def calculate_average_entry(self, symbol: str, transaction_type: str) -> float:
        """Calculate average entry price for a position."""
        executed_orders = [
            o for o in self.get_executed_orders(symbol)
            if o.transaction_type == transaction_type
        ]
        
        if not executed_orders:
            return 0.0
            
        total_value = sum(o.executed_price * o.executed_quantity for o in executed_orders)
        total_quantity = sum(o.executed_quantity for o in executed_orders)
        
        return total_value / total_quantity if total_quantity > 0 else 0.0
        
    def get_total_quantity(self, symbol: str, transaction_type: str) -> int:
        """Get total executed quantity for a position."""
        executed_orders = [
            o for o in self.get_executed_orders(symbol)
            if o.transaction_type == transaction_type
        ]
        
        return sum(o.executed_quantity for o in executed_orders)
        
    def should_retry_order(self, order_id: str) -> bool:
        """Check if order should be retried."""
        if order_id not in self.orders:
            return False
            
        order = self.orders[order_id]
        return (order.status == "REJECTED" and 
                order.retry_count < self.max_retries)
                
    def mark_retry(self, order_id: str):
        """Mark order as retried."""
        if order_id in self.orders:
            self.orders[order_id].retry_count += 1
            
    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders."""
        return [o for o in self.orders.values() if o.status == "PENDING"]
        
    def get_failed_orders(self) -> List[Order]:
        """Get all failed/rejected orders."""
        return [o for o in self.orders.values() if o.status == "REJECTED"]
        
    def clear_stock_orders(self, symbol: str):
        """Clear all orders for a stock (used when position is fully closed)."""
        if symbol in self.stock_orders:
            order_ids = self.stock_orders[symbol]
            for oid in order_ids:
                if oid in self.orders:
                    del self.orders[oid]
            del self.stock_orders[symbol]
            
    def get_summary(self) -> Dict:
        """Get order summary statistics."""
        total = len(self.orders)
        executed = len([o for o in self.orders.values() if o.status == "EXECUTED"])
        pending = len([o for o in self.orders.values() if o.status == "PENDING"])
        rejected = len([o for o in self.orders.values() if o.status == "REJECTED"])
        
        return {
            "total_orders": total,
            "executed": executed,
            "pending": pending,
            "rejected": rejected,
            "success_rate": (executed / total * 100) if total > 0 else 0
        }
