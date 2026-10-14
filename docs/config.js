// 48시간 소개팅 서버 설정 (Supabase). 비워 두면 '데모 모드'로 동작합니다(가입이 이 브라우저에만 저장, 30명 제한 없음).
// url 과 publishable(anon) 키만 넣습니다. 이 두 값은 공개돼도 되는 값이고, 실제 보호는 supabase/schema.sql 의 RLS가 합니다.
// 비밀 키(sb_secret_… / service_role)는 절대 넣지 마세요 — 앱이 감지하면 실행을 멈춥니다.
window.DM_CONFIG = {
  url: "",
  key: ""
};
