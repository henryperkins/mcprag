import { deriveKey, encryptJson, decryptJson } from './crypto';

let keyCache: CryptoKey | null = null;

async function getKey(): Promise<CryptoKey> {
  if (!keyCache) {
    keyCache = await deriveKey('session-v1');
  }
  return keyCache;
}

export async function loadEncrypted<T>(
  storageKey: string,
  fallback: T
): Promise<T> {
  try {
    const stored = localStorage.getItem(storageKey);
    if (!stored) return fallback;
    
    const key = await getKey();
    return await decryptJson<T>(key, stored);
  } catch (error) {
    console.warn('Failed to load encrypted data:', error);
    return fallback;
  }
}

export async function saveEncrypted<T>(
  storageKey: string,
  value: T
): Promise<void> {
  try {
    const key = await getKey();
    const encrypted = await encryptJson(key, value);
    localStorage.setItem(storageKey, encrypted);
  } catch (error) {
    console.error('Failed to save encrypted data:', error);
  }
}