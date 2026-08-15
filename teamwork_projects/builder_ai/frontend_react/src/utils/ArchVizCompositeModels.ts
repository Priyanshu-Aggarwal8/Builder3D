import * as THREE from 'three';
import { PBRMaterialFactory } from './PBRMaterialFactory';

export class ArchVizCompositeModels {
  // Shared geometry cache to eliminate GPU memory leaks and duplicate buffer allocations
  private static geoCache: Map<string, THREE.BufferGeometry> = new Map();

  private static getCachedGeometry<T extends THREE.BufferGeometry>(key: string, creator: () => T): T {
    if (!this.geoCache.has(key)) {
      this.geoCache.set(key, creator());
    }
    return this.geoCache.get(key) as T;
  }

  /**
   * 1. L-Sectional Bouclé Sofa with Cushions and Pillows (Optimized)
   */
  public static createSofaComposite(width = 3.4, depth = 2.2, colorHex = '#D6C7B2'): THREE.Group {
    const group = new THREE.Group();
    const fabricMat = PBRMaterialFactory.createFabricMaterial(colorHex);
    const accentFabricMat = PBRMaterialFactory.createFabricMaterial('#78350F');

    // Base Plinth
    const baseGeo = this.getCachedGeometry(`sofa_base_${width}_${depth}`, () => new THREE.BoxGeometry(width, 0.22, depth));
    const baseMesh = new THREE.Mesh(baseGeo, fabricMat);
    baseMesh.position.y = 0.11;
    baseMesh.castShadow = true;
    baseMesh.receiveShadow = true;
    group.add(baseMesh);

    // Backrest Main
    const backGeoMain = this.getCachedGeometry(`sofa_back_${width}`, () => new THREE.BoxGeometry(width, 0.55, 0.28));
    const backMeshMain = new THREE.Mesh(backGeoMain, fabricMat);
    backMeshMain.position.set(0, 0.48, -depth / 2 + 0.14);
    group.add(backMeshMain);

    // Backrest Side
    const backGeoSide = this.getCachedGeometry(`sofa_side_${depth}`, () => new THREE.BoxGeometry(0.28, 0.55, depth - 0.28));
    const backMeshSide = new THREE.Mesh(backGeoSide, fabricMat);
    backMeshSide.position.set(-width / 2 + 0.14, 0.48, 0.14);
    group.add(backMeshSide);

    // Cushions
    const cushionGeo = this.getCachedGeometry(`sofa_cushion_${width}_${depth}`, () => new THREE.BoxGeometry((width - 0.35) / 3 - 0.04, 0.18, depth - 0.35));
    const cw = (width - 0.35) / 3;
    for (let i = 0; i < 3; i++) {
      const cushion = new THREE.Mesh(cushionGeo, fabricMat);
      cushion.position.set(-width / 2 + 0.35 + i * cw + cw / 2, 0.31, 0.14);
      group.add(cushion);
    }

    // Throw Pillows
    const pillowGeo = this.getCachedGeometry('sofa_pillow', () => new THREE.BoxGeometry(0.45, 0.45, 0.14));
    const pillow1 = new THREE.Mesh(pillowGeo, accentFabricMat);
    pillow1.position.set(-width / 2 + 0.5, 0.45, -depth / 2 + 0.38);
    pillow1.rotation.set(0, 0.25, -0.15);
    group.add(pillow1);

    const pillow2 = new THREE.Mesh(pillowGeo, fabricMat);
    pillow2.position.set(width / 2 - 0.6, 0.45, -depth / 2 + 0.38);
    pillow2.rotation.set(0, -0.2, 0);
    group.add(pillow2);

    return group;
  }

  /**
   * 2. Waterfall Calacatta Quartz Kitchen Island with Sink & Faucet
   */
  public static createKitchenIslandComposite(length = 2.8, width = 1.1, height = 0.95): THREE.Group {
    const group = new THREE.Group();
    const marbleMat = PBRMaterialFactory.createCalacattaMarbleMaterial();
    const flutedWoodMat = PBRMaterialFactory.createFlutedTimberMaterial('#8B5A2B', 36);
    const chromeMat = PBRMaterialFactory.createMetalMaterial('chrome');
    const blackMat = PBRMaterialFactory.createMetalMaterial('black_matte');

    // Base Cabinet
    const baseGeo = this.getCachedGeometry(`island_base_${length}_${width}_${height}`, () => new THREE.BoxGeometry(length - 0.12, height - 0.08, width - 0.12));
    const baseMesh = new THREE.Mesh(baseGeo, flutedWoodMat);
    baseMesh.position.y = (height - 0.08) / 2;
    baseMesh.castShadow = true;
    baseMesh.receiveShadow = true;
    group.add(baseMesh);

    // Waterfall Top Slab
    const topGeo = this.getCachedGeometry(`island_top_${length}_${width}`, () => new THREE.BoxGeometry(length, 0.08, width));
    const topMesh = new THREE.Mesh(topGeo, marbleMat);
    topMesh.position.y = height - 0.04;
    topMesh.castShadow = true;
    group.add(topMesh);

    // Waterfall Left & Right Legs
    const legGeo = this.getCachedGeometry(`island_leg_${height}_${width}`, () => new THREE.BoxGeometry(0.08, height, width));
    const leftLeg = new THREE.Mesh(legGeo, marbleMat);
    leftLeg.position.set(-length / 2 + 0.04, height / 2, 0);
    group.add(leftLeg);

    const rightLeg = new THREE.Mesh(legGeo, marbleMat);
    rightLeg.position.set(length / 2 - 0.04, height / 2, 0);
    group.add(rightLeg);

    // Undermount Sink
    const sinkGeo = this.getCachedGeometry('island_sink', () => new THREE.BoxGeometry(0.55, 0.22, 0.42));
    const sinkMesh = new THREE.Mesh(sinkGeo, chromeMat);
    sinkMesh.position.set(-0.55, height - 0.12, 0);
    group.add(sinkMesh);

    // Faucet
    const faucetGeo = this.getCachedGeometry('island_faucet', () => new THREE.CylinderGeometry(0.015, 0.015, 0.42, 8));
    const faucetMesh = new THREE.Mesh(faucetGeo, blackMat);
    faucetMesh.position.set(-0.55, height + 0.21, -0.15);
    group.add(faucetMesh);

    // Induction Cooktop
    const hobGeo = this.getCachedGeometry('island_hob', () => new THREE.BoxGeometry(0.65, 0.008, 0.52));
    const hobMat = PBRMaterialFactory.createMetalMaterial('black_matte');
    const hobMesh = new THREE.Mesh(hobGeo, hobMat);
    hobMesh.position.set(0.55, height + 0.004, 0);
    group.add(hobMesh);

    return group;
  }

  /**
   * 3. Master Suite Platform Bed with Headboard, Linen & Nightstands
   */
  public static createMasterBedComposite(colorHex = '#D6C7B2'): THREE.Group {
    const group = new THREE.Group();
    const woodMat = PBRMaterialFactory.createFlutedTimberMaterial('#78350F', 40);
    const linenMat = PBRMaterialFactory.createFabricMaterial('#F8FAFC');
    const headboardMat = PBRMaterialFactory.createFabricMaterial(colorHex);

    // Platform Base
    const baseGeo = this.getCachedGeometry('bed_base', () => new THREE.BoxGeometry(2.3, 0.25, 2.5));
    const baseMesh = new THREE.Mesh(baseGeo, woodMat);
    baseMesh.position.y = 0.125;
    baseMesh.castShadow = true;
    group.add(baseMesh);

    // Mattress
    const matGeo = this.getCachedGeometry('bed_mattress', () => new THREE.BoxGeometry(2.0, 0.32, 2.2));
    const matMesh = new THREE.Mesh(matGeo, linenMat);
    matMesh.position.set(0, 0.38, -0.1);
    group.add(matMesh);

    // Acoustic Headboard
    const headGeo = this.getCachedGeometry('bed_headboard', () => new THREE.BoxGeometry(3.2, 1.4, 0.12));
    const headMesh = new THREE.Mesh(headGeo, headboardMat);
    headMesh.position.set(0, 0.85, -1.25);
    group.add(headMesh);

    // Pillows
    const pillowGeo = this.getCachedGeometry('bed_pillow', () => new THREE.BoxGeometry(0.65, 0.14, 0.45));
    for (const side of [-0.55, 0.55]) {
      const pillow = new THREE.Mesh(pillowGeo, linenMat);
      pillow.position.set(side, 0.58, -0.85);
      pillow.rotation.x = -0.2;
      group.add(pillow);
    }

    // Bedside Nightstands (Left & Right)
    const standGeo = this.getCachedGeometry('bed_stand', () => new THREE.BoxGeometry(0.55, 0.45, 0.48));
    const lampGeo = this.getCachedGeometry('bed_lamp', () => new THREE.CylinderGeometry(0.12, 0.16, 0.24, 12));
    const lampMat = PBRMaterialFactory.createMetalMaterial('brushed_bronze');

    for (const side of [-1, 1]) {
      const standMesh = new THREE.Mesh(standGeo, woodMat);
      standMesh.position.set(side * 1.5, 0.225, -1.0);
      group.add(standMesh);

      const lamp = new THREE.Mesh(lampGeo, lampMat);
      lamp.position.set(side * 1.5, 0.57, -1.0);
      group.add(lamp);
    }

    return group;
  }

  /**
   * 4. Solid Walnut Dining Table with 6 Chairs
   */
  public static createDiningSetComposite(): THREE.Group {
    const group = new THREE.Group();
    const woodMat = PBRMaterialFactory.createFlutedTimberMaterial('#5C3D2E', 24);
    const fabricMat = PBRMaterialFactory.createFabricMaterial('#E2E8F0');
    const blackMat = PBRMaterialFactory.createMetalMaterial('black_matte');

    // Tabletop
    const topGeo = this.getCachedGeometry('dining_top', () => new THREE.BoxGeometry(2.6, 0.06, 1.1));
    const topMesh = new THREE.Mesh(topGeo, woodMat);
    topMesh.position.y = 0.75;
    topMesh.castShadow = true;
    group.add(topMesh);

    // Corner Legs
    const legGeo = this.getCachedGeometry('dining_leg', () => new THREE.CylinderGeometry(0.03, 0.02, 0.72, 8));
    for (const lx of [-1.15, 1.15]) {
      for (const lz of [-0.42, 0.42]) {
        const leg = new THREE.Mesh(legGeo, blackMat);
        leg.position.set(lx, 0.36, lz);
        group.add(leg);
      }
    }

    // Chairs (Instanced Seat & Back)
    const seatGeo = this.getCachedGeometry('chair_seat', () => new THREE.BoxGeometry(0.46, 0.05, 0.46));
    const backGeo = this.getCachedGeometry('chair_back', () => new THREE.BoxGeometry(0.46, 0.42, 0.04));

    const chairPositions = [
      [-0.8, -0.65, 0], [0, -0.65, 0], [0.8, -0.65, 0],
      [-0.8, 0.65, Math.PI], [0, 0.65, Math.PI], [0.8, 0.65, Math.PI]
    ];

    chairPositions.forEach(([cx, cz, rot]) => {
      const chair = new THREE.Group();
      chair.position.set(cx, 0, cz);
      chair.rotation.y = rot;

      const seat = new THREE.Mesh(seatGeo, fabricMat);
      seat.position.y = 0.46;
      chair.add(seat);

      const back = new THREE.Mesh(backGeo, fabricMat);
      back.position.set(0, 0.68, -0.21);
      chair.add(back);

      group.add(chair);
    });

    return group;
  }

  /**
   * 5. Spa Bathroom with Freestanding Soaking Tub
   */
  public static createSpaBathroomComposite(): THREE.Group {
    const group = new THREE.Group();
    const tubMat = PBRMaterialFactory.createFabricMaterial('#FAFAFA');
    const chromeMat = PBRMaterialFactory.createMetalMaterial('chrome');

    // Oval Tub
    const tubGeo = this.getCachedGeometry('bath_tub', () => {
      const g = new THREE.CylinderGeometry(0.55, 0.45, 0.62, 16);
      g.scale(1.7, 1.0, 1.0);
      return g;
    });
    const tubMesh = new THREE.Mesh(tubGeo, tubMat);
    tubMesh.position.set(0, 0.31, 0);
    tubMesh.castShadow = true;
    group.add(tubMesh);

    // Tub Mixer Faucet
    const faucetGeo = this.getCachedGeometry('bath_faucet', () => new THREE.CylinderGeometry(0.02, 0.02, 0.95, 8));
    const faucet = new THREE.Mesh(faucetGeo, chromeMat);
    faucet.position.set(1.0, 0.475, 0);
    group.add(faucet);

    return group;
  }
}
