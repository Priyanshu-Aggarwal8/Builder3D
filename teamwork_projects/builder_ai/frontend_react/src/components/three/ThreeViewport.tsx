import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { BuildingModel, RenderMode } from '../../types/model';
import { getProceduralTexture } from '../../utils/textureGenerator';
import { LodLevel, LOD_HIERARCHY } from '../../services/lodHierarchy';
import { PBRMaterialFactory } from '../../utils/PBRMaterialFactory';
import { ArchVizCompositeModels } from '../../utils/ArchVizCompositeModels';

export type LightingPreset = 'noon' | 'sunset' | 'night';

function createRoomBadgeSprite(title: string, sub: string, isLightMode: boolean): THREE.Sprite {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 140;
  const ctx = canvas.getContext('2d')!;

  // Background rounded pill
  ctx.fillStyle = isLightMode ? 'rgba(255, 255, 255, 0.95)' : 'rgba(0, 0, 0, 0.92)';
  ctx.strokeStyle = isLightMode ? 'rgba(0, 0, 0, 0.85)' : 'rgba(255, 255, 255, 0.35)';
  ctx.lineWidth = 5;

  ctx.beginPath();
  ctx.roundRect(8, 8, 496, 124, 62);
  ctx.fill();
  ctx.stroke();

  // Text
  ctx.fillStyle = isLightMode ? '#000000' : '#FFFFFF';
  ctx.font = 'bold 32px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(title, 256, 52);

  ctx.fillStyle = isLightMode ? '#4B5563' : '#9CA3AF';
  ctx.font = 'bold 20px monospace';
  ctx.fillText(sub, 256, 96);

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(3.6, 1.0, 1);
  return sprite;
}

function disposeHierarchy(obj: THREE.Object3D) {
  obj.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      // Dispose non-cached geometries
      if (child.geometry && !child.geometry.userData?.cached) {
        child.geometry.dispose();
      }
    }
  });
}

interface ThreeViewportProps {
  model: BuildingModel | null;
  selectedElementId?: string | null;
  renderMode?: RenderMode;
  showGrid?: boolean;
  theme?: 'dark' | 'light';
  layerVisibility?: Record<string, boolean>;
  selectedFloor?: number | null;
  explodeRatio?: number;
  isCutaway?: boolean;
  isMepGhosting?: boolean;
  sliceHeight?: number | null;
  sunAngle?: number;
  lightingPreset?: LightingPreset;
  lodLevel?: LodLevel;
  isDroneTour?: boolean;
  isFirstPerson?: boolean;
  isMeasuring?: boolean;
  onExitFirstPerson?: () => void;
  onSelectElement?: (elementId: string | null) => void;
  onCursorMove?: (worldPos: THREE.Vector3) => void;
  interactive?: boolean;
}

export const ThreeViewport: React.FC<ThreeViewportProps> = ({
  model,
  selectedElementId,
  renderMode = 'shaded',
  showGrid = true,
  layerVisibility = { structural: true, electrical: true, plumbing: true },
  selectedFloor = null,
  explodeRatio = 0.0,
  isCutaway = false,
  isMepGhosting = false,
  sliceHeight = null,
  sunAngle = Math.PI / 4,
  lightingPreset = 'noon',
  lodLevel = 'building',
  theme = 'dark',
  isDroneTour = false,
  isFirstPerson = false,
  isMeasuring = false,
  onExitFirstPerson,
  onSelectElement,
  onCursorMove,
  interactive = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const dirLightRef = useRef<THREE.DirectionalLight | null>(null);
  const hemiLightRef = useRef<THREE.HemisphereLight | null>(null);
  const ambientLightRef = useRef<THREE.AmbientLight | null>(null);
  const meshGroupRef = useRef<THREE.Group | null>(null);
  const selectionMeshRef = useRef<THREE.LineSegments | null>(null);
  const measurementLineRef = useRef<THREE.Line | null>(null);
  const gridHelperRef = useRef<THREE.GridHelper | null>(null);
  const reqIdRef = useRef<number | null>(null);

  const isFirstPersonRef = useRef(isFirstPerson);
  useEffect(() => { isFirstPersonRef.current = isFirstPerson; }, [isFirstPerson]);

  const isDroneTourRef = useRef(isDroneTour);
  useEffect(() => { isDroneTourRef.current = isDroneTour; }, [isDroneTour]);

  // Mesh map cache: elementId -> THREE.Mesh
  const meshMapRef = useRef<Map<string, THREE.Mesh>>(new Map());

  // Measurement points
  const measurePointsRef = useRef<THREE.Vector3[]>([]);

  // Camera Orbit & Drone State
  const cameraState = useRef({
    radius: 28,
    theta: Math.PI / 4, // Yaw
    phi: Math.PI / 3.2, // Pitch
    target: new THREE.Vector3(0, 3.0, 0),
    isDragging: false,
    dragButton: 0,
    lastX: 0,
    lastY: 0,
    startX: 0,
    startY: 0,
    droneAngle: 0,
    fpPos: new THREE.Vector3(0, 1.7, 12),
    fpYaw: 0,
    fpPitch: 0,
    keys: {} as Record<string, boolean>,
  });

  // 1. Smoothly Adjust Camera for Spatial Scale (LOD)
  useEffect(() => {
    const node = LOD_HIERARCHY.find((n) => n.id === lodLevel);
    if (node && !isFirstPerson) {
      cameraState.current.radius = node.cameraDistance;
      cameraState.current.target.y = node.cameraHeight * 0.2;
    }
  }, [lodLevel]);

  // 2. Initialize Scene & Renderer Once
  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x08090B);
    scene.fog = new THREE.FogExp2(0x08090B, 0.008);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 800);
    cameraRef.current = camera;

    // Renderer (clamped pixel ratio to 1.25 for maximum stability and 120 FPS performance)
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "default",
      preserveDrawingBuffer: false,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.25));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Context Loss Prevention
    const canvas = renderer.domElement;
    const handleContextLost = (e: Event) => {
      e.preventDefault();
      console.warn("WebGL Context Lost. Preserving app state.");
    };
    canvas.addEventListener('webglcontextlost', handleContextLost, false);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);
    ambientLightRef.current = ambientLight;

    const hemiLight = new THREE.HemisphereLight(0xf1f5f9, 0x0f172a, 0.6);
    scene.add(hemiLight);
    hemiLightRef.current = hemiLight;

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.45);
    dirLight.position.set(24 * Math.cos(sunAngle), 34, 24 * Math.sin(sunAngle));
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 180;
    dirLight.shadow.camera.left = -35;
    dirLight.shadow.camera.right = 35;
    dirLight.shadow.camera.top = 35;
    dirLight.shadow.camera.bottom = -35;
    dirLight.shadow.bias = -0.0003;
    scene.add(dirLight);
    dirLightRef.current = dirLight;

    // Ground Grid
    const grid = new THREE.GridHelper(100, 100, 0xD4FF32, 0x1E212B);
    grid.position.y = -0.01;
    (grid.material as THREE.Material).opacity = 0.45;
    (grid.material as THREE.Material).transparent = true;
    scene.add(grid);
    gridHelperRef.current = grid;

    // Shadow Ground Plane
    const groundGeo = new THREE.PlaneGeometry(240, 240);
    const groundMat = new THREE.ShadowMaterial({ opacity: 0.45 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.02;
    ground.receiveShadow = true;
    scene.add(ground);

    // Group for building meshes
    const meshGroup = new THREE.Group();
    scene.add(meshGroup);
    meshGroupRef.current = meshGroup;

    // Selection Wireframe Outline Box
    const selGeo = new THREE.BufferGeometry();
    const selMat = new THREE.LineBasicMaterial({ color: 0xD4FF32, linewidth: 2.5 });
    const selLine = new THREE.LineSegments(selGeo, selMat);
    selLine.visible = false;
    scene.add(selLine);
    selectionMeshRef.current = selLine;

    // Measurement Line
    const measGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]);
    const measMat = new THREE.LineDashedMaterial({ color: 0xD4FF32, dashSize: 0.4, gapSize: 0.2, linewidth: 3 });
    const measLine = new THREE.Line(measGeo, measMat);
    measLine.visible = false;
    scene.add(measLine);
    measurementLineRef.current = measLine;

    // Resize Handler
    const handleResize = () => {
      if (!container || !renderer || !camera) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // Animation Loop
    const animate = () => {
      reqIdRef.current = requestAnimationFrame(animate);
      if (!camera || !scene || !renderer) return;

      const state = cameraState.current;

      if (isDroneTourRef.current) {
        state.droneAngle += 0.006;
        const droneRadius = 32 + Math.sin(state.droneAngle * 0.5) * 4.0;
        const droneHeight = 12 + Math.cos(state.droneAngle * 0.7) * 4.0;
        
        camera.position.set(
          Math.sin(state.droneAngle) * droneRadius,
          droneHeight,
          Math.cos(state.droneAngle) * droneRadius
        );
        camera.lookAt(state.target);
      } else if (isFirstPersonRef.current) {
        const speed = state.keys['ShiftLeft'] || state.keys['ShiftRight'] ? 0.35 : 0.16;
        const forward = new THREE.Vector3(Math.sin(state.fpYaw), 0, Math.cos(state.fpYaw));
        const right = new THREE.Vector3(Math.cos(state.fpYaw), 0, -Math.sin(state.fpYaw));

        if (state.keys['KeyW'] || state.keys['ArrowUp']) state.fpPos.addScaledVector(forward, -speed);
        if (state.keys['KeyS'] || state.keys['ArrowDown']) state.fpPos.addScaledVector(forward, speed);
        if (state.keys['KeyA'] || state.keys['ArrowLeft']) state.fpPos.addScaledVector(right, -speed);
        if (state.keys['KeyD'] || state.keys['ArrowRight']) state.fpPos.addScaledVector(right, speed);
        if (state.keys['KeyQ']) state.fpPos.y -= speed;
        if (state.keys['KeyE']) state.fpPos.y += speed;

        camera.position.copy(state.fpPos);
        const lookTarget = new THREE.Vector3()
          .copy(state.fpPos)
          .add(new THREE.Vector3(
            -Math.sin(state.fpYaw) * Math.cos(state.fpPitch),
            Math.sin(state.fpPitch),
            -Math.cos(state.fpYaw) * Math.cos(state.fpPitch)
          ));
        camera.lookAt(lookTarget);
      } else {
        const x = state.target.x + state.radius * Math.sin(state.phi) * Math.sin(state.theta);
        const y = state.target.y + state.radius * Math.cos(state.phi);
        const z = state.target.z + state.radius * Math.sin(state.phi) * Math.cos(state.theta);

        camera.position.set(x, y, z);
        camera.lookAt(state.target);
      }

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      if (reqIdRef.current) cancelAnimationFrame(reqIdRef.current);
      window.removeEventListener('resize', handleResize);
      canvas.removeEventListener('webglcontextlost', handleContextLost);
      renderer.dispose();
    };
  }, []); // Run once on mount

  // 3. Update Lighting Presets (Day / Sunset / Night)
  useEffect(() => {
    if (!dirLightRef.current || !ambientLightRef.current || !hemiLightRef.current || !sceneRef.current) return;

    if (lightingPreset === 'sunset') {
      sceneRef.current.background = new THREE.Color(0x130D1A);
      sceneRef.current.fog = new THREE.FogExp2(0x130D1A, 0.008);
      dirLightRef.current.color = new THREE.Color(0xF59E0B);
      dirLightRef.current.intensity = 1.7;
      dirLightRef.current.position.set(30, 8, 20);
      ambientLightRef.current.color = new THREE.Color(0x7C2D12);
      ambientLightRef.current.intensity = 0.6;
      hemiLightRef.current.color = new THREE.Color(0xFDBA74);
      hemiLightRef.current.groundColor = new THREE.Color(0x1E1B4B);
    } else if (lightingPreset === 'night') {
      sceneRef.current.background = new THREE.Color(0x05070B);
      sceneRef.current.fog = new THREE.FogExp2(0x05070B, 0.01);
      dirLightRef.current.color = new THREE.Color(0x38BDF8);
      dirLightRef.current.intensity = 0.35;
      dirLightRef.current.position.set(10, 25, 10);
      ambientLightRef.current.color = new THREE.Color(0x1E293B);
      ambientLightRef.current.intensity = 0.4;
      hemiLightRef.current.color = new THREE.Color(0x60A5FA);
      hemiLightRef.current.groundColor = new THREE.Color(0x020617);
    } else if (theme === 'light') {
      sceneRef.current.background = new THREE.Color(0xF8FAFC);
      sceneRef.current.fog = new THREE.FogExp2(0xF8FAFC, 0.005);
      dirLightRef.current.color = new THREE.Color(0xFFFFFF);
      dirLightRef.current.intensity = 1.6;
      dirLightRef.current.position.set(24 * Math.cos(sunAngle), 34, 24 * Math.sin(sunAngle));
      ambientLightRef.current.color = new THREE.Color(0xFFFFFF);
      ambientLightRef.current.intensity = 1.0;
      hemiLightRef.current.color = new THREE.Color(0xFFFFFF);
      hemiLightRef.current.groundColor = new THREE.Color(0xE2E8F0);
    } else {
      sceneRef.current.background = new THREE.Color(0x08090B);
      sceneRef.current.fog = new THREE.FogExp2(0x08090B, 0.008);
      dirLightRef.current.color = new THREE.Color(0xFFFFFF);
      dirLightRef.current.intensity = 1.45;
      dirLightRef.current.position.set(24 * Math.cos(sunAngle), 34, 24 * Math.sin(sunAngle));
      ambientLightRef.current.color = new THREE.Color(0xFFFFFF);
      ambientLightRef.current.intensity = 0.8;
      hemiLightRef.current.color = new THREE.Color(0xF1F5F9);
      hemiLightRef.current.groundColor = new THREE.Color(0x0F172A);
    }
  }, [lightingPreset, sunAngle, theme]);

  // 4. Populate Meshes with PBR Procedural Textures Whenever Model Changes
  useEffect(() => {
    if (!meshGroupRef.current || !model) return;
    const group = meshGroupRef.current;
    meshMapRef.current.clear();

    // Clean up GPU buffers
    while (group.children.length > 0) {
      const child = group.children[0];
      disposeHierarchy(child);
      group.remove(child);
    }

    // Determine if detailed composite furniture models should be instantiated
    const isDetailedInteriorMode = isFirstPerson || selectedFloor !== null || lodLevel === 'apartment';

    Object.values(model.layers || {}).forEach((layer) => {
      const isVisible = layerVisibility[layer.id] ?? layer.visible;
      if (!isVisible) return;

      (layer.elements || []).forEach((el) => {
        if (!el || !el.position || !el.dimensions) return;
        let [x, y, z] = el.position;

        // Accurate floor level calculation based on 3.2m storey height
        const floorLevel = Math.max(1, Math.floor(Math.max(0, y) / 3.2) + 1);

        if (selectedFloor !== null && selectedFloor !== undefined && selectedFloor !== floorLevel) {
          return;
        }

        if (sliceHeight !== null && sliceHeight !== undefined && y > sliceHeight) {
          return;
        }

        if (isCutaway) {
          if (el.type === 'slab' && y > 3.0 && !el.name.includes("Roof")) return;
        }

        if (explodeRatio > 0) {
          const explodeSpacing = explodeRatio * 3.5;
          y += (floorLevel - 1) * explodeSpacing;
        }

        const w = el.dimensions.width || 1;
        const h = el.dimensions.height || 1;
        const d = el.dimensions.depth || 1;
        const nameLower = el.name.toLowerCase();
        const baseColor = el.material?.color || (layer.id === 'electrical' ? '#F59E0B' : layer.id === 'plumbing' ? '#06B6D4' : '#E2E8F0');

        const isCompositeAvailable = renderMode === 'shaded' && !isMepGhosting && lodLevel !== 'mep' && isDetailedInteriorMode;
        let renderedObject: THREE.Object3D | null = null;

        if (isCompositeAvailable) {
          if (nameLower.includes('sofa') || nameLower.includes('couch') || nameLower.includes('sectional')) {
            renderedObject = ArchVizCompositeModels.createSofaComposite(w, d, baseColor);
          } else if (nameLower.includes('kitchen') || nameLower.includes('island')) {
            renderedObject = ArchVizCompositeModels.createKitchenIslandComposite(w, d, h);
          } else if (nameLower.includes('platform_bed') || (nameLower.includes('bed') && !nameLower.includes('nightstand') && !nameLower.includes('lamp'))) {
            renderedObject = ArchVizCompositeModels.createMasterBedComposite(baseColor);
          } else if (nameLower.includes('dining')) {
            renderedObject = ArchVizCompositeModels.createDiningSetComposite();
          } else if (nameLower.includes('soaking_tub') || nameLower.includes('freestanding_tub')) {
            renderedObject = ArchVizCompositeModels.createSpaBathroomComposite();
          }
        }

        if (renderedObject) {
          renderedObject.position.set(x, y, z);
          renderedObject.userData = { elementId: el.id, element: el };
          group.add(renderedObject);
          renderedObject.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.userData = { elementId: el.id, element: el };
              if (!meshMapRef.current.has(el.id)) {
                meshMapRef.current.set(el.id, child);
              }
            }
          });
          return;
        }

        let geometry: THREE.BufferGeometry;
        if (el.type === 'column' || nameLower.includes('satellite') || nameLower.includes('faucet') || nameLower.includes('lamp')) {
          geometry = new THREE.CylinderGeometry(w / 2, w / 2, h, 16);
        } else if (el.type === 'pipe' || el.type === 'conduit') {
          geometry = new THREE.CylinderGeometry(Math.max(w, d) / 2, Math.max(w, d) / 2, h, 8);
        } else {
          geometry = new THREE.BoxGeometry(w, h, d);
        }

        let material: THREE.Material;
        if (renderMode === 'wireframe') {
          material = new THREE.MeshBasicMaterial({ color: 0x8E8F9C, wireframe: true });
        } else if (isMepGhosting || lodLevel === 'mep') {
          if (layer.id === 'electrical') {
            material = new THREE.MeshStandardMaterial({
              color: 0xF59E0B,
              emissive: new THREE.Color(0xF59E0B),
              emissiveIntensity: theme === 'light' ? 0.6 : 1.2,
              roughness: 0.2,
              metalness: 0.3,
            });
          } else if (layer.id === 'plumbing') {
            material = new THREE.MeshStandardMaterial({
              color: 0x0284C7,
              emissive: new THREE.Color(0x06B6D4),
              emissiveIntensity: theme === 'light' ? 0.6 : 1.2,
              roughness: 0.2,
              metalness: 0.4,
            });
          } else {
            material = new THREE.MeshStandardMaterial({
              color: theme === 'light' ? 0xE2E8F0 : 0x1E293B,
              transparent: true,
              opacity: theme === 'light' ? 0.45 : 0.35,
              roughness: 0.85,
              metalness: 0.05,
            });
          }
        } else if (renderMode === 'xray') {
          material = new THREE.MeshPhysicalMaterial({
            color: new THREE.Color(baseColor),
            transparent: true,
            opacity: 0.35,
            roughness: 0.2,
            transmission: 0.6,
          });
        } else {
          // OpenBIM Photorealistic PBR Material Pipeline
          if (el.type === 'window' || nameLower.includes('glass') || nameLower.includes('balustrade')) {
            material = PBRMaterialFactory.createLowEGlassMaterial(0.012, el.material?.color || '#BAE6FD');
          } else if (nameLower.includes('curtain') || nameLower.includes('drape')) {
            material = PBRMaterialFactory.createFabricMaterial('#FAFAF9', true);
          } else if (nameLower.includes('mullion') || nameLower.includes('frame') || nameLower.includes('railing')) {
            material = PBRMaterialFactory.createMetalMaterial('black_matte');
          } else if (nameLower.includes('marble') || nameLower.includes('vanity') || nameLower.includes('counter')) {
            material = PBRMaterialFactory.createCalacattaMarbleMaterial();
          } else if (nameLower.includes('wood') || nameLower.includes('timber') || nameLower.includes('deck') || nameLower.includes('parquet')) {
            material = PBRMaterialFactory.createFlutedTimberMaterial(baseColor, 32);
          } else if (nameLower.includes('sofa') || nameLower.includes('bed') || nameLower.includes('rug') || nameLower.includes('cushion') || nameLower.includes('fabric')) {
            material = PBRMaterialFactory.createFabricMaterial(baseColor);
          } else if (nameLower.includes('faucet') || nameLower.includes('handle') || nameLower.includes('mixer')) {
            material = PBRMaterialFactory.createMetalMaterial('chrome');
          } else if (nameLower.includes('water') || nameLower.includes('pool') || nameLower.includes('fountain')) {
            material = new THREE.MeshPhysicalMaterial({
              color: 0x06B6D4,
              transparent: true,
              opacity: 0.85,
              roughness: 0.05,
              metalness: 0.1,
            });
          } else if (nameLower.includes('lamp') || nameLower.includes('sconce') || nameLower.includes('pendant') || el.type === 'light') {
            material = new THREE.MeshStandardMaterial({
              color: new THREE.Color(baseColor),
              emissive: new THREE.Color(0xFFA726),
              emissiveIntensity: lightingPreset === 'night' ? 3.0 : 1.6,
              roughness: 0.1,
            });
          } else {
            material = new THREE.MeshStandardMaterial({
              color: new THREE.Color(baseColor),
              roughness: el.type === 'slab' ? 0.75 : 0.4,
              metalness: el.type === 'door' ? 0.1 : 0.04,
            });
          }
        }

        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(x, y, z);
        const shouldCast = renderMode === 'shaded' && !isMepGhosting && (el.type === 'slab' || el.type === 'wall' || el.type === 'column' || nameLower.includes('sofa') || nameLower.includes('bed'));
        mesh.castShadow = shouldCast;
        mesh.receiveShadow = renderMode === 'shaded';
        mesh.userData = { elementId: el.id, element: el };

        group.add(mesh);
        meshMapRef.current.set(el.id, mesh);
      });
    });

    // Auto-frame camera to center of the building (supports tall high-rises)
    try {
      if (group.children.length > 0) {
        const box = new THREE.Box3().setFromObject(group);
        if (!box.isEmpty()) {
          const center = new THREE.Vector3();
          const size = new THREE.Vector3();
          box.getCenter(center);
          box.getSize(size);

          cameraState.current.target.copy(center);
          const maxDim = Math.max(size.x, size.y, size.z);
          if (!isFirstPerson && !isDroneTour) {
            cameraState.current.radius = Math.max(26, maxDim * 1.5);
          }
        }
      }
    } catch (err) {
      console.warn("Camera auto-frame notice:", err);
    }
  }, [model, model?.version, layerVisibility, renderMode, selectedFloor, explodeRatio, isCutaway, isMepGhosting, sliceHeight, lightingPreset, lodLevel]);

  // Floor Isolation Zoom & Walkthrough Focus
  useEffect(() => {
    if (selectedFloor !== null && selectedFloor !== undefined) {
      const floorElevation = (selectedFloor - 1) * 3.2 + 1.6;
      cameraState.current.target.set(0, floorElevation, 0);
      if (!isFirstPerson) {
        cameraState.current.radius = 16.0;
        cameraState.current.phi = Math.PI / 3.4;
      } else {
        cameraState.current.fpPos.set(0, floorElevation + 1.4, 4.0);
      }
    }
  }, [selectedFloor, isFirstPerson]);

  // 5. Update Selection Wireframe Box Safely
  useEffect(() => {
    const selLine = selectionMeshRef.current;
    if (!selLine) return;

    if (selectedElementId && meshMapRef.current.has(selectedElementId)) {
      const targetMesh = meshMapRef.current.get(selectedElementId)!;
      try {
        const box = new THREE.Box3().setFromObject(targetMesh);
        const size = new THREE.Vector3();
        const center = new THREE.Vector3();
        box.getSize(size);
        box.getCenter(center);

        size.addScalar(0.08);
        const boxGeo = new THREE.BoxGeometry(size.x, size.y, size.z);
        const edges = new THREE.EdgesGeometry(boxGeo);
        
        selLine.geometry.dispose();
        selLine.geometry = edges;
        selLine.position.copy(center);
        selLine.visible = true;
      } catch (err) {
        console.warn("Selection box error:", err);
      }
    } else {
      selLine.visible = false;
    }
  }, [selectedElementId, explodeRatio, selectedFloor, model]);

  // 6. Pointer & Measurement Gestures
  const handlePointerDown = (e: React.PointerEvent) => {
    if (!interactive) return;
    const state = cameraState.current;
    state.isDragging = true;
    state.dragButton = e.button;
    state.lastX = e.clientX;
    state.lastY = e.clientY;
    state.startX = e.clientX;
    state.startY = e.clientY;

    if (e.button === 0 && isMeasuring && cameraRef.current && containerRef.current && measurementLineRef.current) {
      try {
        const rect = containerRef.current.getBoundingClientRect();
        const mouse = new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          -((e.clientY - rect.top) / rect.height) * 2 + 1
        );
        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(mouse, cameraRef.current);
        if (meshGroupRef.current) {
          const intersects = raycaster.intersectObjects(meshGroupRef.current.children, true);
          if (intersects.length > 0) {
            const hitPoint = intersects[0].point;
            if (measurePointsRef.current.length >= 2) {
              measurePointsRef.current = [];
            }
            measurePointsRef.current.push(hitPoint);
            if (measurePointsRef.current.length === 2) {
              const p1 = measurePointsRef.current[0];
              const p2 = measurePointsRef.current[1];
              const dist = p1.distanceTo(p2).toFixed(2);
              measurementLineRef.current.geometry.setFromPoints([p1, p2]);
              measurementLineRef.current.computeLineDistances();
              measurementLineRef.current.visible = true;
              console.log(`Measured CAD distance: ${dist} m`);
            }
          }
        }
      } catch (err) {}
    }
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!interactive) return;
    const state = cameraState.current;

    if (cameraRef.current && containerRef.current && onCursorMove) {
      try {
        const rect = containerRef.current.getBoundingClientRect();
        const mouse = new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          -((e.clientY - rect.top) / rect.height) * 2 + 1
        );
        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(mouse, cameraRef.current);
        const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
        const targetPos = new THREE.Vector3();
        raycaster.ray.intersectPlane(plane, targetPos);
        if (targetPos) onCursorMove(targetPos);
      } catch (err) {}
    }

    if (!state.isDragging || isDroneTourRef.current) return;
    const dx = e.clientX - state.lastX;
    const dy = e.clientY - state.lastY;

    if (isFirstPersonRef.current) {
      state.fpYaw -= dx * 0.003;
      state.fpPitch = Math.max(-Math.PI / 3, Math.min(Math.PI / 3, state.fpPitch - dy * 0.003));
    } else {
      if (state.dragButton === 0) {
        state.theta -= dx * 0.008;
        state.phi = Math.max(0.05, Math.min(Math.PI / 2 - 0.02, state.phi - dy * 0.008));
      } else if (state.dragButton === 2 || state.dragButton === 1) {
        const panSpeed = state.radius * 0.001;
        state.target.x -= (Math.cos(state.theta) * dx + Math.sin(state.theta) * dy) * panSpeed;
        state.target.z -= (-Math.sin(state.theta) * dx + Math.cos(state.theta) * dy) * panSpeed;
      }
    }

    state.lastX = e.clientX;
    state.lastY = e.clientY;
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    const state = cameraState.current;
    state.isDragging = false;

    // Do NOT select or raycast in first-person or drone mode
    if (!interactive || isFirstPersonRef.current || isDroneTourRef.current) return;

    // Only select on stationary click (not on orbit/drag)
    const moveDist = Math.hypot(e.clientX - (state.startX || e.clientX), e.clientY - (state.startY || e.clientY));
    if (moveDist < 4 && e.button === 0 && cameraRef.current && sceneRef.current && containerRef.current) {
      try {
        const rect = containerRef.current.getBoundingClientRect();
        const mouse = new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          -((e.clientY - rect.top) / rect.height) * 2 + 1
        );
        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(mouse, cameraRef.current);

        if (meshGroupRef.current) {
          const intersects = raycaster.intersectObjects(meshGroupRef.current.children, true);
          if (intersects.length > 0) {
            let hitObj: THREE.Object3D | null = intersects[0].object;
            let foundId: string | null = null;
            while (hitObj && hitObj !== meshGroupRef.current) {
              if (hitObj.userData?.elementId) {
                foundId = hitObj.userData.elementId;
                break;
              }
              hitObj = hitObj.parent;
            }
            if (onSelectElement) onSelectElement(foundId);
          } else {
            if (onSelectElement) onSelectElement(null);
          }
        }
      } catch (err) {
        console.error("Raycast error:", err);
      }
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    if (!interactive || isDroneTour) return;
    e.preventDefault();
    const state = cameraState.current;

    if (e.ctrlKey || e.metaKey) {
      const zoomFactor = e.deltaY > 0 ? 1.05 : 0.95;
      state.radius = Math.max(4, Math.min(180, state.radius * zoomFactor));
    } else if (e.shiftKey) {
      state.target.y = Math.max(0, state.target.y - e.deltaY * 0.02);
    } else {
      state.theta += e.deltaX * 0.005;
      state.phi = Math.max(0.05, Math.min(Math.PI / 2 - 0.02, state.phi + e.deltaY * 0.005));
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      cameraState.current.keys[e.code] = true;
      if (e.code === 'Escape' && onExitFirstPerson) {
        onExitFirstPerson();
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      cameraState.current.keys[e.code] = false;
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [onExitFirstPerson]);

  return (
    <div className="w-full h-full relative overflow-hidden">
      <div
        ref={containerRef}
        className="w-full h-full cursor-grab active:cursor-grabbing select-none overflow-hidden touch-none"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onWheel={handleWheel}
        onContextMenu={(e) => e.preventDefault()}
      />

      {/* FPS Walk Mode HUD Banner */}
      {isFirstPerson && (
        <div className="absolute top-6 left-1/2 -translate-x-1/2 z-30 px-5 py-2.5 rounded-full border shadow-2xl backdrop-blur-xl flex items-center gap-3 bg-black/90 text-white border-white/20 pointer-events-auto">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-xs font-mono font-bold">FPS WALK MODE • [W, A, S, D] to Move • Drag Mouse to Look</span>
          {onExitFirstPerson && (
            <button
              onClick={onExitFirstPerson}
              className="ml-2 px-3 py-1 rounded-full bg-white text-black text-[11px] font-black uppercase tracking-wider hover:bg-neutral-200 transition-transform active:scale-95 cursor-pointer"
            >
              Exit (ESC)
            </button>
          )}
        </div>
      )}
    </div>
  );
};
