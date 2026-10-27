interface SectionTitleProps {
  eyebrow?: string
  title: string
}

export default function SectionTitle({ eyebrow, title }: SectionTitleProps) {
  return (
    <div className="section-title">
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h2>{title}</h2>
    </div>
  )
}
