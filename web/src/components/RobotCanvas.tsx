import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

interface RobotCanvasProps {
  className?: string;
}

export const RobotCanvas: React.FC<RobotCanvasProps> = ({ className = '' }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    // Avoid jsdom / non-browser test environment errors
    if (typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent)) {
      return;
    }

    const canvas = canvasRef.current;
    if (!canvas) return;

    let animationFrameId: number;
    let renderer: THREE.WebGLRenderer;

    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
      });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.05;
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    } catch (err) {
      console.warn('WebGL initialization skipped:', err);
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(30, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 1.1, 11.6);

    // Environment
    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    pmremGenerator.compileEquirectangularShader();
    const roomEnv = new RoomEnvironment();
    scene.environment = pmremGenerator.fromScene(roomEnv, 0.04).texture;

    // Lights
    const hemiLight = new THREE.HemisphereLight(0xfff6ee, 0xd9d2c8, 0.7);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xfff3e6, 1.7);
    keyLight.position.set(-3, 5, 4);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 1024;
    keyLight.shadow.mapSize.height = 1024;
    keyLight.shadow.radius = 6;
    keyLight.shadow.bias = -0.0005;
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0xfff0e6, 1.2);
    rimLight.position.set(4, 2, -4);
    scene.add(rimLight);

    const fillLight = new THREE.PointLight(0xff9a6a, 2.2, 6);
    fillLight.position.set(-3.2, 1.2, 0.6);
    scene.add(fillLight);

    // Materials
    const shellMat = new THREE.MeshPhysicalMaterial({
      color: 0xeeebe6,
      roughness: 0.38,
      clearcoat: 0.45,
      clearcoatRoughness: 0.3,
    });

    const shellLightMat = new THREE.MeshPhysicalMaterial({
      color: 0xf8f6f2,
      roughness: 0.34,
      clearcoat: 0.45,
      clearcoatRoughness: 0.3,
    });

    const jointsMat = new THREE.MeshPhysicalMaterial({
      color: 0x1b1b1f,
      roughness: 0.55,
      metalness: 0.3,
    });

    const deepDarkMat = new THREE.MeshPhysicalMaterial({
      color: 0x0f0f12,
      roughness: 0.7,
      metalness: 0.1,
    });

    const pedestalMat = new THREE.MeshPhysicalMaterial({
      color: 0x2a2928,
      roughness: 0.9,
    });

    // Conic gradient ring canvas
    const ringCanvas = document.createElement('canvas');
    ringCanvas.width = 512;
    ringCanvas.height = 512;
    const ringCtx = ringCanvas.getContext('2d');
    if (ringCtx && typeof ringCtx.createConicGradient === 'function') {
      const conic = ringCtx.createConicGradient(200 * Math.PI / 180, 256, 256);
      conic.addColorStop(0, '#ffb347');
      conic.addColorStop(0.18, '#ff8a3d');
      conic.addColorStop(0.34, '#ff5a5f');
      conic.addColorStop(0.50, '#ff3d8b');
      conic.addColorStop(0.66, '#ff5a5f');
      conic.addColorStop(0.82, '#ff8a3d');
      conic.addColorStop(1.0, '#ffb347');
      ringCtx.fillStyle = conic;
      ringCtx.fillRect(0, 0, 512, 512);
    }

    const ringTexture = new THREE.CanvasTexture(ringCanvas);
    ringTexture.colorSpace = THREE.SRGBColorSpace;

    const ringMat = new THREE.MeshPhysicalMaterial({
      map: ringTexture,
      emissive: new THREE.Color(0xffffff),
      emissiveMap: ringTexture,
      emissiveIntensity: 0.22,
      roughness: 0.5,
      clearcoat: 0.35,
    });

    // Face Screen Canvas
    const faceCanvas = document.createElement('canvas');
    faceCanvas.width = 512;
    faceCanvas.height = 512;
    const faceCtx = faceCanvas.getContext('2d');
    const faceTexture = new THREE.CanvasTexture(faceCanvas);
    faceTexture.colorSpace = THREE.SRGBColorSpace;

    const screenMat = new THREE.MeshPhysicalMaterial({
      color: 0x050508,
      roughness: 0.15,
      clearcoat: 1.0,
      clearcoatRoughness: 0.1,
      emissive: new THREE.Color(0xffffff),
      emissiveMap: faceTexture,
      emissiveIntensity: 1.6,
    });

    // Robot Hierarchy
    const robotRoot = new THREE.Group();
    scene.add(robotRoot);

    const robotBodyGroup = new THREE.Group();
    robotRoot.add(robotBodyGroup);

    // Pedestal
    const pedestal = new THREE.Mesh(new THREE.BoxGeometry(1.7, 1.6, 1.7), pedestalMat);
    pedestal.position.set(0, -2.22, 0);
    pedestal.receiveShadow = true;
    robotRoot.add(pedestal);

    // Legs
    function createLeg(xSide: number) {
      const legGroup = new THREE.Group();
      legGroup.position.set(xSide * 0.35, -0.65, 0);

      const hip = new THREE.Mesh(new THREE.SphereGeometry(0.14, 20, 20), jointsMat);
      hip.castShadow = true;
      legGroup.add(hip);

      const leg = new THREE.Mesh(new RoundedBoxGeometry(0.30, 0.58, 0.32, 3, 0.08), shellMat);
      leg.position.set(0, -0.32, 0);
      leg.castShadow = true;
      legGroup.add(leg);

      const ankle = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 16), jointsMat);
      ankle.position.set(0, -0.65, 0);
      ankle.castShadow = true;
      legGroup.add(ankle);

      const foot = new THREE.Mesh(new RoundedBoxGeometry(0.34, 0.18, 0.54, 3, 0.06), shellLightMat);
      foot.position.set(0, -0.76, 0.1);
      foot.castShadow = true;
      legGroup.add(foot);

      return legGroup;
    }
    robotBodyGroup.add(createLeg(-1));
    robotBodyGroup.add(createLeg(1));

    // Torso
    const torsoMesh = new THREE.Mesh(new RoundedBoxGeometry(1.22, 1.12, 0.92, 4, 0.24), shellMat);
    torsoMesh.position.set(0, 0.16, 0);
    torsoMesh.castShadow = true;
    robotBodyGroup.add(torsoMesh);

    // Chest slab
    const chestSlab = new THREE.Mesh(new RoundedBoxGeometry(0.96, 0.22, 0.68, 3, 0.06), shellLightMat);
    chestSlab.position.set(0, 0.62, 0.06);
    chestSlab.castShadow = true;
    robotBodyGroup.add(chestSlab);

    // 3 LEDs
    const ledColors = [0xff8a3d, 0xff5a5f, 0xff3d8b];
    [-0.16, 0, 0.16].forEach((x, idx) => {
      const led = new THREE.Mesh(
        new THREE.SphereGeometry(0.032, 16, 16),
        new THREE.MeshBasicMaterial({ color: ledColors[idx] })
      );
      led.position.set(x, 0.44, 0.48);
      robotBodyGroup.add(led);
    });

    // Slots
    [-0.22, 0.22].forEach((x) => {
      const slot = new THREE.Mesh(new RoundedBoxGeometry(0.06, 0.26, 0.04, 2, 0.02), jointsMat);
      slot.position.set(x, 0.12, 0.47);
      robotBodyGroup.add(slot);

      const lip = new THREE.Mesh(new THREE.TorusGeometry(0.045, 0.018, 12, 16, Math.PI), jointsMat);
      lip.position.set(x, 0.25, 0.47);
      lip.rotation.z = Math.PI;
      robotBodyGroup.add(lip);
    });

    // Pelvis
    const pelvis = new THREE.Mesh(new RoundedBoxGeometry(0.85, 0.28, 0.7, 3, 0.1), jointsMat);
    pelvis.position.set(0, -0.44, 0);
    robotBodyGroup.add(pelvis);

    // Arms
    const leftArmGroup = new THREE.Group();
    const rightArmGroup = new THREE.Group();
    let leftForearmRef: THREE.Group | null = null;
    let rightForearmRef: THREE.Group | null = null;

    function assembleArm(group: THREE.Group, side: number) {
      group.position.set(side * 0.72, 0.54, 0);
      group.rotation.z = side * 0.16;

      const shoulder = new THREE.Mesh(new THREE.SphereGeometry(0.16, 20, 20), jointsMat);
      shoulder.castShadow = true;
      group.add(shoulder);

      const upperArm = new THREE.Mesh(new RoundedBoxGeometry(0.22, 0.46, 0.22, 3, 0.06), shellMat);
      upperArm.position.set(0, -0.26, 0);
      upperArm.castShadow = true;
      group.add(upperArm);

      const elbow = new THREE.Mesh(new THREE.SphereGeometry(0.13, 16, 16), jointsMat);
      elbow.position.set(0, -0.52, 0);
      elbow.castShadow = true;
      group.add(elbow);

      const forearm = new THREE.Group();
      forearm.position.set(0, -0.52, 0);
      forearm.rotation.x = -0.35;

      const armLower = new THREE.Mesh(new RoundedBoxGeometry(0.20, 0.40, 0.20, 3, 0.06), shellMat);
      armLower.position.set(0, -0.22, 0);
      armLower.castShadow = true;
      forearm.add(armLower);

      const hand = new THREE.Mesh(new RoundedBoxGeometry(0.18, 0.18, 0.22, 3, 0.05), shellLightMat);
      hand.position.set(0, -0.46, 0.02);
      hand.castShadow = true;
      forearm.add(hand);

      const thumb = new THREE.Mesh(new RoundedBoxGeometry(0.06, 0.09, 0.12, 2, 0.02), shellLightMat);
      thumb.position.set(side * -0.09, -0.44, 0.06);
      forearm.add(thumb);

      group.add(forearm);
      return forearm;
    }
    leftForearmRef = assembleArm(leftArmGroup, -1);
    rightForearmRef = assembleArm(rightArmGroup, 1);
    robotBodyGroup.add(leftArmGroup);
    robotBodyGroup.add(rightArmGroup);

    // Neck
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.26, 0.26, 0.24, 24), jointsMat);
    neck.position.set(0, 0.78, 0);
    robotBodyGroup.add(neck);

    // Head pivot
    const headPivot = new THREE.Group();
    headPivot.position.set(0, 0.78, 0);
    robotBodyGroup.add(headPivot);

    const headCenterGroup = new THREE.Group();
    headCenterGroup.position.set(0, 0.78, 0);
    headPivot.add(headCenterGroup);

    // Skull
    const skull = new THREE.Mesh(new RoundedBoxGeometry(1.5, 1.42, 1.3, 4, 0.2), shellMat);
    skull.castShadow = true;
    headCenterGroup.add(skull);

    // Dark back block & bars
    const darkBackBlock = new THREE.Mesh(new RoundedBoxGeometry(1.28, 1.14, 0.9, 3, 0.1), deepDarkMat);
    darkBackBlock.position.set(0, 0, -0.26);
    headCenterGroup.add(darkBackBlock);

    const barGeo1 = new THREE.BoxGeometry(0.04, 0.04, 0.12);
    const barGeo2 = new THREE.BoxGeometry(0.12, 0.04, 0.04);
    for (let i = 0; i < 26; i++) {
      const isTop = i > 16;
      const bar = new THREE.Mesh(isTop ? barGeo1 : barGeo2, jointsMat);
      if (!isTop) {
        bar.position.set((Math.random() - 0.5) * 1.1, (Math.random() - 0.5) * 0.95, -0.72);
      } else {
        bar.position.set((Math.random() - 0.5) * 1.0, 0.58, -0.2 - Math.random() * 0.4);
      }
      headCenterGroup.add(bar);
    }

    // Extruded rounded-rect frame
    function createRoundedRectShape(w: number, h: number, r: number) {
      const s = new THREE.Shape();
      const x = -w / 2, y = -h / 2;
      s.moveTo(x + r, y);
      s.lineTo(x + w - r, y);
      s.quadraticCurveTo(x + w, y, x + w, y + r);
      s.lineTo(x + w, y + h - r);
      s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      s.lineTo(x + r, y + h);
      s.quadraticCurveTo(x, y + h, x, y + h - r);
      s.lineTo(x, y + r);
      s.quadraticCurveTo(x, y, x + r, y);
      return s;
    }

    const outerFrame = createRoundedRectShape(1.5, 1.44, 0.3);
    const innerFrameHole = new THREE.Path();
    const iw = 1.08, ih = 1.02, ir = 0.2;
    const ix = -iw / 2, iy = -ih / 2;
    innerFrameHole.moveTo(ix + ir, iy);
    innerFrameHole.lineTo(ix + iw - ir, iy);
    innerFrameHole.quadraticCurveTo(ix + iw, iy, ix + iw, iy + ir);
    innerFrameHole.lineTo(ix + iw, iy + ih - ir);
    innerFrameHole.quadraticCurveTo(ix + iw, iy + ih, ix + iw - ir, iy + ih);
    innerFrameHole.lineTo(ix + ir, iy + ih);
    innerFrameHole.quadraticCurveTo(ix, iy + ih, ix, iy + ih - ir);
    innerFrameHole.lineTo(ix, iy + ir);
    innerFrameHole.quadraticCurveTo(ix, iy, ix + ir, iy);
    outerFrame.holes.push(innerFrameHole);

    const ringGeo = new THREE.ExtrudeGeometry(outerFrame, {
      depth: 0.1,
      bevelEnabled: true,
      bevelSegments: 4,
      steps: 1,
      bevelSize: 0.03,
      bevelThickness: 0.03,
    });
    ringGeo.center();

    ringGeo.computeBoundingBox();
    if (ringGeo.boundingBox) {
      const rMin = ringGeo.boundingBox.min;
      const rMax = ringGeo.boundingBox.max;
      const rxSpan = rMax.x - rMin.x;
      const rySpan = rMax.y - rMin.y;
      const pos = ringGeo.attributes.position;
      const uvs = ringGeo.attributes.uv;
      for (let i = 0; i < pos.count; i++) {
        const u = (pos.getX(i) - rMin.x) / rxSpan;
        const v = (pos.getY(i) - rMin.y) / rySpan;
        uvs.setXY(i, u, v);
      }
      uvs.needsUpdate = true;
    }

    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.position.set(0, 0, 0.60);
    headCenterGroup.add(ringMesh);

    // Bezel
    const bezelOuter = createRoundedRectShape(1.10, 1.04, 0.2);
    const bezelHole = new THREE.Path();
    const bw = 0.92, bh = 0.86, br = 0.1;
    const bx = -bw / 2, by = -bh / 2;
    bezelHole.moveTo(bx + br, by);
    bezelHole.lineTo(bx + bw - br, by);
    bezelHole.quadraticCurveTo(bx + bw, by, bx + bw, by + br);
    bezelHole.lineTo(bx + bw, by + bh - br);
    bezelHole.quadraticCurveTo(bx + bw, by + bh, bx + bw - br, by + bh);
    bezelHole.lineTo(bx + br, by + bh);
    bezelHole.quadraticCurveTo(bx, by + bh, bx, by + bh - br);
    bezelHole.lineTo(bx, by + br);
    bezelHole.quadraticCurveTo(bx, by, bx + br, by);
    bezelOuter.holes.push(bezelHole);

    const bezelGeo = new THREE.ExtrudeGeometry(bezelOuter, { depth: 0.04, bevelEnabled: false });
    bezelGeo.center();
    const bezelMesh = new THREE.Mesh(bezelGeo, shellLightMat);
    bezelMesh.position.set(0, 0, 0.62);
    headCenterGroup.add(bezelMesh);

    // Screen
    const screenMesh = new THREE.Mesh(new RoundedBoxGeometry(0.9, 0.84, 0.04, 3, 0.08), screenMat);
    screenMesh.position.set(0, 0, 0.66);
    headCenterGroup.add(screenMesh);

    // Ears
    const earGeo = new THREE.CylinderGeometry(0.22, 0.22, 0.18, 24);
    earGeo.rotateZ(Math.PI / 2);
    const leftEar = new THREE.Mesh(earGeo, shellMat);
    leftEar.position.set(-0.82, 0, 0);
    headCenterGroup.add(leftEar);
    const rightEar = new THREE.Mesh(earGeo, shellMat);
    rightEar.position.set(0.82, 0, 0);
    headCenterGroup.add(rightEar);

    const cableGeo = new THREE.TorusGeometry(0.24, 0.04, 16, 32, Math.PI);
    const cableMesh = new THREE.Mesh(cableGeo, jointsMat);
    cableMesh.position.set(0.88, -0.16, 0);
    cableMesh.rotation.y = Math.PI / 2;
    headCenterGroup.add(cableMesh);

    // Face rendering state
    let eyeAlpha = 1.0;
    let quoteAlpha = 0.0;
    let isBlinking = false;
    let blinkStartTime = 0;
    let nextBlinkTime = performance.now() + 3000;

    function renderFaceCanvas(now: number) {
      if (!faceCtx) return;
      faceCtx.fillStyle = '#060608';
      faceCtx.fillRect(0, 0, 512, 512);

      if (!isBlinking && now >= nextBlinkTime) {
        isBlinking = true;
        blinkStartTime = now;
      }
      let vScale = 1.0;
      if (isBlinking) {
        const progress = (now - blinkStartTime) / 180;
        if (progress >= 1.0) {
          isBlinking = false;
          nextBlinkTime = now + 2500 + Math.random() * 3000;
        } else {
          const squash = Math.sin(progress * Math.PI);
          vScale = 1.0 - 0.9 * squash;
        }
      }

      if (eyeAlpha > 0.01) {
        faceCtx.save();
        faceCtx.globalAlpha = eyeAlpha;
        faceCtx.fillStyle = '#ffffff';
        faceCtx.shadowColor = '#ffffff';
        faceCtx.shadowBlur = 18;

        faceCtx.beginPath();
        faceCtx.ellipse(196, 262, 30, Math.max(1, 38 * vScale), 0, 0, Math.PI * 2);
        faceCtx.fill();

        faceCtx.beginPath();
        faceCtx.ellipse(316, 252, 30, Math.max(1, 38 * vScale), 0, 0, Math.PI * 2);
        faceCtx.fill();

        faceCtx.restore();
      }

      if (quoteAlpha > 0.01) {
        faceCtx.save();
        faceCtx.globalAlpha = quoteAlpha;
        faceCtx.fillStyle = '#ffffff';
        faceCtx.shadowColor = '#ffffff';
        faceCtx.shadowBlur = 18;
        faceCtx.font = '900 560px "Arial Black", sans-serif';
        faceCtx.textAlign = 'center';
        faceCtx.textBaseline = 'middle';
        faceCtx.fillText('“', 256, 400);
        faceCtx.restore();
      }

      faceTexture.needsUpdate = true;
    }

    // Motion & Scroll interpolation
    let smoothP = 0;
    let targetCursorX = 0;
    let targetCursorY = 0;
    let cursorX = 0;
    let cursorY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      targetCursorX = (e.clientX / window.innerWidth) * 2 - 1;
      targetCursorY = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener('mousemove', handleMouseMove);

    function easeInOutCubic(t: number) {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    const clock = new THREE.Clock();

    function animate() {
      animationFrameId = requestAnimationFrame(animate);
      const now = performance.now();
      const time = clock.getElapsedTime();

      const rawP = Math.min(2, Math.max(0, window.scrollY / window.innerHeight));
      smoothP += (rawP - smoothP) * 0.08;

      cursorX += (targetCursorX - cursorX) * 0.06;
      cursorY += (targetCursorY - cursorY) * 0.06;

      const targetIsQuote = smoothP > 1.55;
      if (targetIsQuote) {
        quoteAlpha = Math.min(1.0, quoteAlpha + 0.05);
        eyeAlpha = Math.max(0.0, eyeAlpha - 0.05);
      } else {
        eyeAlpha = Math.min(1.0, eyeAlpha + 0.05);
        quoteAlpha = Math.max(0.0, quoteAlpha - 0.05);
      }
      renderFaceCanvas(now);

      const blend = easeInOutCubic(Math.min(1.0, smoothP));
      let camZ = 11.6 + (6.9 - 11.6) * blend;
      const camY = 1.1 + (1.95 - 1.1) * blend;
      const lookY = 0.55 + (1.72 - 0.55) * blend;

      if (window.innerWidth <= 900) {
        camZ *= 1.25;
      }

      camera.position.x = cursorX * 0.25;
      camera.position.y = camY - cursorY * 0.1;
      camera.position.z = camZ;
      camera.lookAt(0, lookY, 0);

      const baseBodyYaw = -0.42 + (-0.2 - -0.42) * blend;
      robotBodyGroup.rotation.y = baseBodyYaw + cursorX * 0.12;

      const baseHeadYaw = -0.6 + (-0.06 - -0.6) * blend;
      const baseHeadPitch = 0.16 + (0.04 - 0.16) * blend;
      const baseHeadRoll = 0.22 + (0 - 0.22) * blend;

      headPivot.rotation.y = baseHeadYaw + cursorX * 0.45;
      headPivot.rotation.x = baseHeadPitch + cursorY * 0.18 + Math.sin(0.9 * time) * 0.02;
      headPivot.rotation.z = baseHeadRoll + Math.sin(0.7 * time) * 0.02;

      robotBodyGroup.position.y = Math.sin(1.4 * time) * 0.02;
      leftArmGroup.rotation.x = Math.sin(1.4 * time - 0.5) * 0.05;
      rightArmGroup.rotation.x = Math.sin(1.4 * time + 0.5) * 0.05;
      if (leftForearmRef) {
        leftForearmRef.rotation.x = -0.35 + Math.sin(1.4 * time) * 0.06;
      }
      if (rightForearmRef) {
        rightForearmRef.rotation.x = -0.35 + Math.sin(1.4 * time + 0.5) * 0.06;
      }

      renderer.render(scene, camera);
    }
    animate();

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={`fixed inset-0 w-screen h-screen pointer-events-none z-0 ${className}`}
      data-testid="three-robot-canvas"
    />
  );
};
