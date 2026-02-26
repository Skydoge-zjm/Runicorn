import { describe, it, expect } from 'vitest'
import en from '../locales/en/index'
import zh from '../locales/zh/index'

/** Recursively collect all leaf keys with dot-notation paths */
function collectKeys(obj: Record<string, any>, prefix = ''): string[] {
  const keys: string[] = []
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      keys.push(...collectKeys(v, path))
    } else {
      keys.push(path)
    }
  }
  return keys.sort()
}

describe('i18n key completeness', () => {
  const enKeys = collectKeys(en)
  const zhKeys = collectKeys(zh)

  it('en and zh have the same number of keys', () => {
    expect(enKeys.length).toBe(zhKeys.length)
  })

  it('en key set equals zh key set', () => {
    const enSet = new Set(enKeys)
    const zhSet = new Set(zhKeys)

    const onlyInEn = enKeys.filter((k) => !zhSet.has(k))
    const onlyInZh = zhKeys.filter((k) => !enSet.has(k))

    expect(onlyInEn).toEqual([])
    expect(onlyInZh).toEqual([])
  })

  it('no orphan keys (en has but zh does not)', () => {
    const zhSet = new Set(zhKeys)
    const orphans = enKeys.filter((k) => !zhSet.has(k))
    if (orphans.length > 0) {
      console.warn('Keys in EN missing from ZH:', orphans)
    }
    expect(orphans).toEqual([])
  })

  it('no orphan keys (zh has but en does not)', () => {
    const enSet = new Set(enKeys)
    const orphans = zhKeys.filter((k) => !enSet.has(k))
    if (orphans.length > 0) {
      console.warn('Keys in ZH missing from EN:', orphans)
    }
    expect(orphans).toEqual([])
  })
})
