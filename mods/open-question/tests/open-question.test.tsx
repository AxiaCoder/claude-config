import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

const PIN = 'mcp__open-question__pin_question'
const UNPIN = 'mcp__open-question__unpin_question'
const SURFACES = ['terminal', 'desktop'] as const

const BAND_PROPS = {
  hasSurvey: false,
  isWorking: false,
  maxRows: 10,
  bodyColumns: 60,
  scroll: { offset: 0, bodyRows: 10 },
  view: {},
}

const PANE_PROPS = {
  title: 'Question',
  isFocused: false,
  bodyColumns: 60,
  placement: 'inline' as const,
  scroll: { offset: 0, bodyRows: 10 },
  view: {},
}

/**
 * Stands for the engine beneath the plugin: draws an empty band, answers pane
 * opens and closes, and records them.
 *
 * @param on the test's registrar
 * @returns the panes opened (by title) and closed (by id), in order
 */
const standInForPanes = (on: On) => {
  const opened: string[] = []
  const closed: string[] = []
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Box } = $.ui.resolve(e)

    return <Box key="engine-band" />
  })
  on('ui.open', ($, e) => {
    opened.push(e.title ?? e.id)

    return { value: { isPlaced: true } }
  })
  on('ui.close', ($, e) => {
    closed.push(e.id)

    return { value: undefined }
  })

  return { opened, closed }
}

/**
 * Calls one of the mod's tools as the model would.
 *
 * @param $ the test's engine
 * @param tool the tool's full name
 * @param input the tool's arguments
 * @returns what the call resolved to
 */
const call = ($: Engine, tool: typeof PIN | typeof UNPIN, input: Record<string, unknown>) =>
  $.tool.call({ tool, ...input }) as Promise<{ deny?: string; result?: unknown }>

/**
 * Pins a question and returns its id, failing the test when refused.
 *
 * @param $ the test's engine
 * @param question the question
 * @param context its optional Markdown
 * @returns the id the tool answered
 */
const pin = async ($: Engine, question: string, context?: string): Promise<string> => {
  const answer = await call($, PIN, context === undefined ? { question } : { question, context })
  expect(answer.deny).toBeUndefined()

  expect(typeof answer.result).toBe('string')

  return answer.result as string
}

describe('pin_question', () => {
  test('refuses a question over 100 characters', async ($, on) => {
    standInForPanes(on)
    const answer = await call($, PIN, { question: 'a'.repeat(101) })
    expect(answer.deny).toMatch(/shorter/)
    expect((await call($, PIN, { question: 'a'.repeat(100) })).deny).toBeUndefined()
  })

  test('refuses a question on several lines', async ($, on) => {
    standInForPanes(on)
    const answer = await call($, PIN, { question: 'First line?\nSecond line?' })
    expect(answer.deny).toMatch(/one line/)
  })

  test('refuses a second open question', async ($, on) => {
    standInForPanes(on)
    await pin($, 'One?')
    const answer = await call($, PIN, { question: 'Two?' })
    expect(answer.deny).toBe(
      'pin_question: A question is already pinned: ask this one in your message, or unpin the open one first.',
    )
  })
})

describe('unpin_question', () => {
  test('removes the question from the band', async ($, on) => {
    standInForPanes(on)
    const id = await pin($, 'Keep the old route?')
    expect((await call($, UNPIN, { id })).deny).toBeUndefined()
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect(await ui.find({ text: /Keep the old route/ })).toBeUndefined()
      await ui.unmount()
    }
  })

  test('answers a string, the only result shape a registered tool takes', async ($, on) => {
    standInForPanes(on)
    const id = await pin($, 'Merge now?')
    expect(id).toMatch(/^q\d+$/)
    const answer = await call($, UNPIN, { id })
    expect(answer.result).toBe(`Unpinned ${id}.`)
  })

  test('refuses an unknown id', async ($, on) => {
    standInForPanes(on)
    expect((await call($, UNPIN, { id: 'q42' })).deny).toMatch(/no pinned question/)
  })
})

describe('band', () => {
  test('draws nothing without a question', async ($, on) => {
    standInForPanes(on)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect(await ui.findAll({ type: 'Button' })).toHaveLength(0)
      expect(await ui.find({ type: 'Text', text: /❓/ })).toBeUndefined()
      expect(await ui.find({ key: 'engine-band' })).toBeDefined()
      await ui.unmount()
    }
  })

  test('draws the question, details only with a context', async ($, on) => {
    standInForPanes(on)
    for (const surface of SURFACES) {
      const bare = await pin($, 'Rename the table?')
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect((await ui.find({ type: 'Text', text: /Rename the table/ }))?.text).toContain('❓ Rename the table?')
      expect(await ui.find({ key: `details:${bare}` })).toBeUndefined()
      expect(await ui.find({ key: `remove:${bare}` })).toBeDefined()
      await ui.press({ key: `remove:${bare}` })

      const rich = await pin($, 'Which cache?', '## Options\n\n- Redis\n- in memory')
      expect(await ui.find({ key: `details:${rich}` })).toBeDefined()
      expect(await ui.find({ key: `remove:${rich}` })).toBeDefined()
      await ui.press({ key: `remove:${rich}` })
      await ui.unmount()
    }
  })

  test('cuts a long question to the band width', async ($, on) => {
    standInForPanes(on)
    const question = 'b'.repeat(100)
    const id = await pin($, question, 'More.')
    const props = { ...BAND_PROPS, bodyColumns: 50 }
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props })
      const shown = (await ui.find({ type: 'Text', text: /❓/ }))?.text ?? ''
      expect(shown).toContain('…')
      expect(4 + shown.length + 1 + '[ détails ]'.length + 1 + '[ x ]'.length).toBeLessThanOrEqual(50)
      await ui.unmount()
    }
  })

  test('frames the questions under a title, only while one is open', async ($, on) => {
    standInForPanes(on)
    for (const surface of SURFACES) {
      const empty = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect(await empty.find({ type: 'Text', text: 'En attente de ta réponse' })).toBeUndefined()
      expect(await empty.find({ key: 'frame' })).toBeUndefined()
      await empty.unmount()

      const id = await pin($, `Ready on ${surface}?`)
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      const frame = await ui.find({ key: 'frame' })
      expect(frame?.props.borderStyle).toBe('round')
      expect(await ui.find({ type: 'Text', text: 'En attente de ta réponse' })).toBeDefined()
      expect(await ui.find({ key: `row:${id}` })).toBeDefined()
      await ui.press({ key: `remove:${id}` })
      await ui.unmount()
    }
  })

  test('[x] removes the question', async ($, on) => {
    standInForPanes(on)
    for (const surface of SURFACES) {
      const id = await pin($, `Ship on ${surface}?`)
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      await ui.press({ key: `remove:${id}` })
      expect(await ui.find({ key: `row:${id}` })).toBeUndefined()
      await ui.unmount()
      expect((await call($, UNPIN, { id })).deny).toMatch(/no pinned question/)
    }
  })

  test('[détails] opens the pane on the context, [x] closes it', async ($, on) => {
    const panes = standInForPanes(on)
    for (const surface of SURFACES) {
      const id = await pin($, `Which cache on ${surface}?`, '## Options\n\n- Redis')
      const band = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      await band.press({ key: `details:${id}` })
      expect(panes.opened).toContain(`Which cache on ${surface}?`)

      const pane = await $.ui.mount({
        plugin: 'open-question',
        surface,
        component: 'Pane',
        requestId: 'open-question',
        props: { ...PANE_PROPS, title: `Which cache on ${surface}?` },
      })
      const markdown = await pane.find({ type: 'Markdown' })
      expect(markdown?.props.text).toBe('## Options\n\n- Redis')

      await band.press({ key: `remove:${id}` })
      expect(panes.closed).toContain('open-question')
      expect(await pane.find({ type: 'Markdown' })).toBeUndefined()
      await pane.unmount()
      await band.unmount()
    }
  })
})

describe('input checks', () => {
  test('refuses an empty question', async ($, on) => {
    standInForPanes(on)
    expect((await call($, PIN, { question: '   ' })).deny).toMatch(/non-empty string/)
    expect((await call($, PIN, {})).deny).toMatch(/non-empty string/)
  })

  test('refuses a context that is not a string', async ($, on) => {
    standInForPanes(on)
    expect((await call($, PIN, { question: 'Why?', context: 42 })).deny).toMatch(/`context` must be a string/)
  })

  test('refuses an unpin without a string id', async ($, on) => {
    standInForPanes(on)
    expect((await call($, UNPIN, { id: 1 })).deny).toMatch(/no pinned question/)
  })

  test('drops a blank context, so no details button is drawn', async ($, on) => {
    standInForPanes(on)
    const id = await pin($, 'Blank context?', '   ')
    const ui = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    expect(await ui.find({ key: `details:${id}` })).toBeUndefined()
    await ui.unmount()
  })
})

describe('pane', () => {
  test('shows a placeholder when no question is selected', async ($, on) => {
    standInForPanes(on)
    await pin($, 'Unrelated?', 'Some context.')
    const pane = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'Pane', requestId: 'open-question', props: PANE_PROPS })
    expect(await pane.find({ type: 'Markdown' })).toBeUndefined()
    expect(await pane.find({ type: 'Text', text: 'No question to show.' })).toBeDefined()
    await pane.unmount()
  })
})

describe('session end', () => {
  const REASONS = ['clear', 'resume', 'logout', 'prompt_input_exit', 'other'] as const
  const standInForSessionEnd = (on: On) => on('session.end', (_, e) => ({ sessionId: e.sessionId }))
  const end = ($: Engine, reason: (typeof REASONS)[number]) =>
    $.session.end({ reason, sessionId: 'test-session', resume: { id: 'test-session' } })

  for (const reason of REASONS) {
    test(`${reason} empties the band and closes the pane`, async ($, on) => {
      const panes = standInForPanes(on)
      standInForSessionEnd(on)
      const id = await pin($, 'Survives the end?', '## Context')
      const band = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
      await band.press({ key: `details:${id}` })
      await band.unmount()

      await end($, reason)

      expect(panes.closed).toContain('open-question')
      const after = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
      expect(await after.find({ key: 'frame' })).toBeUndefined()
      await after.unmount()
      expect((await call($, UNPIN, { id })).deny).toMatch(/no pinned question/)
    })
  }

  test('an ended session frees the slot', async ($, on) => {
    standInForPanes(on)
    standInForSessionEnd(on)
    await pin($, 'One?')
    await end($, 'resume')
    expect((await call($, PIN, { question: 'Two?' })).deny).toBeUndefined()
  })
})

/**
 * Stands for the prompt box beneath the plugin: a draft that reads and fills
 * as the engine's does.
 *
 * @param on the test's registrar
 * @param draft what the person has typed already
 * @returns the box, whose `text` follows every fill
 */
const standInForPrompt = (on: On, draft = '') => {
  const box = { text: draft }
  on('prompt.read', () => ({ value: { text: box.text, cursor: box.text.length } }))
  on('prompt.fill', ($, e) => {
    box.text = e.mode === 'replace' ? e.text : box.text + e.text

    return { isFilled: true }
  })
  on('prompt.submit', ($, e) => ({ text: e.text }))

  return box
}

describe('options', () => {
  test('refuses one option, five, one over 30 characters, one on two lines', async ($, on) => {
    standInForPanes(on)
    const refusals = [
      ['Only one'],
      ['a', 'b', 'c', 'd', 'e'],
      ['short', 'c'.repeat(31)],
      ['first\nline', 'other'],
    ]
    for (const options of refusals) {
      expect((await call($, PIN, { question: 'Pick?', options })).deny).toMatch(/Rephrase/)
    }
    const two = await call($, PIN, { question: 'Two?', options: ['a', 'c'.repeat(30)] })
    expect(two.deny).toBeUndefined()
    await call($, UNPIN, { id: two.result })
    expect((await call($, PIN, { question: 'Four?', options: ['a', 'b', 'c', 'd'] })).deny).toBeUndefined()
  })

  test('draws only [répondre] for an open question', async ($, on) => {
    standInForPanes(on)
    const open = await pin($, 'Why so?')
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect(await ui.find({ key: `answer:${open}` })).toBeDefined()
      expect(await ui.find({ key: `option:${open}:0` })).toBeUndefined()
      await ui.unmount()
    }
  })

  test('draws one button per option, then [répondre]', async ($, on) => {
    standInForPanes(on)
    const choice = (await call($, PIN, { question: 'Which cache?', options: ['Redis', 'Memory'] })).result as string
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect((await ui.find({ key: `option:${choice}:0` }))?.text).toBe('Redis')
      expect((await ui.find({ key: `option:${choice}:1` }))?.text).toBe('Memory')
      expect(await ui.find({ key: `answer:${choice}` })).toBeDefined()
      expect((await ui.find({ key: `answers:${choice}` }))?.props.flexWrap).toBe('wrap')
      await ui.unmount()
    }
  })
})

describe('answers', () => {
  for (const surface of SURFACES) {
    test(`an option fills the answer, the draft kept after it (${surface})`, async ($, on) => {
      standInForPanes(on)
      const box = standInForPrompt(on)
      const id = (await call($, PIN, { question: 'Which cache?', options: ['Redis', 'Memory'] })).result as string
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })

      await ui.press({ key: `option:${id}:0` })
      expect(box.text).toBe('Réponse à « Which cache? » : Redis')

      box.text = 'because it is fast'
      await ui.press({ key: `option:${id}:0` })
      expect(box.text).toBe('Réponse à « Which cache? » : Redis because it is fast')

      await ui.press({ key: `option:${id}:1` })
      expect(box.text).toBe('Réponse à « Which cache? » : Memory because it is fast')
      await ui.unmount()
    })

    test(`[répondre] opens a free answer, the draft kept after it (${surface})`, async ($, on) => {
      standInForPanes(on)
      const box = standInForPrompt(on)
      const id = await pin($, 'Why so?')
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })

      await ui.press({ key: `answer:${id}` })
      expect(box.text).toBe('Réponse à « Why so? » : ')

      box.text = 'no idea yet'
      await ui.press({ key: `answer:${id}` })
      expect(box.text).toBe('Réponse à « Why so? » : no idea yet')

      await ui.press({ key: `answer:${id}` })
      expect(box.text).toBe('Réponse à « Why so? » : no idea yet')
      await ui.unmount()
    })
  }

  test('a tagged submit unpins its question, the prompt unchanged', async ($, on) => {
    standInForPanes(on)
    standInForPrompt(on)
    const answered = await pin($, 'Which cache?')
    const sent = await $.prompt.submit({ text: 'Réponse à « Which cache? » : Redis', wait: false, origin: { kind: 'composer' } })
    expect(sent).toMatchObject({ text: 'Réponse à « Which cache? » : Redis' })
    expect((await call($, UNPIN, { id: answered })).deny).toMatch(/no pinned question/)
  })

  test('an untagged submit keeps the question', async ($, on) => {
    standInForPanes(on)
    standInForPrompt(on)
    const id = await pin($, 'Which cache?')
    await $.prompt.submit({ text: 'Redis, I think', wait: false, origin: { kind: 'composer' } })
    expect((await call($, UNPIN, { id })).deny).toBeUndefined()
  })

  test('a submit tagged with an unknown question unpins nothing', async ($, on) => {
    standInForPanes(on)
    standInForPrompt(on)
    const id = await pin($, 'Which cache?')
    await $.prompt.submit({ text: 'Réponse à « Which queue? » : Kafka', wait: false, origin: { kind: 'composer' } })
    expect((await call($, UNPIN, { id })).deny).toBeUndefined()
  })
})

describe('answer edge cases', () => {
  test('refuses options that are not an array of non-empty strings', async ($, on) => {
    standInForPanes(on)
    expect((await call($, PIN, { question: 'Pick?', options: 'a, b' })).deny).toMatch(/2 to 4 choices/)
    expect((await call($, PIN, { question: 'Pick?', options: ['a', 42] })).deny).toMatch(/non-empty string/)
    expect((await call($, PIN, { question: 'Pick?', options: ['a', '  '] })).deny).toMatch(/non-empty string/)
    expect((await call($, PIN, { question: 'Pick?', options: [] })).deny).toMatch(/2 to 4 choices/)
  })

  test('a question holding » and : still relabels and unpins on its own tag', async ($, on) => {
    standInForPanes(on)
    const box = standInForPrompt(on, 'see logs')
    const question = 'Garder « old » : oui ou non?'
    const id = (await call($, PIN, { question, options: ['oui', 'non'] })).result as string
    const ui = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })

    await ui.press({ key: `option:${id}:0` })
    await ui.press({ key: `option:${id}:1` })
    expect(box.text).toBe(`Réponse à « ${question} » : non see logs`)
    await ui.unmount()

    await $.prompt.submit({ text: box.text, wait: false, origin: { kind: 'composer' } })
    expect((await call($, UNPIN, { id })).deny).toMatch(/no pinned question/)
  })

  test('a question holding quotes fills and unpins verbatim', async ($, on) => {
    standInForPanes(on)
    const box = standInForPrompt(on)
    const question = 'Rename "users" to \'accounts\'?'
    const id = await pin($, question)
    const ui = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    await ui.press({ key: `answer:${id}` })
    expect(box.text).toBe(`Réponse à « ${question} » : `)
    await ui.unmount()

    await $.prompt.submit({ text: `${box.text}yes`, wait: false, origin: { kind: 'composer' } })
    expect((await call($, UNPIN, { id })).deny).toMatch(/no pinned question/)
  })

  test('a tag whose trailing space the composer trimmed still relabels and unpins', async ($, on) => {
    standInForPanes(on)
    const box = standInForPrompt(on, 'Réponse à « Which cache? » :')
    const id = (await call($, PIN, { question: 'Which cache?', options: ['Redis', 'Memory'] })).result as string
    const ui = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    await ui.press({ key: `option:${id}:1` })
    expect(box.text).toBe('Réponse à « Which cache? » : Memory')
    await ui.unmount()

    await $.prompt.submit({ text: 'Réponse à « Which cache? » :', wait: false, origin: { kind: 'composer' } })
    expect((await call($, UNPIN, { id })).deny).toMatch(/no pinned question/)
  })

  test('[répondre] after an option drops the option, keeps the draft', async ($, on) => {
    standInForPanes(on)
    const box = standInForPrompt(on, 'because it is fast')
    const id = (await call($, PIN, { question: 'Which cache?', options: ['Redis', 'Memory'] })).result as string
    const ui = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    await ui.press({ key: `option:${id}:0` })
    await ui.press({ key: `answer:${id}` })
    expect(box.text).toBe('Réponse à « Which cache? » : because it is fast')
    await ui.unmount()
  })

  test('an option that another option starts with is swapped whole', async ($, on) => {
    standInForPanes(on)
    const box = standInForPrompt(on, 'for HA')
    const id = (await call($, PIN, { question: 'Which cache?', options: ['Redis', 'Redis Cluster', 'Memory'] }))
      .result as string
    const ui = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    await ui.press({ key: `option:${id}:1` })
    expect(box.text).toBe('Réponse à « Which cache? » : Redis Cluster for HA')
    await ui.press({ key: `option:${id}:2` })
    expect(box.text).toBe('Réponse à « Which cache? » : Memory for HA')
    await ui.unmount()
  })

  test('a draft tagged for a question since unpinned is relabelled, not stacked', async ($, on) => {
    standInForPanes(on)
    const box = standInForPrompt(on)
    const old = (await call($, PIN, { question: 'Which cache?', options: ['Redis', 'Memory'] })).result as string
    const band = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    await band.press({ key: `option:${old}:0` })
    box.text += ' because it is fast'
    await band.press({ key: `remove:${old}` })

    const next = (await call($, PIN, { question: 'Which queue?', options: ['Kafka', 'SQS'] })).result as string
    await band.press({ key: `option:${next}:0` })
    expect(box.text).not.toContain('Which cache?')
    await band.unmount()
  })
})

describe('review pass 3', () => {
  test('options are trimmed at pin, so a padded option is swapped whole', async ($, on) => {
    standInForPanes(on)
    const box = standInForPrompt(on)
    const id = (await call($, PIN, { question: 'Keep it?', options: [' Oui', 'Non'] })).result as string
    const ui = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    await ui.press({ key: `option:${id}:0` })
    expect(box.text).toBe('Réponse à « Keep it? » : Oui')
    await ui.press({ key: `option:${id}:1` })
    expect(box.text).toBe('Réponse à « Keep it? » : Non')
    await ui.unmount()
  })

  test('the question is trimmed at pin, and the limits apply after trimming', async ($, on) => {
    standInForPanes(on)
    const box = standInForPrompt(on)
    const id = (await call($, PIN, { question: '  Keep it?  ', options: [`  ${'c'.repeat(30)}  `, 'Non'] }))
      .result as string
    const ui = await $.ui.mount({ plugin: 'open-question', surface: 'terminal', component: 'AbovePrompt', props: BAND_PROPS })
    await ui.press({ key: `answer:${id}` })
    expect(box.text).toBe('Réponse à « Keep it? » : ')
    expect((await ui.find({ key: `option:${id}:0` }))?.text).toBe('c'.repeat(30))
    await ui.unmount()
    expect((await call($, PIN, { question: 'Other?' })).deny).toMatch(/already pinned/)
    await call($, UNPIN, { id })
    expect((await call($, PIN, { question: ` ${'a'.repeat(100)} ` })).deny).toBeUndefined()
  })

  test('a prompt dropped beneath the mod keeps its question pinned', async ($, on) => {
    standInForPanes(on)
    on('prompt.submit', () => ({ drop: 'blocked by a settings hook' }))
    const id = await pin($, 'Which cache?')
    const sent = await $.prompt.submit({ text: 'Réponse à « Which cache? » : Redis', wait: false, origin: { kind: 'composer' } })
    expect(sent).toMatchObject({ drop: 'blocked by a settings hook' })
    expect((await call($, UNPIN, { id })).deny).toBeUndefined()
  })
})

const ENGINE_SECTIONS = [
  { id: 'intro', text: 'intro', scope: 'shared' },
  { id: 'env', text: 'env', scope: 'session' },
] as const

/**
 * Builds the input of a prompt composed for a request offering `tools`.
 *
 * @param tools the names of the tools the request offers
 * @returns a complete `prompt.compose` input
 */
const composeInput = (tools: readonly string[]) => ({
  model: 'claude-opus-5-5',
  promptModel: 'claude-opus-5-5',
  surfaces: ['terminal'] as const,
  tools,
  outputStyle: null,
  traits: [],
})

/**
 * Stands for the engine beneath the plugin at `prompt.compose`: answers
 * ENGINE_SECTIONS and records the tools of each input it receives.
 *
 * @param on the test's registrar
 * @returns the tool lists received, in order
 */
const standInForCompose = (on: On) => {
  const received: (readonly string[])[] = []
  on('prompt.compose', ($, e) => {
    received.push(e.tools)

    return { sections: ENGINE_SECTIONS }
  })

  return received
}

describe('prompt', () => {
  test('adds the rule last, as a session section, when the request offers pin_question', async ($, on) => {
    const received = standInForCompose(on)
    const tools = ['Read', PIN, UNPIN]

    const { sections } = await $.prompt.compose(composeInput(tools))

    expect(received).toEqual([tools])
    expect(sections.slice(0, -1)).toEqual([...ENGINE_SECTIONS])
    expect(sections[sections.length - 1]).toMatchObject({ id: 'open-question:rule', scope: 'session' })
    expect(sections[sections.length - 1]?.text).toContain('never pin a question as you ask it')
  })

  test('leaves the sections as next(e) answered when the request lacks pin_question', async ($, on) => {
    const received = standInForCompose(on)

    const { sections } = await $.prompt.compose(composeInput(['Read']))

    expect(received).toEqual([['Read']])
    expect(sections).toEqual([...ENGINE_SECTIONS])
  })
})
