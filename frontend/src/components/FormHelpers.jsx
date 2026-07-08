export function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  )
}

export function PreviewRow({ label, value }) {
  return (
    <div className="preview-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
