// 48시간 소개팅: 방문자의 '원하는 취향'으로 가상 인물을 거르고 점수를 매기는 순수 로직.
// 점수표·척도는 profiles.json(= python match.py export)에서 받아 파이썬 match.py와 같은 숫자를 씁니다.
// 방문자는 자기 특징을 입력하지 않으므로 거르기는 '내 조건 → 상대' 한 방향만 하고, 2단계(임베딩)는 건너뜁니다.
(function (root) {
  "use strict";

  var ANY = ""; // 빈 값 = 상관없음

  function list(v) {
    return String(v || "").split(";").map(function (x) { return x.trim(); }).filter(Boolean);
  }
  function step(data, field, x, y) {
    var s = data.SCALES[field];
    return Math.abs(s.indexOf(x) - s.indexOf(y));
  }
  function byStep(d, same, one) { return d === 0 ? same : d === 1 ? one : 0; }
  function num(v) { return v === ANY || v == null ? null : Number(v); }

  // ---------------------------------------------------------------- 1) 거르기 (내 조건만)
  var RULES = ["희망 나이", "희망 키", "흡연", "종교", "거주 지역"];

  function fails(rule, pref, p) {
    if (rule === "희망 나이") {
      var a = Number(p["나이"]), lo = num(pref.ageMin), hi = num(pref.ageMax);
      return (lo !== null && a < lo) || (hi !== null && a > hi);
    }
    if (rule === "희망 키") {
      var h = Number(p["키(cm)"]), hlo = num(pref.heightMin), hhi = num(pref.heightMax);
      return (hlo !== null && h < hlo) || (hhi !== null && h > hhi);
    }
    if (rule === "흡연") return pref.smoke === "비흡연만" && p["흡연"] !== "비흡연";
    if (rule === "종교") return pref.religion !== ANY && p["종교"] !== pref.religion;
    if (rule === "거주 지역") return pref.cityOnly && pref.city !== ANY && p["거주_시"] !== pref.city;
    throw new Error(rule);
  }

  function filter(data, pref) {
    var pool = data.profiles.filter(function (p) { return p["성별"] === pref.gender; });
    var counts = {}, passed = [];
    RULES.forEach(function (r) { counts[r] = 0; });
    pool.forEach(function (p) {
      var hit = false;
      RULES.forEach(function (r) { if (fails(r, pref, p)) { counts[r] += 1; hit = true; } });
      if (!hit) passed.push(p);
    });
    return { pool: pool.length, counts: counts, dropped: pool.length - passed.length, passed: passed };
  }

  // ---------------------------------------------------------------- 3) 점수 (원하는 값 vs 상대의 실제 값)
  function sharedInterests(pref, p) {
    var theirs = list(p["관심사"]);
    return pref.interests.filter(function (x) { return theirs.indexOf(x) !== -1; });
  }

  function score(data, pref, p) {
    var P = data.POINTS, M = data.MAX, A = data.AGE_BANDS;
    var marriage = pref["결혼의향"] === ANY ? P["결혼_같음"]
      : byStep(step(data, "결혼의향", pref["결혼의향"], p["결혼의향"]), P["결혼_같음"], P["결혼_한칸"]);
    var kids = pref["자녀계획"] === ANY || pref["자녀계획"] === p["자녀계획"] ? P["자녀_같음"]
      : (pref["자녀계획"] === "모름" || p["자녀계획"] === "모름") ? P["자녀_모름"] : 0;
    var habits = data.HABITS.reduce(function (sum, h) {
      return sum + (pref[h] === ANY ? P["습관_같음"] : byStep(step(data, h, pref[h], p[h]), P["습관_같음"], P["습관_한칸"]));
    }, 0);
    var interests = pref.interests.length === 0 ? M["관심사"]
      : Math.min(sharedInterests(pref, p).length * P["관심사_개당"], P["관심사_최대"]);
    var contact = pref["연락빈도"] === ANY ? P["연락_같음"]
      : byStep(step(data, "연락빈도", pref["연락빈도"], p["연락빈도"]), P["연락_같음"], P["연락_한칸"]);
    var mbti = pref.mbti.reduce(function (sum, ch, i) {
      return sum + ((ch === ANY || ch === p["MBTI"][i]) ? P["MBTI_글자"] : 0);
    }, 0);
    var age = P["나이_0_2"];
    var lo = num(pref.ageMin), hi = num(pref.ageMax);
    if (lo !== null && hi !== null) { // 원하는 나이대의 한가운데에서 얼마나 떨어졌는지
      var gap = Math.abs(Number(p["나이"]) - (lo + hi) / 2);
      age = gap <= A[0] ? P["나이_0_2"] : gap <= A[1] ? P["나이_3_5"] : P["나이_6이상"];
    }
    var home = pref.city === ANY || pref.city === p["거주_시"] ? P["같은구"] : P["다른시"];
    var looks = pref.looks.length === 0 || list(p["외모스타일"]).some(function (x) { return pref.looks.indexOf(x) !== -1; })
      ? P["외모_겹침"] : 0;
    var S = data.SCALES;
    var salaryOk = pref.salaryMin === ANY || S["연봉구간"].indexOf(p["연봉구간"]) >= S["연봉구간"].indexOf(pref.salaryMin);
    var eduOk = pref.edu === ANY || step(data, "학력", pref.edu, p["학력"]) <= 1;
    return {
      "가치관": marriage + kids,
      "생활습관": habits,
      "관심사": interests,
      "성격·소통": contact + mbti,
      "나이": age,
      "거주지": home,
      "외모스타일": looks,
      "경제·학력": (salaryOk ? P["연봉_충족"] : 0) + (eduOk ? P["학력_한단계"] : 0)
    };
  }

  function total(sc) { return Object.keys(sc).reduce(function (s, k) { return s + sc[k]; }, 0); }

  function affinity(data, pref, sc) { // 내 중요항목에 가중치를 준 호감도 (100점)
    var w = function (c) { return pref.important.indexOf(c) !== -1 ? data.WEIGHT_IMPORTANT : 1; };
    var keys = Object.keys(data.MAX), num_ = 0, den = 0;
    keys.forEach(function (c) { num_ += sc[c] * w(c); den += data.MAX[c] * w(c); });
    return Math.round(1000 * num_ / den) / 10;
  }

  function rank(data, pref, passed) {
    var rows = passed.map(function (p) {
      var sc = score(data, pref, p);
      return { p: p, score: sc, total: total(sc), affinity: affinity(data, pref, sc) };
    });
    // 호감도 → 가치관 → 생활습관 → 번호 순 (같은 입력이면 항상 같은 순위)
    rows.sort(function (a, b) {
      return (b.affinity - a.affinity) || (b.score["가치관"] - a.score["가치관"]) ||
        (b.score["생활습관"] - a.score["생활습관"]) || (a.p["번호"] < b.p["번호"] ? -1 : 1);
    });
    rows.forEach(function (r, i) { r.rank = i + 1; });
    return rows;
  }

  // ---------------------------------------------------------------- 4) 이유
  function phrase(cat, pref, p, s, data) {
    var t;
    if (cat === "가치관") {
      var m = pref["결혼의향"] === ANY || pref["결혼의향"] === p["결혼의향"];
      var k = pref["자녀계획"] === ANY || pref["자녀계획"] === p["자녀계획"];
      t = m && k ? "원하는 결혼 시기와 자녀 계획이 같" : m ? "원하는 결혼 시기가 같" : k ? "원하는 자녀 계획이 같"
        : s ? "결혼·자녀 계획이 비슷하" : "결혼·자녀 계획은 다르";
      return [t + "고", t + "습니다"];
    }
    if (cat === "생활습관") {
      var same = data.HABITS.filter(function (h) { return pref[h] !== ANY && pref[h] === p[h]; });
      t = same.length ? "원하는 생활습관(" + same.join("·") + ")과 같" : "생활습관이 비슷하";
      return [t + "고", t + "습니다"];
    }
    if (cat === "관심사") {
      var sh = sharedInterests(pref, p);
      if (!pref.interests.length) return ["관심사는 따로 고르지 않았고", "관심사는 따로 고르지 않았습니다"];
      if (!sh.length) return ["관심사는 겹치지 않고", "관심사는 겹치지 않습니다"];
      return ["관심사 " + sh.length + "개(" + sh.join("·") + ")가 겹치고", "관심사 " + sh.length + "개(" + sh.join("·") + ")가 겹칩니다"];
    }
    if (cat === "성격·소통") return ["연락 빈도와 MBTI가 원하는 쪽에 가깝고", "연락 빈도와 MBTI가 원하는 쪽에 가깝습니다"];
    if (cat === "나이") return [p["나이"] + "세로 원하는 나이대에 잘 맞고", p["나이"] + "세로 원하는 나이대에 잘 맞습니다"];
    if (cat === "거주지") {
      if (pref.city === ANY) return ["사는 곳(" + p["거주_시"] + ")은 상관없다고 했고", "사는 곳(" + p["거주_시"] + ")은 상관없다고 했습니다"];
      if (pref.city === p["거주_시"]) return ["원하는 지역(" + p["거주_시"] + ")에 살고", "원하는 지역(" + p["거주_시"] + ")에 삽니다"];
      return ["원하는 지역과 사는 곳이 다르고", "원하는 지역과 사는 곳이 다릅니다"];
    }
    if (cat === "외모스타일") {
      t = s ? "선호하는 외모 스타일과 맞" : "선호하는 외모 스타일과는 다르";
      return [t + "고", t + "습니다"];
    }
    t = s === data.MAX[cat] ? "원하는 연봉·학력 조건과 맞" : "연봉·학력 조건은 일부만 맞";
    return [t + "고", t + "습니다"];
  }

  function explain(data, pref, row) {
    var keys = Object.keys(data.MAX), sc = row.score;
    var top = keys.slice().sort(function (a, b) {
      return (sc[b] - sc[a]) || (sc[b] / data.MAX[b] - sc[a] / data.MAX[a]) || (keys.indexOf(a) - keys.indexOf(b));
    }).slice(0, 3);
    return top.map(function (c, i) {
      var ph = phrase(c, pref, row.p, sc[c], data);
      return (i === top.length - 1 ? ph[1] : ph[0]) + "(" + sc[c] + "/" + data.MAX[c] + ")";
    }).join(", ") + ".";
  }

  function match(data, pref) {
    var f = filter(data, pref);
    var rows = rank(data, pref, f.passed);
    return { filter: f, rows: rows, reason: rows.length ? explain(data, pref, rows[0]) : null };
  }

  function emptyPref() {
    return {
      gender: "여", ageMin: ANY, ageMax: ANY, heightMin: ANY, heightMax: ANY, smoke: ANY, religion: ANY,
      city: ANY, cityOnly: false, "결혼의향": ANY, "자녀계획": ANY, "음주": ANY, "운동": ANY, "주말스타일": ANY,
      "반려동물": ANY, "연락빈도": ANY, mbti: [ANY, ANY, ANY, ANY], edu: ANY, salaryMin: ANY,
      interests: [], looks: [], important: []
    };
  }

  var api = { RULES: RULES, ANY: ANY, list: list, filter: filter, score: score, total: total, affinity: affinity,
    rank: rank, explain: explain, match: match, emptyPref: emptyPref, sharedInterests: sharedInterests };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Match48 = api;
})(this);
