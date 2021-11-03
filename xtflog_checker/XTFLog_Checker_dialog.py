# -*- coding: utf-8 -*-
"""
/***************************************************************************
 XTFLog_CheckerDialog
 A QGIS plugin to visualize XTF files of the class IliVErrors.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-07-13
        git sha              : $Format:%H$
        copyright            : (C) 2021 by GeoWerkstatt GmbH
        email                : support@geowerkstatt.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 3 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import QVariant, Qt
from qgis.core import QgsVectorLayer, QgsField, QgsProject, QgsFeature, QgsGeometry, QgsPointXY, QgsEditorWidgetSetup, QgsMapLayerType
from PyQt5.QtCore import QCoreApplication
import requests
import re
import xml.etree.ElementTree as ET
from .XTFLog_Checker_dock_panel import XTFLog_DockPanel

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/dialog_base.ui'))

class XTFLog_CheckerDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, file_path=None, parent=None):
        """Constructor."""
        super(XTFLog_CheckerDialog, self).__init__(parent)
        self.setupUi(self)
        self.btn_input.clicked.connect(self.getInputFile)
        self.btn_run.clicked.connect(self.visualizeLog)
        self.btn_run.setText(QCoreApplication.translate('generals', 'Create layer'))
        self.btn_run.setEnabled(file_path != None)
        self.btn_cancel.clicked.connect(self.closePlugin)
        self.btn_cancel.setText(QCoreApplication.translate('generals', 'Cancel'))
        self.attributeNames = ["Type", "Message", "Tid", "ObjTag", "TechId", "UserId", "IliQName", "DataSource", "Line", "TechDetail"]
        self.btn_show_error_log.clicked.connect(self.showErrorLog)
        self.btn_show_error_log.setText(QCoreApplication.translate('generals', 'Show error log'))
        self.newLayerGroupBox.setTitle(QCoreApplication.translate('generals', 'Upload xtf-log file'))
        self.existingLayerGroupBox.setTitle(QCoreApplication.translate('generals', 'Show log for existing layer'))
        self.existingLayerLabel.setText(QCoreApplication.translate('generals', 'Only layers created with this plugin can be selected'))
        self.dock = None
        self.errorLayer = None
        self.iface = iface
        self.txt_input.setText(file_path)
        self.txt_input.textChanged.connect(self.inputTextChanged)

    def showEvent(self, event):
        self.updateLayerCombobox()

    def getInputFile(self):
        self.btn_run.setEnabled(False)
        datei = QtWidgets.QFileDialog.getOpenFileName(None, 'Upload', filter="*.xtf")[0]
        self.txt_input.setText(datei)

    def inputTextChanged(self):
        if self.txt_input.text() == "":
            self.btn_run.setEnabled(False)
        else:
            self.btn_run.setEnabled(True)

    def visualizeLog(self):
        path = self.txt_input.text()
        fileName = None
        if(path.startswith("http")):
            try:
                xml_string = requests.get(path).content.decode("utf-8")
                if(len(xml_string)>5000000):
                    self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'Large file'),  QCoreApplication.translate('generals', 'Processing of large XTF-Log files might take a while'), duration=8)
                    self.iface.mainWindow().repaint()
                tree = ET.ElementTree(ET.fromstring(xml_string))
                fileName = re.findall("connectionId=(.*?)&fileExtension=", path)[0] if len(re.findall("connectionId=(.*?)&fileExtension=", path))!=0 else None
            except:
                self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No valid file'), QCoreApplication.translate('generals', 'Could not get a valid XTF-Log file from specified Url'), duration=8)
        else:
            try:
                if(os.path.getsize(path)>5000000):
                    self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'Large file'),  QCoreApplication.translate('generals', 'Processing of large XTF-Log files might take a while'), duration=8)
                    self.iface.mainWindow().repaint()
                tree = ET.parse(path)
                fileName, fileExtension = os.path.splitext(os.path.basename(path))
            except:
                self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No valid file'), QCoreApplication.translate('generals', 'No valid XTF-Log file at specified Path'), duration=8)

        if fileName != None:
            root = tree.getroot()
            x = None
            y = None
            errorLayer = QgsVectorLayer("Point?crs=epsg:2056", fileName + "_Ilivalidator_Errors", "memory")
            errorDataProvider = errorLayer.dataProvider()

            errorDataProvider.addAttributes([QgsField("ErrorId", QVariant.String),
                                            QgsField("Type", QVariant.String),
                                            QgsField("Message", QVariant.String),
                                            QgsField("Tid", QVariant.String),
                                            QgsField("ObjTag", QVariant.String),
                                            QgsField("TechId", QVariant.String),
                                            QgsField("UserId", QVariant.String),
                                            QgsField("IliQName", QVariant.String),
                                            QgsField("DataSource", QVariant.String),
                                            QgsField("Line", QVariant.String),
                                            QgsField("TechDetail", QVariant.String),
                                            QgsField("Checked", QVariant.Int)])

            errorLayer.updateFields()

            # Hide Checked attribute from user
            setup = QgsEditorWidgetSetup('Hidden', {})
            error_idx = errorLayer.fields().indexFromName('Checked')
            errorLayer.setEditorWidgetSetup(error_idx, setup)

            # Remove layer if exists
            existing_error_layer = QgsProject.instance().mapLayersByName("Ilivalidator_errors")
            if len(existing_error_layer) != 0:
                QgsProject.instance().removeMapLayer(existing_error_layer[0])

            QgsProject.instance().addMapLayer(errorLayer)

            interlisPrefix = '{http://www.interlis.ch/INTERLIS2.3}'
            for child in root.iter(interlisPrefix + 'IliVErrors.ErrorLog.Error'):
                ErrorId = child.attrib["TID"]
                attributes = {}
                for attributeName in self.attributeNames:
                    element = child.find(interlisPrefix + attributeName)
                    attributes[attributeName] = (element.text if element != None else "")
                if attributes["Type"] == 'Error' or attributes["Type"] == 'Warning':
                    GeometryElement = child.find(interlisPrefix + 'Geometry')
                    if GeometryElement != None:
                        Coordinate = GeometryElement.find(interlisPrefix + 'COORD');
                        if Coordinate != None:
                            f = QgsFeature()
                            x = Coordinate.find(interlisPrefix + 'C1').text
                            y = Coordinate.find(interlisPrefix + 'C2').text
                            if(x and y):
                                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(x), float(y))))
                            attributeList = [ErrorId]
                            attributeList.extend(list(attributes.values()))
                            # set Checked attribute to unchecked
                            attributeList.append(0)
                            f.setAttributes(attributeList)
                            errorDataProvider.addFeature(f)
            if(errorLayer.featureCount()== 0):
                QgsProject.instance().removeMapLayer(errorLayer)
                self.iface.messageBar().pushMessage(QCoreApplication.translate('generals', 'No Errors'), QCoreApplication.translate('generals', 'The selected XTF file contains no Ilivalidator-Errors, select another file.'), duration=8)
                self.close()
                return

            errorLayer.updateExtents()
            self.errorLayer = errorLayer
            self.hideCheckedColumns(errorLayer)

            if(self.errorLayer != None):
                self.showDock()
            self.close()

    def showErrorLog(self):
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == self.layerbox.currentText():
                self.errorLayer = layer
                self.showDock()

    def hideCheckedColumns(self, layer):
        config = layer.attributeTableConfig()
        columns = config.columns()
        for column in columns:
            if column.name == "Checked":
                column.hidden = True
                break
        config.setColumns(columns)
        layer.setAttributeTableConfig(config)

    def updateLayerCombobox(self):
        self.layerbox.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayerType.VectorLayer:
                if all(x in layer.fields().names() for x in self.attributeNames):
                    self.layerbox.addItem(layer.name())

    def showDock(self):
        for dock in self.iface.mainWindow().findChildren(XTFLog_DockPanel):
            self.iface.removeDockWidget(dock)
        self.dock = XTFLog_DockPanel(self.iface, self.errorLayer)
        self.iface.addTabifiedDockWidget(Qt.RightDockWidgetArea, self.dock, raiseTab=True)
        self.close()

    def closePlugin(self):
        self.close()
        if self.dock != None:
            self.iface.removeDockWidget(self.dock)
