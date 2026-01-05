import pygame
import math
import random

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Braitenberg Vehicles 3 Only (multi lights)")

clock = pygame.time.Clock()
FPS = 60

font = pygame.font.SysFont("consolas", 16)

class Light:
    def __init__(self, x, y, radius=20):
        self.x = x
        self.y = y
        self.radius = radius

    def move_to(self, pos):
        self.x, self.y = pos

    @property
    def pos(self):
        return (self.x, self.y)

    def draw(self, surface):
        pygame.draw.circle(surface, (255, 255, 0), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)


class LightManager:
    """Helper class to manage multiple steady light sources."""

    def __init__(self):
        self.lights = []
        self.reset_defaults()

    def reset_defaults(self):
        self.lights.clear()
        cx, cy = WIDTH // 2, HEIGHT // 2
        spread = 150
        # four default lights around the center
        self.lights.append(Light(cx - spread, cy))
        self.lights.append(Light(cx + spread, cy))
        self.lights.append(Light(cx, cy - spread))
        self.lights.append(Light(cx, cy + spread))

    def add_light_at(self, x, y, radius=20):
        self.lights.append(Light(x, y, radius))

    def add_random_light(self, radius=20):
        x = random.randint(50, WIDTH - 50)
        y = random.randint(50, HEIGHT - 50)
        self.add_light_at(x, y, radius)

    def move_nearest(self, x, y, threshold_factor=2.0):
        if not self.lights:
            return False
        nearest = min(self.lights, key=lambda L: (L.x - x) ** 2 + (L.y - y) ** 2)
        dist_sq = (nearest.x - x) ** 2 + (nearest.y - y) ** 2
        if dist_sq <= (nearest.radius * threshold_factor) ** 2:
            nearest.move_to((x, y))
            return True
        return False

    def remove_nearest(self, x, y, threshold_factor=2.0):
        if not self.lights:
            return False
        nearest = min(self.lights, key=lambda L: (L.x - x) ** 2 + (L.y - y) ** 2)
        dist_sq = (nearest.x - x) ** 2 + (nearest.y - y) ** 2
        if dist_sq <= (nearest.radius * threshold_factor) ** 2:
            self.lights.remove(nearest)
            return True
        return False

    def draw(self, surface):
        for light in self.lights:
            light.draw(surface)

    def get_lights(self):
        return self.lights



class BraitenbergVehicle:
    """
    Modes:
      'lover'     -> Vehicle 3a  (same-side inhibitory)
      'explorer'  -> Vehicle 3b  (crossed inhibitory, approach then avoid)
    """

    def __init__(self, x, y, radius=25, heading=0.0, mode="lover"):
        self.x = x
        self.y = y
        self.radius = radius
        self.heading = heading
        self.mode = mode

        # geometry of sensors
        self.sensor_offset_angle = math.radians(55)
        self.sensor_distance = radius * 1.8

        # tunables
        self.INTENSITY_GAIN = 800.0
        self.BASE_SPEED = 1.8
        self.MOTOR_GAIN = 5.0         # for love
        self.MAX_WHEEL_SPEED = 8.0
        self.TURN_GAIN = 0.06
        self.MOTOR_NOISE = 0.2

        # debug
        self.left_intensity = 0.0
        self.right_intensity = 0.0
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.forward_speed = 0.0
        self.turn_rate = 0.0

    
    def _sensor_positions(self):
        a = self.sensor_offset_angle
        d = self.sensor_distance

        left_local = (math.cos(a) * d, math.sin(a) * d)
        right_local = (math.cos(-a) * d, math.sin(-a) * d)

        ch = math.cos(self.heading)
        sh = math.sin(self.heading)

        def to_world(local):
            lx, ly = local
            wx = self.x + ch * lx - sh * ly
            wy = self.y + sh * lx + ch * ly
            return (wx, wy)

        return to_world(left_local), to_world(right_local)

    def _intensity_from_one_light(self, px, py, light_pos):
        lx, ly = light_pos
        dx = lx - px
        dy = ly - py
        dist_sq = dx * dx + dy * dy

        eps = 1.0
        raw = self.INTENSITY_GAIN / (dist_sq + eps)

        I_MAX = 1.5
        return max(0.0, min(I_MAX, raw))

    def _sensor_intensities(self, lights, left_sensor, right_sensor):
        I_L = 0.0
        I_R = 0.0
        for light in lights:
            I_L += self._intensity_from_one_light(left_sensor[0], left_sensor[1], light.pos)
            I_R += self._intensity_from_one_light(right_sensor[0], right_sensor[1], light.pos)

        I_MAX_SUM = 3.0
        return min(I_L, I_MAX_SUM), min(I_R, I_MAX_SUM)

    
    def set_mode(self, mode: str):
        self.mode = mode

    def reset_random_pose(self):
        self.x = random.uniform(100, WIDTH - 100)
        self.y = random.uniform(100, HEIGHT - 100)
        self.heading = random.uniform(-math.pi, math.pi)

    
    def update(self, lights):
        left_sensor, right_sensor = self._sensor_positions()
        self.left_intensity, self.right_intensity = self._sensor_intensities(
            lights, left_sensor, right_sensor
        )

        I_L = self.left_intensity
        I_R = self.right_intensity

        # Vehicle 3 – inhibitory
        if self.mode == "lover":
            # same-side inhibitory -> attraction to light
            raw_left = self.BASE_SPEED - self.MOTOR_GAIN * I_L
            raw_right = self.BASE_SPEED - self.MOTOR_GAIN * I_R

        elif self.mode == "explorer":
            EXPLORER_GAIN = 2.0
            raw_left = self.BASE_SPEED - EXPLORER_GAIN * I_R
            raw_right = self.BASE_SPEED - EXPLORER_GAIN * I_L

        else:
            raw_left = raw_right = 0.0

        # noise
        raw_left += random.uniform(-self.MOTOR_NOISE, self.MOTOR_NOISE)
        raw_right += random.uniform(-self.MOTOR_NOISE, self.MOTOR_NOISE)

        # clamp
        raw_left = max(0.0, min(self.MAX_WHEEL_SPEED, raw_left))
        raw_right = max(0.0, min(self.MAX_WHEEL_SPEED, raw_right))

        self.left_speed = raw_left
        self.right_speed = raw_right

        self.forward_speed = 0.5 * (self.left_speed + self.right_speed)
        self.turn_rate = (self.right_speed - self.left_speed) * self.TURN_GAIN

        self.heading += self.turn_rate
        self.x += self.forward_speed * math.cos(self.heading)
        self.y += self.forward_speed * math.sin(self.heading)

        self.x %= WIDTH
        self.y %= HEIGHT

  
    def draw(self, surface, light_count: int):
        pygame.draw.circle(surface, (0, 128, 255), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)

        # nose
        nose_x = self.x + math.cos(self.heading) * self.radius
        nose_y = self.y + math.sin(self.heading) * self.radius
        pygame.draw.line(surface, (0, 0, 0), (int(self.x), int(self.y)), (int(nose_x), int(nose_y)), 3)

        # sensors
        left_sensor, right_sensor = self._sensor_positions()
        pygame.draw.circle(surface, (255, 0, 0), (int(left_sensor[0]), int(left_sensor[1])), 5)
        pygame.draw.circle(surface, (255, 0, 0), (int(right_sensor[0]), int(right_sensor[1])), 5)
#vehicle 3b explorer - Strong stimulus inhibits motor rotation, causing speed reduction and turning

        if self.mode == "lover":
            mode_label = "3a – LOVER (same-side inhibitory)"
        elif self.mode == "explorer":
            mode_label = "3b – EXPLORER (crossed inhibitory, approach then avoid)"
        else:
            mode_label = "unknown"

        txt1 = (
            f"Mode: {mode_label}   "
            "[1]=3a lover  [2]=3b explorer  [R]=reset pose"
        )
        txt2 = f"Lights: {light_count}   [C]=reset lights  [N]=random light"
        txt3 = f"I_L={self.left_intensity:.2f}  I_R={self.right_intensity:.2f}"
        txt4 = f"vL={self.left_speed:.2f}  vR={self.right_speed:.2f}  fwd={self.forward_speed:.2f}"
        txt5 = f"turn={self.turn_rate:.4f} rad/frame"

        surface.blit(font.render(txt1, True, (0, 0, 0)), (10, 10))
        surface.blit(font.render(txt2, True, (0, 0, 0)), (10, 30))
        surface.blit(font.render(txt3, True, (0, 0, 0)), (10, 50))
        surface.blit(font.render(txt4, True, (0, 0, 0)), (10, 70))
        surface.blit(font.render(txt5, True, (0, 0, 0)), (10, 90))



def main():
    light_manager = LightManager()

    vehicle = BraitenbergVehicle(
        x=WIDTH // 2,
        y=HEIGHT // 2,
        heading=random.uniform(-math.pi, math.pi),
        mode="lover",   # start with 3a
    )

    running = True
    while running:
        screen.fill((255, 255, 255))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if event.button == 1:
                    moved = light_manager.move_nearest(mx, my)
                    if not moved:
                        light_manager.add_light_at(mx, my)
                elif event.button == 3:
                    light_manager.remove_nearest(mx, my)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    vehicle.set_mode("lover")
                elif event.key == pygame.K_2:
                    vehicle.set_mode("explorer")
                elif event.key == pygame.K_r:
                    vehicle.reset_random_pose()
                elif event.key == pygame.K_c:
                    light_manager.reset_defaults()
                elif event.key == pygame.K_n:
                    light_manager.add_random_light()

        lights = light_manager.get_lights()
        light_manager.draw(screen)

        vehicle.update(lights)
        vehicle.draw(screen, light_count=len(lights))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
