import { describe, expect, it } from 'vitest'
import {
  changePasswordSchema,
  loginSchema,
  passwordChecks,
  passwordStrength,
  resetSchema,
  signupSchema,
  tripPromptSchema,
  validateTripDates,
} from './validation'

describe('loginSchema', () => {
  it('accepts the demo account (reserved .local TLD)', () => {
    const r = loginSchema.safeParse({ email: 'demo@travelgraph.local', password: 'TravelGraphDemo!2026', remember_me: true })
    expect(r.success).toBe(true)
  })

  it('rejects empty and malformed email', () => {
    expect(loginSchema.safeParse({ email: '', password: 'x', remember_me: false }).success).toBe(false)
    const bad = loginSchema.safeParse({ email: 'not-an-email', password: 'x', remember_me: false })
    expect(bad.success).toBe(false)
    if (!bad.success) expect(bad.error.issues[0].message).toBe('Enter a valid email address')
  })

  it('requires a password', () => {
    const r = loginSchema.safeParse({ email: 'a@b.co', password: '', remember_me: true })
    expect(r.success).toBe(false)
  })
})

describe('signupSchema', () => {
  const ok = { full_name: 'Asha Rao', email: 'asha@example.com', password: 'Strong#Pass1', confirm_password: 'Strong#Pass1', terms: true }

  it('accepts valid input', () => {
    expect(signupSchema.safeParse(ok).success).toBe(true)
  })

  it('flags mismatched passwords on confirm_password', () => {
    const r = signupSchema.safeParse({ ...ok, confirm_password: 'different' })
    expect(r.success).toBe(false)
    if (!r.success) {
      const issue = r.error.issues.find((i) => i.path[0] === 'confirm_password')
      expect(issue?.message).toBe('Passwords do not match')
    }
  })

  it('requires 8+ character passwords, a name and accepted terms', () => {
    expect(signupSchema.safeParse({ ...ok, password: 'short', confirm_password: 'short' }).success).toBe(false)
    expect(signupSchema.safeParse({ ...ok, full_name: 'A' }).success).toBe(false)
    expect(signupSchema.safeParse({ ...ok, terms: false }).success).toBe(false)
  })
})

describe('reset / change password schemas', () => {
  it('reset requires matching passwords', () => {
    expect(resetSchema.safeParse({ password: 'Abcdef1!', confirm_password: 'Abcdef1!' }).success).toBe(true)
    expect(resetSchema.safeParse({ password: 'Abcdef1!', confirm_password: 'nope' }).success).toBe(false)
  })
  it('change password validates the new password', () => {
    expect(changePasswordSchema.safeParse({ current_password: 'old', new_password: 'abc', confirm_password: 'abc' }).success).toBe(false)
  })
})

describe('password strength', () => {
  it('scores each rule', () => {
    expect(passwordStrength('').score).toBe(0)
    expect(passwordStrength('abc').score).toBe(0)
    expect(passwordStrength('abcdefgh').score).toBe(1)
    expect(passwordStrength('Abcdefgh').score).toBe(2)
    expect(passwordStrength('Abcdefg1').score).toBe(3)
    expect(passwordStrength('Abcdef1!').score).toBe(4)
    expect(passwordStrength('Abcdef1!').label).toBe('Strong')
  })
  it('reports which checks pass', () => {
    const checks = Object.fromEntries(passwordChecks('Abcdefg1').map((c) => [c.id, c.ok]))
    expect(checks).toEqual({ length: true, case: true, number: true, symbol: false })
  })
})

describe('trip prompt + dates', () => {
  it('requires a meaningful prompt and valid budget', () => {
    expect(tripPromptSchema.safeParse({ prompt: 'short', travelers: 2, budget_inr: 35000 }).success).toBe(false)
    expect(tripPromptSchema.safeParse({ prompt: 'Plan a 5-day Goa trip', travelers: 0, budget_inr: 35000 }).success).toBe(false)
    expect(tripPromptSchema.safeParse({ prompt: 'Plan a 5-day Goa trip', travelers: 2, budget_inr: 500 }).success).toBe(false)
    expect(tripPromptSchema.safeParse({ prompt: 'Plan a 5-day Goa trip', travelers: 2, budget_inr: 35000 }).success).toBe(true)
  })
  it('rejects end before start', () => {
    expect(validateTripDates('2027-01-16', '2027-01-12')).toMatch(/cannot be before/)
    expect(validateTripDates('2027-01-12', '2027-01-16')).toBeNull()
    expect(validateTripDates(undefined, '2027-01-16')).toBeNull()
  })
})
