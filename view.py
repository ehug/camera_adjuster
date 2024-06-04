'''
# ================================================================================================ #
Camera Adjuster 2.0

Purpose: To pose camera for modeling objects from reference images

Dependencies:
            maya
            PySide2

Author: Eric Hug

Updated: 6/02/2024

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

from PySide2 import QtWidgets, QtCore, QtGui
from shiboken2 import wrapInstance
from maya import cmds
from maya import OpenMaya
from maya import OpenMayaUI

# ================================================================================================ #
# VARIABLES
LOG = logging.getLogger(__name__)
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
        # ------------------------- #
        # Camera Combo Box Controls
        # ------------------------- #
        self.cameras_list_widget  = QtWidgets.QWidget()
        self.cameras_list_hLayout = QtWidgets.QHBoxLayout()
        self.cameras_list_widget.setLayout(self.cameras_list_hLayout)
        self.cameras_list_hLayout.setAlignment(QtCore.Qt.AlignLeft)
        self.cameras_list_hLayout.setContentsMargins(QtCore.QMargins(0,0,0,0))
        self.combo_box = QtWidgets.QComboBox()
        self.combo_box.setFixedHeight(32)
        self.combo_box.currentTextChanged.connect(self.change_camera)
        self.refresh_icon = QtGui.QIcon(os.path.dirname(os.path.realpath(__file__)) + 
                                        "/icons/refresh_btn.jpg")
        self.refresh_btn  = QtWidgets.QPushButton(self.refresh_icon, "")
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.clicked.connect(self.load_cameras)
        self.refresh_btn.setStyleSheet('''QPushButton:pressed {background: rgb(200,200,200);
                                                              }''')
        self.refresh_btn.setToolTip("Refresh list of existing cameras")
        self.cameras_list_hLayout.addWidget(self.combo_box)
        self.cameras_list_hLayout.addWidget(self.refresh_btn)
        self.load_cameras()
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
        self.load_pan()
        self.load_zoom()
        self.reset_pan_btn = QtWidgets.QPushButton("Reset Camera Pan")
        self.reset_pan_btn.clicked.connect(self.grid_widget.reset_pan)
        self.local_camera_vlayout.addWidget(self.reset_pan_btn)
        self.zoom_btn = QtWidgets.QPushButton("Reset Camera Zoom")
        self.zoom_btn.clicked.connect(self.grid_widget.reset_zoom)
        self.local_camera_vlayout.addWidget(self.zoom_btn)
        # ------------------------------- #
        # Assemble Widgets to Main Layout
        # ------------------------------- #
        self.main_layout.addWidget(self.cameras_list_widget)
        self.main_layout.addItem(self.spacer)
        self.main_layout.addWidget(self.separator)
        self.main_layout.addWidget(self.body_widget)
        # Finalize
        new_cam = self.combo_box.currentText()
        cmds.lookThru(new_cam)
        cmds.setAttr("{}.panZoomEnabled".format(new_cam), True)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)
        self.main_layout.setSpacing(0)
        self.setWindowFlags(QtCore.Qt.Window)

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

    def change_camera(self):
        '''Change camera chen combo box text changes.'''
        if self.combo_box.currentText():
            new_cam = self.combo_box.currentText()
            cmds.lookThru(new_cam)
            # Allow pan and zoom attributes to be adjusted when switching to new camera
            cmds.setAttr("{}.panZoomEnabled".format(new_cam), True)
            self.change_image_display()
            self.grid_widget.camera=new_cam
            self.load_pan()
            self.load_zoom()

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
        self.grid_widget.scale(1/zoom,1/zoom)

    def zoom_image(self):
        '''Changes the value of attribute zoom on active camera'''
        current_cam = self.combo_box.currentText()
        val = self.zoom_widget.spinbox.value() / 100.000
        cmds.setAttr("{}.zoom".format(current_cam), val)
        img_plane_scale = 1.0 / val
        self.image_plane_point.setScale(img_plane_scale)


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
        y = -(center.y() - 4)
        cmds.setAttr("{}.horizontalPan".format(self.camera), (x/self.width))
        cmds.setAttr("{}.verticalPan".format(self.camera), (y/self.height))


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
                current = cmds.getAttr("{}.{}".format(par, self.attr))
                cmds.setAttr("{}.{}".format(par, self.attr), 
                             current + self.increments_widget.step_box.value())
        # Down Arrow Key
        if event.key() == QtCore.Qt.Key_Down:
            if self.attr:
                current = cmds.getAttr("{}.{}".format(par, self.attr))
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