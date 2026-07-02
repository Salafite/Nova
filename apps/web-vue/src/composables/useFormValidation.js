import { ref, computed } from 'vue'

export function useFormValidation(rules) {
  const errors = ref({})
  const touched = ref({})

  const hasErrors = computed(() => Object.keys(errors.value).length > 0)
  const anyTouched = computed(() => Object.keys(touched.value).length > 0)

  function validate(field, value) {
    if (!rules[field]) return ''
    for (const rule of rules[field]) {
      const err = rule(value)
      if (err) {
        errors.value[field] = err
        return err
      }
    }
    delete errors.value[field]
    return ''
  }

  function touch(field) {
    touched.value[field] = true
  }

  function validateAll(form) {
    errors.value = {}
    touched.value = {}
    for (const field of Object.keys(rules)) {
      touch(field)
      validate(field, form[field])
    }
    return !hasErrors.value
  }

  function clearField(field) {
    delete errors.value[field]
    delete touched.value[field]
  }

  function reset() {
    errors.value = {}
    touched.value = {}
  }

  return { errors, touched, hasErrors, anyTouched, validate, touch, validateAll, clearField, reset }
}

export const required = (msg) => (v) => (v === null || v === undefined || v === '' ? msg || 'This field is required' : '')

export const minLength = (min, msg) => (v) => (v && v.length < min ? msg || `Minimum ${min} characters` : '')

export const maxLength = (max, msg) => (v) => (v && v.length > max ? msg || `Maximum ${max} characters` : '')

export const isNumeric = (msg) => (v) => (v !== '' && v !== null && isNaN(Number(v)) ? msg || 'Must be a number' : '')

export const minValue = (min, msg) => (v) => (v !== '' && v !== null && Number(v) < min ? msg || `Minimum value is ${min}` : '')

export const isEmail = (msg) => (v) => (v && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) ? msg || 'Invalid email' : '')

export const isPhone = (msg) => (v) => (v && !/^[\d\s+\-()]{7,20}$/.test(v) ? msg || 'Invalid phone number' : '')
