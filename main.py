# This Python file uses the following encoding: utf-8
import sys
from pathlib import Path

import pymongo
import os, glob, json

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import Qt, QObject, QFileInfo, QAbstractTableModel, QModelIndex, QDir, QUrl, qDebug, Signal, Slot, QRunnable, QThreadPool, Property


from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow

import DBwin

if __name__ == "__main__":
    app = QApplication(['View Relu Results'])
    screens = app.screens()
    screen = screens[0]

    #titlebar_height = _qapp.qapp.style().pixelMetric(QStyle.PM_TitleBarHeight)
    #w = screen.size().width()
    #h = screen.availableGeometry().height() - titlebar_height
    #app_sz = [int(w * 1 / 3), h]

    print("Screen Size:",screen.size().width(),screen.availableGeometry().height())

    app_Main = DBwin.MAINApp()
    app_Main.show()

    sys.exit(app.exec())


