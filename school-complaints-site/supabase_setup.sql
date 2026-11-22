-- =====================================================================
-- 학교 대신 전해드립니다 : Supabase 초기 설정
-- Supabase 대시보드 > SQL Editor 에 통째로 붙여넣고 Run 하세요.
-- (여러 번 실행해도 안전합니다)
-- =====================================================================

-- 1. 민원 테이블 (기존 complaints.csv 의 8개 컬럼과 1:1 대응)
--    ID        -> id
--    날짜      -> submitted_at
--    상태      -> status
--    공감수    -> likes
--    비밀글    -> is_secret
--    담당 부서 -> department
--    요약 내용 -> summary
--    원본 내용 -> original_text
create table if not exists public.complaints (
  id            text primary key,
  submitted_at  text    not null,
  status        text    not null default '접수 완료'
                        check (status in ('접수 완료', '검토 중', '처리 완료')),
  likes         integer not null default 0 check (likes >= 0),
  is_secret     boolean not null default false,
  department    text    not null default '기타',
  summary       text    not null,
  original_text text    not null
);

-- 2. 보안(RLS): 학생용 앱(anon 키)은 "비밀글이 아닌 민원 읽기"만 가능합니다.
--    비밀글 원본은 학생용 앱이 DB에서 아예 받아오지 못합니다.
--    관리자용 앱은 service_role 키를 쓰며, 이 키는 RLS 를 우회해 전체를 다룹니다.
alter table public.complaints enable row level security;

drop policy if exists "anon can read non-secret complaints" on public.complaints;
create policy "anon can read non-secret complaints"
  on public.complaints
  for select
  to anon
  using (is_secret = false);

revoke insert, update, delete on public.complaints from anon;

-- 테이블 권한: 새 Supabase 프로젝트는 기본으로 권한을 주지 않을 수 있어 직접 지정합니다.
-- (학생용 anon 은 읽기만, 어떤 행을 읽을지는 위의 RLS 정책이 결정 / 관리자용 service_role 은 전체)
grant usage on schema public to anon, service_role;
grant select on public.complaints to anon;
grant select, insert, update, delete on public.complaints to service_role;

-- 3. 학생용 앱이 호출하는 함수 2개 (직접 INSERT/UPDATE 는 막고, 이 함수로만 허용)

-- 3-1. 민원 제출: 상태는 항상 '접수 완료', 공감수는 항상 0 으로 저장됩니다.
create or replace function public.submit_complaint(
  p_id           text,
  p_submitted_at text,
  p_is_secret    boolean,
  p_department   text,
  p_summary      text,
  p_original     text
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if p_original is null
     or char_length(trim(p_original)) = 0
     or char_length(p_original) > 10000 then
    raise exception 'invalid complaint text';
  end if;

  insert into public.complaints
    (id, submitted_at, status, likes, is_secret, department, summary, original_text)
  values (
    p_id,
    p_submitted_at,
    '접수 완료',
    0,
    coalesce(p_is_secret, false),
    case when p_department in ('시설관리부', '급식부', '학생생활부', '교무학사부', '행사복지부', '기타')
         then p_department else '기타' end,
    coalesce(p_summary, ''),
    p_original
  );
end;
$$;

-- 3-2. 공감 +1 (동시에 눌러도 정확히 증가), 비밀글에는 적용되지 않습니다.
create or replace function public.add_like(p_id text)
returns void
language sql
security definer
set search_path = public
as $$
  update public.complaints
     set likes = likes + 1
   where id = p_id
     and is_secret = false;
$$;

revoke execute on function public.submit_complaint(text, text, boolean, text, text, text) from public;
revoke execute on function public.add_like(text) from public;
grant  execute on function public.submit_complaint(text, text, boolean, text, text, text) to anon, service_role;
grant  execute on function public.add_like(text) to anon, service_role;

-- (기존 complaints.csv 6건은 이미 Supabase로 이관했습니다. 학생 글이 GitHub 에 올라가지 않도록 이 파일에서는 뺐습니다.)
