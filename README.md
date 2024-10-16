# ReluRes
- RenderMode, Outline -> property, mapper설정을 뺴서..
- Capture(위아래뒤집은) -> 

rendering capture
- classification
- object detection

full model
- bone
- soft tissue


- Save Comment OK
- nifti file 생성 -> Scandirectory.py -> "direct conversion from numpy"
- Segment -> model 디렉토리 copy, segment OK




read dicom
1) numpy
-> spacing
-> origin, directional cosine
-> RescaleSlop, Intercept value

2) save as nifti file(nii.gz) and 

3) 
-> user matrix (volume origin 만큼)
-> shiftscale to vtkvolume
-> capture to mandible, condyle, rendering direction
-> 

4) 

