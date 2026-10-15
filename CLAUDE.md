# CLAUDE.md

소개팅 매칭 로직 수업 과제. 공개 저장소 `yufe9/dating-match`, GitHub Pages가 `main` 의 `docs/` 를 배포합니다.
UI 문자열과 주석은 전부 한국어입니다.

## 먼저 읽을 것

- `PRODUCT.md`: 누가, 왜 쓰는지와 지켜야 할 제품 원칙
- `DESIGN.md`: 웹(`docs/app.html`) 디자인 규칙서. **화면을 고치기 전에 반드시 읽습니다.**
- `README.md`: 로직 설명과 실행 방법

## 구조

- `match.py` 가 규칙의 원본입니다. 웹은 `python match.py export` 로 만든 `docs/profiles.json` 의 점수표·여행 규칙을 그대로 씁니다.
  점수표나 여행 규칙(`EVENTS`, `TRIP_*`, `FIRST_IMPRESSION`)을 바꾸면 export 를 다시 실행합니다.
- `docs/app-logic.js` 는 화면을 모르는 순수 로직(카드 → 성향 → 여행 온도 → 도시 → 후보 → 48시간 여행), `docs/app.html` 은 화면입니다.
- 웹만 다른 값: 커플 기준 `COUPLE_MIN = 70`(콘솔 85). 웹은 쌍방 확인 없이 바로 여행을 떠나기 때문이며 이유와 시뮬레이션 수치는 `app-logic.js` 주석과 로직 공개 화면에 있습니다.
- CSV에 칸을 추가하지 않습니다. `python match.py check` 의 시각화 기준값(M06 × W22) 해시가 깨집니다.

## 고친 뒤 반드시 실행

```bash
node tests/app-logic.test.js              # 웹 로직 11개
python match.py check                     # 파이썬 자체 점검 + 시각화 기준값
node .claude/skills/design-taste-frontend/scripts/lint.mjs docs/app.html      # 실패 0
node .claude/skills/design-taste-frontend/scripts/inspect.mjs docs/app.html   # 실패 0 (영상 없음 경고 1개는 의도)
python -m http.server 8765 --directory docs   # 다른 터미널에서 켜 두고
node tests/flow.mjs .taste-skill/flow 1440 900 abaabbabaaabbaab   # 하와이
node tests/flow.mjs .taste-skill/flow 1440 900 abaabaaaabbbaaaa   # 홍콩
node tests/flow.mjs .taste-skill/flow 390 844 aaaabaaabbaaaaaa    # 삿포로 (휴대폰 너비)
```

`tests/flow.mjs` 가 남긴 스크린샷을 `docs/design-ref/` 의 기준 화면과 눈으로 비교합니다. 의도한 디자인 변경이면 기준 화면도 새로 찍어 바꿉니다.

## 디자인 도구 (설치형, 저장소에는 없음)

`.claude/` 는 커밋하지 않습니다. 새 컴퓨터에서는 이 폴더에서 다시 설치합니다.

```bash
npx --yes skills@latest add emilkowalski/skills --skill "emil-design-eng" --agent claude-code --yes --copy
npx --yes skills@latest add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend" --agent claude-code --yes --copy
npx --yes impeccable@latest install --providers=claude --scope=project
```

`skills-lock.json` 에 설치한 스킬 버전이 기록돼 있습니다. 디자인 방향 원본은 `.taste-skill/direction.json`(`draw.mjs --show` 로 다시 보기)입니다.

## 규칙

- 외부 라이브러리는 먼저 묻습니다. CSP가 스크립트·이미지를 같은 출처로 제한합니다(폰트만 Google Fonts).
- 화면은 `textContent` 로만 그립니다(`innerHTML` 금지). 학번은 브라우저에 남기지 않습니다.
- `docs/config.js` 에는 Supabase URL과 publishable 키만. 비밀 키(`sb_secret_`, `service_role`)는 절대 넣지 않습니다.
- 가상 인물의 후기·통계를 지어내지 않습니다. 사진은 공개 라이선스만 쓰고 출처를 `docs/assets/credits.json` 과 페이지 바닥에 남깁니다.
- 줄바꿈은 LF입니다. Windows Python 으로 파일을 쓸 때는 `newline="\n"` 또는 바이트로 씁니다(`write_text` 는 CRLF로 바꿉니다).
