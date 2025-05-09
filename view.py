'''
# ================================================================================================ #
Camera Adjuster 2.1.0

Purpose: To pose camera for modeling objects from reference images

Dependencies:
            maya
            OpenMaya
            OpenMayaUI
            PySide2 / PySide6

Author: Eric Hug

Updated: 4/22/2025

Example:
    from importlib import reload
    from camera_adjuster import view
    reload(view)
    view.start_up()
'''
# ================================================================================================ #
# IMPORT
import os
import sys
import logging
from importlib import reload
from functools import partial

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QAction
    from shiboken2 import wrapInstance
except:
    from PySide6 import QtWidgets, QtCore, QtGui
    from PySide6.QtGui import QAction
    from shiboken6 import wrapInstance
from maya import cmds
from maya import OpenMaya
from maya import OpenMayaUI

# ================================================================================================ #
# VARIABLES
LOG = logging.getLogger(__name__)
MENUBAR_STYLESHEET_ACTIVE = '''
QMenuBar {
    background: rgb(55,55,55);
    color: lightgrey;
}
'''
STYLESHEET = '''
QPushButton {
    background: #555;
    border: 0px solid #333;
    font-size: 12pt;
    font-weight: 600;
    color: lightgrey;
}

QPushButton:hover {
    color: white;
    background: #666;
}
QTextEdit#OutputWin_textEdit {font: 24pt Courier; color: lightgrey; font-size: 10pt;}
'''

# ================================================================================================ #
# FUNCTIONS
def start_up(width=500, height=200):
    '''Start Function for user to run the tool.'''
    win = get_maya_main_window()
    for each in win.findChildren(QtWidgets.QWidget):
        # if type(each) == 'PySide2.QtWidgets.QWidget':
        if each.objectName() == "CameraAdjuster":
            each.deleteLater()
    tool = CameraAdjuster(parent=win)
    tool.resize(width, height)
    tool.show()

    return tool

def get_maya_main_window():
    '''Locates Main Window, so we can parent our tool to it.'''
    maya_window_ptr = OpenMayaUI.MQtUtil.mainWindow()

    return wrapInstance(int(maya_window_ptr), QtWidgets.QWidget)

# ================================================================================================ #
# CLASS
class CameraAdjuster(QtWidgets.QWidget):
    def __init__(self, parent=None, currentTab=1):
        super(CameraAdjuster, self).__init__(parent=parent)
        self.setStyleSheet(STYLESHEET)
        self.tips_str = "Tips: \n" \
                        "> You can select a \n" \
                        "cell in the table and \n" \
                        "use the up/down keys \n" \
                        "on your keyboard \n" \
                        "instead of pressing \n" \
                        "the transform buttons.\n" \
                        "> You can also switch \n" \
                        "which control to set \n" \
                        "by using the \n" \
                        "left/right keys." \
        # Base Window
        self.setWindowTitle("Camera Adjuster")
        self.setObjectName("CameraAdjuster")
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setSpacing(6)
        self.setLayout(self.main_layout)
        # ----- #
        # Menus
        # ----- #
        self.menu_bar = QtWidgets.QMenuBar()
        self.menu_actions_dict = {"File": [QtWidgets.QMenu("File"), 
                                           {"Create New Camera" : [QtWidgets.QMenu("Create New Camera"), 
                                                                   {"Perspective" : [QAction("Perspective"),partial(self.new_camera, "Perspective")],
                                                                    "Orthographic": [QtWidgets.QMenu("Orthographic"), 
                                                                                     {"Front" :[QAction("Front"), partial(self.new_camera, "Front")],
                                                                                      "Back"  :[QAction("Back"),  partial(self.new_camera, "Back")],
                                                                                      "Left"  :[QAction("Left"),  partial(self.new_camera, "Left")],
                                                                                      "Right" :[QAction("Right"), partial(self.new_camera, "Right")],
                                                                                      "Top"   :[QAction("Top"),   partial(self.new_camera, "Top")],
                                                                                      "Bottom":[QAction("Bottom"),partial(self.new_camera, "Bottom")]
                                                                                     }
                                                                                    ]
                                                                   }
                                                                  ],
                                            "Image Planes": [QAction("Image Planes"), "separator"],
                                            "Create Image Plane": [QAction("Create Image Plane"), self.new_imagePlane],
                                            "Replace Image Plane": [QAction("Replace Image Plane"), self.replace_imagePlane],
                                            "Delete Image Plane": [QAction("Delete Image Plane"), self.delete_imagePlane]
                                           }
                                          ]
                                  }
        self.build_menu(menu=self.menu_bar, menu_items=self.menu_actions_dict)
        self.menu_bar.setStyleSheet(MENUBAR_STYLESHEET_ACTIVE)
        # ------------------------- #
        # Camera Combo Box Controls
        # ------------------------- #
        self.cameras_list_widget  = QtWidgets.QWidget()
        self.cameras_list_hLayout = QtWidgets.QHBoxLayout()
        self.cameras_list_widget.setLayout(self.cameras_list_hLayout)
        self.cameras_list_hLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.cameras_list_hLayout.setContentsMargins(QtCore.QMargins(0,6,0,0))
        self.combo_box = QtWidgets.QComboBox()
        self.combo_box.setFixedHeight(32)
        self.combo_box.setFixedWidth(175)
        self.combo_box.currentTextChanged.connect(self.change_camera)
        self.refresh_icon = QtGui.QIcon(os.path.dirname(os.path.realpath(__file__)) + 
                                        "/icons/refresh_btn.jpg")
        self.refresh_btn  = QtWidgets.QPushButton(self.refresh_icon, "")
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.clicked.connect(self.load_cameras)
        self.refresh_btn.setStyleSheet('''QPushButton:pressed {background: rgb(200,200,200);
                                                              }''')
        self.refresh_btn.setToolTip("Refresh list of existing cameras")
        self.lock_settings_cbox = QtWidgets.QCheckBox("Lock Transform Attributes")
        self.lock_settings_cbox.clicked.connect(self.lock_camera)
        self.rotate_image_step_widget = StepWidget(limits=[0, 359.999], text="Rotate Image Plane (Degrees):", decimals=3, step_size=5.0, default_val=90)
        self.rotate_cw_btn = QtWidgets.QPushButton(self.refresh_icon, "")
        self.ccw_icon = QtGui.QIcon(os.path.dirname(os.path.realpath(__file__)) + 
                                        "/icons/ccw_btn.jpg")
        self.rotate_ccw_btn = QtWidgets.QPushButton(self.ccw_icon, "")
        self.rotate_cw_btn.clicked.connect(partial(self.rotate_image_plane, 1))
        self.rotate_ccw_btn.clicked.connect(partial(self.rotate_image_plane, -1))
        self.rotate_cw_btn.setFixedSize(32, 32)
        self.rotate_ccw_btn.setFixedSize(32, 32)
        self.cameras_list_hLayout.addWidget(self.combo_box)
        self.cameras_list_hLayout.addWidget(self.refresh_btn)
        self.cameras_list_hLayout.addWidget(self.lock_settings_cbox)
        self.cameras_list_hLayout.addWidget(self.rotate_image_step_widget)
        self.cameras_list_hLayout.addWidget(self.rotate_cw_btn)
        self.cameras_list_hLayout.addWidget(self.rotate_ccw_btn)
        # ------------------ #
        # # Spacer
        # ------------------ #
        self.spacer = QtWidgets.QSpacerItem(10,6)
        self.separator = QtWidgets.QFrame()
        self.separator.setLineWidth(0)
        self.separator.setFrameShape(QtWidgets.QFrame.HLine)
        # -------------------------- #
        # Controls Horizontal Widget
        # -------------------------- #
        self.body_widget = QtWidgets.QWidget()
        self.body_hLayout = QtWidgets.QHBoxLayout()
        self.body_widget.setLayout(self.body_hLayout)
        self.body_hLayout.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))
        self.body_hLayout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        # ------------------------------------- #
        # # Transform Attributes Control Widget #
        # ------------------------------------- #
        self.worldspace_widget = QtWidgets.QWidget()
        self.worldspace_vlayout = QtWidgets.QVBoxLayout()
        self.worldspace_widget.setLayout(self.worldspace_vlayout)
        self.body_hLayout.addWidget(self.worldspace_widget)
        self.body_hLayout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.transform_widget = NavGrid()
        self.transform_widget.setFixedSize(168,252)
        self.worldspace_vlayout.setContentsMargins(QtCore.QMargins(0, 0, 0, 0))
        self.worldspace_vlayout.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.worldspace_vlayout.addWidget(self.transform_widget.increments_widget)
        self.worldspace_vlayout.addWidget(self.transform_widget)
        self.tips_label = QtWidgets.QLabel(self.tips_str)
        self.worldspace_vlayout.addWidget(self.tips_label)
        self.worldspace_vlayout.addStretch()
        # ------------------ #
        # # Controls Divider #
        # ------------------ #
        self.body_separator = QtWidgets.QFrame()
        self.body_separator.setLineWidth(1)
        self.body_separator.setFrameShape(QtWidgets.QFrame.VLine)
        self.body_hLayout.addWidget(self.body_separator)
        # ------------------------------ #
        # # Local Camera Controls Widget #
        # ------------------------------ #
        self.local_camera_widget = QtWidgets.QWidget()
        self.local_camera_vlayout = QtWidgets.QVBoxLayout()
        self.local_camera_widget.setLayout(self.local_camera_vlayout)
        self.body_hLayout.addWidget(self.local_camera_widget)
        # ------------------------------- #
        # # # Camera Pan Grid Control # # #
        self.grid_size = [cmds.getAttr("defaultResolution.width"), 
                          cmds.getAttr("defaultResolution.height")]
        self.grid_widget = CameraView(camera = self.get_current_camera(),
                                           width  = self.grid_size[0],
                                           height = self.grid_size[1])
        self.local_camera_vlayout.addWidget(self.grid_widget)
        self.image_path = self.get_image_plane()
        if os.path.isfile(self.image_path):
            self.image_plane_point = CameraImagePoint(image_path=self.image_path, 
                                                      size=[self.grid_size[0], self.grid_size[1]])
        else:
            self.image_plane_point = QtWidgets.QGraphicsRectItem()
        self.grid_widget.graph_scene.addItem(self.image_plane_point)
        self.image_plane_point.setPos(0, 0)
        self.reset_pan_btn = QtWidgets.QPushButton("Reset Camera Pan")
        self.reset_pan_btn.clicked.connect(self.grid_widget.reset_pan)
        self.local_camera_vlayout.addWidget(self.reset_pan_btn)
        self.zoom_btn = QtWidgets.QPushButton("Reset Camera Zoom")
        self.zoom_btn.clicked.connect(self.grid_widget.reset_zoom)
        self.local_camera_vlayout.addWidget(self.zoom_btn)
        # ------------------------------- #
        # Assemble Widgets to Main Layout
        # ------------------------------- #
        self.main_layout.addWidget(self.menu_bar)
        self.main_layout.addWidget(self.cameras_list_widget)
        self.main_layout.addItem(self.spacer)
        self.main_layout.addWidget(self.separator)
        self.main_layout.addWidget(self.body_widget)
        # Finalize
        self.load_cameras()
        self.load_pan()
        self.load_zoom()
        self.check_cam_locked_state()
        self.load_rotate()
        new_cam = self.combo_box.currentText()
        cmds.lookThru(new_cam)
        cmds.setAttr("{}.panZoomEnabled".format(new_cam), True)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.main_layout.setSpacing(0)
        self.setWindowFlags(QtCore.Qt.Window)


    def build_menu(self, menu=QtWidgets.QMenu(), menu_items={}):
        '''Create the menus at the top of the tool window.
            Parameters:
                        menu       : Menu for all menu items to be stored under. For initial setup, you want to set menu equal to a QMenuBar()
                        menu_items : Dictionary with structure for assembling all menus, submenus, actions, etc. to the "menu" parameter
                                    Format:
                                            {"QMenu_name"   : [QMenu("QMenu_Name"),
                                                               {"QAction_name" : [QAction("QAction_name"), function to trigger],
                                                                "QAction_name" : [QAction("QAction_name"), function to trigger],
                                                                etc.}],
                                             "QAction_name" : [QAction("QAction_name"), function to trigger],
                                              etc.
                                            }
        '''
        for key, val in menu_items.items():
            if isinstance(val[0], QtWidgets.QMenu):
                menu.addMenu(val[0])
                self.build_menu(menu=val[0], menu_items=val[1])
            else:
                menu.addAction(val[0])
                if val[1] == "separator":
                    val[0].setSeparator(True)
                else:
                    val[0].triggered.connect(val[1])

    def new_camera(self, cam_type=""):
        '''Create a new camera for the scene.
            Parameters:
                        cam_type: Camera's type (ex. Front, Back, Left, Right, Top, Down, Perspective)'''
        new_camera = cmds.camera(name=cam_type)
        if cam_type == "Perspective":
            cmds.viewSet(new_camera[0], persp=True)
        elif cam_type == "Front":
            cmds.viewSet(new_camera[0], front=True)
        elif cam_type == "Back":
            cmds.viewSet(new_camera[0], back=True)
        elif cam_type == "Left":
            cmds.viewSet(new_camera[0], leftSide=True)
        elif cam_type == "Right":
            cmds.viewSet(new_camera[0], rightSide=True)
        elif cam_type == "Top":
            cmds.viewSet(new_camera[0], top=True)
        elif cam_type == "Bottom":
            cmds.viewSet(new_camera[0], bottom=True)
        self.load_cameras()
        self.combo_box.setCurrentText(new_camera[1])
        self.change_camera()

    def get_cameras(self):
        '''Get all cameras in scene.'''
        return cmds.ls(cameras=True)

    def get_current_camera(self):
        '''Get the current camera being used in the active viewport.'''
        cur_view = OpenMayaUI.M3dView.active3dView()
        cur_cam = OpenMaya.MDagPath()
        cur_view.getCamera(cur_cam)
        cur_camPath = cur_cam.fullPathName()
        cur_camPath = cur_camPath.split("|")[-1]

        return cur_camPath
    
    def load_cameras(self):
        '''Load up all cameras in scene into the combobox'''
        current_camera = self.get_current_camera()
        cameras = self.get_cameras()
        # Prevent camera in viewport being changed
        # when loading up all cameras to combobox.
        self.combo_box.blockSignals(True)
        self.combo_box.clear()
        for each in cameras:
            self.combo_box.addItem(each)
        # Restore Setting that changes camera in viewport
        # when combobox changes text.
        self.combo_box.setCurrentText(current_camera)
        self.combo_box.blockSignals(False)
        self.grid_widget.camera = current_camera

    def change_camera(self):
        '''Change camera when combo box text changes.'''
        if self.combo_box.currentText():
            new_cam = self.combo_box.currentText()
            cmds.lookThru(new_cam)
            # Allow pan and zoom attributes to be adjusted when switching to new camera
            cmds.setAttr("{}.panZoomEnabled".format(new_cam), True)
            self.change_image_display()
            self.grid_widget.camera=new_cam
            self.load_pan()
            self.load_zoom()
            self.check_cam_locked_state()
            self.load_rotate()
    
    def lock_camera(self):
        '''Locks camera's movement attributes so user doesn't accidentally use mouse to move by mistake'''
        current_camera = self.combo_box.currentText()
        transform_node = cmds.listRelatives(current_camera, parent=True)[0]
        transform_list = ["tx", "ty", "tz", "rx", "ry", "rz"]
        check = False
        if self.lock_settings_cbox.isChecked():
            check = True
        for each in transform_list:
            cmds.setAttr("{}.{}".format(transform_node, each), lock=check)

    def check_cam_locked_state(self):
        '''Updates the Locked Camera Attributes Checkbox when changing active camera'''
        current_camera = self.combo_box.currentText()
        transform_node = cmds.listRelatives(current_camera, parent=True)[0]
        check = cmds.getAttr("{}.tx".format(transform_node), lock=True)
        self.lock_settings_cbox.setChecked(check)

    def new_imagePlane(self):
        '''Create an imagePlane for active camera'''
        current_cam = self.combo_box.currentText()
        file_path = self.browse_command()
        # Check if no file was selected for image plane
        if len(file_path) == 0:
            LOG.error("No file was selected. ImagePlane cancelled.")
            return
        else:
            file_path = file_path.replace("\'", "")
        
        cmds.imagePlane(camera=current_cam, fileName=file_path)
        self.change_image_display()

    def replace_imagePlane(self):
        '''Replace an imagePlane for active camera'''
        current_cam = self.combo_box.currentText()
        file_path = self.browse_command()
        # Check if no file was selected for image plane
        if len(file_path) == 0:
            LOG.error("No file was selected. ImagePlane cancelled.")
            return
        else:
            file_path = file_path.replace("\'", "")
        self.delete_imagePlane()
        cmds.imagePlane(camera=current_cam, fileName=file_path)
        self.change_image_display()

    def delete_imagePlane(self):
        '''Delete imagePlane from active camera'''
        current_cam = self.combo_box.currentText()
        image_plane = cmds.listConnections("{}.imagePlane".format(current_cam))
        if image_plane != None:
            cmds.delete(image_plane)
        else:
            LOG.warning("No Image Plane detected. Deletion ignored.")
        self.change_image_display()
    
    def browse_command(self):
        '''allows user to select an image file,
           and returns folder path into textfield.
        '''
        file_types = "Image Files (*.jpeg *.jpg *.png *.tif);;"
        self.sel_file = QtWidgets.QFileDialog.getOpenFileName(self,
                                                              caption="get file",
                                                              filter=file_types)
        # Return path to textfield
        if isinstance(self.sel_file, tuple):
            # Use for 'file' or 'files'
            new_string = list(self.sel_file)
            new_string.pop(-1)
            new_string = str(new_string).replace("[", "").replace("]", "")
            
        return new_string

    def get_image_plane(self):
        '''Get the image plane for the current camera'''
        current_camera = self.get_current_camera()
        image_plane = cmds.listConnections("{}.imagePlane".format(current_camera))
        if image_plane:
            image_plane = image_plane[0]
            image_path = cmds.getAttr("{}.imageName".format(image_plane))
        else:
            image_path = "No File Exists"
        return image_path

    def change_image_display(self):
        '''Changes the image shown in the CameraView when camera is changed'''
        self.grid_widget.graph_scene.removeItem(self.image_plane_point)
        self.image_path = self.get_image_plane()
        if os.path.isfile(self.image_path):
            self.image_plane_point = CameraImagePoint(image_path=self.image_path, 
                                                      size=[self.grid_size[0], self.grid_size[1]])
        else:
            self.image_plane_point = QtWidgets.QGraphicsRectItem()
        self.grid_widget.graph_scene.addItem(self.image_plane_point)
        self.image_plane_point.setPos(0, 0)

    def zoom_image(self):
        '''Changes the value of attribute zoom on active camera'''
        current_cam = self.combo_box.currentText()
        val = self.zoom_widget.spinbox.value() / 100.000
        cmds.setAttr("{}.zoom".format(current_cam), val)
        img_plane_scale = 1.0 / val
        self.image_plane_point.setScale(img_plane_scale)

    def reset_pan(self):
        '''Reset the pan attributes of current camera.'''
        current_cam = self.combo_box.currentText()
        cmds.setAttr("{}.horizontalPan".format(current_cam), 0)
        cmds.setAttr("{}.verticalPan".format(current_cam), 0)

    def load_pan(self):
        '''When camera changes, take camera's pan attribute 
           offsets and apply them to the CameraView'''
        current_camera = self.combo_box.currentText()
        pan_x = cmds.getAttr("{}.horizontalPan".format(current_camera))
        pan_y = cmds.getAttr("{}.verticalPan".format(current_camera))
        pos_x = self.grid_widget.width * pan_x
        pos_y = self.grid_widget.height * -pan_y
        self.grid_widget.centerOn(pos_x, pos_y)

    def load_zoom(self):
        '''When camera changes, take the camera's zoom attribute 
           and apply it to the CameraView'''
        current_camera = self.combo_box.currentText()
        zoom = cmds.getAttr("{}.zoom".format(current_camera))
        self.grid_widget.setTransform(QtGui.QTransform().scale(1, 1))
        self.grid_widget.scale(1/zoom,1/zoom)

    def rotate_image_plane(self, direction=1):
        '''Rotate Image Plane parented to camera and previewed in tool
        Parameters:
            direction: rotate image clockwise (1) or counter-clockwise (-1)
        '''
        # Get image Plane Shape
        self.image_path = self.get_image_plane()
        if not os.path.isfile(self.image_path):
            LOG.error("Image not found attached to camera.")
        else:
            current_camera = self.get_current_camera()
            image_plane = cmds.listConnections("{}.imagePlane".format(current_camera))[0]
            shape = cmds.listRelatives(image_plane, shapes=True)[0]
            # Check which button is clicked to determine whether to add or subtract
            # get current rotation value
            current_val = cmds.getAttr("{}.rotate".format(shape)) 
            # Get step value from step widget and multiply by +-1 depending on pressed button.
            rotate_by_val = self.rotate_image_step_widget.step_box.value() * direction
            new_total_val = (current_val + rotate_by_val)
            cmds.setAttr("{}.rotate".format(shape), new_total_val)
            self.image_plane_point.setRotation(new_total_val)

    def load_rotate(self):
        '''When camera changes, take image plane shape's rotate attribute 
           and apply them to the CameraView'''
        self.image_path = self.get_image_plane()
        if os.path.isfile(self.image_path):
            current_camera = self.get_current_camera()
            image_plane = cmds.listConnections("{}.imagePlane".format(current_camera))[0]
            shape = cmds.listRelatives(image_plane, shapes=True)[0]
            current_val = cmds.getAttr("{}.rotate".format(shape)) 
            self.image_plane_point.setRotation(current_val)

    
class CameraView(QtWidgets.QGraphicsView):
    '''Camera Panning and Zooming UI Component
        Parameters:
                width            : Width of view-widget
                height           : Height of view-widget
                columns          : Number of columns drawn
                rows             : Number of rows drawn
                line_thickness   : Line thickness of rows and columns drawn in the scene-widget
                border_thickness : Line thickness of border around the child scene-widget
                camera           : Camera being viewed through for the view to mimic
    '''
    def __init__(self, parent=None, width=300, height=300, columns=3, 
                 rows=3, line_thickness=1, border_thickness=1, camera=""):
        super(CameraView, self).__init__(parent=parent)
        # Base Settings
        self.camera = camera
        self.width = width
        self.height = height
        self.columns = columns
        self.rows = rows
        self.line_thickness = line_thickness
        self.border_thickness = border_thickness
        self.startPos = None
        self.zoom = 1
        # Base Component for graph to be made
        self.setFixedSize(self.width, self.height)
        self.setObjectName("CameraView")
        self.scale(1,1)
        self.base_rect = QtCore.QRect(-self.width*3/2, 
                                      -self.height*3/2, 
                                      self.width*3, 
                                      self.height*3)
        self.graph_scene = CameraScene(rect=self.base_rect)
        # Viewer Settings
        self.centerOn(0,0)
        self.setScene(self.graph_scene)
        self.setSceneRect(-self.width*3/2, 
                          -self.height*3/2, 
                          self.width*3, 
                          self.height*3)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # # Drawing the Grid
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        self.draw_grid()

    def draw_grid(self, color=QtCore.Qt.darkGray, line=QtCore.Qt.DashLine):
        '''Draw the dotted lines that make up the grid'''
        pos_incr_x = float(self.width*3) / self.rows
        pos_incr_y = float(self.height*3) / self.columns
        # print(pos_incr_x, pos_incr_y)
        # Horizontal Lines
        start_num = -1
        for num in range(start_num, self.rows):
            lineItem = QtWidgets.QGraphicsLineItem(-self.width*3/2, 
                                                   pos_incr_y * num, 
                                                   self.width*3, 
                                                   pos_incr_y * num)
            lineItem.setZValue(-1)
            lineItem.setPen(QtGui.QPen(color, self.line_thickness, line))
            self.graph_scene.addItem(lineItem)
        # Vertical Lines
        for num in range(start_num, self.columns):
            lineItem = QtWidgets.QGraphicsLineItem(pos_incr_x * num, 
                                                   -self.height*3/2, 
                                                   pos_incr_x * num, 
                                                   self.height*3)
            lineItem.setZValue(-1)
            lineItem.setPen(QtGui.QPen(color, self.line_thickness, line))
            self.graph_scene.addItem(lineItem)
        # Outline
        pen = QtGui.QPen(QtCore.Qt.black, self.border_thickness, QtCore.Qt.SolidLine)
        rect = QtWidgets.QGraphicsRectItem(self.base_rect)
        rect.setZValue(-1)
        rect.setPen(pen)
        self.graph_scene.addItem(rect)

    def reset_zoom(self):
        self.zoom = 1
        self.setTransform(QtGui.QTransform().scale(self.zoom, self.zoom))
        cmds.setAttr("{}.zoom".format(self.camera), 1)

    def reset_pan(self):
        self.centerOn(0,0)
        cmds.setAttr("{}.horizontalPan".format(self.camera), 0)
        cmds.setAttr("{}.verticalPan".format(self.camera), 0)

    def wheelEvent(self, event):
        '''Controls the Zoom between the Viewer and the Maya Camera'''
        zoom_magnify_max = 4.0
        zoom_magnify_min = 0.5
        angle = event.angleDelta() / 8
        degrees = angle.y() * 15
        if degrees > 0:
            self.zoom *= 1.05
        elif degrees < 0:
            self.zoom /= 1.05
        else:
            self.zoom = 1
        if self.zoom > zoom_magnify_max:
            self.zoom = zoom_magnify_max
        if self.zoom < zoom_magnify_min:
            self.zoom = zoom_magnify_min
        self.setTransform(QtGui.QTransform().scale(self.zoom, self.zoom))
        cmds.setAttr("{}.zoom".format(self.camera), 1/self.zoom)

    def mouseMoveEvent(self, event):
        '''Controls Panning effect between the Viewer and the Maya Camera'''
        super(CameraView, self).mouseMoveEvent(event)
        bounding_box = self.mapToScene(self.viewport().geometry()).boundingRect()
        center = bounding_box.center()
        x = center.x() - 4
        y = center.y() - 4
        cmds.panZoom( self.camera, absolute=True, rightDistance=(x/self.width) )
        cmds.panZoom( self.camera, absolute=True, downDistance=(y/self.height) )


class CameraScene(QtWidgets.QGraphicsScene):
    '''Scene component applied to class 'CameraView' 
        Parameters:
                rect: The Size of the scene within the view.
                NOTE: > Value for "rect" can be bigger than width-by-height of CameraView. 
                      The bigger the rect's dimensions, the more panning area it has.'''
    def __init__(self, parent=None, rect=QtCore.QRect(0, 0, 100, 100)):
        super(CameraScene, self).__init__(parent=parent)
        self.rect = rect
        self.setSceneRect(self.rect)


class CameraImagePoint(QtWidgets.QGraphicsPixmapItem):
    '''Represents the Image that appears which the user can interact with for panning and zooming'''
    def __init__(self, parent=None, image_path="", size=[100,100]):
        super(CameraImagePoint, self).__init__(parent=parent)
        self.size = size
        self.image_path = image_path
        if os.path.isfile(self.image_path):
            self.image = QtGui.QPixmap(self.image_path)
            self.image = self.image.scaled(QtCore.QSize(self.size[0], 
                                                        self.size[1]), 
                                                        QtCore.Qt.KeepAspectRatio, 
                                                        QtCore.Qt.FastTransformation)
            self.setPixmap(self.image)
            self.offset = [self.image.width()/2, self.image.height()/2]
            self.setOffset(QtCore.QPointF(-self.offset[0], -self.offset[1]))
            self.setOpacity(0.5)
            self.setZValue(0.5)


class UpDownButtons(QtWidgets.QWidget):
    '''
    Two Buttons with a label in-between. Handy if you need them to do the opposite of each other.
    Arguments:
            text:      Text to appear in the label between the two buttons.
            up_text:   Text to appear on the first button.
            down_text: Text to appear on the second button.
            vertical:  If True, buttons are laid out vertically. 
                       If False, laid out horizontally. 
                       True by Default.
            btn_size:  Dimensions of each button. Ex. [32, 20]
    '''
    def __init__(self, parent=None, text="Direction", up_text="up", 
                 down_text="down", vertical=True, btn_size=[32, 32]):
        super(UpDownButtons, self).__init__(parent=parent)
        # Base Members
        self.up_icon = os.path.dirname(os.path.realpath(__file__)) + "/icons/up_btn.jpg"
        self.down_icon = os.path.dirname(os.path.realpath(__file__)) + "/icons/down_btn.jpg"
        self.stylesheet = '''QPushButton:pressed{
            background: #666;}'''
        self.text = text
        self.up_text = up_text
        self.down_text = down_text
        self.vertical = vertical
        self.btn_size = btn_size
        self.selected = False
        # Base Window
        if self.vertical:
            self.main_layout = QtWidgets.QVBoxLayout()
        else:
            self.main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.main_layout)
        self.setStyleSheet("font-weight: bold")
        # Components
        self.up_btn = QtWidgets.QPushButton(self.up_text)
        self.up_btn.setFixedSize(self.btn_size[0], self.btn_size[1])
        self.label = QtWidgets.QLabel(self.text)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, 
                                 QtWidgets.QSizePolicy.Expanding)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.down_btn = QtWidgets.QPushButton(self.down_text)
        self.down_btn.setFixedSize(self.btn_size[0], self.btn_size[1])
        # Assemble Components
        self.main_layout.addWidget(self.up_btn)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.down_btn)
        # Component Settings
        self.main_layout.setAlignment(QtCore.Qt.AlignVCenter)
        self.main_layout.setAlignment(QtCore.Qt.AlignHCenter)
        self.up_btn.setIcon(QtGui.QIcon(self.up_icon)) 
        self.down_btn.setIcon(QtGui.QIcon(self.down_icon)) 
        self.up_btn.setStyleSheet(self.stylesheet)
        self.down_btn.setStyleSheet(self.stylesheet)


class NavGrid(QtWidgets.QTableWidget):
    '''Navigation Widget to Control a Camera's Transformation Attributes
        NOTES:
            > Increment Widget for setting the step size is not parented within the 
            Table Widget and must be assigned to a separate external layout.
    '''
    def __init__(self, parent=None):
        super(NavGrid, self).__init__(parent=parent)
        # Initial Table Widget Settings
        self.attr = "tx"
        self.setObjectName("NavGrid")
        self.setRowCount(2)
        self.setColumnCount(3)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # StyleSheets for buttons
        self.red = '''QPushButton:pressed {
                            color: white;
                            background: rgb(200,50,50);
                            }'''
        self.blue = '''QPushButton:pressed {
                            color: white;
                            background: rgb(0,100,255);
                            }'''
        self.green = '''QPushButton:pressed {
                            color: white;
                            background: rgb(0,200,100);
                            }'''
        # Components
        self.increments_widget = StepWidget() # Will be added to separate layout in parent widget
        self.tx = UpDownButtons(text="tx", up_text="", down_text="")
        self.ty = UpDownButtons(text="ty", up_text="", down_text="")
        self.tz = UpDownButtons(text="tz", up_text="", down_text="")
        self.rx = UpDownButtons(text="rx", up_text="", down_text="")
        self.ry = UpDownButtons(text="ry", up_text="", down_text="")
        self.rz = UpDownButtons(text="rz", up_text="", down_text="")
        # Assemble Components
        self.setCellWidget(0,0,self.tx)
        self.setCellWidget(0,1,self.ty)
        self.setCellWidget(0,2,self.tz)
        self.setCellWidget(1,0,self.rx)
        self.setCellWidget(1,1,self.ry)
        self.setCellWidget(1,2,self.rz)
        # Component Settings
        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        # Button Methods
        self.tx.up_btn.clicked.connect(  partial( self.set_attr, "tx", False))
        self.tx.down_btn.clicked.connect(partial( self.set_attr, "tx", True) )
        self.ty.up_btn.clicked.connect(  partial( self.set_attr, "ty", False))
        self.ty.down_btn.clicked.connect(partial( self.set_attr, "ty", True) )
        self.tz.up_btn.clicked.connect(  partial( self.set_attr, "tz", False))
        self.tz.down_btn.clicked.connect(partial( self.set_attr, "tz", True) )
        self.rx.up_btn.clicked.connect(  partial( self.set_attr, "rx", False))
        self.rx.down_btn.clicked.connect(partial( self.set_attr, "rx", True) )
        self.ry.up_btn.clicked.connect(  partial( self.set_attr, "ry", False))
        self.ry.down_btn.clicked.connect(partial( self.set_attr, "ry", True) )
        self.rz.up_btn.clicked.connect(  partial( self.set_attr, "rz", False))
        self.rz.down_btn.clicked.connect(partial( self.set_attr, "rz", True) )
        # Button color when clicked
        self.tx.up_btn.setStyleSheet(self.red)
        self.tx.down_btn.setStyleSheet(self.red)
        self.ty.up_btn.setStyleSheet(self.green)
        self.ty.down_btn.setStyleSheet(self.green)
        self.tz.up_btn.setStyleSheet(self.blue)
        self.tz.down_btn.setStyleSheet(self.blue)
        self.rx.up_btn.setStyleSheet(self.red)
        self.rx.down_btn.setStyleSheet(self.red)
        self.ry.up_btn.setStyleSheet(self.green)
        self.ry.down_btn.setStyleSheet(self.green)
        self.rz.up_btn.setStyleSheet(self.blue)
        self.rz.down_btn.setStyleSheet(self.blue)
        # Finalize
        self.setWindowFlags(QtCore.Qt.Window)

    def mouseReleaseEvent(self, event):
        '''Determine which one of the six manipulation options is selected'''
        super(NavGrid, self).mousePressEvent(event)
        index = self.indexAt(event.pos())
        if index.isValid():
            self.selectedCell = [self.currentRow(), self.currentColumn()]
            self.current_attr = self.cellWidget(self.currentRow(), 
                                                self.currentColumn()).label.text()
            self.attr = self.current_attr
        else:
            self.selectedCell = [-1,-1]
            self.current_attr = ""
            self.setCurrentIndex(QtCore.QModelIndex())
        
    def keyPressEvent(self,event):
        '''Settings for arrow keys. 
        NOTES:
            Left/Right for changing which attribute is being modified. 
            Up/Down applies transformation to selected attribute.
        '''
        self.selectedCell = [self.currentRow(), self.currentColumn()]
        cell_num = (self.columnCount()*self.currentRow()) + self.currentColumn()
        par = cmds.listRelatives(self.get_current_camera(),parent=True)[0]
        # Left Arrow Key
        if event.key() == QtCore.Qt.Key_Left:
            if cell_num == 0:
                new_selected_cell = 5
            else:
                new_selected_cell = cell_num - 1
            new_selected_cell = [(new_selected_cell-(new_selected_cell % self.columnCount())) / self.rowCount(), 
                                new_selected_cell % self.columnCount()]
            self.setCurrentCell(new_selected_cell[0], new_selected_cell[1])
            if self.cellWidget(new_selected_cell[0], new_selected_cell[1]):
                self.attr = self.cellWidget(new_selected_cell[0], new_selected_cell[1]).label.text()
            else:
                self.attr = ""
        # Right Arrow Key
        if event.key() == QtCore.Qt.Key_Right:
            if cell_num == 5:
                new_selected_cell = 0
            else:
                new_selected_cell = cell_num + 1
            new_selected_cell = [(new_selected_cell-(new_selected_cell % self.columnCount())) / self.rowCount(), 
                                new_selected_cell % self.columnCount()]
            self.setCurrentCell(new_selected_cell[0], new_selected_cell[1])
            if self.cellWidget(new_selected_cell[0], new_selected_cell[1]):
                self.attr = self.cellWidget(new_selected_cell[0], new_selected_cell[1]).label.text()
            else:
                self.attr = ""
        # Up Arrow Key
        if event.key() == QtCore.Qt.Key_Up:
            if self.attr:
                full_attr = "{}.{}".format(par, self.attr)
                current = cmds.getAttr("{}.{}".format(par, self.attr))
                locked = cmds.getAttr(full_attr, lock=True)
                if locked:
                    cmds.setAttr(full_attr, lock=False)
                    cmds.setAttr("{}.{}".format(par, self.attr), 
                                current + self.increments_widget.step_box.value())
                    cmds.setAttr(full_attr, lock=True)
                else:
                    cmds.setAttr("{}.{}".format(par, self.attr), 
                                current + self.increments_widget.step_box.value())
        # Down Arrow Key
        if event.key() == QtCore.Qt.Key_Down:
            if self.attr:
                full_attr = "{}.{}".format(par, self.attr)
                current = cmds.getAttr("{}.{}".format(par, self.attr))
                locked = cmds.getAttr(full_attr, lock=True)
                if locked:
                    cmds.setAttr(full_attr, lock=False)
                    cmds.setAttr("{}.{}".format(par, self.attr), 
                                current - self.increments_widget.step_box.value())
                    cmds.setAttr(full_attr, lock=True)
                else:
                    cmds.setAttr("{}.{}".format(par, self.attr), 
                                current - self.increments_widget.step_box.value())

    def get_current_camera(self):
        '''Get the current camera being used in the active viewport.'''
        cur_view = OpenMayaUI.M3dView.active3dView()
        cur_cam = OpenMaya.MDagPath()
        cur_view.getCamera(cur_cam)
        cur_camPath = cur_cam.fullPathName()
        cur_camPath = cur_camPath.split("|")[-1]
        return cur_camPath
    
    def adjust_value(self, object_name, attribute="", increment=1, negative=False):
        '''Orients or translates the specified object along a specific axis by a specific increment.
        Good for manually adjusting camera to match perspective of grid to concept art for modeling.'''
        attribute_name = "{}.{}".format(object_name, attribute)
        # Adjust Camera
        current_val = cmds.getAttr(attribute_name)
        locked = cmds.getAttr(attribute_name, lock=True)
        if locked:
            cmds.setAttr(attribute_name, lock=False)
            if negative:
                output = current_val - increment
                cmds.setAttr(attribute_name, output)
            else:
                output = current_val + increment
                cmds.setAttr(attribute_name, output)
            cmds.setAttr(attribute_name, lock=True)
        else:
            if negative:
                output = current_val - increment
                cmds.setAttr(attribute_name, output)
            else:
                output = current_val + increment
                cmds.setAttr(attribute_name, output)
            
    def set_attr(self, attr, neg):
        '''Change value of selected object(s)
            Parameters:
                    attr: transform attribute to be modified
                    neg: Boolean value determining if value should be added or subtracted'''
        cam = cmds.listRelatives(self.get_current_camera(), parent=True)[0]
        inc = self.increments_widget.step_box.value()
        self.adjust_value(object_name=cam,
                          attribute=attr,
                          increment=inc,
                          negative=neg)


class StepWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, limits=[0, 180], text="Step Size:", 
                 decimals=3, step_size=1.0, default_val=1.0):
        '''Incremental widget for Determining how much a camera is rotated or translated
            Parameters:
                    text        : text for label.
                    limits      : min and max values of spinbox.
                    decimals    : number of decimals to display in spinbox.
                    step_size   : step-value increment when up or down button pushed.
                    default_val : initial value in the spinbox when loaded.
        '''
        super(StepWidget, self).__init__(parent)
        # Members
        self.text        = text
        self.limits      = limits
        self.decimals    = decimals
        self.step_size   = step_size
        self.default_val = default_val
        # Components
        self.main_layout = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel(self.text)
        self.step_box = QtWidgets.QDoubleSpinBox()
        # Assemble
        self.setLayout(self.main_layout)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.step_box)
        # Settings
        self.step_box.setDecimals(self.decimals)
        self.step_box.setSingleStep(self.step_size)
        self.step_box.setValue(self.default_val)
        if self.limits[0] and self.limits[1]: 
            if self.limits[0] >= self.max:
                LOG.error("Minimum is set greater than or equal to maximum.")
        if self.limits[0]:
            if self.default_val < self.limits[0]:
                self.step_box.setValue(self.limits[0])
            self.step_box.setMinimum(self.limits[0])
        if self.limits[1]:
            if self.default_val > self.limits[1]:
                self.step_box.setValue(self.limits[1])
            self.step_box.setMaximum(self.limits[1])