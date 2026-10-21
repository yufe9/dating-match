---
name: 48시간 소개팅
description: 여행하며 상대를 알아가는 소개팅. 하늘 위에 떠 있는 유리 한 장씩, 그리고 한 장씩 뒤집히는 타로카드.
colors:
  sky: "#aec6e2"
  navy: "#11143a"
  navy-muted: "#3a3f6e"
  rose: "#b52a55"
  hero-ice: "#b8c9ea"
  hero-rose: "#ecb5c3"
  hero-apricot: "#f2c6a6"
  night: "#0d1030"
  hawaii-sky: "#f4a07c"
  hawaii-ink: "#2b0b16"
  hawaii-muted: "#5a2433"
  hawaii-accent: "#a3164f"
  hongkong-sky: "#0f2f3a"
  hongkong-ink: "#f6f2ea"
  hongkong-muted: "#b9cdc9"
  hongkong-accent: "#ff7fa8"
  sapporo-sky: "#d3e5ef"
  sapporo-ink: "#0c1a24"
  sapporo-muted: "#3f5464"
  sapporo-accent: "#9a4c0c"
  tarot-back: "#141a5c"
  error-red: "#b3261e"
typography:
  display:
    fontFamily: "Pretendard Variable, Pretendard, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "clamp(3.375rem, 1.6rem + 7vw, 7.5rem)"
    fontWeight: 680
    lineHeight: 0.95
    letterSpacing: "-0.05em"
  headline:
    fontFamily: "Pretendard Variable, Pretendard, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "clamp(2.125rem, 1.3rem + 3.2vw, 4rem)"
    fontWeight: 680
    lineHeight: 1.1
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Pretendard Variable, Pretendard, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "clamp(1.5rem, 1.2rem + 1vw, 2rem)"
    fontWeight: 680
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  lead:
    fontFamily: "Pretendard Variable, Pretendard, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "clamp(1.25rem, 1.1rem + 0.7vw, 1.625rem)"
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Pretendard Variable, Pretendard, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "clamp(1.0625rem, 1.02rem + 0.2vw, 1.1875rem)"
    fontWeight: 400
    lineHeight: 1.6
  small:
    fontFamily: "Pretendard Variable, Pretendard, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Pretendard Variable, Pretendard, Apple SD Gothic Neo, Malgun Gothic, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0.02em"
rounded:
  input: "14px"
  tarot: "22px"
  panel: "30px"
  sheet: "34px"
  pill: "999px"
spacing:
  gutter: "clamp(16px, 3.2vw, 40px)"
  panel: "clamp(24px, 3.4vw, 44px)"
  section: "140px"
components:
  button-primary:
    backgroundColor: "{colors.rose}"
    textColor: "#ffffff"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    padding: "18px 28px"
  glass-panel:
    textColor: "{colors.navy}"
    rounded: "{rounded.panel}"
    padding: "{spacing.panel}"
  tarot-face:
    textColor: "{colors.navy}"
    typography: "{typography.lead}"
    rounded: "{rounded.tarot}"
  tarot-back:
    backgroundColor: "{colors.tarot-back}"
    textColor: "#ffffff"
    rounded: "{rounded.tarot}"
---

# Design System: 48시간 소개팅

`docs/app.html` 의 디자인 규칙서. 값의 원본은 위 머리말이고, 실제 코드는 `docs/app.html` 맨 위 `:root` 와 `html[data-city=…]` 블록이다. 어긋나면 코드를 기준으로 이 문서를 고친다. 제품 사실은 `PRODUCT.md`.

## Overview

**하늘 위의 유리 한 장씩.** 사용자가 지정한 아티팩트 **Liquid Glass Lab**(굴절 유리, 반사광, 떠다니는 색 덩어리)과 **Anime.js v4 데모판**, 레퍼런스 **danielaristizabal.net**(하늘색 한 면, 비스듬히 겹친 사진 더미, 세로 캡션, 모서리 고정 글자)을 따른다(2026-10-15). 그 전의 탑승권 디자인은 버렸다.

- **대문**(`#intro`): 세 도시의 노을 하늘(위 삿포로 얼음 `hero-ice` → 가운데 홍콩 `hero-rose` → 아래 하와이 `hero-apricot`, 2026-10-21) + 같은 보정을 건 도시 사진 6장 더미 + 광택 로즈 하트 로고 + 큰 글자 `48 HOURS`(남색 채움) / `LOVE TRIP`(로즈 외곽선) + 굴절 유리 카드 한 장. 카드 안에서 소개 → 탑승 수속 → 누구와·나이 → 이상형 월드컵 시작이 바뀐다.
- **이상형 월드컵**(`#cards`): 타로카드 두 장(A·B)이 덱에서 날아와 한 장씩 뒤집힌다. 고르면 고른 카드가 떠올랐다 위로 날아가고 남은 카드는 떨어진다.
- **여행 온도는 글로 알리지 않는다.** 카드를 고르는 동안 하늘색(`data-city`)만 지금 기운 도시 쪽으로 바뀐다. "지금은 홍콩" 같은 문구를 다시 넣지 않는다(사용자 지정: 긴장감).
- **목적지·후보·일정표·로직**: 모두 유리 패널. 궁합 1위 후보는 같은 유리에 강조색 테두리 2px 를 두르고, 채운 버튼은 1위 카드에만 둔다.

## Colors

- 기본 하늘 `sky`, 글자 `navy`·`navy-muted`, 포인트 `rose` 한 색(버튼·하트·LOVE TRIP 외곽선·진행 점).
- **글자색은 잉크(`--ink`)와 뮤트(`--muted`) 두 가지뿐.** 색은 글자가 아니라 면(버튼, 막대, 테두리, 지도 경로)에만 쓴다. 색 면 위에 긴 글을 올리지 않는다.
- 떠다니는 색 덩어리는 2개(`--b1·--b2`, `--b3·--b4`), 중심을 화면 모서리 바깥에 둔다. 밝은 하늘은 명도 75% 이상·채도 75% 이하, 어두운 하늘(홍콩)은 명도 30% 이하.
- 대문 사진 6장에는 같은 보정(`saturate(.72) sepia(.16) contrast(.9) brightness(1.06)`)을 건다. 사진 파일은 바꾸지 않는다.
- **하와이**: 석양 산호빛 하늘 `hawaii-sky`, 글자 `hawaii-ink`·`hawaii-muted`, 강조 `hawaii-accent`, 덩어리 살구·로즈.
- **홍콩**: 유일한 어두운 하늘 `hongkong-sky`. 같은 토큰을 뒤집는다: 유리는 어둡게(`#081a21` 50~62%), 글자는 밝게(`hongkong-ink`·`hongkong-muted`), 강조는 밝게(`hongkong-accent`) + 그 위 글자는 어둡게(`--accent-ink: #1a0610`), 반사광 `--sheen` .12, 덩어리 옥빛·자두(명도 30% 이하).
- **삿포로**: 얼음빛 하늘 `sapporo-sky`, 가로등 같은 강조 `sapporo-accent`, 덩어리 눈·가로등빛.
- 예외: 온도 막대(`.temp-fill`)의 차가움→뜨거움 그라데이션은 데이터라서 유지한다(막대 위에 글자 없음).

### Named Rules
- **도시 색은 `html[data-city]` 블록에서만 바꾼다.** 요소마다 도시 색을 직접 쓰지 않는다.
- **대비 4.5:1.** 잉크·뮤트는 바탕, 바탕 + 덩어리, 그 위 최소 틴트 유리 중 가장 나쁜 면에서 4.5:1 이상(2026-10-21 계산: 뮤트 최저 5.66). 새 색은 넣기 전에 잰다.
- 글자 아래 유리는 블러 16px(굴절 필터, 크롬 계열) / 20px(그 외), 밝은 하늘에서 흰색 40% 이상.
- 바닥글은 도시와 무관한 밤하늘 `night`.

## Typography

**Pretendard 하나만 쓴다**(SIL OFL, `docs/vendor/pretendard/PretendardVariable.woff2`, 가변 굵기 45~920). Google Fonts 를 쓰지 않는다. Apple SD Gothic Neo 파일은 라이선스상 사이트에 올리지 않는다.

- **크기 6단계**(390px → 최대): display 54→120 · headline 34→64 · title 24→32 · lead 20→26 · body 17→19 · small·label 14. 이 밖의 크기를 새로 만들지 않는다.
- **굵기 3종**: 큰 글자(display·headline·title) 680, 강조(lead·body 의 강조, label) 600, 본문·보조 400. 500·620·760 은 쓰지 않는다. 예외는 대문의 그래픽 글자 `48 HOURS / LOVE TRIP`(760) 하나.
- 자간: display −0.05em, headline −0.035em, title −0.025em, lead −0.015em, body −0.005em, small 0, label +0.02em(영문 대문자는 +0.08em).
- 제목은 어떤 너비에서도 두 줄 이하. 한글은 `word-break: keep-all`.
- 숫자는 `tabular-nums`.

## Layout

- 좌우 여백 `spacing.gutter`, 큰 구역 사이 `spacing.section`.
- 대문은 `min-height: max(100svh, 880px)`: 탑승 수속 단계에서도 유리 카드가 잘리지 않게.
- 휴대폰: 대문은 로고 → 큰 글자 → 사진 더미 → 유리 카드 순으로 쌓이고, 첫 화면 안에 시작 버튼이 보여야 한다. 타로카드는 두 장이 나란히 화면 너비를 나눠 쓴다.

## Elevation & Depth

유리가 깊이를 만든다: 안쪽 반사층(inset 그림자 여러 겹) + 아래로 떨어지는 부드러운 그림자 하나 + 포인터를 따라오는 반사광(`--mx --my`, 세기 `--sheen`). 굴절 필터의 안쪽 블러는 16px 이라 굴절은 테두리에서만 보이고 글자 뒤는 흐리다. 굴절(SVG 변위 필터)은 `data-glass` 가 붙은 큰 유리(대문 카드, 목적지 패널, 일정표, 버튼)에만 쓰고, 스크립트가 만드는 패널(후보, 로직 단계)과 3D 로 뒤집히는 타로카드에는 CSS 유리만 쓴다(Chromium 외 브라우저는 블러로 대체).

## Shapes

입력칸 14px, 타로카드 22px, 패널 30px, 대문 카드 34px, 버튼·막대 완전 둥근 알약. 타로카드 앞면은 안쪽 10px 에 얇은 틀을 두르고, 뒷면은 남색 위 하트 무늬 + `48 HOURS`.

## Components

### 이상형 월드컵 (타로카드)
- 장면 제목 위에 로마 숫자(`VII / XVI`), 아래에 진행 점 16개. 카드 앞면: 위 `VII · A`, 가운데 선택지 문장(lead 600), 아래 `이쪽이 더 나답다`.
- 움직임(Anime.js): 두 장이 화면 아래 75% 지점에서 ±16° 기울어진 채 120ms 간격으로 올라오고(720ms, out(4)), 260ms 간격으로 한 장씩 `rotateY 180 → 0` 뒤집힌다(780ms, inOut(3)). 고르면 고른 카드 `scale 1.06`·위로 18px(260ms) → 남은 카드 아래로 떨어지며 사라짐(420ms) → 고른 카드 위로 날아감(480ms) → 다음 두 장.
- 날아오는 중의 클릭은 무시한다(`busy`). 화면에 들어오면 초점은 카드가 아니라 장면 제목에 둔다(카드에 두면 A 를 미리 고른 것처럼 보임).

### 도시 공개 (16번째 카드 → 탑승권)
16번째 카드를 고르면 남은 카드는 떨어지고, 고른 카드가 `rotateY 540`·가로로 늘어나며 사라지고, 유리 탑승권(`#bpass`: BOARDING PASS · 인천 ICN → / 도착지 코드 / 도시 · 48시간, 남색 떼어 내는 부분 FLIGHT 48H GATE 16)이 돌아 나타난다. 도착지 코드와 도시 이름은 `scrambleText` 로 전광판처럼 1.3초 굴러 멈추고, 그 순간(3초) 하늘이 그 도시 색으로 바뀐 뒤 탑승권이 위로 사라지며 결과 화면으로 넘어간다(전체 약 4.7초). 사용자가 세 후보(탑승권·도시 카드 셔플·비행기 창문) 중 고른 연출이다.

### 48시간 여행 (지도 위 이동 경로)
그 도시 사진을 옅게(22%) 깐 유리 지도에 공항 → 6h → 18h → 30h → 42h 곡선 경로. "나"(잉크색)와 상대(강조색, 이름 끝 글자) 두 점이 구간마다 1.1초씩 걷고(상대는 140ms 늦게), 지나온 길은 강조색으로 그려진다(`createDrawable`). 지점에 닿으면 핀이 커지고 말풍선에 무슨 일·왜·호감도 변화가 뜨며, 오른쪽 일정표 줄과 호감도 막대가 함께 바뀐다. 가장자리 지점의 말풍선은 지도 안쪽으로 붙인다(`--tx --ty`). "로직 공개"를 누르면 재생을 건너뛰고 마지막 상태로.

### 후보 얼굴 (AI 가상 얼굴)
후보 카드 왼쪽에 1:1 얼굴 사진(`docs/assets/avatar-{f|m}-{a|b|c}.jpg`, 640px). 사용자가 Gemini 로 만든 AI 가상 얼굴이며, **사람이 아니라 추천 순위 자리에 고정**된다: A(궁합 1위) 단정·따뜻·아이보리, B 밝고 활동적·연하늘, C 세련·개성·차콜. 남녀가 같은 분위기·옷 색을 공유해 성별을 바꿔도 같은 세트로 보인다. 원본(1792×2400)을 위에서 80px 아래부터 1792×1792 로 잘라 Gemini 워터마크가 빠지게 했다. 배경은 사이트 하늘과 같은 하늘색이라 누끼를 따지 않는다. 사진 아래에 늘 "AI 가상 얼굴"을 적고, 지도 위 점에는 쓰지 않는다(사용자 지정). 버튼은 글 아래에 둔다(옆에 두면 글 칸이 너무 좁아짐).

### 대문 움직임
사진 더미 흩어져 쌓임 → 큰 글자 한 글자씩(splitText) → 유리 카드 맺힘 → 로고 스프링 → 공항 코드 스크램블. 마우스를 따라 사진이 `data-depth` 만큼 움직인다(createAnimatable). 시작하면 사진이 위로 흩어지며 카드 화면으로.

### 공통
- 버튼: 알약 + 강조색 단색(대문 시작 버튼은 로즈 단색 + 유리 반사광), 누르면 `scale(.97)`, 마우스 기기에서만 hover 시 밝아지고 화살표가 4px 이동.
- 로직 공개: 유리 패널이 0.9초 간격으로 올라오고 "한 번에 보기"·"다시 재생"을 늘 둔다.
- 움직임 줄이기 설정이면 날아오기·뒤집기·떠다니기를 모두 끄고 바로 보여 준다.

## Do's and Don'ts

### Do:
- **Do** 새 화면도 하늘 + 유리 패널 + Pretendard 로 만든다.
- **Do** 도시를 추가할 때 `app-logic.js` 의 `CITIES`, `app.html` 의 `html[data-city]` 블록(하늘·글자·강조·유리 알파·`--b1~--b4`)과 `PHOTOS`, 사진 2장 + `credits.json`, 이 문서의 Colors 를 함께 고친다.
- **Do** 고친 뒤 `lint.mjs` 실패 0, `inspect.mjs --allow gradient,shadow,glass` 실패 0, `node tests/flow.mjs` 세 도시를 돌리고 `docs/design-ref/` 와 비교한다.

### Don't:
- **Don't** 카드를 고르는 동안 도시 이름이나 온도를 글로 알려 주지 않는다.
- **Don't** Pretendard 외 글꼴, 외부 글꼴 서비스를 추가하지 않는다.
- **Don't** 제목 위에 작은 라벨(eyebrow)을 단다. 고정폭 글꼴을 쓴다.
- **Don't** 이모지로 아이콘을 대신한다. 가상 인물의 후기·통계를 지어낸다.
- **Don't** `transition: all`, `ease-in` 으로 들어오는 움직임, 레이아웃 속성 애니메이션을 쓴다.
