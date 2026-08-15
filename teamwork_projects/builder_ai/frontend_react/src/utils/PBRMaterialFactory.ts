import * as THREE from 'three';

export class PBRMaterialFactory {
  private static textureCache: Map<string, THREE.CanvasTexture> = new Map();
  private static materialCache: Map<string, THREE.Material> = new Map();

  /**
   * 1. Fine Fabric Weave (Sofas, Cushions, Bed Linen)
   */
  public static createFabricMaterial(colorHex: string | number = 0xD6C7B2, isSheer = false): THREE.MeshStandardMaterial {
    const key = `fabric_${colorHex}_${isSheer}`;
    if (this.materialCache.has(key)) return this.materialCache.get(key) as THREE.MeshStandardMaterial;

    const normalMap = this.generateFabricNormalMap();
    const mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(colorHex),
      roughness: 0.9,
      metalness: 0.0,
      normalMap,
      normalScale: new THREE.Vector2(0.5, 0.5),
      transparent: isSheer,
      opacity: isSheer ? 0.75 : 1.0,
    });
    this.materialCache.set(key, mat);
    return mat;
  }

  /**
   * 2. Calacatta Polished Marble (Kitchen Islands, Bath Vanities, Floors)
   */
  public static createCalacattaMarbleMaterial(): THREE.MeshStandardMaterial {
    const key = 'calacatta_marble_mat';
    if (this.materialCache.has(key)) return this.materialCache.get(key) as THREE.MeshStandardMaterial;

    const diffuseMap = this.generateMarbleTexture();
    const mat = new THREE.MeshStandardMaterial({
      map: diffuseMap,
      roughness: 0.15,
      metalness: 0.05,
    });
    this.materialCache.set(key, mat);
    return mat;
  }

  /**
   * 3. Fluted Slatted Timber (Wall Paneling, Island Base, Headboards)
   */
  public static createFlutedTimberMaterial(colorHex: string | number = 0xC9935E, ribCount = 32): THREE.MeshStandardMaterial {
    const key = `fluted_${colorHex}_${ribCount}`;
    if (this.materialCache.has(key)) return this.materialCache.get(key) as THREE.MeshStandardMaterial;

    const normalMap = this.generateFlutedNormalMap(ribCount);
    const mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(colorHex),
      normalMap,
      normalScale: new THREE.Vector2(1.2, 1.2),
      roughness: 0.45,
      metalness: 0.0,
    });
    this.materialCache.set(key, mat);
    return mat;
  }

  /**
   * 4. High-Performance Low-E Architectural Glass (Windows, Balustrades)
   */
  public static createLowEGlassMaterial(_thicknessMeters = 0.012, tintHex: string | number = 0xBAE6FD): THREE.MeshPhysicalMaterial {
    const key = `low_e_glass_${tintHex}`;
    if (this.materialCache.has(key)) return this.materialCache.get(key) as THREE.MeshPhysicalMaterial;

    const mat = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color(tintHex),
      transparent: true,
      opacity: 0.42,
      roughness: 0.04,
      metalness: 0.1,
      reflectivity: 0.9,
    });
    this.materialCache.set(key, mat);
    return mat;
  }

  /**
   * 5. Metallic Architectural Finishes (Faucets, Mullions, Frames)
   */
  public static createMetalMaterial(type: 'chrome' | 'black_matte' | 'brushed_bronze' | 'stainless'): THREE.MeshStandardMaterial {
    const key = `metal_${type}`;
    if (this.materialCache.has(key)) return this.materialCache.get(key) as THREE.MeshStandardMaterial;

    let mat: THREE.MeshStandardMaterial;
    switch (type) {
      case 'chrome':
        mat = new THREE.MeshStandardMaterial({ color: 0xF1F5F9, roughness: 0.08, metalness: 0.95 });
        break;
      case 'black_matte':
        mat = new THREE.MeshStandardMaterial({ color: 0x1A1A1A, roughness: 0.35, metalness: 0.8 });
        break;
      case 'brushed_bronze':
        mat = new THREE.MeshStandardMaterial({ color: 0xB45309, roughness: 0.25, metalness: 0.85 });
        break;
      case 'stainless':
      default:
        mat = new THREE.MeshStandardMaterial({ color: 0x94A3B8, roughness: 0.2, metalness: 0.9 });
        break;
    }
    this.materialCache.set(key, mat);
    return mat;
  }

  /**
   * Procedural Normal Map for Fluted Ribs (256x256 high-perf)
   */
  private static generateFlutedNormalMap(ribs: number): THREE.CanvasTexture {
    const key = `fluted_tex_${ribs}`;
    if (this.textureCache.has(key)) return this.textureCache.get(key)!;

    const size = 256;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d')!;
    const imgData = ctx.createImageData(size, size);

    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const u = (x / size) * ribs * 2 * Math.PI;
        const slopeX = -Math.sin(u) * 0.8;
        const nx = slopeX;
        const ny = 0.0;
        const nz = 1.0;
        const len = Math.hypot(nx, ny, nz);

        const idx = (y * size + x) * 4;
        imgData.data[idx] = Math.floor(((nx / len) * 0.5 + 0.5) * 255);
        imgData.data[idx + 1] = Math.floor(((ny / len) * 0.5 + 0.5) * 255);
        imgData.data[idx + 2] = Math.floor(((nz / len) * 0.5 + 0.5) * 255);
        imgData.data[idx + 3] = 255;
      }
    }
    ctx.putImageData(imgData, 0, 0);

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.generateMipmaps = false;
    texture.minFilter = THREE.LinearFilter;
    this.textureCache.set(key, texture);
    return texture;
  }

  /**
   * Procedural Micro-Weave Normal Map for Fabrics (128x128 high-perf)
   */
  private static generateFabricNormalMap(): THREE.CanvasTexture {
    const key = 'fabric_normal_tex';
    if (this.textureCache.has(key)) return this.textureCache.get(key)!;
    const size = 128;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d')!;
    const imgData = ctx.createImageData(size, size);

    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const u = (x / size) * 32 * Math.PI;
        const v = (y / size) * 32 * Math.PI;
        const nx = Math.sin(u) * Math.cos(v) * 0.3;
        const ny = Math.cos(u) * Math.sin(v) * 0.3;
        const nz = 1.0;
        const len = Math.hypot(nx, ny, nz);

        const idx = (y * size + x) * 4;
        imgData.data[idx] = Math.floor(((nx / len) * 0.5 + 0.5) * 255);
        imgData.data[idx + 1] = Math.floor(((ny / len) * 0.5 + 0.5) * 255);
        imgData.data[idx + 2] = Math.floor(((nz / len) * 0.5 + 0.5) * 255);
        imgData.data[idx + 3] = 255;
      }
    }
    ctx.putImageData(imgData, 0, 0);
    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(4, 4);
    texture.generateMipmaps = false;
    texture.minFilter = THREE.LinearFilter;
    this.textureCache.set(key, texture);
    return texture;
  }

  /**
   * Procedural Calacatta Marble Diffuse Map (512x512 high-perf)
   */
  private static generateMarbleTexture(): THREE.CanvasTexture {
    const key = 'calacatta_marble_tex';
    if (this.textureCache.has(key)) return this.textureCache.get(key)!;

    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext('2d')!;

    // Polished white marble base
    ctx.fillStyle = '#FAF9F6';
    ctx.fillRect(0, 0, 512, 512);

    // Primary smoky grey veining
    ctx.strokeStyle = '#D1D5DB';
    ctx.lineWidth = 3.0;
    ctx.beginPath();
    ctx.moveTo(0, 90);
    ctx.bezierCurveTo(160, 210, 310, 60, 512, 340);
    ctx.stroke();

    // Warm Calacatta gold vein
    ctx.strokeStyle = '#D97706';
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.moveTo(90, 0);
    ctx.bezierCurveTo(210, 240, 340, 390, 490, 512);
    ctx.stroke();

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.generateMipmaps = false;
    texture.minFilter = THREE.LinearFilter;
    this.textureCache.set(key, texture);
    return texture;
  }
}
