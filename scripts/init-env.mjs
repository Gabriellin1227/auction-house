import { randomBytes } from 'node:crypto'
import { chmodSync, existsSync, readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const path = fileURLToPath(new URL('../.env', import.meta.url))
const example = fileURLToPath(new URL('../.env.example', import.meta.url))
let content = readFileSync(existsSync(path) ? path : example, 'utf8')
let changed = false
for (const name of ['AUTH_SECRET', 'AUDIT_SECRET']) {
  const pattern = new RegExp(`^${name}=(.*)$`, 'm')
  const match = content.match(pattern)
  if (!match || !match[1].trim()) {
    const line = `${name}=${randomBytes(48).toString('hex')}`
    content = match
      ? content.replace(pattern, line)
      : `${content.trimEnd()}\n${line}\n`
    changed = true
  }
}
if (changed) {
  writeFileSync(path, content, { mode: 0o600 })
  chmodSync(path, 0o600)
  console.log('.env preparado com chaves locais. Não inclua no Git.')
} else {
  console.log('.env já contém as chaves; configuração preservada.')
}
