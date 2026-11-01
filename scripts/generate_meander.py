import os

matrix_frieze = [
    [1,1,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,0,0],
    [1,1,1,1,1,1,1,1,1,1,1,0],
    [1,0,0,0,0,0,0,0,0,0,1,0],
    [1,0,1,1,1,1,1,1,1,0,1,0],
    [1,0,1,0,0,0,0,0,1,0,1,0],
    [1,0,1,0,1,1,1,0,1,0,1,0],
    [1,0,1,0,1,0,1,0,1,0,1,0],
    [1,0,1,0,1,0,1,1,1,0,1,0],
    [1,0,1,0,1,0,0,0,0,0,1,0],
    [1,0,1,0,1,1,1,1,1,1,1,0],
    [1,0,1,0,0,0,0,0,0,0,0,0],
    [1,0,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,0,0],
    [1,1,1,1,1,1,1,1,1,1,1,1],
]

scale = 10
W = 12 * scale
H_frieze = 15 * scale

def matrix_to_rects(mat):
    rects = []
    for y, row in enumerate(mat):
        x = 0
        while x < len(row):
            if row[x] == 1:
                start_x = x
                while x < len(row) and row[x] == 1:
                    x += 1
                w = (x - start_x) * scale
                h = scale
                rects.append(f'  <rect x="{start_x * scale}" y="{y * scale}" width="{w}" height="{h}" />')
            else:
                x += 1
    return '\n'.join(rects)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(base_dir, 'static')
    frieze_rects = matrix_to_rects(matrix_frieze)
    matrix_wallpaper = matrix_frieze + [[0]*12 for _ in range(9)]
    H_wallpaper = len(matrix_wallpaper) * scale
    wallpaper_rects = matrix_to_rects(matrix_wallpaper)

    themes = {'purple': '#a855f7', 'red': '#ef4444', 'blue': '#0ea5e9'}
    for name, color in themes.items():
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H_frieze}" width="{W}" height="{H_frieze}" fill="{color}" shape-rendering="crispEdges">
{frieze_rects}
</svg>
'''
        with open(os.path.join(out_dir, f'meander-{name}.svg'), 'w', encoding='utf-8') as f:
            f.write(svg)
        if name == 'purple':
            with open(os.path.join(out_dir, 'meander.svg'), 'w', encoding='utf-8') as f:
                f.write(svg)

    for name, color in themes.items():
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H_wallpaper}" width="{W}" height="{H_wallpaper}" fill="{color}" shape-rendering="crispEdges">
{wallpaper_rects}
</svg>
'''
        with open(os.path.join(out_dir, f'meander-wallpaper-{name}.svg'), 'w', encoding='utf-8') as f:
            f.write(svg)
