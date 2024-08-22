# This Python file uses the following encoding: utf-8
import sys
from pathlib import Path

import pymongo
import os, glob, json

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import Qt, QObject, QFileInfo, QAbstractTableModel, QModelIndex, QDir, QUrl, qDebug, Signal, Slot, QRunnable, QThreadPool, Property

import DBwin


if __name__ == "__main__":
    # qmlRegisterType<TableModel>("TableModel", 0, 1, "TableModel");

    app = QGuiApplication(sys.argv)
    DBwin.MAINApp()

    sys.exit(app.exec())


