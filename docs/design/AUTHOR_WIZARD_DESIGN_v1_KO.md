> 0.4.2에서 실제 Guided Brief 애드온을 구현했습니다. 이 문서는 이전 설계 기록입니다. 설치된 기능과 제한은 [현재 사용 안내](../GUIDED_BRIEF_KO.md)를 참고하세요.

# FAB Author — AMMR Wizard 설계 v1

2026-09-09 · 설계/인터랙션 프로토타입 · 설치 버전 0.4.1 변경 없음

## 해결할 문제

사용자는 장비의 기능을 이해하지만 원본 CAD/FBX를 Author용으로 다시 정리하기 어렵다. 하나의 장비가 여러 root에 나뉘고, Mesh 부모가 자체 형상과 다른 기능의 자식을 동시에 가진다. Workspace 같은 보조 Mesh, 연결점 Empty, 리그 Armature가 섞인다. Quick의 전체 자식 분석은 의도하지 않은 형상을 포함할 수 있고, Advanced의 primitive/좌표/재질 입력은 작업 부담을 사용자에게 넘긴다.

목표는 원본을 정리하지 않고 **기능 설명 + 선택으로 연결한 주요 부품 + 필요한 실측**을 작성하는 것이다. 장비 의미를 알 수 없는 자동 분류는 후보로 표시한다. 이 단계에서 최종 스타일 모델을 자동 생성한다고 주장하지 않는다.

## 원칙

- 원본 hierarchy와 기능별 부품 목록을 별도로 유지한다. reparent, join, decimate, rename을 요구하지 않는다.
- Object/Collection/Armature/Bone 소속을 하나의 조립 tree로 오인하지 않는다. 목록은 source 탐색용이다.
- 의미, 사용자 확인, 측정, 추정, 미확인을 구분해 보관한다. 모르는 숫자는 null이다. 0으로 채우지 않는다.
- 모든 주요 단계에 `Back`, `Next`, `Save Draft`를 둔다. 단계 이동 및 저장은 미완료 상태에서도 가능하다.
- `Skip measurement`와 부품별 `Describe only`를 허용한다. 결과에 해당 정보가 미측정임을 명시한다.
- 장비 유형의 질문에 답하게 하고 primitive, bevel, topology 작성은 별도 Advanced 작업으로 둔다.
- 전체 전송 텍스트는 최대 1000 UTF-16 code units. 초과 시 Copy/Export를 막고, 묵시적인 잘라내기·분할 전송은 하지 않는다.
- UI는 영어. 사용자 설명과 결과 텍스트는 한국어를 포함한 Unicode를 허용한다.
- 로컬 작성과 사용자의 수동 전달을 지원한다. 네트워크·새 dependency·상용 add-on은 필요하지 않다.

## 화면 구성

기존 `N > FAB Author` 탭을 그대로 사용한다. `Guided Brief`를 새 진입점으로 추가하고, 기존 Quick/Advanced는 접힌 `Other workflows`로 이동하는 안이다. 새 N 탭을 추가하지 않는다. 기존 draft를 자동 변환하거나 덮어쓰지 않는다.

Sidebar에는 현재 단계와 필요한 필드만 표시한다. 큰 source tree는 `Browse Sources`의 별도 Blender dialog에서 탐색한다. viewport 선택을 유지하는 non-modal sidebar를 기본으로 하며, wizard 전체를 blocking modal로 만들지 않는다.

```text
FAB Author
Guided Brief · AMMR
2 / 5  Describe
--------------------------------
Purpose                 [text]
Base outline            [L-shaped]
Arm count               [1]
Arm 1 kind              [Articulated]
Arm 1 axes              [7 / Unknown]
Additional mechanisms   [Linear stage] ...
Distinctive features    [text]
--------------------------------
Back      Save Draft      Next
```

## 1. Scope — 포함 대상

실제 UI 제목은 `Scope`이다.

| UI | 동작 |
| --- | --- |
| Add Selection | Object Mode의 현재 선택을 대상 후보에 추가. 다중 root 지원 |
| Add Collection | 선택 Collection의 소속과 자식 Collection을 명시한 후보 생성 |
| Selected Only / Include Children | 각 추가 동작의 범위를 선택. 이전 선택을 명시적으로 표시 |
| Browse Sources | hierarchy, object type, membership, geometry/reference 상태를 탐색 |
| Show Included / Show Excluded | 원본에 overlay 표시. 기존 숨김/선택 상태를 보존·복원 |
| Review Candidates | 보조 형상 후보마다 Keep / Exclude / Decide later |
| Confirm Scope | 최종 include/exclude snapshot 확정 |

후보 탐색 시 이름, display type, 크기 등의 이유를 보여줄 수 있지만 이름만으로 자동 제외하지 않는다. Workspace를 Keep으로 확인하는 선택도 허용한다. Camera/Light는 물리 형상 측정에서 제외하되 목록에 이유를 표시한다. Empty/Armature는 좌표·리그 reference로 남기고 표시 아이콘 크기를 치수에 포함하지 않는다. 실제 bone/armature 변형은 평가된 Mesh의 현재 pose에 반영한다.

후손 제외는 상위 include보다 우선한다. 단일 object와 branch 제외를 구분한다. 같은 Mesh가 여러 선택 root 또는 Collection에서 도달해도 한 번만 포함한다. 숨김 object도 후보 포함 사실을 표시하며 가시성만으로 임의 제외하지 않는다.

미해결 보조 후보가 있으면 나머지 작성은 계속할 수 있지만 전송 전에는 처리해야 한다. scope 확정 전 숫자는 `Provisional`이며 최종 치수로 전송하지 않는다. 장비가 전부 합쳐진 하나의 Mesh인 경우 `Describe only`로 진행하거나 별도 수동 선택 경로를 안내한다. 자동 의미 분리를 보장하지 않는다.

## 2. Describe — 장비 구성 질문

| 질문 | 답/분기 | 필수 여부 |
| --- | --- | --- |
| Asset type | v1은 AMMR. 이후 다른 유형 추가 | 필수 |
| Purpose | 한두 문장의 작업 목적 | 필수 |
| Base outline | Rectangular / L-shaped / U-shaped / Other / Unknown | 필수 선택, Unknown 허용 |
| Open area | L/U/Other일 때 위치를 고르거나 짧게 설명 | 선택 |
| Arm count | 1 / 2 / Other / Unknown. 숫자에 맞춰 arm card 생성 | 필수 선택, Unknown 허용 |
| Arm kind / Axes | Articulated / SCARA / Other / Unknown, 자유도는 미확인 허용 | 팔별 선택 |
| Additional mechanisms | Lift / Linear stage / Rotary unit / Tool storage / Holder / Other | 선택, 복수 |
| Distinctive features | 보존할 특징. 예: 빈 공간, 두 기구의 상대 배치 | 선택 |

질문에 답하면 **기능 카드**가 생긴다. object 이름이나 Mesh 개수로 팔 수/관절 수를 확정하지 않는다. 선택지를 바꾸면 관련 질문만 노출한다. 팔 수를 줄여도 기존 카드의 설명·binding은 archive로 보존하며 전송에서는 inactive 처리한다.

`Other`는 범용 자유 설명과 추가 부품 카드로 이어진다. v1에서 처리하지 못하는 구성을 기존 유형에 억지로 맞추지 않는다.

## 3. Parts — 주요 부품을 원본에 연결

초기 필수 입력은 장비 유형·목적·대상 확인이다. 부품 연결을 건너뛰어도 설명 작성은 가능하다. 정확한 측정이 필요할 때 주요 2~4묶음을 우선 연결한다.

| 카드 UI | 동작 |
| --- | --- |
| Pick in Viewport / Browse Sources | 현재 선택 또는 원본 tree에서 선택 |
| Selected Only / Include Children | Empty/Armature 선택 시 실제 형상 후손이 없으면 범위 확대 안내. 자동 확대하지 않음 |
| Assign Selection | **확정 scope와 교집합**인 형상만 binding. 포함/제외 목록을 즉시 표시 |
| Add / Replace / Remove Sources | 기존 binding의 변경 의도를 명시 |
| Show Assigned | 해당 형상 강조 및 frame. 확인용 원본 선택 후 복구 가능 |
| Describe only | binding 없이 역할·대략적인 위치를 설명 |
| Importance | Must keep / Supporting / Omit from brief |

하나의 부품은 여러 root의 Mesh를 가질 수 있다. 하나의 Mesh가 둘 이상의 물리 부품에 중복 배정되면 이동 또는 reference-only 공유를 선택한다. 부모 카드와 하위 카드가 함께 사용될 때 aggregate bounds는 집합 합집합으로 계산한다. 기능 관계는 binding이나 Blender parent와 독립적이다.

선택 예외: base Mesh의 자체 geometry만 배정하면 자식 gripper가 base 치수에 섞이지 않는다. arm branch를 배정해도 scope에서 제외한 Workspace는 다시 포함되지 않는다. 새 object가 scope 밖에 있으면 `Add to Scope`로 돌아가 재확인한다.

## 4. Measure & Relations — 수치와 의미를 구분

측정은 `Measure`를 눌렀을 때 수행하고 원본을 변경하지 않는다. unit, asset frame, pose/frame, 대상 snapshot을 결과에 묶는다.

| 항목 | 동작/표현 |
| --- | --- |
| Units | Scene units / Custom. 원본 수치와 단위 환산값을 함께 확인 |
| Front / Up | 기본 -Y / +Z 제시, viewport 화살표를 보고 확인하거나 active orientation 사용 |
| Overall size | 확정 scope의 실제 평가 geometry를 asset frame에서 측정 |
| Component size / Center | 배정 geometry의 asset-frame bounds와 중심. joint 위치로 간주하지 않음 |
| Approximate placement | Front / Rear / Left / Right / Center / Inside opening / Other / Unknown |
| Mounted on | 사용자 지정 물리 지지 관계, Unknown 허용 |
| Motion | Fixed / Vertical / Cartesian / Rotary / Articulated / Unknown |
| Coordination | Independent / Moves together / Unknown, 대상 부품 쌍을 지정 |
| Work sequence | 사용자 설명. 형상이나 parent로 작업 순서를 자동 추론하지 않음 |

v1의 측정 기준은 현재 pose에서의 전체 외곽이다. 이동 stroke, 작업 영역, 기구학적 joint center, 장비 정격 치수와 구분한다. bounding box가 L/U자의 빈 공간을 설명하지 못하므로 outline/open-area 설명을 별도로 유지한다. 여러 부품의 독립 승강이 두 개의 물리 column을 뜻한다고 단정하지 않는다.

scope/geometry/pose/unit/frame 변경 시 관련 수치를 `Needs refresh`로 표시한다. 변경 검출은 depsgraph dirty 표식과 측정 snapshot 검사로 구현하고, 매 panel draw에서 geometry를 다시 계산하지 않는다. stale 수치를 포함한 전송은 차단한다. 수치를 제외한 설명 전송은 허용한다.

Collection instances는 인스턴스 변환을 포함한 geometry 평가가 구현·검증된 경우만 측정한다. 초기 지원 밖의 linked/instance 구조는 `Measurement unavailable`과 Describe only를 제공한다. 원본을 editable로 바꾸도록 강제하지 않는다.

## 5. Review — 1000자 검토

사용자가 읽을 수 있는 구조화 텍스트를 생성한다. `Purpose`, 주요 부품 역할, Must keep 특징, 독립/동시 동작 관계, 명시적인 Unknown은 핵심이다. 숫자는 측정 provenance가 있을 때만 추가한다. 상세 object 이름과 전체 hierarchy는 로컬에 보관하며 기본 전송에서 제외한다.

출력 형식은 새 `AW1` brief로 설계한다. 자유 입력 문자열은 따옴표/개행/구분자를 JSON string 규칙으로 escape하여 필드 경계와 구분한다. **현재 FQ1 decoder와 호환되지 않으며** 이 프로토타입은 모델 생성 포맷이 아니다. AW1 정의와 importer 구현 전에는 production 지원으로 표시하지 않는다.

| Review 요소 | 정책 |
| --- | --- |
| Readable brief | 실제 복사/저장될 문자열과 동일 |
| Character count | 전체 문자열의 UTF-16 code units. 1000 이하만 Copy/Export 허용 |
| Include measurements / placement / hierarchy summary | 선택 항목별 문자 비용과 실제 결과를 갱신 |
| Must keep | 자동 제거 금지. 사용자가 수정하거나 중요도 변경 |
| Over limit | 초과 문자 수와 줄일 수 있는 항목 표시. 자동 절단·무단 생략 없음 |
| Missing data | 미측정/Unknown을 명시. 설명만으로 작성 가능 |
| Copy Text / Export .txt | 같은 canonical 문자열. UTF-8, BOM/추가 개행 없음 |
| Save Local Draft | 전체 내용, 선택 연결, 제외 사유, hierarchy, 측정 snapshot 저장 |

하나의 완결된 1000자 이하 전송본을 만들며, 분할 전송을 전제하지 않는다.

## 로컬 데이터 및 유지보수

Source registry: 로컬 stable ID → object pointer, 원래 이름, 부모, Collection membership, object type, library identity, visibility, geometry/reference 구분. 식별자를 원본 이름에 의존하지 않고 draft에 저장한다. rename은 binding을 유지하며 삭제/교체 시 missing 상태로 재연결을 요청한다.

Scope: root 선택, selection mode, expanded ID 집합, include/exclude override, 확인 이력, revision.

Functional parts: 별도 ID, 역할, 설명, importance, source binding 또는 describe-only, approximate placement, user-confirmed relations.

Measurements: meters, asset-frame orientation/origin, current frame/pose, source IDs, revision, status. 미측정은 null.

Brief: 선택한 전송 fields, canonical text, 문자 수, schema version. 기존 rich recipe와는 별도 저장한다.

Undo와 scene 저장/재열기를 지원한다. source에서 추출한 내용을 public repository로 자동 수집하지 않는다. 기존 library 등록/완성 Author .blend import 경로는 재사용한다.

## 구현 단위

1. `brief_spec.py`: 별도 draft, 질문 정의, canonical 텍스트, 문자 제한, 검증. bpy 없이 검증 가능.
2. `source_scope.py`: identity, object/collection traversal, 명시적 포함/제외, bounds 측정, stale 상태.
3. `brief_ui.py`: 기존 FAB Author 안의 5단계 UI와 source picker. draw는 읽기만 수행.
4. 기존 `author_model.py`의 평가 geometry 측정 helper는 scope/단위 의미를 확인한 뒤 재사용. Quick envelope 생성과 결합하지 않음.
5. 별도 namespace/version의 draft migration. 배포 버전 번호는 실제 구현·설치 검증 후 확정.

## 완료 기준과 회귀 시나리오

| 사례 | 통과 조건 |
| --- | --- |
| 다중 root 장비 | 전체 선택의 합집합, 중복 Mesh 없음 |
| Workspace가 arm의 자식 | Exclude 후 팔 배정/재측정에도 제외 유지 |
| 형상이 있는 base 부모 | Selected Only는 자신의 geometry만 측정 |
| Empty/Armature | geometry로 부풀리지 않고 reference 보존; 실제 pose 적용 |
| 알 수 없는 보조 형상 | 자동 누락 없이 Keep/Exclude 확인 |
| 독립 승강 부품 두 개 | 관계를 보존하되 물리 column 개수 추정하지 않음 |
| 미측정/단일 joined Mesh | Describe only로 작성, 임의 치수 없음 |
| 한글·emoji·1000/1001자 | 문자열 전체 기준 경계, 초과 전송 차단 |
| source/pose/unit 변경 | stale 수치 전송 차단 또는 수치 제외 |
| 2개 팔 → 1개 팔 → 2개 팔 | inactive 작성 내용 복구, 전송 수 일치 |
| 저장·재열기·Undo | 선택 연결/제외/질문 상태 보존 |
| 기존 Quick/Advanced/Library | 기존 draft, 52 assets, 3 templates 사용 유지 |

UI 검증 시 320~420px sidebar에서 줄바꿈, 선택 범위 피드백, back/next, 재개, 오류 복구를 실제 Blender에서 확인한다. 텍스트 작성 도구의 완료를 렌더 품질 통과로 대체하지 않는다. 후속 에셋 생성은 별도 render → inspect → correction 과정으로 검증한다.

## 이번 산출물의 검증 범위

기존 코드의 역할·측정·Quick export 경로를 읽고 설계했다. 별도 interactive mockup으로 scope 후보 결정, 구성 분기, 명시적 부품 배정, 독립 운동 관계, 미측정/데모 수치, 1000자 초과를 검토한다. mockup은 Blender 연결 및 실제 CAD 측정을 수행하지 않는다. 실제 sidebar layout/Blender 통합 검증은 구현 단계의 작업이다.

프로토타입은 대표 분기를 보여주는 범위다. 팔 수 1~4/Unknown, 단일 선택 Replace 배정, 현재 입력 유지, 선택한 요약 텍스트의 수동 복사를 제공한다. production 설계의 Other 수량 입력, Add/Remove 바인딩, Save Draft/재열기, 실제 viewport picking/overlay는 아직 구현하지 않았다. 데모 측정값은 명시적으로 ILLUSTRATIVE_ONLY이며 원본 치수 필드는 계속 unmeasured이다.

23개의 순수 상태·문자열 및 JavaScript 문법 검사를 통과했다. 보고서는 `docs/design/validation.json`, 검사 스크립트는 `tools/check_author_wizard_design.cjs`이다. 범용 예제의 문자 수는 검증 보고서의 sample_characters에 기록한다. 1000/1001 경계, 한글/emoji, scope 확인, Workspace 제외의 유지, base 자체/자식 선택, 중복 배정, 팔 개수 변경, 독립 운동, 미측정/데모 표시 등을 확인했다. 브라우저 또는 대화 내 렌더 결과를 직접 검사하지 않았으므로 layout/실제 UI 조작 검증 완료로 보고하지 않는다.

## 공개 데모 사용

`docs/design/author-wizard-v1.html`을 다운로드해 브라우저에서 연다. 별도 서버 없이 사용한다. 예제 hierarchy는 독립적으로 만든 간단한 범용 데이터이며 실제 장비 자료가 아니다. 원본 fragment는 `docs/design/author-wizard.fragment.html`이다.

```powershell
node tools/check_author_wizard_design.cjs docs/design/author-wizard.fragment.html docs/design/validation.json
```

이 명령은 개발 검증용이며 Node 설치는 애드온 사용 요건이 아니다. 실제 Blender 연동이나 geometry 측정을 수행하지 않는다.
