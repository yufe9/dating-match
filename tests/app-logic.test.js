// 웹 로직(docs/app-logic.js) 자체 점검: node tests/app-logic.test.js
// 먼저 python match.py export 로 docs/profiles.json을 만들어 두어야 합니다.
"use strict";
const assert = require("assert");
const path = require("path");
const M = require("../docs/app-logic.js");
const data = require(path.join(__dirname, "..", "docs", "profiles.json"));

const base = () => Object.assign(M.emptyPref(), { gender: "여" });

// 1) 아무 조건도 고르지 않으면 반대 성별 35명 전원이 통과하고 모두 100점
let r = M.match(data, base());
assert.strictEqual(r.filter.passed.length, 35);
assert(r.rows.every(x => x.total === 100 && x.affinity === 100));

// 2) 고른 성별만 나오고, 항목 점수는 만점을 넘지 않는다
for (const g of ["남", "여"]) {
  r = M.match(data, Object.assign(base(), { gender: g, "음주": "자주", interests: ["등산", "요리"], mbti: ["E", "", "", "J"] }));
  assert(r.rows.every(x => x.p["성별"] === g));
  assert(r.rows.every(x => Object.keys(data.MAX).every(c => x.score[c] >= 0 && x.score[c] <= data.MAX[c])));
}

// 3) '비흡연만'이면 흡연자(가끔·흡연)가 걸러지고, 걸린 인원 = 그 성별의 흡연자 수
const smokers = data.profiles.filter(p => p["성별"] === "남" && p["흡연"] !== "비흡연").length;
r = M.match(data, Object.assign(base(), { gender: "남", smoke: "비흡연만" }));
assert(smokers > 0 && r.filter.counts["흡연"] === smokers);
assert(r.rows.every(x => x.p["흡연"] === "비흡연"));

// 4) 아무도 못 지나가는 조건이면 결과 0명, 이유 없음
r = M.match(data, Object.assign(base(), { ageMin: "60", ageMax: "70" }));
assert.strictEqual(r.rows.length, 0);
assert.strictEqual(r.reason, null);

// 5) 같은 입력이면 순위가 항상 같다 / 중요항목은 호감도만 바꾸고 항목 점수는 그대로
const pref = Object.assign(base(), { "결혼의향": "1~2년내", "자녀계획": "원함", "주말스타일": "밖", interests: ["여행"] });
const a = M.match(data, pref), b = M.match(data, pref);
assert.deepStrictEqual(a.rows.map(x => x.p["번호"]), b.rows.map(x => x.p["번호"]));
const w = M.match(data, Object.assign({}, pref, { important: ["관심사"] }));
const byId = Object.fromEntries(a.rows.map(x => [x.p["번호"], x]));
assert(w.rows.every(x => x.total === byId[x.p["번호"]].total));

// ---------------------------------------------------------------- 여행 카드 흐름
// 6) 카드는 16장 이하, 모두 두 갈래(a·b)이고 각자 바꾸는 값이 있다
assert(M.CARDS.length <= 16);
assert(M.CARDS.every(c => c.scene && c.a.text && c.b.text && c.a.set && c.b.set));

// 7) 모든 가상 인물이 세 도시 중 하나에 배정되고, 도시마다 남녀 모두 있다
const cityIds = M.CITIES.map(c => c.id);
for (const g of ["남", "여"]) {
  const got = new Set(data.profiles.filter(p => p["성별"] === g).map(p => M.cityOf(M.heat(M.traitsOf(p))).id));
  assert.deepStrictEqual([...got].sort(), [...cityIds].sort());
}

// 8) 전부 a / 전부 b / 번갈아 고른 세 경우: 온도는 0~12, 후보는 3명, 같은 답이면 같은 후보
const allA = M.CARDS.map(() => "a"), allB = M.CARDS.map(() => "b"), mix = M.CARDS.map((_, i) => (i % 2 ? "a" : "b"));
for (const ans of [allA, allB, mix]) {
  for (const [g, age] of [["여", 28], ["남", 33]]) {
    const { me, pref } = M.fromAnswers(ans, g, age);
    const h = M.heat(me);
    assert(h >= 0 && h <= 12);
    const c1 = M.candidates(data, me, pref), c2 = M.candidates(data, me, pref);
    assert.strictEqual(c1.picks.length, 3);
    assert(c1.picks.every(x => x.p["성별"] === g));
    assert.deepStrictEqual(c1.picks.map(x => x.p["번호"]), c2.picks.map(x => x.p["번호"]));
    // 9) 48시간 여행: 이벤트 4개, 6·18·30·42시간째, 호감도 0~100, 커플 = 양쪽 최종 웹 기준(M.COUPLE_MIN) 이상, 재현성
    const t = M.trip(data, me, c1.picks[0], ans.join(""));
    assert.deepStrictEqual(t.log.map(e => e.hour), [6, 18, 30, 42]);
    assert(t.log.every(e => e.now.me >= 0 && e.now.me <= 100 && e.now.them >= 0 && e.now.them <= 100));
    assert.strictEqual(t.couple, Math.min(t.end.me, t.end.them) >= M.COUPLE_MIN);
    assert(M.COUPLE_MIN <= data.COUPLE_MIN);  // 웹 기준은 콘솔보다 높을 수 없다
    assert.deepStrictEqual(t, M.trip(data, me, c1.picks[0], ans.join("")));
  }
}
// 10) 가장 뜨거운 답(즉흥·바깥·운동·술자리·외향·붙어 다니기)은 12점 하와이, 반대로 고르면 0점 삿포로
const hot = { 0: "b", 1: "b", 4: "a", 8: "a", 9: "a", 11: "b" };
const hotAns = M.CARDS.map((_, i) => hot[i] || "a"), coldAns = M.CARDS.map((_, i) => (hot[i] ? (hot[i] === "a" ? "b" : "a") : "a"));
assert.strictEqual(M.heat(M.fromAnswers(hotAns, "여", 28).me), 12);
assert.strictEqual(M.heat(M.fromAnswers(coldAns, "여", 28).me), 0);
assert.strictEqual(M.cityOf(12).id, "hawaii");
assert.strictEqual(M.cityOf(0).id, "sapporo");
// 11) 같은 벡터의 코사인 유사도는 1
const v = M.vector(data, M.traitsOf(data.profiles[0]));
assert.strictEqual(M.cosine(v, v), 1);

console.log("웹 로직 자체 점검 통과 (11개)");
