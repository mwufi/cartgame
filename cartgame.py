import pygame
import time
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Initialize Pygame
pygame.init()
pygame.font.init()

# Constants
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900
CART_SIZE = 40
STATION_SIZE = 80
MINE_SIZE = 60
MARKET_SIZE = 60

# Add new constants for price history
PRICE_HISTORY_LENGTH = 50
PRICE_GRAPH_WIDTH = 180
PRICE_GRAPH_HEIGHT = 100

# Add new constant for price momentum
PRICE_MOMENTUM_FACTOR = 0.7  # Higher = more momentum
PRICE_VOLATILITY = 0.03  # Reduced from 0.1

# Add at the top with other constants
POSITION_TOLERANCE = 10  # pixels of tolerance for position checks

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BROWN = (139, 69, 19)
GOLD = (255, 215, 0)


@dataclass
class Resource:
    name: str
    base_value: float
    rarity: float
    color: Tuple[int, int, int]


@dataclass
class Cart:
    x: float
    y: float
    capacity: int
    speed: float
    mining_speed: float
    contents: Dict[str, int]
    cart_type: str  # 'mining' or 'market'
    state: str  # 'mining'/'returning' for mining carts, 'loading'/'selling' for market carts

    def is_full(self) -> bool:
        return sum(self.contents.values()) >= self.capacity

    def get_contents_amount(self) -> int:
        return sum(self.contents.values())


class Station:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.storage = {"iron": 0, "copper": 0, "gold": 0}
        self.processing_speed = 1.0
        self.storage_capacity = 1000
        self.money = 1000

        self.upgrade_costs = {
            "capacity": 1000,
            "speed": 1500,
            "mining": 2000,
            "processing": 2500,
            "storage": 3000,
        }
        self.upgrade_multipliers = {
            "capacity": 1.5,
            "speed": 1.3,
            "mining": 1.4,
            "processing": 1.2,
            "storage": 2.0,
        }


class MiningGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Mining Station Idle Game")

        # HUD colors and styling
        self.hud_colors = {
            'background': (40, 44, 52),
            'panel': (30, 33, 39),
            'text': (200, 200, 200),
            'highlight': (97, 175, 239),
            'button': (55, 60, 70),
            'button_hover': (70, 75, 85)
        }

        # Fonts
        self.font = pygame.font.SysFont("Arial", 16)
        self.cart_font = pygame.font.SysFont("Arial", 12)  # Smaller font for cart numbers
        self.large_font = pygame.font.SysFont("Arial", 24)

        # Game elements positions
        self.mine_pos = (100, SCREEN_HEIGHT // 2)
        self.station_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.market_pos = (SCREEN_WIDTH - 100, SCREEN_HEIGHT // 2)

        # Initialize game objects
        self.resources = {
            "iron": Resource("Iron", 10, 0.8, GRAY),
            "copper": Resource("Copper", 15, 0.6, (184, 115, 51)),
            "gold": Resource("Gold", 50, 0.2, GOLD),
        }

        self.station = Station(self.station_pos[0], self.station_pos[1])

        # Add global cart stats that apply to all carts (including future ones)
        self.cart_stats = {
            "capacity": 50,
            "speed": 100,
            "mining": 3.0,
        }

        # Initialize first cart using global stats
        self.carts = [
            Cart(
                x=self.station_pos[0],
                y=self.station_pos[1],
                capacity=self.cart_stats["capacity"],
                speed=self.cart_stats["speed"],
                mining_speed=self.cart_stats["mining"],
                contents={},
                cart_type="mining",
                state="mining",
            )
        ]

        self.market_prices = {r: res.base_value for r, res in self.resources.items()}
        self.last_update = time.time()

        # Button areas
        self.buttons = {
            "new_mining_cart": pygame.Rect(10, 10, 150, 30),
            "new_market_cart": pygame.Rect(10, 50, 150, 30),
            "convert_to_mining": pygame.Rect(10, 90, 150, 30),
            "convert_to_market": pygame.Rect(10, 130, 150, 30),
            "upgrade_capacity": pygame.Rect(10, 170, 150, 30),
            "upgrade_speed": pygame.Rect(10, 210, 150, 30),
            "upgrade_mining": pygame.Rect(10, 250, 150, 30),
        }

        # Add price volatility
        self.price_volatility = 0.1
        self.last_price_update = time.time()
        self.price_update_interval = 5.0  # seconds

        # Add resource icons
        self.resource_icons = {
            "iron": self.create_resource_icon(GRAY, "Fe"),
            "copper": self.create_resource_icon((184, 115, 51), "Cu"),
            "gold": self.create_resource_icon(GOLD, "Au")
        }

        # Add price history tracking
        self.price_history = {
            resource: [price] * PRICE_HISTORY_LENGTH 
            for resource, price in self.market_prices.items()
        }

        # Add price momentum tracking
        self.price_momentum = {resource: 0.0 for resource in self.resources}
        
        # Add resource selling toggles
        self.resource_selling_enabled = {resource: True for resource in self.resources}

        # Modify buttons dictionary to include resource toggles
        self.buttons.update({
            f"toggle_{resource}": pygame.Rect(10, 290 + i * 40, 150, 30)
            for i, resource in enumerate(self.resources)
        })

    def create_resource_icon(self, color, symbol, size=20):
        surface = pygame.Surface((size, size))
        surface.fill(self.hud_colors['background'])
        
        # Draw circular background
        pygame.draw.circle(surface, color, (size//2, size//2), size//2)
        
        # Add chemical symbol
        font = pygame.font.SysFont("Arial", size//2, bold=True)
        text = font.render(symbol, True, BLACK)
        text_rect = text.get_rect(center=(size//2, size//2))
        surface.blit(text, text_rect)
        
        return surface

    def update_market_prices(self):
        current_time = time.time()
        if current_time - self.last_price_update >= self.price_update_interval:
            for resource in self.market_prices:
                # Apply momentum-based price changes
                random_force = random.uniform(-PRICE_VOLATILITY, PRICE_VOLATILITY)
                self.price_momentum[resource] = (
                    self.price_momentum[resource] * PRICE_MOMENTUM_FACTOR + 
                    random_force * (1 - PRICE_MOMENTUM_FACTOR)
                )
                
                # Update price based on momentum
                base_price = self.resources[resource].base_value
                current_price = self.market_prices[resource]
                new_price = current_price * (1 + self.price_momentum[resource])
                
                # Keep prices within reasonable bounds
                self.market_prices[resource] = max(
                    base_price * 0.5, 
                    min(base_price * 2.0, new_price)
                )
                
                # Update price history
                self.price_history[resource].pop(0)
                self.price_history[resource].append(self.market_prices[resource])
            
            self.last_price_update = current_time

    def update(self):
        current_time = time.time()
        delta_time = current_time - self.last_update
        self.last_update = current_time

        self.update_market_prices()

        for i, cart in enumerate(self.carts):
            vertical_offset = i * 5

            if cart.cart_type == "mining":
                self.update_mining_cart(cart, vertical_offset, delta_time)
            else:  # market cart
                self.update_market_cart(cart, vertical_offset, delta_time)

    def update_mining_cart(self, cart, vertical_offset, delta_time):
        if cart.state == "mining":
            # Move to mine
            dx = self.mine_pos[0] - cart.x
            dy = self.mine_pos[1] - cart.y + vertical_offset
            dist = (dx**2 + dy**2) ** 0.5

            if dist < POSITION_TOLERANCE:  # Increased tolerance
                if not cart.is_full():
                    # Mining logic
                    for resource_name, resource in self.resources.items():
                        if random.random() < resource.rarity * cart.mining_speed * delta_time * 2:
                            cart.contents[resource_name] = cart.contents.get(resource_name, 0) + 1

                if cart.is_full():
                    cart.state = "returning"
                    # Snap to exact position when changing state
                    cart.x = self.mine_pos[0]
                    cart.y = self.mine_pos[1] + vertical_offset
            else:
                # Move towards mine
                cart.x += (dx / dist) * cart.speed * delta_time
                cart.y += (dy / dist) * cart.speed * delta_time

        elif cart.state == "returning":
            # Move to station
            dx = self.station_pos[0] - cart.x
            dy = self.station_pos[1] - cart.y + vertical_offset
            dist = (dx**2 + dy**2) ** 0.5

            if dist < POSITION_TOLERANCE:  # Increased tolerance
                self.transfer_to_station(cart)
                cart.state = "mining"
                # Snap to exact position when changing state
                cart.x = self.station_pos[0]
                cart.y = self.station_pos[1] + vertical_offset
            else:
                cart.x += (dx / dist) * cart.speed * delta_time
                cart.y += (dy / dist) * cart.speed * delta_time

    def update_market_cart(self, cart, vertical_offset, delta_time):
        if cart.state == "loading":
            dx = self.station_pos[0] - cart.x
            dy = self.station_pos[1] - cart.y + vertical_offset
            dist = (dx**2 + dy**2) ** 0.5

            if dist < POSITION_TOLERANCE:  # Increased tolerance
                if self.load_from_station(cart):
                    cart.state = "selling"
                    # Snap to exact position when changing state
                    cart.x = self.station_pos[0]
                    cart.y = self.station_pos[1] + vertical_offset
            else:
                cart.x += (dx / dist) * cart.speed * delta_time
                cart.y += (dy / dist) * cart.speed * delta_time

        elif cart.state == "selling":
            dx = self.market_pos[0] - cart.x
            dy = self.market_pos[1] - cart.y + vertical_offset
            dist = (dx**2 + dy**2) ** 0.5

            if dist < POSITION_TOLERANCE:  # Increased tolerance
                self.sell_cart_resources(cart)
                cart.state = "loading"
                # Snap to exact position when changing state
                cart.x = self.market_pos[0]
                cart.y = self.market_pos[1] + vertical_offset
            else:
                cart.x += (dx / dist) * cart.speed * delta_time
                cart.y += (dy / dist) * cart.speed * delta_time

    def transfer_to_station(self, cart):
        for resource_name, amount in cart.contents.items():
            transfer_amount = min(
                amount, 
                self.station.storage_capacity - sum(self.station.storage.values())
            )
            if transfer_amount > 0:
                self.station.storage[resource_name] = (
                    self.station.storage.get(resource_name, 0) + transfer_amount
                )
                cart.contents[resource_name] = 0

    def load_from_station(self, cart):
        if cart.is_full():
            return False

        space_left = cart.capacity - cart.get_contents_amount()
        loaded_something = False

        # Only load enabled resources
        for resource, amount in self.station.storage.items():
            if amount > 0 and self.resource_selling_enabled[resource]:
                transfer_amount = min(amount, space_left)
                cart.contents[resource] = cart.contents.get(resource, 0) + transfer_amount
                self.station.storage[resource] -= transfer_amount
                space_left -= transfer_amount
                loaded_something = True

            if space_left <= 0:
                break

        return loaded_something

    def sell_cart_resources(self, cart):
        for resource_name, amount in cart.contents.items():
            if amount > 0:
                sale_price = self.market_prices[resource_name] * amount
                self.station.money += sale_price
                cart.contents[resource_name] = 0

    def draw_gradient_rect(self, surface, color, rect, direction="vertical"):
        """Draw a rectangle with a gradient effect"""
        if direction == "vertical":
            for i in range(rect[3]):
                alpha = int(255 * (1 - i/rect[3] * 0.5))  # 50% darker at bottom
                current_color = (
                    min(255, int(color[0] * alpha/255)),
                    min(255, int(color[1] * alpha/255)),
                    min(255, int(color[2] * alpha/255))
                )
                pygame.draw.line(surface, current_color, 
                               (rect[0], rect[1] + i),
                               (rect[0] + rect[2], rect[1] + i))

    def draw_price_graph(self, surface, x, y, resource):
        """Draw price history graph for a resource"""
        # Draw graph background
        graph_rect = pygame.Rect(x, y, PRICE_GRAPH_WIDTH, PRICE_GRAPH_HEIGHT)
        pygame.draw.rect(surface, self.hud_colors['panel'], graph_rect)
        pygame.draw.rect(surface, self.hud_colors['highlight'], graph_rect, 1)

        # Calculate min and max prices for scaling
        prices = self.price_history[resource]
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price or 1

        # Draw price line
        points = []
        for i, price in enumerate(prices):
            point_x = x + (i * PRICE_GRAPH_WIDTH // PRICE_HISTORY_LENGTH)
            point_y = y + PRICE_GRAPH_HEIGHT - int((price - min_price) / price_range * PRICE_GRAPH_HEIGHT)
            points.append((point_x, point_y))

        if len(points) > 1:
            pygame.draw.lines(surface, self.resources[resource].color, False, points, 2)

    def draw(self):
        self.screen.fill(self.hud_colors['background'])

        # Draw main game area
        game_area = pygame.Surface((SCREEN_WIDTH - 220, SCREEN_HEIGHT - 20))
        game_area.fill(WHITE)

        # Draw mine with gradient
        mine_rect = (
            self.mine_pos[0] - MINE_SIZE // 2 - 10,
            self.mine_pos[1] - MINE_SIZE // 2 - 10,
            MINE_SIZE,
            MINE_SIZE
        )
        self.draw_gradient_rect(game_area, BROWN, mine_rect)
        mine_text = self.font.render("MINE", True, WHITE)
        text_rect = mine_text.get_rect(center=(self.mine_pos[0] - 10, self.mine_pos[1] - 10))
        game_area.blit(mine_text, text_rect)

        # Draw station with gradient
        station_rect = (
            self.station_pos[0] - STATION_SIZE // 2 - 10,
            self.station_pos[1] - STATION_SIZE // 2 - 10,
            STATION_SIZE,
            STATION_SIZE
        )
        self.draw_gradient_rect(game_area, BLUE, station_rect)
        station_text = self.font.render("STATION", True, WHITE)
        text_rect = station_text.get_rect(center=(self.station_pos[0] - 10, self.station_pos[1] - 10))
        game_area.blit(station_text, text_rect)

        # Draw market with gradient
        market_rect = (
            self.market_pos[0] - MARKET_SIZE // 2 - 10,
            self.market_pos[1] - MARKET_SIZE // 2 - 10,
            MARKET_SIZE,
            MARKET_SIZE
        )
        self.draw_gradient_rect(game_area, GREEN, market_rect)
        market_text = self.font.render("MARKET", True, WHITE)
        text_rect = market_text.get_rect(center=(self.market_pos[0] - 10, self.market_pos[1] - 10))
        game_area.blit(market_text, text_rect)

        # Draw carts with gradient
        for cart in self.carts:
            cart_color = RED if cart.is_full() else BLACK
            cart_rect = (
                cart.x - CART_SIZE // 2 - 10,
                cart.y - CART_SIZE // 2 - 10,
                CART_SIZE,
                CART_SIZE
            )
            self.draw_gradient_rect(game_area, cart_color, cart_rect)

            # Display contents with icons
            if cart.contents:
                y_offset = 0
                for resource, amount in cart.contents.items():
                    if amount > 0:
                        scaled_icon = pygame.transform.scale(self.resource_icons[resource], (15, 15))
                        game_area.blit(
                            scaled_icon, 
                            (cart.x - CART_SIZE//2 - 10, cart.y - CART_SIZE//2 - 10 + y_offset)
                        )
                        amount_text = self.cart_font.render(str(amount), True, WHITE)
                        game_area.blit(
                            amount_text, 
                            (cart.x - CART_SIZE//2 + 8, cart.y - CART_SIZE//2 - 10 + y_offset)
                        )
                        y_offset += 15

        # Blit game_area onto main screen
        self.screen.blit(game_area, (10, 10))

        # Draw side panel
        panel_rect = pygame.Rect(SCREEN_WIDTH - 200, 10, 190, SCREEN_HEIGHT - 20)
        pygame.draw.rect(self.screen, self.hud_colors['panel'], panel_rect)
        pygame.draw.rect(self.screen, self.hud_colors['highlight'], panel_rect, 1)

        # Draw stats with improved styling
        y_offset = 20
        title_font = pygame.font.SysFont("Arial", 20, bold=True)
        
        # Money display
        money_text = title_font.render(f"${self.station.money:.0f}", True, self.hud_colors['highlight'])
        self.screen.blit(money_text, (SCREEN_WIDTH - 190, y_offset))
        
        y_offset += 40

        # Storage display with icons
        storage_title = title_font.render("Storage", True, self.hud_colors['text'])
        self.screen.blit(storage_title, (SCREEN_WIDTH - 190, y_offset))
        y_offset += 30

        for resource, amount in self.station.storage.items():
            # Draw resource icon
            self.screen.blit(self.resource_icons[resource], (SCREEN_WIDTH - 190, y_offset))
            
            # Draw amount
            resource_text = self.font.render(f": {amount}", True, self.hud_colors['text'])
            self.screen.blit(resource_text, (SCREEN_WIDTH - 165, y_offset + 2))
            
            y_offset += 25

        # Market prices
        y_offset += 20
        price_title = title_font.render("Market Prices", True, self.hud_colors['text'])
        self.screen.blit(price_title, (SCREEN_WIDTH - 190, y_offset))
        y_offset += 30

        for resource, price in self.market_prices.items():
            # Draw resource icon
            self.screen.blit(self.resource_icons[resource], (SCREEN_WIDTH - 190, y_offset))
            
            # Draw price with trend indicator
            price_text = self.font.render(f": ${price:.2f}", True, self.hud_colors['text'])
            self.screen.blit(price_text, (SCREEN_WIDTH - 165, y_offset + 2))
            
            y_offset += 25

        # Draw price graphs
        y_offset += 40
        graph_title = title_font.render("Price History", True, self.hud_colors['text'])
        self.screen.blit(graph_title, (SCREEN_WIDTH - 190, y_offset))
        y_offset += 30

        for resource in self.resources:
            self.draw_price_graph(self.screen, SCREEN_WIDTH - 190, y_offset, resource)
            y_offset += PRICE_GRAPH_HEIGHT + 10

        # Draw buttons with improved styling
        for name, rect in self.buttons.items():
            mouse_pos = pygame.mouse.get_pos()
            button_color = self.hud_colors['button_hover'] if rect.collidepoint(mouse_pos) else self.hud_colors['button']
            
            pygame.draw.rect(self.screen, button_color, rect)
            pygame.draw.rect(self.screen, self.hud_colors['highlight'], rect, 1)
            
            # Button title
            text = self.font.render(name.replace("_", " ").title(), True, self.hud_colors['text'])
            self.screen.blit(text, (rect.x + 5, rect.y + 2))

            # Cost and effect
            if "new" in name:
                cost_text = self.cart_font.render(f"Cost: ${500}", True, self.hud_colors['highlight'])
                self.screen.blit(cost_text, (rect.x + 5, rect.y + 18))
            elif "upgrade" in name:
                # Extract the upgrade type (everything after "upgrade_")
                upgrade_type = name.replace("upgrade_", "")
                
                # Get cost and multiplier
                cost = self.station.upgrade_costs.get(upgrade_type)
                multiplier = self.station.upgrade_multipliers.get(upgrade_type, 1)
                
                # Show current and next values for cart stats
                if upgrade_type in self.cart_stats:
                    current_value = self.cart_stats[upgrade_type]
                    next_value = current_value * multiplier
                    
                    if upgrade_type == "capacity":
                        value_text = f"{int(current_value)} → {int(next_value)}"
                    else:
                        value_text = f"{current_value:.1f} → {next_value:.1f}"
                    
                    cost_text = self.cart_font.render(
                        f"Cost: ${cost:,d} ({value_text})", 
                        True, 
                        self.hud_colors['highlight']
                    )
                else:
                    cost_text = self.cart_font.render(
                        f"Cost: ${cost:,d} (+{(multiplier-1)*100:.0f}%)", 
                        True, 
                        self.hud_colors['highlight']
                    )
                self.screen.blit(cost_text, (rect.x + 5, rect.y + 18))

        # Draw resource toggle buttons
        for resource in self.resources:
            button_rect = self.buttons[f"toggle_{resource}"]
            enabled = self.resource_selling_enabled[resource]
            
            # Draw button with enabled/disabled state
            button_color = (
                self.hud_colors['highlight'] if enabled 
                else self.hud_colors['button']
            )
            pygame.draw.rect(self.screen, button_color, button_rect)
            pygame.draw.rect(self.screen, self.hud_colors['highlight'], button_rect, 1)
            
            # Draw resource icon and text
            self.screen.blit(self.resource_icons[resource], (button_rect.x + 5, button_rect.y + 5))
            text = self.font.render(
                f"Sell {resource.title()}: {'ON' if enabled else 'OFF'}", 
                True, 
                self.hud_colors['text']
            )
            self.screen.blit(text, (button_rect.x + 25, button_rect.y + 5))

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()

                    # Check button clicks
                    if self.buttons["new_mining_cart"].collidepoint(mouse_pos):
                        self.add_cart("mining")
                    elif self.buttons["new_market_cart"].collidepoint(mouse_pos):
                        self.add_cart("market")
                    elif self.buttons["convert_to_mining"].collidepoint(mouse_pos):
                        self.convert_to_mining()
                    elif self.buttons["convert_to_market"].collidepoint(mouse_pos):
                        self.convert_to_market()
                    elif self.buttons["upgrade_capacity"].collidepoint(mouse_pos):
                        self.upgrade("capacity")
                    elif self.buttons["upgrade_speed"].collidepoint(mouse_pos):
                        self.upgrade("speed")
                    elif self.buttons["upgrade_mining"].collidepoint(mouse_pos):
                        self.upgrade("mining")

                    # Check resource toggle buttons
                    for resource in self.resources:
                        if self.buttons[f"toggle_{resource}"].collidepoint(mouse_pos):
                            self.resource_selling_enabled[resource] = not self.resource_selling_enabled[resource]

            self.update()
            self.draw()

            # Cap at 60 FPS
            pygame.time.Clock().tick(60)

        pygame.quit()

    def add_cart(self, cart_type: str):
        cart_cost = 500
        if self.station.money >= cart_cost:
            self.station.money -= cart_cost
            self.carts.append(
                Cart(
                    x=self.station_pos[0],
                    y=self.station_pos[1],
                    capacity=self.cart_stats["capacity"],  # Use global stats
                    speed=self.cart_stats["speed"],
                    mining_speed=self.cart_stats["mining"],
                    contents={},
                    cart_type=cart_type,
                    state="mining" if cart_type == "mining" else "loading"
                )
            )
            return True
        return False

    def convert_to_mining(self):
        market_carts = [cart for cart in self.carts if cart.cart_type == "market"]
        if market_carts:
            cart = market_carts[0]
            cart.cart_type = "mining"
            cart.state = "mining"
            cart.contents = {}  # Clear contents when converting

    def convert_to_market(self):
        mining_carts = [cart for cart in self.carts if cart.cart_type == "mining"]
        if mining_carts:
            cart = mining_carts[0]
            cart.cart_type = "market"
            cart.state = "loading"
            cart.contents = {}  # Clear contents when converting

    def upgrade(self, upgrade_type: str):
        # Get the cost for this upgrade type
        cost = self.station.upgrade_costs.get(upgrade_type)
        if cost is None:
            print(f"Warning: No cost found for upgrade type {upgrade_type}")
            return False

        if self.station.money >= cost:
            self.station.money -= cost

            multiplier = self.station.upgrade_multipliers[upgrade_type]
            
            # Update global stats and all existing carts
            if upgrade_type in self.cart_stats:
                old_value = self.cart_stats[upgrade_type]
                new_value = old_value * multiplier
                self.cart_stats[upgrade_type] = new_value
                
                # Update all existing carts
                for cart in self.carts:
                    if upgrade_type == "capacity":
                        cart.capacity = int(new_value)
                    elif upgrade_type == "speed":
                        cart.speed = new_value
                    elif upgrade_type == "mining":
                        cart.mining_speed = new_value

            # Increase the cost for next upgrade
            self.station.upgrade_costs[upgrade_type] = int(cost * 1.5)
            return True
        return False


if __name__ == "__main__":
    game = MiningGame()
    game.run()
