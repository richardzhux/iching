import { HEXAGRAM_LIBRARY } from "./hexagram-library"

export type RelationKind = "main" | "changed" | "mutual" | "inverse" | "reverse"

/** All binaries in the project are ordered from the first (bottom) line upward. */
export function hexagramBinary(values: readonly number[]) {
  return values.map((value) => value === 7 || value === 9 ? "1" : "0").join("")
}

export function relatedHexagramBinaries(values: readonly number[]) {
  if (values.length !== 6 || values.some((value) => ![6, 7, 8, 9].includes(value))) return []
  const binary = hexagramBinary(values)
  const changed = values.some((value) => value === 6 || value === 9)
    ? values.map((value) => value === 6 || value === 7 ? "1" : "0").join("")
    : null
  return [
    { kind: "main" as const, binary },
    { kind: "changed" as const, binary: changed },
    { kind: "mutual" as const, binary: binary.slice(1, 4) + binary.slice(2, 5) },
    { kind: "inverse" as const, binary: [...binary].map((bit) => bit === "1" ? "0" : "1").join("") },
    { kind: "reverse" as const, binary: [...binary].reverse().join("") },
  ].map((item) => ({ ...item, entry: HEXAGRAM_LIBRARY.find((entry) => entry.binary === item.binary) }))
}

export function lineName(position: number, yang: boolean) {
  const number = yang ? "九" : "六"
  return position === 1 ? `初${number}` : position === 6 ? `上${number}` : `${number}${["", "一", "二", "三", "四", "五"][position]}`
}
