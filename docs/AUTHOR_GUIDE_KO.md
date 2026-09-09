# FAB Author 0.4.0 — 모델을 텍스트 명세와 에셋으로 만들기

Blender 4.3.0에서 검증했습니다. **N → FAB Author**를 엽니다. 네트워크, Codex, MCP, 외부 Python 패키지는 필요하지 않습니다. 기존 장면 조립 도구는 **FAB Kit** 탭에 있습니다.

## 먼저 예제로 익히기

1. 빈 Scene에서 **1 Setup → Try AMMR Example**을 누릅니다. 기존 초안이 있으면 **New Asset Draft**로 새 초안을 시작합니다. 이전 초안은 Blender Text block에 보관되고 장면의 원본·프리뷰는 유지됩니다.
2. **3 Review**에서 38개 부품과 오류 수를 확인하고 **Generate New Preview**를 누릅니다.
3. **2 Parts**에서 부품을 선택해 치수·재질을 바꾸고 다시 프리뷰를 만듭니다. 이전 프리뷰도 남습니다.
4. **Export JSON**으로 내보낸 후 **Import JSON**으로 다시 불러와 봅니다. `.json`은 기계 판독용이고 함께 생성되는 `.summary.txt`는 사람용 요약입니다. 모델 재생성에는 JSON 전체가 필요합니다.

## 시나리오 A — CAD에서 가져온 모델의 부품 측정

### 1 Setup: 먼저 좌표계 설정

원본이 있는 `.blend`를 다른 이름으로 저장한 뒤 시작합니다. 모델 전체 또는 대표 부품을 선택할 수 있어야 합니다. Collection instance는 작업용 복사본을 개별 객체로 만든 뒤 사용합니다.

- **Asset name / Asset type:** Equipment, AMR, AMMR, Robot Arm, Humanoid, OHT 중 선택합니다. 타입은 추천 부품과 라이브러리 분류를 결정합니다.
- **Meters / Blender unit:** 1 BU가 1 m이면 `1`, 1 BU가 1 mm이면 `0.001`입니다. **Use Scene Unit Scale**은 Scene의 Unit Scale을 읽습니다. CAD가 이미 미터로 변환되었다면 다시 0.001을 곱하지 마세요. 알고 있는 치수 한 개로 확인합니다.
- **Reference rotation:** 내보내는 모델의 위는 +Z, 전면은 -Y입니다. **Use Active Object Orientation**은 활성 객체의 회전만 가져옵니다. 형상과 객체 축이 다르면 직접 회전을 입력합니다.
- **Reference origin:** 전체 모델을 선택하고 **Origin at Selection Floor**로 전체 폭·깊이 중앙의 바닥에 원점을 둡니다. 특정 기준점이 필요하면 3D Cursor를 옮기고 **Origin at 3D Cursor**를 누릅니다.
- **Show Frame Axes:** 내보내기 기준 축을 확인합니다. 가이드는 렌더되지 않습니다.

측정 이후에는 좌표계가 잠깁니다. 다른 기준으로 처음부터 만들려면 **New Asset Draft**를 사용합니다. 같은 ID의 수정 명세를 불러오면 이 장면의 좌표계·원본 연결을 유지합니다. 다른 ID는 새 명세로 취급하고 기준을 초기화합니다.

### 2 Parts: 선택 → 역할 → 측정

1. 예: AMMR의 베이스를 이루는 객체를 모두 선택합니다. 수십 개 CAD 객체를 한 부품으로 묶어 측정할 수 있습니다.
2. **Add Base** 또는 **Add role → Add Component**를 누릅니다. 목록의 이름을 `Drive chassis`처럼 기능이 드러나게 바꿉니다.
3. **Axes**에서 `Active object axes` 또는 `Asset axes`를 선택하고 **Measure Selection**을 누릅니다. 위치·회전·실제 evaluated mesh의 외곽 치수를 읽습니다. 부모 transform, scale, modifier 결과가 반영됩니다.
4. **Size (m)**에서 알려진 치수와 일치하는지 확인합니다. **Show Assigned**로 연결된 원본을 다시 선택하고 **Refresh**로 변경된 원본을 재측정합니다.
5. 직접 입력하려면 크기와 **Position / rotation**을 채우고 **Use Entered Values**를 누릅니다. 측정한 수치도 직접 수정할 수 있습니다.
6. **Shape**를 선택합니다. Box, Cylinder, Ellipsoid, Taper, Profile, Path를 지원합니다. Cylinder 축은 부품 local Z입니다. 치수 입력은 m, 회전 UI와 JSON은 도입니다.
7. **Shape / material details**에서 FAB 재질 역할, bevel 비율, 특징 메모를 설정합니다. Bevel은 가장 짧은 변에 대한 비율입니다. Path radius는 m 단위입니다.
8. 바퀴·센서·팔 링크·관절·그리퍼 등 알아보는 데 필요한 부품을 반복합니다. 역할 추천은 가이드이며 누락 경고만 표시합니다.

목록의 체크박스를 끄면 그 부품을 생성에서 제외합니다. 체크 아이콘은 측정/수동 확인 여부입니다. Remove는 초안 부품만 지웁니다. 원본 객체 연결은 로컬 `.blend`에 저장되며 JSON에는 원본 파일 경로나 객체 이름이 자동으로 포함되지 않습니다. **.blend를 저장해야 다음 작업 때 연결과 초안이 유지됩니다.**

### 단면, 배관, 관절을 더 자세히 전달하기

- **Profile:** 부품 local XY에 놓인 평면 외곽선이 필요합니다. 작업용 메시의 Edit Mode에서 단순한 닫힌 edge loop 하나를 선택하고 **Capture Selected Edges**를 누릅니다. 오목한 외곽도 가능하며 Size Z만큼 두께를 줍니다. CAD의 구멍 수백 개나 모든 경계를 함께 선택하지 않습니다.
- **Path:** Edit Mode에서 한 줄로 연결된 edge chain을 선택합니다. 포인트 위치와 굵기로 케이블·파이프를 생성합니다. 분기한 경로는 부품을 나눕니다.
- 최대 256개 점입니다. 닫힌 Path는 마지막 닫힘 점을 포함하므로 고유 점은 최대 255개입니다. 단면에 구멍을 뚫는 boolean 기능은 이 버전에 없습니다.
- **Joint / axes:** 3D Cursor를 관절 중심에 두고 **Joint Center from Cursor**를 누릅니다. 회전축 방향을 가진 객체를 활성화하고 X/Y/Z를 선택해 **Read Active Local Axis**를 누릅니다. **Show Joint Axis**로 확인합니다.
- Parent는 부품 관계를 기록합니다. 모든 부품 위치·회전과 관절 중심·축은 asset 기준의 절대값입니다. 부모 변환을 중복 적용하지 않습니다. 관절 데이터는 현재 포즈를 설명하며 rig나 애니메이션을 만들지 않습니다.

### 3 Review: 확인 후 텍스트 전달

**Recognizable features**에는 반드시 남겨야 할 실루엣·기능을, **Omit / simplify**에는 단순화할 요소를 적습니다. Blocking issues가 0이면 **Generate New Preview**를 사용합니다. 프리뷰는 명세만으로 만들어지므로 추출이 충분한지 원본 옆에서 확인할 수 있습니다.

좌표·치수·회전·관절·단면·경로는 정밀 값을 유지해 JSON에 담습니다. 선택 객체의 모든 폴리곤을 덤프하거나 자동으로 부품 기능을 판별하지는 않습니다. 필요한 부품 역할과 재현 방식을 사용자가 지정합니다.

**Export JSON**, **Copy JSON**, **Create Text Block**을 지원합니다. 전송은 사용자가 직접 합니다. 생성 도구에 JSON 전체와 원하는 표현을 전달하면 동일 schema의 수정 recipe 또는 개별 FAB Author `.blend` 에셋을 받을 수 있습니다. JSON을 임의 실행 코드로 해석하지 않습니다. 최대 2 MB, 256개 부품입니다.

## 시나리오 B — 돌아온 결과를 에셋으로 등록

1. **4 Library → Local Library**에서 설치 디렉터리 밖의 쓰기 가능한 전용 폴더를 고릅니다. 기존 파일이 없는 새 폴더로 시작하는 것이 편합니다.
2. 수정된 **JSON recipe**를 받았다면 **3 Review → Import JSON/Paste JSON → Generate New Preview**로 확인하고 **4 Library → Save Asset + Thumbnail**을 누릅니다. 이 버튼은 현재 초안에서 모델을 다시 생성합니다. 뷰포트에서 손으로 바꾼 프리뷰 메시를 저장하는 버튼이 아닙니다.
3. 완성된 **개별 FAB Author `.blend`**를 받았다면 **Import Author .blend**로 등록합니다. recipe를 재생성하지 않고 파일에 들어 있는 형상을 유지합니다. FAB Author 메타데이터가 포함된 한 개의 에셋 collection 파일이어야 합니다. 일반 CAD 파일이나 여러 장면을 포함한 작업용 `.blend`는 대상이 아닙니다.
4. **FAB Kit → Add Assets**에서 이름을 검색해 기존 에셋처럼 배치합니다. 또는 Asset Browser의 **FAB Local Assets**를 선택해 썸네일을 드래그합니다. 라이브러리를 바꾼 뒤 No items가 보이면 왼쪽 **All**을 눌러 이전 카탈로그 필터를 해제합니다. 최초 등록 뒤 Preferences의 **Save Preferences**를 사용하면 경로를 확실히 저장할 수 있습니다.
5. 같은 ID를 저장하면 새 파일이 만들어지고 FAB Kit 목록은 최신 버전을 가리킵니다. 기존 장면에 이미 배치한 모델은 바뀌지 않습니다. 필요할 때 Replace Model로 교체합니다. Blender Asset Browser에는 보존된 이전 revision도 보일 수 있습니다.

저장 중에는 작은 프리뷰를 렌더하고, 설치된 Blender를 별도 백그라운드 프로세스로 실행해 썸네일을 포함합니다. 첫 저장은 shader 준비로 잠시 걸릴 수 있습니다. 새 프로그램이나 패키지를 설치하지 않습니다. 애드온 업데이트 ZIP과 로컬 라이브러리를 분리해 관리하십시오. 다른 PC로 옮길 때는 라이브러리 폴더 전체 또는 개별 에셋 `.blend`를 옮깁니다.

## 문제 해결

| 증상 | 확인할 것 |
|---|---|
| 크기가 1,000배 차이 | BU당 미터 값과 CAD import 시 이미 적용된 변환을 확인. 새 초안으로 재측정 |
| 회전된 부품이 너무 크게 측정됨 | Active object axes의 방향이 형상과 일치하는지 확인. 필요하면 수동 회전/치수 또는 Profile 사용 |
| Flat selection 오류 | 두께 없는 메시. 수동으로 nonzero 두께를 입력하거나 Profile 사용 |
| Refresh 실패 | 원본 삭제·다른 Scene 이동 여부 확인. 다시 선택 후 Measure Selection |
| 단면 캡처 실패 | 연결된 단일 평면 경계인지, local XY 방향인지 확인. 교차·여러 경계·분기 불가 |
| 붙여넣기 실패 | 사람용 summary가 아닌 JSON 전체인지, schema_version=1인지 확인. 파일 Import 대안 사용 |
| Library 버튼 비활성 | Local Library 폴더와 Object Mode 확인 |
| 에셋 썸네일 저장 실패 | 폴더 쓰기 권한과 설치 Blender 실행 권한 확인. 실패하면 기존 index는 유지됨 |

측정값의 정확성과 형상 재현의 완전성은 별개입니다. 복잡한 CAD 외형을 박스 하나로 측정하면 같은 치수의 박스가 나옵니다. 중요한 실루엣을 부품·단면으로 추가하고, 결과 프리뷰를 보고 재질과 detail을 조정하는 방식입니다.
