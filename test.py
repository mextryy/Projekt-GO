import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QListWidget, QMessageBox, QFileDialog
)
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QPointF
import math

# --- Geometry classes ---

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def translate(self, dx, dy):
        self.x += dx
        self.y += dy

    def scale(self, sx, sy, center):
        self.x = center.x + sx * (self.x - center.x)
        self.y = center.y + sy * (self.y - center.y)

    def rotate(self, angle_deg, center):
        angle_rad = math.radians(angle_deg)
        x_shifted = self.x - center.x
        y_shifted = self.y - center.y
        x_new = x_shifted * math.cos(angle_rad) - y_shifted * math.sin(angle_rad)
        y_new = x_shifted * math.sin(angle_rad) + y_shifted * math.cos(angle_rad)
        self.x = center.x + x_new
        self.y = center.y + y_new

    def to_dict(self):
        return {'x': self.x, 'y': self.y}

    @staticmethod
    def from_dict(d):
        return Point(d['x'], d['y'])


class Polygon:
    def __init__(self, points=None):
        self.points = points if points else []

    def translate(self, dx, dy):
        for p in self.points:
            p.translate(dx, dy)

    def scale(self, sx, sy, center):
        for p in self.points:
            p.scale(sx, sy, center)

    def rotate(self, angle_deg, center):
        for p in self.points:
            p.rotate(angle_deg, center)

    def to_dict(self):
        return {'points': [p.to_dict() for p in self.points]}

    @staticmethod
    def from_dict(d):
        pts = [Point.from_dict(pd) for pd in d['points']]
        return Polygon(pts)

    def center(self):
        if not self.points:
            return Point(0, 0)
        x_avg = sum(p.x for p in self.points) / len(self.points)
        y_avg = sum(p.y for p in self.points) / len(self.points)
        return Point(x_avg, y_avg)


# --- Canvas widget for drawing ---

class Canvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.shapes = []  # list of Polygon objects
        self.selected_index = None
        self.setMinimumSize(600, 400)
        self.setMouseTracking(True)
        self.dragging_point_index = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        pen_normal = QPen(Qt.black, 2)
        pen_selected = QPen(Qt.red, 3)
        for i, shape in enumerate(self.shapes):
            pen = pen_selected if i == self.selected_index else pen_normal
            painter.setPen(pen)
            pts = [QPointF(p.x, p.y) for p in shape.points]
            if len(pts) == 1:
                painter.drawEllipse(pts[0], 5, 5)
            elif len(pts) > 1:
                for j in range(len(pts)):
                    painter.drawEllipse(pts[j], 4, 4)
                    if j < len(pts) - 1:
                        painter.drawLine(pts[j], pts[j + 1])
                # close polygon
                if len(pts) > 2:
                    painter.drawLine(pts[-1], pts[0])

    def mousePressEvent(self, event):
        # Check if clicked near any point to select shape or drag point
        pos = event.pos()
        for i, shape in enumerate(self.shapes):
            for j, p in enumerate(shape.points):
                dist = math.hypot(p.x - pos.x(), p.y - pos.y())
                if dist < 8:
                    self.selected_index = i
                    self.dragging_point_index = j
                    self.update()
                    return
        self.selected_index = None
        self.update()

    def mouseMoveEvent(self, event):
        if self.dragging_point_index is not None and self.selected_index is not None:
            pos = event.pos()
            shape = self.shapes[self.selected_index]
            shape.points[self.dragging_point_index].x = pos.x()
            shape.points[self.dragging_point_index].y = pos.y()
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging_point_index = None


# --- Main Application Window ---

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interaktywny system transformacji 2D")
        self.canvas = Canvas()

        # Controls
        self.list_shapes = QListWidget()
        self.btn_add_point = QPushButton("Dodaj punkt")
        self.btn_add_polygon = QPushButton("Dodaj wielokąt")
        self.btn_delete_shape = QPushButton("Usuń wybrany")
        self.btn_translate = QPushButton("Translacja")
        self.btn_scale = QPushButton("Skalowanie")
        self.btn_rotate = QPushButton("Obrót")
        self.btn_undo = QPushButton("Cofnij")
        self.btn_save = QPushButton("Zapisz do pliku")
        self.btn_load = QPushButton("Wczytaj z pliku")

        self.input_dx = QLineEdit("0")
        self.input_dy = QLineEdit("0")
        self.input_sx = QLineEdit("1")
        self.input_sy = QLineEdit("1")
        self.input_angle = QLineEdit("0")

        self.history = []  # do undo

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        # Left: canvas
        layout.addWidget(self.canvas, 3)

        # Right: controls
        control_layout = QVBoxLayout()
        layout.addLayout(control_layout, 1)

        control_layout.addWidget(QLabel("Obiekty:"))
        control_layout.addWidget(self.list_shapes)
        control_layout.addWidget(self.btn_add_point)
        control_layout.addWidget(self.btn_add_polygon)
        control_layout.addWidget(self.btn_delete_shape)

        control_layout.addWidget(QLabel("Translacja (dx, dy):"))
        hl1 = QHBoxLayout()
        hl1.addWidget(self.input_dx)
        hl1.addWidget(self.input_dy)
        control_layout.addLayout(hl1)
        control_layout.addWidget(self.btn_translate)

        control_layout.addWidget(QLabel("Skalowanie (sx, sy):"))
        hl2 = QHBoxLayout()
        hl2.addWidget(self.input_sx)
        hl2.addWidget(self.input_sy)
        control_layout.addLayout(hl2)
        control_layout.addWidget(self.btn_scale)

        control_layout.addWidget(QLabel("Obrót (stopnie):"))
        control_layout.addWidget(self.input_angle)
        control_layout.addWidget(self.btn_rotate)

        control_layout.addWidget(self.btn_undo)
        control_layout.addWidget(self.btn_save)
        control_layout.addWidget(self.btn_load)

        control_layout.addStretch()

    def _connect_signals(self):
        self.btn_add_point.clicked.connect(self.add_point)
        self.btn_add_polygon.clicked.connect(self.add_polygon)
        self.btn_delete_shape.clicked.connect(self.delete_shape)
        self.btn_translate.clicked.connect(self.translate_shape)
        self.btn_scale.clicked.connect(self.scale_shape)
        self.btn_rotate.clicked.connect(self.rotate_shape)
        self.btn_undo.clicked.connect(self.undo)
        self.btn_save.clicked.connect(self.save_to_file)
        self.btn_load.clicked.connect(self.load_from_file)
        self.list_shapes.currentRowChanged.connect(self.select_shape)
        self.canvas.mouseReleaseEvent = self.on_canvas_mouse_release

    def add_point(self):
        p = Polygon([Point(100, 100)])
        self.canvas.shapes.append(p)
        self.list_shapes.addItem("Punkt")
        self.save_history()
        self.canvas.update()

    def add_polygon(self):
        # Dodaj prosty trójkąt na sztywno
        p = Polygon([Point(200, 200), Point(250, 200), Point(225, 150)])
        self.canvas.shapes.append(p)
        self.list_shapes.addItem("Wielokąt")
        self.save_history()
        self.canvas.update()

    def delete_shape(self):
        idx = self.list_shapes.currentRow()
        if idx >= 0:
            del self.canvas.shapes[idx]
            self.list_shapes.takeItem(idx)
            self.canvas.selected_index = None
            self.save_history()
            self.canvas.update()

    def select_shape(self, index):
        self.canvas.selected_index = index
        self.canvas.update()

    def save_history(self):
        # Zapisujemy głęboką kopię kształtów do historii do cofania
        snapshot = json.dumps([shape.to_dict() for shape in self.canvas.shapes])
        self.history.append(snapshot)
        # Limit historii do 20
        if len(self.history) > 20:
            self.history.pop(0)

    def undo(self):
        if len(self.history) < 2:
            QMessageBox.information(self, "Cofnij", "Brak wcześniejszego stanu do cofnięcia.")
            return
        self.history.pop()  # usuwamy obecny
        last = self.history[-1]
        shapes_data = json.loads(last)
        self.canvas.shapes = [Polygon.from_dict(d) for d in shapes_data]
        self.list_shapes.clear()
        for s in self.canvas.shapes:
            if len(s.points) == 1:
                self.list_shapes.addItem("Punkt")
            else:
                self.list_shapes.addItem("Wielokąt")
        self.canvas.selected_index = None
        self.canvas.update()

    def get_selected_shape(self):
        idx = self.canvas.selected_index
        if idx is None or idx < 0 or idx >= len(self.canvas.shapes):
            QMessageBox.warning(self, "Błąd", "Wybierz najpierw obiekt.")
            return None
        return self.canvas.shapes[idx]

    def translate_shape(self):
        shape = self.get_selected_shape()
        if not shape:
            return
        try:
            dx = float(self.input_dx.text())
            dy = float(self.input_dy.text())
        except ValueError:
            QMessageBox.warning(self, "Błąd", "Nieprawidłowe wartości dx lub dy.")
            return
        shape.translate(dx, dy)
        self.save_history()
        self.canvas.update()

    def scale_shape(self):
        shape = self.get_selected_shape()
        if not shape:
            return
        try:
            sx = float(self.input_sx.text())
            sy = float(self.input_sy.text())
        except ValueError:
            QMessageBox.warning(self, "Błąd", "Nieprawidłowe wartości sx lub sy.")
            return
        center = shape.center()
        shape.scale(sx, sy, center)
        self.save_history()
        self.canvas.update()

    def rotate_shape(self):
        shape = self.get_selected_shape()
        if not shape:
            return
        try:
            angle = float(self.input_angle.text())
        except ValueError:
            QMessageBox.warning(self, "Błąd", "Nieprawidłowa wartość kąta.")
            return
        center = shape.center()
        shape.rotate(angle, center)
        self.save_history()
        self.canvas.update()

    def save_to_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Zapisz scenę", "", "JSON files (*.json)")
        if filename:
            try:
                data = [shape.to_dict() for shape in self.canvas.shapes]
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                QMessageBox.information(self, "Zapis", "Zapisano pomyślnie.")
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie udało się zapisać pliku:\n{e}")

    def load_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Wczytaj scenę", "", "JSON files (*.json)")
        if filename:
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                self.canvas.shapes = [Polygon.from_dict(d) for d in data]
                self.list_shapes.clear()
                for s in self.canvas.shapes:
                    if len(s.points) == 1:
                        self.list_shapes.addItem("Punkt")
                    else:
                        self.list_shapes.addItem("Wielokąt")
                self.canvas.selected_index = None
                self.save_history()
                self.canvas.update()
                QMessageBox.information(self, "Wczytaj", "Wczytano pomyślnie.")
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie udało się wczytać pliku:\n{e}")

    def on_canvas_mouse_release(self, event):
        # Po zmianie pozycji punktu na canvas, zapisujemy stan
        if self.canvas.dragging_point_index is not None:
            self.save_history()
        self.canvas.dragging_point_index = None
        self.canvas.update()
        QWidget.mouseReleaseEvent(self.canvas, event)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 600)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":

    main()