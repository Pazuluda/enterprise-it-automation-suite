import { useState } from 'react'

export default function CopyTextButton({ text, label = 'Copier', copiedLabel = 'Copié' }) {
  const [copied, setCopied] = useState(false)

  async function copyText() {
    const value = String(text || '')

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(value)
      } else {
        const textarea = document.createElement('textarea')
        textarea.value = value
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.focus()
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }

      setCopied(true)

      window.setTimeout(() => {
        setCopied(false)
      }, 1400)
    } catch (error) {
      window.alert(`Copie impossible : ${error.message}`)
    }
  }

  return (
    <button
      type="button"
      className={copied ? 'copy-button copied' : 'copy-button'}
      onClick={copyText}
    >
      {copied ? copiedLabel : label}
    </button>
  )
}
