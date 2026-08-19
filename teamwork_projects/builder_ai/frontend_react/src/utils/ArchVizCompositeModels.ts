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
   * 1. L-Sectional Bouclé Sofa with Cushions, Wooden Plinth and Accent Pillows
   */
  public static createSofaComposite(width = 3.4, depth = 2.2, colorHex = '#D6C7B2'): THREE.Group {
    const group = new THREE.Group();
    const fabricMat = PBRMaterialFactory.createFabricMaterial(colorHex);
    const accentFabricMat = PBRMaterialFactory.createFabricMaterial('#78350F');
    const plinthMat = PBRMaterialFactory.createFlutedTimberMaterial('#451A03', 16);

    // Base Plinth
    const baseGeo = this.getCachedGeometry(`sofa_base_${width}_${depth}`, () => new THREE.BoxGeometry(width, 0.08, depth));
    const baseMesh = new THREE.Mesh(baseGeo, plinthMat);
    baseMesh.position.y = 0.04;
    baseMesh.castShadow = true;
    baseMesh.receiveShadow = true;
    group.add(baseMesh);

    // Seat Platform
    const seatGeo = this.getCachedGeometry(`sofa_seat_${width}_${depth}`, () => new THREE.BoxGeometry(width - 0.04, 0.22, depth - 0.04));
    const seatMesh = new THREE.Mesh(seatGeo, fabricMat);
    seatMesh.position.y = 0.19;
    seatMesh.castShadow = true;
    group.add(seatMesh);

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
    const cushionGeo = this.getCachedGeometry(`sofa_cushion_${width}_${depth}`, () => new THREE.BoxGeometry((width - 0.35) / 3 - 0.04, 0.16, depth - 0.35));
    const cw = (width - 0.35) / 3;
    for (let i = 0; i < 3; i++) {
      const cushion = new THREE.Mesh(cushionGeo, fabricMat);
      cushion.position.set(-width / 2 + 0.35 + i * cw + cw / 2, 0.38, 0.14);
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
   * 2. Waterfall Calacatta Quartz Kitchen Island with Sink, Faucet & Induction Hob
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
   * 5. CAD-Detailed 6-Person Commercial Workstation Pod with Dual 4K Displays & Screen Dividers
   */
  public static createWorkstationClusterComposite(width = 3.6, depth = 1.4, colorHex = '#E2E8F0'): THREE.Group {
    const group = new THREE.Group();
    const deskMat = PBRMaterialFactory.createFlutedTimberMaterial('#F1F5F9', 16);
    const frameMat = PBRMaterialFactory.createMetalMaterial('black_matte');
    const acousticScreenMat = PBRMaterialFactory.createFabricMaterial('#3B82F6');
    const screenMat = new THREE.MeshStandardMaterial({
      color: 0x0F172A,
      emissive: new THREE.Color(0x38BDF8),
      emissiveIntensity: 0.35,
      roughness: 0.1,
    });
    const standMat = PBRMaterialFactory.createMetalMaterial('chrome');

    // Dual Main Desktops
    const deskGeo = this.getCachedGeometry(`workstation_top_${width}_${depth}`, () => new THREE.BoxGeometry(width, 0.04, depth));
    const deskMesh = new THREE.Mesh(deskGeo, deskMat);
    deskMesh.position.y = 0.72;
    deskMesh.castShadow = true;
    deskMesh.receiveShadow = true;
    group.add(deskMesh);

    // Steel O-Leg Structural Frames (Left, Center, Right)
    const legGeo = this.getCachedGeometry(`workstation_leg_${depth}`, () => new THREE.BoxGeometry(0.06, 0.70, depth - 0.05));
    for (const lx of [-width / 2 + 0.05, 0, width / 2 - 0.05]) {
      const leg = new THREE.Mesh(legGeo, frameMat);
      leg.position.set(lx, 0.35, 0);
      leg.castShadow = true;
      group.add(leg);
    }

    // Central Acoustic Privacy Screen Divider
    const screenDividerGeo = this.getCachedGeometry(`workstation_divider_${width}`, () => new THREE.BoxGeometry(width - 0.2, 0.42, 0.04));
    const dividerMesh = new THREE.Mesh(screenDividerGeo, acousticScreenMat);
    dividerMesh.position.set(0, 0.95, 0);
    dividerMesh.castShadow = true;
    group.add(dividerMesh);

    // 6x Dual 4K Desktop Monitors + Articulation Stands
    const monitorGeo = this.getCachedGeometry('workstation_monitor', () => new THREE.BoxGeometry(0.55, 0.32, 0.02));
    const monitorStandGeo = this.getCachedGeometry('workstation_stand', () => new THREE.CylinderGeometry(0.015, 0.015, 0.25, 8));

    const deskOffsets = [-1.1, 0, 1.1];
    for (const ox of deskOffsets) {
      for (const side of [-0.4, 0.4]) {
        // Stand
        const stand = new THREE.Mesh(monitorStandGeo, standMat);
        stand.position.set(ox, 0.72 + 0.125, side * 0.45);
        group.add(stand);

        // Screen
        const monitor = new THREE.Mesh(monitorGeo, screenMat);
        monitor.position.set(ox, 0.72 + 0.25, side * 0.45);
        monitor.rotation.y = side > 0 ? Math.PI : 0;
        group.add(monitor);
      }
    }

    return group;
  }

  /**
   * 6. CAD-Detailed Ergonomic Task Chair (5-Star Castor Base, Lumbar Mesh Back, 3D Armrests)
   */
  public static createErgonomicTaskChairComposite(colorHex = '#0F172A'): THREE.Group {
    const group = new THREE.Group();
    const meshMat = PBRMaterialFactory.createFabricMaterial(colorHex);
    const frameMat = PBRMaterialFactory.createMetalMaterial('black_matte');
    const chromeMat = PBRMaterialFactory.createMetalMaterial('chrome');

    // 5-Star Base Center Cylinder
    const cylinderGeo = this.getCachedGeometry('chair_cylinder', () => new THREE.CylinderGeometry(0.025, 0.025, 0.38, 8));
    const cylinder = new THREE.Mesh(cylinderGeo, chromeMat);
    cylinder.position.y = 0.22;
    group.add(cylinder);

    // Base Spoke Legs (5-Star)
    const spokeGeo = this.getCachedGeometry('chair_spoke', () => new THREE.BoxGeometry(0.28, 0.02, 0.03));
    for (let i = 0; i < 5; i++) {
      const angle = (i * 2 * Math.PI) / 5;
      const spoke = new THREE.Mesh(spokeGeo, frameMat);
      spoke.position.set((Math.cos(angle) * 0.28) / 2, 0.04, (Math.sin(angle) * 0.28) / 2);
      spoke.rotation.y = -angle;
      group.add(spoke);
    }

    // Contoured Seat Cushion
    const seatGeo = this.getCachedGeometry('task_chair_seat', () => new THREE.BoxGeometry(0.50, 0.08, 0.48));
    const seat = new THREE.Mesh(seatGeo, meshMat);
    seat.position.y = 0.45;
    seat.castShadow = true;
    group.add(seat);

    // Curved Lumbar Mesh Backrest
    const backGeo = this.getCachedGeometry('task_chair_back', () => new THREE.BoxGeometry(0.46, 0.52, 0.05));
    const back = new THREE.Mesh(backGeo, meshMat);
    back.position.set(0, 0.74, -0.22);
    back.rotation.x = -0.08;
    back.castShadow = true;
    group.add(back);

    // 3D Armrests (Left & Right)
    const armGeo = this.getCachedGeometry('task_chair_arm', () => new THREE.BoxGeometry(0.08, 0.24, 0.22));
    for (const ax of [-0.26, 0.26]) {
      const arm = new THREE.Mesh(armGeo, frameMat);
      arm.position.set(ax, 0.60, -0.05);
      group.add(arm);
    }

    return group;
  }

  /**
   * 7. 14-Person Executive Boardroom Table with Pop-Up AV Connectivity
   */
  public static createBoardroomConferenceComposite(width = 4.8, depth = 1.4, colorHex = '#78350F'): THREE.Group {
    const group = new THREE.Group();
    const walnutMat = PBRMaterialFactory.createFlutedTimberMaterial(colorHex, 24);
    const metalMat = PBRMaterialFactory.createMetalMaterial('black_matte');
    const avBoxMat = PBRMaterialFactory.createMetalMaterial('brushed_bronze');

    // Solid Walnut Chamfered Tabletop
    const topGeo = this.getCachedGeometry(`boardroom_top_${width}_${depth}`, () => new THREE.BoxGeometry(width, 0.08, depth));
    const top = new THREE.Mesh(topGeo, walnutMat);
    top.position.y = 0.74;
    top.castShadow = true;
    top.receiveShadow = true;
    group.add(top);

    // Pedestal Metal Stanchion Bases
    const pedGeo = this.getCachedGeometry(`boardroom_ped_${depth}`, () => new THREE.BoxGeometry(0.35, 0.70, depth - 0.3));
    for (const px of [-width / 3, width / 3]) {
      const ped = new THREE.Mesh(pedGeo, metalMat);
      ped.position.set(px, 0.35, 0);
      ped.castShadow = true;
      group.add(ped);
    }

    // Flush Pop-Up AV Cable & Media Port Boxes
    const avGeo = this.getCachedGeometry('boardroom_av_box', () => new THREE.BoxGeometry(0.40, 0.005, 0.18));
    for (const ax of [-1.2, 1.2]) {
      const av = new THREE.Mesh(avGeo, avBoxMat);
      av.position.set(ax, 0.782, 0);
      group.add(av);
    }

    return group;
  }

  /**
   * 8. Architectural Elevator Core Lobby Wall & Stainless Steel Doors (Replaces solid black box!)
   */
  public static createElevatorCoreComposite(width = 3.6, height = 3.2, depth = 3.0, wallColor = '#F1F5F9'): THREE.Group {
    const group = new THREE.Group();
    const wallMat = new THREE.MeshStandardMaterial({ color: new THREE.Color(wallColor), roughness: 0.85 });
    const steelMat = PBRMaterialFactory.createMetalMaterial('chrome');
    const indicatorMat = new THREE.MeshStandardMaterial({
      color: 0x0284C7,
      emissive: new THREE.Color(0x38BDF8),
      emissiveIntensity: 1.2,
      roughness: 0.1,
    });
    const revealMat = PBRMaterialFactory.createMetalMaterial('black_matte');

    // Main Core Wall Enclosure (Light Architectural Finish)
    const wallGeo = this.getCachedGeometry(`elev_core_wall_${width}_${height}_${depth}`, () => new THREE.BoxGeometry(width, height, depth));
    const wall = new THREE.Mesh(wallGeo, wallMat);
    wall.position.y = height / 2;
    wall.castShadow = true;
    wall.receiveShadow = true;
    group.add(wall);

    // 2x Brushed Stainless Steel Elevator Sliding Doors (Front Face)
    const doorGeo = this.getCachedGeometry('elev_door_leaf', () => new THREE.BoxGeometry(1.1, 2.3, 0.04));
    const revealGeo = this.getCachedGeometry('elev_door_reveal', () => new THREE.BoxGeometry(0.04, 2.3, 0.05));
    const indicatorGeo = this.getCachedGeometry('elev_indicator', () => new THREE.BoxGeometry(0.35, 0.12, 0.02));

    for (const dx of [-0.9, 0.9]) {
      // Steel Doors
      const door = new THREE.Mesh(doorGeo, steelMat);
      door.position.set(dx, 1.15, depth / 2 + 0.02);
      group.add(door);

      // Center Reveal Line
      const reveal = new THREE.Mesh(revealGeo, revealMat);
      reveal.position.set(dx, 1.15, depth / 2 + 0.03);
      group.add(reveal);

      // Top Directional Floor Indicator Display
      const indicator = new THREE.Mesh(indicatorGeo, indicatorMat);
      indicator.position.set(dx, 2.45, depth / 2 + 0.03);
      group.add(indicator);
    }

    return group;
  }

  /**
   * 9. Architectural Fire Stairwell Enclosure with Safety Door & Illuminated Exit Sign
   */
  public static createStairCoreComposite(width = 3.6, height = 3.2, depth = 2.8, wallColor = '#F1F5F9'): THREE.Group {
    const group = new THREE.Group();
    const wallMat = new THREE.MeshStandardMaterial({ color: new THREE.Color(wallColor), roughness: 0.85 });
    const doorMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.4, metalness: 0.3 });
    const pushBarMat = PBRMaterialFactory.createMetalMaterial('chrome');
    const exitSignMat = new THREE.MeshStandardMaterial({
      color: 0x10B981,
      emissive: new THREE.Color(0x10B981),
      emissiveIntensity: 2.0,
      roughness: 0.1,
    });

    // Core Enclosure Wall
    const wallGeo = this.getCachedGeometry(`stair_core_wall_${width}_${height}_${depth}`, () => new THREE.BoxGeometry(width, height, depth));
    const wall = new THREE.Mesh(wallGeo, wallMat);
    wall.position.y = height / 2;
    wall.castShadow = true;
    wall.receiveShadow = true;
    group.add(wall);

    // Fire Door Leaf
    const doorGeo = this.getCachedGeometry('stair_fire_door', () => new THREE.BoxGeometry(1.0, 2.2, 0.06));
    const door = new THREE.Mesh(doorGeo, doorMat);
    door.position.set(0, 1.1, depth / 2 + 0.03);
    group.add(door);

    // Panic Push-Bar
    const barGeo = this.getCachedGeometry('stair_push_bar', () => new THREE.BoxGeometry(0.85, 0.04, 0.04));
    const bar = new THREE.Mesh(barGeo, pushBarMat);
    bar.position.set(0, 1.0, depth / 2 + 0.07);
    group.add(bar);

    // Illuminated Emergency Exit Sign
    const signGeo = this.getCachedGeometry('stair_exit_sign', () => new THREE.BoxGeometry(0.35, 0.12, 0.04));
    const sign = new THREE.Mesh(signGeo, exitSignMat);
    sign.position.set(0, 2.35, depth / 2 + 0.05);
    group.add(sign);

    return group;
  }

  /**
   * 10. Private Acoustic Focus & Phone Pod
   */
  public static createFocusPodComposite(colorHex = '#334155'): THREE.Group {
    const group = new THREE.Group();
    const acousticMat = PBRMaterialFactory.createFabricMaterial(colorHex);
    const glassMat = PBRMaterialFactory.createLowEGlassMaterial(0.01, '#BAE6FD');
    const woodMat = PBRMaterialFactory.createFlutedTimberMaterial('#D4A373', 16);
    const handleMat = PBRMaterialFactory.createMetalMaterial('chrome');

    // Pod Shell (U-shaped Acoustic Walls & Roof)
    const shellGeo = this.getCachedGeometry('focus_pod_shell', () => new THREE.BoxGeometry(1.4, 2.4, 1.4));
    const shell = new THREE.Mesh(shellGeo, acousticMat);
    shell.position.y = 1.2;
    shell.castShadow = true;
    group.add(shell);

    // Glass Front Door
    const doorGeo = this.getCachedGeometry('focus_pod_door', () => new THREE.BoxGeometry(0.8, 2.1, 0.04));
    const door = new THREE.Mesh(doorGeo, glassMat);
    door.position.set(0, 1.1, 0.72);
    group.add(door);

    // Handle
    const handleGeo = this.getCachedGeometry('focus_pod_handle', () => new THREE.CylinderGeometry(0.015, 0.015, 0.45, 8));
    const handle = new THREE.Mesh(handleGeo, handleMat);
    handle.position.set(0.32, 1.05, 0.75);
    group.add(handle);

    // Integrated Desktop
    const deskGeo = this.getCachedGeometry('focus_pod_desk', () => new THREE.BoxGeometry(0.9, 0.04, 0.45));
    const desk = new THREE.Mesh(deskGeo, woodMat);
    desk.position.set(0, 0.95, -0.2);
    group.add(desk);

    return group;
  }

  /**
   * 11. Spa Bathroom with Freestanding Soaking Tub
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
