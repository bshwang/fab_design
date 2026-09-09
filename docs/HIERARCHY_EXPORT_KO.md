# Blender hierarchy 텍스트 추출

설치된 애드온과 별개로 실행하는 작은 Blender Python 도구다. Object 부모·자식 구조를 추출하며 Mesh 형상과 원본 parent를 변경하지 않는다.

1. 저장소의 [export_selected_hierarchy.py](../tools/export_selected_hierarchy.py)를 준비한다.
2. Blender의 **Object Mode**에서 원하는 모델의 최상위 부모를 선택한다. 여러 root를 선택할 수 있다.
3. **Scripting → Text Editor → Open**으로 스크립트를 연다.
4. **Run Script**를 누른다.
5. Text Editor에 새 `Robot_Hierarchy.txt`가 표시된다. 결과가 1000자 이내면 클립보드에도 복사된다.

```text
RobotRoot [EMPTY] (+1 children)
  ArmAssembly [EMPTY] (+2 children)
    ShoulderMesh [MESH]
    ForearmMesh [MESH]
```

1000자를 넘으면 전체 결과는 Blender Text block에 남고 클립보드는 변경하지 않는다. 더 작은 조립체를 선택하거나 스크립트 상단의 `MAX_DEPTH = None`을 `MAX_DEPTH = 2`로 바꾸면 root 아래 두 단계까지 요약할 수 있다. `children`은 직접 자식 수다.

결과를 파일로 보관하려면 Text Editor의 **Text → Save As**를 사용한다. `.blend`를 저장하면 Text block도 함께 보관된다. 재실행할 때는 Text Editor의 텍스트 목록에서 실행 스크립트를 다시 선택한다.

이 도구는 Object tree만 추출한다. Collection 구성, Armature 내부 Bone tree, Bone parenting/constraints, 치수나 실제 형상을 추출하지 않는다. 이미 FBX 변환에서 사라진 CAD assembly 구조를 복구하지 않는다. 숨겨진 자식도 포함할 수 있으므로 전송 전에 텍스트를 확인한다.

Blender 4.3.0의 합성 부모·자식 모델에서 실행 및 중복 선택 처리를 확인했다. 새 dependency는 필요하지 않다.
