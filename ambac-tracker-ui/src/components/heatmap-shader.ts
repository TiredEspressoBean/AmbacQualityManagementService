import * as THREE from "three";

// Vertex shader
const vertexShader = `
  varying vec3 vWorldPosition;
  varying vec3 vNormal;

  void main() {
    vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;
    vNormal = normalize(normalMatrix * normal);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

// Fragment shader
const fragmentShader = `
  uniform vec3 annotationPositions[50];
  uniform int annotationCount;
  uniform float heatRadius;
  uniform float heatIntensity;
  uniform vec3 baseColor;

  varying vec3 vWorldPosition;
  varying vec3 vNormal;

  // Heat map color gradient: blue -> cyan -> green -> yellow -> red
  vec3 getHeatColor(float t) {
    // Clamp t between 0 and 1
    t = clamp(t, 0.0, 1.0);

    if (t < 0.25) {
      // Blue to Cyan
      float localT = t / 0.25;
      return mix(vec3(0.0, 0.0, 1.0), vec3(0.0, 1.0, 1.0), localT);
    } else if (t < 0.5) {
      // Cyan to Green
      float localT = (t - 0.25) / 0.25;
      return mix(vec3(0.0, 1.0, 1.0), vec3(0.0, 1.0, 0.0), localT);
    } else if (t < 0.75) {
      // Green to Yellow
      float localT = (t - 0.5) / 0.25;
      return mix(vec3(0.0, 1.0, 0.0), vec3(1.0, 1.0, 0.0), localT);
    } else {
      // Yellow to Red
      float localT = (t - 0.75) / 0.25;
      return mix(vec3(1.0, 1.0, 0.0), vec3(1.0, 0.0, 0.0), localT);
    }
  }

  void main() {
    float totalHeat = 0.0;

    // Calculate heat contribution from each annotation
    for (int i = 0; i < 50; i++) {
      if (i >= annotationCount) break;

      vec3 annotationPos = annotationPositions[i];
      float dist = distance(vWorldPosition, annotationPos);

      // Inverse distance falloff
      float heat = heatIntensity / (1.0 + dist / heatRadius);
      totalHeat += heat;
    }

    // Normalize heat value
    totalHeat = clamp(totalHeat, 0.0, 1.0);

    // Mix base color with heat color
    vec3 heatColor = getHeatColor(totalHeat);
    vec3 finalColor = mix(baseColor, heatColor, totalHeat);

    // Add basic lighting
    vec3 lightDir = normalize(vec3(1.0, 1.0, 1.0));
    float diffuse = max(dot(vNormal, lightDir), 0.0) * 0.5 + 0.5;
    finalColor *= diffuse;

    gl_FragColor = vec4(finalColor, 1.0);
  }
`;

export interface HeatMapShaderProps {
  annotationPositions: THREE.Vector3[];
  heatRadius?: number;
  heatIntensity?: number;
  baseColor?: THREE.Color;
}

export function createHeatMapMaterial({
  annotationPositions,
  heatRadius = 0.5,
  heatIntensity = 1.0,
  baseColor = new THREE.Color(0x94a3b8),
}: HeatMapShaderProps): THREE.ShaderMaterial {
  // Pad positions array to 50 (shader limit)
  const paddedPositions = new Float32Array(150); // 50 * 3 (x, y, z)

  annotationPositions.slice(0, 50).forEach((pos, i) => {
    paddedPositions[i * 3] = pos.x;
    paddedPositions[i * 3 + 1] = pos.y;
    paddedPositions[i * 3 + 2] = pos.z;
  });

  return new THREE.ShaderMaterial({
    uniforms: {
      annotationPositions: { value: paddedPositions },
      annotationCount: { value: Math.min(annotationPositions.length, 50) },
      heatRadius: { value: heatRadius },
      heatIntensity: { value: heatIntensity },
      baseColor: { value: baseColor },
    },
    vertexShader,
    fragmentShader,
    side: THREE.DoubleSide,
  });
}
