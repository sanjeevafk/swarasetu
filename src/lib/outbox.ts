/**
 * IndexedDB outbox for offline triage records.
 * Records are queued while offline and flushed to POST /api/v1/sync/cases
 * when connectivity returns (idempotent via client_uuid on the server).
 */

import type { SyncCaseItem } from '@/types/api';

const DB_NAME = 'swarasetu-outbox';
const DB_VERSION = 1;
const STORE = 'pending-cases';

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'client_uuid' });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function withStore<T>(
  mode: IDBTransactionMode,
  fn: (store: IDBObjectStore) => IDBRequest,
): Promise<T> {
  const db = await openDb();
  try {
    return await new Promise<T>((resolve, reject) => {
      const tx = db.transaction(STORE, mode);
      const req = fn(tx.objectStore(STORE));
      tx.oncomplete = () => resolve(req.result as T);
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

export async function enqueue(item: SyncCaseItem): Promise<void> {
  await withStore<void>('readwrite', (store) => store.put(item));
}

export async function listQueued(): Promise<SyncCaseItem[]> {
  return withStore<SyncCaseItem[]>('readonly', (store) => store.getAll());
}

export async function countQueued(): Promise<number> {
  return withStore<number>('readonly', (store) => store.count());
}

export async function removeQueued(uuids: string[]): Promise<void> {
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      const store = tx.objectStore(STORE);
      uuids.forEach((uuid) => store.delete(uuid));
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

export interface FlushResult {
  ok: boolean;
  accepted: number;
  duplicates: number;
}

/** Push every queued record to the backend; clear only acknowledged ones. */
export async function flushOutbox(
  syncFn: (items: SyncCaseItem[]) => Promise<{ accepted: number; duplicates: number }>,
): Promise<FlushResult> {
  const queued = await listQueued();
  if (queued.length === 0) {
    return { ok: true, accepted: 0, duplicates: 0 };
  }
  try {
    const res = await syncFn(queued);
    await removeQueued(queued.map((q) => q.client_uuid));
    return { ok: true, ...res };
  } catch {
    return { ok: false, accepted: 0, duplicates: 0 };
  }
}
