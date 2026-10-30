import React, { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { Node, VM } from "../api";
import {
  RotateCcw,
  Eye,
  Server,
  Layers,
  Cpu,
  Terminal,
  Activity,
  Zap,
  ShieldCheck,
  AlertTriangle,
  Info,
} from "lucide-react";

interface ClusterSceneProps {
  nodes: Node[];
  vms: VM[];
  selectedNodeId: string | null;
  selectedVmId: string | null;
  onSelectNode: (nodeId: string | null) => void;
  onSelectVm: (vmId: string | null) => void;
  onOpenTerminal?: (vm: VM) => void;
  cinematicStage?: number; // 0 to 4
  cinematicProgress?: number; // continuous float 0.0 to 4.0
  isFullViewport?: boolean;
}

// Camera keyframes for the 5 cinematic stages
const STAGE_KEYFRAMES = [
  // 0: Origin (High wide establishing shot above central controller)
  { pos: new THREE.Vector3(0, 14, 25), look: new THREE.Vector3(0, 2.2, 0) },
  // 1: Hosts (Glides toward Node A and Node B)
  { pos: new THREE.Vector3(-7, 9.2, 18), look: new THREE.Vector3(-3.2, 1.8, 0) },
  // 2: Fabric (Low-angle tracking along luminous network bus)
  { pos: new THREE.Vector3(0, 4.2, 13), look: new THREE.Vector3(0, 1.8, -1.2) },
  // 3: Workloads (Sweeping close-up of worker node A and its microVM instances)
  { pos: new THREE.Vector3(-8.8, 5.0, 7.2), look: new THREE.Vector3(-8.5, 1.6, 0.5) },
  // 4: Launchpad (Grand pullback framing the full digital cluster universe)
  { pos: new THREE.Vector3(0, 17, 28), look: new THREE.Vector3(0, 1.8, 0) },
];

export const ClusterScene: React.FC<ClusterSceneProps> = ({
  nodes,
  vms,
  selectedNodeId,
  selectedVmId,
  onSelectNode,
  onSelectVm,
  onOpenTerminal,
  cinematicStage,
  cinematicProgress,
  isFullViewport = false,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [viewMode, setViewMode] = useState<"3d" | "2d">("3d");
  const [webGlAvailable, setWebGlAvailable] = useState<boolean>(true);
  const [hoveredEntity, setHoveredEntity] = useState<{
    type: "controller" | "node" | "vm";
    id: string;
    name: string;
    details?: string;
  } | null>(null);

  // References for Three.js state
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const animFrameIdRef = useRef<number | null>(null);
  const clickableObjectsRef = useRef<THREE.Object3D[]>([]);
  const envTextureRef = useRef<THREE.WebGLRenderTarget | null>(null);

  // Camera animation target
  const targetCameraPosRef = useRef<THREE.Vector3>(new THREE.Vector3(0, 14, 25));
  const targetLookAtRef = useRef<THREE.Vector3>(new THREE.Vector3(0, 2.2, 0));
  const isTransitioningRef = useRef<boolean>(false);

  // Animated elements references
  const controllerSculptureRef = useRef<THREE.Group | null>(null);
  const controllerRingsRef = useRef<THREE.Mesh[]>([]);
  const controllerInnerCoreRef = useRef<THREE.Mesh | null>(null);
  const nodeBeaconsRef = useRef<THREE.Mesh[]>([]);
  const vmGroupRefs = useRef<{ group: THREE.Group; baseAngle: number; radius: number; speed: number }[]>([]);
  const distantMonolithsRef = useRef<THREE.Group | null>(null);

  // Flowing network trails
  const networkCurveARef = useRef<{ curve: THREE.CubicBezierCurve3; pointsMesh: THREE.Points; progress: Float32Array; speeds: Float32Array } | null>(null);
  const networkCurveBRef = useRef<{ curve: THREE.CubicBezierCurve3; pointsMesh: THREE.Points; progress: Float32Array; speeds: Float32Array } | null>(null);

  const defaultCameraPos = new THREE.Vector3(0, 14, 25);
  const defaultLookAt = new THREE.Vector3(0, 2.2, 0);

  // Check prefers-reduced-motion
  const prefersReducedMotion =
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // React to continuous cinematic progress or stage changes
  useEffect(() => {
    if (!cameraRef.current || !controlsRef.current) return;

    let targetPos: THREE.Vector3;
    let targetLook: THREE.Vector3;

    if (cinematicProgress !== undefined) {
      const p = Math.max(0, Math.min(STAGE_KEYFRAMES.length - 1, cinematicProgress));
      const idx = Math.min(STAGE_KEYFRAMES.length - 2, Math.floor(p));
      const frac = p - idx;
      // Smooth cosine interpolation
      const smoothT = 0.5 - 0.5 * Math.cos(frac * Math.PI);

      targetPos = new THREE.Vector3().lerpVectors(STAGE_KEYFRAMES[idx].pos, STAGE_KEYFRAMES[idx + 1].pos, smoothT);
      targetLook = new THREE.Vector3().lerpVectors(STAGE_KEYFRAMES[idx].look, STAGE_KEYFRAMES[idx + 1].look, smoothT);
    } else if (cinematicStage !== undefined && STAGE_KEYFRAMES[cinematicStage]) {
      targetPos = STAGE_KEYFRAMES[cinematicStage].pos.clone();
      targetLook = STAGE_KEYFRAMES[cinematicStage].look.clone();
    } else {
      return;
    }

    targetCameraPosRef.current.copy(targetPos);
    targetLookAtRef.current.copy(targetLook);
    isTransitioningRef.current = true;

    if (prefersReducedMotion) {
      cameraRef.current.position.copy(targetPos);
      controlsRef.current.target.copy(targetLook);
      isTransitioningRef.current = false;
    }
  }, [cinematicProgress, cinematicStage, prefersReducedMotion]);

  // Initialize Three.js Scene
  useEffect(() => {
    if (viewMode !== "3d" || !mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || 500;

    // 1. Scene with Cinematic Midnight Blue background and deep navy atmospheric fog
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x0a1428); // Midnight blue (#0A1428)
    scene.fog = new THREE.FogExp2(0x0a1428, 0.016);

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 150);
    camera.position.copy(defaultCameraPos);
    cameraRef.current = camera;

    // 3. Renderer with antialiasing and ACESFilmic tone mapping
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false,
        powerPreference: "high-performance",
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.25;
      rendererRef.current = renderer;
      container.innerHTML = "";
      container.appendChild(renderer.domElement);
      setWebGlAvailable(true);
    } catch (e) {
      console.warn("WebGL initialization failed, falling back to 2D schematic:", e);
      setWebGlAvailable(false);
      setViewMode("2d");
      return;
    }

    // 4. Generate Studio HDR-Equivalent Environment Map via PMREMGenerator
    // This provides realistic specular reflections, sheen, and iridescence to all glass materials!
    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    pmremGenerator.compileEquirectangularShader();

    const envScene = new THREE.Scene();
    // Sky gradient sphere
    const envDomeGeo = new THREE.SphereGeometry(60, 32, 16);
    const envDomeMat = new THREE.MeshBasicMaterial({
      color: 0x0a1428,
      side: THREE.BackSide,
    });
    const envDome = new THREE.Mesh(envDomeGeo, envDomeMat);
    envScene.add(envDome);

    // Studio specular cards for rich reflections on glass:
    // Overhead Soft White Key Box
    const topKeyGeo = new THREE.PlaneGeometry(35, 35);
    const topKeyMat = new THREE.MeshBasicMaterial({ color: 0xf4f6ff });
    const topKey = new THREE.Mesh(topKeyGeo, topKeyMat);
    topKey.position.set(0, 40, 5);
    topKey.rotation.x = Math.PI / 2;
    envScene.add(topKey);

    // Left Cobalt Blue Specular Panel
    const cobaltCardGeo = new THREE.PlaneGeometry(35, 25);
    const cobaltCardMat = new THREE.MeshBasicMaterial({ color: 0x3158c9 });
    const cobaltCard = new THREE.Mesh(cobaltCardGeo, cobaltCardMat);
    cobaltCard.position.set(-35, 18, -10);
    cobaltCard.rotation.y = Math.PI / 3;
    envScene.add(cobaltCard);

    // Right Electric Cyan Specular Panel
    const cyanCardGeo = new THREE.PlaneGeometry(35, 25);
    const cyanCardMat = new THREE.MeshBasicMaterial({ color: 0x00d9ff });
    const cyanCard = new THREE.Mesh(cyanCardGeo, cyanCardMat);
    cyanCard.position.set(35, 18, 10);
    cyanCard.rotation.y = -Math.PI / 3;
    envScene.add(cyanCard);

    // Rear Periwinkle Accent Panel
    const periCardGeo = new THREE.PlaneGeometry(40, 20);
    const periCardMat = new THREE.MeshBasicMaterial({ color: 0x8fa8ff });
    const periCard = new THREE.Mesh(periCardGeo, periCardMat);
    periCard.position.set(0, 22, -40);
    envScene.add(periCard);

    const envRenderTarget = pmremGenerator.fromScene(envScene, 0.04);
    scene.environment = envRenderTarget.texture;
    envTextureRef.current = envRenderTarget;

    // Clean up temporary environment generation objects
    envDomeGeo.dispose();
    envDomeMat.dispose();
    topKeyGeo.dispose();
    topKeyMat.dispose();
    cobaltCardGeo.dispose();
    cobaltCardMat.dispose();
    cyanCardGeo.dispose();
    cyanCardMat.dispose();
    periCardGeo.dispose();
    periCardMat.dispose();
    pmremGenerator.dispose();

    // 5. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2.05;
    controls.minDistance = 6;
    controls.maxDistance = 55;
    controls.target.copy(defaultLookAt);
    controlsRef.current = controls;

    // 6. Lighting: Cinematic Blue Environment Lighting
    // Deep navy ambient fill ensuring shadows are never pitch black
    const ambientLight = new THREE.AmbientLight(0x101827, 2.0);
    scene.add(ambientLight);

    // Soft white studio key light
    const dirLight = new THREE.DirectionalLight(0xf4f6ff, 2.2);
    dirLight.position.set(18, 30, 22);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 1024;
    dirLight.shadow.mapSize.height = 1024;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 90;
    dirLight.shadow.bias = -0.0004;
    scene.add(dirLight);

    // Cobalt blue fill light from left/back
    const cobaltFill = new THREE.DirectionalLight(0x3158c9, 1.4);
    cobaltFill.position.set(-24, 18, -12);
    scene.add(cobaltFill);

    // Electric cyan rim light from behind to trace glass edges
    const cyanRim = new THREE.DirectionalLight(0x00d9ff, 1.5);
    cyanRim.position.set(0, 12, -26);
    scene.add(cyanRim);

    // Node A local rim point light (Jade/Mint)
    const nodeALight = new THREE.PointLight(0x18c9a7, 3.4, 24);
    nodeALight.position.set(-8.5, 4.5, 2.0);
    scene.add(nodeALight);

    // Node B local rim point light (Amethyst/Lavender)
    const nodeBLight = new THREE.PointLight(0x9366f1, 3.4, 24);
    nodeBLight.position.set(8.5, 4.5, 2.0);
    scene.add(nodeBLight);

    // 7. Ground Platform & Perspective Grid
    // Perspective Grid in deep navy and elevated blue-grey
    const grid = new THREE.GridHelper(70, 70, 0x1a2942, 0x0f172a);
    grid.position.y = -0.01;
    scene.add(grid);

    // Large elevated circular dais in Elevated Blue-Grey (#1A2942)
    const daisGeo = new THREE.CylinderGeometry(23, 24, 0.45, 64);
    const daisMat = new THREE.MeshStandardMaterial({
      color: 0x1a2942, // Elevated blue-grey
      roughness: 0.45,
      metalness: 0.4,
    });
    const dais = new THREE.Mesh(daisGeo, daisMat);
    dais.position.y = -0.25;
    dais.receiveShadow = true;
    scene.add(dais);

    // Outer perimeter laser cyan ring with soft glow
    const daisRingGeo = new THREE.RingGeometry(23.2, 23.45, 64);
    const daisRingMat = new THREE.MeshBasicMaterial({
      color: 0x00d9ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.4,
    });
    const daisRing = new THREE.Mesh(daisRingGeo, daisRingMat);
    daisRing.rotation.x = -Math.PI / 2;
    daisRing.position.y = -0.01;
    scene.add(daisRing);

    // 8. Distant Geometric Structures (Monoliths in the deep fog for spatial scale)
    const distantGroup = new THREE.Group();
    const monolithGeo = new THREE.BoxGeometry(2.5, 14, 2.5);
    const monolithMat = new THREE.MeshPhysicalMaterial({
      color: 0x101827,
      transmission: 0.45,
      roughness: 0.25,
      metalness: 0.3,
      transparent: true,
      opacity: 0.35,
    });

    const distantPositions = [
      { x: -36, z: -32, h: 12 },
      { x: -22, z: -42, h: 16 },
      { x: 0, z: -46, h: 20 },
      { x: 24, z: -40, h: 15 },
      { x: 38, z: -30, h: 13 },
      { x: -42, z: -15, h: 10 },
      { x: 44, z: -14, h: 11 },
    ];

    distantPositions.forEach((dp) => {
      const m = new THREE.Mesh(monolithGeo, monolithMat);
      m.position.set(dp.x, dp.h / 2, dp.z);
      distantGroup.add(m);

      // Subtle cyan beacon line at the top
      const beaconLineGeo = new THREE.BoxGeometry(0.1, 0.1, 2.5);
      const beaconLineMat = new THREE.MeshBasicMaterial({ color: 0x00d9ff, transparent: true, opacity: 0.5 });
      const bLine = new THREE.Mesh(beaconLineGeo, beaconLineMat);
      bLine.position.set(dp.x, dp.h, dp.z);
      distantGroup.add(bLine);
    });
    scene.add(distantGroup);
    distantMonolithsRef.current = distantGroup;

    // 9. Sparse Ambient Stardust Field
    const starCount = 380;
    const starGeo = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      starPositions[i * 3] = (Math.random() - 0.5) * 75;
      starPositions[i * 3 + 1] = Math.random() * 28 + 0.5;
      starPositions[i * 3 + 2] = (Math.random() - 0.5) * 75;
    }
    starGeo.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
    const starMat = new THREE.PointsMaterial({
      color: 0x00d9ff,
      size: 0.14,
      transparent: true,
      opacity: 0.45,
    });
    const starField = new THREE.Points(starGeo, starMat);
    scene.add(starField);

    // Animation Loop
    let clock = new THREE.Clock();
    let isVisible = true;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          isVisible = entry.isIntersecting;
        });
      },
      { threshold: 0.05 }
    );
    observer.observe(container);

    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);

      if (!isVisible) return;

      const delta = clock.getDelta();
      const elapsed = clock.getElapsedTime();

      // Smooth camera interpolation towards target
      if (isTransitioningRef.current && cameraRef.current && controlsRef.current) {
        cameraRef.current.position.lerp(targetCameraPosRef.current, 0.06);
        controlsRef.current.target.lerp(targetLookAtRef.current, 0.06);

        if (
          cameraRef.current.position.distanceTo(targetCameraPosRef.current) < 0.06 &&
          controlsRef.current.target.distanceTo(targetLookAtRef.current) < 0.06
        ) {
          isTransitioningRef.current = false;
        }
      }

      controls.update();

      // Animate Iridescent Glass Controller Sculpture
      if (controllerSculptureRef.current && !prefersReducedMotion) {
        controllerSculptureRef.current.rotation.y = elapsed * 0.28;
        controllerSculptureRef.current.position.y = 1.75 + Math.sin(elapsed * 1.5) * 0.08;
      }

      // Animate Gyroscope Rings at differential speeds
      controllerRingsRef.current.forEach((r, idx) => {
        if (!prefersReducedMotion) {
          r.rotation.z = elapsed * (0.35 + idx * 0.15) * (idx % 2 === 0 ? 1 : -1);
          r.rotation.x = Math.sin(elapsed * 0.4 + idx) * 0.15;
        }
      });

      // Animate Luminous Inner Pearl Core
      if (controllerInnerCoreRef.current && !prefersReducedMotion) {
        const pulse = 1.0 + Math.sin(elapsed * 2.4) * 0.06;
        controllerInnerCoreRef.current.scale.set(pulse, pulse, pulse);
      }

      // Animate MicroVMs orbiting smoothly around host nodes
      if (!prefersReducedMotion) {
        vmGroupRefs.current.forEach((vmItem) => {
          const currentAngle = vmItem.baseAngle + elapsed * vmItem.speed;
          vmItem.group.position.x = Math.cos(currentAngle) * vmItem.radius;
          vmItem.group.position.z = Math.sin(currentAngle) * vmItem.radius;
          vmItem.group.position.y = 1.35 + Math.sin(elapsed * 2.0 + vmItem.baseAngle) * 0.08;
        });
      }

      // Animate flowing photon particles along Bézier network trails
      if (!prefersReducedMotion) {
        [networkCurveARef.current, networkCurveBRef.current].forEach((trail) => {
          if (!trail) return;
          const posAttr = trail.pointsMesh.geometry.attributes.position as THREE.BufferAttribute;
          const count = trail.progress.length;
          for (let i = 0; i < count; i++) {
            trail.progress[i] += trail.speeds[i] * delta * 0.28;
            if (trail.progress[i] > 1.0) {
              trail.progress[i] = 0.0;
            }
            const pt = trail.curve.getPointAt(trail.progress[i]);
            posAttr.setXYZ(i, pt.x, pt.y + (Math.sin(elapsed * 3.0 + i) * 0.03), pt.z);
          }
          posAttr.needsUpdate = true;
        });
      }

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container || !camera || !renderer) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", handleResize);
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      controls.dispose();
      if (envTextureRef.current) envTextureRef.current.dispose();
      renderer.dispose();
      if (container) container.innerHTML = "";
    };
  }, [viewMode, prefersReducedMotion]);

  // Re-build Cluster Meshes whenever nodes or vms change
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || viewMode !== "3d") return;

    // Clear previous cluster group
    const existingGroup = scene.getObjectByName("cluster_entities");
    if (existingGroup) {
      scene.remove(existingGroup);
    }

    const clusterGroup = new THREE.Group();
    clusterGroup.name = "cluster_entities";
    clickableObjectsRef.current = [];
    controllerRingsRef.current = [];
    nodeBeaconsRef.current = [];
    vmGroupRefs.current = [];

    // =========================================================================
    // 1. CENTRAL CONTROLLER — Iridescent Glass Sculpture (Reference 2 Inspired)
    // =========================================================================
    const controllerGroup = new THREE.Group();
    controllerGroup.position.set(0, 0, 0);
    controllerGroup.userData = {
      type: "controller",
      id: "controller",
      name: "VM Controller (Orchestrator Hub)",
      details: "Central Hub • Port 8000 • Direct-Kernel Boot Orchestrator",
    };

    // Pedestal: Layered rounded beveled cylinder in elevated blue-grey (#1A2942)
    const baseGeo = new THREE.CylinderGeometry(2.7, 3.1, 0.65, 48);
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0x1a2942, // Elevated blue-grey
      roughness: 0.35,
      metalness: 0.6,
    });
    const controllerBase = new THREE.Mesh(baseGeo, baseMat);
    controllerBase.position.y = 0.325;
    controllerBase.castShadow = true;
    controllerBase.receiveShadow = true;
    controllerGroup.add(controllerBase);

    // Polished Pearl-Silver Collar Ring on Pedestal
    const collarGeo = new THREE.CylinderGeometry(2.4, 2.55, 0.22, 48);
    const collarMat = new THREE.MeshStandardMaterial({
      color: 0xdce6f2, // Pearl silver
      roughness: 0.15,
      metalness: 0.8,
    });
    const collar = new THREE.Mesh(collarGeo, collarMat);
    collar.position.y = 0.72;
    controllerGroup.add(collar);

    // Glowing Electric Cyan Inset Groove Ring
    const grooveGeo = new THREE.TorusGeometry(2.56, 0.04, 16, 64);
    const grooveMat = new THREE.MeshBasicMaterial({
      color: 0x00d9ff,
      transparent: true,
      opacity: 0.85,
    });
    const groove = new THREE.Mesh(grooveGeo, grooveMat);
    groove.rotation.x = Math.PI / 2;
    groove.position.y = 0.68;
    controllerGroup.add(groove);

    // --- Iridescent Glass Sculpture (Floating & Rotating Focal Point) ---
    const sculptureGroup = new THREE.Group();
    sculptureGroup.position.y = 1.75;

    // Material: Glossy Cobalt-Blue Iridescent Glass
    const cobaltGlassMat = new THREE.MeshPhysicalMaterial({
      color: 0x3158c9, // Cobalt blue (#3158C9)
      emissive: 0x1f3fa8,
      emissiveIntensity: 0.2,
      roughness: 0.06,
      metalness: 0.08,
      transmission: 0.68,
      thickness: 1.4,
      ior: 1.54,
      clearcoat: 1.0,
      clearcoatRoughness: 0.03,
      iridescence: 0.92,
      iridescenceIOR: 1.34,
      iridescenceThicknessRange: [120, 420],
      specularColor: new THREE.Color(0x8fa8ff), // Periwinkle highlights
      attenuationColor: new THREE.Color(0x1a2ffb),
      attenuationDistance: 2.0,
      transparent: true,
    });

    // Sculptural Outer Envelope: Faceted Rounded Glass Jewel
    const jewelGeo = new THREE.OctahedronGeometry(1.35, 3);
    const jewelMesh = new THREE.Mesh(jewelGeo, cobaltGlassMat);
    jewelMesh.castShadow = true;
    sculptureGroup.add(jewelMesh);

    // Nested Interlocking Curved Ribbon Toruses (Layered rounded geometry)
    const torusGeo1 = new THREE.TorusGeometry(1.68, 0.16, 24, 64);
    const torus1 = new THREE.Mesh(torusGeo1, cobaltGlassMat);
    torus1.rotation.x = Math.PI / 3;
    torus1.rotation.y = Math.PI / 5;
    sculptureGroup.add(torus1);

    const torusGeo2 = new THREE.TorusGeometry(1.52, 0.14, 24, 64);
    const torus2 = new THREE.Mesh(torusGeo2, cobaltGlassMat);
    torus2.rotation.x = -Math.PI / 4;
    torus2.rotation.z = Math.PI / 3;
    sculptureGroup.add(torus2);

    // Inner Core: Luminous Pearl Silver Sphere with soft Cyan Glow
    const pearlCoreGeo = new THREE.SphereGeometry(0.72, 32, 32);
    const pearlCoreMat = new THREE.MeshPhysicalMaterial({
      color: 0xdce6f2, // Pearl silver
      roughness: 0.18,
      metalness: 0.35,
      clearcoat: 0.9,
      emissive: 0x00d9ff,
      emissiveIntensity: 0.38,
    });
    const pearlCore = new THREE.Mesh(pearlCoreGeo, pearlCoreMat);
    sculptureGroup.add(pearlCore);
    controllerInnerCoreRef.current = pearlCore;

    // Radiant Central Core PointLight
    const innerLight = new THREE.PointLight(0x00d9ff, 4.2, 18);
    sculptureGroup.add(innerLight);

    // Orbiting Gyroscopic Accent Rings (Periwinkle & Electric Cyan)
    const ring1Geo = new THREE.TorusGeometry(2.1, 0.028, 16, 64);
    const ring1Mat = new THREE.MeshBasicMaterial({
      color: 0x8fa8ff, // Periwinkle
      transparent: true,
      opacity: 0.7,
    });
    const gyroRing1 = new THREE.Mesh(ring1Geo, ring1Mat);
    gyroRing1.rotation.x = Math.PI / 2.2;
    sculptureGroup.add(gyroRing1);
    controllerRingsRef.current.push(gyroRing1);

    const ring2Geo = new THREE.TorusGeometry(2.35, 0.024, 16, 64);
    const ring2Mat = new THREE.MeshBasicMaterial({
      color: 0x00d9ff, // Electric Cyan
      transparent: true,
      opacity: 0.55,
    });
    const gyroRing2 = new THREE.Mesh(ring2Geo, ring2Mat);
    gyroRing2.rotation.x = Math.PI / 1.7;
    gyroRing2.rotation.y = Math.PI / 4;
    sculptureGroup.add(gyroRing2);
    controllerRingsRef.current.push(gyroRing2);

    controllerGroup.add(sculptureGroup);
    controllerSculptureRef.current = sculptureGroup;

    clusterGroup.add(controllerGroup);
    clickableObjectsRef.current.push(jewelMesh, controllerBase, torus1, torus2);

    // =========================================================================
    // 2. WORKER NODES (Node A: Jade Glass, Node B: Amethyst Glass)
    // =========================================================================
    const nodePositions: Record<string, THREE.Vector3> = {
      "node-a": new THREE.Vector3(-8.5, 0, 0.5),
      "node-b": new THREE.Vector3(8.5, 0, 0.5),
    };

    // Shared Node Geometry System
    nodes.forEach((node, index) => {
      const pos = nodePositions[node.id] || new THREE.Vector3(index === 0 ? -8.5 : 8.5, 0, 0.5);
      const isSelected = selectedNodeId === node.id;
      const isHealthy = node.status === "HEALTHY";
      const isNodeA = node.id === "node-a";

      // Color Palette specifications per prompt
      // Node A: Jade (#18C9A7), Mint highlights (#75F0D0), Deep Teal (#126E70)
      // Node B: Amethyst (#9366F1), Lavender highlights (#D1B8FF), Deep Violet (#492B8D)
      const nodeColor = isNodeA ? 0x18c9a7 : 0x9366f1;
      const highlightColor = isNodeA ? 0x75f0d0 : 0xd1b8ff;
      const shadowColor = isNodeA ? 0x126e70 : 0x492b8d;

      // Real health indicators (separate from artistic glass color)
      // Emerald Green (#168A62) for Healthy, Vermilion (#E6533C) for Degraded/Critical
      const healthColor = isHealthy ? 0x168a62 : 0xe6533c;

      const nodeGroup = new THREE.Group();
      nodeGroup.position.copy(pos);
      nodeGroup.userData = {
        type: "node",
        id: node.id,
        name: `Worker Node: ${node.id} (${isNodeA ? "Jade Glass Host" : "Amethyst Glass Host"})`,
        details: `Status: ${node.status} • Schedulable: ${node.memory_schedulable_mb} MB • Active VMs: ${vms.filter((v) => v.node_id === node.id).length}`,
      };

      // Base Platform: Tiered elevated disk in elevated blue-grey (#1A2942)
      const platGeo = new THREE.CylinderGeometry(3.6, 4.0, 0.45, 48);
      const platMat = new THREE.MeshStandardMaterial({
        color: isSelected ? 0x223554 : 0x1a2942,
        roughness: 0.35,
        metalness: 0.5,
      });
      const platMesh = new THREE.Mesh(platGeo, platMat);
      platMesh.position.y = 0.225;
      platMesh.receiveShadow = true;
      nodeGroup.add(platMesh);

      // Edge illumination groove on platform (Mint for Node A, Lavender for Node B)
      const edgeRingGeo = new THREE.RingGeometry(3.5, 3.65, 48);
      const edgeRingMat = new THREE.MeshBasicMaterial({
        color: highlightColor,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: isSelected ? 0.9 : 0.6,
      });
      const edgeRing = new THREE.Mesh(edgeRingGeo, edgeRingMat);
      edgeRing.rotation.x = -Math.PI / 2;
      edgeRing.position.y = 0.455;
      nodeGroup.add(edgeRing);

      // Memory Allocation Gauge Ring (Visualizing real reserved vs schedulable memory)
      const reservedMem = vms
        .filter((v) => v.node_id === node.id && ["RUNNING", "PENDING", "UNKNOWN"].includes(v.status))
        .reduce((sum, v) => sum + v.memory_mb, 0);
      const schedMem = node.memory_schedulable_mb || 1;
      const memFraction = Math.min(1, reservedMem / schedMem);

      const memGaugeGeo = new THREE.TorusGeometry(3.1, 0.07, 16, 48);
      const memGaugeMat = new THREE.MeshStandardMaterial({
        color: memFraction > 0.85 ? 0xe6533c : memFraction > 0.6 ? 0xffb800 : highlightColor,
        emissive: memFraction > 0.85 ? 0xe6533c : highlightColor,
        emissiveIntensity: 0.45,
        roughness: 0.2,
      });
      const memGauge = new THREE.Mesh(memGaugeGeo, memGaugeMat);
      memGauge.rotation.x = Math.PI / 2;
      memGauge.position.y = 0.47;
      nodeGroup.add(memGauge);

      // --- Sculptural Glass Chassis (No flat black boxes!) ---
      // Internal Computational Core with stratified memory bus slabs
      const coreColGeo = new THREE.CylinderGeometry(0.85, 0.85, 3.0, 16);
      const coreColMat = new THREE.MeshStandardMaterial({
        color: shadowColor,
        emissive: nodeColor,
        emissiveIntensity: 0.35,
        roughness: 0.3,
        metalness: 0.7,
      });
      const coreCol = new THREE.Mesh(coreColGeo, coreColMat);
      coreCol.position.y = 2.1;
      nodeGroup.add(coreCol);

      // Memory Bus Stratified Luminous Rings inside the column
      for (let s = 0; s < 4; s++) {
        const slabGeo = new THREE.TorusGeometry(0.9, 0.03, 12, 32);
        const slabMat = new THREE.MeshBasicMaterial({
          color: highlightColor,
          transparent: true,
          opacity: 0.8,
        });
        const slab = new THREE.Mesh(slabGeo, slabMat);
        slab.rotation.x = Math.PI / 2;
        slab.position.y = 1.2 + s * 0.6;
        nodeGroup.add(slab);
      }

      // Outer Faceted Glass Monolith Casing (MeshPhysicalMaterial with rich iridescence)
      const glassCasingGeo = new THREE.CylinderGeometry(1.65, 1.85, 3.4, 8);
      const glassCasingMat = new THREE.MeshPhysicalMaterial({
        color: nodeColor,
        roughness: 0.09,
        metalness: 0.12,
        transmission: 0.62,
        thickness: 1.1,
        ior: 1.48,
        clearcoat: 0.95,
        clearcoatRoughness: 0.04,
        iridescence: 0.78,
        iridescenceIOR: 1.33,
        iridescenceThicknessRange: [100, 360],
        specularColor: new THREE.Color(highlightColor),
        attenuationColor: new THREE.Color(shadowColor),
        attenuationDistance: 1.8,
        transparent: true,
      });
      const glassCasing = new THREE.Mesh(glassCasingGeo, glassCasingMat);
      glassCasing.position.y = 2.25;
      glassCasing.castShadow = true;
      glassCasing.receiveShadow = true;
      nodeGroup.add(glassCasing);

      // Optical Top Crown with Explicit Health Beacon
      const crownGeo = new THREE.CylinderGeometry(1.4, 1.65, 0.3, 8);
      const crownMat = new THREE.MeshStandardMaterial({
        color: 0xdce6f2, // Pearl silver top trim
        roughness: 0.2,
        metalness: 0.7,
      });
      const crown = new THREE.Mesh(crownGeo, crownMat);
      crown.position.y = 4.0;
      nodeGroup.add(crown);

      // Separate Explicit Health Beacon Jewel
      const beaconGeo = new THREE.OctahedronGeometry(0.38, 2);
      const beaconMat = new THREE.MeshStandardMaterial({
        color: healthColor,
        emissive: healthColor,
        emissiveIntensity: isHealthy ? 1.2 : 1.8,
        roughness: 0.15,
      });
      const beacon = new THREE.Mesh(beaconGeo, beaconMat);
      beacon.position.y = 4.45;
      nodeGroup.add(beacon);
      nodeBeaconsRef.current.push(beacon);

      // Selection Ring Feedback (Expands when clicked)
      if (isSelected) {
        const selRingGeo = new THREE.RingGeometry(4.1, 4.35, 48);
        const selRingMat = new THREE.MeshBasicMaterial({
          color: 0x00d9ff,
          side: THREE.DoubleSide,
        });
        const selRing = new THREE.Mesh(selRingGeo, selRingMat);
        selRing.rotation.x = -Math.PI / 2;
        selRing.position.y = 0.46;
        nodeGroup.add(selRing);
      }

      clickableObjectsRef.current.push(glassCasing, platMesh, beacon, crown);

      // =========================================================================
      // 3. VIRTUAL MACHINES — Frosted Pearl Glass (#F4F1FF) Objects
      // =========================================================================
      const nodeVms = vms.filter((v) => v.node_id === node.id);
      const vmOrbitRadius = 3.2;

      nodeVms.forEach((vm, vmIndex) => {
        const baseAngle = (vmIndex / Math.max(1, nodeVms.length)) * Math.PI * 2;
        const isVmSelected = selectedVmId === vm.id;

        const vmGroup = new THREE.Group();
        vmGroup.position.set(
          Math.cos(baseAngle) * vmOrbitRadius,
          1.35 + (vmIndex % 2) * 0.4,
          Math.sin(baseAngle) * vmOrbitRadius
        );
        vmGroup.userData = {
          type: "vm",
          id: vm.id,
          name: `VM: ${vm.name}`,
          details: `Status: ${vm.status} • ${vm.vcpus} vCPU • ${vm.memory_mb} MB RAM • IP: ${vm.ip_address || "None"}`,
          vmData: vm,
        };

        // Real health/state indication
        let stateColor = 0xa8b4ca; // Muted for STOPPED
        if (vm.status === "RUNNING") stateColor = 0x168a62; // Emerald Green
        else if (vm.status === "PENDING") stateColor = 0xffca80; // Warm highlight
        else if (vm.status === "FAILED" || vm.status === "UNKNOWN") stateColor = 0xe6533c; // Vermilion

        // Outer Frosted Pearl Glass Jewel Silhouette
        const vmShellGeo = new THREE.DodecahedronGeometry(0.48, 1);
        const vmShellMat = new THREE.MeshPhysicalMaterial({
          color: 0xf4f1ff, // Frosted pearl
          roughness: 0.28, // Soft frosted diffusion
          metalness: 0.08,
          transmission: 0.74,
          thickness: 0.8,
          ior: 1.46,
          clearcoat: 0.85,
          clearcoatRoughness: 0.08,
          specularColor: new THREE.Color(0xb8d9ff), // Pale blue highlights
          attenuationColor: new THREE.Color(0xb8d9ff),
          attenuationDistance: 1.6,
          transparent: true,
        });
        const vmMesh = new THREE.Mesh(vmShellGeo, vmShellMat);
        vmMesh.castShadow = true;
        vmGroup.add(vmMesh);

        // Inner State Node (Communicates real operational state)
        const innerStateGeo = new THREE.SphereGeometry(0.2, 16, 16);
        const innerStateMat = new THREE.MeshStandardMaterial({
          color: stateColor,
          emissive: stateColor,
          emissiveIntensity: vm.status === "RUNNING" ? 1.2 : 0.6,
          roughness: 0.2,
        });
        const innerState = new THREE.Mesh(innerStateGeo, innerStateMat);
        vmGroup.add(innerState);

        // Thin vertical luminous laser tether anchoring VM to pedestal
        const tetherGeo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0, 0),
          new THREE.Vector3(0, -0.9 - (vmIndex % 2) * 0.4, 0),
        ]);
        const tetherMat = new THREE.LineDashedMaterial({
          color: 0x00d9ff,
          dashSize: 0.2,
          gapSize: 0.12,
          transparent: true,
          opacity: 0.5,
        });
        const tether = new THREE.Line(tetherGeo, tetherMat);
        tether.computeLineDistances();
        vmGroup.add(tether);

        // Ground anchor ring on node platform
        const anchorRingGeo = new THREE.RingGeometry(0.25, 0.32, 24);
        const anchorRingMat = new THREE.MeshBasicMaterial({
          color: 0x00d9ff,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.6,
        });
        const anchorRing = new THREE.Mesh(anchorRingGeo, anchorRingMat);
        anchorRing.rotation.x = -Math.PI / 2;
        anchorRing.position.y = -0.9 - (vmIndex % 2) * 0.4;
        vmGroup.add(anchorRing);

        // Clear Selection Feedback (Glowing Cyan Halo)
        if (isVmSelected) {
          const selWireGeo = new THREE.WireframeGeometry(new THREE.DodecahedronGeometry(0.68, 1));
          const selWireMat = new THREE.LineBasicMaterial({ color: 0x00d9ff });
          const selWire = new THREE.LineSegments(selWireGeo, selWireMat);
          vmGroup.add(selWire);
        }

        nodeGroup.add(vmGroup);
        clickableObjectsRef.current.push(vmMesh);

        // Track for smooth orbit animation
        vmGroupRefs.current.push({
          group: vmGroup,
          baseAngle,
          radius: vmOrbitRadius,
          speed: 0.15 + (vmIndex % 3) * 0.05,
        });
      });

      clusterGroup.add(nodeGroup);

      // =========================================================================
      // 4. FLOWING CYAN LIGHT TRAILS — Curved Bézier Spline Network Highway
      // =========================================================================
      const startPoint = new THREE.Vector3(0, 1.75, 0);
      const endPoint = pos.clone().add(new THREE.Vector3(0, 2.25, 0));

      // Sculpted 3D Cubic Bézier Curve arcing smoothly across space
      const midPoint1 = startPoint.clone().lerp(endPoint, 0.35);
      midPoint1.y += 1.2;
      const midPoint2 = startPoint.clone().lerp(endPoint, 0.7);
      midPoint2.y += 0.8;

      const bezierCurve = new THREE.CubicBezierCurve3(startPoint, midPoint1, midPoint2, endPoint);
      const curvePoints = bezierCurve.getPoints(64);

      // Luminous Network Bus Line
      const curveGeo = new THREE.BufferGeometry().setFromPoints(curvePoints);
      const curveMat = new THREE.LineBasicMaterial({
        color: isHealthy ? 0x00d9ff : 0xe6533c,
        transparent: true,
        opacity: isSelected ? 0.95 : 0.65,
      });
      const networkLine = new THREE.Line(curveGeo, curveMat);
      clusterGroup.add(networkLine);

      // Flowing Photon Stream (Particles gliding along the Bézier curve)
      const photonCount = 28;
      const photonGeo = new THREE.BufferGeometry();
      const pPositions = new Float32Array(photonCount * 3);
      const pProgress = new Float32Array(photonCount);
      const pSpeeds = new Float32Array(photonCount);

      for (let i = 0; i < photonCount; i++) {
        const prog = i / photonCount;
        pProgress[i] = prog;
        const pt = bezierCurve.getPointAt(prog);
        pPositions[i * 3] = pt.x;
        pPositions[i * 3 + 1] = pt.y;
        pPositions[i * 3 + 2] = pt.z;
        pSpeeds[i] = 1.0 + Math.random() * 0.4;
      }

      photonGeo.setAttribute("position", new THREE.BufferAttribute(pPositions, 3));
      const photonMat = new THREE.PointsMaterial({
        color: isHealthy ? 0x00d9ff : 0xe6533c,
        size: 0.22,
        transparent: true,
        opacity: 0.95,
      });
      const photonMesh = new THREE.Points(photonGeo, photonMat);
      clusterGroup.add(photonMesh);

      if (node.id === "node-a") {
        networkCurveARef.current = { curve: bezierCurve, pointsMesh: photonMesh, progress: pProgress, speeds: pSpeeds };
      } else {
        networkCurveBRef.current = { curve: bezierCurve, pointsMesh: photonMesh, progress: pProgress, speeds: pSpeeds };
      }
    });

    scene.add(clusterGroup);
  }, [nodes, vms, selectedNodeId, selectedVmId, viewMode]);

  // Pointer interactions with Raycasting
  const handlePointerDown = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!mountRef.current || !cameraRef.current) return;
      const rect = mountRef.current.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(x, y), cameraRef.current);
      const intersects = raycaster.intersectObjects(clickableObjectsRef.current, true);

      if (intersects.length > 0) {
        let obj: THREE.Object3D | null = intersects[0].object;
        while (obj && !obj.userData?.type && obj.parent) {
          obj = obj.parent;
        }

        if (obj?.userData?.type === "node") {
          const nId = obj.userData.id;
          onSelectNode(selectedNodeId === nId ? null : nId);
          onSelectVm(null);

          if (cameraRef.current && controlsRef.current) {
            const worldPos = new THREE.Vector3();
            obj.getWorldPosition(worldPos);
            targetCameraPosRef.current.set(worldPos.x, worldPos.y + 5.5, worldPos.z + 9.5);
            targetLookAtRef.current.set(worldPos.x, worldPos.y + 1.8, worldPos.z);
            isTransitioningRef.current = true;
          }
        } else if (obj?.userData?.type === "vm") {
          const vId = obj.userData.id;
          onSelectVm(selectedVmId === vId ? null : vId);

          if (cameraRef.current && controlsRef.current) {
            const worldPos = new THREE.Vector3();
            obj.getWorldPosition(worldPos);
            targetCameraPosRef.current.set(worldPos.x, worldPos.y + 3.8, worldPos.z + 5.5);
            targetLookAtRef.current.set(worldPos.x, worldPos.y + 0.5, worldPos.z);
            isTransitioningRef.current = true;
          }
        } else if (obj?.userData?.type === "controller") {
          onSelectNode(null);
          onSelectVm(null);
          resetCamera();
        }
      }
    },
    [selectedNodeId, selectedVmId, onSelectNode, onSelectVm]
  );

  const handlePointerMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!mountRef.current || !cameraRef.current) return;
    const rect = mountRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(x, y), cameraRef.current);
    const intersects = raycaster.intersectObjects(clickableObjectsRef.current, true);

    if (intersects.length > 0) {
      let obj: THREE.Object3D | null = intersects[0].object;
      while (obj && !obj.userData?.type && obj.parent) {
        obj = obj.parent;
      }
      if (obj?.userData) {
        setHoveredEntity({
          type: obj.userData.type,
          id: obj.userData.id,
          name: obj.userData.name,
          details: obj.userData.details,
        });
        if (mountRef.current) mountRef.current.style.cursor = "pointer";
        return;
      }
    }
    setHoveredEntity(null);
    if (mountRef.current) mountRef.current.style.cursor = "grab";
  }, []);

  const resetCamera = () => {
    targetCameraPosRef.current.copy(defaultCameraPos);
    targetLookAtRef.current.copy(defaultLookAt);
    isTransitioningRef.current = true;
    onSelectNode(null);
    onSelectVm(null);
  };

  const activeNode = nodes.find((n) => n.id === selectedNodeId);
  const activeVm = vms.find((v) => v.id === selectedVmId);

  return (
    <div
      style={{
        position: isFullViewport ? "fixed" : "relative",
        inset: isFullViewport ? 0 : undefined,
        width: "100%",
        height: isFullViewport ? "100vh" : "460px",
        borderRadius: isFullViewport ? "0" : "var(--radius-xl)",
        overflow: "hidden",
        backgroundColor: "var(--bg-primary)",
        border: isFullViewport ? "none" : "1px solid var(--border)",
        boxShadow: isFullViewport ? "none" : "var(--shadow-md)",
        marginBottom: isFullViewport ? "0" : "28px",
        zIndex: isFullViewport ? 0 : 1,
      }}
    >
      {viewMode === "3d" ? (
        <div
          ref={mountRef}
          onMouseDown={handlePointerDown}
          onMouseMove={handlePointerMove}
          style={{ width: "100%", height: "100%", touchAction: "none" }}
        />
      ) : (
        /* Accessible 2D Fallback Schematic (Preserving complete functional monitoring) */
        <div
          style={{
            width: "100%",
            height: "100%",
            padding: "32px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            backgroundColor: "var(--bg-card)",
          }}
        >
          {!webGlAvailable && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 16px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(255, 184, 0, 0.12)",
                border: "1px solid var(--warning)",
                color: "var(--warning)",
                fontSize: "12px",
                marginBottom: "20px",
              }}
            >
              <Info size={16} />
              <span>Operating in Accessible 2D Topology Mode (WebGL acceleration not available)</span>
            </div>
          )}

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "24px",
              width: "100%",
              maxWidth: "940px",
            }}
          >
            {/* Node A (Jade Glass Host) */}
            {nodes[0] ? (
              <div
                onClick={() => onSelectNode(nodes[0].id)}
                style={{
                  flex: 1,
                  padding: "20px",
                  borderRadius: "var(--radius-lg)",
                  backgroundColor: selectedNodeId === nodes[0].id ? "var(--sidebar-active)" : "var(--bg-surface)",
                  border: `2px solid ${selectedNodeId === nodes[0].id ? "var(--accent-jade)" : "var(--border)"}`,
                  cursor: "pointer",
                  transition: "all 0.18s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Server size={18} style={{ color: "var(--accent-jade)" }} />
                    <strong style={{ color: "var(--text-primary)", fontSize: "14px" }}>{nodes[0].id} (Jade Glass)</strong>
                  </div>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      color: nodes[0].status === "HEALTHY" ? "var(--color-acid-lime)" : "var(--danger)",
                    }}
                  >
                    {nodes[0].status}
                  </span>
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  RAM: {nodes[0].memory_schedulable_mb} MB Schedulable
                </div>
                <div style={{ fontSize: "12px", color: "var(--accent-jade)", marginTop: "4px" }}>
                  {vms.filter((v) => v.node_id === nodes[0].id).length} Active MicroVMs
                </div>
              </div>
            ) : (
              <div
                style={{
                  flex: 1,
                  padding: "20px",
                  borderRadius: "var(--radius-lg)",
                  backgroundColor: "var(--bg-surface)",
                  border: "1px dashed var(--border)",
                  textAlign: "center",
                  color: "var(--text-muted)",
                  fontSize: "12px",
                }}
              >
                No Node A registered
              </div>
            )}

            {/* Controller Hub (Cobalt & Pearl) */}
            <div
              style={{
                padding: "22px 28px",
                borderRadius: "var(--radius-lg)",
                backgroundColor: "var(--bg-surface)",
                border: "2px solid var(--primary-deep)",
                textAlign: "center",
                minWidth: "210px",
                boxShadow: "var(--shadow-cobalt-glow)",
              }}
            >
              <Cpu size={28} style={{ color: "var(--primary)", margin: "0 auto 8px" }} />
              <div style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "14.5px" }}>VM Controller Hub</div>
              <div style={{ fontSize: "11px", color: "var(--primary)", fontFamily: "var(--font-mono)", marginTop: "2px" }}>
                Cobalt Iridescent Core
              </div>
            </div>

            {/* Node B (Amethyst Glass Host) */}
            {nodes[1] ? (
              <div
                onClick={() => onSelectNode(nodes[1].id)}
                style={{
                  flex: 1,
                  padding: "20px",
                  borderRadius: "var(--radius-lg)",
                  backgroundColor: selectedNodeId === nodes[1].id ? "var(--sidebar-active)" : "var(--bg-surface)",
                  border: `2px solid ${selectedNodeId === nodes[1].id ? "var(--accent-violet)" : "var(--border)"}`,
                  cursor: "pointer",
                  transition: "all 0.18s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Server size={18} style={{ color: "var(--accent-violet)" }} />
                    <strong style={{ color: "var(--text-primary)", fontSize: "14px" }}>{nodes[1].id} (Amethyst Glass)</strong>
                  </div>
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      color: nodes[1].status === "HEALTHY" ? "var(--color-acid-lime)" : "var(--danger)",
                    }}
                  >
                    {nodes[1].status}
                  </span>
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  RAM: {nodes[1].memory_schedulable_mb} MB Schedulable
                </div>
                <div style={{ fontSize: "12px", color: "var(--accent-violet)", marginTop: "4px" }}>
                  {vms.filter((v) => v.node_id === nodes[1].id).length} Active MicroVMs
                </div>
              </div>
            ) : (
              <div
                style={{
                  flex: 1,
                  padding: "20px",
                  borderRadius: "var(--radius-lg)",
                  backgroundColor: "var(--bg-surface)",
                  border: "1px dashed var(--border)",
                  textAlign: "center",
                  color: "var(--text-muted)",
                  fontSize: "12px",
                }}
              >
                No Node B registered
              </div>
            )}
          </div>
        </div>
      )}

      {/* Floating Canvas Overlays (Shown when embedded in Overview) */}
      {!isFullViewport && (
        <>
          <div
            style={{
              position: "absolute",
              top: "14px",
              left: "16px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              zIndex: 10,
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                letterSpacing: "0.06em",
                fontWeight: 600,
                textTransform: "uppercase",
                color: "var(--primary)",
                backgroundColor: "rgba(10, 20, 40, 0.8)",
                backdropFilter: "blur(10px)",
                padding: "6px 14px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              3D Cluster Spatial Twin
            </span>
            <div style={{ display: "flex", gap: "6px" }}>
              <button
                onClick={() => setViewMode(viewMode === "3d" ? "2d" : "3d")}
                title="Toggle 3D View / 2D Schematic"
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "6px 12px",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: "rgba(10, 20, 40, 0.8)",
                  color: "var(--text-primary)",
                  border: "1px solid var(--border)",
                  backdropFilter: "blur(10px)",
                }}
              >
                <Eye size={13} />
                <span>{viewMode === "3d" ? "2D Schematic" : "3D View"}</span>
              </button>
              {viewMode === "3d" && (
                <button
                  onClick={resetCamera}
                  title="Reset Viewpoint"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "5px",
                    padding: "6px 12px",
                    fontSize: "11.5px",
                    fontWeight: 600,
                    borderRadius: "var(--radius-sm)",
                    backgroundColor: "rgba(10, 20, 40, 0.8)",
                    color: "var(--text-primary)",
                    border: "1px solid var(--border)",
                    backdropFilter: "blur(10px)",
                  }}
                >
                  <RotateCcw size={12} />
                  <span>Reset Camera</span>
                </button>
              )}
            </div>
          </div>

          {hoveredEntity && (
            <div
              style={{
                position: "absolute",
                bottom: "16px",
                left: "16px",
                padding: "10px 18px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(10, 20, 40, 0.92)",
                border: "1px solid var(--primary)",
                color: "var(--text-primary)",
                backdropFilter: "blur(12px)",
                boxShadow: "var(--shadow-cyan-glow)",
                zIndex: 10,
                pointerEvents: "none",
              }}
            >
              <div style={{ fontSize: "13px", fontWeight: 700 }}>{hoveredEntity.name}</div>
              {hoveredEntity.details && (
                <div style={{ fontSize: "11.5px", color: "var(--text-secondary)", marginTop: "2px" }}>
                  {hoveredEntity.details}
                </div>
              )}
            </div>
          )}

          {(activeNode || activeVm) && (
            <div
              style={{
                position: "absolute",
                top: "14px",
                right: "16px",
                width: "320px",
                maxHeight: "calc(100% - 28px)",
                overflowY: "auto",
                borderRadius: "var(--radius-lg)",
                backgroundColor: "rgba(16, 24, 39, 0.94)",
                border: "1px solid var(--border-glow)",
                backdropFilter: "blur(18px)",
                padding: "16px",
                boxShadow: "var(--shadow-lg)",
                zIndex: 15,
                display: "flex",
                flexDirection: "column",
                gap: "12px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {activeNode ? (
                    <Server size={18} style={{ color: activeNode.id === "node-a" ? "var(--accent-jade)" : "var(--accent-violet)" }} />
                  ) : (
                    <Layers size={18} style={{ color: "var(--color-frosted-pearl)" }} />
                  )}
                  <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>
                    {activeNode ? activeNode.id : activeVm?.name}
                  </strong>
                </div>
                <button
                  onClick={() => {
                    onSelectNode(null);
                    onSelectVm(null);
                  }}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: "2px",
                    fontSize: "16px",
                  }}
                >
                  &times;
                </button>
              </div>

              {activeNode && (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Health:</span>
                    <span style={{ color: activeNode.status === "HEALTHY" ? "var(--color-acid-lime)" : "var(--danger)", fontWeight: 700 }}>
                      {activeNode.status}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Sculptural Glass:</span>
                    <span style={{ color: activeNode.id === "node-a" ? "var(--accent-jade)" : "var(--accent-violet)", fontWeight: 600 }}>
                      {activeNode.id === "node-a" ? "Jade Glass & Mint" : "Amethyst Glass & Lavender"}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Total Memory:</span>
                    <span style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                      {activeNode.memory_total_mb} MB
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Schedulable RAM:</span>
                    <span style={{ color: "var(--primary)", fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                      {activeNode.memory_schedulable_mb} MB
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Resident VMs:</span>
                    <span style={{ color: "var(--text-primary)" }}>
                      {vms.filter((v) => v.node_id === activeNode.id).length} instances
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Worker URL:</span>
                    <span style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)", fontSize: "11px" }}>
                      {activeNode.url}
                    </span>
                  </div>
                </div>
              )}

              {activeVm && (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Status:</span>
                    <span
                      style={{
                        color: activeVm.status === "RUNNING" ? "var(--color-acid-lime)" : "var(--text-secondary)",
                        fontWeight: 700,
                      }}
                    >
                      {activeVm.status}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Sculptural Form:</span>
                    <span style={{ color: "var(--color-pale-blue)", fontWeight: 600 }}>Frosted Pearl Glass</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Host Node:</span>
                    <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{activeVm.node_id}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>vCPU / RAM:</span>
                    <span style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                      {activeVm.vcpus} vCPU • {activeVm.memory_mb} MB
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "4px" }}>
                    <span style={{ color: "var(--text-muted)" }}>IPv4:</span>
                    <span style={{ color: "var(--primary)", fontFamily: "var(--font-mono)" }}>
                      {activeVm.ip_address || "None"}
                    </span>
                  </div>
                  {activeVm.status === "RUNNING" && onOpenTerminal && (
                    <button
                      onClick={() => onOpenTerminal(activeVm)}
                      style={{
                        marginTop: "6px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px",
                        padding: "8px 12px",
                        borderRadius: "var(--radius-sm)",
                        backgroundColor: "var(--primary-deep)",
                        color: "#FFFFFF",
                        fontSize: "12px",
                        fontWeight: 600,
                        border: "1px solid var(--primary)",
                      }}
                    >
                      <Terminal size={14} />
                      <span>Open Console</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
};
