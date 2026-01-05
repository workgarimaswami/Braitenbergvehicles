#Plan
# Vehicle 2 – Iteration 1 (simple but working)
# -------------------------------------------
# * World:
#   - One circular light source in the middle of the window.
#   - One Vehicle 2 with two light sensors and two motors.
#
# * Behaviour:
#   - We implement **Vehicle 2a (the coward)** only.
#   - Each sensor is wired to the motor on the **same side**.
#   - Higher light intensity -> faster motor.
#   - Because of same-side wiring, the side nearer the light speeds up
#     and the vehicle curves **away** from the light.
#
# * Simplifications:
#   - Intensity is just a linear falloff with distance.
#   - Differential-drive kinematics are simplified:
#       forward_speed = (v_l + v_r) / 2
#       turn_rate      = (v_r - v_l) * TURN_GAIN
#   - We ignore real time and just use one step per frame.
#
# * What to watch:
#   - Start the vehicle somewhere near the light and angle it randomly.
#   - You should see it veer away and drift toward darker regions.
#
# * Later improvements (Iteration 2):
#   - Use inverse-square law for light.
#   - Support both Vehicle 2a (coward) and 2b (aggressive) with a key press.
#   - Make parameters (gains, max speeds, etc.) easier to tune.
#

import pygame
import math
import random

pygame.init()

# Window setup
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Braitenberg Vehicle 2a – Coward")

clock = pygame.time.Clock()
FPS = 60

font = pygame.font.SysFont("consolas", 16)


class Light:
    def __init__(self, x, y, radius=20):
        self.x = x
        self.y = y
        self.radius = radius

    def move_to(self, pos):
        # thinking: keep it super direct, the mouse click is the new center
        self.x, self.y = pos

    @property
    def pos(self):
        return (self.x, self.y)

    def draw(self, surface):
        pygame.draw.circle(surface, (255, 255, 0), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)


class VehicleTwoSimple:
    """Vehicle 2a – coward, same-side wiring, simple intensity model."""

    def __init__(self, x, y, radius=25, heading=0.0):
        self.x = x
        self.y = y
        self.radius = radius
        self.heading = heading

        # thinking: sensors slightly in front and off to the sides
        self.sensor_offset_angle = math.radians(25)
        self.sensor_distance = radius * 1.2

        # debug values
        self.left_intensity = 0.0
        self.right_intensity = 0.0
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.forward_speed = 0.0
        self.turn_rate = 0.0

        # tuning knobs
        self.MAX_INTENSITY = 1.0
        self.MAX_SENSOR_RANGE = 250.0  # beyond this, basically dark
        self.MOTOR_GAIN = 4.0          # intensity -> wheel speed
        self.TURN_GAIN = 0.06          # difference -> radians per frame

    # --- geometry helpers -------------------------------------------------

    def _sensor_positions(self):
        """Compute sensor positions in world coordinates."""
        # thinking: sensors are at ±offset, measured from heading
        a = self.sensor_offset_angle
        d = self.sensor_distance

        # local coordinates (vehicle-centric)
        left_local = (math.cos(a) * d, math.sin(a) * d)
        right_local = (math.cos(-a) * d, math.sin(-a) * d)

        # rotate + translate into world space
        ch = math.cos(self.heading)
        sh = math.sin(self.heading)

        def to_world(local):
            lx, ly = local
            wx = self.x + ch * lx - sh * ly
            wy = self.y + sh * lx + ch * ly
            return (wx, wy)

        return to_world(left_local), to_world(right_local)

    # --- sensing -----------------------------------------------------------

    def _intensity_at(self, px, py, light_pos):
        """Simple linear falloff of intensity with distance."""
        lx, ly = light_pos
        dx = lx - px
        dy = ly - py
        dist = math.hypot(dx, dy)

        # thinking: closer -> stronger, clamp nicely between 0 and 1
        if dist >= self.MAX_SENSOR_RANGE:
            return 0.0
        # invert and normalize
        return (self.MAX_SENSOR_RANGE - dist) / self.MAX_SENSOR_RANGE * self.MAX_INTENSITY

    # --- control + motion --------------------------------------------------

    def update(self, light_pos):
        # 1. sense
        left_sensor, right_sensor = self._sensor_positions()
        self.left_intensity = self._intensity_at(left_sensor[0], left_sensor[1], light_pos)
        self.right_intensity = self._intensity_at(right_sensor[0], right_sensor[1], light_pos)

        # 2. map intensity to wheel speeds (same-side wiring: coward)
        #    left sensor -> left motor, right sensor -> right motor
        self.left_speed = self.left_intensity * self.MOTOR_GAIN
        self.right_speed = self.right_intensity * self.MOTOR_GAIN

        # 3. differential drive kinematics (very lightweight)
        self.forward_speed = (self.left_speed + self.right_speed) * 0.5
        self.turn_rate = (self.right_speed - self.left_speed) * self.TURN_GAIN

        # 4. integrate motion
        self.heading += self.turn_rate
        self.x += self.forward_speed * math.cos(self.heading)
        self.y += self.forward_speed * math.sin(self.heading)

        # wrap around screen so it never disappears
        self.x %= WIDTH
        self.y %= HEIGHT

    # --- drawing -----------------------------------------------------------

    def draw(self, surface):
        # body
        pygame.draw.circle(surface, (0, 0, 255), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)

        # heading "nose"
        nose_x = self.x + math.cos(self.heading) * self.radius
        nose_y = self.y + math.sin(self.heading) * self.radius
        pygame.draw.line(surface, (0, 0, 0), (int(self.x), int(self.y)), (int(nose_x), int(nose_y)), 2)

        # sensors
        left_sensor, right_sensor = self._sensor_positions()
        pygame.draw.circle(surface, (255, 0, 0), (int(left_sensor[0]), int(left_sensor[1])), 5)
        pygame.draw.circle(surface, (255, 0, 0), (int(right_sensor[0]), int(right_sensor[1])), 5)

        # debug info
        txt1 = f"Vehicle 2a (coward) – same-side wiring"
        txt2 = f"I_L={self.left_intensity:.2f}  I_R={self.right_intensity:.2f}"
        txt3 = f"vL={self.left_speed:.2f} vR={self.right_speed:.2f}  turn={self.turn_rate:.3f}"

        surface.blit(font.render(txt1, True, (0, 0, 0)), (10, 10))
        surface.blit(font.render(txt2, True, (0, 0, 0)), (10, 30))
        surface.blit(font.render(txt3, True, (0, 0, 0)), (10, 50))


def main_simple():
    light = Light(WIDTH // 2, HEIGHT // 2, radius=25)

    # thinking: start vehicle left of the light with random heading
    vehicle = VehicleTwoSimple(WIDTH // 2 - 150, HEIGHT // 2, heading=random.uniform(-math.pi, math.pi))

    running = True
    while running:
        screen.fill((255, 255, 255))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # click to move the light, handy for live demos
            if event.type == pygame.MOUSEBUTTONDOWN:
                light.move_to(event.pos)

        light.draw(screen)
        vehicle.update(light.pos)
        vehicle.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main_simple()
