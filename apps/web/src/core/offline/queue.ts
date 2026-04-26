// Phase A item 5 — Offline queue + online-status hook.
//
// Spec: docs/chartnav/closure/PHASE_A_Tablet_Charting_Requirements.md §3.3.
//
// What this module is:
//   - A small IndexedDB-backed queue of pending writes the tablet
//     accumulates while offline (per-encounter key, single-writer
//     guarantee per encounter, simple FIFO).
//   - A `useOnlineStatus` hook that drives the offline banner and the
//     offline-guard for sign / export.
//
// What this module is NOT (truth limitations §9):
//   - It is NOT a full offline-first documentation engine. There is
//     no CRDT, no merge resolver, no background-sync registration
//     against a service worker. ChartNav is explicitly NOT
//     offline-first in Phase A.
//   - When the network drops mid-encounter, the queue lets the
//     clinician keep typing; on reconnect a flush is attempted but
//     a server-side conflict (newer attestation, e.g.) is surfaced
//     for explicit resolution rather than silently merged.
import { useEffect, useState } from "react";

const DB_NAME = "chartnav-offline";
const DB_VERSION = 1;
const STORE = "queue";

export interface QueuedWrite {
  id: string;                 // `${encounterId}:${monotonic}`
  encounterId: number;
  enqueuedAt: string;         // ISO timestamp
  method: "POST" | "PATCH" | "PUT";
  path: string;               // relative to API base URL
  body: unknown;
}

let _dbPromise: Promise<IDBDatabase> | null = null;

function openDb(): Promise<IDBDatabase> {
  if (_dbPromise) return _dbPromise;
  if (typeof indexedDB === "undefined") {
    return Promise.reject(new Error("indexeddb_unavailable"));
  }
  _dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        const store = db.createObjectStore(STORE, { keyPath: "id" });
        store.createIndex("encounterId", "encounterId", { unique: false });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return _dbPromise;
}

/** Reset the cached DB handle (test-only convenience; do not call in
 *  production code). */
export function _resetOfflineQueueForTests() {
  _dbPromise = null;
}

export async function enqueueWrite(write: QueuedWrite): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(write);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function listQueuedWrites(encounterId?: number): Promise<QueuedWrite[]> {
  const db = await openDb();
  return new Promise<QueuedWrite[]>((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const store = tx.objectStore(STORE);
    const req = encounterId !== undefined
      ? store.index("encounterId").getAll(IDBKeyRange.only(encounterId))
      : store.getAll();
    req.onsuccess = () => resolve((req.result || []) as QueuedWrite[]);
    req.onerror = () => reject(req.error);
  });
}

export async function dropQueuedWrite(id: string): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function clearQueue(): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).clear();
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/** Best-effort flush. Returns the writes that succeeded; conflicts
 *  (HTTP 409) are surfaced to the caller for resolution rather than
 *  silently merged. */
export async function flushQueue(
  apiBase: string,
  identityHeader: Record<string, string>,
): Promise<{ flushed: QueuedWrite[]; conflicts: QueuedWrite[]; errors: { write: QueuedWrite; status: number }[] }> {
  const flushed: QueuedWrite[] = [];
  const conflicts: QueuedWrite[] = [];
  const errors: { write: QueuedWrite; status: number }[] = [];
  const queued = await listQueuedWrites();
  // FIFO by enqueuedAt then id for stability.
  queued.sort((a, b) => (a.enqueuedAt < b.enqueuedAt ? -1 : a.enqueuedAt > b.enqueuedAt ? 1 : a.id.localeCompare(b.id)));
  for (const w of queued) {
    try {
      const r = await fetch(`${apiBase}${w.path}`, {
        method: w.method,
        headers: { "Content-Type": "application/json", ...identityHeader },
        body: JSON.stringify(w.body),
      });
      if (r.ok) {
        await dropQueuedWrite(w.id);
        flushed.push(w);
      } else if (r.status === 409) {
        conflicts.push(w);
      } else {
        errors.push({ write: w, status: r.status });
      }
    } catch {
      // Network still flaky — leave the write in the queue and stop.
      break;
    }
  }
  return { flushed, conflicts, errors };
}

/** Hook: returns the current navigator.onLine value and updates on
 *  `online` / `offline` events. Defaults to `true` in non-browser
 *  environments (jsdom / node) so unit tests see the optimistic state. */
export function useOnlineStatus(): boolean {
  const initial =
    typeof navigator !== "undefined" && typeof navigator.onLine === "boolean"
      ? navigator.onLine
      : true;
  const [online, setOnline] = useState<boolean>(initial);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);
  return online;
}
