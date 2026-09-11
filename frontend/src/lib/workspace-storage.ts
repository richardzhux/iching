import type { StateStorage } from "zustand/middleware"

// Full source texts outgrow localStorage's small quota after a few readings.
// Keep the existing localStorage snapshot intact as a migration fallback.
const DATABASE = "iching-workspace"
const OBJECT_STORE = "workspace"
let database: Promise<IDBDatabase> | undefined
let writes: Promise<void> = Promise.resolve()

function openDatabase() {
  database ??= new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 1)
    request.onupgradeneeded = () => {
      request.result.createObjectStore(OBJECT_STORE)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
  return database
}

async function read(name: string): Promise<string | null> {
  const db = await openDatabase()
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(OBJECT_STORE, "readonly")
    const request = transaction.objectStore(OBJECT_STORE).get(name)
    request.onsuccess = () => resolve(typeof request.result === "string" ? request.result : null)
    request.onerror = () => reject(request.error)
  })
}

async function write(name: string, value: string | null) {
  const db = await openDatabase()
  return new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(OBJECT_STORE, "readwrite")
    const store = transaction.objectStore(OBJECT_STORE)
    if (value === null) store.delete(name)
    else store.put(value, name)
    transaction.oncomplete = () => resolve()
    transaction.onerror = () => reject(transaction.error)
    transaction.onabort = () => reject(transaction.error)
  })
}

export const workspaceStorage: StateStorage = {
  async getItem(name) {
    await writes.catch(() => undefined)
    try {
      const stored = await read(name)
      if (stored !== null) return stored
    } catch {
      // Environments without IndexedDB can continue using the legacy store.
    }
    return localStorage.getItem(name)
  },
  setItem(name, value) {
    writes = writes.catch(() => undefined).then(async () => {
      try { await write(name, value) }
      catch { localStorage.setItem(name, value) }
    })
    return writes
  },
  removeItem(name) {
    writes = writes.catch(() => undefined).then(async () => {
      await write(name, null)
      localStorage.removeItem(name)
    })
    return writes
  },
}
