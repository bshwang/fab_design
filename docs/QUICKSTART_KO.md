# FAB Scene Kit 0.4.0 — 사용법

Blender 4.3용 로컬 FAB 인포그래픽 조립 도구입니다. 모델·템플릿이 설치 ZIP에 포함됩니다. 외부 Python, pip, API 키, MCP, 네트워크 연결은 필요하지 않습니다.

## 설치

1. Blender에서 **Edit → Preferences → Add-ons**를 엽니다.
2. 우측 메뉴의 **Install from Disk**에서 fab_scene_kit-0.4.0.zip을 선택합니다. ZIP을 먼저 풀 필요가 없습니다.
3. 설치한 **FAB Scene Kit**을 활성화합니다.
4. 3D Viewport에서 N을 누르고 **FAB Kit** 탭을 엽니다.

다른 Blender 버전은 호환성 확인 후 사용하십시오. 일반 사용에는 소스 코드 편집이 필요하지 않습니다.

## 모델에서 텍스트 명세 만들기 (0.4.0)

**N → FAB Author**에서 타입·좌표계를 설정하고, 부품을 선택해 **Measure Selection**으로 치수·위치·회전을 읽습니다. 단면·경로·관절 축도 기록할 수 있습니다. **3 Review → Export JSON**으로 전달하고, 돌아온 recipe를 Import JSON으로 확인한 뒤 **4 Library → Save Asset + Thumbnail**로 등록합니다. 완성된 개별 FAB Author `.blend`는 **Import Author .blend**로 추가합니다. [단계별 작성 안내](AUTHOR_GUIDE_KO.md)를 참고하세요. 기본 52개 에셋과 3개 템플릿은 0.3.0 라이브러리를 유지합니다.

## 첫 장면

1. Template에서 **FAB Example**을 선택합니다. Light/Dark를 고르고 **Create New Scene**을 누릅니다.
2. 기존 Scene을 보존하고 독립된 FAB Scene을 만듭니다. 상단 Scene 목록으로 기존 장면으로 돌아갈 수 있습니다.
3. 바닥과 조명·카메라만 필요하면 **Blank Stage**, 장비가 없는 cleanroom은 **FAB Overview**를 선택합니다.
4. 배치 후 테마를 바꿀 때는 Light/Dark 선택 다음 **Apply Theme**를 누릅니다.

## 모델 추가

**버튼으로 추가**

1. Add Assets에서 Category와 Asset을 선택합니다. Search로 이름을 좁힐 수 있습니다.
2. **Add at 3D Cursor**을 누릅니다. 3D Cursor의 XY와 **Place on**에서 고른 높이에 생성됩니다.
3. G로 이동, R Z로 회전합니다. **Rotate 90°**, **Snap to Level**도 사용할 수 있습니다.
4. 기본 장비·사람·로봇은 바닥 기준입니다. OHT와 FFU는 Rail height 기준에 생성됩니다.

**썸네일 드래그앤드롭**

1. **Browse Thumbnails**를 누르면 3D Viewport 아래에 Asset Browser를 엽니다. 충분한 크기의 Asset Browser가 이미 있으면 재사용합니다.
2. Asset Browser는 **FAB Scene Kit** 라이브러리로 열립니다. 카테고리 또는 검색을 사용합니다.
3. 썸네일을 Viewport로 드래그하고 Collection instance로 배치합니다.
4. 방금 배치한 instance를 선택해 **Use FAB Settings**을 누릅니다. 바닥·그리드·현재 테마와 라벨 설정을 적용합니다.
5. 처음 등록한 라이브러리를 다음 실행에도 유지하려면 Preferences의 **Save Preferences**를 사용합니다.

라이브러리가 보이지 않으면 Preferences → FAB Scene Kit에서 **Register Asset Browser library**를 누릅니다. 별도 data 묶음을 쓰려면 Data folder에 library와 templates가 들어 있는 폴더를 지정합니다.

## 반복 배치와 선택 편집

- **Duplicate Once:** 선택한 대표 에셋을 Spacing만큼 복제합니다.
- **Create Row:** 활성 에셋 뒤에 Copies 수만큼 추가합니다. **Duplicate & Arrange**의 Axis와 Spacing을 사용합니다.
- **Align Selected:** 여러 에셋을 선택해 같은 축·간격으로 정렬합니다.
- **Selected Asset:** Name/ID와 라벨 방식을 수정합니다. 크기·위치는 하위 **Label & Geometry Details**에 있습니다. 같은 장비의 다른 복제본은 바뀌지 않습니다.
- **Highlight Asset / Remove Highlight:** 선택한 에셋만 강조합니다.
- **Replace Model / Pose:** **Add Assets**에서 원하는 모델/포즈를 고른 후 **Label & Geometry Details**에서 누릅니다. 교체할 모델 이름이 버튼 위에 표시됩니다. 현재 위치와 라벨을 유지하면서 모델을 교체합니다.
- **Edit Individual Parts:** collection instance를 개별 object로 전환합니다. 이후에는 Blender 기본 편집 기능을 사용합니다.

텍스트를 수정하려면 라벨 자체보다 장비 root를 선택하십시오. 모델은 한 번의 선택으로 이동하는 collection instance입니다.

## 텍스트와 한글

라벨은 Floor(바닥), Above(상단), Front(전면), Hidden(숨김)을 제공합니다. 전면 라벨은 장비 형태에 따라 Label offset으로 표면 위치를 조정합니다.

Scene Text의 Title과 Show asset labels는 변경 즉시 반영됩니다. Local font를 바꾼 후에는 **Apply Font / Refresh Labels**를 누릅니다.

한글을 넣을 때는 Local font에서 사용 권한이 있는 로컬 .ttf 또는 .otf를 지정합니다. 기본 Blender 내장 폰트는 한글 표시를 보장하지 않습니다. **Apply Font / Refresh Labels**로 적용하고 프리뷰에서 확인합니다. 애드온의 **Save New .blend**는 명시적으로 선택한 폰트를 파일 안에 포함합니다. 배포 ZIP에는 외부 폰트가 없습니다.

## Cleanroom과 바닥 편집

1. **Cleanroom & Stage → Select Cleanroom**을 누릅니다. 기존 파일의 잠긴 cleanroom도 선택할 수 있습니다.
2. G로 전체 cleanroom을 이동하고 Width/Depth로 크기를 조절합니다. 배치한 설비는 별도 객체라 자동으로 따라 움직이지 않습니다.
3. **Edit Floor / Wall Parts**를 누르면 바닥·벽·기둥 등을 개별 객체로 전환하고 바닥 메시를 선택합니다.
4. 원하는 부품을 뷰포트에서 클릭하고 **Edit Selected Mesh**를 누릅니다. 편집 후 **Finish Mesh Editing**을 누릅니다. 기본 키맵에서는 Tab도 사용할 수 있습니다.
5. 전체를 다시 옮기려면 **Select Cleanroom** 또는 **Selected Asset → Select Whole Asset**을 누릅니다. 변환 직후 Ctrl+Z로 되돌릴 수 있습니다.

새 템플릿의 cleanroom과 utility pad는 뷰포트에서 바로 선택할 수 있습니다. 기존 파일은 0.2.0에서 한 번만 잠금을 해제합니다. 이후 직접 건 잠금은 유지하며 Select Cleanroom으로 필요할 때 해제합니다.

**배치 높이**: Add Assets의 Place on에서 Cleanroom(선택한 room의 바닥), Stage(외곽 받침대), 3D Cursor(커서 높이), Custom height(직접 입력)를 고릅니다. Utility pad 위에 놓으려면 3D Cursor 도구로 해당 표면을 찍고 3D Cursor 높이를 사용합니다. 기존 파일의 수동 높이는 Custom height로 유지됩니다. OHT/FFU는 Rail height를 사용합니다.

## 바닥과 OHT

- Cleanroom & Stage 아래 **Outer Stage**의 Width/Depth → **Resize Outer Stage**는 외부 베이스만 바꿉니다. 이미 배치한 장비와 중앙 cleanroom의 크기는 유지됩니다.
- Floor Z는 새 바닥형 에셋의 배치 높이입니다. Example의 중앙 cleanroom은 약 0.79m, 외부 베이스는 약 0.39m입니다. 유틸리티 pad 위에는 해당 pad 높이를 더합니다.
- **Add Loop at Cursor:** Cursor XY를 중심으로 지정한 폭·깊이·높이의 둥근 사각 폐루프와 차량을 만듭니다.
- 개별 레일을 선택하고 **Connect Next Rail**을 누르면 끝점에 직선 또는 90° 코너를 연결합니다.
- 레일을 선택하고 **Add Vehicle on Rail**을 누르면 해당 구간에 차량을 올립니다.
- Show overhead assets는 OHT와 천장형 요소의 표시를 바꿉니다.

로봇은 검토된 정적 포즈를 제공합니다. OHT는 설명용 레일 조립이며 물류 시뮬레이션이나 공학적인 경로 검증 기능이 아닙니다.

## 카메라·출력

1. Camera 방향을 선택하고 **Apply Camera Direction**을 누릅니다.
2. **Frame All** 또는 **Frame Selected**으로 정사영 카메라를 맞춥니다.
3. Aspect에서 4:3 또는 16:9를 선택하고 **Apply Aspect Ratio**를 누릅니다.
4. Output folder를 지정합니다.
5. **Preview 50%**는 현재 해상도의 50%, **Render PNG**는 100%로 렌더합니다. 기존 파일이 있으면 번호를 붙여 보존합니다.
6. 라벨의 가림과 겹침, OHT·천장과 장비 관계, 바닥·그림자 잘림을 직접 확인합니다.
7. **Save New .blend**로 편집 가능한 장면을 저장합니다. 모델과 재질은 파일에 포함되며, 원본 라이브러리를 이동해도 저장된 장면을 열 수 있습니다.

Check Scene은 식별자·모델 누락·변환 값·바닥 영역 등의 기본 구조 검사입니다. 미적인 완성도와 모든 3D 가림을 자동 판정하지 않습니다.

**저장 범위**: Save New .blend는 활성 장면을 포함한 현재 Blender 파일 전체를 저장합니다. 기존 파일은 번호를 붙여 보존합니다. 출력 폴더가 없으면 렌더와 저장 버튼이 비활성화되고 안내가 표시됩니다. 렌더 중 Esc로 취소할 수 있습니다.

## 포함 에셋

- 제조 5종: Lithography, Etch, Deposition, Inspection, Testing
- 유틸리티 10종: HVAC, Chiller, UPW, Wastewater, Scrubber, Bulk gas, Gas cabinet, Chemical supply, Electrical, Control room
- 로봇 6항목: AMR·Cobot·Humanoid 각각 기본/작업 또는 운반 포즈
- 사람 2항목: Cleanroom operator, Utility worker
- 물류: FOUP, cart, buffer rack, OHT 차량·직선 레일·곡선 레일·지지 구조
- 공간: Cleanroom cutaway, floor tile, wall, FFU, utility pad
- 연결: 직선 배관, elbow, duct, 관계 화살표

총 39개 라이브러리 항목이며 로봇의 포즈 변형을 포함한 수입니다.

## 현재 범위

정적인 FAB 전체 설명 장면에 맞췄습니다. 임의 CAD/FBX 스타일 변환, 자동 공장 설계, 자동 라벨 배치 최적화, 복잡한 OHT 분기망, 로봇 애니메이션, JSON 레시피는 이번 버전에 포함하지 않습니다. Blender 기본 .blend 저장이 편집 원본입니다.


## 0.3.0 — 새 장비와 사람

라이브러리는 총 52개 항목입니다. 새 에셋은 아래 검색어로 찾습니다.

- Manufacturing: `wafer`, `dicing`, `metrology`, `microscope`
- Utilities: `terminal`
- Robots: `SCARA`
- Logistics: `wafer`, `cassette`, `chip tray`
- People: `standing`, `operating`, `wafer handling`, `walking`, `seated`, `worker`

사람은 약 1.75m 성인 비율의 고정 포즈 에셋입니다. Seated는 stool을 포함합니다. 애니메이션용 rig는 포함하지 않습니다. 300 mm wafer는 실제 지름 0.3m이므로 전체 FAB에서는 작게 보이는 것이 정상입니다. 책상 위 소품은 Place on의 Custom height 또는 G/Z로 작업대 상판에 맞춥니다.

새로 배치하는 사람과 새 템플릿은 개정 모델을 사용합니다. 기존 저장 씬의 사람은 자동 교체하지 않습니다. 바꾸려면 기존 사람을 선택하고 Add Assets에서 원하는 People 모델을 고른 다음, Selected Asset의 Label & Geometry Details에서 **Replace Model / Pose**를 누릅니다. 위치·회전·크기·사용자 라벨은 유지됩니다. 개별 메시로 변환했던 사람은 새 에셋을 별도로 배치합니다.
