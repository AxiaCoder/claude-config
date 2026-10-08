import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { AskedQuestion, OpenQuestion } from '../types'

const PANE = 'open-question'
const PIN_TOOL = 'mcp__open-question__pin_question'
const UNPIN_TOOL = 'mcp__open-question__unpin_question'
const MAX_QUESTION_LENGTH = 100
const MAX_OPEN_QUESTIONS = 1
const MAX_HISTORY = 100
const ELLIPSIS = '…'
const PREFIX = '❓ '
const PREFIX_CELLS = 3
const GAP = '   '
const FRAME_CELLS = 4
const FRAME_TITLE = 'En attente de ta réponse'
const DETAILS_LABEL = 'détails'
const REMOVE_LABEL = 'x'
const ANSWER_LABEL = 'répondre'
const MIN_OPTIONS = 2
const MAX_OPTIONS = 4
const MAX_OPTION_LENGTH = 30

const questions = atom({ plugin: 'open-question', key: 'questions' } as const, [])
const nextId = atom({ plugin: 'open-question', key: 'nextId' } as const, 1)
const shownId = atom({ plugin: 'open-question', key: 'shownId' } as const, null)
const asked = atom({ plugin: 'open-question', key: 'asked' } as const, [])

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
    return 'pin_question: A question is already pinned: ask this one in your message, or unpin the open one first.'
  }

  return undefined
}

/**
 * Checks the `options` of a `pin_question` input.
 *
 * @param options the options as the model sent them; undefined for an open question
 * @returns the refusal the model reads, or undefined when they are accepted
 */
const refuseOptions = (options: unknown): string | undefined => {
  if (options === undefined) {
    return undefined
  }
  if (!Array.isArray(options) || options.length < MIN_OPTIONS || options.length > MAX_OPTIONS) {
    return `pin_question: \`options\` takes ${MIN_OPTIONS} to ${MAX_OPTIONS} choices. Rephrase the question, or put the detail in \`context\`.`
  }
  for (const option of options) {
    if (typeof option !== 'string' || option.trim() === '') {
      return 'pin_question: each option must be a non-empty string.'
    }
    if (/[\r\n]/.test(option) || option.length > MAX_OPTION_LENGTH) {
      return `pin_question: each option fits on one line, at most ${MAX_OPTION_LENGTH} characters; ${JSON.stringify(option)} does not. Rephrase it shorter, or put the detail in \`context\`.`
    }
  }

  return undefined
}

/**
 * The words that open the user's answer to a question, up to the colon.
 *
 * @param question the question as pinned
 * @returns `Réponse à « <question> » :`
 */
const answerTag = (question: string): string => `Réponse à « ${question} » :`

/**
 * Removes from a draft the answer opening of any question pinned this session,
 * and the option it carried, so a press relabels the draft instead of stacking.
 *
 * The longest matching tag wins, then the longest matching option.
 *
 * @param draft the prompt box's text
 * @param history every question pinned this session
 * @returns what the person typed beside the answer opening
 */
const stripAnswer = (draft: string, history: readonly AskedQuestion[]): string => {
  const matching = history.filter(one => draft.startsWith(answerTag(one.question)))
  if (matching.length === 0) {
    return draft
  }

  const question = matching.reduce((longest, one) => (one.question.length > longest.length ? one.question : longest), '')
  const rest = draft.slice(answerTag(question).length).trimStart()
  const option = matching
    .filter(one => one.question === question)
    .flatMap(one => one.options ?? [])
    .filter(choice => rest === choice || rest.startsWith(`${choice} `))
    .reduce((longest, choice) => (choice.length > longest.length ? choice : longest), '')

  return rest.slice(option.length).trimStart()
}

/**
 * Puts the answer to `one` in the prompt box, the draft already typed kept after it.
 *
 * @param $ the engine interface of the pressing hook
 * @param one the question answered
 * @param option the option pressed; undefined for a free answer
 */
const fillAnswer = async ($: EngineInterface, one: OpenQuestion, option?: string): Promise<void> => {
  const draft = stripAnswer((await $.prompt.read()).text, await read($, asked))
  const head = option === undefined ? `${answerTag(one.question)} ` : `${answerTag(one.question)} ${option}`
  const separator = option === undefined || draft === '' ? '' : ' '
  await $.prompt.fill({ text: head + separator + draft, mode: 'replace' })
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
        'Pins a question that awaits the user\'s answer above the prompt, so it stays visible while you keep working. Use it for any question that awaits the user\'s answer; pinning never blocks your work. `question`: one line, at most 100 characters. `context`: optional Markdown the user can open for details. `options`: 2 to 4 choices, one line and at most 30 characters each, for a multiple-choice question; leave it out for an open question. An answer given through the bar arrives as `Réponse à « <question> » : …` and unpins the question by itself. At most one pinned at once. Returns the question\'s id.',
      inputSchema: {
        type: 'object',
        properties: {
          question: { type: 'string', description: 'The question, one line, at most 100 characters.' },
          context: { type: 'string', description: 'Optional Markdown context shown in a details pane.' },
          options: {
            type: 'array',
            items: { type: 'string' },
            minItems: MIN_OPTIONS,
            maxItems: MAX_OPTIONS,
            description: 'Optional choices for a multiple-choice question, one line and at most 30 characters each.',
          },
        },
        required: ['question'],
      },
      isDeferred: false,
    })
    await $.tool.register({
      name: 'unpin_question',
      description:
        'Removes a pinned question by its id. Call it when an answer typed directly (not through the bar) settles the question; an answer through the bar has already unpinned it; an answer that misses the question leaves it pinned.',
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
    await update($, questions, () => [])
    await update($, shownId, () => null)
    await update($, asked, () => [])
    await $.ui.close({ id: PANE })

    return next(e)
  })

  on('tool.call', { tool: PIN_TOOL }, async ($, e) => {
    const raw = e as unknown as { question?: unknown; context?: unknown; options?: unknown }
    const trim = (value: unknown): unknown => (typeof value === 'string' ? value.trim() : value)
    const input = {
      question: trim(raw.question),
      context: raw.context,
      options: Array.isArray(raw.options) ? raw.options.map(trim) : raw.options,
    }
    const refusal = refusePin(input.question, (await read($, questions)).length) ?? refuseOptions(input.options)
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
    if (Array.isArray(input.options)) {
      pinned.options = input.options.map(String)
    }
    let isFull = false
    await update($, questions, list => {
      isFull = list.length >= MAX_OPEN_QUESTIONS

      return isFull ? list : [...list, pinned]
    })
    if (isFull) {
      return { deny: refusePin(pinned.question, MAX_OPEN_QUESTIONS) ?? 'pin_question: refused.' }
    }
    const record: AskedQuestion = pinned.options ? { question: pinned.question, options: pinned.options } : { question: pinned.question }
    await update($, asked, history => [...history, record].slice(-MAX_HISTORY))

    return { result: id }
  }).catch(() => ({ deny: 'pin_question: the question could not be pinned.' }))

  on('tool.call', { tool: UNPIN_TOOL }, async ($, e) => {
    const { id } = e as unknown as { id?: unknown }
    if (typeof id !== 'string' || !(await removeQuestion($, id))) {
      return { deny: `unpin_question: no pinned question has the id ${JSON.stringify(id)}.` }
    }

    return { result: `Unpinned ${id}.` }
  }).catch(() => ({ deny: 'unpin_question: the question could not be unpinned.' }))

  on('prompt.submit', async ($, e, next) => {
    const sent = await next(e)
    if (sent.drop !== undefined) {
      return sent
    }
    const answered = (await read($, questions)).find(one => e.text.startsWith(answerTag(one.question)))
    if (answered !== undefined) {
      await removeQuestion($, answered.id)
    }

    return sent
  }).catch(($, e, next) => next(e))

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
            <Box key={`question:${one.id}`} flexDirection="column">
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
              <Box
                key={`answers:${one.id}`}
                flexDirection="row"
                flexWrap="wrap"
                columnGap={1}
                marginLeft={PREFIX_CELLS}
              >
                {(one.options ?? []).map((option, index) => (
                  <Button key={`option:${one.id}:${index}`} label={option} onPress={() => fillAnswer($, one, option)} />
                ))}
                <Button key={`answer:${one.id}`} label={ANSWER_LABEL} onPress={() => fillAnswer($, one)} />
              </Box>
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
