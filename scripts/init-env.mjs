import { randomBytes } from 'node:crypto'
import { chmodSync, existsSync, readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const path = fileURLToPath(new URL('../.env', import.meta.url))
const example = fileURLToPath(new URL('../.env.example', import.meta.url))
let content = readFileSync(existsSync(path) ? path : example, 'utf8')
const match = content.match(/^AUTH_SECRET=(.*)$/m)
if (!match || !match[1].trim()) {
  const line = `AUTH_SECRET=${randomBytes(48).toString('hex')}`
  content = match
    ? content.replace(/^AUTH_SECRET=.*$/m, line)
    : `${content.trimEnd()}\n${line}\n`
  writeFileSync(path, content, { mode: 0o600 })
  chmodSync(path, 0o600)
  console.log(
    '.env preparado com chave de autenticação local. Não inclua no Git.',
  )
} else {
  console.log('.env já contém AUTH_SECRET; configuração preservada.')
}
