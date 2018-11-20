# Setup

```python
%gui qt5

from skimage import data
from skimage.color import rgb2gray
import napari_gui as gui
from numpy import array, random
```

## Display a single image

```python
viewer = gui.imshow(data.camera())
```

### Add a new layer

```python
viewer.add_image(rgb2gray(data.astronaut()),{})
```

### Add a third layer

```python
viewer.add_image(data.camera(),{})
```

### Add a marker layer

```python
marker_list = array([[100, 100], [200, 200], [333, 111]])
viewer.add_markers(marker_list, size=20)
```

### Reorder layers

```python
viewer.layers.swap(3,1)
```

```python
viewer.layers.reorder([2,1,3,0])
```

### Remove first layer

```python
viewer.layers.pop(0)
```

## Add a multidimensional layer

```python
viewer = gui.imshow(random.rand(500, 500, 20, 10))
```

### Add a new layer

```python
viewer.add_image(random.rand(500, 500, 20, 10),{})
```

```python

```