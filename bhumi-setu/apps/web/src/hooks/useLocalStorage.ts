import { useState, useEffect } from 'react';

/**
 * Hook for persisting state in localStorage with automatic
 * serialization/deserialization.
 *
 * @param key - localStorage key
 * @param initialValue - Default value if key doesn't exist
 * @returns Tuple of [value, setValue] similar to useState
 *
 * @example
 * ```tsx
 * const [language, setLanguage] = useLocalStorage('app-language', 'en');
 * ```
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? (JSON.parse(item) as T) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(storedValue));
    } catch (error) {
      console.warn(`Error writing localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  return [storedValue, setStoredValue];
}
