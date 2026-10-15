// 웹 흐름 점검: 입장 → 출발 준비 → 카드 16장 → 목적지·후보 → 48시간 여행 → 로직 공개를 브라우저로 눌러 보고 화면마다 스크린샷을 남깁니다.
// 준비: 다른 터미널에서  python -m http.server 8765 --directory docs
// 실행: node tests/flow.mjs [출력 폴더=.taste-skill/flow] [너비=1440] [높이=900] [답 16자, a/b=abaabbabaaabbaab]
// 하와이·홍콩·삿포로를 모두 보려면 답을 바꿔 세 번 돌립니다 (예: abaabbabaaabbaab / abaabaaaabbbaaaa / aaaabaaabbaaaaaa).
// 브라우저는 taste 스킬(.claude/skills/design-taste-frontend)의 cdp.mjs 로 설치된 Chrome/Edge를 씁니다. Node 22 이상.
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const [out = path.join(root, ".taste-skill", "flow"), w = "1440", h = "900", pattern = "abaabbabaaabbaab"] = process.argv.slice(2);
if (!/^[ab]{16}$/.test(pattern)) throw new Error("답은 a/b 16자여야 합니다: " + pattern);
const cdp = path.join(root, ".claude", "skills", "design-taste-frontend", "scripts", "lib", "cdp.mjs");
if (!fs.existsSync(cdp)) throw new Error("taste 스킬이 없습니다. CLAUDE.md 의 설치 명령을 먼저 실행하세요: " + cdp);
fs.mkdirSync(out, { recursive: true });
const { Browser, sleep } = await import(pathToFileURL(cdp).href);

const b = await Browser.launch({ width: +w, height: +h });
const p = await b.newPage({ width: +w, height: +h, mobile: +w < 500, dsf: 1 });
const tag = w + "-" + pattern;
const shot = (name) => p.screenshot({ path: path.join(out, `${tag}-${name}.jpg`), quality: 70 });
const click = (id) => p.eval((x) => document.getElementById(x).click(), id);
try {
  await p.goto("http://127.0.0.1:8765/app.html", { settleMs: 2000 });
  await p.eval(() => { window.__errs = []; window.addEventListener("error", (e) => window.__errs.push(String(e.message))); });
  await p.eval(() => {  // 데모 모드(config.js 가 빈 상태)에서 돌립니다. 가짜 학번은 해시로만 이 브라우저에 남습니다
    document.getElementById("sid").value = "20260000";
    document.getElementById("sname").value = "점검" + Math.floor(Math.random() * 1000);
    document.getElementById("consent").checked = true;
    document.getElementById("gate-btn").click();
  });
  await sleep(800);
  await shot("1-prep");
  await click("prep-btn");
  await sleep(500);
  for (let i = 0; i < 16; i++) {
    if (i === 6) await shot("2-card");
    await click("choice-" + pattern[i]);
    await sleep(520);
  }
  await sleep(1600);
  await shot("3-result");
  await p.eval(() => document.querySelector(".passengers").scrollIntoView());
  await sleep(600);
  await shot("4-passengers");
  await p.eval(() => document.querySelector(".pass .btn").click());
  await sleep(8500);
  await p.eval(() => document.getElementById("trip").scrollIntoView());
  await sleep(500);
  await shot("5-trip");
  await click("logic-btn");
  await sleep(7000);
  await p.eval(() => document.getElementById("logic").scrollIntoView());
  await sleep(400);
  await shot("6-logic");
  const info = await p.eval(() => ({
    errs: window.__errs, city: document.documentElement.dataset.city, verdict: document.getElementById("verdict-a").textContent,
    steps: document.querySelectorAll(".lstep.on").length, overflow: document.documentElement.scrollWidth > window.innerWidth
  }));
  console.log(tag, JSON.stringify(info));
  if (info.errs.length || info.overflow || info.steps !== 6) process.exitCode = 1;
} finally { await b.close(); }
