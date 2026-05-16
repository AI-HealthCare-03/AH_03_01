# 헬씨루틴 — 프론트엔드

만성질환 생활습관 챌린지 서비스의 Next.js 15 프론트엔드입니다.

## 사전 요구사항

- Node.js 20+
- pnpm 11+

pnpm이 없으면: `npm install -g pnpm`

## 설치 및 실행

```bash
# 1. 의존성 설치
pnpm install

# 2. 환경변수 설정
cp .env.local.example .env.local
# .env.local 파일의 NEXT_PUBLIC_API_BASE_URL 을 백엔드 주소로 변경

# 3. 개발 서버 실행 (http://localhost:3000)
pnpm dev

# 4. 빌드
pnpm build

# 5. 프로덕션 서버
pnpm start
```

## 환경변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `NEXT_PUBLIC_API_BASE_URL` | FastAPI 백엔드 주소 | `http://localhost:8000` |

## 개발 명령어

```bash
pnpm dev        # 개발 서버
pnpm build      # 프로덕션 빌드
pnpm start      # 프로덕션 서버
pnpm lint       # ESLint 검사
pnpm format     # Prettier 포매팅
pnpm typecheck  # TypeScript 타입 검사
```

## 기술 스택

- **프레임워크**: Next.js 15 App Router
- **언어**: TypeScript (strict)
- **스타일**: Tailwind CSS v4
- **폰트**: Pretendard Variable (CDN)
- **서버 상태**: TanStack Query v5
- **클라이언트 상태**: Zustand v5
- **폼**: react-hook-form + zod
- **HTTP**: Axios
- **아이콘**: lucide-react
- **패키지 매니저**: pnpm

## 디렉터리 구조

```
src/
  app/
    (auth)/       # 인증 화면 그룹 (GNB 없음)
    (main)/       # 로그인 후 화면 그룹 (GNB 포함)
  components/
    ui/           # Button, Input, Modal, Badge, Toast, Checkbox
    auth/         # PasswordStrengthBar, DestructiveModal
    layout/       # GNB, SplitAuthShell, SimpleAuthShell, Providers
  lib/
    api/          # client.ts (axios + interceptor), auth.ts
    tokens.ts     # localStorage 토큰 관리
    validators.ts # Zod 스키마 + 유틸
  stores/
    auth.ts       # Zustand 인증 스토어
  hooks/
    useAuth.ts    # 인증 훅
  styles/
    tokens.css    # CSS 변수 디자인 토큰
  types/          # 공통 타입
  constants/      # 상수
```

## 백엔드 연동

백엔드는 `http://localhost:8000` 에서 동작하며 API prefix는 `/api/v1/` 입니다.

백엔드가 아직 구현되지 않은 항목은 코드에 `// TODO(backend): <엔드포인트> 추가 필요` 코멘트로 표시했습니다.

현재 미구현 항목:
- SMS 인증 (`/api/v1/auth/sms/*`)
- 카카오 OAuth (`/api/v1/auth/kakao`)
- 아이디 찾기 (`/api/v1/auth/find-id`)
- 비밀번호 재설정 (`/api/v1/auth/reset-password`)
- 이메일/닉네임 중복 확인 (`/api/v1/auth/check-*`)
- 이전 계정 복원 (`/api/v1/auth/restore`)

> 본 서비스는 의학적 진단을 대체하지 않습니다.
