import { useEffect, useRef, type ReactNode } from 'react'

export default function Dialog({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current!
    dialog.showModal()
    return () => dialog.close()
  }, [])
  return (
    <dialog ref={ref} className="dialog" aria-label={title} onCancel={onClose}>
      <div className="dialog__heading">
        <h2>{title}</h2>
        <button type="button" aria-label="Fechar janela" onClick={onClose}>
          ×
        </button>
      </div>
      {children}
    </dialog>
  )
}
