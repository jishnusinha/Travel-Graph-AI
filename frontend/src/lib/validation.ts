import { z } from 'zod'

const EMAIL_RE = /^[^@\s]+@[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$/

/** Syntax-only email check; matches the backend (accepts reserved TLDs like .local). */
export const emailSchema = z
  .string()
  .trim()
  .min(1, 'Email is required')
  .regex(EMAIL_RE, 'Enter a valid email address')

export interface PasswordCheck {
  id: 'length' | 'case' | 'number' | 'symbol'
  label: string
  ok: boolean
}

export function passwordChecks(password: string): PasswordCheck[] {
  return [
    { id: 'length', label: 'At least 8 characters', ok: password.length >= 8 },
    { id: 'case', label: 'Upper & lowercase letters', ok: /[a-z]/.test(password) && /[A-Z]/.test(password) },
    { id: 'number', label: 'At least one number', ok: /\d/.test(password) },
    { id: 'symbol', label: 'At least one symbol', ok: /[^A-Za-z0-9]/.test(password) },
  ]
}

/** 0..4 strength score used by the strength meter. */
export function passwordStrength(password: string): { score: number; label: string } {
  if (!password) return { score: 0, label: '' }
  const score = passwordChecks(password).filter((c) => c.ok).length
  const label = ['', 'Weak', 'Fair', 'Good', 'Strong'][score] ?? ''
  return { score, label }
}

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Password is required'),
  remember_me: z.boolean(),
})
export type LoginForm = z.infer<typeof loginSchema>

const strongPassword = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .max(128, 'Password is too long')

export const signupSchema = z
  .object({
    full_name: z.string().trim().min(2, 'Enter your full name').max(200),
    email: emailSchema,
    password: strongPassword,
    confirm_password: z.string().min(1, 'Confirm your password'),
    terms: z.boolean().refine((v) => v, 'Please accept the terms to continue'),
  })
  .refine((d) => d.password === d.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match',
  })
export type SignupForm = z.infer<typeof signupSchema>

export const forgotSchema = z.object({ email: emailSchema })
export type ForgotForm = z.infer<typeof forgotSchema>

export const resetSchema = z
  .object({
    password: strongPassword,
    confirm_password: z.string().min(1, 'Confirm your password'),
  })
  .refine((d) => d.password === d.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match',
  })
export type ResetForm = z.infer<typeof resetSchema>

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, 'Enter your current password'),
    new_password: strongPassword,
    confirm_password: z.string().min(1, 'Confirm your new password'),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match',
  })
export type ChangePasswordForm = z.infer<typeof changePasswordSchema>

export const tripPromptSchema = z.object({
  prompt: z.string().trim().min(8, 'Describe your trip in at least 8 characters').max(2000),
  destination: z.string().trim().optional(),
  origin: z.string().trim().optional(),
  start_date: z.string().optional(),
  end_date: z.string().optional(),
  travelers: z.number().int().min(1, 'At least 1 traveler').max(20, 'Max 20 travelers'),
  budget_inr: z.number().int().min(1000, 'Budget must be at least ₹1,000'),
})
export type TripPromptForm = z.infer<typeof tripPromptSchema>

export function validateTripDates(start?: string, end?: string): string | null {
  if (start && end && end < start) return 'End date cannot be before start date'
  return null
}
