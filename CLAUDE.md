\# Project Instructions



Claude Code는 작업을 시작하기 전에 반드시 아래 문서를 확인하고 준수한다.



\## 1. 기본 개발 규칙



프로젝트의 전체 개발 원칙, 구조, 구현 순서, 금지사항 및 코딩 규칙은 `AGENTS.md`를 따른다.



모든 작업 시작 전에 `AGENTS.md`를 먼저 읽는다.



다음 작업에서는 `AGENTS.md`의 내용을 최우선으로 참고한다.



\* 요구사항 분석

\* 프로젝트 구조 변경

\* Backend 개발

\* Frontend 개발

\* Database 설계

\* API 설계

\* Refactoring

\* 신규 기능 구현

\* 기존 기능 수정

\* 테스트 및 검증



`AGENTS.md`와 현재 구현 방식이 충돌할 경우 `AGENTS.md`를 우선한다.



\---



\## 2. UI/UX 개발 규칙



UI 또는 UX와 관련된 작업을 수행할 때는 반드시 `UI\_DESIGN.md`를 추가로 읽고 준수한다.



다음 작업은 `UI\_DESIGN.md`를 기준으로 한다.



\* 신규 화면 개발

\* 기존 화면 개선

\* Dashboard

\* Sidebar

\* Header

\* Navigation

\* Card

\* Table

\* Form

\* Modal

\* Dialog

\* Button

\* Tabs

\* Typography

\* Spacing

\* Color

\* Responsive Layout

\* Component 디자인

\* 화면 배치 및 정보 구조



UI를 임의로 디자인하지 않는다.



기존 프로젝트의 공통 Component와 `UI\_DESIGN.md`에 정의된 디자인 시스템을 우선 사용한다.



\---



\## 3. 문서 우선순위



일반적인 개발 작업:



`AGENTS.md` → 기존 프로젝트 구조 및 코드



UI/UX 작업:



`AGENTS.md` → `UI\_DESIGN.md` → 기존 공통 UI Component → 기존 화면



UI 작업에서도 기능, 데이터 구조, API, 프로젝트 아키텍처에 관한 규칙은 `AGENTS.md`를 따른다.



디자인, Layout, Component 표현 방식, Spacing, Typography 등에 관한 규칙은 `UI\_DESIGN.md`를 따른다.



\---



\## 4. 작업 절차



새로운 기능이나 화면을 구현할 때 다음 순서를 따른다.



1\. `AGENTS.md` 확인

2\. 작업 요구사항 분석

3\. UI 작업이 포함되어 있으면 `UI\_DESIGN.md` 확인

4\. 기존 코드 및 공통 Component 확인

5\. 재사용 가능한 기능과 Component 확인

6\. 구현

7\. 기능 검증

8\. UI 작업이면 UI consistency 검증

9\. 발견된 문제 수정



설계가 필요한 작업에서는 바로 코드를 작성하지 않는다.



먼저 기존 구조와 관련 문서를 확인하고 구현 방향을 결정한 후 작업한다.



\---



\## 5. 기존 구현 우선



새로운 코드나 Component를 만들기 전에 기존 구현을 검색한다.



가능하면 다음을 재사용한다.



\* 공통 Layout

\* UI Component

\* Utility

\* API

\* Service

\* Model

\* Form

\* Table

\* Modal

\* 공통 CSS / Tailwind class

\* Design Token



동일하거나 유사한 기능을 중복 구현하지 않는다.



\---



\## 6. UI 구현 후 검수



UI 변경 작업이 완료되면 `UI\_DESIGN.md`를 기준으로 다음을 확인한다.



\* Layout 일관성

\* Alignment

\* Spacing

\* Typography hierarchy

\* Button hierarchy

\* Card style

\* Table density

\* Form layout

\* Color consistency

\* Border 및 Shadow 사용

\* Component 재사용 여부

\* Desktop responsive

\* Mobile responsive

\* 기존 화면과의 디자인 일관성



문제가 발견되면 수정한 후 작업을 완료한다.



\---



\## 7. 기본 원칙



`AGENTS.md`는 프로젝트 전체 개발 규칙의 기준 문서이다.



`UI\_DESIGN.md`는 UI/UX 구현 및 디자인의 기준 문서이다.



Claude Code는 두 문서를 작업 컨텍스트로 사용하며, 관련 작업을 수행하기 전에 반드시 해당 문서를 확인한다.



