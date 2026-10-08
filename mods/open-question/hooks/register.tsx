import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { OpenQuestion } from '../types'

const PANE = 'open-question'
const PIN_TOOL = 'mcp__open-question__pin_question'
const UNPIN_TOOL = 'mcp__open-question__unpin_question'
const MAX_QUESTION_LENGTH = 100
const MAX_OPEN_QUESTIONS = 3
const ELLIPSIS = '…'
const PREFIX = '❓ '
const PREFIX_CELLS = 3
const GAP = '   '
const FRAME_CELLS = 4
const FRAME_TITLE = 'En attente de ta réponse'
const DETAILS_LABEL = 'détails'
const REMOVE_LABEL = 'x'

const questions = atom({ plugin: 'open-question', key: 'questions' } as const, [])
const nextId = atom({ plugin: 'open-question', key: 'nextId' } as const, 1)
const shownId = atom({ plugin: 'open-question', key: 'shownId' } as const, null)

/**
 * Cells the terminal takes to draw a Button labelled `label`: `[ label ]`.
 *
 * @param label the Button's label
 * @returns its width in cells
 */
const buttonCells = (label: string): number => label.length + 4

/**
 * Cuts `text` to at most `cells` characters, ending it with an ellipsis when cut.
 *
 * @param text the question to fit
 * @param cells the room left on the line, in cells; below 1, the ellipsis alone
 * @returns `text` whole when it fits, else its head and `…`
 */
const fitToCells = (text: string, cells: number): string => {
  if (text.length <= cells) {
    return text
  }

  return text.slice(0, Math.max(0, cells - 1)).trimEnd() + ELLIPSIS
}

/**
 * Checks a `pin_question` input against the rules the model is held to.
 *
 * @param question the question as the model sent it
 * @param openCount how many questions are pinned already
 * @returns the refusal the model reads, or undefined when the input is accepted
 */
const refusePin = (question: unknown, openCount: number): string | undefined => {
  if (typeof question !== 'string' || question.trim() === '') {
    return 'pin_question: `question` must be a non-empty string.'
  }
  if (/[\r\n]/.test(question)) {
    return 'pin_question: `question` must fit on one line. Rephrase it as one short line and put the detail in `context`.'
  }
  if (question.length > MAX_QUESTION_LENGTH) {
    return `pin_question: \`question\` is ${question.length} characters, the limit is ${MAX_QUESTION_LENGTH}. Rephrase it shorter and put the detail in \`context\`.`
  }
  if (openCount >= MAX_OPEN_QUESTIONS) {
    return `pin_question: ${MAX_OPEN_QUESTIONS} questions are already pinned. Settle or unpin one before pinning another.`
  }

  return undefined
}

/**
 * Removes a pinned question, and closes the details pane when it shows that one.
 *
 * @param $ the engine interface of the calling hook
 * @param id the question's id
 * @returns true when a question was removed, false when no pinned question has that id
 */
const removeQuestion = async ($: EngineInterface, id: string): Promise<boolean> => {
  let isFound = false
  await update($, questions, list => {
    isFound = list.some(one => one.id === id)

    return list.filter(one => one.id !== id)
  })
  if (isFound && (await read($, shownId)) === id) {
    await update($, shownId, () => null)
    await $.ui.close({ id: PANE })
  }

  return isFound
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.tool.register({
      name: 'pin_question',
      description:
        'Pins a question that awaits the user\'s answer above the prompt, so it stays visible while you keep working. Use it for a question you asked the user that does not block your current work. `question`: one line, at most 100 characters. `context`: optional Markdown the user can open for details. At most 3 pinned at once. Returns the question\'s id.',
      inputSchema: {
        type: 'object',
        properties: {
          question: { type: 'string', description: 'The question, one line, at most 100 characters.' },
          context: { type: 'string', description: 'Optional Markdown context shown in a details pane.' },
        },
        required: ['question'],
      },
      isDeferred: false,
    })
    await $.tool.register({
      name: 'unpin_question',
      description:
        'Removes a pinned question by its id. Call it once the user\'s answer settles the question; if the answer misses the question, leave it pinned.',
      inputSchema: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'The id pin_question returned.' },
        },
        required: ['id'],
      },
      isDeferred: false,
    })

    return next(e)
  })

  on('session.end', async ($, e, next) => {
    if (e.reason === 'clear') {
      await update($, questions, () => [])
      await update($, shownId, () => null)
      await $.ui.close({ id: PANE })
    }

    return next(e)
  })

  on('tool.call', { tool: PIN_TOOL }, async ($, e) => {
    const input = e as unknown as { question?: unknown; context?: unknown }
    const refusal = refusePin(input.question, (await read($, questions)).length)
    if (refusal !== undefined) {
      return { deny: refusal }
    }
    if (input.context !== undefined && typeof input.context !== 'string') {
      return { deny: 'pin_question: `context` must be a string of Markdown.' }
    }

    let id = ''
    await update($, nextId, n => {
      id = `q${n}`

      return n + 1
    })
    const pinned: OpenQuestion = { id, question: String(input.question) }
    if (typeof input.context === 'string' && input.context.trim() !== '') {
      pinned.context = input.context
    }
    let isFull = false
    await update($, questions, list => {
      isFull = list.length >= MAX_OPEN_QUESTIONS

      return isFull ? list : [...list, pinned]
    })
    if (isFull) {
      return { deny: refusePin(pinned.question, MAX_OPEN_QUESTIONS) ?? 'pin_question: refused.' }
    }

    return { result: id }
  }).catch(() => ({ deny: 'pin_question: the question could not be pinned.' }))

  on('tool.call', { tool: UNPIN_TOOL }, async ($, e) => {
    const { id } = e as unknown as { id?: unknown }
    if (typeof id !== 'string' || !(await removeQuestion($, id))) {
      return { deny: `unpin_question: no pinned question has the id ${JSON.stringify(id)}.` }
    }

    return { result: `Unpinned ${id}.` }
  }).catch(() => ({ deny: 'unpin_question: the question could not be unpinned.' }))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const list = await read($, questions)
    if (e.props.hasSurvey || list.length === 0) {
      return next(e)
    }

    const { Box, Button, Text } = $.ui.resolve(e)
    const columns = e.props.bodyColumns - FRAME_CELLS

    return (
      <Box key="frame" flexDirection="column" borderStyle="round" borderColor="claude" paddingX={1}>
        <Text bold color="claude">
          {FRAME_TITLE}
        </Text>
        {list.map(one => {
          const buttons = (one.context ? buttonCells(DETAILS_LABEL) + 1 : 0) + buttonCells(REMOVE_LABEL)
          const room = columns - PREFIX_CELLS - GAP.length - buttons

          return (
            <Box key={`row:${one.id}`} flexDirection="row">
              <Text wrap="truncate-end">
                {PREFIX}
                {fitToCells(one.question, room)}
                {GAP}
              </Text>
              {one.context && (
                <Button
                  key={`details:${one.id}`}
                  label={DETAILS_LABEL}
                  onPress={async () => {
                    await update($, shownId, () => one.id)
                    await $.ui.open({ id: PANE, title: one.question })
                  }}
                />
              )}
              {one.context && <Text> </Text>}
              <Button
                key={`remove:${one.id}`}
                label={REMOVE_LABEL}
                onPress={async () => {
                  await removeQuestion($, one.id)
                }}
              />
            </Box>
          )
        })}
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Markdown, Text } = $.ui.resolve(e)
    const id = await read($, shownId)
    const shown = (await read($, questions)).find(one => one.id === id)

    if (shown?.context === undefined) {
      return <Text dimColor>No question to show.</Text>
    }

    return <Markdown key="context" text={shown.context} />
  })
}
