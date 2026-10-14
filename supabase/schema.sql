-- 48시간 소개팅 가입 정원(30명) 관리
-- Supabase 대시보드 → SQL Editor 에 이 파일 전체를 붙여넣어 실행합니다. 여러 번 실행해도 안전합니다.
-- 실행한 뒤 입장 코드를 정합니다(이 파일에는 넣지 마세요 — 저장소가 공개입니다):
--   update public.dm_settings set code = '수업에서-알려줄-코드' where id = 1;
--
-- 개인정보 보호 설계
--   * dm_members·dm_settings 표에는 RLS를 켜고 정책을 하나도 주지 않습니다 → 방문자(anon)는 직접 읽기·쓰기가 전혀 안 됩니다.
--   * 방문자는 두 함수만 부를 수 있습니다: dm_signup(가입/재입장), dm_count(현재 인원 수).
--   * dm_signup은 입장 코드가 틀리면 학번을 보기도 전에 같은 답(bad_code)만 돌려줍니다.
--     → 코드를 모르는 외부인은 "이 학번이 가입했는지"를 알아낼 수도, 가짜 학번으로 정원을 채울 수도 없습니다.
--   * 두 함수 모두 다른 사람의 학번·이름을 돌려주지 않습니다. 명단은 대시보드(Table Editor)에서 주인만 봅니다.
--   * 과제가 끝나면: truncate table public.dm_members;  (또는 프로젝트 삭제)

create table if not exists public.dm_members (
  slot        int primary key check (slot between 1 and 30),
  student_id  text not null unique check (student_id ~ '^[0-9]{6,12}$'),
  name        text not null check (char_length(name) between 2 and 20),
  created_at  timestamptz not null default now()
);

create table if not exists public.dm_settings (
  id    int primary key check (id = 1),
  code  text  -- 입장 코드. 비어 있으면 아무도 가입할 수 없습니다
);
insert into public.dm_settings (id, code) values (1, null) on conflict (id) do nothing;

alter table public.dm_members enable row level security;
alter table public.dm_settings enable row level security;
-- 정책 없음 = anon/authenticated 모두 접근 불가 (의도한 것입니다. 정책을 추가하지 마세요)
revoke all on table public.dm_members from anon, authenticated;
revoke all on table public.dm_settings from anon, authenticated;

drop function if exists public.dm_signup(text, text);

create or replace function public.dm_signup(p_code text, p_student_id text, p_name text)
returns json
language plpgsql
security definer
set search_path = ''
as $$
declare
  want text;
  sid  text := btrim(coalesce(p_student_id, ''));
  nm   text := btrim(coalesce(p_name, ''));
  cur  public.dm_members%rowtype;
  free int;
begin
  -- 입장 코드부터 확인 — 틀리면 학번 조회 없이 같은 답
  select s.code into want from public.dm_settings s where s.id = 1;
  if want is null or want = '' or coalesce(btrim(p_code), '') <> want then
    return json_build_object('ok', false, 'reason', 'bad_code');
  end if;
  if sid !~ '^[0-9]{6,12}$' then
    return json_build_object('ok', false, 'reason', 'bad_id');
  end if;
  if char_length(nm) not between 2 and 20 then
    return json_build_object('ok', false, 'reason', 'bad_name');
  end if;

  -- 동시에 여러 명이 가입해도 31번째가 들어오지 않게 표를 잠그고 셉니다
  lock table public.dm_members in share row exclusive mode;

  select * into cur from public.dm_members m where m.student_id = sid;
  if found then
    if cur.name = nm then  -- 같은 학번·이름이면 재입장
      return json_build_object('ok', true, 'slot', cur.slot, 'again', true,
                               'count', (select count(*) from public.dm_members));
    end if;
    return json_build_object('ok', false, 'reason', 'taken');
  end if;

  -- 비어 있는 가장 작은 번호 (대시보드에서 누군가를 지워도 다음 가입이 깨지지 않게)
  select min(g) into free from generate_series(1, 30) g
   where not exists (select 1 from public.dm_members m where m.slot = g);
  if free is null then
    return json_build_object('ok', false, 'reason', 'full', 'count', 30);
  end if;

  insert into public.dm_members (slot, student_id, name) values (free, sid, nm);
  return json_build_object('ok', true, 'slot', free, 'again', false,
                           'count', (select count(*) from public.dm_members));
end;
$$;

create or replace function public.dm_count()
returns int
language sql
stable
security definer
set search_path = ''
as $$ select count(*)::int from public.dm_members $$;

revoke all on function public.dm_signup(text, text, text) from public;
revoke all on function public.dm_count() from public;
grant execute on function public.dm_signup(text, text, text) to anon, authenticated;
grant execute on function public.dm_count() to anon, authenticated;
