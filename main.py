import tkinter as tk
import math
import numpy as np
import colorsys

# Константы
WIDTH, HEIGHT = 800, 800
SCALE_INIT = 70
FOV = 256
AXIS_COLORS = ['#ff0000', '#00ff00', '#0000ff']  # RGB для X,Y,Z

class Camera:
    def __init__(self):
        self.angle_x = 0.0
        self.angle_y = 0.0
        self.scale = SCALE_INIT
        self.dragging = False
        self.last_x = 0
        self.last_y = 0

def generate_grid():
    steps_u = 30
    steps_v = 40
    grid = []
    for u in np.linspace(-2, 2, steps_u):
        row = []
        for v in np.linspace(0, 2 * math.pi, steps_v):
            x = math.cosh(u) * math.cos(v)
            y = math.cosh(u) * math.sin(v)
            z = math.sinh(u)
            row.append((x, y, z))
        grid.append(row)
    return np.array(grid, dtype=np.float32)

def generate_axes(length=3):
    return [
        [(0, 0, 0), (length, 0, 0)],  # X
        [(0, 0, 0), (0, length, 0)],  # Y
        [(0, 0, 0), (0, 0, length)]   # Z
    ]

def rotate_point(x, y, z, angle_x, angle_y):
    y, z = y * math.cos(angle_x) - z * math.sin(angle_x), y * math.sin(angle_x) + z * math.cos(angle_x)
    x, z = x * math.cos(angle_y) + z * math.sin(angle_y), -x * math.sin(angle_y) + z * math.cos(angle_y)
    return x, y, z

def project_point(x, y, z, scale):
    f = FOV / (FOV + z + 1e-5)
    screen_x = max(0, min(int(WIDTH/2 + x * f * scale), WIDTH-1))
    screen_y = max(0, min(int(HEIGHT/2 - y * f * scale), HEIGHT-1))
    return (screen_x, screen_y)

def draw_line(img, x0, y0, x1, y1, color):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    
    while True:
        if 0 <= x0 < WIDTH and 0 <= y0 < HEIGHT:
            img.put(color, (x0, y0))
        
        if x0 == x1 and y0 == y1:
            break
            
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy

class Renderer:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg='black')
        self.canvas.pack()
        self.img = tk.PhotoImage(width=WIDTH, height=HEIGHT)
        self.canvas.create_image((WIDTH//2, HEIGHT//2), image=self.img)
        self.camera = Camera()
        self.grid = generate_grid()
        self.axes = generate_axes()
        
        self.canvas.bind('<Button-1>', self.start_drag)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<MouseWheel>', self.zoom)

    def start_drag(self, event):
        self.camera.dragging = True
        self.camera.last_x = event.x
        self.camera.last_y = event.y

    def drag(self, event):
        if self.camera.dragging:
            dx = event.x - self.camera.last_x
            dy = event.y - self.camera.last_y
            self.camera.angle_y += dx * 0.01
            self.camera.angle_x += dy * 0.01
            self.camera.last_x = event.x
            self.camera.last_y = event.y
            self.render()

    def zoom(self, event):
        self.camera.scale *= 1.1 if event.delta > 0 else 0.9
        if self.camera.scale > SCALE_INIT:
            self.camera.scale = SCALE_INIT
        self.render()

    def render_axes(self):
        for axis_idx, axis in enumerate(self.axes):
            points = []
            for point in axis:
                x, y, z = rotate_point(*point, self.camera.angle_x, self.camera.angle_y)
                proj = project_point(x, y, z, self.camera.scale)
                points.append(proj)
            
            if len(points) >= 2:
                x0, y0 = points[0]
                x1, y1 = points[1]
                draw_line(self.img, x0, y0, x1, y1, AXIS_COLORS[axis_idx])

    def render_hyperboloid(self):
        projected = []
        z_buffer = []
        min_z = float('inf')
        max_z = -float('inf')
        
        for row in self.grid:
            proj_row = []
            z_row = []
            for point in row:
                x_rot, y_rot, z_rot = rotate_point(*point, self.camera.angle_x, self.camera.angle_y)
                proj = project_point(x_rot, y_rot, z_rot, self.camera.scale)
                proj_row.append(proj)
                z_row.append(z_rot)
                if 0 <= proj[0] < WIDTH and 0 <= proj[1] < HEIGHT:
                    min_z = min(min_z, z_rot)
                    max_z = max(max_z, z_rot)
            projected.append(proj_row)
            z_buffer.append(z_row)
        
        depth_range = max(max_z - min_z, 1e-5)
        
        # Новые параметры цвета
        HUE_START = 0.9   # 280 градусов (фиолетовый)
        HUE_END = 0.90     # 300 градусов (лиловый)
        SATURATION = 0.8
        VALUE_START = 0.9
        VALUE_END = 0.1
        
        # Горизонтальные линии
        for i in range(len(projected)):
            for j in range(len(projected[i])-1):
                x0, y0 = projected[i][j]
                x1, y1 = projected[i][j+1]
                z0 = z_buffer[i][j]
                z1 = z_buffer[i][j+1]
                
                d0 = (z0 - min_z) / depth_range
                d1 = (z1 - min_z) / depth_range
                
                # Цвета для начальной и конечной точек
                h0 = HUE_START + (HUE_END - HUE_START) * d0
                v0 = VALUE_START + (VALUE_END - VALUE_START) * d0
                color0 = tuple(int(255 * c) for c in colorsys.hsv_to_rgb(h0, SATURATION, v0))
                
                h1 = HUE_START + (HUE_END - HUE_START) * d1
                v1 = VALUE_START + (VALUE_END - VALUE_START) * d1
                color1 = tuple(int(255 * c) for c in colorsys.hsv_to_rgb(h1, SATURATION, v1))
                
                self.draw_gradient_line(x0, y0, x1, y1, color0, color1)
        
        # Вертикальные линии (аналогично)
        for j in range(len(projected[0])):
            for i in range(len(projected)-1):
                x0, y0 = projected[i][j]
                x1, y1 = projected[i+1][j]
                z0 = z_buffer[i][j]
                z1 = z_buffer[i+1][j]
                
                d0 = (z0 - min_z) / depth_range
                d1 = (z1 - min_z) / depth_range
                
                h0 = HUE_START + (HUE_END - HUE_START) * d0
                v0 = VALUE_START + (VALUE_END - VALUE_START) * d0
                color0 = tuple(int(255 * c) for c in colorsys.hsv_to_rgb(h0, SATURATION, v0))
                
                h1 = HUE_START + (HUE_END - HUE_START) * d1
                v1 = VALUE_START + (VALUE_END - VALUE_START) * d1
                color1 = tuple(int(255 * c) for c in colorsys.hsv_to_rgb(h1, SATURATION, v1))
                
                self.draw_gradient_line(x0, y0, x1, y1, color0, color1)

    def draw_gradient_line(self, x0, y0, x1, y1, color0, color1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        total = max(math.hypot(x1-x0, y1-y0), 1e-5)
        
        while True:
            if 0 <= x0 < WIDTH and 0 <= y0 < HEIGHT:
                t = max(0.0, min(1.0, math.hypot(x0 - x0, y0 - y0)/total))
                r = int(color0[0] * (1 - t) + color1[0] * t)
                g = int(color0[1] * (1 - t) + color1[1] * t)
                b = int(color0[2] * (1 - t) + color1[2] * t)
                self.img.put(f"#{r:02x}{g:02x}{b:02x}", (x0, y0))
            
            if x0 == x1 and y0 == y1:
                break
                
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def render(self):
        self.img = tk.PhotoImage(width=WIDTH, height=HEIGHT)
        self.render_hyperboloid()
        self.render_axes()
        self.canvas.itemconfig("all", image=self.img)
        self.canvas.update()

def main():
    root = tk.Tk()
    root.title("3D Hyperboloid with Axes")
    renderer = Renderer(root)
    renderer.render()
    root.mainloop()

if __name__ == "__main__":
    main()
