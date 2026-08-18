export const meta = {
  name: 'phase-harness',
  description: 'Phase 번호를 받아 coding→(test→verify→review 피드백 루프, 최대 3회)→compound 순서로 해당 Phase 개발 사이클을 실행한다',
  phases: [
    { title: 'Compound Log 확인', detail: '누적 결정사항·주의사항 파악' },
    { title: 'Coding', detail: '해당 Phase 문서만 참고해 구현/수정' },
    { title: 'Test', detail: '체크리스트 작성 후 테스트 실행, 통과 항목 스크린샷' },
    { title: 'Verify', detail: 'Phase 완료 기준 체크리스트 재확인, pass/fail 판정' },
    { title: 'Review', detail: '소스코드/로그 기반 버그 점검, BLOCKING/NIT 보고' },
    { title: 'Compound', detail: '반복 패턴 분석, compound-log.md 기록, 하네스 개선' },
  ],
}

const MAX_LOOPS = 3

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['pass', 'fail'] },
    report: { type: 'string', description: '해당 에이전트 정의 형식 그대로의 전체 보고 내용' },
  },
  required: ['verdict', 'report'],
}

const phaseNum = Number(args)
if (!Number.isInteger(phaseNum) || phaseNum < 1) {
  throw new Error('phase-harness는 Phase 번호(정수, 예: 1)를 args로 받아야 합니다.')
}

const phaseDoc = `FE/docs/PHASES/PHASE${phaseNum}.md`
const logPath = 'FE/docs/compound-log.md'

function withContext(agentFile, task) {
  return `아래 순서를 반드시 지켜서 작업해줘.
1. ${logPath} 파일을 먼저 읽고, 지금까지 누적된 결정사항·주의사항·반복됐던 실수를 파악한다. 파일이 없거나 비어 있으면 없다고 알고 넘어간다.
2. FE/.claude/agents/${agentFile}.md 파일을 읽고, 그 안에 정의된 역할과 규칙을 그대로 따른다.
3. ${logPath}에 적힌 주의사항(특히 아래 요약된 내용)을 이번 작업에 반영한다.

[compound-log.md 누적 요약]
${logDigest}

작업:
${task}`
}

phase('Compound Log 확인')
const logDigest = await agent(
  `${logPath} 파일을 읽고, 지금까지 기록된 문제점·반복 패턴·하네스 개선 이력을 짧게 요약해줘. 파일이 없거나 비어 있으면 "기록된 내용 없음"이라고만 답해줘.`,
  { label: 'compound-log-digest', phase: 'Compound Log 확인' }
)

phase('Coding')
let codingResult = await agent(
  withContext(
    'coding',
    `${phaseDoc} 문서만 참고해서 이번 Phase(${phaseNum})의 개발을 진행해줘. 다른 Phase 범위의 기능은 만들지 마. ${phaseDoc}가 없으면 멈추고 알려줘.`
  ),
  { label: 'coding', phase: 'Coding' }
)

let testResult = null
let verifyResult = null
let reviewResult = null
let attempt = 0
let stopReason = 'all-pass'

while (attempt < MAX_LOOPS) {
  attempt++
  log(`피드백 루프 ${attempt}/${MAX_LOOPS}번째 시도: test → verify → review 실행`)

  phase('Test')
  testResult = await agent(
    withContext(
      'test',
      `${phaseDoc} 문서를 기준으로 방금 끝난 구현에 대한 체크리스트를 만들고, 테스트를 직접 실행해서 통과/실패를 구분해줘. 눈으로 확인 가능한 화면은 screenshots 폴더에 png 캡쳐를 남겨줘. verdict 필드에는 실패 항목이 하나라도 있으면 fail, 전부 통과면 pass를 넣고, report 필드에는 test.md에서 정의한 형식(통과/실패 목록) 그대로 담아줘.\n\n[coding 단계 결과]\n${codingResult}`
    ),
    { label: `test-attempt${attempt}`, phase: 'Test', schema: VERDICT_SCHEMA }
  )

  phase('Verify')
  verifyResult = await agent(
    withContext(
      'verify',
      `${phaseDoc} 문서의 "완료 기준 체크리스트"를 다시 확인해서 이번 Phase(${phaseNum})가 실제로 끝났는지 항목별 O/X로 판정해줘. verdict 필드에는 verify.md에서 정의한 대로 전체 O면 pass, 하나라도 X면 fail을 넣고, report 필드에는 항목별 O/X와 근거를 그대로 담아줘.\n\n[coding 단계 결과]\n${codingResult}\n\n[test 단계 결과]\n${JSON.stringify(testResult)}`
    ),
    { label: `verify-attempt${attempt}`, phase: 'Verify', schema: VERDICT_SCHEMA }
  )

  phase('Review')
  reviewResult = await agent(
    withContext(
      'review',
      `이번 Phase(${phaseNum}) 작업으로 바뀐 소스코드와 남아있는 로그를 근거로 버그·동작 오류를 점검해줘. verdict 필드에는 review.md에서 정의한 대로 [BLOCKING]이 하나도 없으면 pass, 하나라도 있으면 fail을 넣고, report 필드에는 [BLOCKING]/[NIT] 목록을 그대로 담아줘.\n\n[coding 단계 결과]\n${codingResult}`
    ),
    { label: `review-attempt${attempt}`, phase: 'Review', schema: VERDICT_SCHEMA }
  )

  if (!testResult || !verifyResult || !reviewResult) {
    stopReason = 'agent-unavailable'
    log('test/verify/review 중 결과를 받지 못한 단계가 있어 루프를 중단합니다.')
    break
  }

  const anyFail = testResult.verdict === 'fail' || verifyResult.verdict === 'fail' || reviewResult.verdict === 'fail'

  if (!anyFail) {
    stopReason = 'all-pass'
    log(`${attempt}번째 시도에서 test/verify/review 모두 pass. 루프를 종료합니다.`)
    break
  }

  if (attempt >= MAX_LOOPS) {
    stopReason = 'max-loops-reached'
    log(`최대 ${MAX_LOOPS}번 시도했지만 아직 FAIL이 남아 있어 루프를 종료합니다.`)
    break
  }

  log(`${attempt}번째 시도에서 FAIL 발견 — 코드 수정 후 test 단계부터 다시 실행합니다.`)
  phase('Coding')
  codingResult = await agent(
    withContext(
      'coding',
      `${phaseDoc} 기준으로 아래 FAIL 결과를 최소한으로 수정해줘. 이미 통과한 부분은 건드리지 마.\n\n[test 결과]\n${JSON.stringify(testResult)}\n\n[verify 결과]\n${JSON.stringify(verifyResult)}\n\n[review 결과]\n${JSON.stringify(reviewResult)}`
    ),
    { label: `coding-fix-attempt${attempt}`, phase: 'Coding' }
  )
}

phase('Compound')
const compoundResult = await agent(
  withContext(
    'compound',
    `이번 Phase(${phaseNum}) 실행 결과를 분석해서 문제점과 반복 패턴을 ${logPath}에 date/tags/category 형식으로 기록해줘. 피드백 루프를 ${attempt}번 돌았고 종료 사유는 "${stopReason}"이야 (all-pass: 전부 통과, max-loops-reached: 최대 횟수까지 돌았는데도 FAIL 남음, agent-unavailable: 단계 실행 실패). 특히 max-loops-reached인 경우는 반드시 반복 패턴으로 취급해서 원인과 재발 방지책을 남겨줘. 필요하면 관련 하네스 파일도 최소한으로 고쳐줘.\n\n[coding 최종 결과]\n${codingResult}\n\n[test 최종 결과]\n${JSON.stringify(testResult)}\n\n[verify 최종 결과]\n${JSON.stringify(verifyResult)}\n\n[review 최종 결과]\n${JSON.stringify(reviewResult)}`
  ),
  { label: 'compound', phase: 'Compound' }
)

return {
  phase: phaseNum,
  attempts: attempt,
  stopReason,
  coding: codingResult,
  test: testResult,
  verify: verifyResult,
  review: reviewResult,
  compound: compoundResult,
}
