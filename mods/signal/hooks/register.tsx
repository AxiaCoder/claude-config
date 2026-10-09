import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

const NOTE_TOOL = 'mcp__signal__note'
const MAX_NOTE_LENGTH = 100
const PREFIX = '💡 '

const RULE_SECTION = {
  id: 'signal:rule',
  text: "While the signal mod is loaded, use `note` for what deserves the user's eye without calling for an answer: it shows one line above the prompt until the user's next prompt. A question is asked in your message, never in a note.",
  scope: 'session',
} as const

const note = atom({ plugin: 'signal', key: 'note' } as const, null)

/**
 * Checks a `note` input against the rules the model is held to.
 *
 * @param text the note as the model sent it, already trimmed when a string
 * @returns the refusal the model reads, or undefined when the input is accepted
 */
const refuseNote = (text: unknown): string | undefined => {
  if (typeof text !== 'string' || text === '') {
    return 'note: `text` must be a non-empty string.'
  }
  if (/[\r\n]/.test(text)) {
    return 'note: `text` must fit on one line. Rephrase it as one short line.'
  }
  if (text.length > MAX_NOTE_LENGTH) {
    return `note: \`text\` is ${text.length} characters, the limit is ${MAX_NOTE_LENGTH}. Rephrase it shorter.`
  }

  return undefined
}

/**
 * Registers the `note` tool, its rule, the band above the prompt, and the
 * hooks that clear the note at the next prompt and at session end.
 *
 * @param on the plugin's registrar
 */
export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.tool.register({
      name: 'note',
      description:
        "Shows a one-line note above the prompt, visible until the user's next prompt, for what deserves the user's eye without calling for an answer. A question belongs in your message, never in a note. `text`: one line, at most 100 characters. A new note replaces the current one.",
      inputSchema: {
        type: 'object',
        properties: {
          text: { type: 'string', description: 'The note, one line, at most 100 characters.' },
        },
        required: ['text'],
      },
      isDeferred: false,
    })

    return next(e)
  })

  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    if (!e.tools.includes(NOTE_TOOL)) {
      return composed
    }

    return { sections: [...composed.sections, RULE_SECTION] }
  })

  on('session.end', async ($, e, next) => {
    await update($, note, () => null)

    return next(e)
  })

  on('tool.call', { tool: NOTE_TOOL }, async ($, e) => {
    const { text: raw } = e as unknown as { text?: unknown }
    const text = typeof raw === 'string' ? raw.trim() : raw
    const refusal = refuseNote(text)
    if (refusal !== undefined) {
      return { deny: refusal }
    }

    await update($, note, () => String(text))

    return { result: 'Note shown above the prompt.' }
  }).catch(() => ({ deny: 'note: the note could not be shown.' }))

  on('prompt.submit', async ($, e, next) => {
    const sent = await next(e)
    if (sent.drop === undefined) {
      await update($, note, () => null)
    }

    return sent
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const shown = await read($, note)
    if (e.props.hasSurvey || shown === null) {
      return next(e)
    }

    const { Box, Text } = $.ui.resolve(e)
    const below = await next(e)

    return (
      <Box key="signal-band" flexDirection="column">
        <Text key="note" wrap="truncate-end">
          {PREFIX}
          {shown}
        </Text>
        {below}
      </Box>
    )
  })
}
