export default function PanelHeader({ title, subtitle, action }) {
  return (
    <div className="panel-header">
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
