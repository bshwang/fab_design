# FAB Scene Kit 0.4.2 — Guided Brief

**N → FAB Author → Guided Brief**에서 실제 원본을 선택하고 장비 구성·역할·필요한 실측을 AW1 텍스트로 정리합니다. 전송 텍스트는 전체 1000자 이내입니다. 원본 geometry, 이름, 부모·자식 관계를 변경하지 않습니다.

Guided Brief는 설치된 기능입니다. 기존 Quick Capture와 Advanced는 같은 FAB Author 탭의 Workflow 선택으로 접근합니다. FAB Kit / FAB Author 두 탭을 사용합니다.

## 1 Scope — 포함할 대상부터 확인

1. Object Mode에서 장비의 부모 오브젝트들을 선택합니다. 서로 다른 root를 여러 개 선택할 수 있습니다.
2. **Include Children → Add Selection**을 누릅니다. 개별 Mesh만 추가할 때는 Selected Only를 사용합니다.
3. 보조 형상 후보가 있으면 해당 행이 선택됩니다. **Review Next Helper**로 다음 후보를 찾을 수 있습니다.
4. Workspace 같은 보조 형상은 행의 **Decision → Exclude**로 제외합니다. 실제 물리 부품이면 Keep으로 확인합니다. 이름만으로 자동 제외하지 않습니다.
5. **Show Included / Show Excluded**로 선택 범위를 확인한 뒤 **Confirm Scope**를 누릅니다.

Source 목록에는 Mesh뿐 아니라 Empty/Armature도 남습니다. 기준점과 리그는 자체 아이콘 크기를 형상 치수에 포함하지 않습니다. Camera/Light도 물리 치수에서 제외합니다. Mesh/Curve/Surface/Text의 실제 평가 geometry만 측정합니다.

**Keep Selection / Exclude Selection**은 현재 viewport 선택과 Scope selection 모드에 적용됩니다. 행의 Decision은 그 행만 바꿉니다. 숨김/선택 잠금 객체의 가시성은 바꾸지 않으며, Show 동작 결과에 선택한 개수를 표시합니다. **Restore Previous Selection**으로 원래 선택으로 돌아갈 수 있습니다.

Collection 드롭다운과 **Add Collection + Child Collections**로 Collection 전체를 추가할 수도 있습니다. 선택 결과는 snapshot입니다. 새 객체를 추가했으면 Add Selection을 다시 눌러 snapshot에 포함시키세요.

Collection instance 측정은 이번 버전에서 지원하지 않습니다. 해당 행을 Exclude하고 기능 카드에서 Describe Only로 설명할 수 있습니다. 원본을 editable로 바꾸거나 join할 필요는 없습니다.

## 2 Describe — 장비 구성을 선택

- **Type / Purpose:** 장비 유형과 작업 목적.
- **Base outline / Open area:** Rectangular, L-shaped, U-shaped 등 외형과 빈 공간 설명.
- **Arm count / Arm kind / Axes:** 팔 개수와 종류, 자유도. 모르면 Unknown 또는 Axes=0.
- **Additional mechanisms:** Cartesian handler, Lift, Rotary, Tool storage, Holder.
- **Must-keep features:** 최종 에셋에 반드시 남겨야 하는 특징.

질문에 답하면 기능별 부품 카드가 만들어집니다. 팔 수를 줄이거나 기구를 해제하면 해당 카드는 inactive 상태로 보관되며, 다시 선택하면 내용이 복구됩니다. 실제 rig의 Bone 수로 팔 수/자유도를 추정하지 않습니다.

## 3 Parts — 주요 부품만 원본에 연결

1. 목록에서 Mobile base, Arm 1 등의 카드를 선택합니다.
2. Viewport 또는 Outliner에서 해당 원본을 선택합니다.
3. **Selected Only / Include Children** 범위를 확인합니다.
4. **Assign / Replace**로 연결하거나 **Add Selection**으로 여러 원본을 같은 카드에 추가합니다.

**베이스 자체의 크기가 필요하면 베이스 Mesh를 Selected Only로 지정하세요.** 부모 아래의 툴/홀더가 치수에 섞이지 않습니다. 팔 root를 Include Children으로 지정해도 Scope에서 제외한 Workspace는 다시 포함되지 않습니다.

하나의 물리 source를 두 기능 카드에 중복 배정하면 알려줍니다. 더 작은 범위를 선택하거나 기존 카드에서 Describe Only로 연결을 해제하세요. 기존 hierarchy를 고칠 필요는 없습니다.

**Describe Only**를 사용하면 원본 연결 없이 기능·위치를 말로 설명할 수 있습니다. Placement, Motion, Mounted on, Function / features는 사용자가 입력합니다. **Add Other**로 추가 기구를 설명할 수 있고, Importance의 Omit from brief는 사용자가 전송에서 제외하기 위한 선택입니다.

## 4 Measure & Relations — 실측은 필요할 때만

1. Scene scale 또는 Custom scale을 고릅니다. 좌표 1이 1mm를 뜻하는 모델이면 Custom=0.001입니다. Scene 설정이 이미 이를 반영했다면 이중 환산하지 않도록 표시된 값을 확인합니다.
2. Source front를 고릅니다. Custom은 회전 입력이나 **Use Active Object Orientation**을 사용할 수 있습니다.
3. **I checked units and front direction**을 체크합니다.
4. **Measure / Refresh All**을 누릅니다.

전체 크기와 배정한 카드들의 크기·중심 위치를 현재 pose의 평가된 geometry에서 읽습니다. Armature 변형, object scale, 회전과 scene 단위를 반영합니다. 출력 단위는 m, 기준은 전체 XY 중심과 최저 Z, -Y front / +Z up입니다. 전체 bounding size만으로 L자의 빈 공간을 알 수 없으므로 외형 설명을 함께 유지하세요.

원본·pose·단위·좌표계·부품 배정이 바뀌면 측정값을 갱신해야 합니다. 전송 시에도 geometry fingerprint를 다시 확인하므로 오래된 수치를 그대로 내보내지 않습니다. 치수가 필요 없다면 다음 단계에서 Include measurements를 끄면 됩니다.

**Component A / Component B / Relationship**에서 Independent vertical travel 등을 지정하고 Work sequence를 설명합니다. 이 정보로 실제 관절 rig나 애니메이션이 생성되지는 않습니다. 물리적인 지지 구조나 동작 범위가 미확인이면 임의의 숫자로 채우지 않습니다.

평가된 정점이 500만 개를 넘으면 측정 범위를 줄이거나 측정값 없이 설명을 내보내세요. UI 선택과 기능 설명은 사용할 수 있습니다.

## 5 Review — 정확히 복사될 텍스트 확인

- **Include measurements:** 실측을 포함할지 선택합니다. 미측정일 때 size는 null입니다.
- **Include root names:** 필요한 경우에만 원본의 root 이름을 포함합니다. 전체 hierarchy는 기본 전송에 넣지 않습니다.
- **View Brief in Text Block:** 실제 출력 문자열을 Blender Text Editor에서 확인합니다.
- **Copy AW1 Text (1000 max) / Export AW1 Text:** 전체 길이가 1000자 이하이고 검토 조건이 충족되었을 때만 동작합니다.

문자 수는 UTF-16 code units 기준입니다. 한글 1글자는 1, 보통의 emoji는 2로 계산합니다. 초과하면 몇 글자를 줄여야 하는지 표시하며, 설명을 자르거나 주요 부품을 자동 삭제하지 않습니다. 복사 실패 시 오류를 표시하고 파일 Export를 사용할 수 있습니다.

AW1은 기하·의미 설명용 JSON 텍스트이며 **FQ1 Quick Capture 또는 Advanced 모델 생성 recipe와는 다릅니다.** AW1을 해당 importer에 넣어 geometry를 생성하지 마세요. 설명을 전달해 모델을 제작하고, 돌아온 완성 에셋은 **Import Finished Author Asset**으로 기존 Local Library 경로에서 추가합니다.

## 저장·재개와 hierarchy

`.blend`를 저장하면 wizard 내용과 로컬 source 연결도 저장됩니다. 새로 열면 측정값을 재확인하도록 표시합니다.

패널 아래 **Local draft files → Save Draft / Load Draft**는 전체 작성 내용을 로컬 JSON으로 보관합니다. 이 파일은 1000자 제한 전송본이 아닙니다. 같은 `.blend`에서 불러오면 object 이름/type/data/library가 일치하는 source를 연결합니다. 다른 파일 또는 누락된 source는 연결되지 않으며, source 행에서 **Reconnect to Active Object**로 재연결할 수 있습니다. 불러온 뒤 Scope를 확인하고 다시 측정하세요.

**New Draft (Archive Current)**는 현재 draft를 Blender Text block에 보관한 뒤 새 draft를 시작합니다. 기존 Quick/Advanced draft는 별도로 유지됩니다.

Scope의 **Hierarchy to Text / Copy if <= 1000**은 Object 부모·자식, 종류, 포함 상태를 추출합니다. Depth=0은 전체, Depth=2는 root 아래 두 단계입니다. 전체 결과는 Text block에 남고 1000자 이하일 때만 복사합니다. Bone tree와 기구학적 연결은 이 출력에 포함되지 않습니다.
