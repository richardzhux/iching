"use client"

import { useEffect, useRef, useState } from "react"
import { getImageProps } from "next/image"
import * as THREE from "three"
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js"
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js"
import { useAutumnMotion } from "./autumn-motion"

export type AutumnStageProps = {
  values?: readonly number[]
  coins?: readonly number[] | null
  toss?: number
  changed?: boolean
  preview?: boolean
  showCoins?: boolean
  showStalks?: boolean
  showCompass?: boolean
  ritualPhase?: number
  remainingStalks?: number
  upperTrigram?: number | null
  lowerTrigram?: number | null
  selectedLine?: number | null
  onToss?: () => void
  onLineSelect?: (position: number) => void
}

const PREVIEW = [8, 9, 7, 8, 7, 8]
const EMPTY: readonly number[] = []

export default function AutumnStage(props: AutumnStageProps) {
  const container = useRef<HTMLDivElement>(null)
  const { paused } = useAutumnMotion()
  const latest = useRef({ ...props, paused })
  const redraw = useRef<(() => void) | null>(null)
  const [unavailable, setUnavailable] = useState(false)

  useEffect(() => {
    latest.current = { ...props, paused }
    redraw.current?.()
  }, [props, paused])

  useEffect(() => {
    const mount = container.current
    if (!mount) return
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "low-power" })
    } catch {
      const fallback = requestAnimationFrame(() => setUnavailable(true))
      return () => cancelAnimationFrame(fallback)
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75))
    renderer.setClearColor(0x000000, 0)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 0.94
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFShadowMap
    mount.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    const camera = new THREE.OrthographicCamera(0, 1, 1, 0, 1, 4000)
    camera.position.z = 1800
    const world = new THREE.Group()
    scene.add(world)

    const room = new RoomEnvironment()
    const pmrem = new THREE.PMREMGenerator(renderer)
    const environment = pmrem.fromScene(room, 0.04)
    scene.environment = environment.texture
    room.dispose()
    pmrem.dispose()
    scene.add(new THREE.HemisphereLight(0xfff8e9, 0xa16a42, 0.9))
    const sunlight = new THREE.DirectionalLight(0xffe8bc, 2.5)
    sunlight.position.set(-350, 900, 800)
    sunlight.castShadow = true
    sunlight.position.set(300, -160, 950)
    sunlight.target.position.set(850, -780, 0)
    sunlight.shadow.mapSize.set(1024, 1024)
    sunlight.shadow.camera.left = -850
    sunlight.shadow.camera.right = 850
    sunlight.shadow.camera.top = 850
    sunlight.shadow.camera.bottom = -850
    sunlight.shadow.camera.far = 3000
    sunlight.shadow.bias = -0.0004
    sunlight.shadow.normalBias = 0.4
    world.add(sunlight, sunlight.target)
    const groundGeometry = new THREE.PlaneGeometry(700, 180)
    const groundMaterial = new THREE.ShadowMaterial({ opacity: 0.18 })
    const ground = new THREE.Mesh(groundGeometry, groundMaterial)
    ground.position.set(850, -785, -35)
    ground.receiveShadow = true
    world.add(ground)

    const loader = new THREE.TextureLoader()
    const textures: THREE.Texture[] = []
    const loadTexture = (path: string) => {
      const texture = loader.load(path, () => redraw.current?.())
      texture.colorSpace = THREE.SRGBColorSpace
      texture.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 4)
      textures.push(texture)
      return texture
    }
    const stone = loadTexture("/autumn/ivory-stone.webp")
    stone.wrapS = stone.wrapT = THREE.RepeatWrapping
    stone.repeat.set(0.7, 0.18)
    const coinTexture = (src: string) => getImageProps({ src, alt: "", width: 256, height: 256 }).props.src
    const front = loadTexture(coinTexture("/autumn/coin-front.png"))
    const back = loadTexture(coinTexture("/autumn/coin-back.png"))

    const whole = new RoundedBoxGeometry(274, 50, 27, 4, 5)
    const half = new RoundedBoxGeometry(126, 50, 27, 4, 5)
    const rows = Array.from({ length: 6 }, (_, index) => {
      const group = new THREE.Group()
      const material = new THREE.MeshPhysicalMaterial({ map: stone, bumpMap: stone, bumpScale: 0.8, color: 0xdfcab0, roughness: 0.49, metalness: 0.04, clearcoat: 0.3, clearcoatRoughness: 0.4, envMapIntensity: 0.35, transparent: true })
      const solid = new THREE.Mesh(whole, material)
      const left = new THREE.Mesh(half, material)
      const right = new THREE.Mesh(half, material)
      left.position.x = -74
      right.position.x = 74
      for (const mesh of [solid, left, right]) mesh.userData.line = index + 1
      group.add(solid, left, right)
      group.position.set(850, -(619 - index * 78), 0)
      group.rotation.set(0.15, -0.13, 0)
      world.add(group)
      return { group, material, solid, left, right, appeared: -1, value: 0 }
    })

    const coinShape = new THREE.Shape()
    coinShape.absarc(0, 0, 57, 0, Math.PI * 2, false)
    const hole = new THREE.Path()
    hole.moveTo(-12, -12)
    hole.lineTo(-12, 12)
    hole.lineTo(12, 12)
    hole.lineTo(12, -12)
    hole.closePath()
    coinShape.holes.push(hole)
    const coinBody = new THREE.ExtrudeGeometry(coinShape, { depth: 5, bevelEnabled: true, bevelSize: 1, bevelThickness: 1, bevelSegments: 2, curveSegments: 64, steps: 1 })
    coinBody.translate(0, 0, -2.5)
    const bronze = new THREE.MeshStandardMaterial({ color: 0x936331, metalness: 0.76, roughness: 0.5, envMapIntensity: 1.1 })
    const faceGeometry = new THREE.PlaneGeometry(126, 126)
    const faceFront = new THREE.MeshStandardMaterial({ map: front, transparent: true, alphaTest: 0.12, color: 0xa0784c, roughness: 0.65, metalness: 0.38, envMapIntensity: 0.25 })
    const faceBack = new THREE.MeshStandardMaterial({ map: back, transparent: true, alphaTest: 0.12, color: 0xa0784c, roughness: 0.65, metalness: 0.38, envMapIntensity: 0.25 })
    const coinPositions = [[712, 739, -0.18], [854, 730, 0.12], [996, 739, -0.28]]
    const coins = coinPositions.map(([x, y, angle], index) => {
      const group = new THREE.Group()
      const body = new THREE.Mesh(coinBody, bronze)
      body.castShadow = true
      const obverse = new THREE.Mesh(faceGeometry, faceFront)
      const reverse = new THREE.Mesh(faceGeometry, faceBack)
      obverse.position.z = 3.7
      reverse.position.z = -3.7
      reverse.rotation.y = Math.PI
      for (const mesh of [body, obverse, reverse]) mesh.userData.coin = index
      group.add(body, obverse, reverse)
      group.position.set(x, -y, 35)
      group.rotation.set(-0.42, index === 1 ? 0.24 : -0.18, angle)
      world.add(group)
      return { group, x, y, angle }
    })

    const stalkGeometry = new THREE.CylinderGeometry(1.6, 2.1, 139, 7)
    const stalkMaterial = new THREE.MeshStandardMaterial({ color: 0xcaa77c, roughness: 0.72, metalness: 0.03 })
    const setAsideMaterial = new THREE.MeshStandardMaterial({ color: 0x9d7c57, roughness: 0.8, transparent: true, opacity: 0.5 })
    const stalks = Array.from({ length: 50 }, () => {
      const stalk = new THREE.Mesh(stalkGeometry, stalkMaterial)
      stalk.castShadow = true
      stalk.position.set(854, -737, 40)
      world.add(stalk)
      return stalk
    })

    const compass = new THREE.Group()
    compass.position.set(854, -752, 25)
    compass.rotation.x = -0.3
    const ringGeometry = new THREE.TorusGeometry(99, 1.5, 7, 80)
    const ringMaterial = new THREE.MeshStandardMaterial({ color: 0xa77837, roughness: 0.5, metalness: 0.7 })
    const ring = new THREE.Mesh(ringGeometry, ringMaterial)
    compass.add(ring)
    const glyphGeometry = new THREE.BoxGeometry(21, 2.5, 2.5)
    const glyphHalfGeometry = new THREE.BoxGeometry(8.5, 2.5, 2.5)
    const trigramBits = ["111", "011", "101", "001", "110", "010", "100", "000"]
    const compassSigns = trigramBits.map((bits, index) => {
      const group = new THREE.Group()
      const material = new THREE.MeshStandardMaterial({ color: 0x8d6638, roughness: 0.55, metalness: 0.45 })
      const angle = Math.PI / 2 - index * Math.PI / 4
      group.position.set(Math.cos(angle) * 78, Math.sin(angle) * 78, 0)
      group.rotation.z = angle - Math.PI / 2
      bits.split("").forEach((bit, row) => {
        if (bit === "1") {
          const line = new THREE.Mesh(glyphGeometry, material)
          line.position.y = 7 - row * 7
          group.add(line)
        } else {
          for (const x of [-6.5, 6.5]) {
            const line = new THREE.Mesh(glyphHalfGeometry, material)
            line.position.set(x, 7 - row * 7, 0)
            group.add(line)
          }
        }
      })
      compass.add(group)
      return { group, material }
    })
    const petalGeometry = new THREE.SphereGeometry(12, 12, 8)
    const petals = Array.from({ length: 5 }, (_, index) => {
      const angle = index * Math.PI * 2 / 5 + Math.PI / 2
      const petal = new THREE.Mesh(petalGeometry, ringMaterial)
      petal.position.set(Math.cos(angle) * 15, Math.sin(angle) * 15, 0)
      petal.scale.set(0.9, 1.2, 0.23)
      petal.rotation.z = angle - Math.PI / 2
      compass.add(petal)
      return petal
    })
    world.add(compass)

    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()
    const aim = { x: 0, y: 0 }
    let hover = 0
    let frame = 0
    let visible = true
    let disposed = false
    let lastToss = 0
    let tossStarted = -100
    let lastChanged = false
    let changeStarted = -100
    let lastRitualPhase = 0
    let ritualStarted = -100
    const epoch = performance.now()

    function render() {
      frame = 0
      if (disposed || !visible || document.hidden) return
      const now = (performance.now() - epoch) / 1000
      const current = latest.current
      const values = current.preview ? PREVIEW : current.values ?? EMPTY
      if ((current.toss ?? 0) !== lastToss) {
        lastToss = current.toss ?? 0
        tossStarted = now
      }
      if (Boolean(current.changed) !== lastChanged) {
        lastChanged = Boolean(current.changed)
        changeStarted = now
      }
      if ((current.ritualPhase ?? 0) !== lastRitualPhase) {
        lastRitualPhase = current.ritualPhase ?? 0
        ritualStarted = now
      }
      rows.forEach((row, index) => {
        const value = values[index]
        const filled = value === 6 || value === 7 || value === 8 || value === 9
        const moving = value === 6 || value === 9
        const yang = Boolean(value === 7 || value === 9) !== Boolean(current.changed && moving)
        if (row.value !== (value ?? 0)) {
          row.value = value ?? 0
          row.appeared = now
        }
        const appear = current.paused ? 1 : THREE.MathUtils.clamp((now - row.appeared) / 0.65, 0, 1)
        const grow = 1 - Math.pow(1 - appear, 3)
        row.solid.visible = !filled || yang
        row.left.visible = row.right.visible = filled && !yang
        row.material.opacity = filled ? 0.5 + grow * 0.5 : 0.19
        row.material.color.set(moving ? 0xe7b65b : 0xdfcab0)
        row.material.emissive.set(moving ? 0x7a4108 : 0x000000)
        row.material.emissiveIntensity = moving ? 0.1 : 0
        row.material.metalness = moving ? 0.55 : 0.02
        row.material.roughness = moving ? 0.33 : 0.65
        row.material.envMapIntensity = moving ? 0.8 : 0.35
        const active = hover === index + 1 || current.selectedLine === index + 1
        const changeWave = !current.paused && moving ? Math.sin(Math.min((now - changeStarted) / 0.75, 1) * Math.PI) : 0
        row.group.scale.setScalar(filled ? 0.95 + grow * 0.05 : 1)
        row.group.position.y = -(619 - index * 78) - (1 - grow) * 13 + (current.paused ? 0 : Math.sin(now * 0.65 + index * 0.14) * 2.4)
        row.group.position.z = active ? 16 : 0
        row.group.rotation.y = -0.13 + (current.paused ? 0 : aim.x * 0.07) + changeWave * 0.35
        row.group.rotation.x = 0.15 + (current.paused ? 0 : aim.y * 0.04)
      })
      coins.forEach((coin, index) => {
        coin.group.visible = current.showCoins !== false
        const progress = current.paused ? 1 : THREE.MathUtils.clamp((now - tossStarted) / 1.22, 0, 1)
        const airborne = progress > 0 && progress < 1
        const turn = 1 - Math.pow(1 - progress, 2)
        const reverse = current.coins?.[index] === 3
        coin.group.position.y = -coin.y + (airborne ? Math.sin(progress * Math.PI) * (112 + index * 15) : current.paused ? 0 : Math.sin(now * 0.75 + index) * 3)
        coin.group.position.x = coin.x + (airborne ? Math.sin(progress * Math.PI) * (index - 1) * 14 : 0)
        coin.group.rotation.x = -0.64 + (airborne ? turn * Math.PI * (8 + index * 2) : 0)
        coin.group.rotation.y = (reverse ? Math.PI : 0) + (index === 1 ? 0.24 : -0.18) + (airborne ? turn * Math.PI * 4 : 0)
        coin.group.rotation.z = coin.angle + (airborne ? Math.sin(progress * Math.PI) * 0.65 : 0)
      })
      const ritualProgress = current.paused ? 1 : THREE.MathUtils.clamp((now - ritualStarted) / 0.5, 0, 1)
      const remaining = current.remainingStalks ?? 49
      stalks.forEach((stalk, index) => {
        stalk.visible = Boolean(current.showStalks)
        if (!stalk.visible) return
        const reserved = index === 49
        const active = index < remaining
        const halfCount = Math.ceil(remaining / 2)
        const inLeft = index < halfCount
        const localIndex = inLeft ? index : index - halfCount
        const bundleSize = inLeft ? halfCount : remaining - halfCount
        const gathered = !current.ritualPhase
        const x = reserved ? 1080 : !active ? 1034 + (index - remaining) * 3 : gathered ? 780 + index * 3.1 : (inLeft ? 788 : 922) + (localIndex - bundleSize / 2) * 3.8
        const y = reserved ? -724 : !active ? -760 : -744 + (index % 4) * 2 + (!current.paused ? Math.sin(ritualProgress * Math.PI) * (index % 2 ? 16 : -12) : 0)
        const angle = reserved ? -0.7 : !active ? -0.3 : gathered ? (24 - index) * 0.014 : (inLeft ? 0.24 : -0.24) + (localIndex - bundleSize / 2) * 0.012
        const speed = current.paused ? 1 : 0.13
        stalk.position.x += (x - stalk.position.x) * speed
        stalk.position.y += (y - stalk.position.y) * speed
        stalk.rotation.z += (angle - stalk.rotation.z) * speed
        stalk.rotation.x = -0.22
        stalk.material = active || reserved ? stalkMaterial : setAsideMaterial
      })
      compass.visible = Boolean(current.showCompass)
      if (compass.visible) {
        const turn = current.paused ? 0 : Math.sin(Math.min((now - tossStarted) / 0.95, 1) * Math.PI) * 0.28
        compass.rotation.z = turn
        compassSigns.forEach(({ group, material }, index) => {
          const phase = current.ritualPhase ?? 0
          const chosen = phase === 1 ? index + 1 === current.upperTrigram : phase >= 2 ? index + 1 === current.lowerTrigram || index + 1 === current.upperTrigram : false
          material.color.set(chosen ? 0xe4ad4d : 0x8d6638)
          material.emissive.set(chosen ? 0x8c5110 : 0x000000)
          material.emissiveIntensity = chosen ? 0.25 : 0
          group.scale.setScalar(chosen ? 1.18 : 1)
          group.position.z = chosen ? 10 : 0
        })
        petals.forEach((petal, index) => { petal.scale.z = 0.23 + (current.paused ? 0 : Math.sin(now * 0.8 + index) * 0.035) })
      }
      renderer.render(scene, camera)
      if (!current.paused) frame = requestAnimationFrame(render)
    }
    function requestRender() {
      if (!frame && !disposed) frame = requestAnimationFrame(render)
    }
    redraw.current = requestRender
    const resize = () => {
      const { width, height } = mount.getBoundingClientRect()
      if (!width || !height) return
      renderer.setSize(width, height)
      camera.right = width
      camera.top = height
      camera.updateProjectionMatrix()
      const scale = Math.max(width / 1536, height / 1024)
      const position = width < 760 ? 0.55 : 0.5
      world.scale.setScalar(scale)
      world.position.set((width - 1536 * scale) * position, height - (height - 1024 * scale) / 2, 0)
      requestRender()
    }
    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(mount)
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (visible) requestRender() }, { threshold: 0.01 })
    observer.observe(mount)
    const visibility = () => { if (!document.hidden) requestRender() }
    document.addEventListener("visibilitychange", visibility)
    const findObject = (event: MouseEvent) => {
      const rect = mount.getBoundingClientRect()
      pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1)
      raycaster.setFromCamera(pointer, camera)
      return raycaster.intersectObjects([...rows.map((row) => row.group), ...coins.map((coin) => coin.group)], true)[0]?.object
    }
    const move = (event: PointerEvent) => {
      const object = findObject(event)
      hover = Number(object?.userData.line ?? 0)
      aim.x = pointer.x
      aim.y = pointer.y
      renderer.domElement.style.cursor = object && (latest.current.onToss || latest.current.onLineSelect) ? "pointer" : "default"
      requestRender()
    }
    const leave = () => { hover = 0; aim.x = 0; aim.y = 0; requestRender() }
    const click = (event: MouseEvent) => {
      const object = findObject(event)
      if (object?.userData.line) latest.current.onLineSelect?.(Number(object.userData.line))
      else if (object?.userData.coin !== undefined) latest.current.onToss?.()
    }
    mount.addEventListener("pointermove", move)
    mount.addEventListener("pointerleave", leave)
    mount.addEventListener("click", click)
    resize()

    return () => {
      disposed = true
      redraw.current = null
      cancelAnimationFrame(frame)
      resizeObserver.disconnect()
      observer.disconnect()
      document.removeEventListener("visibilitychange", visibility)
      mount.removeEventListener("pointermove", move)
      mount.removeEventListener("pointerleave", leave)
      mount.removeEventListener("click", click)
      whole.dispose(); half.dispose(); coinBody.dispose(); faceGeometry.dispose()
      rows.forEach((row) => row.material.dispose())
      stalkGeometry.dispose(); stalkMaterial.dispose(); setAsideMaterial.dispose()
      ringGeometry.dispose(); ringMaterial.dispose(); glyphGeometry.dispose(); glyphHalfGeometry.dispose(); petalGeometry.dispose()
      compassSigns.forEach(({ material }) => material.dispose())
      bronze.dispose(); faceFront.dispose(); faceBack.dispose()
      textures.forEach((texture) => texture.dispose())
      sunlight.shadow.dispose()
      groundGeometry.dispose(); groundMaterial.dispose()
      environment.dispose()
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [])

  return (
    <div ref={container} className="autumn-stage" aria-hidden="true">
      {unavailable && props.values?.length ? (
        <div className="autumn-stage-fallback">
          {[...props.values].reverse().map((value, index) => <p key={index}>{props.values!.length - index} · {value === 7 || value === 9 ? "yang" : "yin"}{value === 6 || value === 9 ? " · changing" : ""}</p>)}
        </div>
      ) : null}
    </div>
  )
}
