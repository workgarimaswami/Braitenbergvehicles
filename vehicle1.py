import pygame
import math

pygame.init()

# Setup Pygame window
WIDTH, HEIGHT = 500, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Vehicle 1 - Braitenberg's Simplest Agent")

clock = pygame.time.Clock()
fps = 60
font = pygame.font.SysFont("consolas", 16)


# Vehicle 1 Definition
class VehicleOne:
    def __init__(self, x, y, radius=20, heading=0):
        self.x = x
        self.y = y
        self.radius = radius
        self.heading = heading
        self.speed = 0.0
        
        # Sensor position (front center)
        self.sensor_distance = self.radius + 5
    #finds where the robot’s front sensor is located, based on how far it is in front of the robot and which way the robot is facing.
    def sensor_position(self):
        """Compute the (x,y) position of the single front sensor."""
        sx = self.x + math.cos(self.heading) * self.sensor_distance
        sy = self.y + math.sin(self.heading) * self.sensor_distance
        return sx, sy

    #function computes how bright a light appears at a sensor’s position using the inverse-square law — brightness drops rapidly as distance increases.
    def intensity_at(self, sx, sy, light_x, light_y):
        """Simple inverse-square law for light intensity."""
        dx = light_x - sx
        dy = light_y - sy
        dist_sq = dx * dx + dy * dy
        if dist_sq == 0:
            return 1.0
        return min(1.0 / dist_sq * 5000, 1.0)  # scaled

    #function updates the robot’s position and speed based on the light’s position.
    #The robot measures how bright the light is, moves faster when it’s brighter, slows down with friction, and moves forward in whatever direction it’s facing. If it leaves the screen boundaries, it wraps around to the other side.
    def update(self, light_pos):
        # Sense light intensity
        sensor_x, sensor_y = self.sensor_position()
        intensity = self.intensity_at(sensor_x, sensor_y, light_pos[0], light_pos[1])

        # Motor control: speed proportional to intensity,Adjust speed based on light brightness 
        self.speed = intensity * 5.0  # scale factor
        friction = 0.1 #Apply friction (slow it down a little)
        self.speed = max(self.speed - friction, 0)

        # Move forward in the current direction
        self.x += math.cos(self.heading) * self.speed
        self.y += math.sin(self.heading) * self.speed

        # Keep it inside the world (wrap around edges)
        self.x %= WIDTH
        self.y %= HEIGHT

    def draw(self, surface):
        # Draw the robot's body , Draws the robot’s blue circular body.
        pygame.draw.circle(surface, (0, 0, 255), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)

        # Draw sensor, Draws a red circle for the front sensor.
        sensor_x, sensor_y = self.sensor_position()
        pygame.draw.circle(surface, (255, 0, 0), (int(sensor_x), int(sensor_y)), 5)

        # Debug info, Optionally shows a text label for the robot’s current speed.
        if font:
            surface.blit(
                font.render(f"Speed={self.speed:.2f}", True, (0, 0, 0)),
                (10, 10),
            )


# Light Source, setting up the light
class Light:
    def __init__(self, x, y, radius=20):
        self.x = x
        self.y = y
        self.radius = radius
    #moving the ligth
    def move_light(self, pos):
        self.x, self.y = pos
    #Get the light's position
    def pos(self):
        return self.x, self.y
    #Draw the light on screen
    def draw(self, surface):
        pygame.draw.circle(surface, (255, 255, 0), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)


# Main Simulation
vehicle = VehicleOne(WIDTH // 4, HEIGHT // 2)
light = Light(WIDTH // 2, HEIGHT // 2)

running = True
while running:
    #Clear the screen
    screen.fill((255, 255, 255))
    #Handle user events (inputs)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # Move the light when you click
        if event.type == pygame.MOUSEBUTTONDOWN:
            light.move_light(event.pos)

    # Update and draw the simulation
    light.draw(screen)
    vehicle.update(light.pos())
    vehicle.draw(screen)

    pygame.display.flip() #Refresh the screen
    clock.tick(fps) #Control frame rate

pygame.quit()
