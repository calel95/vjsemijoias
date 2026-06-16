#!/usr/bin/env python3
"""
Gera SVGs de placeholder bonitos para os produtos VJ Semijoias
Funciona 100% offline, sem dependência de internet
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"

# Cores VJ
GOLD_DARK = "#a67c3d"
GOLD = "#c9a86a"
GOLD_LIGHT = "#e0c489"
GOLD_PALE = "#f3e7d1"
CREAM = "#fbf6ee"
ROSE_LIGHT = "#e9c5a0"

# Placeholders por categoria (com ícone emoji)
PRODUCTS = {
    "brinco-marguerite": ("Brinco Marguerite", "✨", "BRINCOS"),
    "colar-sol-dourado": ("Colar Sol Dourado", "☀️", "COLARES"),
    "pulseira-tennis": ("Pulseira Tennis", "⚜️", "PULSEIRAS"),
    "anel-luna": ("Anel Luna", "🌙", "ANÉIS"),
    "pingente-flor-lis": ("Pingente Flor de Lis", "🌸", "PINGENTES"),
    "brinco-argola-crocodilo": ("Brinco Argola Crocodilo", "🐊", "BRINCOS"),
    "colar-gota-orvalho": ("Colar Gota de Orvalho", "💧", "COLARES"),
    "pulseira-elo-coracao": ("Pulseira Elo Coração", "💕", "PULSEIRAS"),
    "anel-duas-cores": ("Anel Duas Cores", "💍", "ANÉIS"),
    "pingente-estrela": ("Pingente Estrela", "⭐", "PINGENTES"),
}

def create_placeholder_svg(name, emoji, category, filename):
    """Cria um SVG de placeholder bonito"""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" width="600" height="600">
  <defs>
    <linearGradient id="bg-{filename}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{CREAM};stop-opacity:1" />
      <stop offset="50%" style="stop-color:{GOLD_PALE};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{GOLD_LIGHT};stop-opacity:1" />
    </linearGradient>
    <radialGradient id="ring-{filename}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:{GOLD_LIGHT};stop-opacity:0" />
      <stop offset="60%" style="stop-color:{GOLD};stop-opacity:0.3" />
      <stop offset="100%" style="stop-color:{GOLD_DARK};stop-opacity:0.6" />
    </radialGradient>
    <filter id="shadow-{filename}">
      <feGaussianBlur in="SourceAlpha" stdDeviation="8"/>
      <feOffset dx="0" dy="4" result="offsetblur"/>
      <feComponentTransfer>
        <feFuncA type="linear" slope="0.3"/>
      </feComponentTransfer>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  
  <!-- Background gradient -->
  <rect width="600" height="600" fill="url(#bg-{filename})"/>
  
  <!-- Decorative circles -->
  <circle cx="450" cy="150" r="80" fill="{GOLD_PALE}" opacity="0.5"/>
  <circle cx="150" cy="450" r="100" fill="{ROSE_LIGHT}" opacity="0.3"/>
  <circle cx="500" cy="500" r="60" fill="{GOLD_LIGHT}" opacity="0.4"/>
  
  <!-- Big ring (decorative) -->
  <circle cx="300" cy="300" r="180" fill="none" stroke="{GOLD}" stroke-width="3" opacity="0.4"/>
  <circle cx="300" cy="300" r="160" fill="none" stroke="{GOLD_DARK}" stroke-width="1" opacity="0.3"/>
  
  <!-- Diamond shape on top -->
  <g filter="url(#shadow-{filename})">
    <polygon points="300,80 280,100 300,140 320,100" fill="{GOLD_DARK}" opacity="0.7"/>
    <line x1="280" y1="100" x2="320" y2="100" stroke="{GOLD}" stroke-width="2"/>
  </g>
  
  <!-- Central icon (emoji) -->
  <text x="300" y="330" font-size="180" text-anchor="middle" fill="{GOLD_DARK}" opacity="0.6" font-family="Arial, sans-serif">{emoji}</text>
  
  <!-- Product name -->
  <text x="300" y="450" font-size="28" font-weight="bold" text-anchor="middle" fill="{GOLD_DARK}" font-family="Georgia, serif">{name}</text>
  
  <!-- Category -->
  <text x="300" y="490" font-size="16" text-anchor="middle" fill="{GOLD}" letter-spacing="3" font-family="Arial, sans-serif">{category}</text>
  
  <!-- VJ logo subtle -->
  <text x="300" y="555" font-size="14" text-anchor="middle" fill="{GOLD_DARK}" letter-spacing="5" font-family="Georgia, serif" opacity="0.5">VJ SEMIJOIAS</text>
</svg>'''
    return svg

def main():
    output_dir = FRONTEND_ROOT / "images" / "products"
    os.makedirs(output_dir, exist_ok=True)
    
    for filename, (name, emoji, category) in PRODUCTS.items():
        svg = create_placeholder_svg(name, emoji, category, filename)
        path = output_dir / f'{filename}.svg'
        with path.open('w', encoding='utf-8') as f:
            f.write(svg)
        print(f"✓ Criado: {path}")
    
    print(f"\n✅ {len(PRODUCTS)} placeholders SVG criados em {output_dir}")
    print("   Funcionam 100% offline!")

if __name__ == "__main__":
    main()
