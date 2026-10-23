#!/usr/bin/env python3
"""
Shadow Slave Texture Generator - Pure Python PNG Writer
Generates all required textures using only standard library (struct, zlib, os, random).
"""
import struct
import zlib
import os
import random

# ============================================================
# PNG Writer (pure Python, stdlib only)
# ============================================================

def write_png(filename, width, height, pixels):
    """Write a PNG file using pure Python (struct, zlib)."""
    import struct
    import zlib
    
    # Build raw image data with filter bytes
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # Filter type 0 (None)
        for x in range(width):
            r, g, b, a = pixels[y][x]
            raw.extend([r, g, b, a])
    
    compressed = zlib.compress(raw, 9)
    
    # Build PNG
    out = bytearray()
    
    # PNG signature
    out += b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr_crc = zlib.crc32(b'IHDR' + struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) & 0xffffffff
    out = bytearray()
    out += struct.pack('>I', 13)
    out += b'IHDR'
    out += struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    out += struct.pack('>I', zlib.crc32(b'IHDR' + struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) & 0xffffffff)
    
    # IDAT chunk
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # Filter type 0 (None)
        for x in range(width):
            r, g, b, a = pixels[y][x]
            raw.extend([r, g, b, a])
    
    compressed = zlib.compress(raw, 9)
    idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
    out += struct.pack('>I', len(compressed))
    out += b'IDAT'
    out += compressed
    out += struct.pack('>I', idat_crc)
    
    # IEND chunk
    out += struct.pack('>I', 0)
    out += b'IEND'
    out += struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff)
    
    with open(filename, 'wb') as f:
        f.write(out)

# ============================================================
# Texture Generators
# ============================================================

def create_shadow_slave():
    w, h = 64, 64
    pixels = [[(0, 0, 0, 0) for _ in range(w)] for _ in range(h)]
    
    SHADOW_BASE = (10, 10, 15, 255)
    SHADOW_DARK = (5, 5, 10, 255)
    SHADOW_MID = (20, 15, 25, 255)
    EYE_GLOW = (80, 180, 255, 255)
    EYE_CORE = (180, 220, 255, 255)
    RUNE_GLOW = (120, 80, 200, 255)
    RUNE_BRIGHT = (180, 140, 255, 255)
    
    for y in range(64):
        for x in range(64):
            pixels[y][x] = (0, 0, 0, 0)
    
    # HEAD: UV x:32-37, y:0-11
    for x in range(32, 38):
        for y in range(0, 6):
            if x in (32, 37) or y in (0, 5):
                pixels[y][x] = (5, 5, 10, 255)
            elif x in (34, 35) and y in (2, 3):
                if (x == 34 and y == 2) or (x == 35 and y == 2):
                    pixels[y][x] = (80, 180, 255, 255)
                elif (x == 34 and y == 3) or (x == 35 and y == 3):
                    pixels[y][x] = (180, 220, 255, 255)
                else:
                    pixels[y][x] = (10, 10, 15, 255)
            else:
                pixels[y][x] = (10, 10, 15, 255)
    
    for x in range(32, 38):
        for y in range(6, 12):
            pixels[y][x] = (20, 15, 25, 255) if (x+y)%2==0 else (10, 10, 15, 255)
    
    for x in range(38, 44):
        for y in range(0, 6):
            pixels[y][x] = (10, 10, 15, 255)
    
    for x in range(0, 6):
        for y in range(0, 2):
            if x in (0, 5) or y in (0, 1):
                pixels[y][x] = (5, 5, 10, 255)
            else:
                pixels[y][x] = (10, 10, 15, 255)
    
    for x in range(6, 16):
        for y in range(0, 12):
            pixels[y][x] = (20, 15, 25, 255) if x < 8 else (10, 10, 15, 255)
    
    for rx, ry in [(2,0), (3,0), (2,1), (3,1)]:
        pixels[ry][rx] = (120, 80, 200, 255)
    for rx, ry in [(2,0), (3,0), (2,1), (3,1)]:
        pixels[ry][rx] = (180, 140, 255, 255)
    
    for x in range(48, 50):
        for y in range(16, 20):
            if x in (48, 49) or y in (16, 19):
                pixels[y][x] = (5, 5, 10, 255)
            else:
                pixels[y][x] = (10, 10, 15, 255)
    
    for x in range(40, 42):
        for y in range(16, 20):
            if x in (40, 41) or y in (16, 19):
                pixels[y][x] = (5, 5, 10, 255)
            else:
                pixels[y][x] = (10, 10, 15, 255)
    
    for x in range(0, 2):
        for y in range(16, 22):
            if x in (0, 1) or y in (16, 21):
                pixels[y][x] = (5, 5, 10, 255)
            else:
                pixels[y][x] = (10, 10, 15, 255)
    
    for x in range(16, 18):
        for y in range(16, 22):
            if x in (16, 17) or y in (16, 21):
                pixels[y][x] = (5, 5, 10, 255)
            else:
                pixels[y][x] = (10, 10, 15, 255)
    
    random.seed(42)
    for _ in range(30):
        px = random.randint(0, 63)
        py = random.randint(0, 63)
        r, g, b, a = pixels[py][px]
        if a > 0:
            pixels[py][px] = (min(255, r+20), min(255, g+10), min(255, b+30), 255)
    
    return [[(0,0,0,0) for _ in range(64)] for _ in range(64)]

def create_echo_shade():
    w, h = 64, 64
    pixels = [[(0, 0, 0, 0) for _ in range(w)] for _ in range(h)]
    
    BASE = (20, 10, 40, 200)
    DARK = (10, 5, 20, 220)
    LIGHT = (60, 40, 100, 220)
    EYE = (100, 200, 255, 255)
    EYE_CORE = (200, 230, 255, 255)
    GLOW = (100, 80, 255, 200)
    
    for y in range(64):
        for x in range(64):
            pixels[y][x] = (0, 0, 0, 0)
    
    for x in range(32, 38):
        for y in range(0, 6):
            if x in (32, 37) or y in (0, 5):
                pixels[y][x] = (10, 5, 20, 255)
            elif x in (34, 35) and y in (2, 3):
                if x in (34, 35) and y == 2:
                    pixels[y][x] = (100, 200, 255, 255)
                elif x in (34, 35) and y == 3:
                    pixels[y][x] = (200, 230, 255, 255)
                else:
                    pixels[y][x] = (20, 10, 40, 255)
            else:
                pixels[y][x] = (20, 10, 40, 255)
    
    for x in range(32, 38):
        for y in range(6, 12):
            pixels[y][x] = (40, 30, 80, 255) if (x+y)%2==0 else (20, 10, 40, 255)
    
    for x in range(38, 44):
        for y in range(0, 6):
            pixels[y][x] = (20, 10, 40, 255)
    
    for x in range(0, 6):
        for y in range(0, 2):
            if x in (0, 5) or y in (0, 1):
                pixels[y][x] = (10, 5, 20, 255)
            else:
                pixels[y][x] = (20, 10, 40, 255)
    
    for x in range(6, 16):
        for y in range(0, 12):
            pixels[y][x] = (40, 30, 80, 255) if x < 8 else (20, 10, 40, 255)
    
    for rx, ry in [(2,0), (3,0), (2,1), (3,1)]:
        pixels[ry][rx] = (140, 100, 255, 255)
    for rx, ry in [(2,0), (3,0), (2,1), (3,1)]:
        pixels[ry][rx] = (180, 160, 255, 255)
    
    for x in range(48, 50):
        for y in range(16, 20):
            if x in (48, 49) or y in (16, 19):
                pixels[y][x] = (10, 5, 20, 255)
            else:
                pixels[y][x] = (20, 10, 40, 255)
    
    for x in range(40, 42):
        for y in range(16, 20):
            if x in (40, 41) or y in (16, 19):
                pixels[y][x] = (10, 5, 20, 255)
            else:
                pixels[y][x] = (20, 10, 40, 255)
    
    for x in range(0, 2):
        for y in range(16, 22):
            if x in (0, 1) or y in (16, 21):
                pixels[y][x] = (10, 5, 20, 255)
            else:
                pixels[y][x] = (20, 10, 40, 255)
    
    for x in range(16, 18):
        for y in range(16, 22):
            if x in (16, 17) or y in (16, 21):
                pixels[y][x] = (10, 5, 20, 255)
            else:
                pixels[y][x] = (20, 10, 40, 255)
    
    return pixels

def create_item_texture(base_color, highlight_color):
    w, h = 16, 16
    pixels = [[(0, 0, 0, 0) for _ in range(w)] for _ in range(h)]
    for x in range(16):
        for y in range(16):
            dx, dy = x-8, y-8
            dist = (dx*dx + (dy*0.8)**2)**0.5
            if dist < 6:
                if dist < 3:
                    pixels[y][x] = (min(255, base_color[0]+40), min(255, base_color[1]+40), min(255, base_color[2]+40), 255)
                elif dist < 4:
                    pixels[y][x] = base_color
                else:
                    pixels[y][x] = (base_color[0]//2, base_color[1]//2, base_color[2]//2, 255)
    for x in range(4, 7):
        for y in range(4, 7):
            pixels[y][x] = highlight_color
    return [[(0,0,0,0) for _ in range(16)] for _ in range(16)]

def create_spawn_egg():
    w, h = 16, 16
    pixels = [[(0,0,0,0) for _ in range(w)] for _ in range(h)]
    for x in range(16):
        for y in range(16):
            dx, dy = x-8, y-8
            dist = (dx*dx + dy*dy)**0.5
            if dist < 6:
                if dist < 2:
                    pixels[y][x] = (180, 100, 255, 255)
                elif dist < 4:
                    pixels[y][x] = (100, 50, 180, 255)
                else:
                    pixels[y][x] = (50, 20, 100, 255)
    return pixels

def write_png(filename, width, height, pixels):
    import struct
    import zlib
    
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            r, g, b, a = pixels[y][x]
            raw.extend([r, g, b, a])
    
    compressed = zlib.compress(raw, 9)
    
    out = bytearray(b'\x89PNG\r\n\x1a\n')
    
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr_crc = zlib.crc32(b'IHDR' + struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) & 0xffffffff
    out = bytearray(b'\x89PNG\r\n\x1a\n')
    out += struct.pack('>I', 13) + b'IHDR' + struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    out += struct.pack('>I', zlib.crc32(b'IHDR' + struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) & 0xffffffff)
    
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            r, g, b, a = pixels[y][x]
            raw.extend([r, g, b, a])
    
    compressed = zlib.compress(raw, 9)
    out += struct.pack('>I', len(compressed)) + b'IDAT' + zlib.compress(raw, 9)
    out += struct.pack('>I', zlib.crc32(b'IDAT' + zlib.compress(raw, 9)) & 0xffffffff)
    
    out += struct.pack('>I', 0) + b'IEND' + struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff)
    
    with open(filename, 'wb') as f:
        f.write(out)

# ============================================================
# Main Generation
# ============================================================

def main():
    os.makedirs('shadow_slave_addon/ShadowSlave_RP/textures/entity', exist_ok=True)
    os.makedirs('shadow_slave_addon/ShadowSlave_RP/textures/items', exist_ok=True)
    
    print("Generating shadow_slave.png...")
    shadow_pixels = create_shadow_slave()
    write_png('shadow_slave_addon/ShadowSlave_RP/textures/entity/shadow_slave.png', 64, 64, shadow_pixels)
    print("Created shadow_slave.png")
    
    print("Creating echo_shade.png...")
    echo_pixels = create_echo_shade()
    write_png('shadow_slave_addon/ShadowSlave_RP/textures/entity/echo_shade.png', 64, 64, echo_pixels)
    print("Created echo_shade.png")
    
    print("Creating item textures...")
    essence = create_item_texture((40, 20, 80, 255), (180, 180, 255, 255))
    write_png('shadow_slave_addon/ShadowSlave_RP/textures/items/shadow_essence.png', 16, 16, essence)
    print("Created shadow_essence.png")
    
    fragment = create_item_texture((80, 180, 255, 255), (200, 220, 255, 255))
    write_png('shadow_slave_addon/ShadowSlave_RP/textures/items/soul_fragment.png', 16, 16, fragment)
    print("Created soul_fragment.png")
    
    core = create_item_texture((140, 80, 255, 255), (220, 200, 255, 255))
    write_png('shadow_slave_addon/ShadowSlave_RP/textures/items/soul_core.png', 16, 16, core)
    print("Created soul_core.png")
    
    egg = create_spawn_egg()
    write_png('shadow_slave_addon/ShadowSlave_RP/textures/items/spawn_egg.png', 16, 16, egg)
    write_png('shadow_slave_addon/ShadowSlave_RP/textures/entity/spawn_egg.png', 16, 16, egg)
    print("Created spawn_egg.png (items and entity)")
    
    print("\nAll textures generated successfully!")

if __name__ == '__main__':
    main()
