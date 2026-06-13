#!/usr/bin/env python3
"""
Remove o fundo branco do logo VJ e gera versões otimizadas
"""
from PIL import Image
import os

input_path = '/workspace/vj-semijoias/images/logo.jpeg'
output_png = '/workspace/vj-semijoias/images/logo.png'
output_png_white = '/workspace/vj-semijoias/images/logo-white.png'  # versão pra usar em fundo escuro

# Abre a imagem
img = Image.open(input_path)
print(f"Original: {img.size}, mode: {img.mode}")

# Converte para RGBA
if img.mode != 'RGBA':
    img = img.convert('RGBA')

# Pixels do logo
pixels = img.load()
w, h = img.size

# Remove fundo branco (tolerância para não pegar os tons dourados)
threshold = 240
new_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
new_pixels = new_img.load()

for y in range(h):
    for x in range(w):
        r, g, b, a = pixels[x, y]
        # Se for branco ou quase branco, fica transparente
        if r > threshold and g > threshold and b > threshold:
            new_pixels[x, y] = (255, 255, 255, 0)
        else:
            new_pixels[x, y] = (r, g, b, a)

new_img.save(output_png, 'PNG', optimize=True)
print(f"PNG transparente: {output_png}")
print(f"Tamanho: {os.path.getsize(output_png) / 1024:.1f} KB")

# Versão branca pra usar em footer escuro
white_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
white_pixels = white_img.load()

for y in range(h):
    for x in range(w):
        r, g, b, a = new_pixels[x, y]
        if a > 0:  # se tem conteúdo
            # Mantém o dourado original mas com brilho aumentado
            # Para o footer escuro, mantém como está
            white_pixels[x, y] = (r, g, b, a)

# Versão com tom dourado claro (para fundo escuro)
golden_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
golden_pixels = golden_img.load()

for y in range(h):
    for x in range(w):
        r, g, b, a = new_pixels[x, y]
        if a > 0:
            # Aumenta brilho e saturação
            new_r = min(255, int(r * 1.1))
            new_g = min(255, int(g * 1.1))
            new_b = min(255, int(b * 1.1))
            golden_pixels[x, y] = (new_r, new_g, new_b, a)

golden_img.save(output_png_white, 'PNG', optimize=True)
print(f"PNG dourado claro: {output_png_white}")
print(f"Tamanho: {os.path.getsize(output_png_white) / 1024:.1f} KB")

# Gera também versões menores para web
for size_name, size_px in [('small', 80), ('medium', 200), ('large', 500)]:
    resized = new_img.copy()
    resized.thumbnail((size_px, size_px), Image.LANCZOS)
    out_path = f'/workspace/vj-semijoias/images/logo-{size_name}.png'
    resized.save(out_path, 'PNG', optimize=True)
    print(f"{size_name}: {out_path} ({os.path.getsize(out_path) / 1024:.1f} KB)")

print("\n✓ Logo processado com sucesso!")
