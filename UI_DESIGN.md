\# UI/UX 구현 기본 지침



이 프로젝트의 UI를 구현하거나 수정할 때 아래 규칙을 반드시 준수한다.



\## 1. UI 구현 방식



UI를 임의로 디자인하지 않는다.



검증된 SaaS/B2B 웹 애플리케이션 디자인 패턴을 사용한다.



주요 참고 방향:



\* Linear

\* Vercel Dashboard

\* Notion

\* Stripe Dashboard

\* shadcn/ui



특정 서비스를 그대로 복제하지 말고 다음 요소만 참고한다.



\* Layout

\* Spacing

\* Typography hierarchy

\* Card structure

\* Table structure

\* Navigation

\* Form layout

\* Modal/Dialog

\* Button hierarchy

\* Empty state

\* Loading state



\---



\## 2. 구현 전에 화면 구조부터 분석



새로운 페이지를 구현할 때 바로 코드를 작성하지 않는다.



먼저 다음을 정의한다.



1\. 페이지 목적

2\. 주요 사용자 행동

3\. 정보 우선순위

4\. 페이지 Layout

5\. 필요한 Component

6\. Desktop / Mobile 대응

7\. 기존 Component 재사용 여부



그 후 구현한다.



\---



\## 3. 디자인 시스템 통일



프로젝트 전체에서 다음 항목을 통일한다.



\### Spacing



가능하면 다음 간격 체계를 사용한다.



\* 4px

\* 8px

\* 12px

\* 16px

\* 24px

\* 32px

\* 48px



임의의 margin/padding 값을 남발하지 않는다.



\### Border Radius



동일 종류의 Component는 동일한 radius를 사용한다.



\### Typography



명확한 hierarchy를 유지한다.



예:



\* Page Title

\* Section Title

\* Card Title

\* Body

\* Secondary Text

\* Caption



한 화면에서 지나치게 많은 font-size를 사용하지 않는다.



\### Color



색상을 장식 목적으로 남발하지 않는다.



색상은 다음 용도를 중심으로 사용한다.



\* Primary action

\* Status

\* Warning

\* Error

\* Success

\* Selected state



\---



\## 4. Component 우선 구현



페이지별 HTML을 반복 작성하지 않는다.



공통 Component를 우선 사용한다.



예:



\* AppShell

\* Sidebar

\* Header

\* PageHeader

\* Card

\* StatCard

\* DataTable

\* FormField

\* Button

\* Modal

\* Tabs

\* Badge

\* EmptyState

\* Pagination

\* SearchInput



같은 UI가 2회 이상 사용되면 공통 Component화를 검토한다.



\---



\## 5. UI Library



가능하면 다음 우선순위를 따른다.



1\. shadcn/ui

2\. Radix UI

3\. Tailwind CSS



이미 존재하는 검증된 Component를 우선 사용한다.



Button, Dialog, Dropdown, Tooltip, Tabs, Select 등을 임의로 새로 만들지 않는다.



\---



\## 6. 관리자/B2B 화면 원칙



이 프로젝트는 장식적인 Landing Page보다 업무용 SaaS UI를 우선한다.



다음 특성을 유지한다.



\* 높은 정보 가독성

\* 명확한 hierarchy

\* 과도하지 않은 whitespace

\* 일정한 alignment

\* 데이터 비교가 쉬운 구조

\* 일관된 상태 표시

\* 불필요한 animation 최소화



Gradient, Glassmorphism, 과도한 Shadow 사용을 피한다.



\---



\## 7. Dashboard



Dashboard는 다음 구조를 기본으로 검토한다.



Page Header



↓



KPI / Summary Cards



↓



Chart / 주요 현황



↓



Table / Activity / 상세 데이터



KPI Card는 다음 정보를 명확히 분리한다.



\* Label

\* Value

\* Comparison

\* Trend

\* Supporting information



\---



\## 8. Table



업무 시스템의 Table은 특히 중요하다.



다음을 고려한다.



\* Column alignment

\* Header readability

\* Row height

\* Status Badge

\* Hover

\* Sorting

\* Filtering

\* Search

\* Pagination

\* Empty State



Table 내부에 불필요한 Button을 많이 배치하지 않는다.



Secondary action은 Dropdown Menu 사용을 검토한다.



\---



\## 9. Form



Form은 입력 순서를 기준으로 그룹화한다.



관련 Field를 Section으로 묶는다.



가능하면 다음 순서를 사용한다.



Label



Input



Helper Text / Error



Required 표시를 통일한다.



Form 전체를 하나의 거대한 Card 안에 몰아넣지 않는다.



\---



\## 10. 구현 후 UI Review



화면 구현 후 반드시 스스로 UI Review를 수행한다.



다음 항목을 검사한다.



\* alignment가 맞는가

\* spacing이 일관적인가

\* font hierarchy가 명확한가

\* 같은 기능의 Button 스타일이 동일한가

\* Card 스타일이 통일되어 있는가

\* border가 과도하지 않은가

\* shadow가 과도하지 않은가

\* 정보 밀도가 적절한가

\* 주요 Action이 명확한가

\* Desktop 화면에서 지나치게 넓게 늘어나지 않는가

\* Mobile에서 layout이 무너지지 않는가



문제가 발견되면 구현 완료로 판단하지 말고 수정한다.



\---



\## 11. 금지 사항



다음을 피한다.



\* 페이지마다 다른 디자인 스타일

\* 임의의 color 값

\* 임의의 spacing 값

\* 지나치게 큰 제목

\* 지나치게 둥근 Card

\* 모든 요소에 Shadow 사용

\* 모든 내용을 Card로 감싸기

\* 의미 없는 Gradient

\* 필요 없는 Animation

\* 지나치게 큰 빈 공간

\* Emoji를 UI Icon으로 사용

\* 서로 다른 Icon library 혼용



\---



\## 12. 기존 UI 개선 시



기존 화면을 수정할 경우 기능을 유지하면서 다음 순서로 개선한다.



1\. Layout

2\. Information hierarchy

3\. Spacing

4\. Typography

5\. Component consistency

6\. Color

7\. Interaction

8\. Responsive



기능 코드를 필요 이상으로 변경하지 않는다.



UI 개선 때문에 Backend/API 동작을 변경하지 않는다.



