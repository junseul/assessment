# WorkSync 설계서

## 승인된 구현 범위

- Django 기반 WorkSync 초기 프로젝트
- 이메일 기반 로그인/로그아웃
- 로그인 사용자용 주간 업무 대시보드 셸
- 관리자용 사용자 생성, 사용자 목록, 본인 비밀번호 변경
- PostgreSQL `worksync` 전용 사용자 테이블
- 기존 `exitinterview.accounts_user` 계정의 명시적 초기 이관
- 프로젝트 전용 Podman 이미지, 컨테이너, Static/Media Volume

## 데이터 및 권한 원칙

- WorkSync 계정은 `worksync` DB에 독립 저장한다.
- 기존 로그인 계정은 `import_legacy_users` 관리 명령으로만 가져온다.
- 비밀번호는 Django 해시를 그대로 이관하며 평문으로 조회하거나 저장하지 않는다.
- 일반사용자는 주간 업무 화면만 접근한다.
- 관리자와 시스템 관리자는 관리자 설정에 접근한다.
- 별도 JSON API 없이 Django View/Form/Template를 사용한다.
- 운영 Migration과 계정 이관은 자동 실행하지 않는다.

## 운영 식별정보

- 프로젝트 슬러그: `worksync`
- Django 프로젝트 모듈: `config`
- 기본 앱: `core`
- 이미지: `worksync-django`
- 컨테이너: `worksync-web`
- 외부 포트: `60002`
- PostgreSQL 네트워크: `review360-net`
