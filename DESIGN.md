---
name: 48시간 소개팅
description: 여행하며 상대를 알아가는 소개팅. 페이지 전체가 한 장의 탑승권 묶음이고, 여행지마다 색이 바뀐다.
colors:
  field-putty: "#dedad3"
  paper-bone: "#f3f2ef"
  paper-bone-step: "#e6e4df"
  ink-black: "#0a0a0a"
  ink-muted: "#55514a"
  accent-harbour-teal: "#256f82"
  hawaii-sunset-field: "#e2502a"
  hawaii-shell-paper: "#fff3e6"
  hawaii-shell-step: "#fbe1cb"
  hawaii-ink: "#2a0d05"
  hawaii-muted: "#6b3a2a"
  hawaii-hibiscus: "#a3123a"
  hongkong-jade-night: "#0e3a37"
  hongkong-paper: "#f5ecdc"
  hongkong-paper-step: "#eadcc4"
  hongkong-ink: "#141110"
  hongkong-muted: "#5a4d40"
  hongkong-neon-red: "#c8102e"
  hongkong-on-field: "#f5ecdc"
  sapporo-ice-field: "#c9dce7"
  sapporo-snow-paper: "#fbfcfd"
  sapporo-snow-step: "#e6eef3"
  sapporo-ink: "#0c1a24"
  sapporo-muted: "#3f5464"
  sapporo-lamp-amber: "#a0520f"
  error-red: "#b3261e"
typography:
  display:
    fontFamily: "Gowun Batang, Nanum Myeongjo, Batang, serif"
    fontSize: "clamp(3.4rem, 1.6rem + 7vw, 7.5rem)"
    fontWeight: 700
    lineHeight: 0.95
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Gowun Batang, Nanum Myeongjo, Batang, serif"
    fontSize: "clamp(2rem, 1.3rem + 3.2vw, 4rem)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  lead:
    fontFamily: "Gowun Batang, Nanum Myeongjo, Batang, serif"
    fontSize: "clamp(1.25rem, 1.1rem + 0.7vw, 1.625rem)"
    fontWeight: 400
    lineHeight: 1.45
  body:
    fontFamily: "IBM Plex Sans KR, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "clamp(1.0625rem, 1.02rem + 0.2vw, 1.1875rem)"
    fontWeight: 400
    lineHeight: 1.55
  small:
    fontFamily: "IBM Plex Sans KR, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  none: "0"
  ticket: "10px"
spacing:
  gutter: "clamp(16px, 3.2vw, 40px)"
  part: "clamp(28px, 4vw, 64px)"
  section: "140px"
components:
  button-primary:
    backgroundColor: "{colors.accent-harbour-teal}"
    textColor: "{colors.paper-bone}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "16px 26px"
  button-primary-hover:
    backgroundColor: "{colors.ink-black}"
    textColor: "{colors.paper-bone}"
  ticket:
    backgroundColor: "{colors.paper-bone}"
    textColor: "{colors.ink-black}"
    rounded: "{rounded.ticket}"
    padding: "{spacing.part}"
  ticket-stub:
    backgroundColor: "{colors.paper-bone-step}"
    textColor: "{colors.ink-black}"
    padding: "{spacing.part}"
  choice:
    backgroundColor: "{colors.paper-bone-step}"
    textColor: "{colors.ink-black}"
    typography: "{typography.lead}"
    rounded: "{rounded.none}"
    padding: "clamp(22px, 3.4vw, 36px) clamp(20px, 3vw, 32px)"
  choice-picked:
    backgroundColor: "{colors.accent-harbour-teal}"
    textColor: "{colors.paper-bone}"
  pass-best:
    backgroundColor: "{colors.ink-black}"
    textColor: "{colors.paper-bone}"
    rounded: "{rounded.ticket}"
---

# Design System: 48시간 소개팅

이 문서는 `docs/app.html` 의 디자인 규칙서다. 값의 원본은 위 머리말(YAML)이고, 실제 코드는 `docs/app.html` 맨 위 `:root` 와 `html[data-city=…]` 블록이다. 둘이 어긋나면 코드를 기준으로 이 문서를 고친다. 제품 사실(누가, 왜, 무엇을)은 `PRODUCT.md` 에 있다.

## Overview

**핵심 비유: 탑승권 묶음.** 여행에 실제로 있는 인쇄물인 탑승권을 페이지 자체로 쓴다. 입장 화면은 탑승권과 떼어 내는 부분(탑승 수속), 카드는 한 장씩 넘기는 탑승권, 목적지는 발권된 표, 후보는 탑승객 표, 48시간은 톱니로 잘린 일정표 슬립, 바닥글은 탑승권 뒷면이다. 새 화면을 만들 때도 이 셋 중 하나의 종이로 만든다: 탑승권(점선 절취선 + 반원 홈), 떼어 내는 부분(한 단계 어두운 종이), 일정표 슬립(아래가 톱니, 점선 리더).

**여행 온도가 페이지 색을 정한다.** 카드를 고르는 동안 화면 바탕이 지금 기운 도시 색으로 바뀌고, 목적지가 정해지면 그 도시 색으로 고정된다. 이것이 이 페이지의 "살아 있는 한 가지"다.

이 방향은 taste 스킬의 방향 추첨에서 `page-is-the-object`(seed 90236116)를 고른 결과다. `node .claude/skills/design-taste-frontend/scripts/draw.mjs --show` 로 원래 지침을 다시 볼 수 있다(`.taste-skill/direction.json`).

## Colors

종이·잉크·바탕 세 가지에 강조색 하나. 두 도수 인쇄물처럼 평평한 색만 쓴다.

### 기본 (출발 전)
- **Putty 바탕** `field-putty`: 페이지 바닥. 도시가 정해지기 전의 공항 대기실.
- **Bone 종이** `paper-bone` / 한 단계 어두운 `paper-bone-step`: 탑승권과 떼어 내는 부분. 노란 크림으로 바꾸지 않는다.
- **잉크** `ink-black`, 보조 `ink-muted`.
- **Harbour Teal** `accent-harbour-teal`: 강조. 행동 버튼과 지금 위치(진행 점)에만.

### 하와이: 석양이 지고 뜨겁고 열정적인
`hawaii-sunset-field` 바탕, `hawaii-shell-paper` 종이, `hawaii-hibiscus` 강조. 바탕 위 글자는 거의 검은 갈색.

### 홍콩: 따뜻하지만 약간 시린 구석
`hongkong-jade-night` 바탕(유일한 어두운 바탕이라 바탕 위 글자는 `hongkong-on-field` 밝은색), 따뜻한 종이 `hongkong-paper`, `hongkong-neon-red` 강조.

### 삿포로: 차갑고 얼음장 같지만 따뜻한 구석
`sapporo-ice-field` 바탕, 눈빛 종이 `sapporo-snow-paper`, 가로등 하나 같은 `sapporo-lamp-amber` 강조.

### Named Rules
- **도시 색은 한 곳에서만.** 색 변수(`--field --paper --paper-2 --ink --muted --accent --accent-ink --on-field --on-field-muted`)를 `html[data-city="…"]` 블록에서만 바꾼다. 개별 요소에 도시 색을 직접 쓰지 않는다.
- **대비 4.5:1.** 강조색 위 흰 글자, 바탕 위 글자 모두 4.5:1 이상. 새 강조색은 넣기 전에 잰다.
- **회색 본문 금지.** 읽는 글은 `--ink`. `--muted` 는 보조 설명(14px 글)에만.

## Typography

두 서체만 쓴다. 제목·장면·목적지 이름은 **Gowun Batang**(손으로 찍은 활판 같은 명조), 본문·표·입력은 **IBM Plex Sans KR**. 크기는 다섯 단계(`display` `headline` `lead` `body` `small`)뿐이고, 여섯 번째 크기를 만들지 않는다.

### Named Rules
- **제목은 어떤 너비에서도 두 줄 이하.** 넘치면 글자를 줄이지 말고 말을 줄인다("48시간은 이렇게 흘러갑니다" → "48시간의 일정표").
- **한글은 단어 단위로 줄바꿈.** `body` 에 `word-break: keep-all` 이 걸려 있다. 지우면 "48 / 시간"처럼 단어가 잘린다.
- **본문 최소 17px, 보조 글 14px.** 13px 이하는 쓰지 않는다.
- **숫자는 `font-variant-numeric: tabular-nums`.** 고정폭 글꼴로 흉내 내지 않는다.

## Layout

- 좌우 여백은 `spacing.gutter` 하나, 큰 구역 사이는 `spacing.section`(140px)으로 구역 안 간격보다 확실히 크게.
- 탑승권은 데스크톱에서 본문 1.7 : 떼어 내는 부분 1, 760px 이하에서는 위아래로 쌓이고 절취선이 가로로 눕는다.
- 결과 쪽은 아래로 쌓인다: 목적지 → 일정표 → 로직 공개. 앞 화면을 지우지 않는다.
- 휴대폰 첫 화면에도 행동 버튼이 하나 보여야 한다(입장 화면의 `탑승 수속하기`).

## Elevation & Depth

**평평하다.** 쉬고 있는 요소에는 그림자가 없다. 면은 그림자나 선이 아니라 종이 색 한 단계(`--paper` → `--paper-2`)로 나눈다. 강조하고 싶으면 색을 뒤집는다(궁합 1위 탑승객 표는 잉크 바탕에 종이색 글자).

## Shapes

- 종이(탑승권·카드·후보 표·로직 단계)는 `rounded.ticket` 10px, 버튼과 선택지는 `rounded.none` 각진 모서리. 이 둘 말고 다른 둥글기를 만들지 않는다.
- **절취선**: 6px 둥근 점선(`border: 6px dotted var(--field)`) + 양 끝에 바탕색 반원 홈(지름 34px). 얇은 1px 선으로 대신하지 않는다.
- **톱니**: 일정표 슬립 아래쪽은 `clip-path: polygon` 톱니(`zigzag()` 함수). 위쪽은 곧다.
- **점선 리더**: 일정표 줄은 왼쪽 내용 … 오른쪽 값 사이를 4px 점선으로 잇는다.

## Components

### Buttons
평평한 한 색, 각진 모서리. 누르면 `scale(0.97)`(140ms), 마우스가 있는 기기에서만 hover 시 잉크색으로 뒤집힌다. 보조 버튼(`.btn.ghost`)은 테두리 대신 글자색 13% 면을 채운다.

### 카드 (양자택일)
장면 제목(`headline`) 아래 두 선택지를 위아래로 두고 사이를 "또는" 절취선으로 나눈다. 고르면 강조색으로 채워진 뒤 200ms 만에 고른 쪽 반대 방향으로 빠지고, 다음 카드가 260ms 동안 들어온다(ease-out). 진행은 16개 점으로만 보여 준다(번호 매기기 금지).

### 탑승객 표 (후보)
본문 · 절취선 · 버튼 칸. 1위만 색을 뒤집는다. 이름은 `Gowun Batang`, 자기소개는 전체 잉크, 숫자(성향 유사도·궁합 점수)는 보조 줄에.

### 일정표 슬립 (48시간)
호감도 막대 두 줄(나 → 상대는 잉크, 상대 → 나는 강조색, 커플 기준선은 종이색 세로선) + 시간별 줄이 1.3초 간격으로 켜진다. 마지막 줄은 잉크 바탕 결과 띠.

### 로직 공개 단계
왼쪽 설명(4) : 오른쪽 표·막대(7). 0.9초 간격으로 한 단계씩 올라온다. "한 번에 보기"와 "다시 재생"을 늘 둔다.

### 움직임
- 감속 곡선 `cubic-bezier(0.22, 1, 0.36, 1)`(들어오고 나감), `cubic-bezier(0.76, 0, 0.24, 1)`(화면 안에서 움직임). `ease-in` 금지, `transition: all` 금지, `transform`·`opacity`·`clip-path` 만 움직인다.
- 사진은 위에서 아래로 열리고(`clip-path`), 큰 사진은 24초에 걸쳐 6% 천천히 확대된다.
- 끝은 커튼 바닥: 본문이 위로 걷히며 탑승권 뒷면(바닥글)이 드러난다.
- `prefers-reduced-motion: reduce` 에서는 이동 없이 바로 보인다.

## Do's and Don'ts

### Do:
- **Do** 새 화면을 탑승권·떼어 내는 부분·일정표 슬립 중 하나로 만든다.
- **Do** 도시를 추가할 때 네 곳을 함께 고친다: `docs/app-logic.js` 의 `CITIES`(온도 구간, 이름, 공항 코드, 분위기 문장), `docs/app.html` 의 `html[data-city]` 색 블록과 `PHOTOS`, 사진 2장 + `docs/assets/credits.json`, 이 문서의 Colors.
- **Do** 사진은 실제 그 도시의 공개 라이선스 사진만 쓰고 바닥글에 출처를 남긴다(`assets.mjs --get`).
- **Do** 고친 뒤 `lint.mjs` 와 `inspect.mjs` 실패 0, `node tests/flow.mjs` 로 세 도시 흐름을 눌러 보고 스크린샷을 `docs/design-ref/` 와 비교한다.

### Don't:
- **Don't** 제목 위에 작은 라벨(eyebrow)을 단다.
- **Don't** 고정폭 글꼴, 01/02/03 번호, 얇은 구분선, 1px 테두리 상자를 쓴다(실제 표의 칸 선은 예외).
- **Don't** 그라데이션(배경·버튼·글자), 쉬고 있는 요소의 그림자, 유리 효과(배경 흐림), 둥근 알약 모양 탭을 쓴다.
- **Don't** 보라색·남색 강조, 노란 크림 바탕에 테라코타 조합을 쓴다.
- **Don't** 이모지나 아이콘 카드 줄로 빈자리를 채운다. 비면 크기를 키우거나 사진을 넣는다.
- **Don't** 가상 인물의 후기·통계·성공 사례를 지어낸다.
