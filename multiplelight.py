import pygame
import math
import random
pygame.init()

# Setup Pygame window
WIDTH, HEIGHT = 600, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Vehicle 1 - Multi-Light & Randomness")

clock = pygame.time.Clock()
fps = 60
font = pygame.font.SysFont("consolas", 16)


# Vehicle Definition
class VehicleOne:
    def __init__(self, x, y, radius=20, heading=0):
        self.x = x
        self.y = y
        self.radius = radius
        self.heading = heading
        self.speed = 0.0
        self.sensor_distance = self.radius + 5

    def sensor_position(self):
        sx = self.x + math.cos(self.heading) * self.sensor_distance
        sy = self.y + math.sin(self.heading) * self.sensor_distance
        return sx, sy

    def intensity_at(self, sx, sy, light_x, light_y):
        dx = light_x - sx
        dy = light_y - sy
        dist_sq = dx * dx + dy * dy
        if dist_sq == 0:
            return 1.0
        return min(1.0 / dist_sq * 5000, 1.0)

    def update(self, lights):
        sensor_x, sensor_y = self.sensor_position()

        # Sum light intensity from all sources
        total_intensity = 0
        for light in lights:
            total_intensity += self.intensity_at(sensor_x, sensor_y, light.x, light.y)
        total_intensity = min(total_intensity, 1.0)

        # Motor control
        self.speed = total_intensity * 5.0
        friction = 0.1
        self.speed = max(self.speed - friction, 0)

        # Random heading jitter
        self.heading += random.uniform(-0.05, 0.05)

        # Move forward
        self.x += math.cos(self.heading) * self.speed
        self.y += math.sin(self.heading) * self.speed

        # Wrap around screen
        self.x %= WIDTH
        self.y %= HEIGHT

    def draw(self, surface):
        pygame.draw.circle(surface, (0, 0, 255), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)

        sensor_x, sensor_y = self.sensor_position()
        pygame.draw.circle(surface, (255, 0, 0), (int(sensor_x), int(sensor_y)), 5)

        if font:
            surface.blit(
                font.render(f"Speed={self.speed:.2f}", True, (0, 0, 0)),
                (10, 10),
            )
# Light Source
class Light:
    def __init__(self, x, y, radius=20):
        self.x = x
        self.y = y
        self.radius = radius

    def move_light(self, pos):
        self.x, self.y = pos

    def pos(self):
        return self.x, self.y

    def draw(self, surface):
        pygame.draw.circle(surface, (255, 255, 0), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)

# Main Simulation
vehicle = VehicleOne(WIDTH // 4, HEIGHT // 2)
# Initial lights
lights = [
    Light(WIDTH // 2, HEIGHT // 2),
    Light(WIDTH // 3, HEIGHT // 3),
]

running = True
while running:
    screen.fill((255, 255, 255))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Left-click: add light
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            lights.append(Light(event.pos[0], event.pos[1]))

        # Right-click: remove nearest light
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if lights:
                mx, my = event.pos
                nearest = min(lights, key=lambda l: (l.x - mx)**2 + (l.y - my)**2)
                lights.remove(nearest)

    # Draw lights
    for light in lights:
        light.draw(screen)

    # Update and draw vehicle
    vehicle.update(lights)
    vehicle.draw(screen)

    pygame.display.flip()
    clock.tick(fps)

pygame.quit()
