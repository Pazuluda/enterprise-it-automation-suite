export const AD_LOGON_HOURS_CLEAR_VALUE =
  '__EITAS_CLEAR_LOGON_HOURS__'

export const AD_LOGON_DAY_LABELS = [
  'Dimanche',
  'Lundi',
  'Mardi',
  'Mercredi',
  'Jeudi',
  'Vendredi',
  'Samedi',
]

export const AD_LOGON_HOURS_PER_DAY = 24
export const AD_LOGON_TOTAL_HOURS = 168
export const AD_LOGON_BYTE_COUNT = 21

function positiveModulo(value, divisor) {
  return ((value % divisor) + divisor) % divisor
}

export function getLogonHoursSubmissionValue(
  value
) {
  return value === AD_LOGON_HOURS_CLEAR_VALUE
    ? ''
    : value
}

export function normalizeLogonHoursHex(value) {
  if (
    value === undefined ||
    value === null ||
    value === ''
  ) {
    return ''
  }

  let tokens

  if (
    Array.isArray(value) ||
    ArrayBuffer.isView(value)
  ) {
    tokens = Array.from(value).map(item =>
      Number(item).toString(16).padStart(2, '0')
    )
  } else {
    tokens = String(value)
      .trim()
      .split(/[\s,;]+/)
      .filter(Boolean)
  }

  if (
    tokens.length !== AD_LOGON_BYTE_COUNT ||
    tokens.some(token =>
      !/^[0-9a-f]{2}$/i.test(String(token))
    )
  ) {
    return ''
  }

  return tokens
    .map(token => String(token).toUpperCase())
    .join(' ')
}

export function parseLogonHoursHex(value) {
  const normalized =
    normalizeLogonHoursHex(value)

  if (!normalized) {
    return new Uint8Array(
      AD_LOGON_BYTE_COUNT
    )
  }

  return Uint8Array.from(
    normalized
      .split(' ')
      .map(token => Number.parseInt(token, 16))
  )
}

export function serializeLogonHoursBytes(value) {
  const bytes = Array.from(value || [])

  if (bytes.length !== AD_LOGON_BYTE_COUNT) {
    throw new Error(
      'logonHours doit contenir 21 octets.'
    )
  }

  return bytes
    .map(byte =>
      Number(byte)
        .toString(16)
        .padStart(2, '0')
        .toUpperCase()
    )
    .join(' ')
}

export function createAllAllowedLogonHoursHex() {
  return Array(
    AD_LOGON_BYTE_COUNT
  ).fill('FF').join(' ')
}

export function createAllDeniedLogonHoursHex() {
  return Array(
    AD_LOGON_BYTE_COUNT
  ).fill('00').join(' ')
}

export function getLogonHoursOffsetHours(
  utcOffsetMinutes
) {
  const numericOffset = Number(
    utcOffsetMinutes
  )

  if (!Number.isFinite(numericOffset)) {
    return 0
  }

  return Math.trunc(numericOffset / 60)
}

export function getUtcLogonHourIndex(
  localHourIndex,
  utcOffsetMinutes
) {
  const offsetHours =
    getLogonHoursOffsetHours(
      utcOffsetMinutes
    )

  return positiveModulo(
    Number(localHourIndex) - offsetHours,
    AD_LOGON_TOTAL_HOURS
  )
}

export function isLocalLogonHourAllowed(
  value,
  localHourIndex,
  utcOffsetMinutes
) {
  const normalized =
    normalizeLogonHoursHex(value)

  if (!normalized) {
    return true
  }

  const bytes = parseLogonHoursHex(
    normalized
  )

  const utcIndex = getUtcLogonHourIndex(
    localHourIndex,
    utcOffsetMinutes
  )

  const byteIndex = Math.floor(
    utcIndex / 8
  )
  const bitIndex = utcIndex % 8

  return (
    (bytes[byteIndex] & (1 << bitIndex)) !== 0
  )
}

export function toggleLocalLogonHour(
  value,
  localHourIndex,
  utcOffsetMinutes
) {
  const normalized =
    normalizeLogonHoursHex(value)

  const bytes = normalized
    ? parseLogonHoursHex(normalized)
    : new Uint8Array(
        AD_LOGON_BYTE_COUNT
      ).fill(0xff)

  const utcIndex = getUtcLogonHourIndex(
    localHourIndex,
    utcOffsetMinutes
  )

  const byteIndex = Math.floor(
    utcIndex / 8
  )
  const bitIndex = utcIndex % 8

  bytes[byteIndex] ^= (1 << bitIndex)

  return serializeLogonHoursBytes(bytes)
}

export function countAllowedLocalLogonHours(
  value
) {
  const normalized =
    normalizeLogonHoursHex(value)

  if (!normalized) {
    return AD_LOGON_TOTAL_HOURS
  }

  return Array.from(
    parseLogonHoursHex(normalized)
  ).reduce((total, byte) => {
    let remaining = byte
    let count = 0

    while (remaining) {
      count += remaining & 1
      remaining >>= 1
    }

    return total + count
  }, 0)
}

export function formatLogonHoursOffset(
  utcOffsetMinutes
) {
  const numericOffset = Number(
    utcOffsetMinutes
  )

  if (!Number.isFinite(numericOffset)) {
    return 'UTC'
  }

  const sign = numericOffset >= 0
    ? '+'
    : '-'

  const absoluteMinutes = Math.abs(
    numericOffset
  )

  const hours = Math.floor(
    absoluteMinutes / 60
  )

  const minutes = absoluteMinutes % 60

  return minutes
    ? `UTC${sign}${hours}:${String(minutes).padStart(2, '0')}`
    : `UTC${sign}${hours}`
}
