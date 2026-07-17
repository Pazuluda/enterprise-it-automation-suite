async function copyText(value) {
  const text = String(value ?? '')

  if (navigator?.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // Fallback below
    }
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '0'
  document.body.appendChild(textarea)

  textarea.focus()
  textarea.select()
  textarea.setSelectionRange(0, textarea.value.length)

  try {
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)

    if (!ok) {
      throw new Error('Copie refusée par le navigateur')
    }

    return true
  } catch (err) {
    document.body.removeChild(textarea)
    throw err
  }
}

export {
  copyText,
}
