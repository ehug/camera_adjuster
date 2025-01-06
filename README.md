# Camera Adjuster Tool

Author: Eric Hug 

![Tool Preview](tool_preview.jpg)

## Requirements
* Maya 2022 (with python 3) through 2025

## Installation
* Place downloaded folder into your local "maya/scripts" folder. (Make sure it is named "camera_adjuster" and *not* "camera_adjuster-main")
* Open Maya.
* Open Maya's Script Editor. In a Python tab, run the tool using the following python code:
```python
from importlib import reload
from camera_adjuster import view
reload(view)
view.start_up()
```

## Usage
### Export

* **Step 1:** Load the tool using the four lines of code above.
* **Step 2:** Create (Under "File" --> "Create New Camera") or load a specific camera you want to begin modeling from. 
  * **Note:** To rename your camera, rename it as you normally would and then press the refresh button to for the name to update in your list of cameras.
* **Step 3:** Go to "File" --> "Create Image Plane", and select an iamge file you want to parent to your active camera.
* **Step 4:** When you start blocking out your mesh, you can use the translate and rotate controls within this tool to position your camera so that your mesh is lined up with your image plane's perspective.
* **Step 5:** When you're happy with the camera positioning, you can lock the attributes to prevent accidentally messing up your perspective by pressing the "Lock Transform Attributes" checkbox. 
  * **Note:** You can also adjust your camera's positioning with the tool's translate and rotate controls while the camera is locked.
* **Step 6:** When getting into details for your mesh, you can zoom in on your image plane by hovering over the image displayed in the tool and using your mouse wheel. You can also move/pan the image plane around by clicking and dragging the image around within the tool.

