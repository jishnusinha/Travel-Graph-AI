import { describe, expect, it } from 'vitest'
import { toggleCompareId } from './terra'

describe('compare tray', () => {
  it('keeps at most three ids and toggles membership', () => {
    expect(toggleCompareId(['a'], 'b')).toEqual(['a', 'b'])
    expect(toggleCompareId(['a', 'b', 'c'], 'd')).toEqual(['a', 'b', 'c'])
    expect(toggleCompareId(['a', 'b'], 'a')).toEqual(['b'])
  })
})
