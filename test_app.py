"""
Sample application to test Function Flow Analyzer
"""

def calculate_total(items):
    """Calculate total price"""
    total = 0
    for item in items:
        total += get_item_price(item)
    return apply_discount(total)

def get_item_price(item):
    """Get price for item"""
    base_price = fetch_base_price(item)
    return base_price * 1.1  # Add tax

def fetch_base_price(item):
    """Fetch base price from database"""
    prices = {"apple": 1.5, "banana": 0.8, "orange": 2.0}
    return prices.get(item, 1.0)

def apply_discount(amount):
    """Apply discount to amount"""
    if amount > 10:
        return amount * 0.9
    return amount

async def process_order(order_id):
    """Async function to process order"""
    order = await fetch_order(order_id)
    total = calculate_total(order['items'])
    await send_confirmation(order_id, total)
    return total

async def fetch_order(order_id):
    """Fetch order from API"""
    return {"id": order_id, "items": ["apple", "banana"]}

async def send_confirmation(order_id, total):
    """Send order confirmation"""
    print(f"Order {order_id} confirmed: ${total:.2f}")

class ShoppingCart:
    """Shopping cart manager"""
    
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        """Add item to cart"""
        self.items.append(item)
        self.update_display()
    
    def update_display(self):
        """Update cart display"""
        total = calculate_total(self.items)
        print(f"Cart total: ${total:.2f}")
    
    def checkout(self):
        """Checkout cart"""
        if validate_cart(self.items):
            return calculate_total(self.items)
        return 0

def validate_cart(items):
    """Validate cart items"""
    return len(items) > 0

if __name__ == "__main__":
    cart = ShoppingCart()
    cart.add_item("apple")
    cart.add_item("banana")
    print(f"Final: ${cart.checkout():.2f}")
