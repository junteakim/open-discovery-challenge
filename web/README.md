# PipeCAD Web

브라우저에서 동작하는 플랜트 배관 CAD입니다. 데스크톱 [PipeCAD](https://github.com/eryar/PipeCAD)의 **공개 기능 명세**(축망, 설비, 구조, 배관, ISO, MTO, PCF)를 웹으로 재구현했습니다. PipeCAD 본체는 오픈소스가 아니므로 원본 바이너리나 플러그인 코드를 포함하지 않습니다.

## 실행

```bash
cd web
npm install
npm test
npm run dev
```

프로덕션 빌드:

```bash
npm run build
npm run preview
```

## 샘플 로그인

원본 PipeCAD Sample과 같습니다.

- 사용자: `SYSTEM`
- 비밀번호: `XXXXXX`

## 기능

| 모듈 | 웹에서 하는 일 |
| --- | --- |
| Design | 3D 뷰, CE 트리, 속성, 리본 |
| Grid | 축망 생성 |
| Equipment | 용기 / 탱크 / 펌프 / 열교환기 + 노즐 |
| Structure | 기둥 / 보 / 플랫폼 |
| Piping | 직교 라우트, 엘보, 게이트/체크 밸브, PCF 입출력 |
| Draft | ISO 축측도 SVG, 평면도, MTO CSV |

조작: 좌클릭 선택, 우클릭/드래그 회전, 휠 줌, `F` 맞춤, `Delete` 삭제, `Esc` 취소.
