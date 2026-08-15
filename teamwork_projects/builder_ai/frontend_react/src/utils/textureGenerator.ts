import * as THREE from 'three';

// Cache generated textures so we don't recreate them every frame
const textureCache: Map<string, THREE.CanvasTexture> = new Map();

/**
 * Creates high-detail procedural architectural textures using Canvas API
 */
export function getProceduralTexture(type: 'marble' | 'wood' | 'concrete' | 'pavers' | 'water' | 'hvac' | 'solar' | 'fabric' | 'tile'): THREE.CanvasTexture {
  if (textureCache.has(type)) {
    return textureCache.get(type)!;
  }

  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');

  if (!ctx) {
    const fallback = new THREE.CanvasTexture(canvas);
    return fallback;
  }

  if (type === 'marble') {
    // Calacatta Marble with Gold/Grey Veins
    ctx.fillStyle = '#F8FAFC';
    ctx.fillRect(0, 0, 512, 512);

    ctx.strokeStyle = '#CBD5E1';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(0, 80);
    ctx.bezierCurveTo(150, 180, 250, 60, 512, 300);
    ctx.stroke();

    ctx.strokeStyle = '#D97706'; // Gold Accent Vein
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(80, 0);
    ctx.bezierCurveTo(200, 220, 320, 380, 480, 512);
    ctx.stroke();

    ctx.strokeStyle = '#94A3B8';
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(300, 0);
    ctx.bezierCurveTo(340, 180, 180, 340, 220, 512);
    ctx.stroke();

  } else if (type === 'wood') {
    // Scandinavian White Oak Hardwood Planks
    ctx.fillStyle = '#D4A373';
    ctx.fillRect(0, 0, 512, 512);

    const plankHeight = 32;
    for (let y = 0; y < 512; y += plankHeight) {
      ctx.fillStyle = y % (plankHeight * 2) === 0 ? '#C9935E' : '#DFB285';
      ctx.fillRect(0, y, 512, plankHeight - 2);

      // Plank seams
      ctx.fillStyle = '#8C5A2B';
      ctx.fillRect(0, y + plankHeight - 2, 512, 2);

      // Vertical Staggered Seams
      const stagger = (y / plankHeight) % 3;
      const seamX = (stagger * 160 + 80) % 512;
      ctx.fillRect(seamX, y, 2, plankHeight);
    }

  } else if (type === 'concrete') {
    // Architectural Formwork Concrete with Tie Holes
    ctx.fillStyle = '#475569';
    ctx.fillRect(0, 0, 512, 512);

    // Formwork Panels
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 2;
    ctx.strokeRect(4, 4, 250, 250);
    ctx.strokeRect(258, 4, 250, 250);
    ctx.strokeRect(4, 258, 250, 250);
    ctx.strokeRect(258, 258, 250, 250);

    // Tie-Rod Indents
    ctx.fillStyle = '#1E293B';
    const tiePoints = [
      [30, 30], [224, 30], [30, 224], [224, 224],
      [284, 30], [482, 30], [284, 224], [482, 224],
      [30, 284], [224, 284], [30, 482], [224, 482],
      [284, 284], [482, 284], [284, 482], [482, 482],
    ];
    tiePoints.forEach(([x, y]) => {
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    });

  } else if (type === 'pavers') {
    // Large Format Modern Exterior Paver Slabs
    ctx.fillStyle = '#1E212B';
    ctx.fillRect(0, 0, 512, 512);

    const gridSize = 64;
    ctx.strokeStyle = '#0F1117';
    ctx.lineWidth = 3;
    for (let x = 0; x < 512; x += gridSize) {
      for (let y = 0; y < 512; y += gridSize) {
        ctx.fillStyle = (x + y) % (gridSize * 2) === 0 ? '#282C37' : '#222530';
        ctx.fillRect(x + 2, y + 2, gridSize - 4, gridSize - 4);
      }
    }

  } else if (type === 'water') {
    // Pool Turquoise Water Texture
    const grad = ctx.createLinearGradient(0, 0, 512, 512);
    grad.addColorStop(0, '#06B6D4');
    grad.addColorStop(0.5, '#0284C7');
    grad.addColorStop(1, '#0369A1');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 512, 512);

    // Light Caustic Rings
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.35)';
    ctx.lineWidth = 2;
    for (let i = 0; i < 20; i++) {
      ctx.beginPath();
      ctx.arc((i * 45) % 512, (i * 70) % 512, 25 + (i % 15), 0, Math.PI * 2);
      ctx.stroke();
    }

  } else if (type === 'hvac') {
    // Industrial Chiller / HVAC Metal Louver Grille
    ctx.fillStyle = '#1E293B';
    ctx.fillRect(0, 0, 512, 512);

    ctx.fillStyle = '#0F172A';
    for (let y = 0; y < 512; y += 16) {
      ctx.fillRect(10, y, 492, 8);
    }

    ctx.strokeStyle = '#64748B';
    ctx.lineWidth = 6;
    ctx.strokeRect(6, 6, 500, 500);

  } else if (type === 'solar') {
    // Photovoltaic Solar Panel Array
    ctx.fillStyle = '#0F172A';
    ctx.fillRect(0, 0, 512, 512);

    const cellW = 80;
    const cellH = 120;
    ctx.strokeStyle = '#38BDF8';
    ctx.lineWidth = 1;

    for (let x = 10; x < 500; x += cellW + 10) {
      for (let y = 10; y < 500; y += cellH + 10) {
        ctx.fillStyle = '#1E3A8A';
        ctx.fillRect(x, y, cellW, cellH);

        // Thin busbars
        ctx.strokeRect(x, y, cellW, cellH);
        ctx.beginPath();
        ctx.moveTo(x + cellW / 2, y);
        ctx.lineTo(x + cellW / 2, y + cellH);
        ctx.stroke();
      }
    }

  } else if (type === 'fabric') {
    // Boucle / Linen Sofa Upholstery
    ctx.fillStyle = '#334155';
    ctx.fillRect(0, 0, 512, 512);

    ctx.fillStyle = '#475569';
    for (let x = 0; x < 512; x += 8) {
      for (let y = 0; y < 512; y += 8) {
        if ((x + y) % 16 === 0) {
          ctx.fillRect(x, y, 4, 4);
        }
      }
    }

  } else if (type === 'tile') {
    // Large Format Porcelain Bathroom Tiles
    ctx.fillStyle = '#E2E8F0';
    ctx.fillRect(0, 0, 512, 512);

    ctx.strokeStyle = '#94A3B8';
    ctx.lineWidth = 2;
    for (let x = 0; x < 512; x += 128) {
      for (let y = 0; y < 512; y += 128) {
        ctx.strokeRect(x, y, 128, 128);
      }
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.anisotropy = 8;
  textureCache.set(type, texture);

  return texture;
}
