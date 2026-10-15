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

  // ================================================================ 여행 카드 → 여행지 → 후보 → 48시간 여행
  // 카드는 '나는 여행 갈 때 어떤가'를 묻습니다. 답은 내 성향(me)이 되고, 같은 값을 상대에게 바라는 값(pref)으로도 씁니다.
  // set 의 키: 척도 항목(주말스타일·음주·운동·연락빈도·반려동물·결혼의향), EI·JP(MBTI 1·4번째 글자), interests·looks(추가),
  // salaryMin, tall(키 차이 나는 구도), ageSpan(내 나이 ± 몇 살), religionNone(종교 없는 사람만)
  var CARDS = [
    { scene: "출발 전, 일정표", a: { text: "분 단위 일정표가 있어야 마음이 놓인다", set: { JP: "J" } },
      b: { text: "비행기표만 있으면 나머지는 가서 정한다", set: { JP: "P" } } },
    { scene: "출발 전, 숙소 예약", a: { text: "잠자리가 여행의 절반, 숙소에 돈을 쓴다", set: { "주말스타일": "집" } },
      b: { text: "숙소는 잠만 자는 곳, 돈은 음식과 체험에", set: { "주말스타일": "밖" } } },
    { scene: "출발 전, 여행 경비", a: { text: "한 번 가는 여행, 좋은 경험엔 아끼지 않는다", set: { salaryMin: "5~7천" } },
      b: { text: "가성비 맛집 찾고 버스 타는 재미가 크다", set: { salaryMin: ANY } } },
    { scene: "공항, 첫 커플 사진", a: { text: "키 차이가 확 나는 구도가 설렌다", set: { tall: true } },
      b: { text: "눈높이가 비슷한 구도가 편하다", set: { tall: false } } },
    { scene: "첫날 아침", a: { text: "해 뜨기 전에 나가 해변을 달린다", set: { "운동": "주3이상" } },
      b: { text: "알람은 끄고 늦잠, 브런치부터 시작한다", set: { "운동": "안함" } } },
    { scene: "첫날 점심", a: { text: "웨이팅 두 시간이어도 소문난 맛집", set: { interests: ["맛집", "와인"] } },
      b: { text: "시장에서 장 봐서 숙소에서 같이 요리", set: { interests: ["요리", "베이킹"] } } },
    { scene: "첫날 오후", a: { text: "서핑이나 트레킹, 몸으로 부딪히는 체험", set: { interests: ["등산", "캠핑", "러닝"] } },
      b: { text: "미술관이나 공연, 천천히 보고 듣는 체험", set: { interests: ["전시회", "공연", "영화"] } } },
    { scene: "첫날 저녁, 마주 앉은 사람", a: { text: "단정하고 깔끔한 셔츠 차림에 눈이 간다", set: { looks: ["단정한", "깔끔한", "차분한", "지적인"] } },
      b: { text: "자유롭고 개성 있는 차림에 눈이 간다", set: { looks: ["개성있는", "밝은", "세련된", "운동하는"] } } },
    { scene: "첫날 밤", a: { text: "현지 바에서 한잔하며 밤을 길게 쓴다", set: { "음주": "자주" } },
      b: { text: "숙소로 일찍 돌아와 내일을 아낀다", set: { "음주": "안마심" } } },
    { scene: "첫날 밤, 숙소 라운지", a: { text: "처음 본 여행자와도 금방 친구가 된다", set: { EI: "E" } },
      b: { text: "둘이서만 조용히 있는 시간이 좋다", set: { EI: "I" } } },
    { scene: "둘째 날 아침 식탁", a: { text: "학창 시절 이야기가 통하는 또래가 좋다", set: { ageSpan: 3 } },
      b: { text: "나이 차가 있어도 대화가 통하면 된다", set: { ageSpan: 7 } } },
    { scene: "둘째 날 오전", a: { text: "반나절쯤은 각자 하고 싶은 걸 한다", set: { "연락빈도": "적게" } },
      b: { text: "48시간 내내 붙어 다니고 싶다", set: { "연락빈도": "자주" } } },
    { scene: "둘째 날 골목길", a: { text: "길고양이만 보여도 멈춰 선다", set: { "반려동물": "좋아함" } },
      b: { text: "동물은 멀리서 보는 게 편하다", set: { "반려동물": "싫음" } } },
    { scene: "둘째 날 오후", a: { text: "사진을 수백 장 남겨야 여행이다", set: { interests: ["사진", "여행"] } },
      b: { text: "폰은 넣어 두고 책 한 권 들고 걷는다", set: { interests: ["독서", "글쓰기"] } } },
    { scene: "해 질 녘, 언덕 위 오래된 성당", a: { text: "조용히 앉아 마음을 고르는 시간이 좋다", set: { religionNone: false } },
      b: { text: "건물만 구경하고 나온다, 신앙 이야기는 부담", set: { religionNone: true } } },
    { scene: "마지막 밤, 모닥불 앞", a: { text: "1~2년 안에 결혼까지 생각하는 연애", set: { "결혼의향": "1~2년내" } },
      b: { text: "좋은 사람이면 언젠가, 지금은 이 여행", set: { "결혼의향": "언젠가" } } }
  ];
  var TALL = { "남": 177, "여": 163 };  // 키 차이 나는 구도: 남성 상대는 이 키 이상, 여성 상대는 이 키 이하
  var SHORTLIST = 5, PICKS = 3;          // 성향 벡터로 5명 추린 뒤 규칙 점수로 3명을 보여 줍니다
  // 웹의 커플 기준. 콘솔은 쌍방 확인(양쪽 85+)을 통과한 쌍만 여행을 보내지만, 웹은 고른 사람과 바로 떠나므로 기준을 낮춥니다.
  // 65,536가지 카드 조합 시뮬레이션: 85점이면 1위와 여행 시 커플 3.7%, 70점이면 22.7% (3명 중 누군가와는 34.8%)
  var COUPLE_MIN = 70;

  // ---------------------------------------------------------------- 여행 온도 → 도시
  // 바깥·술자리·운동·함께·외향·즉흥일수록 뜨겁습니다. 각 0~2점, 합계 0~12점
  var HEAT = [["주말스타일", ["집", "반반", "밖"]], ["음주", ["안마심", "가끔", "자주"]], ["운동", ["안함", "주1~2", "주3이상"]],
    ["연락빈도", ["적게", "보통", "자주"]]];
  var CITIES = [  // 온도 이하이면 그 도시 (차가운 쪽부터)
    { id: "sapporo", name: "삿포로", code: "CTS", max: 4, mood: "차갑고 얼음장 같지만, 따뜻한 구석이 있는 사람" },
    { id: "hongkong", name: "홍콩", code: "HKG", max: 7, mood: "따뜻하지만, 어딘가 시린 구석이 있는 사람" },
    { id: "hawaii", name: "하와이", code: "HNL", max: 12, mood: "석양처럼 뜨겁고 열정적인 사람" }
  ];
  function heat(t) {  // t = 성향 (프로필 한 명 또는 방문자의 me). 모르는 값은 0점
    var h = HEAT.reduce(function (s, x) { return s + Math.max(0, x[1].indexOf(t[x[0]])); }, 0);
    return h + (t.EI === "E" ? 2 : 0) + (t.JP === "P" ? 2 : 0);
  }
  function cityOf(h) { return CITIES.filter(function (c) { return h <= c.max; })[0]; }
  function traitsOf(p) {  // 프로필 → 성향 (방문자 me 와 같은 모양)
    return { "주말스타일": p["주말스타일"], "음주": p["음주"], "운동": p["운동"], "연락빈도": p["연락빈도"],
      "반려동물": p["반려동물"], "결혼의향": p["결혼의향"], EI: p["MBTI"][0], JP: p["MBTI"][3], interests: list(p["관심사"]) };
  }

  // ---------------------------------------------------------------- 카드 답 → 성향(me)·바라는 값(pref)
  function fromAnswers(answers, gender, myAge) {  // answers[i] = "a" | "b"
    var me = { interests: [] }, pref = emptyPref(), tall = false, span = 5, religionNone = false;
    pref.gender = gender;
    CARDS.forEach(function (c, i) {
      var s = (c[answers[i]] || {}).set;
      if (!s) return;
      Object.keys(s).forEach(function (k) {
        var v = s[k];
        if (k === "interests") { me.interests = me.interests.concat(v); pref.interests = pref.interests.concat(v); }
        else if (k === "looks") pref.looks = v.slice();
        else if (k === "salaryMin") pref.salaryMin = v;
        else if (k === "tall") tall = v;
        else if (k === "ageSpan") span = v;
        else if (k === "religionNone") religionNone = v;
        else if (k === "EI") { me.EI = v; pref.mbti[0] = v; }
        else if (k === "JP") { me.JP = v; pref.mbti[3] = v; }
        else { me[k] = v; pref[k] = v; }
      });
    });
    pref.ageMin = String(myAge - span); pref.ageMax = String(myAge + span);
    if (tall) { if (gender === "남") pref.heightMin = String(TALL["남"]); else pref.heightMax = String(TALL["여"]); }
    pref.religionNone = religionNone;
    return { me: me, pref: pref };
  }

  // ---------------------------------------------------------------- 성향 벡터 (웹의 '임베딩')
  // 언어 모델 대신, 카드가 묻는 성향을 -1~1 숫자로 늘어놓은 벡터를 만들고 코사인 유사도를 잽니다
  var VEC_SCALES = ["주말스타일", "음주", "운동", "연락빈도", "반려동물", "결혼의향"];
  var VEC_GROUPS = [["맛집", "와인"], ["요리", "베이킹"], ["등산", "캠핑", "러닝"], ["전시회", "공연", "영화"], ["사진", "여행"], ["독서", "글쓰기"]];
  function vector(data, t) {
    var v = VEC_SCALES.map(function (f) {
      var s = data.SCALES[f], i = s.indexOf(t[f]);
      return i < 0 ? 0 : 2 * i / (s.length - 1) - 1;
    });
    v.push(t.EI === "E" ? 1 : t.EI === "I" ? -1 : 0, t.JP === "P" ? 1 : t.JP === "J" ? -1 : 0);
    VEC_GROUPS.forEach(function (g) {
      v.push(g.some(function (x) { return (t.interests || []).indexOf(x) !== -1; }) ? 1 : 0);
    });
    return v;
  }
  function cosine(a, b) {
    var d = 0, na = 0, nb = 0;
    a.forEach(function (x, i) { d += x * b[i]; na += x * x; nb += b[i] * b[i]; });
    return na && nb ? Math.round(1000 * d / Math.sqrt(na * nb)) / 1000 : 0;
  }

  // ---------------------------------------------------------------- 후보: 도시 → 거르기 → 벡터 5명 → 규칙 점수 3명
  var TRIP_RULES = ["희망 나이", "희망 키", "종교"];
  function tripFails(rule, pref, p) {
    if (rule === "종교") return pref.religionNone && p["종교"] !== "없음";
    return fails(rule, pref, p);
  }
  function candidates(data, me, pref) {
    var h = heat(me), city = cityOf(h);
    var near = { sapporo: ["sapporo", "hongkong", "hawaii"], hongkong: ["hongkong", "sapporo", "hawaii"], hawaii: ["hawaii", "hongkong", "sapporo"] }[city.id];
    var people = data.profiles.filter(function (p) { return p["성별"] === pref.gender; });
    var counts = {}, passed, used = [], pool = [];
    // 같은 도시에서 3명이 안 되면 가까운 도시까지 넓힙니다 (넓힌 사실은 로직 화면에 그대로 보여 줌)
    for (var n = 1; n <= near.length; n++) {
      used = near.slice(0, n);
      pool = people.filter(function (p) { return used.indexOf(cityOf(heat(traitsOf(p))).id) !== -1; });
      TRIP_RULES.forEach(function (r) { counts[r] = 0; });
      passed = pool.filter(function (p) {
        var hit = false;
        TRIP_RULES.forEach(function (r) { if (tripFails(r, pref, p)) { counts[r] += 1; hit = true; } });
        return !hit;
      });
      if (passed.length >= PICKS) break;
    }
    var mv = vector(data, me);
    var sims = passed.map(function (p) { return { p: p, sim: cosine(mv, vector(data, traitsOf(p))) }; })
      .sort(function (a, b) { return (b.sim - a.sim) || (a.p["번호"] < b.p["번호"] ? -1 : 1); });
    var short = sims.slice(0, SHORTLIST);
    var rows = rank(data, pref, short.map(function (x) { return x.p; }));
    rows.forEach(function (r) {
      r.sim = short.filter(function (x) { return x.p === r.p; })[0].sim;
      r.reason = explain(data, pref, r);
    });
    return { heat: h, city: city, cities: used, people: people.length, pool: pool.length, counts: counts,
      passed: passed.length, sims: sims, picks: rows.slice(0, PICKS) };
  }

  // ---------------------------------------------------------------- 48시간 여행 (match.py run_trip 과 같은 규칙)
  function seeded(key) {  // 문자열 → 0~1 난수 (FNV-1a + mulberry32). 같은 키면 같은 여행
    var h = 2166136261;
    for (var i = 0; i < key.length; i++) { h ^= key.charCodeAt(i); h = Math.imul(h, 16777619); }
    return function () {
      h = (h + 0x6D2B79F5) | 0;
      var t = Math.imul(h ^ (h >>> 15), 1 | h);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function eventKind(data, test, me, p, sc) {
    if (test === "운") return "운";
    var d;
    if (data.SCALES[test]) d = data.SCALES[test].indexOf(me[test]) < 0 ? 1 : step(data, test, me[test], p[test]);
    else if (test === "가치관") d = sc["가치관"] === data.MAX["가치관"] ? 0 : sc["가치관"] >= data.MAX["가치관"] / 2 ? 1 : 2;
    else if (test === "관심사") {
      var n = (me.interests || []).filter(function (x) { return list(p["관심사"]).indexOf(x) !== -1; }).length;
      d = n >= 2 ? 0 : n === 1 ? 1 : 2;
    } else d = me.JP === p["MBTI"][3] ? 0 : 2;  // MBTI J/P — 길 잃었을 때 계획파와 즉흥파
    return ["같음", "한칸", "두칸"][Math.min(d, 2)];
  }
  function trip(data, me, row, key) {
    var p = row.p, sc = row.score, theirImp = list(p["중요항목"]);
    var fit = { me: row.affinity, them: affinity(data, { important: theirImp }, sc) };  // 상대는 자기 중요항목을 2.5배로 봅니다
    var rnd = seeded(key + "|" + p["번호"]), first = {}, now = {}, log = [];
    ["me", "them"].forEach(function (who) {  // 첫인상: 방향마다 따로 뽑습니다 (match.py season_score 와 같은 식)
      first[who] = Math.round(10 * (rnd() * 2 - 1) * data.FIRST_IMPRESSION) / 10;
      now[who] = Math.round(10 * Math.min(100, Math.max(0, fit[who] + first[who]))) / 10;
    });
    var start = { me: now.me, them: now.them };
    var pool = data.EVENTS.slice();
    for (var i = pool.length - 1; i > 0; i--) { var j = Math.floor(rnd() * (i + 1)); var t = pool[i]; pool[i] = pool[j]; pool[j] = t; }
    pool.slice(0, data.TRIP_EVENTS).forEach(function (ev, k) {
      var kind = eventKind(data, ev[1], me, p, sc), base = kind === "운" ? 0 : data.TRIP_EFFECT[kind], delta = {}, parts = {};
      ["me", "them"].forEach(function (who) {
        var boost = who === "them" && ev[2] && theirImp.indexOf(ev[2]) !== -1 ? data.IMPORTANT_BOOST : 1;
        var luck = Math.floor(rnd() * (2 * data.TRIP_LUCK + 1)) - data.TRIP_LUCK;
        var next = Math.round(10 * Math.min(100, Math.max(0, now[who] + base * boost + luck))) / 10;
        delta[who] = Math.round(10 * (next - now[who])) / 10;  // 0~100으로 자른 뒤 실제로 바뀐 만큼
        parts[who] = { base: base, boost: boost, luck: luck };
        now[who] = next;
      });
      log.push({ hour: 6 + 12 * k, name: ev[0], test: ev[1], cat: ev[2], kind: kind, delta: delta, parts: parts, now: { me: now.me, them: now.them } });
    });
    return { fit: fit, first: first, start: start, log: log, end: now,
      couple: Math.min(now.me, now.them) >= COUPLE_MIN, theirImportant: theirImp };
  }

  var api = { RULES: RULES, ANY: ANY, list: list, filter: filter, score: score, total: total, affinity: affinity,
    rank: rank, explain: explain, match: match, emptyPref: emptyPref, sharedInterests: sharedInterests,
    CARDS: CARDS, CITIES: CITIES, TALL: TALL, heat: heat, cityOf: cityOf, traitsOf: traitsOf, fromAnswers: fromAnswers,
    vector: vector, cosine: cosine, candidates: candidates, trip: trip, COUPLE_MIN: COUPLE_MIN };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Match48 = api;
})(this);
