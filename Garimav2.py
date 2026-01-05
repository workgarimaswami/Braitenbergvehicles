#Love and explorer 
# Vehicle 3a → Love
# Same-side inhibitory, Approaches light, Slows down and stays

# Vehicle 3b → Explorer
# Crossed inhibitory, Approaches when far , Gets “repelled” when too close 

#f(x)=1/x
# 4A = instincts , differentiable, thresold
# 4B = will, ticking like behavior because the funciton is non differential, special taste

import pygame                  
import math                    
import random                  

pygame.init()                  

WIDTH, HEIGHT = 800, 600      
screen = pygame.display.set_mode((WIDTH, HEIGHT))  
png = pygame                    
pygame.display.set_caption("Garima's limited edition Braitenberg Vehicle 2 – Car Version + Sun Lights")

clock = pygame.time.Clock()
FPS = 60     
font = pygame.font.SysFont("consolas", 16) 


def draw_sun(surface, x, y, radius):
    pygame.draw.circle(surface, (255, 215, 0), (int(x), int(y)), radius)
    pygame.draw.circle(surface, (255, 180, 0), (int(x), int(y)), radius, 2)
    for i in range(8):#sun rays   
        angle = math.radians(i * 45)
        sx = x + math.cos(angle) * (radius + 10)
        sy = y + math.sin(angle) * (radius + 10)
        pygame.draw.line(surface, (255, 200, 0), (x, y), (sx, sy), 3)# draw ray line from center (x,y) to (sx,sy) 
        
class Light:
    def __init__(self, x, y, radius=18): #constructor for each light object: position x,y and radius default 18 
        self.x = x                
        self.y = y                
        self.radius = radius      

    def move_to(self, pos):
        self.x, self.y = pos # destructure tuple and assign to instance variables

    @property
    def pos(self):
        # property to get position as a tuple
        return (self.x, self.y)

    def draw(self, surface):
        # draw this light onto the provided surface by calling helper draw_sun
        draw_sun(surface, self.x, self.y, self.radius)


class LightManager:
    def __init__(self):
        self.lights = []         # Light instances
        self.reset_defaults()    

    def reset_defaults(self):
        self.lights.clear()     
        cx, cy = WIDTH // 2, HEIGHT // 2         # compute center coordinates
        spread = 150            # how far from center default lights are placed
        self.lights.append(Light(cx - spread, cy)) #r
        self.lights.append(Light(cx + spread, cy)) #l
        self.lights.append(Light(cx, cy - spread)) #a
        self.lights.append(Light(cx, cy + spread)) #b

    def add_light_at(self, x, y, radius=18):
        # add a new Light at explicit coordinates (used for mouse clicks)
        self.lights.append(Light(x, y, radius))

    def add_random_light(self, radius=18):
        x = random.randint(50, WIDTH - 50)
        y = random.randint(50, HEIGHT - 50)
        self.add_light_at(x, y, radius)

    def move_nearest(self, x, y, threshold_factor=2.0):
        # move the nearest light to (x,y) if the click is sufficiently close
        if not self.lights:
            return False         # no lights to move: return False (indicates nothing moved)
        nearest = min(self.lights, key=lambda L: (L.x - x)**2 + (L.y - y)**2)
        # find the light with minimum squared distance to (x,y)
        dist_sq = (nearest.x - x)**2 + (nearest.y - y)**2
        # compute squared distance to nearest
        if dist_sq <= (nearest.radius * threshold_factor)**2:
            # if within threshold_factor * radius (squared check), consider it a hit
            nearest.move_to((x, y))   # update the nearest light to new mouse coords
            return True               # indicate success
        return False                  # click too far: do nothing and return False

    def remove_nearest(self, x, y, threshold_factor=2.0):
        # remove the nearest light if the click is sufficiently close
        if not self.lights:
            return False
        nearest = min(self.lights, key=lambda L: (L.x - x)**2 + (L.y - y)**2)
        dist_sq = (nearest.x - x)**2 + (nearest.y - y)**2
        if dist_sq <= (nearest.radius * threshold_factor)**2:
            self.lights.remove(nearest)  # remove from the list
            return True
        return False

    def draw(self, surface):
        # draw all lights onto the provided surface
        for L in self.lights:
            L.draw(surface)

    def get_lights(self):
        # return the internal lights list (used by the vehicle to sense lights)
        return self.lights

class BraitenbergVehicle2:
    def __init__(self, x, y, radius=30, heading=0.0, mode="coward"):
        self.x = x                  
        self.y = y                  
        self.radius = radius        # size of the vehicle; used for visual scale and sensor distance
        self.heading = heading      # orientation in radians (0 = right/east, positive = rotate ccw)
        self.mode = mode            # behavior mode: "coward" or "aggressive"

        self.sensor_offset_angle = math.radians(50)
        # angle between vehicle heading and each sensor (50 degrees converted to radians)
        self.sensor_distance = radius * 1.6
        # how far ahead of the vehicle body the sensors are positioned (relative to radius)

        self.INTENSITY_GAIN = 800.0   
        self.MOTOR_GAIN = 6.0         
        self.BASE_SPEED = 1.4        
        self.MAX_WHEEL_SPEED = 7.0 
        self.TURN_GAIN = 0.055    
        self.MOTOR_NOISE = 0.3        

        self.left_intensity = 0    
        self.right_intensity = 0    
        self.left_speed = 0          
        self.right_speed = 0         
        self.forward_speed = 0       
        self.turn_rate = 0           

    def _sensor_positions(self):
        # compute the world coordinates of the left and right sensors based on vehicle pose
        a = self.sensor_offset_angle
        d = self.sensor_distance

        left_local = (math.cos(a)*d, math.sin(a)*d)
        # local coordinates of left sensor relative to the vehicle center before rotation
        right_local = (math.cos(-a)*d, math.sin(-a)*d)
        # local coordinates for right sensor (negative angle)

        ch = math.cos(self.heading)
        sh = math.sin(self.heading)
        # precompute cos and sin of heading for rotation matrix

        def to_world(local):
            # nested helper: rotate and translate a local point to world coordinates
            lx, ly = local
            wx = self.x + ch*lx - sh*ly
            wy = self.y + sh*lx + ch*ly
            return (wx, wy)

        return to_world(left_local), to_world(right_local)
        # return a tuple: (left_sensor_world_pos, right_sensor_world_pos)

    def _intensity_from_one_light(self, px, py, light_pos):
        # compute contribution of a single light to a sensor at (px,py)
        lx, ly = light_pos                     
        dx, dy = lx - px, ly - py              
        dist_sq = dx*dx + dy*dy                
        raw = self.INTENSITY_GAIN / (dist_sq + 1)
        # inverse-square-like falloff with +1 to avoid division by zero; scaled by INTENSITY_GAIN
        return min(max(raw, 0.0), 1.5)         

    def _sensor_intensities(self, lights, left_s, right_s):
        # sum intensity contributions from all lights for both sensors
        I_L = 0
        I_R = 0
        for L in lights:
            I_L += self._intensity_from_one_light(left_s[0], left_s[1], L.pos)
            # accumulate intensity from this light for left sensor
            I_R += self._intensity_from_one_light(right_s[0], right_s[1], L.pos)
            # accumulate for right sensor
        return min(I_L, 3.0), min(I_R, 3.0)
        # clamp each sensor total to maximum of 3.0 and return tuple (left, right)

    def set_mode(self, mode):
        # setter to change vehicle behavior mode externally (e.g., keystrokes)
        self.mode = mode

    def reset_random_pose(self):
        # place the vehicle at a random location and heading within bounds (for testing)
        self.x = random.uniform(80, WIDTH - 80)
        self.y = random.uniform(80, HEIGHT - 80)
        self.heading = random.uniform(-math.pi, math.pi)

    def update(self, lights):
        # main physics/brain update per frame given the list of Light objects
        left_s, right_s = self._sensor_positions()
        # compute current sensor world coordinates
        self.left_intensity, self.right_intensity = self._sensor_intensities(lights, left_s, right_s)
        # compute sensor intensities from all lights

        if self.mode == "coward":
            raw_L = self.BASE_SPEED + self.MOTOR_GAIN * self.left_intensity
            raw_R = self.BASE_SPEED + self.MOTOR_GAIN * self.right_intensity
            # in 'coward' (repellent) wiring: each wheel is influenced by the same-side sensor intensity
            # this tends to increase speed on the brighter side, making the vehicle turn away
        else:
            raw_L = self.BASE_SPEED + self.MOTOR_GAIN * self.right_intensity
            raw_R = self.BASE_SPEED + self.MOTOR_GAIN * self.left_intensity
            # in 'aggressive' (attractive) wiring: cross coupling (left wheel <- right sensor)
            # this tends to steer the vehicle toward lights

        raw_L += random.uniform(-self.MOTOR_NOISE, self.MOTOR_NOISE)
        raw_R += random.uniform(-self.MOTOR_NOISE, self.MOTOR_NOISE)
        # add small random perturbation to wheel speeds to avoid perfectly deterministic motion

        self.left_speed = max(-self.MAX_WHEEL_SPEED, min(self.MAX_WHEEL_SPEED, raw_L))
        self.right_speed = max(-self.MAX_WHEEL_SPEED, min(self.MAX_WHEEL_SPEED, raw_R))
        # clamp each wheel speed between -MAX_WHEEL_SPEED and +MAX_WHEEL_SPEED

        self.forward_speed = 0.5*(self.left_speed + self.right_speed)
        # forward translational speed is average of left and right wheels
        self.turn_rate = (self.right_speed - self.left_speed) * self.TURN_GAIN
        # angular speed (change in heading) proportional to wheel differential scaled by TURN_GAIN

        self.heading += self.turn_rate
        # integrate heading
        self.x += self.forward_speed * math.cos(self.heading)
        self.y += self.forward_speed * math.sin(self.heading)
        # integrate position: move along heading by forward_speed each frame

        self.x %= WIDTH
        self.y %= HEIGHT
        # wrap-around boundaries using modulus so the vehicle reappears on the opposite edge

   
    def draw(self, surface, light_count):
        car_w = self.radius * 2
        car_h = self.radius * 1.2

        ch = math.cos(self.heading)
        sh = math.sin(self.heading)
        # precompute cos and sin for rotating shape corners

        def rotate_point(px, py):
            rx = self.x + px*ch - py*sh
            ry = self.y + px*sh + py*ch
            return (rx, ry)

        half_w = car_w/2
        half_h = car_h/2
        # compute half-extents of car rectangle

        corners = [
            rotate_point(-half_w, -half_h),
            rotate_point(+half_w, -half_h),
            rotate_point(+half_w, +half_h),
            rotate_point(-half_w, +half_h),
        ]
        # define 4 corner points of the rectangle body in local coordinates, rotated to world via rotate_point

        pygame.draw.polygon(surface, (0, 120, 255), corners)
        pygame.draw.polygon(surface, (0, 0, 0), corners, 3)

        wheel_w = car_w * 0.1
        wheel_h = car_h * 0.6

        def draw_wheel(offset_x, offset_y):
            w_corners = []
            for (ox, oy) in [
                (-wheel_w, -wheel_h),
                (+wheel_w, -wheel_h),
                (+wheel_w, +wheel_h),
                (-wheel_w, +wheel_h),
            ]:
                wx, wy = rotate_point(offset_x + ox, offset_y + oy)
                w_corners.append((wx, wy))
            pygame.draw.polygon(surface, (40, 40, 40), w_corners)
            # draw wheel as dark rectangle

        draw_wheel(+half_w * 0.9, -half_h)
        draw_wheel(+half_w * 0.9, +half_h)
        draw_wheel(-half_w * 0.9, -half_h)
        draw_wheel(-half_w * 0.9, +half_h)
        # draw four wheels near each corner (front/back, left/right) using offsets scaled by half_w/half_h

        nose_x = self.x + math.cos(self.heading)*(half_w)
        nose_y = self.y + math.sin(self.heading)*(half_w)
        # compute a point at the vehicle's nose (half_w ahead along heading)
        pygame.draw.circle(surface, (255, 255, 255), (int(nose_x), int(nose_y)), 8)
        # draw a white circle as a headlight / nose marker

        left_s, right_s = self._sensor_positions()
        # compute current sensor world positions for drawing
        pygame.draw.circle(surface, (255, 0, 0), (int(left_s[0]), int(left_s[1])), 5)
        # draw left sensor as small red circle
        pygame.draw.circle(surface, (255, 0, 0), (int(right_s[0]), int(right_s[1])), 5)
        # draw right sensor likewise

        txt1 = f"Mode: {'COWARD' if self.mode=='coward' else 'AGGRESSIVE'}  [1]=coward [2]=aggressive [R]=reset  L-click:add/move  R-click:remove"
        # prepare UI string showing mode and controls; uses inline ternary to display mode label
        txt2 = f"Lights: {light_count}   [C]=reset lights [N]=random light"
        # prepare second UI string showing number of lights and additional controls

        surface.blit(font.render(txt1, True, (0, 0, 0)), (10, 10))
        # render txt1 to a Surface via font and blit (draw) it at coordinates (10,10) in black
        surface.blit(font.render(txt2, True, (0, 0, 0)), (10, 30))
        # render txt2 and draw at (10,30)

def main():
    # entry point for the application logic (creates manager and vehicle, runs main loop)
    light_manager = LightManager()  # instantiate the manager that holds and manipulates lights
    vehicle = BraitenbergVehicle2(WIDTH//2, HEIGHT//2, heading=random.uniform(-math.pi, math.pi))
    # create vehicle centered on screen with random initial heading angle

    running = True  # control flag for main loop
    while running:  # game loop: runs until running is set False
        screen.fill((240, 240, 240))
        # fill background with a light gray color to clear previous frame

        for event in pygame.event.get():
            # event polling loop: iterate all events currently waiting
            if event.type == pygame.QUIT:
                running = False
                # user requested to close the window (click X) -> break loop and exit program
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # get mouse coordinates from event
                if event.button == 1:
                    # left mouse button pressed
                    moved = light_manager.move_nearest(mx, my)
                    # attempt to move nearest light to click location (returns True if moved)
                    if not moved:
                        light_manager.add_light_at(mx, my)
                        # if no nearby light was moved, create a new light at this position
                elif event.button == 3:
                    # right mouse button pressed
                    light_manager.remove_nearest(mx, my)
                    # remove nearest light if click is close enough
            if event.type == pygame.KEYDOWN:
                # keyboard key pressed events
                if event.key == pygame.K_1:
                    vehicle.set_mode("coward")
                    # set vehicle mode to coward when '1' pressed
                elif event.key == pygame.K_2:
                    vehicle.set_mode("aggressive")
                    # set to aggressive when '2' pressed
                elif event.key == pygame.K_r:
                    vehicle.reset_random_pose()
                    # reset vehicle to a random pose when 'r' pressed
                elif event.key == pygame.K_c:
                    light_manager.reset_defaults()
                    # reset lights to default cross pattern when 'c' pressed
                elif event.key == pygame.K_n:
                    light_manager.add_random_light()
                    # add a random light when 'n' pressed

        lights = light_manager.get_lights()  # fetch current list of lights for sensing and drawing
        light_manager.draw(screen)           # draw lights to the screen first (so vehicle appears on top)

        vehicle.update(lights)               # update vehicle physics/behavior based on lights
        vehicle.draw(screen, len(lights))    # draw the vehicle, passing light count for UI

        pygame.display.flip()                # flip the display buffers to show the rendered frame
        clock.tick(FPS)                      # pause to maintain the target FPS (limits speed)

    pygame.quit()                           # cleanup and close pygame when loop exits

if __name__ == "__main__":
    main()                                 # if script executed directly, call main() to start the app
