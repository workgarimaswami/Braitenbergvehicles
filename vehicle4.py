import pygame
import math
import random


pygame.init()
WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Braitenberg Vehicle 4 – Values & Special Tastes")

clock = pygame.time.Clock()
FPS = 60
font = pygame.font.SysFont("consolas", 16)



class Light:
    def __init__(self, x, y, radius=18):
        self.x = x
        self.y = y
        self.radius = radius

    @property
    def pos(self):
        return (self.x, self.y)

    def move_to(self, pos):
        self.x, self.y = pos

    def draw(self, surf):
        pygame.draw.circle(surf, (255, 255, 0), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)


class LightManager:
    def __init__(self):
        self.lights = []
        self.reset_defaults()

    def reset_defaults(self):
        """Two lights around center (good for figure-8 / peanut trajectories)."""
        self.lights.clear()
        cx, cy = WIDTH // 2, HEIGHT // 2
        spread = 120
        self.lights.append(Light(cx - spread, cy))
        self.lights.append(Light(cx + spread, cy))

    def clear_all(self):
        self.lights.clear()

    def add_light_at(self, x, y, radius=18):
        self.lights.append(Light(x, y, radius))

    def add_random_light(self, radius=18):
        x = random.randint(60, WIDTH - 60)
        y = random.randint(60, HEIGHT - 60)
        self.add_light_at(x, y, radius)

    def _nearest(self, x, y):
        if not self.lights:
            return None, None
        nearest = min(self.lights, key=lambda L: (L.x - x) ** 2 + (L.y - y) ** 2)
        dist_sq = (nearest.x - x) ** 2 + (nearest.y - y) ** 2
        return nearest, dist_sq

    def move_nearest_or_add(self, x, y, threshold_factor=2.0):
        """If click is near a light, move that light; else add a new one."""
        nearest, dist_sq = self._nearest(x, y)
        if nearest is not None and dist_sq <= (nearest.radius * threshold_factor) ** 2:
            nearest.move_to((x, y))
        else:
            self.add_light_at(x, y)

    def remove_nearest(self, x, y, threshold_factor=2.0):
        nearest, dist_sq = self._nearest(x, y)
        if nearest is not None and dist_sq <= (nearest.radius * threshold_factor) ** 2:
            self.lights.remove(nearest)

    def draw(self, surf):
        for L in self.lights:
            L.draw(surf)

    def get_lights(self):
        return self.lights


# ------------------------ Vehicle 4 ------------------------

class Vehicle4:
    """
    Braitenberg Vehicle 4 (from 'Values and Special Tastes').

    1.Two forward sensors.
    2.Motors driven by nonlinear sensor→motor mapping.
    3.Crossed excitatory wiring:
          left sensor  -> right motor
          right sensor -> left motor

    mode = '4a'  : non-monotonic (bell-shaped) mapping -> orbits, loops, figure-8.
    mode = '4b'  : threshold / step mapping -> jerky, decision-like turns.
    """

    def __init__(self, x, y, heading=0.0, radius=22, mode="4a"):
        self.x = x
        self.y = y
        self.heading = heading
        self.radius = radius
        self.mode = mode

        # geometry
        self.sensor_angle = math.radians(55)
        self.sensor_dist = radius * 2.2

        # intensity model
        self.INTENSITY_GAIN = 800.0    # 1 / distance^2 scaling

        # motors / kinematics
        self.BASE_SPEED = 0.2
        self.MOTOR_GAIN = 9.0
        self.MAX_WHEEL_SPEED = 10.0
        self.TURN_GAIN = 0.18          # higher => tighter turns -> more loops
        self.NOISE = 0.02              # small noise to break perfect symmetry

        # Vehicle 4a bell parameters (in intensity units)
        self.mu_4a = 0.35              # preferred intensity (orbit distance)
        self.sigma_4a = 0.18

        # Vehicle 4b thresholds
        self.low_4b = 0.15
        self.high_4b = 0.40

        # debug
        self.left_I = 0.0
        self.right_I = 0.0
        self.left_w = 0.0
        self.right_w = 0.0
        self.v = 0.0
        self.omega = 0.0

        # trail
        self.trail = []
        self.max_trail_len = 2000

    # ---------- geometry helpers ----------

    def _sensor_positions(self):
        a = self.sensor_angle
        d = self.sensor_dist

        sL_local = (math.cos(a) * d, math.sin(a) * d)
        sR_local = (math.cos(-a) * d, math.sin(-a) * d)

        ch = math.cos(self.heading)
        sh = math.sin(self.heading)

        def to_world(local):
            lx, ly = local
            wx = self.x + ch * lx - sh * ly
            wy = self.y + sh * lx + ch * ly
            return (wx, wy)

        return to_world(sL_local), to_world(sR_local)

    # ---------- sensing ----------

    def _intensity_from_light(self, px, py, light_pos):
        lx, ly = light_pos
        dx = lx - px
        dy = ly - py
        d2 = dx * dx + dy * dy
        eps = 1.0
        I = self.INTENSITY_GAIN / (d2 + eps)
        return I

    def _sensor_intensities(self, lights, sL, sR):
        I_L = 0.0
        I_R = 0.0
        for L in lights:
            I_L += self._intensity_from_light(sL[0], sL[1], L.pos)
            I_R += self._intensity_from_light(sR[0], sR[1], L.pos)
        return I_L, I_R

    # ---------- sensor → motor mappings -------------------------------------------------------

    def _map_4a_bell(self, I):
        """
        Non-monotonic value curve:
            f(I) = base + gain * exp( - (I - mu)^2 / (2*sigma^2) )
        """
        mu = self.mu_4a
        sigma = self.sigma_4a
        bell = math.exp(-((I - mu) ** 2) / (2.0 * sigma * sigma))
        return self.BASE_SPEED + self.MOTOR_GAIN * bell

    def _map_4b_threshold(self, I):
        """
        Threshold / step mapping.
        """
        if I < self.low_4b:
            level = 0.0
        elif I < self.high_4b:
            level = 0.5
        else:
            level = 1.0
        return self.BASE_SPEED + self.MOTOR_GAIN * level

    # ---------- dynamics ----------

    def set_mode(self, mode):
        self.mode = mode

    def clear_trail(self):
        self.trail.clear()

    def random_pose(self):
        self.x = random.uniform(80, WIDTH - 80)
        self.y = random.uniform(80, HEIGHT - 80)
        self.heading = random.uniform(-math.pi, math.pi)
        self.clear_trail()

    def update(self, lights, dt=1.0):
        sL, sR = self._sensor_positions()
        self.left_I, self.right_I = self._sensor_intensities(lights, sL, sR)

        # choose mapping
        if self.mode == "4a":
            L_raw = self._map_4a_bell(self.left_I)
            R_raw = self._map_4a_bell(self.right_I)
        else:  # 4b
            L_raw = self._map_4b_threshold(self.left_I)
            R_raw = self._map_4b_threshold(self.right_I)

        # crossed excitatory wiring
        left_wheel = R_raw
        right_wheel = L_raw

        # noise
        left_wheel += random.uniform(-self.NOISE, self.NOISE)
        right_wheel += random.uniform(-self.NOISE, self.NOISE)

        # clamp
        left_wheel = max(-self.MAX_WHEEL_SPEED, min(self.MAX_WHEEL_SPEED, left_wheel))
        right_wheel = max(-self.MAX_WHEEL_SPEED, min(self.MAX_WHEEL_SPEED, right_wheel))

        self.left_w = left_wheel
        self.right_w = right_wheel

        # kinematics
        self.v = 0.5 * (left_wheel + right_wheel)
        self.omega = (right_wheel - left_wheel) * self.TURN_GAIN

        self.heading += self.omega * dt
        self.x += self.v * math.cos(self.heading) * dt
        self.y += self.v * math.sin(self.heading) * dt

        # wrap world
        self.x %= WIDTH
        self.y %= HEIGHT

        # trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.max_trail_len:
            self.trail.pop(0)

    # ---------- drawing ----------

    def draw(self, surf, light_count):
        # trail first
        if len(self.trail) > 2:
            pygame.draw.lines(surf, (180, 180, 180), False,
                              [(int(px), int(py)) for (px, py) in self.trail], 2)

        # body
        pygame.draw.circle(surf, (0, 200, 0), (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(surf, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)

        # heading
        nose_x = self.x + math.cos(self.heading) * self.radius
        nose_y = self.y + math.sin(self.heading) * self.radius
        pygame.draw.line(surf, (0, 0, 0), (int(self.x), int(self.y)), (int(nose_x), int(nose_y)), 3)

        # sensors
        sL, sR = self._sensor_positions()
        pygame.draw.circle(surf, (255, 0, 0), (int(sL[0]), int(sL[1])), 5)
        pygame.draw.circle(surf, (255, 0, 0), (int(sR[0]), int(sR[1])), 5)

        # HUD text
        mode_label = "4a – non-monotonic (orbits & loops)" if self.mode == "4a" else "4b – thresholds / steps"
        t1 = f"Mode: {mode_label}   [1] 4a   [2] 4b   [R] reset pose   [T] clear trail"
        t2 = f"Lights: {light_count}   L-click: move / add   R-click: remove   [C] reset   [N] random   [X] clear all"
        t3 = f"I_L={self.left_I:.3f}  I_R={self.right_I:.3f}"
        t4 = f"vL={self.left_w:.2f}  vR={self.right_w:.2f}  v={self.v:.2f}"
        t5 = f"turn={self.omega:.4f} rad/frame"

        surf.blit(font.render(t1, True, (0, 0, 0)), (10, 10))
        surf.blit(font.render(t2, True, (0, 0, 0)), (10, 30))
        surf.blit(font.render(t3, True, (0, 0, 0)), (10, 50))
        surf.blit(font.render(t4, True, (0, 0, 0)), (10, 70))
        surf.blit(font.render(t5, True, (0, 0, 0)), (10, 90))


# ------------------------ main loop ------------------------

def main():
    light_manager = LightManager()

    vehicle = Vehicle4(
        x=WIDTH // 2,
        y=HEIGHT // 2 - 160,   # start above the default lights
        heading=math.radians(60),
        mode="4a",
    )

    running = True
    while running:
        dt = clock.tick(FPS) / 60.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if event.button == 1:        # left -> move nearest or add
                    light_manager.move_nearest_or_add(mx, my)
                elif event.button == 3:      # right -> remove nearest
                    light_manager.remove_nearest(mx, my)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    vehicle.set_mode("4a")
                elif event.key == pygame.K_2:
                    vehicle.set_mode("4b")
                elif event.key == pygame.K_r:
                    vehicle.random_pose()
                elif event.key == pygame.K_t:
                    vehicle.clear_trail()
                elif event.key == pygame.K_c:
                    light_manager.reset_defaults()
                    vehicle.clear_trail()
                elif event.key == pygame.K_n:
                    light_manager.add_random_light()
                elif event.key == pygame.K_x:
                    light_manager.clear_all()
                    vehicle.clear_trail()

        lights = light_manager.get_lights()
        vehicle.update(lights, dt=1.0)

        screen.fill((255, 255, 255))
        light_manager.draw(screen)
        vehicle.draw(screen, len(lights))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
