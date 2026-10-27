import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
const local = fileURLToPath(new URL('../.tools/bin/uv', import.meta.url))
const command = existsSync(local) ? local : 'uv'
const result = spawnSync(command, process.argv.slice(2), { stdio: 'inherit' })
if (result.error)
  console.error(
    'Instale uv e execute npm run setup:backend. Consulte o README.',
  )
process.exit(result.status ?? 1)
